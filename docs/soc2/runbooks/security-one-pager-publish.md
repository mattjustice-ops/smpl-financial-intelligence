# Security one-pager — publish checklist (Month 2)

> **Readiness only — not SOC 2 certified.**  
> Source draft: [../SECURITY_ONE_PAGER.md](../SECURITY_ONE_PAGER.md).  
> This checklist does **not** mark the scoreboard item complete until Matt publishes / shares.

## Where it should live for sales

| Channel | Recommendation |
|---------|----------------|
| **Canonical source (now)** | `docs/soc2/SECURITY_ONE_PAGER.md` — share PDF/export or markdown **under NDA** |
| **Public marketing site** | **No dedicated `/security` page exists** today. Do **not** invent a new public page unless product decides to. Prefer NDA share + questionnaire answers. |
| **Related public page** | [https://www.smpl-ai.com/compliance](https://www.smpl-ai.com/compliance) — Type I **progress** scoreboard only; not a substitute for the one-pager and **must not** claim certification |
| **App-internal** | `/app/compliance` mirrors the scoreboard for the team |

## Pre-publish checks

| # | Check | Done? |
|---|--------|-------|
| 1 | Opens with honest “pursuing SOC 2 / not certified” framing | ☐ |
| 2 | No “SOC 2 compliant” / “certified” language | ☐ |
| 3 | Stack names match [01_system_boundary.md](../01_system_boundary.md) | ☐ |
| 4 | Subprocessors summary matches [02_subprocessors.md](../02_subprocessors.md) (no invented vendors) | ☐ |
| 5 | Isolation language: design yes; evidence “ask under NDA” until test Pass | ☐ |
| 6 | AI / Anthropic: keys server-side; not system of record for numbers | ☐ |
| 7 | Export / PDF filename e.g. `SMPL_Security_One_Pager_YYYY-MM.pdf` — store outside git or in sales vault | ☐ |
| 8 | Sales told: share under NDA; link `/compliance` only as progress, not certification | ☐ |

## Publish actions (Matt)

1. Final read of [../SECURITY_ONE_PAGER.md](../SECURITY_ONE_PAGER.md).
2. Export PDF (or paste into sales knowledge base / NDA data room).
3. Optional: add one sentence to sales Trust & Security answers pointing at the PDF.
4. Then mark scoreboard **Security one-pager published for sales** `[x]` and sync `frontend/lib/compliance/progress.ts`.

## Status

**WIP** — draft improved 2026-07-29 for near-publish readiness. **Not published** until Matt completes the actions above.

_Document control: Month 2 prep — do not mark Month 2 item complete from this checklist alone._
