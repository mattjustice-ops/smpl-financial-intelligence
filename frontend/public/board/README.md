# Board platform demo (static)

June 2026 executive board package — HTML prototype with SMPL sample data.

- **Local:** http://localhost:3002/board
- **Production:** https://smpl-financial-intelligence.vercel.app/board

## Files

| Path | Purpose |
|------|---------|
| `index.html` | Self-contained board dashboard (Chart.js via CDN) |
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

## Export buttons

| Button | Opens |
|--------|--------|
| ✦ MD&A Deck ↗ (top bar) | `SMPL_Board_Review_Q2_2026.pptx` |
| ✦ Variance Commentary ↗ (top bar) | `SMPL_MDA_Package_June2026.xlsx` |

See `docs/VISUAL_DESIGN_WORKFLOW.md` for how this relates to the live `/app` platform.
