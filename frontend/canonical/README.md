# Platform baseline (Board + Forecast Engine)

This folder is the **committed fallback** for the corrected June 2026 demo platform. When local edits break charts, KPIs, or dataset alignment, reset from here — do not copy from Downloads or older HTML exports.

## Commands (from `frontend/`)

| Command | When to use |
|---------|-------------|
| `npm run reset:platform` | Restore `public/board`, `public/forecast-engine`, and shared dataset files from this baseline |
| `npm run snapshot:platform` | After a verified good state, freeze current `public/` into `canonical/` for the next fallback |
| `npm run verify:platform` | Run board + forecast + outlook alignment checks |

## What is included

- **Board** — `board/index.html`, territory map assets (`us_emea_basemap.svg`, pin/projection JSON)
- **Forecast Engine** — `forecast-engine/index.html` with embedded `SRC` dataset
- **Shared** — `board-data.js`, `board-hydrate.js`, `smpl-skin.js`, `smpl-outlook.js`, `smpl-demo-seed.js`

Live URLs: `/board`, `/forecast-engine` (and embedded `/app/board`).

## Updating the baseline

1. Stabilize the platform in `public/` and pass `npm run verify:platform`.
2. Run `npm run snapshot:platform`.
3. Commit `frontend/canonical/` with your other changes.

## If `canonical/` is not fully populated yet

`reset:platform` falls back to **git HEAD** for `frontend/public/**` when large baseline files are missing from `canonical/`. After your first good state:

```powershell
npm run snapshot:platform
git add canonical
git commit -m "Freeze June 2026 platform baseline"
```

That copies board HTML, forecast HTML, shared JS, and the territory basemap into `canonical/` for one-command resets without relying on git history alone.

Export files (PPTX/XLSX) stay under `public/board/exports/` and are copied separately via `npm run copy:board-exports`.
