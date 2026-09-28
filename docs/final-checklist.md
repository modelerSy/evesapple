# Submission checklist

## AUTOMATED / VERIFIED BY CODEX

- [x] Public demo root responds at `https://evesapple.kr`
- [x] Public `/about` responds at `https://evesapple.kr/about`
- [x] Cached example endpoint returns the actual stored `MISSING_CONTEXT` record with 0 AI-Q jobs and 5 sources
- [x] `/health` returns 200
- [x] `/docs`, `/redoc`, `/openapi.json`, `/.env`, and public source maps return 404
- [x] `eve-apple.service` is active and loopback-bound to `127.0.0.1:8100`
- [x] `cloudflared.service` is active
- [x] AI-Q remains loopback-only
- [x] README, submission text, demo script, architecture, security snapshot, and public `/about` are present
- [x] Working-tree/bundle secret audit completed without printing secret values
- [x] `.env` ignore rule exists and the current `.env` mode is 600

## MUST BE DONE BY USER

- [ ] Create or select the intended root Git repository before publishing
- [ ] Verify `git status`, `.gitignore`, and all files staged for the public repository
- [ ] Insert the final GitHub repository URL into `docs/submission.md` and README if desired
- [ ] Review the existing modified `aiq/deploy/compose/docker-compose.yaml` before any commit
- [ ] Review runtime credentials and rotate NVIDIA API key if required by the submission policy
- [ ] Review Tavily/API credentials
- [ ] Review Cloudflare tunnel token
- [ ] Record and review demo video
- [ ] Create submission PDF/Word material if required
- [ ] Submit Google Form/application before deadline

## DO NOT COMMIT UNLESS EXPLICITLY INTENDED

- [ ] `.env` and `aiq/deploy/.env`
- [ ] `.venv/`, `frontend/node_modules/`, `frontend/dist/`
- [ ] `data/eve_evidence.sqlite3` (runtime EvidenceMemory cache)
- [ ] local logs, temporary curl outputs, and model/download caches
