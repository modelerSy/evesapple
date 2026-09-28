"""Evidence-driven, deterministic hierarchical orchestration for EVE V0.2."""
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx

from .aiq_client import AIQError, run_shallow_research
from .evidence_memory import EvidenceMemory
from .nemotron_client import MissingNvidiaApiKey, NemotronResponseError, call_nemotron_json
from backend.app.models import (AgentTrace, Claim, ClaimComponent, ComponentStatus,
    Evidence, EvidenceRequirement, EvidenceStatus, InvestigationResponse, ResearchStats)

logger = logging.getLogger("eve.investigator")

REQUIREMENT_PROMPT = """You are EVE's Lead Investigator. For each factual claim, define only the evidence requirements needed to verify it. Split every compound claim into independently verifiable components; never use a generic component such as claim_1. For example, separate an entity, period, outcome, numeric effect, population, and measurement when each is asserted. Return JSON only: {{\"requirements\":[{{\"component\":string,\"expected\":string,\"required\":boolean,\"required_evidence\":string,\"preferred_source_types\":[string]}}]}}. Prefer PRIMARY_STUDY, TRIAL_REGISTRY, REGULATOR, OFFICIAL_STATISTICS, OFFICIAL_DOCUMENT where relevant. Category: {mode}. Claims: {claims}"""
JUDGE_PROMPT = """You are EVE's Evidence Judge. Evaluate each requirement only from the compact evidence objects provided. VERIFIED needs direct support for the expected value; UNVERIFIED is missing/indirect; CONFLICTING is credible direct disagreement. Return JSON only: {{\"results\":[{{\"component\":string,\"requirement\":string,\"status\":\"VERIFIED|UNVERIFIED|CONFLICTING|NOT_APPLICABLE\",\"direct_support\":boolean,\"evidence_ids\":[string],\"conflicts\":[string],\"limitations\":[string],\"confidence_reason\":string}}]}}."""

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _urls(report: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"https?://[^\s)\]>]+", report)))

