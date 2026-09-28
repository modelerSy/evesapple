import asyncio
import json
import os
import time
from typing import Any
from pathlib import Path
from uuid import uuid4

import httpx

class AIQError(RuntimeError):
    pass


def _enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


async def _command(args: list[str], timeout_seconds: float = 45.0) -> str:
    """Run one OpenShell CLI operation without shell interpolation or secrets."""
    try:
        process = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    except FileNotFoundError as exc:
        raise AIQError("OpenShell CLI is not installed or is not on PATH") from exc
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except TimeoutError as exc:
        process.kill()
        await process.communicate()
        raise AIQError("OpenShell CLI operation timed out") from exc
    if process.returncode:
        raise AIQError(f"OpenShell CLI operation failed ({process.returncode}): {stderr.decode(errors='replace')[:800]}")
    return stdout.decode(errors="replace")


class OpenShellAIQTransport:
    """Makes the EVE Hunter's AI-Q HTTP calls from an OpenShell sandbox.

    The sandbox receives no project `.env` and no API keys. It is allowed only
    to call the loopback-only AI-Q host service through the documented
    `host.openshell.internal` route. AI-Q itself remains an independently
    operated service; this transport does not modify AI-Q core.
    """

    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.policy = os.getenv(
            "EVE_OPENSHELL_POLICY_FILE",
            str(root / "security" / "openshell" / "eve-evidence-hunter-policy.yaml"),
        )
        self.image = os.getenv("EVE_OPENSHELL_IMAGE", "eve-openshell-evidence-hunter:0.1")
        self.name = f"eve-h-{uuid4().hex[:10]}"
        self.base = "http://host.openshell.internal:8000"

    async def start(self) -> None:
        await _command([
            "openshell", "sandbox", "create", "--name", self.name,
            "--from", self.image, "--policy", self.policy,
            "--cpu", "1", "--memory", "512Mi", "--detach", "--no-tty",
            "--", "/bin/sh", "-c", "sleep 600",
        ])

    async def close(self) -> None:
        # Sandbox deletion is best-effort after the outcome is already known.
        try:
            await _command(["openshell", "sandbox", "delete", self.name], timeout_seconds=30)
        except AIQError:
            pass

    async def request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        args = [
            "openshell", "sandbox", "exec", "--name", self.name, "--no-login-shell", "--",
            "/usr/bin/curl", "--fail", "--silent", "--show-error", "--max-time", "30",
            "-X", method,
        ]
        if payload is not None:
            args += ["-H", "Content-Type: application/json", "--data", json.dumps(payload, ensure_ascii=False)]
        args.append(f"{self.base}{path}")
        raw = await _command(args)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AIQError("OpenShell AI-Q request returned invalid JSON") from exc


async def _run_shallow_research_openshell(query: str, timeout_seconds: float) -> dict[str, Any]:
    started = time.perf_counter()
    transport = OpenShellAIQTransport()
    try:
        await transport.start()
        submitted = await transport.request_json(
            "POST", "/v1/jobs/async/submit", {"agent_type": "shallow_researcher", "input": query}
        )
        job_id = submitted.get("job_id")
        if not job_id:
            raise AIQError("AI-Q submission through OpenShell did not return a job_id")
        deadline = time.perf_counter() + timeout_seconds
        while time.perf_counter() < deadline:
            data = await transport.request_json("GET", f"/v1/jobs/async/job/{job_id}")
            if data.get("status") in {"success", "completed"}:
                report = data.get("report") or data.get("result") or data.get("output") or ""
                if not report:
                    report_data = await transport.request_json("GET", f"/v1/jobs/async/job/{job_id}/report")
                    report = report_data.get("report") or report_data.get("content") or report_data.get("output") or ""
                if isinstance(report, dict):
                    report = report.get("report") or report.get("content") or str(report)
                return {
                    "job_id": job_id,
                    "report": report,
                    "latency_seconds": time.perf_counter() - started,
                    "execution_boundary": "openshell",
                }
            if data.get("status") in {"failed", "failure", "cancelled"}:
                raise AIQError(f"AI-Q job {job_id} ended with {data.get('status')}: {data.get('error')}")
            await asyncio.sleep(2)
        return {
            "job_id": job_id,
            "report": "",
            "timed_out": True,
            "latency_seconds": time.perf_counter() - started,
            "execution_boundary": "openshell",
        }
    finally:
        await transport.close()


async def run_shallow_research(query: str, timeout_seconds: float = 360.0) -> dict[str, Any]:
    if _enabled(os.getenv("EVE_OPENSHELL_ENABLED")):
        return await _run_shallow_research_openshell(query, timeout_seconds)
    base = os.getenv("AIQ_SERVER_URL", "http://127.0.0.1:8000").rstrip("/")
    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{base}/v1/jobs/async/submit", json={"agent_type": "shallow_researcher", "input": query})
        if response.is_error:
            raise AIQError(f"AI-Q submit failed ({response.status_code}): {response.text[:1000]}")
        job_id = response.json()["job_id"]
        deadline = time.perf_counter() + timeout_seconds
        while time.perf_counter() < deadline:
            result = await client.get(f"{base}/v1/jobs/async/job/{job_id}")
            result.raise_for_status()
            data = result.json()
            if data.get("status") in {"success", "completed"}:
                report = data.get("report") or data.get("result") or data.get("output") or ""
                if not report:
                    report_response = await client.get(f"{base}/v1/jobs/async/job/{job_id}/report")
                    if report_response.is_success:
                        report_payload = report_response.json()
                        report = report_payload.get("report") or report_payload.get("content") or report_payload.get("output") or ""
                if isinstance(report, dict):
                    report = report.get("report") or report.get("content") or str(report)
                return {"job_id": job_id, "report": report, "latency_seconds": time.perf_counter() - started}
            if data.get("status") in {"failed", "failure", "cancelled"}:
                raise AIQError(f"AI-Q job {job_id} ended with {data.get('status')}: {data.get('error')}")
            await asyncio.sleep(2)
    return {"job_id": job_id, "report": "", "timed_out": True, "latency_seconds": time.perf_counter() - started}
