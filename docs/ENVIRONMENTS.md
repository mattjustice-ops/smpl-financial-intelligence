# SMPL environments — Production vs Sandbox

We use two **logical** environments. Infrastructure names (Railway services, Neon branches, script filenames) may still say `staging` from early gl-5 work — that is the same thing as **sandbox**.

## Naming

| What we call it | Purpose | Who uses it |
|-----------------|---------|-------------|
| **Production** | Live customer-facing app | Paying customers, prod demos, real invites |
| **Sandbox** | Safe copy for development and PR checks | Engineers, Preview URLs, smoke tests before merge |

**Not** separate POC instances: sandbox is one shared engineering environment. **SMPL Demo Co** is the demo workspace inside sandbox (and prod) with pre-loaded charts data.

## Stack mapping

| Layer | Production | Sandbox |
|-------|------------|---------|
| Frontend | Vercel **Production** | Vercel **Preview** (feature branches / PRs) |
| API | Railway `sfi-api-production` | Railway `sfi-api-staging` * |
| Database | Neon **prod** branch | Neon **staging** branch * |
| Auth DB (Vercel) | `AUTH_DATABASE_URL` → prod Neon | `AUTH_DATABASE_URL` → sandbox Neon |
| API URLs (Vercel) | `SFI_BACKEND_URL` / `NEXT_PUBLIC_API_URL` → prod API | Same vars → sandbox API |

\* Legacy infra labels; treat as **sandbox** in conversation and runbooks.

## Rules

1. **Sandbox Preview must never call production API or prod Neon.**
2. **Production must never use sandbox API or sandbox Neon.**
3. Default login workspace on sandbox Preview: **SMPL Demo Co** (`8571e520-…`) — full enterprise demo data.
4. **Customer Corp** is a separate test org for the white-glove POC playbook (poc-0), not the default Preview demo.

## Sandbox Git branch

**Branch:** `gl-5b-sandbox` (renamed from `gl-5b-preview-test`)

**Stable Preview URLs** (after a Git-triggered deploy, not CLI redeploy):

- `https://smpl-financial-intelligence-git-gl-5b-sandbox-smplai.vercel.app`
- `https://smpl-financial-intelligence-mattjustice-ops-smplai.vercel.app` (author URL on team)

Old branch URLs and deployment hashes from `gl-5b-preview-test` return **404** after branch delete — expected.

## Railway sandbox (`sfi-api-staging`)

Set **API_CORS_ORIGINS** so browser dashboards on Preview can call the sandbox API.

```powershell
.\scripts\set-railway-sandbox-cors.ps1          # CLI (requires railway login + link)
.\scripts\set-railway-sandbox-cors.ps1 -PrintOnly   # paste into Railway dashboard
```

Confirm **DATABASE_URL** on `sfi-api-staging` uses sandbox Neon (`ep-fragrant-grass-…`), not prod.

## Local config files (legacy names)

| File | Meaning |
|------|---------|
| `frontend/.env.staging.local` | Sandbox API + Neon URLs for local scripts |
| `STAGING_API_URL` / `STAGING_DATABASE_URL` | Same as sandbox API / sandbox DB |

## Related docs

- [GO_LIVE_GL5_STAGING.md](./GO_LIVE_GL5_STAGING.md) — gl-5 setup checklist (sandbox)
- [GO_LIVE_GL6_MONITORING.md](./GO_LIVE_GL6_MONITORING.md) — monitoring, backups, incident runbook
- [GO_LIVE_POC_DIRECT_DATA_ACCESS.md](./GO_LIVE_POC_DIRECT_DATA_ACCESS.md) — per-customer POC (path A)

---

## Sandbox → production (simple methodology)

**Both environments stay live.** That is normal: sandbox is where you break things; production is where customers are. You do not shut sandbox down after go-live.

You also do **not** “move” sandbox to prod like copying a server. Promotion is **code through git**, not data migration.

### What promotes (automatic)

| What | How |
|------|-----|
| Application code (frontend + backend) | Merge PR → `main` → Vercel Production + Railway prod deploy |
| Bug fixes, UI, API logic | Same — always ship via git |

### What does **not** promote

| What | Why |
|------|-----|
| Sandbox Neon data | Test/demo data; prod has real customer orgs |
| SMPL Demo Co / Customer Corp test state | Re-seed or script on each env if needed |
| Vercel env vars | Set **once per environment** (Preview vs Production); already done for API URLs |
| Magic-link sessions | Users sign in again on each URL |

### Recommended flow (5 steps)

```
1. Branch     → push → Vercel Preview (sandbox) builds automatically
2. Verify     → login on Preview, spot-check /app, optional smoke-test-staging.ps1
3. Merge      → PR to main (only path to production code)
4. Prod deploy → Vercel + Railway prod auto-build from main
5. Sanity     → prod /health, optional smoke-test-plan-entitlements.ps1 on prod
```

**Merge to `main` is the only promotion lever.** Sandbox exists so step 2 happens before step 3.

### When env vars change

Rare after gl-5b. If you add a new secret or URL:

1. Add to **Production** in Vercel / Railway prod.
2. Add to **Preview (sandbox)** with sandbox values (different API URL, different Neon branch).
3. Redeploy both — no code merge required for env-only fixes.

Use `print-vercel-preview-api-values.ps1` as the template: same variable **names**, different **values** per environment.

### Optional simplifications later

- **Railway:** point sandbox service at `main` too (same commit as prod, different `DATABASE_URL`) — less branch drift.
- **CI gate:** run `smoke-test-staging.ps1` on PR before merge (GitHub Action).
- **Renames:** rename Railway `sfi-api-staging` → `sfi-api-sandbox` when convenient (cosmetic only).

### Mental model

```
        ┌─────────────┐         merge main         ┌─────────────┐
        │   SANDBOX   │  ──────────────────────► │ PRODUCTION  │
        │  (Preview)  │      (code only)         │   (live)    │
        └─────────────┘                          └─────────────┘
              │                                        │
         sandbox API                              prod API
         sandbox Neon                              prod Neon
```

Same repo. Two configs. One front door to prod: **merge**.
