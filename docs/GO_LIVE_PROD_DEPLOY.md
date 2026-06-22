# Production deploy — live Neon warehouse + Vercel

Deploy code to Vercel, load warehouse data into Neon, and wire Railway for live outlook + optional Claude.

## What ships in this deploy

| Surface | Live Neon data | Claude (commentary / exports) |
|---------|----------------|--------------------------------|
| `/forecast-engine` (signed in) | Yes — outlook API | N/A |
| `/app/board` (signed in) | Yes — 3-statement + ARR/revenue sync | Via Railway API |
| `/board` (public demo) | Demo fallback | Sign-in required for live |
| Month-end exports (toolbar) | Live when signed in | `include_ai_commentary=true` + Railway key |

Claude keys live on **Railway only** — never on Vercel.

---

## Run order

### 1. Load Neon warehouse (same branch as Railway + AUTH)

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence
.\scripts\load-prod-warehouse.ps1
```

Uses `frontend/.env.neon-production.local` if present.

### 2. Railway production API

Confirm on `sfi-api-production` (or your prod service):

| Variable | Value |
|----------|--------|
| `DATABASE_URL` | Same Neon URL as warehouse load |
| `API_CORS_ORIGINS` | `https://smpl-financial-intelligence.vercel.app,https://smpl-ai.com,http://localhost:3002` |
| `BILLING_INTERNAL_API_KEY` | Same as Vercel |
| `ANTHROPIC_API_KEY` | Prod key (for commentary + exports) |

```powershell
.\scripts\set-railway-anthropic-keys.ps1 -SkipSandbox
```

Redeploy Railway after env changes.

### 3. Vercel production

```powershell
.\scripts\set-vercel-api-env.ps1 -BackendUrl "https://sfi-api-production.up.railway.app"
# Auth vars if not set:
# .\scripts\set-vercel-prod-auth-env.ps1 -DatabaseUrl "..." -ProdUrl "https://smpl-ai.com"
.\scripts\deploy-prod-live.ps1 -CommitPush
```

### 4. Smoke test (signed in)

1. `https://smpl-financial-intelligence.vercel.app/login` → magic link  
2. `/app/board` → top bar shows **Live · {org}**  
3. **3-Statement** tab → Jun revenue/tax match warehouse  
4. **Regenerate AI commentary** on Executive Summary (needs `ANTHROPIC_API_KEY`)  
5. **MD&A Deck** / **Variance Commentary** → downloads from API (not static `/board/exports/`)  
6. `/forecast-engine` → footer **Live · …**

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Demo data" in board footer | Sign in; check `SFI_BACKEND_URL` on Vercel |
| Outlook 401/403 | Session-sync / org membership / entitlements |
| Commentary 503 | `ANTHROPIC_API_KEY` on Railway |
| Commentary 409 | Validation warnings — resolve warehouse ties or check export validation |
| Promote 409 | Same validation gate on forecast promote |

---

## Optional: custom domain

```powershell
.\scripts\setup-smpl-ai-domain.ps1
# After DNS valid, update AUTH_URL to https://smpl-ai.com and redeploy
```
