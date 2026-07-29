# Secrets env-store spot-check evidence — 2026-07-29

> Filled after [../runbooks/secrets-env-store-spotcheck.md](../runbooks/secrets-env-store-spotcheck.md).  
> **Sanitized only** — no API keys, connection strings, or passwords.  
> Completing a real Pass = Month 2 readiness evidence. **Not** SOC 2 certification.

## Status: PARTIAL — GIT PASS; CLOUD CONSOLES AWAITING MATT

| Field | Value |
|-------|--------|
| Date of spot-check | 2026-07-29 |
| Operator | Agent (git + local hygiene) + Matt Justice (live consoles still required) |
| Environments checked | ☐ Vercel Production ☐ Railway `sfi-api-production` ☑ Neon connectivity via local gitignored file (read-only name check) ☑ Git tracked files |
| Live console access this session? | ☑ Partial — no `vercel` / `railway` / `neonctl` CLIs; `gh` unauthenticated |
| Overall result | ☑ Partial (not Pass until A/B/C console rows confirmed) |
| Scoreboard | `[~]` until Matt confirms Vercel + Railway + Neon console rows → then `[x]` if Pass |

---

## Checklist results

| # | Check | Result | Notes (no secrets) |
|---|--------|--------|-------------------|
| A1 | Vercel: `AUTH_SECRET`, `AUTH_DATABASE_URL`, `AUTH_URL` / `APP_BASE_URL` present (Production) | ☑ Partial | Local gitignored `frontend/.env.vercel-production.local` (prior env pull) lists those **names**. Live Vercel Production console **not** opened this session — Matt must confirm. |
| A2 | Vercel: `SFI_BACKEND_URL` + `NEXT_PUBLIC_API_URL` point at Railway prod | ☑ Partial | Same local pull lists both **names**. Matt: confirm Production values are Railway API base (no secret paste). |
| A3 | Vercel: Resend / `EMAIL_FROM` present for magic link | ☑ Partial | Local pull lists `AUTH_RESEND_KEY` + `EMAIL_FROM`. Matt console confirm. |
| A4 | Vercel: **no** `ANTHROPIC_API_KEY` (Claude on Railway only) | ☑ Partial | Local pull has **no** `ANTHROPIC_*` key names. Matt: confirm absent in Vercel Production UI. |
| A5 | Vercel: no secrets in `NEXT_PUBLIC_*` | ☑ Partial | Local pull `NEXT_PUBLIC_*` names only: `API_URL`, `SCHEDULING_URL`, `STRIPE_PUBLISHABLE_KEY` (publishable OK). Matt: confirm no secret material in any `NEXT_PUBLIC_*`. |
| B1 | Railway: `DATABASE_URL` present | ☑ Blocked | No Railway CLI/console this session. |
| B2 | Railway: `ANTHROPIC_API_KEY` present | ☑ Blocked | No Railway CLI/console. Local gitignored `backend/secrets.env` has Anthropic **name** for local/dev only — not proof of Railway Production. |
| B3 | Railway: `API_CORS_ORIGINS` includes prod web origins | ☑ Blocked | No Railway CLI/console. |
| B4 | Railway: `BILLING_INTERNAL_API_KEY` matches Vercel (if used) | ☑ Blocked | Not verified; confirm or mark N/A if unused. |
| B5 | Railway: `OPENAI_API_KEY` unset (or documented if intentionally live) | ☑ Blocked | Boundary locked 2026-07-28: OpenAI unused. Matt: confirm **unset** on Railway Production. |
| C1 | Neon connection string only in env stores / gitignored local files | ☑ Partial | Tracked git has placeholders only. Local `frontend/.env.neon-production.local` is gitignored and holds `DATABASE_URL` name; read-only org listing succeeded (no URL pasted). Matt: confirm Neon → Vercel/Railway copies, not git. |
| D1 | `git check-ignore` covers `backend/secrets.env` + local `.env*` | ☑ Pass | `.gitignore` matches all four paths checked. |
| D2 | `git ls-files` / `git grep` — no live prod secrets in tracked files | ☑ Pass | Tracked env files are `*.example` only. Cleaner grep (excl. venv/tmp): placeholders / docs patterns only — no live-looking `sk-ant-api…`, `sk_live_…`, `whsec_…`, or Neon host credentials in tracked files. |
| D3 | GitHub secret scanning / push protection still enabled | ☑ Pass | Prior evidence [dependabot-enabled-2026-07-28.md](./dependabot-enabled-2026-07-28.md); `gh` not authenticated this session — treat as still enabled unless Matt sees otherwise. |

---

## Git commands run (paste command names only + outcome)

| Command | Outcome |
|---------|---------|
| `git check-ignore -v backend/secrets.env frontend/.env.local frontend/.env.neon-production.local frontend/.env.vercel-production.local` | All four ignored (`.gitignore` lines 13 / 37) |
| `git ls-files "*.env" "*.env.*" "*secrets.env*"` | Only `*.example` tracked (+ docs/templates; no live `secrets.env`) |
| `git grep` live-looking secret patterns (excl. `.agents`, `docs/video`, `backend/.venv312`, `backend/tmp`) | Placeholder / docs hits only — **Pass** |

---

## Findings / remediation

- **Git hygiene Pass** — local secret files exist and are ignored; no live production secrets in tracked files.
- **Cloud consoles Blocked/Partial** — Matt must open Vercel Production, Railway `sfi-api-production`, and Neon `smpl-auth-prod` / `production` and tick A1–A5, B1–B5, C1 with Pass (or Fail + rotate).
- Optional: re-pull Vercel env to refresh local mirror after any var changes (keep gitignored).

## Matt console checklist (exact clicks)

1. **Vercel** → project `smpl-financial-intelligence` → Settings → Environment Variables → **Production**: confirm A1–A5 (names only; do not paste values into git/chat).
2. **Railway** → `sfi-api-production` → Variables: confirm B1–B5.
3. **Neon** → `smpl-auth-prod` / branch `production`: confirm connection strings are sourced into Vercel/Railway only (C1).
4. Update this file rows to Pass/Fail; if all Pass → scoreboard `[x]` + sync `progress.ts`.

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Security owner | Matt Justice | | ☐ Pass ☐ Fail ☑ Partial (git done; consoles pending) |

_Readiness evidence only — not SOC 2 certified._
