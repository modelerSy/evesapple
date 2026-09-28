# Final system state — submission snapshot

## Production

- Public URL: https://evesapple.kr
- Product explanation: https://evesapple.kr/about
- EVE service: enabled user systemd service, bound only to `127.0.0.1:8100`
- Public ingress: Cloudflare Tunnel
- AI-Q API and PostgreSQL: loopback-only

## Architecture and agents

`React → FastAPI → deterministic EVE Orchestrator → Lead Investigator / Evidence Memory / Evidence Hunter → Evidence Synthesizer → Evidence Judge → EVE Report`

- Lead Investigator: hosted Nemotron claim extraction, requirements, sufficiency check
- Evidence Hunter: AI-Q shallow research; at most two jobs per Fast Bite request
- Evidence Synthesizer: deterministic citation/evidence normalization
- Evidence Judge: hosted Nemotron component-level evaluation
- EVE Orchestrator: deterministic state machine, retry and stop budget

## NVIDIA technologies actually used

- NVIDIA Nemotron hosted API
- NVIDIA AI-Q / Agent Skills (`shallow_researcher`)
- NVIDIA OpenShell 0.1.1

NemoClaw is not active. Its installer required a different OpenShell version
than the validated 0.1.1 runtime; EVE intentionally did not downgrade the
security environment.

## OpenShell enforcement scope

Evidence Hunter AI-Q control-plane requests can use a disposable OpenShell
sandbox with no project `.env`, API keys, SSH material, or Docker socket. The
policy permits the required AI-Q job submit/status/report routes through the
OpenShell host-service route. This is not a claim that AI-Q's own hosted-model
or Tavily infrastructure runs inside the EVE sandbox.

Verified runtime outcomes: normal AI-Q research ALLOW; secret-shaped `.env`
fixture DENY; SSH-path fixture DENY; unauthorized egress DENY;
prompt-injection-shaped exfiltration DENY.

## Evidence Memory

EvidenceMemory stores canonical claims, requirements, normalized evidence,
verification results, and retrieval time in local SQLite. It reuses only
compatible claims and refuses changed critical numeric or temporal constraints.
For example, `4 weeks / 37%` does not match `12 weeks / 7%`.

The public cached demo record is the stored 4-week/37% advertising claim:
`MISSING_CONTEXT`, five source candidates, zero fresh AI-Q jobs, and no verified
direct component.

## Benchmarks

- Cold V0.2 investigation: 294.81 s
- Warm exact EvidenceMemory cache: 36.16 s
- Semantic-equivalent cache hit: 26.39 s
- OpenShell transport shallow job: 100.13 s
- Public cached E2E check: 64.42 s (includes live claim extraction before cache lookup)

## Known limitations

- Cold research latency remains material.
- Quality depends on public/retrievable primary evidence.
- Some claims remain inconclusive by design.
- Fast Bite does not automatically call Deep Bite.
- Root project Git repository has not been initialized in this workspace; do
  not publish runtime files until the intended repository and ignore rules are
  reviewed.
