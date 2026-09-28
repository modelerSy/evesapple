# Hackathon demo outline

1. Select `ADVERTISEMENT` or `POLITICS` and paste a claim.
2. Show Nemotron extracting atomic factual claims and evidence requirements.
3. Show the deterministic Fast Bite state trace: Claim Analyst → Evidence
   Hunter → Evidence Judge → targeted retry or stop.
4. Show evidence status rather than a forced TRUE/FALSE result: `CONFIRMED`,
   `MISSING_CONTEXT`, `INSUFFICIENT_EVIDENCE`, or `CONFLICTING_EVIDENCE`.
5. Open the OpenShell audit: one disposable Evidence Hunter sandbox can call
   only local AI-Q; secret-shaped fixture reads and unapproved internet egress
   are runtime-denied.
6. Explain the difference between Fast Bite (at most two shallow AI-Q jobs)
   and user-selected Deep Bite (never auto-invoked).

## Accurate NVIDIA technology statement

- Hosted NVIDIA Nemotron performs structured Claim Analyst and Evidence Judge
  inference.
- NVIDIA AI-Q `shallow_researcher` performs source research with the existing
  Tavily + hosted-model backend.
- OpenShell 0.1.1 enforces the EVE Evidence Hunter's least-privilege runtime
  boundary.
- NemoClaw is not presented as part of EVE: its official installation smoke
  test remains blocked by the current OpenShell version compatibility mismatch.
