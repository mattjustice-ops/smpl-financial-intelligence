# Visual design workflow — Claude + Cursor

SMPL uses two complementary surfaces for UI work. Both should stay aligned on the same data model and design tokens.

## Roles

| Tool | Best for | Output |
|------|----------|--------|
| **Claude** (claude.ai or API) | Rapid board-package layouts, chart styling, executive copy, slide navigation, static prototypes | Single-file HTML (`frontend/public/board/index.html`) |
| **Cursor** (this repo) | API-connected platform, GL drilldown, period filters, auth, deployment | Next.js (`frontend/app`, `frontend/components`) + FastAPI |

## Source of truth

- **Public demo / board package:** `frontend/public/board/index.html`  
  Origin: Claude prototype from May 2026 SMPL data. Served at `/board`.
- **Live platform:** `frontend/app/app/` and related components. Served at `/app`. Reads from backend APIs.

When you change visuals in Claude, copy the updated HTML into `frontend/public/board/index.html` (or ask Cursor to diff and port specific sections).

When you change visuals in the live platform, reference the board HTML for spacing, colors, and chart treatment.

## Shared design tokens

From the board HTML `:root` block — use these in React/Tailwind when porting:

```
--teal: #1D9E75
--navy: #1a2e44
--blue: #185FA5
--red: #D85A30
--amber: #BA7517
--gray: #888780
--serif: Fraunces
--mono: DM Mono
```

Fonts: [Fraunces](https://fonts.google.com/specimen/Fraunces) (headlines), [DM Mono](https://fonts.google.com/specimen/DM+Mono) (metrics).

## Recommended loop

1. **Prototype in Claude** — Paste a section spec or screenshot + sample numbers. Ask for HTML/CSS/Chart.js matching SMPL tokens.
2. **Drop into repo** — Replace or merge `frontend/public/board/index.html`.
3. **Port to platform in Cursor** — Reference the HTML file: *"Match the OpEx stack chart in `public/board/index.html` exec slide."*
4. **Wire data** — Backend services already compute from GL; frontend consumes `/api/v1/...` routes.

## Prompt template for Claude (visual changes)

```
You are updating the SMPL board platform HTML prototype.

Constraints:
- Keep :root design tokens (teal #1D9E75, navy #1a2e44, Fraunces + DM Mono)
- Chart.js only, no build step
- Embedded data objects (SD, TS_DATA, GTM, etc.) — do not break existing keys
- Static commentary must remain if AI API is unavailable

Task: [describe change — e.g. "add 6th KPI card for Rule of 40 on exec slide"]

Return the full updated HTML file or the changed <style> + <script> sections with clear markers.
```

## Prompt template for Cursor (integrating Claude output)

```
Read frontend/public/board/index.html and [target component].

Port [specific UI element] to React, using existing API data from [endpoint].
Match colors, typography, and chart options from the board HTML.
Do not change backend unless required for data shape.
```

## AI commentary

The board HTML calls `api.anthropic.com` directly from the browser — this **cannot** ship with a secret key.

Options:

1. **Demo mode (current):** Static commentary + friendly error on regenerate.
2. **Production:** Add backend route `POST /api/v1/commentary/generate` (OpenAI already wired) and point board buttons at your API via a thin proxy page later.

## Updating the board demo after Claude edits

```powershell
Copy-Item -LiteralPath "C:\Users\mattj\Downloads\SMPL_Board_Platform_May2026 (1).html" `
  -Destination "frontend\public\board\index.html" -Force
```

Then commit when ready. Vercel redeploy picks up the static file automatically.
