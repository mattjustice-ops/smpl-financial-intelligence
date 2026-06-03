# Board platform demo (static)

May 2026 executive board package — HTML prototype with SMPL sample data.

- **Local:** http://localhost:3002/board
- **Production:** https://smpl-financial-intelligence.vercel.app/board

## Files

| Path | Purpose |
|------|---------|
| `index.html` | Self-contained board dashboard (Chart.js via CDN) |
| `exports/SMPL_Board_Review_May2026.pptx` | **Full MD&A** (top bar) — board review deck |
| `exports/SMPL_MDA_Package_May2026.xlsx` | **Variance Commentary** (footer) |

## Refresh from local sources

```powershell
cd frontend
npm run copy:board-all
```

Or separately:

- `npm run copy:board` — HTML from Downloads `(5).html`
- `npm run copy:board-exports` — PPTX + XLSX from OneDrive

Then commit `index.html` and `exports/*` for Vercel.

## Export buttons

| Button | Opens |
|--------|--------|
| ✦ Full MD&A ↗ (top bar) | `SMPL_Board_Review_May2026.pptx` |
| ✦ Variance Commentary ↗ (footer) | `SMPL_MDA_Package_May2026.xlsx` |

See `docs/VISUAL_DESIGN_WORKFLOW.md` for how this relates to the live `/app` platform.
