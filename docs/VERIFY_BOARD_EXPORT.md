# Verify you are running the NEW board export engine

If the deck looks unchanged, the API process is almost certainly serving **old code** or you are opening an **old downloaded file**.

## 1. Backend must show engine on startup

Restart API:

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence\backend
.\start-api.ps1
```

In that terminal you should see:

```text
[SFI] Board presentation engine: smpl-board-v2
```

If you do **not** see that line, you are not running this repo's `backend` folder.

## 2. Ping endpoint (browser)

Open:

http://127.0.0.1:8000/api/v1/export/ping

Expected JSON:

```json
{
  "status": "ok",
  "service": "export",
  "board_engine": "smpl-board-v2",
  "pipeline": "reporting.export.board_slides",
  "executive_slide_layout": "executive_scorecard",
  "marketing_channels_layout": "marketing_source"
}
```

If `board_engine` is missing or different → wrong server or stale process.

## 3. Frontend toolbar

After refresh http://localhost:3002, the export panel should show:

`API: http://127.0.0.1:8000 · board engine: smpl-board-v2`

Export Board Package again. After success:

`Last board export engine: smpl-board-v2`

If export **fails** with "OLD API build" — follow step 1 (restart correct backend).

**Note:** Browsers hide custom response headers unless CORS exposes them. The app now exposes `X-Board-Package-Engine`; restart **both** backend and frontend after pulling this fix.

## 4. Visible proof inside the .pptx

Every slide (including cover) should have bottom-right gray text:

`SMPL · smpl-board-v2`

Cover subtitle includes: `Engine smpl-board-v2`

Executive summary slide should be **split layout**:

- Left: CM / QTD / YTD / FY Outlook table
- Right: orange **Key takeaways** + bullets
- Bottom: ARR trajectory chart (when data exists)

Marketing channels: **wide table left**, orange commentary **right** (not full-width table only).

## 5. Local script (optional)

```powershell
cd backend
.\.venv\Scripts\python.exe .\scripts\verify_board_export.py
```

Writes `docs/reference-decks/_verify_output.pptx` and prints each slide `layout=`.

## Wrong repo?

Confirm `start-api.ps1` prints Python from:

`...\saas-financial-intelligence\backend\.venv\Scripts\python.exe`

not another clone path.
