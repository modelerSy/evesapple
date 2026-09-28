# Eve's Apple

## EVE — Evidence Verification Engine

### Take a bite. Know what's real.

EVE investigates verifiable claims in political and advertising content. It
does not decide what a person should believe. It shows what evidence was
found, what directly supports a claim, what limits it, and what remains
unverified.

## 1. Problem

Online claims are often misleading through omission rather than being wholly
false: a number can lack context, an underlying study can test a different
product or population, or secondary sources can repeat a result that is hard
to trace to original evidence. A generic credibility score hides those
distinctions.

## 2. What EVE does

1. Accepts political or advertising text.
2. Uses Nemotron to extract factual claims and evidence requirements.
3. Checks conservative Evidence Memory for compatible prior work.
4. On a cache miss, uses AI-Q research for primary, supporting, and limiting
   evidence.
5. Normalizes citations and asks Nemotron to judge direct component coverage.
6. Performs at most one targeted follow-up research pass in Fast Bite.
7. Returns `CONFIRMED`, `MISSING_CONTEXT`, `INSUFFICIENT_EVIDENCE`,
   `CONFLICTING_EVIDENCE`, or `UNVERIFIED` — never a forced TRUE/FALSE label.

## 3. Why EVE is agentic

EVE is not a single model response. The deterministic Python orchestrator
coordinates specialized roles and controls the research budget:

```text
User
  ↓
EVE Orchestrator
  ↓
Lead Investigator (Nemotron) → Evidence Requirements
  ↓
Evidence Memory
  ├─ compatible record → Evidence Report
  └─ cache miss
       ↓
Evidence Hunter → OpenShell runtime boundary → AI-Q Research Agent
       ↓
Primary + supporting + challenging source candidates
       ↓
Evidence Synthesizer → Evidence Judge (Nemotron)
       ↓
Lead Investigator sufficiency decision
  ├─ sufficient → STOP
  └─ incomplete → one targeted retry at most
       ↓
EVE Report
```

The system decomposes claims, selects evidence targets, evaluates coverage,
detects missing evidence, decides whether to retry, and stops under an
explicit budget.

## 4. NVIDIA technologies actually used

| Technology | Running EVE use |
|---|---|
| NVIDIA Nemotron hosted API | claim extraction, evidence requirement planning, evidence judgment, sufficiency reasoning |
| NVIDIA AI-Q / Agent Skills | `shallow_researcher` source discovery and research workflow |
| NVIDIA OpenShell | least-privilege runtime boundary for Evidence Hunter AI-Q control-plane requests |

NemoClaw is **not** an active EVE runtime technology. It was evaluated, but
its current installer required an OpenShell version incompatible with the
validated EVE OpenShell 0.1.1 environment. EVE intentionally avoids a runtime
downgrade and uses OpenShell directly.

## 5. Secure autonomous research

Evidence Hunter runs through a disposable OpenShell sandbox when
`EVE_OPENSHELL_ENABLED=true`. The policy uses hard Landlock enforcement and
allows only the AI-Q job submit/status/report routes through the official
host-service path. It does not pass the project `.env`, API keys, SSH files,
or Docker socket into the sandbox.

Runtime tests confirmed:

| Test | Result |
|---|---|
| Normal AI-Q research | ALLOW |
| Project `.env` fixture | DENY |
| SSH-path fixture | DENY |
| Unauthorized network egress | DENY |
| Prompt-injection-shaped exfiltration attempt | DENY |

OpenShell protects the EVE Evidence Hunter execution boundary. It does not
claim to sandbox AI-Q's independently operated hosted-model or Tavily
infrastructure. Full evidence is in [docs/security.md](docs/security.md).

## 6. Evidence model

Each claim is evaluated as independently verifiable requirements, with
provenance and limitations preserved. A cited URL alone is not treated as
direct verification. This is why a report may legitimately say
`MISSING_CONTEXT` even when it contains relevant sources.

## 7. Demo

Open the production app and use **View cached example investigation**. It
loads the actual stored result for:

> “Using this product for 4 weeks improves skin elasticity by 37%.”

The record is clearly marked as previously completed and starts no new
Nemotron or AI-Q job. Its stored result is `MISSING_CONTEXT`, with five source
candidates and no verified direct component.

Live Demo: [https://evesapple.kr](https://evesapple.kr)

How EVE Works: [https://evesapple.kr/about](https://evesapple.kr/about)

Repository: [https://github.com/modelerSy/evesapple](https://github.com/modelerSy/evesapple)

## 8. Running locally

```bash
cp .env.example .env
# Set NVIDIA_API_KEY and TAVILY_API_KEY locally; do not commit .env.

python -m pip install -r backend/requirements.txt
cd frontend && npm install && npm run build && cd ..

APP_ENV=development python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8100
```

For a development frontend, run `npm run dev` in `frontend/`. The FastAPI
service exposes `POST /api/v1/investigate` and serves the production Vite build
same-origin from `frontend/dist`.

## 9. Production deployment

The deployed app is bound only to `127.0.0.1:8100` and is served publicly
through Cloudflare Tunnel at [https://evesapple.kr](https://evesapple.kr).
AI-Q and PostgreSQL remain localhost-only. Production disables `/docs`,
`/redoc`, and `/openapi.json`.

The enabled user service is defined in
[deploy/eve-apple.service](deploy/eve-apple.service).

## 10. Current limitations

- Cold investigations can take several minutes.
- Quality is limited by publicly available and retrievable evidence.
- Some claims cannot be conclusively verified.
- The V0.2 Evidence Memory matcher is deliberately conservative and does not
  reuse evidence when critical numerical or temporal constraints differ.
- Deep Bite remains an explicit separate path; Fast Bite does not invoke it
  automatically.

## 11. Hackathon scope

This text-first MVP focuses on evidence-aware investigation before social login,
video download/analysis, large local model deployment, production
authentication, or broad retrieval infrastructure. It preserves uncertainty as
a product feature.

> EVE doesn't tell you what to believe. EVE shows you what the evidence says.
