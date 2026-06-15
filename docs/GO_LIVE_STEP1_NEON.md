# Go-live Step 1 — Neon auth database + Vercel auth env

**Milestone:** Auth milestone (items am-4 through am-7 on `/progress`)  
**Goal:** Production magic-link login on Vercel infrastructure.

**Production URL:** https://smpl-financial-intelligence.vercel.app

---

## Overview

| Step | Who | Time |
|------|-----|------|
| 1. Create Neon Postgres | You (browser) | ~5 min |
| 2. Run migrations + seed | PowerShell script | ~2 min |
| 3. Add Vercel env vars | You (browser) | ~5 min |
| 4. Redeploy Vercel | One click | ~2 min |
| 5. Smoke test `/login` | You | ~2 min |

**Phase B (hosted API)** can run in parallel — see `docs/DEPLOYMENT.md` Phase 2. Magic-link **click** → `/app` needs `SFI_BACKEND_URL` once the API is live.

---

## Step 1 — Create Neon project

1. Go to [https://neon.tech](https://neon.tech) and sign in (GitHub is fine).
2. **New Project** → name e.g. `smpl-auth-prod`
3. Region: pick one close to your users (e.g. US East).
4. Copy the **connection string** (PostgreSQL). It looks like:
   ```
   postgresql://USER:PASSWORD@ep-xxxx.us-east-1.aws.neon.tech/neondb?sslmode=require
   ```
5. Keep this secret — it becomes `AUTH_DATABASE_URL` on Vercel.

**Tip:** Neon free tier is enough for auth milestone smoke tests.

---

## Step 2 — Migrate + seed (from your machine)

From repo root, paste your Neon connection string:

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence

.\scripts\setup-prod-auth-db.ps1 `
  -DatabaseUrl "postgresql://USER:PASSWORD@ep-xxxx.neon.tech/neondb?sslmode=require" `
  -Email mattjustice@smpl-ai.com
```

This script:

1. Runs `alembic upgrade head` (all tables including `authjs_*`, `users`, `organization_members`)
2. Creates demo org `8571e520-0687-4516-bdee-379f37c58c1f` if missing
3. Seeds a pending invite for your email
4. Prints the Vercel env vars to add next

---

## Step 3 — Vercel environment variables

**Vercel → smpl-financial-intelligence → Settings → Environment Variables → Production**

| Variable | Value |
|----------|--------|
| `AUTH_DATABASE_URL` | Neon connection string (same as above) |
| `AUTH_SECRET` | New random string — run `openssl rand -base64 32` |
| `AUTH_URL` | `https://smpl-financial-intelligence.vercel.app` |
| `APP_BASE_URL` | Same as `AUTH_URL` |
| `AUTH_RESEND_KEY` | Your Resend API key (`re_...`) |
| `EMAIL_FROM` | `SMPL.ai <onboarding@resend.dev>` (or verified domain) |

Also run `.\scripts\print-vercel-auth-env.ps1` for a printable checklist.

**Do not** paste localhost URLs into Production.

---

## Step 4 — Redeploy

Env vars apply only to **new** deployments:

**Vercel → Deployments → … → Redeploy**

---

## Step 5 — Smoke test

1. Open https://smpl-financial-intelligence.vercel.app/login
2. Enter the email you seeded with `-Email`
3. Check inbox for the magic link (Resend dev mode may only deliver to your Resend account email)
4. **Email received?** → Auth milestone ~80% done (am-4, am-5, am-6 complete)
5. **Click link → `/app`?** → Needs `SFI_BACKEND_URL` pointing to hosted FastAPI (Phase B)

Update checklist in `frontend/lib/go-live-progress.ts` and refresh `/progress`.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Build fails on Vercel | Should be fixed — `db.ts` skips auth URL at build time |
| Login shows Configuration error | Missing or wrong `AUTH_DATABASE_URL` / `AUTH_SECRET` |
| Email not received | Check `AUTH_RESEND_KEY`, `EMAIL_FROM`, Resend dashboard logs |
| Link works but Access Denied | Email needs pending invite; re-run setup script with `-Email` |
| Link works but /app empty/errors | Set `SFI_BACKEND_URL` to hosted API (not localhost) |

---

## Next step (parallel)

**Phase B — Host FastAPI + warehouse Postgres** on Railway (see `railway.toml`, `docs/DEPLOYMENT.md`).

When API URL is live, add to Vercel:

- `SFI_BACKEND_URL`
- `NEXT_PUBLIC_API_URL`

Then complete am-7 and start Customer /app checklist items.

---

## Related

- `docs/VERCEL_AUTH_DEPLOY.md`
- `docs/CUSTOMER_ACCESS.md`
- `scripts/setup-prod-auth-db.ps1`
- `scripts/print-vercel-auth-env.ps1`
