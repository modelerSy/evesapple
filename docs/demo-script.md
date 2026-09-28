# Eve's Apple demo script

The reliable live path is **View cached example investigation**. Say clearly:
“This is a previously completed Evidence Memory record; it starts no new
Nemotron or AI-Q job during the demo.”

## A. 90-second version

1. **0:00–0:12 — Problem**
   “Misleading claims are often not entirely false. A number may exist, but the product, population, duration, or original study context is missing.”

2. **0:12–0:25 — Input**
   Select `ADVERTISEMENT` and show: “Using this product for 4 weeks improves skin elasticity by 37%.” Click **View cached example investigation**.

3. **0:25–0:40 — Evidence requirements**
   “EVE does not jump to TRUE/FALSE. It asks what direct evidence would connect the product, four-week period, skin-elasticity outcome, and 37% value.”

4. **0:40–0:55 — Result**
   “This completed record is `MISSING_CONTEXT`: it retains five source candidates, but no direct component met EVE’s verification threshold. Relevant sources are not automatically proof of the exact marketing claim.”

5. **0:55–1:10 — Agentic loop**
   Open `/about`. “On a cache miss, Nemotron creates requirements; AI-Q researches primary, supporting, and limiting sources; Nemotron judges coverage; the deterministic orchestrator can perform one targeted retry, then stops.”

6. **1:10–1:25 — Security**
   “Evidence Hunter’s AI-Q control-plane requests run through OpenShell. We verified allow for AI-Q research and deny for secret-shaped file reads, SSH-path reads, unauthorized egress, and prompt-injection-shaped exfiltration.”

7. **1:25–1:30 — Close**
   “EVE doesn’t tell you what to believe. EVE shows you what the evidence says. Take a bite. Know what’s real.”

## B. 2-minute version

1. **0:00–0:20 — Problem**
   “Political and advertising content often loses context between an original source and a viral claim. A statistic can be real but not generalizable; a study can be real but not test the advertised product.”

2. **0:20–0:35 — Product principle**
   “EVE is evidence-first. It presents status, sources, limitations, and missing context rather than a generic credibility score or a forced TRUE/FALSE verdict.”

3. **0:35–0:55 — Cached example**
   On the landing page click **View cached example investigation**. “This is a real previously completed Evidence Memory record. No fresh model or research job is started for this demo.” Point out `MISSING_CONTEXT`, `0 AI-Q job(s)`, five source candidates, and the unverified core quantitative requirement.

4. **0:55–1:15 — Requirements and evidence**
   “The stored requirement asks for direct quantitative evidence tying together product identity, a four-week intervention, skin-elasticity measurement, and a 37% claim. Candidate sources are separated from direct supporting and challenging evidence.”

5. **1:15–1:35 — Agent architecture**
   Open `/about`. “Lead Investigator and Evidence Judge use NVIDIA Nemotron. AI-Q performs autonomous research. Evidence Synthesizer is deterministic normalization. The Python EVE Orchestrator owns state transitions, the two-job Fast Bite budget, and the stop/retry decision.”

6. **1:35–1:50 — Adaptive research**
   “On a cache miss, EVE performs a first shallow research pass. If key requirements remain uncovered, it generates a targeted query for only those gaps and can run one more AI-Q pass. It then reports the evidence state rather than searching forever.”

7. **1:50–2:00 — Runtime security and close**
   “OpenShell is the runtime boundary for Evidence Hunter. Its policy permits only the needed AI-Q routes and denies project-secret, SSH-path, and arbitrary-egress access. EVE doesn’t tell you what to believe; it shows you what the evidence says.”

## What to say if a judge asks

| Question | Concise answer |
|---|---|
| Why is this agentic? | EVE decomposes claims, plans evidence requirements, invokes research, evaluates coverage, decides whether a targeted retry is useful, and stops under a deterministic budget. |
| Why not just ChatGPT or search? | Search gives links and a chat answer gives prose. EVE tracks whether each required part of a claim has direct evidence, provenance, limitations, and missing context. |
| What does Nemotron do? | Hosted Nemotron performs structured claim extraction, requirement planning, and evidence judgment. |
| What does AI-Q do? | AI-Q `shallow_researcher` performs autonomous source research for primary, supporting, and limiting evidence candidates. |
| What does OpenShell actually protect? | It enforces the EVE Evidence Hunter execution boundary: the disposable sandbox has no project secrets and only the permitted AI-Q network routes. It does not claim to sandbox AI-Q's own hosted-model or Tavily infrastructure. |
| Why no TRUE/FALSE? | A claim can be partly supported while the product identity, population, duration, or measurement context is still missing. A binary label would hide that uncertainty. |
| Why is NemoClaw not active? | Its installer required an OpenShell version incompatible with the validated OpenShell 0.1.1 runtime. We avoided downgrading a working security boundary. |
| What happens on cache hit? | EVE checks critical constraints, retrieves a compatible Evidence Memory record, starts no AI-Q job, and transparently marks research stages as not needed. |
| What happens when evidence is insufficient? | The report remains MISSING_CONTEXT or INSUFFICIENT_EVIDENCE. On a cache miss, Fast Bite may issue one targeted retry before it stops. |
| Biggest current limitation? | Cold research latency and availability of retrievable primary evidence. EVE cannot create missing public evidence. |
