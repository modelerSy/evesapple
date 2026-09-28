import asyncio
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agent.investigator import investigate_fast
from agent.nemotron_client import MissingNvidiaApiKey
from .models import InvestigationJob, InvestigationRequest

logger = logging.getLogger("eve.jobs")
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "eve_jobs.sqlite3"

def now():
    return datetime.now(timezone.utc).isoformat()

class JobManager:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.tasks: dict[str, asyncio.Task] = {}
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS investigation_jobs (
                id TEXT PRIMARY KEY, status TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, request_json TEXT NOT NULL,
                result_json TEXT, error TEXT, cancel_requested INTEGER NOT NULL DEFAULT 0
            )""")

    def create(self, request: InvestigationRequest) -> str:
        job_id = str(uuid.uuid4())
        timestamp = now()
        with self._connect() as conn:
            conn.execute("INSERT INTO investigation_jobs(id,status,created_at,updated_at,request_json) VALUES(?,?,?,?,?)",
                         (job_id, "QUEUED", timestamp, timestamp, request.model_dump_json()))
        self.tasks[job_id] = asyncio.create_task(self._run(job_id), name=f"eve-investigation-{job_id}")
        return job_id

    def _row(self, job_id):
        with self._connect() as conn:
            return conn.execute("SELECT * FROM investigation_jobs WHERE id=?", (job_id,)).fetchone()

    def get(self, job_id: str) -> InvestigationJob | None:
        row = self._row(job_id)
        if not row: return None
        result = json.loads(row["result_json"]) if row["result_json"] else None
        if result:
            # Older judge responses occasionally serialized list-shaped fields
            # as a single string. Normalize persisted results at the API
            # boundary so a completed investigation remains viewable.
            for item in result.get("components", []):
                for key in ("evidence_ids", "conflicts", "limitations"):
                    if isinstance(item.get(key), str):
                        item[key] = [item[key]] if item[key] else []
            for item in result.get("evidence", []):
                for key in ("limitations", "provenance"):
                    if isinstance(item.get(key), str):
                        item[key] = [item[key]] if item[key] else []
        return InvestigationJob(investigation_id=row["id"], status=row["status"], created_at=row["created_at"],
                                updated_at=row["updated_at"], result=result, error=row["error"])

    def _update(self, job_id, **values):
        values["updated_at"] = now()
        assignments = ", ".join(f"{key}=?" for key in values)
        with self._connect() as conn:
            conn.execute(f"UPDATE investigation_jobs SET {assignments} WHERE id=?", (*values.values(), job_id))

    def _cancelled(self, job_id):
        row = self._row(job_id)
        return not row or row["cancel_requested"] or row["status"] == "CANCELLED"

    async def _run(self, job_id):
        row = self._row(job_id)
        if not row: return
        self._update(job_id, status="RUNNING")
        try:
            request = InvestigationRequest.model_validate(json.loads(row["request_json"]))
            result = await investigate_fast(request)
            if self._cancelled(job_id): return
            self._update(job_id, status="COMPLETED", result_json=result.model_dump_json())
        except asyncio.CancelledError:
            self._update(job_id, status="CANCELLED", cancel_requested=1)
        except MissingNvidiaApiKey:
            logger.exception("job failed: missing NVIDIA API key")
            self._update(job_id, status="FAILED", error="NVIDIA API authentication is unavailable.")
        except Exception as exc:
            logger.exception("job failed type=%s", type(exc).__name__)
            if not self._cancelled(job_id):
                self._update(job_id, status="FAILED", error="EVE could not complete the investigation.")
        finally:
            self.tasks.pop(job_id, None)

    def clear_active(self) -> int:
        with self._connect() as conn:
            rows = conn.execute("SELECT id FROM investigation_jobs WHERE status IN ('QUEUED','RUNNING')").fetchall()
            ids = [row["id"] for row in rows]
            if ids:
                conn.executemany("DELETE FROM investigation_jobs WHERE id=?", [(item,) for item in ids])
        return len(ids)

    def resume_queued(self):
        with self._connect() as conn:
            # A process restart cannot continue an in-flight coroutine. Make
            # those records resumable only during the real service startup;
            # CLI inspection must never rewrite live job state.
            conn.execute("UPDATE investigation_jobs SET status='QUEUED', updated_at=? WHERE status='RUNNING'", (now(),))
            rows = conn.execute("SELECT id FROM investigation_jobs WHERE status='QUEUED' ORDER BY created_at").fetchall()
        for row in rows:
            if row["id"] not in self.tasks:
                self.tasks[row["id"]] = asyncio.create_task(self._run(row["id"]), name=f"eve-investigation-{row['id']}")
        return len(rows)

    def list_active(self):
        with self._connect() as conn:
            return conn.execute("SELECT id,status,created_at,updated_at FROM investigation_jobs WHERE status IN ('QUEUED','RUNNING') ORDER BY created_at").fetchall()

job_manager = JobManager()
