# Vercel auth milestone deploy

Deploy the **frontend only** to validate marketing, login shell, and Auth.js on production infrastructure. This is **not** full customer go-live — `/app` still uses the demo org until PR2.

**Production URL:** https://smpl-financial-intelligence.vercel.app

---

## What works after this deploy

| Route | Without prod API/DB | With prod AUTH_DATABASE_URL + API |
|-------|---------------------|-----------------------------------|
| `/` marketing | Yes | Yes |
| `/board` | Yes | Yes |
| `/login` UI | Yes | Yes |
| Magic link email | Needs `AUTH_RESEND_KEY` | Yes |
| Magic link click → `/app` | Needs `AUTH_DATABASE_URL` + `SFI_BACKEND_URL` | Yes (demo org data until PR2) |

---

## One-time Vercel project settings

1. [Vercel dashboard](https://vercel.com) → project **smpl-financial-intelligence**
2. **Settings → General → Root Directory:** `frontend`
3. **Framework:** Next.js (auto)

If the project is not connected yet: **Add New → Project** → import `mattjustice-ops/smpl-financial-intelligence` → set Root Directory **`frontend`**.

---

## Step 1 — Environment variables

From repo root:

```powershell
.\scripts\print-vercel-auth-env.ps1
```

Add each variable in **Vercel → Settings → Environment Variables → Production**.

### Minimum for auth smoke test

| Variable | Example |
|----------|---------|
| `AUTH_SECRET` | New random string (`openssl rand -base64 32`) |
| `AUTH_URL` | `https://smpl-financial-intelligence.vercel.app` |
| `APP_BASE_URL` | Same as `AUTH_URL` |
| `AUTH_RESEND_KEY` | `re_...` from Resend |
| `EMAIL_FROM` | `onboarding@resend.dev` (dev) or verified domain later |
| `AUTH_DATABASE_URL` | Neon/Supabase Postgres connection string |

### Required before `/app` works in prod

| Variable | Notes |
|----------|-------|
| `SFI_BACKEND_URL` | Hosted FastAPI URL (Railway/Render) — **not** `127.0.0.1` |
| `NEXT_PUBLIC_API_URL` | Same as `SFI_BACKEND_URL` |
| `BILLING_INTERNAL_API_KEY` | Same value on Vercel and backend (optional locally) |

Stripe vars are optional until you test checkout on production — see `docs/VERCEL_STRIPE_SETUP_BEGINNER.md`.

---

## Step 2 — Auth database migrations

On your **production** Postgres (the DB used by `AUTH_DATABASE_URL`):

```powershell
cd backend
$env:DATABASE_URL = "postgresql+psycopg://USER:PASS@HOST:5432/DB"
.\.venv312\Scripts\python.exe -m alembic upgrade head
```

This creates `authjs_users`, `authjs_verification_token`, `users`, `organization_members`, etc.

---

## Step 3 — Build, commit, push

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence
.\scripts\deploy-frontend-vercel.ps1 -CommitPush
```

This runs `npm run build`, commits if needed, and `git push origin main`. Vercel auto-deploys on push.

---

## Step 4 — Redeploy after env changes

If you added env vars **after** the last deploy:

**Vercel → Deployments → … → Redeploy**

Env vars are not applied to old deployments until redeploy.

---

## Step 5 — Smoke test

1. Open https://smpl-financial-intelligence.vercel.app/login
2. Enter an email with a **pending invite** in prod DB (or seed after API is up)
3. Check inbox for “Your SMPL sign-in link”
4. Click link → should land on `/app`

**Expected limitations (OK for this milestone):**

- Dashboard may show demo org data (hardcoded org ID until PR2)
- No customer invites until prod API + invites are seeded
- Resend `onboarding@resend.dev` only delivers to your Resend account email in dev mode

---

## Next before real customers

1. Host FastAPI + warehouse Postgres (Railway — see `docs/DEPLOYMENT.md` Phase 2)
2. Wire `/app` to `session.user.activeOrganizationId`
3. Verified email domain on Resend
4. Stripe live keys (when charging)

---

## Related

- `docs/CUSTOMER_ACCESS.md` — login flow and local setup
- `docs/RESEND_EMAIL_SETUP.md` — Resend keys
- `docs/DEPLOYMENT.md` — full stack (board + API + platform)
