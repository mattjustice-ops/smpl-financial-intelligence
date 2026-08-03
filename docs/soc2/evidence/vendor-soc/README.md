# Vendor SOC / ISO report collection

**Purpose:** Track and store evidence that SMPL reviewed material subprocessors’ independent assurance reports (SOC 2, ISO 27001, etc.) per [P09](../../policies/P09_vendor_subprocessor_management.md) and the named list in [02_subprocessors.md](../../02_subprocessors.md).

**Status (2026-08-03):** Public Trust Center research pass complete for P0 + GitHub — see [TRACKER.md](./TRACKER.md) + [PUBLIC_RESEARCH_2026-07-29.md](./PUBLIC_RESEARCH_2026-07-29.md). **No Type II reports received.** Public Stripe SOC 3 summary only (gitignored `private/`). This-week execution: [WORKING_PACK_2026-08.md](./WORKING_PACK_2026-08.md). Readiness only — not SOC 2 certified.

Parent scoreboard: [../../PROGRESS.md](../../PROGRESS.md) · Tracker: [TRACKER.md](./TRACKER.md) · Working pack: [WORKING_PACK_2026-08.md](./WORKING_PACK_2026-08.md) · Session kit: [SESSION_CHECKLIST_2026-07-31.md](./SESSION_CHECKLIST_2026-07-31.md) · Review: [REVIEW_CHECKLIST.md](./REVIEW_CHECKLIST.md) · Templates: [REQUEST_TEMPLATES.md](./REQUEST_TEMPLATES.md)

---

## What belongs here (in git)

| Artifact | Commit? | Notes |
|----------|---------|--------|
| This README, [TRACKER.md](./TRACKER.md), [REQUEST_TEMPLATES.md](./REQUEST_TEMPLATES.md), working pack, session kit, review checklist | **Yes** | Process + status only |
| Redacted review notes (date reviewed, report type/period, exceptions noted, “OK for use”) | **Yes** | Prefer markdown; no customer data, no NDA-secret excerpts |
| Links to Trust Centers / portals | **Yes** | Already in the tracker |
| Full SOC / ISO **PDFs**, bridge letters, pentest packs under NDA | **No** | See storage rules below |
| NDA countersignatures, portal credentials, API keys | **No** | Never |

---

## Where to store proprietary PDFs (outside git)

Vendor SOC 2 Type II reports and most ISO certificates are **confidential / NDA-bound**. Do **not** commit binaries into this repo.

**Preferred storage (pick one and stick to it):**

1. **Local / Drive folder (recommended):**  
   `~/Documents/SMPL/soc2/vendor-reports/` (or equivalent OneDrive/Google Drive path **outside** the git working tree)  
   Naming: `YYYY-MM-DD_<vendor>_<report-type>_period-YYYY-YYYY.pdf`  
   Example: `2026-08-05_neon_soc2-type2_2025-01-2025-12.pdf`

2. **Gitignored path inside the repo (optional):**  
   `docs/soc2/evidence/vendor-soc/private/` — gitignored via root `.gitignore`. Use only if you want files near the tracker; still treat as NDA material. Prefer option 1 so clones never risk leaking PDFs.

3. **Never:** commit PDFs to git, attach full reports to public issues/PRs, or paste report text into committed markdown.

After downloading a report, update [TRACKER.md](./TRACKER.md): status → `received` / `reviewed`, date, report period, and a short note. Optionally add a one-line entry in a `REVIEW_NOTES.md` (sanitized) — do not paste exception tables or auditor findings verbatim if the NDA forbids redistribution.

---

## Collection workflow (Matt)

1. Open [TRACKER.md](./TRACKER.md) — priority = **product Customer Data** vendors first (Vercel, Railway, Neon, Resend, Anthropic, Stripe, GitHub).
2. Use [REQUEST_TEMPLATES.md](./REQUEST_TEMPLATES.md) (or the portal’s built-in NDA/request form).
3. Sign vendor NDA / click-through in the Trust Center if required.
4. Download PDF to the **private** store (not git).
5. Skim: report type, period end date, scope matches how SMPL uses the service, material exceptions.
6. Update tracker status + date; mark “vendor report collected?” in [02_subprocessors.md](../../02_subprocessors.md) only after a real review.
7. Annual re-pull (or on material change) — P09 cadence.

**Honest statuses only:** `not started` → `researched` / `public summary available` → `requested` → `nda signed` → `received` → `reviewed`. Public SOC 3 / marketing pages are **not** Type II `received`. Do not mark reviewed without a file in the private store and a date.

---

## Priority tiers

| Tier | Vendors | Why |
|------|---------|-----|
| **P0 — product Customer Data** | Vercel, Railway, Neon, Resend, Anthropic, Stripe | On product DPA exhibit ([02_subprocessors.md](../../02_subprocessors.md)) |
| **P1 — CI / secrets adjacency** | GitHub | Code + CI; may hold secrets config; not customer warehouse |
| **P2 — inventory / questionnaires** | Sanity (marketing), Squarespace (DNS), Google (corporate email / IdP) | Not product Customer Data subprocessors; useful for access inventory + security questionnaires |
| **Skip for now** | HubSpot (sales CRM), OpenAI (not live) | Per Matt Q1–Q10 2026-07-28 |

Auth.js is application software on Vercel — **not** a separate vendor report target.
