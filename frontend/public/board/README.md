# Board platform demo (static)

June 2026 executive board package — HTML prototype with SMPL sample data.

- **Local:** http://localhost:3002/board
- **Production:** https://smpl-financial-intelligence.vercel.app/board

## Files

| Path | Purpose |
|------|---------|
| `index.html` | Self-contained board dashboard (Chart.js via CDN) |
| `us_emea_basemap.svg` | Pre-rendered territory map geography (Natural Earth / world-atlas) |
| `projection_params.json` | Verified D3 projection for pin placement |
| `pin_coordinates.json` | Reference pin positions for the four territories |
| `exports/SMPL_Board_Review_Q2_2026.pptx` | **MD&A Deck** (top bar) |
| `exports/SMPL_MDA_Package_June2026.xlsx` | **Variance Commentary** (top bar) |

## Refresh from local sources

```powershell
cd frontend
npm run update:board-june
```

Or separately:

- `npm run copy:board` — HTML from Downloads `(6).html` (patches export URLs + top bar)
- `npm run copy:board-exports` — PPTX + XLSX from OneDrive/Downloads

Then commit `index.html` and `exports/*` for Vercel.

## Territory map basemap

The Sales → Region Map tab loads `us_emea_basemap.svg` (verified coastlines) and overlays live pins from board data. Copy the asset once if missing:

```powershell
python scripts/copy-basemap.py
```

Source: `Downloads/us_emea_basemap.svg` from the territory map handoff package.

## Export buttons

| Button | Opens |
|--------|--------|
| ✦ MD&A Deck ↗ (top bar) | `SMPL_Board_Review_Q2_2026.pptx` |
| ✦ Variance Commentary ↗ (top bar) | `SMPL_MDA_Package_June2026.xlsx` |

See `docs/VISUAL_DESIGN_WORKFLOW.md` for how this relates to the live `/app` platform.
