# Security one-pager — publish checklist (Month 2)

> **Readiness only — not SOC 2 certified.**  
> Source: [../SECURITY_ONE_PAGER.md](../SECURITY_ONE_PAGER.md).  
> Evidence: [../evidence/security-one-pager-published-2026-07-29.md](../evidence/security-one-pager-published-2026-07-29.md).

## Where sales finds it

| Channel | Location |
|---------|----------|
| **Canonical source** | `docs/soc2/SECURITY_ONE_PAGER.md` — share under **NDA** |
| **NDA PDF export** | `docs/soc2/SMPL_Security_One_Pager_2026-07.pdf` |
| **Publish evidence** | `docs/soc2/evidence/security-one-pager-published-2026-07-29.md` |
| **Public marketing site** | **No** dedicated `/security` page. Do **not** invent one unless product decides to. Prefer NDA share + questionnaire answers. |
| **Related public page** | [https://www.smpl-ai.com/compliance](https://www.smpl-ai.com/compliance) — Type I **progress** scoreboard only; **not** a substitute for the one-pager and **must not** claim certification |
| **App-internal** | `/app/compliance` mirrors the scoreboard for the team |

## Pre-publish checks

| # | Check | Done? |
|---|--------|-------|
| 1 | Opens with honest “pursuing SOC 2 / not certified” framing | ☑ 2026-07-29 |
| 2 | No “SOC 2 compliant” / “certified” language | ☑ 2026-07-29 |
| 3 | Stack names match [01_system_boundary.md](../01_system_boundary.md) | ☑ 2026-07-29 |
| 4 | Subprocessors summary matches [02_subprocessors.md](../02_subprocessors.md) (no invented vendors) | ☑ 2026-07-29 |
| 5 | Isolation language: design yes; readiness Pass evidence shareable under NDA (not certification) | ☑ 2026-07-29 (aligned to tenant isolation Pass) |
| 6 | AI / Anthropic: keys server-side; not system of record for numbers | ☑ 2026-07-29 |
| 7 | Export / PDF filename `SMPL_Security_One_Pager_2026-07.pdf` in `docs/soc2/` | ☑ 2026-07-29 |
| 8 | Sales guidance: share under NDA; link `/compliance` only as progress, not certification | ☑ Documented in one-pager + evidence |

## Publish bar (met 2026-07-29)

**Published for sales** = NDA-ready, versioned, PDF exported, linked from scoreboard / sales pack — **not** requiring a live customer email send.

Completed:

1. Final read of [../SECURITY_ONE_PAGER.md](../SECURITY_ONE_PAGER.md) (honest pursuing language; stack/subprocessors aligned).
2. PDF export at `docs/soc2/SMPL_Security_One_Pager_2026-07.pdf`.
3. Sales findability documented on the one-pager and in evidence.
4. Scoreboard **Security one-pager published for sales** `[x]` + `frontend/lib/compliance/progress.ts` synced.

### Optional (Matt — customer send)

When a prospect asks: attach the PDF (or markdown) **under NDA**; optionally point Trust & Security answers at the PDF. Actual outbound send is optional and does not block the scoreboard item.

## Status

**Complete for sales readiness 2026-07-29** — NDA pack available. **Not** SOC 2 certified. No public `/security` page created.

_Document control: Month 2 — published for sales use under NDA; readiness only._
