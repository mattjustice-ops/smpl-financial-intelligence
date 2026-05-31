# Cloud deployment (Option 3)

Public demo URL structure after deploy:

| Route | What it serves | Backend required |
|-------|----------------|------------------|
| `/` | Marketing landing page | No |
| `/board` | May 2026 board package (static HTML prototype) | No |
| `/app` | Live platform (Management P&L, workforce, etc.) | Yes |

The **board demo** works on Vercel alone — no API or database needed. Share that URL with investors, board members, and prospects immediately.

The **live platform** (`/app`) needs the FastAPI backend + Postgres with your org data loaded.

---

## Phase 1 — Board demo on Vercel (fastest path)

1. Push this repo to GitHub.
2. Import the project in [Vercel](https://vercel.com/new):
   - **Root Directory:** `frontend`
   - **Framework:** Next.js (auto-detected)
3. Deploy. No environment variables required for landing + board demo.
4. Share: `https://your-project.vercel.app/board`

Local preview:

```powershell
cd frontend
npm run dev
# http://localhost:3002/board
```

---

## Phase 2 — Live platform (Railway or Render)

### Backend (Railway)

1. Create a new project → **Add PostgreSQL**.
2. Add a service from this repo; set **Root Directory** to `backend`.
3. Set environment variables:

| Variable | Example |
|----------|---------|
| `DATABASE_URL` | From Railway Postgres plugin (use `postgresql+psycopg://...` form) |
| `API_CORS_ORIGINS` | `https://your-frontend.vercel.app,http://localhost:3002` |

4. Deploy. Confirm `https://your-api.up.railway.app/health` returns build metadata.

5. Run migrations / seed (one-time, from your machine or Railway shell):

```powershell
cd backend
$env:DATABASE_URL = "postgresql+psycopg://..."
python scripts/sync_warehouse_schema.py
# Then load your GL CSVs via existing import scripts
```

### Frontend env (Vercel)

Add to Vercel project settings:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://your-api.up.railway.app` |
| `SFI_BACKEND_URL` | Same as above (server-side proxy) |

Redeploy frontend after setting env vars.

---

## Phase 3 — Optional hardening before wide sharing

- Add Vercel **Password Protection** (Pro) or basic auth middleware on `/app`.
- Keep `/board` public as the marketing demo.
- Do **not** expose Anthropic/OpenAI keys in the static board HTML; AI regenerate buttons need a backend proxy (see `docs/VISUAL_DESIGN_WORKFLOW.md`).

---

## Files in this repo

| File | Purpose |
|------|---------|
| `frontend/public/board/index.html` | Claude-built board dashboard (source of truth for visual demo) |
| `frontend/vercel.json` | Vercel config + `/board` rewrite |
| `backend/Dockerfile` | Container image for Railway/Render |
| `railway.toml` | Railway service hints |
| `render.yaml` | Optional Render blueprint |

---

## Troubleshooting

- **Board demo blank charts:** Check browser console; Chart.js loads from CDN — needs internet.
- **AI commentary buttons fail:** Expected without API key; static commentary still displays.
- **`/app` empty or errors:** Backend not running or `NEXT_PUBLIC_API_URL` wrong.
- **CORS errors:** Add your Vercel domain to `API_CORS_ORIGINS` on the backend.
