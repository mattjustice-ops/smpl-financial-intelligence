# Customer access (Auth.js + provisioning)

## Flow

1. **Provision** — Stripe checkout or manual ops creates an `organizations` row + `pending_user_invites` for the customer email.
2. **Sign in** — Customer visits `/login`, enters work email, clicks magic link.
3. **Session sync** — Next.js calls `POST /api/v1/auth/session-sync` to upsert `users`, accept invites, create `organization_members`.
4. **Seats** — Each plan has a seat limit (Starter 2, Professional 5, Enterprise 10). Login fails with `seats_full` if the org is at capacity.
5. **Dashboard** — PR2 wires `/app` to the logged-in org (PR1 protects `/app` and requires invite).

## Local setup

### 1. Database migration

```powershell
cd backend
.\.venv312\Scripts\Activate.ps1
alembic upgrade head
```

### 2. Environment variables

**frontend/.env.local**

```env
AUTH_SECRET=generate-with-openssl-rand-base64-32
AUTH_URL=http://localhost:3002
SFI_BACKEND_URL=http://127.0.0.1:8001
# Magic-link tokens (defaults to local Docker Postgres if unset)
AUTH_DATABASE_URL=postgresql://sfi:sfi_dev_password@localhost:5432/sfi
# Resend magic-link email — see docs/RESEND_EMAIL_SETUP.md
RESEND_TOKEN_FILE=C:\Users\mattj\OneDrive\Documents\Resend Token.txt
EMAIL_FROM=SMPL.ai <onboarding@resend.dev>
# Or AUTH_RESEND_KEY=re_... for Vercel
# Optional — same value on backend if set
# BILLING_INTERNAL_API_KEY=your-random-secret
```

**backend/.env** (optional)

```env
BILLING_INTERNAL_API_KEY=your-random-secret
```

Without Resend or `EMAIL_SERVER`, magic links only print in the `npm run dev` terminal.

**Recommended:** run `.\scripts\setup-resend-email.ps1` and add a Resend API key (see `docs/RESEND_EMAIL_SETUP.md`).

### 3. Start Postgres (if not already running)

From the repo root:

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence
docker compose up -d
```

Wait ~5 seconds. Postgres listens on **localhost:5432** (Docker service name is `db`, not `sfi-postgres`).

### 4. Create a test invite

```powershell
.\scripts\seed-dev-invite.ps1 -Email you@company.com -OrganizationId 8571e520-0687-4516-bdee-379f37c58c1f
```

Uses the backend Python script (no Docker container name required). If Postgres is down, the script tells you to run `docker compose up -d`.

### 5. Run stack

```powershell
cd backend; .\start-api.ps1 -Port 8001
cd frontend; npm install; npm run dev
```

Open http://localhost:3002/login → enter invited email → check inbox for magic link → `/app`.

Auth.js stores verification tokens in Postgres (`authjs_verification_token`). Run `alembic upgrade head` so that table exists.

## API (internal)

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/auth/session-sync` | Upsert user, accept invites, return org list |
| `GET /api/v1/auth/organizations/{id}/seats` | Seat limit / used / available |

Requires `X-Billing-Internal-Key` header when `BILLING_INTERNAL_API_KEY` is set on the backend.

## Vercel production

| Key | Value |
|-----|--------|
| `AUTH_SECRET` | Random secret (same as local, different per env) |
| `AUTH_URL` | `https://smpl-financial-intelligence.vercel.app` |
| `SFI_BACKEND_URL` | Production API URL |
| `BILLING_INTERNAL_API_KEY` | Shared secret with backend |
| `AUTH_RESEND_KEY` or `RESEND_TOKEN_FILE` | Resend API key for magic links |
| `EMAIL_FROM` | Sender address (verified domain in production) |
| `AUTH_DATABASE_URL` | Postgres for verification tokens |

## PR2 (next)

- Wire `/app` to `session.user.activeOrganizationId`
- Authenticated API proxy with membership checks on all org routes
- Plan module entitlements in UI + API
