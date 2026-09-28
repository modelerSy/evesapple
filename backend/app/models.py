from enum import Enum
from pydantic import BaseModel, Field

class Category(str, Enum):
    POLITICS = "POLITICS"
    ADVERTISEMENT = "ADVERTISEMENT"

class ClaimType(str, Enum):
    EXISTENCE = "existence"
    QUANTITATIVE = "quantitative"
    TEMPORAL = "temporal"
    ATTRIBUTION = "attribution"
    COMPARATIVE = "comparative"
    OTHER = "other"

class EvidenceStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    MISSING_CONTEXT = "MISSING_CONTEXT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    UNVERIFIED = "UNVERIFIED"

class ExtractRequest(BaseModel):
    category: Category
    content: str = Field(min_length=1, max_length=20000)
    source_url: str | None = None

class Claim(BaseModel):
    claim: str
    type: ClaimType
    verification_questions: list[str] = Field(default_factory=list)

class ComponentStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    CONFLICTING = "CONFLICTING"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class ClaimComponent(BaseModel):
    name: str
    expected: str
    status: ComponentStatus = ComponentStatus.UNVERIFIED
    evidence_ids: list[str] = Field(default_factory=list)
    direct_support: bool = False
    conflicts: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

class EvidenceRequirement(BaseModel):
    component: str
    expected: str = ""
    required: bool = True
    required_evidence: str
    preferred_source_types: list[str] = Field(default_factory=list)

class Evidence(BaseModel):
    evidence_id: str
    claim_id: str
    title: str
    url: str
    publisher: str | None = None
    published_at: str | None = None
    source_type: str
    stance: str = "NEUTRAL"
    excerpt: str = ""
    supports_what: str = ""
    limitations: list[str] = Field(default_factory=list)
    provenance: list[str] = Field(default_factory=list)

class InvestigationRequest(BaseModel):
    mode: Category
    content: str = Field(min_length=1, max_length=20000)
    image_data_urls: list[str] = Field(default_factory=list, max_length=5)
    research_depth: str = Field(default="fast", pattern="^(fast|deep)$")

class ResearchStats(BaseModel):
    aiq_jobs: int = 0
    queries: int = 0
    sources: int = 0
    early_stopped: bool = False
    latency_seconds: float = 0

class AgentTrace(BaseModel):
    agent: str
    action: str
    status: str = "completed"
    details: dict = Field(default_factory=dict)
    started_at: str | None = None
    duration_ms: int | None = None

class InvestigationResponse(BaseModel):
    claims: list[Claim] = Field(default_factory=list)
    components: list[ClaimComponent] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    status: EvidenceStatus
    missing_context: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    research_stats: ResearchStats
    stages: list[str] = Field(default_factory=list)
    trace: list[AgentTrace] = Field(default_factory=list)
    requirements: list[EvidenceRequirement] = Field(default_factory=list)

class InvestigationJob(BaseModel):
    investigation_id: str
    status: str
    created_at: str
    updated_at: str
    result: InvestigationResponse | None = None
    error: str | None = None

class ClaimExtractionResponse(BaseModel):
    original_content: str
    category: Category
    claims: list[Claim]
    model: str