def _source_type(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "pubmed" in host or "clinicaltrials.gov" in host:
        return "PRIMARY_STUDY"
    if any(item in host or item in url.lower() for item in (".gov", ".go.kr", "kosis", "kostat", "fda.gov")):
        return "REGULATOR_OR_OFFICIAL"
    if any(item in host for item in ("doi.org", "mdpi.com", "nature.com", "sciencedirect.com")):
        return "PUBLISHED_STUDY"
    return "SECONDARY"

class EvidenceSynthesizer:
    """Deterministic extraction; raw AI-Q prose is not passed to the Judge."""
    def normalize(self, report: str, start_index: int) -> list[Evidence]:
        evidence = []
        for offset, url in enumerate(_urls(report), start_index):
            host = urlparse(url).netloc.lower()
            line = next((item.strip(" -*#") for item in report.splitlines() if url in item), host)
            lowered = line.lower()
            limitations = []
            if any(token in lowered for token in ("no significant", "limited", "unclear", "not identified", "marketing")):
                limitations.append(line[:280])
            stance = "CHALLENGING" if any(token in lowered for token in ("no significant", "contradict", "challenge", "unsubstantiated")) else "NEUTRAL"
            evidence.append(Evidence(evidence_id=f"ev_{offset:03d}", claim_id="investigation", title=line[:240], url=url,
                publisher=host, source_type=_source_type(url), stance=stance, excerpt=line[:480],
                supports_what="Candidate evidence; Judge determines direct component coverage.", limitations=limitations, provenance=[url]))
        return evidence

    def compact(self, evidence: list[Evidence], limit: int = 8) -> list[dict]:
        priority = {"PRIMARY_STUDY": 0, "REGULATOR_OR_OFFICIAL": 1, "PUBLISHED_STUDY": 2, "SECONDARY": 3}
        selected = sorted(evidence, key=lambda item: priority.get(item.source_type, 9))[:limit]
        return [{"evidence_id": item.evidence_id, "title": item.title, "url": item.url,
                 "source_type": item.source_type, "stance": item.stance, "excerpt": item.excerpt,
                 "limitations": item.limitations} for item in selected]

@dataclass
class InvestigationState:
    investigation_id: str
    mode: str
    original_content: str
    image_data_urls: list[str] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    components: list[ClaimComponent] = field(default_factory=list)
    requirements: list[EvidenceRequirement] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    missing_components: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 2
    aiq_jobs_used: int = 0
    max_aiq_jobs: int = 2
    next_action: str = "ANALYZE_CLAIM"
    final_status: EvidenceStatus = EvidenceStatus.INSUFFICIENT_EVIDENCE
    trace: list[AgentTrace] = field(default_factory=list)
    stages: list[str] = field(default_factory=list)
    judge_result: dict = field(default_factory=dict)
    cache_hit: bool = False
    started: float = field(default_factory=time.perf_counter)

    def trace_action(self, agent: str, action: str, started: float, status: str = "completed", **details) -> None:
        elapsed = time.perf_counter() - started
        self.trace.append(AgentTrace(agent=agent, action=action, status=status, details=details,
            started_at=(datetime.now(timezone.utc) - timedelta(seconds=elapsed)).isoformat(), duration_ms=round(elapsed * 1000)))

async def _nemotron(state: InvestigationState, purpose: str, prompt: str, *, budget: int, max_tokens: int, category: str = "", enable_thinking: bool = False, image_data_urls: list[str] | None = None) -> dict:
    # Hosted inference can occasionally return a transient malformed/provider
    # failure. Retry once before declaring the whole investigation partial.
    for attempt in range(2):
        started = time.perf_counter()
        try:
            data, model = await call_nemotron_json(prompt, budget=budget, max_tokens=max_tokens, category=category, enable_thinking=enable_thinking, image_data_urls=image_data_urls)
            state.trace_action("Nemotron", purpose, started, model=model, reasoning_budget=budget if enable_thinking else 0, input_chars=len(prompt), max_tokens=max_tokens, success=True, attempt=attempt + 1)
            return data
        except MissingNvidiaApiKey:
            raise
        except (httpx.TimeoutException, NemotronResponseError, RuntimeError, ValueError) as exc:
            retrying = attempt == 0
            state.trace_action("Nemotron", purpose, started, status="retrying" if retrying else "failed", reasoning_budget=budget if enable_thinking else 0, input_chars=len(prompt), max_tokens=max_tokens, success=False, attempt=attempt + 1, error_type=type(exc).__name__)
            logger.warning("nemotron_call_failed purpose=%s attempt=%s error_type=%s", purpose, attempt + 1, type(exc).__name__)
            if not retrying:
                raise

class LeadInvestigator:
    async def extract_claims(self, state: InvestigationState) -> None:
        started = time.perf_counter(); state.stages.append("CLAIM_EXTRACTION")
        extracted = await _nemotron(state, "CLAIM_EXTRACTION", state.original_content, budget=1024, max_tokens=1800, category=state.mode, enable_thinking=True, image_data_urls=getattr(state, "image_data_urls", []))
        state.claims = [Claim(**item) for item in extracted.get("claims", [])]
        state.trace_action("LeadInvestigator", "ANALYZE_CLAIM", started, claims=len(state.claims))

    async def plan_requirements(self, state: InvestigationState) -> None:
        started = time.perf_counter(); state.stages += ["COMPONENT_DECOMPOSITION", "PLAN_REQUIREMENTS"]
        claims = json.dumps([item.claim for item in state.claims], ensure_ascii=False)
        planned = await _nemotron(state, "PLAN_REQUIREMENTS", REQUIREMENT_PROMPT.format(mode=state.mode, claims=claims), budget=1024, max_tokens=1800)
        state.requirements = [EvidenceRequirement(**item) for item in planned.get("requirements", [])]
        state.components = [ClaimComponent(name=item.component, expected=item.expected) for item in state.requirements]
        state.trace_action("LeadInvestigator", "PLAN_REQUIREMENTS", started, claims=len(state.claims), requirements=len(state.requirements))

    def check_sufficiency(self, state: InvestigationState) -> bool:
        required = {item.component for item in state.requirements if item.required}
        verdicts = {item.name: item.status for item in state.components}
        return bool(required) and all(verdicts.get(item) == ComponentStatus.VERIFIED for item in required) and not state.conflicts

class EvidenceHunter:
    async def research(self, state: InvestigationState, targeted: bool) -> None:
        started = time.perf_counter(); state.iteration += 1
        requirements = [item for item in state.requirements if item.required and (not targeted or item.component in state.missing_components or item.component in state.conflicts)]
        focus = "\n".join(f"- {item.component}: expected {item.expected}; {item.required_evidence}" for item in requirements)
        if targeted:
            action, stage = "RESEARCH_MISSING_EVIDENCE", "SEARCHING_MISSING_EVIDENCE"
            query = f"Targeted check for unresolved claims ({state.mode}): {state.original_content}\nFocus components:\n{focus}\nProvide compact citations and direct findings or counter-evidence."
        else:
            action, stage = "RESEARCH_EVIDENCE", "SEARCHING_PRIMARY_SOURCE"
            query = f"Verify factual claims ({state.mode}): {state.original_content}\nKey components:\n{focus}\nProvide compact primary evidence, direct support, or counter-evidence."
        state.stages.append(stage)
        try:
            result = await run_shallow_research(query)
        except AIQError as exc:
            # A submitted shallow-research job can fail during AI-Q citation
            # integrity checks. Count that attempt and spend the remaining
            # Fast Bite job budget on one identical retry instead of failing
            # the entire investigation immediately.
            state.aiq_jobs_used += 1
            state.trace_action("EvidenceHunter", action, started, status="partial", aiq_job=state.aiq_jobs_used,
                query_chars=len(query), reason="research job failed", error_type=type(exc).__name__)
            logger.warning("research_job_failed stage=%s attempt=%s error_type=%s", stage, state.aiq_jobs_used, type(exc).__name__)
            if state.aiq_jobs_used < state.max_aiq_jobs:
                return await self.research(state, targeted=targeted)
            raise
        state.aiq_jobs_used += 1
        added = EvidenceSynthesizer().normalize(result.get("report", ""), len(state.evidence) + 1)
        state.evidence.extend(added)
        state.trace_action("EvidenceHunter", action, started, aiq_job=state.aiq_jobs_used, query_chars=len(query), sources_added=len(added), job_latency_seconds=result.get("latency_seconds"), timed_out=result.get("timed_out", False), execution_boundary=result.get("execution_boundary", "direct_local"))

class EvidenceJudge:
    async def judge(self, state: InvestigationState) -> None:
        started = time.perf_counter(); state.stages += ["SYNTHESIZING_EVIDENCE", "EVALUATING_EVIDENCE"]
        synthesizer = EvidenceSynthesizer(); compact = synthesizer.compact(state.evidence)
        state.trace_action("EvidenceSynthesizer", "NORMALIZE_EVIDENCE", started, raw_evidence=len(state.evidence), compact_evidence=len(compact))
        prompt = JUDGE_PROMPT + "\nCLAIM=" + state.original_content + "\nREQUIREMENTS=" + json.dumps([item.model_dump() for item in state.requirements], ensure_ascii=False) + "\nEVIDENCE=" + json.dumps(compact, ensure_ascii=False)
        result = await _nemotron(state, "JUDGE_EVIDENCE", prompt, budget=1024, max_tokens=1600)
        state.judge_result = result
        by_component = {item.get("component"): item for item in result.get("results", [])}
        for component in state.components:
            match = by_component.get(component.name)
            if match:
                component.status = ComponentStatus(match.get("status", component.status))
                component.direct_support = bool(match.get("direct_support", False))
                component.evidence_ids = match.get("evidence_ids", [])
                component.conflicts = match.get("conflicts", [])
                component.limitations = match.get("limitations", [])
        required = {item.component for item in state.requirements if item.required}
        state.missing_components = [item.name for item in state.components if item.name in required and item.status == ComponentStatus.UNVERIFIED]
        state.conflicts = [item.name for item in state.components if item.name in required and item.status == ComponentStatus.CONFLICTING]
        state.trace_action("EvidenceJudge", "JUDGE_EVIDENCE", started, missing_components=state.missing_components, conflicts=state.conflicts, compact_evidence=len(compact))

class EVEOrchestrator:
    def __init__(self, request):
        self.state = InvestigationState(f"eve-{int(time.time() * 1000)}", request.mode.value, request.content, image_data_urls=request.image_data_urls)
        self.lead, self.hunter, self.judge, self.memory = LeadInvestigator(), EvidenceHunter(), EvidenceJudge(), EvidenceMemory()

    def _apply_cached_verification(self, state: InvestigationState, record: dict) -> None:
        verdict = json.loads(record["verification_json"])
        by_component = {item.get("component"): item for item in verdict.get("results", [])}
        for component in state.components:
            match = by_component.get(component.name)
            if match:
                component.status = ComponentStatus(match.get("status", component.status)); component.direct_support = bool(match.get("direct_support", False)); component.evidence_ids = match.get("evidence_ids", []); component.conflicts = match.get("conflicts", []); component.limitations = match.get("limitations", [])
        required = {item.component for item in state.requirements if item.required}
        state.missing_components = [item.name for item in state.components if item.name in required and item.status == ComponentStatus.UNVERIFIED]
        state.conflicts = [item.name for item in state.components if item.name in required and item.status == ComponentStatus.CONFLICTING]

    async def run(self) -> InvestigationResponse:
        state = self.state
        try:
            await self.lead.extract_claims(state)
            check = time.perf_counter(); state.stages.append("CHECKING_EVIDENCE_MEMORY")
            record = self.memory.lookup(state.original_content, state.mode, [])
            state.trace_action("EvidenceMemory", "CACHE_HIT" if record else "CACHE_MISS", check, match_score=record.get("match_score") if record else None)
            if record:
                state.cache_hit = True; state.requirements = [EvidenceRequirement(**item) for item in json.loads(record["requirements_json"])]
                state.components = [ClaimComponent(name=item.component, expected=item.expected) for item in state.requirements]
                state.evidence = self.memory.decode_evidence(record); self._apply_cached_verification(state, record)
                state.trace_action("LeadInvestigator", "CHECK_SUFFICIENCY", time.perf_counter(), cached=True, sufficient=self.lead.check_sufficiency(state))
            else:
                await self.lead.plan_requirements(state)
                state.stages.append("RESEARCH_PLANNING"); await self.hunter.research(state, targeted=False); await self.judge.judge(state)
                state.trace_action("LeadInvestigator", "CHECK_SUFFICIENCY", time.perf_counter(), cached=False, sufficient=self.lead.check_sufficiency(state))
            if not self.lead.check_sufficiency(state) and state.aiq_jobs_used < state.max_aiq_jobs and not state.cache_hit:
                state.trace.append(AgentTrace(agent="LeadInvestigator", action="RESEARCH_MISSING_EVIDENCE", details={"missing_components": state.missing_components, "conflicts": state.conflicts, "reason": "required coverage incomplete"}, started_at=_now(), duration_ms=0))
                await self.hunter.research(state, targeted=True); await self.judge.judge(state)
            if self.lead.check_sufficiency(state):
                state.final_status, state.next_action = EvidenceStatus.CONFIRMED, "STOP"
            else:
                state.final_status = EvidenceStatus.CONFLICTING_EVIDENCE if state.conflicts else (EvidenceStatus.MISSING_CONTEXT if state.missing_components else EvidenceStatus.INSUFFICIENT_EVIDENCE)
                state.next_action = "BUILD_REPORT"
            try:
                # Reuse only cleanly completed investigations. A completed
                # MISSING_CONTEXT report is valid evidence; a partial service
                # failure is not.
                self.memory.store(state.original_content, state.mode, state.requirements, state.evidence, state.judge_result, cacheable=True)
            except Exception as exc:
                # Evidence Memory is an optimization; persistence must not
                # discard an otherwise usable investigation report.
                state.trace.append(AgentTrace(agent="EvidenceMemory", action="STORE", status="partial", details={"reason": "memory persistence unavailable", "error_type": type(exc).__name__}, started_at=_now(), duration_ms=0))
        except MissingNvidiaApiKey:
            raise
        except (AIQError, httpx.TimeoutException, TimeoutError, NemotronResponseError, RuntimeError, ValueError) as exc:
            state.final_status, state.next_action = EvidenceStatus.INSUFFICIENT_EVIDENCE, "BUILD_REPORT"
            if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
                reason = "agent timeout"
            elif isinstance(exc, AIQError):
                reason = "research service unavailable"
            elif isinstance(exc, NemotronResponseError):
                reason = "agent returned an invalid response"
            else:
                reason = "agent service unavailable"
            logger.warning("investigation_partial stage=%s error_type=%s", state.stages[-1] if state.stages else "START", type(exc).__name__)
            state.trace.append(AgentTrace(agent="EVEOrchestrator", action="BUILD_REPORT", status="partial", details={"reason": reason, "error_type": type(exc).__name__}, started_at=_now(), duration_ms=0))
        state.stages += ["BUILDING_REPORT", "COMPLETE"]
        state.trace.append(AgentTrace(agent="EVEOrchestrator", action="BUILD_REPORT", details={"final_status": state.final_status.value, "cache_hit": state.cache_hit}, started_at=_now(), duration_ms=0))
        return InvestigationResponse(claims=state.claims, components=state.components, requirements=state.requirements, evidence=state.evidence, status=state.final_status, missing_context=state.missing_components, conflicts=state.conflicts, citations=[item.url for item in state.evidence], stages=state.stages, trace=state.trace, research_stats=ResearchStats(aiq_jobs=state.aiq_jobs_used, queries=state.aiq_jobs_used, sources=len(state.evidence), early_stopped=state.next_action == "STOP", latency_seconds=time.perf_counter() - state.started))

async def investigate_fast(request) -> InvestigationResponse:
    return await EVEOrchestrator(request).run()
