# Sales Talk Track (live meeting aide)

Personal / sales meeting aide for SMPL founders and sales: **someone asks a question → the browser mic hears it → a vetted KB answer card appears** (or a deflect card if uncovered). It is **not** the in-product finance Copilot (`/copilot` warehouse features).

## Open it

| Environment | URL |
|---|---|
| Local | `http://localhost:3002/app/sales-talk` |
| Production | `https://<your-frontend-host>/app/sales-talk` |

Auth: same gate as Ops — signed-in user whose email is in `SMPL_OPS_ADMIN_EMAILS` (in local `NODE_ENV=development`, any signed-in user is allowed if that env var is empty).

Also linked from **Ops** → “Sales Talk Track”.

## How to use in a live call

1. Open Chrome on desktop (best Web Speech support).
2. Go to `/app/sales-talk`, pick **Audience mode** (CFO, Investor, etc.).
3. Click **Start listening** and allow the microphone.
4. **Disclose** to the room that an AI assistant is running for notes/reference.
5. When a prospect asks something question-like, a card appears:
   - **Verified / Directional** — sayable answer from the KB
   - **Deflect / No prepared answer** — use the script; never invent numbers
6. **Pause** when you need silence; **Clear** resets transcript + cards.
7. If detection misses, use the small **Manual trigger** box (secondary only).

Optional: press **Space** (when not typing in an input) to start listening if paused.

## Privacy & STT caveat

- This app does **not** persist audio to disk.
- The rolling transcript is **in-memory / session-only** in the browser tab.
- Browser **Web Speech API** may send audio to the vendor’s cloud speech service (commonly Google in Chrome, Apple on Safari). Treat sensitive investor/customer calls accordingly.
- Electron + local Whisper / system loopback is intentionally out of scope for this MVP; revisit if Web Speech quality or privacy is insufficient.

## Knowledge base

File: `frontend/content/sales-kb/knowledge_base.json`

Each entry:

| Field | Notes |
|---|---|
| `id` | Stable id (shown on cards) |
| `title` | Card title |
| `topics` / `keywords` | Retrieval matching |
| `answer` | Sayable text (source of truth) |
| `confidence` | `verified` \| `directional` \| `do-not-answer` |
| `audiences` | Optional: `cfo` \| `it` \| `fpa` \| `ceo` \| `engineer` \| `investor` \| `general` |
| `tone` | `external_safe` (default) or `internal_deep` |
| `deflect_script` | For `do-not-answer` entries |
| `source` | Provenance note |

Governance / freeze / lock detail lives in `governance-workflow-internal` (`internal_deep`). Customer-facing close language is `governance-workflow` (`external_safe`).

### Adding an entry

1. Append an object to `entries` with the fields above.
2. Prefer `external_safe` for anything said to customers/investors.
3. Use `do-not-answer` + `deflect_script` until a number is locked.
4. Redeploy / refresh — no code change required for new entries.

## Retrieval & rephrase

- Keyword scoring over title, topics, keywords, answer (no embeddings).
- Filters by audience when set; prefers `external_safe` unless **Include internal deep** is on.
- Below threshold → **No prepared answer** (fail closed).
- Optional Anthropic rephrase (`ANTHROPIC_API_KEY` on the Next server): rewrites matched KB text for the audience only — **must not add facts**. No key / failure → raw KB text.

API: `POST /api/sales-talk/answer` (Ops-admin auth).

## Difference from product Copilot

| | Sales Talk Track | Product Copilot |
|---|---|---|
| Purpose | Live sales/investor talk track | In-product finance Q&A over tenant data |
| Grounding | Vetted sales KB JSON | Warehouse / reporting context |
| Route | `/app/sales-talk` | Product `/copilot` surfaces |
| Audio | Browser mic + Web Speech | N/A |

Do not merge these codepaths.
