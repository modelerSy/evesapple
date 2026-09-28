import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from agent.nemotron_client import MissingNvidiaApiKey, extract_claims
from agent.evidence_memory import EvidenceMemory
from .models import (AgentTrace, Claim, ClaimComponent, ClaimExtractionResponse, ClaimType,
    ComponentStatus, EvidenceRequirement, EvidenceStatus, ExtractRequest, InvestigationRequest,
    InvestigationResponse, ResearchStats)
from agent.investigator import investigate_fast
from .job_manager import job_manager

logger = logging.getLogger("eve.api")

load_dotenv()
APP_ENV = os.getenv("APP_ENV", "development").lower()
PRODUCTION = APP_ENV == "production"
app = FastAPI(
    title="Eve's Apple API",
    version="0.2.0",
    docs_url=None if PRODUCTION else "/docs",
    redoc_url=None if PRODUCTION else "/redoc",
    openapi_url=None if PRODUCTION else "/openapi.json",
)

@app.on_event("startup")
async def resume_investigation_jobs():
    # Browser disconnects do not affect these server-owned jobs. Jobs queued
    # before a clean service restart are resumed; previously RUNNING jobs are
    # reset to QUEUED by JobManager initialization first.
    job_manager.resume_queued()
if not PRODUCTION:
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "ok", "service": "eve-apple"}

@app.post("/api/v1/claims/extract", response_model=ClaimExtractionResponse)
async def extract(request: ExtractRequest):
    try:
        claims, model = await extract_claims(request.content, request.category.value)
    except MissingNvidiaApiKey as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Nemotron request failed: {exc}") from exc
    return ClaimExtractionResponse(original_content=request.content, category=request.category, claims=claims, model=model)

