# Secrets env-store spot-check evidence — 2026-07-29

> Filled after [../runbooks/secrets-env-store-spotcheck.md](../runbooks/secrets-env-store-spotcheck.md).  
> **Sanitized only** — no API keys, connection strings, or passwords.  
> Completing a real Pass = Month 2 readiness evidence. **Not** SOC 2 certification.  
> **Agent limitation:** Cursor agent **cannot** open Vercel / Railway / Neon consoles for Matt. Live console rows **Pass** via Matt chat attestation 2026-07-29 (same pattern as access-review Allow).

## Status: PASS — 2026-07-29

| Field | Value |
|-------|--------|
| Date of spot-check | 2026-07-29 |
| Operator | Agent (git + local hygiene) + Matt Justice (Vercel / Railway / Neon consoles) |
| Environments checked | ☑ Vercel Production ☑ Railway `sfi-api-production` ☑ Neon ☑ Git tracked files |
| Live console access this session? | ☑ Matt confirmed A1–A5, B1–B5, C1 via chat (agent had no CLIs) |
| Overall result | ☑ **Pass** |
| Scoreboard | `[x]` |
| Attestation | Matt confirmed console checks + Org-B-only T1/T2 2026-07-29 via chat. |

---

## Checklist results

| # | Check | Result | Notes (no secrets) |
|---|--------|--------|-------------------|
| A1 | Vercel: `AUTH_SECRET`, `AUTH_DATABASE_URL`, `AUTH_URL` / `APP_BASE_URL` present (Production) | ☑ **Pass** | Matt confirmed in Vercel Production console 2026-07-29 (chat). Prior: local gitignored pull listed those **names**. |
| A2 | Vercel: `SFI_BACKEND_URL` + `NEXT_PUBLIC_API_URL` point at Railway prod | ☑ **Pass** | Matt confirmed Production values are Railway API base (no secret paste). |
| A3 | Vercel: Resend / `EMAIL_FROM` present for magic link | ☑ **Pass** | Matt confirmed `AUTH_RESEND_KEY` + `EMAIL_FROM` present. |
| A4 | Vercel: **no** `ANTHROPIC_API_KEY` (Claude on Railway only) | ☑ **Pass** | Matt confirmed absent in Vercel Production UI. |
| A5 | Vercel: no secrets in `NEXT_PUBLIC_*` | ☑ **Pass** | Matt confirmed no secret material in any `NEXT_PUBLIC_*`. |
| B1 | Railway: `DATABASE_URL` present | ☑ **Pass** | Matt confirmed on Railway `sfi-api-production` Variables. |
| B2 | Railway: `ANTHROPIC_API_KEY` present | ☑ **Pass** | Matt confirmed on Railway Production. |
| B3 | Railway: `API_CORS_ORIGINS` includes prod web origins | ☑ **Pass** | Matt confirmed. |
| B4 | Railway: `BILLING_INTERNAL_API_KEY` matches Vercel (if used) | ☑ **Pass** | Matt confirmed (or N/A if unused — closed as Pass per Matt console check). |
| B5 | Railway: `OPENAI_API_KEY` unset (or documented if intentionally live) | ☑ **Pass** | Matt confirmed **unset** on Railway Production (boundary: OpenAI unused). |
| C1 | Neon connection string only in env stores / gitignored local files | ☑ **Pass** | Matt confirmed Neon → Vercel/Railway copies, not git. Tracked git remains placeholders only. |
| D1 | `git check-ignore` covers `backend/secrets.env` + local `.env*` | ☑ Pass | `.gitignore` matches all four paths checked. |
| D2 | `git ls-files` / `git grep` — no live prod secrets in tracked files | ☑ Pass | Tracked env files are `*.example` only. Cleaner grep (excl. venv/tmp): placeholders / docs patterns only — no live-looking `sk-ant-api…`, `sk_live_…`, `whsec_…`, or Neon host credentials in tracked files. |
| D3 | GitHub secret scanning / push protection still enabled | ☑ Pass | Prior evidence [dependabot-enabled-2026-07-28.md](./dependabot-enabled-2026-07-28.md); treat as still enabled. |

---

## Git commands run (paste command names only + outcome)

| Command | Outcome |
|---------|---------|
| `git check-ignore -v backend/secrets.env frontend/.env.local frontend/.env.neon-production.local frontend/.env.vercel-production.local` | All four ignored (`.gitignore` lines 13 / 37) |
| `git ls-files "*.env" "*.env.*" "*secrets.env*"` | Only `*.example` tracked (+ docs/templates; no live `secrets.env`) |
| `git grep` live-looking secret patterns (excl. `.agents`, `docs/video`, `backend/.venv312`, `backend/tmp`) | Placeholder / docs hits only — **Pass** |

---

## Findings / remediation

- **Overall Pass 2026-07-29** — git hygiene Pass (agent) + Vercel/Railway/Neon console rows Pass (Matt chat attestation).
- No live production secrets invented or pasted into this evidence file.
- Optional: re-pull Vercel env to refresh local mirror after any var changes (keep gitignored).

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Security owner | Matt Justice | 2026-07-29 | ☑ **Pass** — Matt confirmed console checks + Org-B-only T1/T2 2026-07-29 via chat. |

_Readiness evidence only — not SOC 2 certified._
