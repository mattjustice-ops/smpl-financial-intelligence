# gl-6 — Monitoring, backups, and incident runbook (minimal)

**Goal:** Know when prod is unhealthy, how to recover, and what to run before customer outreach or a POC load.

**Production URLs**

| Surface | URL |
|---------|-----|
| Frontend | https://smpl-financial-intelligence.vercel.app |
| Login | https://smpl-financial-intelligence.vercel.app/login |
| Progress | https://smpl-financial-intelligence.vercel.app/progress |
| Frontend health (proxies API) | https://smpl-financial-intelligence.vercel.app/health |
| Railway prod API | https://sfi-api-production.up.railway.app/health |
| Railway prod DB | https://sfi-api-production.up.railway.app/health/db |

**Sandbox (Preview)**

| Surface | URL |
|---------|-----|
| Branch Preview | https://smpl-financial-intelligence-git-gl-5b-sandbox-smplai.vercel.app |
| Sandbox API | https://sfi-api-staging-production.up.railway.app/health |

See `docs/ENVIRONMENTS.md` for production vs sandbox mapping.

---

## Dashboards (where to look)

| System | Console | Check |
|--------|---------|-------|
| **Vercel** | [vercel.com](https://vercel.com) → `smpl-financial-intelligence` | Latest **Production** deploy green; env vars intact |
| **Railway** | [railway.app](https://railway.app) → `smpl-ai` → `sfi-api-production` | Service online; recent deploy after `main` push |
| **Neon** | [console.neon.tech](https://console.neon.tech) | Prod branch healthy; connection count normal |
| **Resend** | [resend.com](https://resend.com) | Domain verified; magic-link delivery |

---

## Backups

| Data | Method |
|------|--------|
| **Neon prod** | Branch PITR / restore from Neon console (enable on prod project if not already) |
| **Auth DB** | Same Neon project as warehouse (verify branch in Vercel `AUTH_DATABASE_URL`) |
| **Code** | GitHub `main` — redeploy any prior commit via Vercel/Railway |
| **Customer CSV staging** | Never commit — local or secure bucket only (`GO_LIVE_POC_DIRECT_DATA_ACCESS.md`) |

Before loading a real customer POC: note current Neon **branch / timestamp** or create a short-lived backup branch.

---

## Pre-outreach smoke (run before Monday messages)

From repo root:

```powershell
# Prod API + entitlements
.\scripts\smoke-test-plan-entitlements.ps1

# Optional: sandbox stack
.\scripts\smoke-test-staging.ps1

# Full prod readiness (health + entitlements)
.\scripts\smoke-test-prod-readiness.ps1
```

**Manual (5 min):**

1. Incognito → prod `/login` → new magic link → `/app` shows **SMPL Demo Co**
2. `/health` on prod frontend → JSON `status: ok`
3. `/board` loads June 2026 demo

---

## Incident runbook (minimal)

### Symptom: site 502 / blank / API errors

1. Check Vercel **Production** deployment status (failed build vs runtime).
2. Check Railway `sfi-api-production` logs and `/health`.
3. Check Neon status page / connection limits.
4. **Rollback:** Vercel → Deployments → previous Production deployment → **Redeploy**. Railway → redeploy previous image or revert `main` and push.

### Symptom: magic links not arriving

1. Resend dashboard → logs for `noreply@smpl-ai.com`.
2. Vercel Production env: `AUTH_RESEND_KEY`, `EMAIL_FROM`.
3. Customer spam folder; try `@smpl-ai.com` internal test.

### Symptom: wrong workspace / empty dashboards

1. `/api/auth/session` while logged in — check `activeOrganizationId`.
2. Prod must use prod API + prod Neon (not sandbox URLs in Production env).
3. Re-run `provision-prod-customer.ps1` or `set-staging-demo-workspace.ps1` on correct env.

### Symptom: customer POC data wrong

1. Confirm org UUID in `setup-prod-warehouse.ps1` matches provisioned org.
2. Run validation scripts from `GO_LIVE_POC_DIRECT_DATA_ACCESS.md`.
3. Do **not** mix sandbox and prod Neon URLs.

---

## Escalation

| Role | Action |
|------|--------|
| **Engineering** | Fix deploy, env, or code; merge via `main` |
| **Ops / sales** | Pause POC timeline; communicate to prospect |
| **Security** | Revoke access shares; rotate keys if leak suspected |

---

## Related docs

- `docs/ENVIRONMENTS.md` — prod vs sandbox
- `docs/GO_LIVE_GL1_CUSTOMER_PROVISIONING.md` — invite / new org
- `docs/GO_LIVE_POC_DIRECT_DATA_ACCESS.md` — white-glove POC
- `docs/GO_LIVE_GL5_STAGING.md` — sandbox smoke tests

---

## gl-6 definition of done (minimal)

- [x] Health URLs documented
- [x] Dashboard links documented
- [x] Backup approach documented (Neon PITR + git redeploy)
- [x] Incident runbook (502, auth, workspace, POC)
- [x] Pre-outreach smoke script (`smoke-test-prod-readiness.ps1`)

Optional later: Datadog/Sentry, PagerDuty, automated uptime checks.
