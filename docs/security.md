# EVE runtime security boundary

## Verified result at a glance

| Security test | Result |
|---|---|
| Normal AI-Q research | **ALLOW** |
| Project `.env` access | **DENY** |
| SSH path access | **DENY** |
| Unauthorized egress | **DENY** |
| Prompt-injection exfiltration | **DENY** |

These are OpenShell runtime-policy outcomes, not application prompt refusals.

## Scope and threat model

EVE accepts untrusted political and advertising text. The Evidence Hunter may
use that text to request research, so it must not gain access to project
secrets, user SSH data, Docker, arbitrary host files, or arbitrary egress.

OpenShell is used as the runtime enforcement boundary for EVE's autonomous
Evidence Hunter. Each AI-Q request uses a disposable OpenShell sandbox. The
sandbox receives no project `.env`, NVIDIA key, Tavily key, SSH material, or
Docker socket. It can invoke only `/usr/bin/curl`, only to the local AI-Q
service through `host.openshell.internal:8000`, and only on the three
job-submit/status/report routes required by Fast Bite.

AI-Q remains the existing backend-only service bound to `127.0.0.1:8000`.
`host.openshell.internal` is the OpenShell gateway's host-service route; it is
not sandbox localhost, and no host-network mode or public AI-Q binding is
enabled. AI-Q core was not modified.

This boundary protects the EVE Hunter's filesystem and its requests to AI-Q.
It does **not** claim to sandbox AI-Q's independently running internal Tavily
or hosted-model calls. A future AI-Q/OpenShell adapter must use the exact
certified AI-Q/OpenShell compatibility pair before that broader claim can be
made.

## Effective least-privilege policy

The committed policy is [eve-evidence-hunter-policy.yaml](../security/openshell/eve-evidence-hunter-policy.yaml).

| Capability | Decision | Enforcement |
|---|---|---|
| EVE Hunter process | ALLOW as UID/GID 10001 | OpenShell process policy |
| Minimal executable/runtime paths | ALLOW | Landlock read-only paths |
| `/tmp` | ALLOW write | Landlock read-write path |
| Project `.env`, real `$HOME/.ssh`, Docker socket, unrelated files | DENY | not mounted; Landlock allow-list |
| AI-Q job submit/status/report | ALLOW | `curl` + exact host/port/path REST rules |
| Other AI-Q paths, direct loopback, public internet | DENY | OpenShell L7/network policy |
| Hosted NVIDIA/Tavily credentials | DENY to sandbox | no provider or environment secret is attached |

`landlock.compatibility: hard_requirement` causes sandbox startup to fail if
the kernel cannot enforce the file rules. The custom image contains only
harmless `.env` and SSH-shaped fixtures so denial can be demonstrated without
copying real secrets into a test image.

## Runtime validation (2026-09-28)

OpenShell CLI/gateway: `0.1.1`, gateway `openshell`, mTLS authenticated,
`systemctl --user openshell-gateway` active. Test image:
`eve-openshell-evidence-hunter:0.1`; policy admission was accepted with
hard-Landlock and the sandbox logs recorded `Isolation boundary enforcement
confirmed`.

| Test | Command (sanitized) | OpenShell decision | Result |
|---|---|---|---|
| 1. Normal research | sandbox `curl POST /v1/jobs/async/submit`, then poll/report | `HTTP:POST/GET ALLOWED`, policy `aiq_local_host` | PASS — AI-Q `shallow_researcher` job succeeded and returned cited report |
| 2. Project `.env` | `cat /home/sangyun/Desktop/Eve/.env` | host path absent because it is not mounted; matching image `.env` fixture produced `Permission denied` | PASS — no real secret was available; fixture was Landlock-denied |
| 3. SSH | `cat /home/sangyun/.ssh/id_ed25519` | `Permission denied` on harmless image SSH fixture | PASS — host SSH directory is not mounted |
| 4. Unapproved egress | `curl https://example.com/` | `NET:OPEN DENIED`, `transparent_tcp_policy_denied` | PASS |
| 5. Prompt-injection simulation | untrusted text requested `.env` read and external API-key send; sanctioned AI-Q job-status read ran first | sanctioned job-status `HTTP:GET ALLOWED`; fixture read denied; `example.com` egress denied | PASS — runtime control, not an LLM refusal |

The injection test deliberately invoked the attempted file and egress actions
as a runtime negative control. It proves the policy blocks them even when an
application does not refuse the request. It does not assert that an LLM is
incapable of generating malicious text.

## NemoClaw status

NemoClaw is **not validated yet**. Its current installer required an
OpenShell release no newer than `0.0.116`, while the active official packaged
gateway is `0.1.1`. The installer stopped on that version mismatch; no system
OpenShell downgrade or removal was performed. The installer-created local
0.0.116 binaries were moved to a recovery directory so `/usr/bin/openshell`
continues to resolve to 0.1.1. A user-local Node 22.23.3 is available through
nvm; the system Node 20 was not changed.

Accurate status wording:

- NemoClaw: **Blocked — official secure-agent stack not yet validated because of the documented version mismatch.**
- OpenShell: **Used as the runtime enforcement boundary for EVE's autonomous Evidence Hunter.**
