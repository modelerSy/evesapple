# EVE Agent Capabilities V0.2

These are application-level boundaries backed by the committed OpenShell policy
for EvidenceHunter. The other agent rows remain orchestration capabilities,
not separate sandboxes.

| Agent | NVIDIA inference | Evidence Memory | AI-Q research | Approved research network | Direct web | Agent invocation | Project secrets | Arbitrary filesystem |
|---|---|---|---|---|---|---|---|---|
| LeadInvestigator | ALLOW | READ | DENY | DENY | DENY | DENY | DENY | DENY |
| EvidenceHunter | DENY | write through orchestrator only | ALLOW | ALLOW | via AI-Q only | DENY | DENY | DENY |
| EvidenceSynthesizer | DENY | DENY | DENY | DENY | DENY | DENY | DENY | DENY |
| EvidenceJudge | ALLOW | compact evidence read | DENY | DENY | DENY | DENY | DENY | DENY |
| EVEOrchestrator | DENY | READ/WRITE | via agents only | via agents only | DENY | ALLOW | DENY | DENY |

LeadInvestigator performs Nemotron claim extraction and requirement planning.
EvidenceHunter is the only role that invokes local AI-Q
`shallow_researcher`, through a disposable OpenShell sandbox with no project
secrets and AI-Q-only egress. EvidenceSynthesizer deterministically compacts raw
research output. EvidenceJudge evaluates compact evidence but cannot search.
The deterministic Python orchestrator decides retry and stop actions.