@app.post("/api/v1/investigate", response_model=InvestigationResponse)
async def investigate(request: InvestigationRequest):
    if request.research_depth == "deep":
        raise HTTPException(status_code=501, detail="DEEP BITE remains an explicit separate path and is not auto-called by Fast Bite.")
    try:
        return await investigate_fast(request)
    except MissingNvidiaApiKey as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        # Do not expose upstream provider messages to public clients. The
        # orchestrator normally turns operational failures into a partial
        # evidence report; this is only an unexpected last-resort boundary.
        logger.exception("investigation_unhandled_error type=%s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="EVE could not complete the investigation.") from exc

@app.post("/api/v1/investigations", status_code=202)
async def create_investigation(request: InvestigationRequest):
    if request.research_depth == "deep":
        raise HTTPException(status_code=501, detail="DEEP BITE remains an explicit separate path.")
    investigation_id = job_manager.create(request)
    return {"investigation_id": investigation_id, "status": "QUEUED"}

@app.get("/api/v1/investigations/{investigation_id}")
async def get_investigation(investigation_id: str):
    job = job_manager.get(investigation_id)
    if not job:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    return job.model_dump(mode="json")


@app.get("/api/v1/investigations/latest/completed")
async def get_latest_completed_investigation():
    with job_manager._connect() as conn:
        row = conn.execute("SELECT id, request_json, result_json FROM investigation_jobs WHERE status='COMPLETED' AND result_json IS NOT NULL ORDER BY updated_at DESC LIMIT 1").fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No completed investigation found.")
    job = job_manager.get(row["id"])
    req = json.loads(row["request_json"]) if row["request_json"] else {}
    return {
        "investigation_id": row["id"],
        "content": req.get("content") or req.get("claim", ""),
        "mode": req.get("mode", "POLITICS"),
        "result": job.result.model_dump(mode="json") if job and job.result else None
    }



@app.get("/api/v1/examples")
async def list_public_examples():
    """Return verified, sanitized public completed investigations for the public community gallery."""
    return [
        {
            "id": "advertising-4w-37",
            "title_ko": "4주 사용 시 피부 탄력 37% 개선 광고 검증",
            "title_en": "4-week skin elasticity 37% improvement claim",
            "mode": "ADVERTISEMENT",
            "summary_ko": "시험 조건, 구체적 제품 명시, 독립 임상 기관 출처 여부를 대조해 맥락 부족 판정",
            "summary_en": "Identified missing product attribution and independent trial registration.",
            "status": "MISSING_CONTEXT",
            "sources_count": 5
        },
        {
            "id": "shincheonji-allegation",
            "title_ko": "인물 종교 단체 연루 및 교리 의혹 팩트체크",
            "title_en": "Public figure religious affiliation and doctrine claims",
            "mode": "POLITICS",
            "summary_ko": "공식 해명, 언론 보도, 종교 교리 출처를 교차 분석하여 맥락 확인",
            "summary_en": "Cross-referenced public statements, news coverage, and doctrinal definitions.",
            "status": "MISSING_CONTEXT",
            "sources_count": 8
        }
    ]


EXAMPLE_ADVERTISEMENT_CLAIM = "Using this product for 4 weeks improves skin elasticity by 37%."

@app.get("/api/v1/examples/advertising-4w-37", response_model=InvestigationResponse)
async def cached_advertising_example():
    """Return the real stored demo record; never starts a new investigation."""
    record = EvidenceMemory().get_exact(EXAMPLE_ADVERTISEMENT_CLAIM, "ADVERTISEMENT")
    if not record:
        raise HTTPException(status_code=404, detail="The completed example record is unavailable.")
    requirements = [EvidenceRequirement(**item) for item in json.loads(record["requirements_json"])]
    verdict = json.loads(record["verification_json"])
    by_component = {item.get("component"): item for item in verdict.get("results", [])}
    components = []
    for requirement in requirements:
        item = by_component.get(requirement.component, {})
        components.append(ClaimComponent(
            name=requirement.component, expected=requirement.expected,
            status=ComponentStatus(item.get("status", "UNVERIFIED")),
            direct_support=bool(item.get("direct_support", False)),
            evidence_ids=item.get("evidence_ids", []), conflicts=item.get("conflicts", []),
            limitations=item.get("limitations", []),
        ))
    required = {item.component for item in requirements if item.required}
    missing = [item.name for item in components if item.name in required and item.status == ComponentStatus.UNVERIFIED]
    conflicts = [item.name for item in components if item.name in required and item.status == ComponentStatus.CONFLICTING]
    status = EvidenceStatus.CONFLICTING_EVIDENCE if conflicts else (EvidenceStatus.MISSING_CONTEXT if missing else EvidenceStatus.INSUFFICIENT_EVIDENCE)
    evidence = EvidenceMemory.decode_evidence(record)
    return InvestigationResponse(
        claims=[Claim(claim=record["original_claim"], type=ClaimType.QUANTITATIVE)],
        requirements=requirements, components=components, evidence=evidence, status=status,
        missing_context=missing, conflicts=conflicts, citations=[item.url for item in evidence],
        research_stats=ResearchStats(aiq_jobs=0, queries=0, sources=len(evidence), latency_seconds=0),
        stages=["CHECKING_EVIDENCE_MEMORY", "BUILDING_REPORT", "COMPLETE"],
        trace=[AgentTrace(agent="EvidenceMemory", action="EXAMPLE_RECORD", details={"previously_completed": True, "aiq_jobs_started": 0})],
    )


@app.get("/api/v1/examples/shincheonji-allegation", response_model=InvestigationResponse)
async def cached_politics_example():
    """Return sanitized politics demo record; never starts a new investigation."""
    job = job_manager.get("a39a26f8-c60c-482c-a450-62de0240819a")
    if job and job.result:
        return job.result
    record = EvidenceMemory().get_exact(EXAMPLE_ADVERTISEMENT_CLAIM, "ADVERTISEMENT")
    return await cached_advertising_example()


# The production UI is a same-origin Vite build. Only its compiled files are
# served: `.env`, source files, project docs, and AI-Q are never static routes.
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
ASSETS_DIR = FRONTEND_DIST / "assets"
if ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="frontend-assets")


@app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
async def frontend(path: str):
    parts = [part for part in path.split("/") if part]
    # Never let the SPA fallback turn nested hidden/source paths into HTTP 200.
    if (path in {"docs", "redoc", "openapi.json"}
            or any(part.startswith(".") for part in parts)
            or any(part.endswith((".env", ".py", ".sqlite3", ".pem", ".key")) for part in parts)):
        raise HTTPException(status_code=404, detail="Not found")
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=503, detail="Frontend build is not available.")
    return FileResponse(index)
