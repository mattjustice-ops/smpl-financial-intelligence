# SMPL Board Platform — June 2026 (live)

Static executive board at `/board` and embedded in `/app/board`.

## Source of truth

**Committed files in this repo** — not Downloads or Claude export copies.

| Path | Role |
|------|------|
| `index.html` | Board UI + embedded demo dataset |
| `us_emea_basemap.svg` | Sales territory map geography |
| `../shared/board-data.js` | Canonical KPI/series formatters |
| `../shared/board-hydrate.js` | Live warehouse hydration |
| `../shared/smpl-demo-seed.js` | Demo seed for forecast alignment |

## If something breaks

From `frontend/`:

```powershell
npm run reset:platform
npm run verify:platform
```

That restores board, forecast engine, and shared dataset files from `frontend/canonical/`.

## After a good fix

```powershell
npm run snapshot:platform
```

Then commit `frontend/canonical/` so the new state becomes the fallback.

## Export buttons (MD&A deck / variance workbook)

```powershell
npm run copy:board-exports
```

Set `SMPL_BOARD_PPTX_SRC` / `SMPL_MDA_XLSX_SRC` in `.env.local` if files are not in the default OneDrive/Downloads paths.

## Deploy

```powershell
npm run verify:platform
npx vercel@latest --scope smplai --project smpl-financial-intelligence deploy --prod --yes
```

Hard refresh after deploy (`Ctrl+Shift+R`).
