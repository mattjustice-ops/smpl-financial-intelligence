# Secrets env-store spot-check evidence — YYYY-MM-DD

> Fill after [../runbooks/secrets-env-store-spotcheck.md](../runbooks/secrets-env-store-spotcheck.md).  
> **Sanitized only** — never paste API keys, connection strings, or passwords.  
> Completing a real Pass = Month 2 readiness evidence. **Not** SOC 2 certification.

## Status: WIP — AWAITING RUN

| Field | Value |
|-------|--------|
| Date of spot-check | YYYY-MM-DD |
| Operator | Matt Justice |
| Environments checked | ☐ Vercel Production ☐ Railway `sfi-api-production` ☐ Neon `smpl-auth-prod` ☐ Git tracked files |
| Live console access this session? | ☐ Yes ☐ Partial ☐ Blocked (form prepared only) |
| Overall result | ☐ Pass ☐ Fail ☐ Blocked |
| Scoreboard | Leave `[ ]` until Pass |

---

## Checklist results

| # | Check | Result | Notes (no secrets) |
|---|--------|--------|-------------------|
| A1 | Vercel: `AUTH_SECRET`, `AUTH_DATABASE_URL`, `AUTH_URL` / `APP_BASE_URL` present (Production) | ☐ Pass ☐ Fail ☐ Blocked | |
| A2 | Vercel: `SFI_BACKEND_URL` + `NEXT_PUBLIC_API_URL` point at Railway prod | ☐ Pass ☐ Fail ☐ Blocked | |
| A3 | Vercel: Resend / `EMAIL_FROM` present for magic link | ☐ Pass ☐ Fail ☐ Blocked | |
| A4 | Vercel: **no** `ANTHROPIC_API_KEY` (Claude on Railway only) | ☐ Pass ☐ Fail ☐ Blocked | |
| A5 | Vercel: no secrets in `NEXT_PUBLIC_*` | ☐ Pass ☐ Fail ☐ Blocked | |
| B1 | Railway: `DATABASE_URL` present | ☐ Pass ☐ Fail ☐ Blocked | |
| B2 | Railway: `ANTHROPIC_API_KEY` present | ☐ Pass ☐ Fail ☐ Blocked | |
| B3 | Railway: `API_CORS_ORIGINS` includes prod web origins | ☐ Pass ☐ Fail ☐ Blocked | |
| B4 | Railway: `BILLING_INTERNAL_API_KEY` matches Vercel (if used) | ☐ Pass ☐ Fail ☐ N/A ☐ Blocked | |
| B5 | Railway: `OPENAI_API_KEY` unset (or documented if intentionally live) | ☐ Pass ☐ Fail ☐ Blocked | |
| C1 | Neon connection string only in env stores / gitignored local files | ☐ Pass ☐ Fail ☐ Blocked | |
| D1 | `git check-ignore` covers `backend/secrets.env` + local `.env*` | ☐ Pass ☐ Fail ☐ Blocked | |
| D2 | `git ls-files` / `git grep` — no live prod secrets in tracked files | ☐ Pass ☐ Fail ☐ Blocked | |
| D3 | GitHub secret scanning / push protection still enabled | ☐ Pass ☐ Fail ☐ Blocked | See dependabot evidence 2026-07-28 |

---

## Git commands run (paste command names only + outcome)

| Command | Outcome |
|---------|---------|
| `git check-ignore -v …` | |
| `git ls-files "*.env" …` | |
| `git grep …` (tracked) | |

---

## Findings / remediation

-

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Security owner | Matt Justice | | ☐ Pass ☐ Fail ☐ Blocked |

_Readiness evidence only — not SOC 2 certified._
