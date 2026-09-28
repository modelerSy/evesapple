# EVE architecture

## MVP boundary

`React UI → FastAPI → Nemotron hosted chat API → typed Claim model → UI`

The API boundary is ready for the full workflow:

`INPUT → extraction → claim extraction → research planning → original source search → primary/supporting/challenging evidence → cross-validation → synthesis → EVE report`

## NVIDIA alignment

| NVIDIA capability | EVE use |
|---|---|
| Nemotron hosted API | low-temperature structured claim extraction and later evidence synthesis |
| `aiq-research` | deep-research orchestration for source discovery |
| `rag-blueprint` | ingest source documents and retrieve cited passages |
| `nemo-retriever` / `nemo-retriever-mcp` | retrieval and reranking layer |
| `nemotron-retrieval-recipes` | Nemotron-compatible retrieval patterns |
| `rag-eval` | retrieval/groundedness evaluation |
| OpenShell 0.1.1 | runtime-enforced Evidence Hunter sandbox: Landlock filesystem policy and AI-Q-only network rules |
| NemoClaw | not integrated or claimed for EVE; official smoke validation is blocked by OpenShell version compatibility |

EVE reports evidence status rather than a single truth score: `CONFIRMED`, `MISSING_CONTEXT`, `INSUFFICIENT_EVIDENCE`, `CONFLICTING_EVIDENCE`, `UNVERIFIED`.

## Runtime flow

`React (same origin) → FastAPI orchestrator → OpenShell Evidence Hunter sandbox → host.openshell.internal:8000 → AI-Q shallow_researcher → Tavily / hosted NVIDIA model`

The AI-Q backend remains loopback-only. The sandbox's `localhost` is not used
for host access; OpenShell's policy-controlled host-service route is used
instead. See [security.md](security.md) for the enforced scope and limits.
