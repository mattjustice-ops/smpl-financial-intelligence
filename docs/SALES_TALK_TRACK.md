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
2. Go to `/app/sales-talk`, pick **Audience mode** (CFO, Investor, IT, etc.).
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
| `topics` / `keywords` | Retrieval matching (add phrasings prospects actually say) |
| `answer` | Sayable text (source of truth) |
| `confidence` | `verified` \| `directional` \| `do-not-answer` |
| `audiences` | Optional: `cfo` \| `it` \| `fpa` \| `ceo` \| `engineer` \| `investor` \| `general` |
| `tone` | `external_safe` (default) or `internal_deep` |
| `deflect_script` | For `do-not-answer` entries |
| `source` | Provenance note |

Governance / freeze / lock detail lives in `governance-workflow-internal` (`internal_deep`). Customer-facing close language is `governance-workflow` (`external_safe`). Prefer `it`, `cfo`, and `general` on security/implementation entries.

### Adding an entry (reminder)

1. Append an object to `entries` in `frontend/content/sales-kb/knowledge_base.json` with the fields above.
2. Prefer `external_safe` for anything said to customers/investors; use `internal_deep` only for sales-internal depth (e.g. named subprocessors, SOC 2 scope path).
3. Use `do-not-answer` + `deflect_script` until a number or claim is locked (TAM, pricing, funding, partner logos, issued SOC 2 report).
4. **Do not invent certifications** — SOC 2 language must stay “pursuing / in progress” until a report is issued (`docs/SMPL_SOC2_Readiness_Reference_v2.md`).
5. Seed `topics` and `keywords` with real prospect phrasings (“how do we trust your security”, “where is data stored”, “SOC2”, “encryption”).
6. Avoid freeze/lock ladder jargon in `external_safe` answers.
7. Redeploy / refresh — no code change required for new entries (retrieval synonym tweaks live in `frontend/lib/sales-talk/retrieve.ts` if needed).

### Security & trust topics covered (KB v2+)

| Theme | Example entry ids |
|---|---|
| Trust / security posture | `security-trust-overview`, `it-questionnaire-overview` |
| Encryption (TLS + at rest) | `encryption-transit-rest` |
| Tenant isolation | `tenant-isolation` |
| No GL / ERP write-back | `no-gl-writeback`, `does-not-replace-erp` |
| Hosting / SaaS model | `hosting-architecture`, `environments-prod-sandbox` |
| Where data is stored | `where-data-stored` |
| Named subprocessors (internal) | `subprocessors-named` (Vercel, Railway, Neon, Resend, Anthropic, Stripe) |
| Auth today + SSO honesty | `auth-magic-link`, `sso-roadmap` |
| SOC 2 honesty | `soc2-status`, `soc2-scope-internal`, `dna-soc2-report` |
| AI data handling / keys | `ai-data-handling`, `ai-keys-server-side` |
| Implementation / onboarding | `implementation-security`, `onboarding-paths`, `white-glove-readonly`, `data-sources-ingest` |
| RBAC / secrets | `rbac-access`, `secrets-cors` |
| Talk-track tool privacy | `talk-track-privacy` |

Still DNA (do not invent): TAM/SAM/SOM, pricing/ACV, funding, named design-partner counts, issued SOC 2 report/certificate.

### Platform features & customization topics covered (KB v2+)

| Theme | Example entry ids |
|---|---|
| Feature overview / what’s included | `platform-features-overview`, `plan-modules-included` |
| ARR/MRR, statements, scenarios | `arr-mrr-reporting`, `three-financial-statements`, `scenarios-actual-budget-forecast` |
| Customization / CoA / per-customer reports | `customize-reporting-per-customer`, `methodology-coa-config`, `customization-at-implementation` |
| Per-org tenant (not inventing private cloud) | `per-org-tenant-environment` |
| Data path honesty (CSV / white-glove vs connectors) | `data-sources-ingest`, `connectors-today-vs-roadmap`, `dna-native-connectors-live` |
| Board / MD&A / AI commentary (no freeze jargon) | `board-deck-and-mda`, `ai-commentary-capabilities` |
| Finance vs executive views | `finance-executive-views` (depth limited — don’t invent RBAC) |
| Boundaries | `what-platform-does-not-do`, `does-not-replace-erp`, `no-gl-writeback` |
| GTM / pipeline / cash / Mgmt P&L | `gtm-pipeline-cash-modules`, `management-pl-and-drilldown`, `dashboards-exports-same-logic` |

Avoid freeze/lock / Prompt 5 jargon in `external_safe` answers when talking close and board packages.

## Retrieval & rephrase

- Keyword scoring over title, topics, keywords, answer (no embeddings), with light synonym expansion (e.g. `soc2` ↔ compliance/encryption phrasings).
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
