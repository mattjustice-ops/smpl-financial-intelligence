# Secrets env-store spot-check (Month 2)

> **Readiness only — not SOC 2 certified.**  
> Confirm production secrets live in host env/secret stores and are **not** in git.  
> This session may be **blocked** without Matt’s Vercel / Railway / Neon console access — still fill the evidence form with Pass / Fail / Blocked per row.

| Field | Value |
|-------|--------|
| Related policies | [P05](../policies/P05_change_management_policy.md), [CHANGE_MANAGEMENT.md](../CHANGE_MANAGEMENT.md) |
| Scoreboard item | Secrets only in env stores (spot-check) — Month 2 |
| Owner | Matt Justice |
| Evidence template | [../evidence/secrets-env-store-spotcheck-TEMPLATE.md](../evidence/secrets-env-store-spotcheck-TEMPLATE.md) |
| Do not | Paste secret **values** into git, chat, or evidence files |

---

## Goal

Prove (sanitized checklist + optional screenshots kept local):

1. Production secrets are set in **Vercel**, **Railway**, and connection strings originate from **Neon** (held in those env stores).
2. Git history / tracked files do not contain live production secrets.
3. Local secret files are gitignored and not staged.

---

## Exact places to verify (Matt — console + CLI)

### A. Vercel (frontend / Auth.js)

Project: **smpl-financial-intelligence** · Environment: **Production** (also skim Preview if used).

Open: Vercel → Project → **Settings → Environment Variables**. Confirm **names exist** (do not export values into evidence):

| Var name (expected) | Purpose |
|---------------------|---------|
| `AUTH_SECRET` | Auth.js session secret |
| `AUTH_URL` / `APP_BASE_URL` | Canonical app URL (`https://www.smpl-ai.com` or Vercel hostname) |
| `AUTH_DATABASE_URL` | Neon Postgres (same branch as API warehouse) |
| `AUTH_RESEND_KEY` (or Resend via token file pattern locally) | Magic-link email |
| `EMAIL_FROM` | From address on verified domain |
| `SFI_BACKEND_URL` | Railway API base URL |
| `NEXT_PUBLIC_API_URL` | Browser API base (same Railway URL in prod) |
| `BILLING_INTERNAL_API_KEY` | Shared with Railway (if billing webhooks live) |
| Stripe server vars (if checkout live) | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, price IDs — **never** `NEXT_PUBLIC_*` for secrets |
| Sanity read token (if set) | `SANITY_API_READ_TOKEN` — server-only |

**Must not** appear on Vercel as browser-exposed secrets:

- `ANTHROPIC_API_KEY` (Railway only — see [GO_LIVE_PROD_DEPLOY.md](../../GO_LIVE_PROD_DEPLOY.md))
- Any `sk-ant-…`, `sk_live_…`, Neon passwords in `NEXT_PUBLIC_*`

### B. Railway (API)

Service: **`sfi-api-production`**.

Open: Railway → service → **Variables**. Confirm names exist:

| Var name (expected) | Purpose |
|---------------------|---------|
| `DATABASE_URL` | Neon production connection (psycopg form OK) |
| `ANTHROPIC_API_KEY` | LLM commentary / exports |
| `API_CORS_ORIGINS` | Allowed browser origins |
| `BILLING_INTERNAL_API_KEY` | Must match Vercel when used |
| Optional | `SFI_PUBLIC_API_URL`, `SMPL_OPS_ADMIN_EMAILS`, `OPENAI_API_KEY` (**should be unset** if OpenAI not live — boundary locked 2026-07-28) |

### C. Neon (connection string source)

Project: **`smpl-auth-prod`** · branch **`production`** (AWS us-east-1).

- Confirm connection strings are copied into Vercel `AUTH_DATABASE_URL` / Railway `DATABASE_URL` — **not** committed to the repo.
- Do **not** change production URLs during this spot-check.
- Optional: note whether a Neon API key exists for ops (local / password manager only — not git).

### D. Git / repo hygiene (can run without cloud consoles)

From repo root (PowerShell):

```powershell
# 1) Tracked files that look like env dumps (should be empty or only *.example)
git ls-files "*.env" "*secrets*" "*credentials*"

# 2) Confirm ignore rules cover local secret files
git check-ignore -v backend/secrets.env frontend/.env.local frontend/.env.neon-production.local

# 3) Quick content scan of TRACKED files only (false positives OK — review hits)
git grep -I -n -E "sk-ant-api|sk_live_|sk_test_|whsec_|postgres(ql)?(\+psycopg)?://[^:]+:[^@]+@" -- ":!.agents" ":!docs/video" || echo "No matches in tracked files"
```

Expected:

| Check | Expected |
|-------|----------|
| `backend/secrets.env` | **Untracked** / gitignored |
| `frontend/.env.local`, `.env.neon-production.local`, `.env.vercel-production.local` | **Untracked** / gitignored |
| Tracked examples | `.env.example` / docs with **placeholder** values only |
| GitHub | Secret Protection + push protection already confirmed 2026-07-28 — [dependabot-enabled-2026-07-28.md](../evidence/dependabot-enabled-2026-07-28.md) |

If `git grep` hits a tracked file with a live-looking secret → **Fail**: rotate immediately (P04), remove from git history as needed, re-run spot-check.

### E. Local-only (optional; do not commit results)

- Password manager / `*_TOKEN_FILE` paths hold connector keys (Stripe test, HubSpot, etc.).
- Connector sandbox keys must **not** be promoted to Railway/Vercel production unless intentionally live.

---

## Pass criteria

| # | Criterion |
|---|-----------|
| 1 | Vercel Production has required auth + API URL vars; no Anthropic key on Vercel |
| 2 | Railway production has `DATABASE_URL` + `ANTHROPIC_API_KEY` (+ CORS / billing key as applicable) |
| 3 | Neon connection strings only in env stores / local gitignored files |
| 4 | Spot-check commands show no live production secrets in **tracked** git files |
| 5 | Evidence form filled with Pass/Fail/Blocked — **no secret values** |

---

## After the run

1. Copy [../evidence/secrets-env-store-spotcheck-TEMPLATE.md](../evidence/secrets-env-store-spotcheck-TEMPLATE.md) → `secrets-env-store-spotcheck-YYYY-MM-DD.md`.
2. Mark scoreboard `[x]` only when Pass (or document residual Fail + remediation).
3. Sync `frontend/lib/compliance/progress.ts` when marking complete.
4. Keep screenshots in a private vault or `*.local.md` (gitignored).

---

_Document control: Month 2 prep 2026-07-29 — readiness pack only; item remains open until Matt executes._
