# Change management — GitHub → Vercel / Railway

**Status:** Working description of the **actual** production path (readiness documentation).  
**Policy:** [policies/P05_change_management_policy.md](./policies/P05_change_management_policy.md) (DRAFT — not approved).  
**Owner:** Matt Justice (Engineering owner)  
**Last updated:** 2026-07-26

Branch protection on `main` and MFA on GitHub/Vercel/Railway are **confirmed live** (2026-07-26). This document is readiness evidence — **not** a claim of SOC 2 certification.

---

## Overview

| Surface | Host | Source |
|---------|------|--------|
| Customer web app (Next.js) | **Vercel** | GitHub repo → `frontend` |
| API (FastAPI / Python) | **Railway** | GitHub repo → `backend` |
| Datastore | **Neon** (Postgres) | Migrations / load scripts; not “deployed” like app code |
| Source of truth for code | **GitHub** | Branches + pull requests → `main` |

Production domains in use include `smpl-ai.com` and the Vercel project hostname (e.g. `smpl-financial-intelligence.vercel.app`). API example hostname pattern: Railway service such as `sfi-api-production` (`*.up.railway.app`).

---

## Standard path (happy path)

```text
Feature branch → Pull request on GitHub → Review → Merge to main
        → Vercel builds/deploys frontend
        → Railway builds/deploys API
        → Smoke test (health, login, critical routes)
```

1. **Develop** on a feature branch in GitHub.
2. **Open a PR** against `main`. Address review comments.
3. **Merge** to `main` (control live: GitHub branch ruleset — required PR before merge; solo-friendly, approvals may be 0 — **confirmed 2026-07-26**).
4. **Frontend:** Vercel project (root directory `frontend`) builds and deploys production.
5. **API:** Railway service (root directory `backend`) builds and deploys production.
6. **Verify:** API `/health`, magic-link login, critical `/app` routes; board/export paths if touched.
7. **Rollback:** Redeploy previous deployment in Vercel and/or Railway if needed.

Related ops docs (implementation detail): `docs/DEPLOYMENT.md`, `docs/GO_LIVE_PROD_DEPLOY.md`, `docs/VERCEL_AUTH_DEPLOY.md`.

---

## Who can promote

| Action | Who (current) | Notes |
|--------|---------------|-------|
| Merge to `main` | Matt Justice (+ any future reviewers) | Branch ruleset: required PR before merge — **Y** 2026-07-26 |
| Deploy / promote Vercel production | Matt Justice | Team admin; MFA **Y** 2026-07-26 |
| Deploy / promote Railway production | Matt Justice | Project access; MFA **Y** 2026-07-26 |
| Change production env vars / secrets | Matt Justice | Vercel + Railway consoles only |
| Neon schema / warehouse load | Matt Justice | Prefer reviewed migrations; load scripts documented |

---

## Secrets & configuration

| Secret location | Used for |
|-----------------|----------|
| Vercel env | Frontend / Auth.js / `SFI_BACKEND_URL` / billing keys as applicable |
| Railway env | `DATABASE_URL`, `ANTHROPIC_API_KEY`, CORS, internal API keys |
| Neon | Connection strings (held in env stores, not git) |
| Git | **Must not** contain production secrets or customer dumps |

Claude / Anthropic keys: **Railway only** — never in browser or static board HTML.

---

## Database & data changes

- Schema: Alembic / migration PRs preferred; apply with production `DATABASE_URL` under controlled process.
- Warehouse loads / white-glove POC data: privileged ops path owned by Matt; treat as Confidential ([P06](./policies/P06_data_classification_and_handling.md)).
- Backup / restore: [P12](./policies/P12_backup_and_restore.md) — runbook [runbooks/neon-restore-test.md](./runbooks/neon-restore-test.md); restore test **Pass** 2026-07-27 (PITR throwaway; Railway `DATABASE_URL` unchanged) — [evidence/neon-restore-test-2026-07-27.md](./evidence/neon-restore-test-2026-07-27.md).

---

## Emergency changes

Allowed to restore service or contain an incident ([P04](./policies/P04_incident_response_plan.md)):

1. Fix forward or roll back via Vercel/Railway.
2. Rotate any exposed secrets immediately.
3. Document after-the-fact (PR + notes) within 2 business days.

---

## Evidence for auditors (when ready)

| Artifact | Source |
|----------|--------|
| PR + approval history | GitHub |
| Deploy history | Vercel + Railway dashboards |
| Branch protection / ruleset settings | GitHub — ruleset protecting `main` with required PR — **confirmed 2026-07-26** |
| This document + approved P05 | `docs/soc2/` |

---

## Open confirmations for Matt

- [x] GitHub: protect `main`, required PR before merge — done 2026-07-26 (solo-friendly; approvals may be 0)
- [x] MFA on GitHub, Vercel, Railway — done 2026-07-26
- [!] Confirm exact production project/service names and whether staging is separate
- [!] Dependabot (or equivalent) enabled

---

_End of working CHANGE_MANAGEMENT.md_
