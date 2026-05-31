# OpenAI API key setup (Windows)

PowerShell does **not** run lines like `OPENAI_API_KEY=sk-...` — that is only for `.env` files.

## Easiest: paste at prompt

```powershell
cd backend
.\scripts\set-openai-key.ps1
```

Paste your real key from https://platform.openai.com/api-keys (starts with `sk-`).

Then:

```powershell
.\start-api.ps1
```

Expect: `OpenAI: configured`

## Or: save Notepad to a file first

1. In Notepad, **File → Save As** → `C:\Users\mattj\Downloads\openai-key.txt`
2. Put one line: `OPENAI_API_KEY=sk-proj-...` (your real key)

Or import from your saved file:

```powershell
.\scripts\import-openai-key.ps1 -Path "$env:USERPROFILE\Downloads\ChatGPT API Commentary Key.txt"
```
3. Run:

```powershell
.\scripts\import-openai-key.ps1 -Path "C:\Users\mattj\Downloads\openai-key.txt"
.\start-api.ps1
```

## Verify

Open in browser (use **127.0.0.1**, not `localhost` — Windows can route them differently):

http://127.0.0.1:8000/api/v1/export/ping

You must see `"api_build": "openai-ping-v3"` and `"openai_configured": true`. If the JSON is missing `api_build`, the browser is hitting a stale/cached response or the wrong host — run `.\scripts\verify-ping.ps1` in PowerShell while the API is running.

Should include: `"openai_configured": true`
