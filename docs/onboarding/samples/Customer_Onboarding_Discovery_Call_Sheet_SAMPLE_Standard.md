# Customer Onboarding — Discovery Call Sheet

**SAMPLE — illustrative only; not a real customer.**  
**Persona:** Acme Analytics (standard / straightforward SaaS)  
**Filled for:** showing customers what complete, decision-ready answers look like  
**Audience:** Implementation / CS (customer-facing)  
**Use:** First discovery call attachment or Notion paste  
**Principle:** Under ~15 minutes on first pass — ask only what systems cannot discover.  
**Source of truth for formal fields:** Customer Environment Profile (CEP / ABS-009) v1.0

---

## How to use this sheet

| Label | Meaning |
|-------|---------|
| **CEP** | Documented Customer Environment Profile field — safe to treat as formal onboarding |
| **Gate** | Concrete ARR / subscription decision from GPES + Billing CKR — blocks ARR until answered |
| **Recommended** | Reconstructed from product methodology docs — **not yet a formal CEP field**; do not over-claim |
| **Readiness gate** | Books-quality prerequisite (Section 0). If any gate fails, onboarding pauses — no Readiness Score is produced until the customer resolves it |
| **Score input** | Accounting-policy answer that sets module status (READY / PARTIAL / UNAVAILABLE) in the Readiness Score and names the improvement path |

**Do not ask on this call:** API scopes, auth methods, field mappings, custom fields, pipeline inventories, currencies, org hierarchies — those are auto-discovered after connect.

**Capture style:** Decision + owner (who confirmed) + date. Prefer “accept SMPL default” over inventing policy on the fly.

**Sample capture metadata**

| Field | Value |
|-------|-------|
| Call date | 2026-03-12 |
| Confirmed by | Priya Shah (VP Finance) |
| Also present | Jordan Lee (RevOps), Alex Chen (Controller) |
| Day-1 ARR intent | Single canonical ARR (Board = Operational) |

---

## Data ownership — read this first

> **You own your data and the process that creates it.** SMPL reports on what your books and source systems contain. We do not reconcile, reclassify, rebuild, or post entries on your behalf.
>
> What SMPL does:
> - Tells you exactly what each report needs from your books and systems.
> - Flags gaps during discovery and the systems review, along with what each gap will mean for your reporting.
> - Recommends ways to improve your process, if you ask.
>
> Where a gap comes from how data is recorded, closing it is an action for your team. Reports reflect your books as recorded — gaps show up as labeled limitations, not as numbers SMPL has adjusted. If the readiness gates in Section 0 are not met, onboarding pauses until they are.

---

## 0. Readiness gates *(Readiness gate — Recommended)*

> Ask first. A “No” on any gate means SMPL cannot produce reliable reporting from the books as they stand. Record the answer, explain why, and agree to revisit once the customer has resolved it. Do not work around a failed gate.

| # | Gate question | Required | Customer answer |
|---|---------------|----------|-----------------|
| 0.1 | Are the books kept on an **accrual basis** (not cash or tax basis)? | Yes | **Yes — accrual**, ASC 606 revenue. Outside CPA prepares tax return from the same books. |
| 0.2 | Which **single book of record** should SMPL report from? Who owns it? | One named book + owner | **QuickBooks Online Advanced (GAAP)** — owned by Alex Chen (Controller). No separate tax or investor copy. |
| 0.3 | Are the books **closed monthly**, with a named close owner and a target close day? | Yes | **Yes** — Alex Chen; hard close BD+5 (see 7.1). |
| 0.4 | Can the finance lead walk through the most recent month’s income statement and explain the material lines? | Yes | **Yes** — Priya walked Feb 2026 IS on the call. |
| 0.5 | Does the customer accept the data-ownership terms above? | Yes | **Yes** — Priya Shah, 2026-03-12. |

**Gate result: PASS.**

---

## 1. Company overview *(CEP)*

| # | Question | Notes / answer |
|---|----------|----------------|
| 1.1 | Company name (legal or preferred operating)? | **Acme Analytics, Inc.** (operating name: Acme Analytics) |
| 1.2 | Industry? | B2B SaaS — product analytics / BI for mid-market |
| 1.3 | Business model? | **SaaS subscription** (annual and monthly seats). No metered usage billing today. Professional services are rare (<5% of revenue) and booked separately — not in ARR. |
| 1.4 | Headquarters? | Austin, TX, USA |
| 1.5 | Operating countries / entities? | **Single legal entity** (Acme Analytics, Inc.). Customers mostly US/Canada; a few UK logos billed in USD. |
| 1.6 | Primary reporting currency? | **USD** — all FI / board reporting in USD |
| 1.7 | Approximate revenue range? | ~$18–22M ARR |
| 1.8 | Approximate employee count? | ~95 W-2 employees |
| 1.9 | Fiscal year end? | **December 31** (calendar year) |

---

## 2. Connected systems *(CEP)*

For each relevant system (ERP, CRM, Billing, HRIS, Payroll, Planning, Data Warehouse, BI, other):

| System type | 2.1 Vendor | 2.2 Version (if known) | 2.3 Primary business owner | 2.4 Implementation contact |
|-------------|------------|------------------------|----------------------------|----------------------------|
| Billing | **Stripe** Billing | Current (cloud) | Priya Shah (VP Finance) | Morgan Blake (Finance Systems) |
| CRM | **HubSpot** Sales Hub | Enterprise | Jordan Lee (RevOps) | Jordan Lee |
| ERP / GL | **QuickBooks Online** Advanced | Current | Alex Chen (Controller) | Morgan Blake |
| HRIS / Payroll | **Rippling** | Current | Dana Ortiz (People Ops) | Dana Ortiz |
| Planning | Google Sheets + annual board budget workbook | N/A | Priya Shah | Priya Shah |
| BI | HubSpot dashboards + Looker Studio (light) | N/A | Jordan Lee | — |
| Data Warehouse | None in Day 1 scope | — | — | — |

Skip technical connector detail here.

---

## 3. Business definitions *(CEP)*

Customer-specific definition **or** accept SMPL standard default:

| # | Metric / concept | Decision (custom / SMPL default) |
|---|------------------|----------------------------------|
| 3.1 | Active Customer | **SMPL default:** paying account with at least one non-canceled, non-trial subscription. Parent company = one customer (no multi-entity complexity). |
| 3.2 | **ARR** | **SMPL default / single intent:** annualized recurring subscription revenue from active paid subscriptions. Exclude one-time fees, PS, and trials. Canonical for Board, Investor, and Operational reporting Day 1. |
| 3.3 | **MRR** | ARR ÷ 12. Same inclusion rules as ARR. |
| 3.4 | Churn | Logo or ARR lost when subscription cancels / is not renewed. Report both logo churn and gross ARR churn. |
| 3.5 | Expansion | Net increase in ARR from existing customers (upsell seats / plan upgrades) in period. |
| 3.6 | Contraction | Decrease in ARR from existing customers still active (downgrades / seat reductions), separate from full churn. |
| 3.7 | Renewal | Same-customer continuation at renewal date; price increases at renewal count as expansion, not new logo. |
| 3.8 | Bookings | Closed-won ACV from HubSpot; expected to tie to Stripe new/expansion ARR within ~5% monthly (RevOps owns recon). |
| 3.9 | Qualified Pipeline | HubSpot stages **Proposal Sent** and later (weighted pipeline for forecast). |
| 3.10 | Active Employee | Rippling status = Active (W-2). |
| 3.11 | Contractor | 1099 / external; **excluded** from headcount metrics Day 1 (see 5.7). |
| 3.12 | FTE | Headcount count (1.0 per active employee); part-timers rare — treat as 1.0 if Active. |

**Also ask *(CEP + FIE intent):*** Do you report more than one ARR to different audiences (e.g. Board / Investor / Operational / Sales)? If yes, which is canonical for SMPL Day 1?

**Answer:** **No.** One ARR definition for board, investors, and ops. Sales ACV in HubSpot is bookings, not a second ARR. Canonical Day 1 = SMPL ARR from Stripe. Confirmed: Priya Shah, 2026-03-12.

**Also ask *(Recommended — Score input):*** Do you report **adjusted profitability metrics** (e.g. Adjusted EBITDA, contribution margin) differently by audience? For each, capture the audience, the add-backs, and who owns the definition. All versions come from the same book of record plus documented adjustments — SMPL does not keep separate P&L copies.

| Audience | Metric name | Add-backs / adjustments | Definition owner |
|----------|-------------|-------------------------|------------------|
| Internal management | EBITDA | None — reported EBITDA | Priya Shah |
| Investor / board | EBITDA (same) | None today; may add back stock comp in 2027 | Priya Shah |
| Lender / covenant | N/A | No debt facility | — |

---

## 4. ARR / subscription policy decisions — hard gates *(Gate)*

These come from the **Subscription Normalization Gate** (GPES Stripe reference + Billing CKR). ARR Movement is blocked until resolved. Defaults below are SMPL defaults — confirm explicitly; trial treatment is the most common ARR disagreement.

| # | Gate question | SMPL default | Customer answer |
|---|---------------|--------------|-----------------|
| 4.1 | Include **trialing** subscriptions in ARR? | **Exclude** | **Accept SMPL default — Exclude.** Trials convert before counting. Confirmed: Priya / Jordan, 2026-03-12. |
| 4.2 | Include **past_due / unpaid** subscriptions in ARR? | **Exclude** | **Accept SMPL default — Exclude.** Collections works ~14 days; ARR drops when Stripe moves past_due until paid. Confirmed: Alex Chen. |
| 4.3 | **Usage-based ARR policy** (only if metered pricing exists): are committed minimums in ARR? Uncommitted overages? | N/A if no metered pricing | **N/A — no metered / usage pricing.** Seat-based only. |
| 4.4 | If usage exists: pricing method? | per-unit / tiered / volume | **N/A** |

**Related billing decisions *(Gate / Billing CKR Implementation Decision Flow):***

| # | Question | Answer |
|---|----------|--------|
| 4.5 | Is Billing the authoritative source for subscriptions, or is there a separate CPQ / contract system? | **Stripe is authoritative** for subscriptions and ARR. HubSpot is CRM / opportunities only (no CPQ). DocuSign for MSA; commercial terms live in Stripe. |
| 4.6 | Multiple subscription items / add-ons — how should they aggregate into ARR? | Sum all recurring line items on the subscription (base plan + add-on modules). One-time onboarding SKUs excluded. |
| 4.7 | Multiple billing accounts / sites (regional / product) — consolidation strategy? | **Single Stripe account**, live mode only. One consolidation = company total. |
| 4.8 | Non-card methods (ACH / invoice) present? Settlement lag / banking pairing needed? | Mostly card; ~20% ACH / invoice for mid-market. Settlement lag accepted in cash forecast defaults; no special banking pairing required Day 1. |
| 4.9 | Live-only data confirmed (exclude test / sandbox)? | **Yes — live only.** Sandbox never used for reporting. Expect Stripe `livemode` filter. |
| 4.10 | Reactivation vs New Business dormancy window? | **Accept SCBM default 90 days.** Return within 90 days = reactivation; after 90 = new logo. |

---

## 5. Business policies *(CEP)*

| # | Policy | Decision |
|---|--------|----------|
| 5.1 | Revenue recognition approach | ASC 606 ratable over subscription term. Monthly books close on QuickBooks; deferred revenue rolled by Controller. |
| 5.2 | **ARR methodology** (how annual recurring revenue is calculated) | Annualize recurring Stripe subscription amount: monthly × 12; annual contracts at contract ARR. No usage component. Point-in-time ending ARR each month-end. |
| 5.3 | Usage-based billing — exists? how treated in reporting? | **Does not exist.** Aligns with gate 4.3 N/A. |
| 5.4 | Trial handling | 14-day trials in Stripe; **excluded from ARR** until converted to active paid. Aligns with 4.1. |
| 5.5 | Renewal treatment (vs new bookings) | Auto-renew default. Renewal of same ARR = renewal movement; uplift at renewal = expansion. New logo only for new customer IDs. |
| 5.6 | Cancellation policy (impact on churn / ARR) | ARR removed at effective cancel / period end (not at notice date). Mid-term cancels rare; when they happen, ARR drops on cancel effective date. |
| 5.7 | Contractor policy (included in headcount metrics?) | **Exclude contractors** from HC / FTE metrics Day 1. Contractor spend stays in opex (GL), not HC. |
| 5.8 | Department ownership rules (cost / spend attribution) | Departments: GTM, Product Eng, G&A, CS. Owner = department head; finance maps QBO classes → departments. |
| 5.9 | Cost center ownership rules | QBO Classes ≈ cost centers; one primary class per employee in Rippling. |
| 5.10 | Multi-entity reporting rollup | **N/A — single entity.** |

### System of authority *(CEP)*

Which connected system is authoritative for each:

| Concept | System of record |
|---------|------------------|
| Customer | HubSpot (company) ↔ Stripe customer (billing id); Stripe wins for “paying customer” |
| Product | Stripe Products / Prices |
| Employee | Rippling |
| Department | Rippling + QBO Class mapping |
| Cost Center | QuickBooks Online Class |
| Opportunity | HubSpot |
| Subscription | **Stripe** |
| Invoice | Stripe (billing); QBO for accounting invoices / AR |
| Revenue | QuickBooks Online (recognized); Stripe for ARR/MRR |
| Headcount | Rippling |
| Compensation | Rippling |

---

## 6. Forecasting methodology *(Recommended — not formal CEP)*

> **Recommended addition.** CEP lists Cash Forecasting / Scenario Planning as desired modules only. There is no dedicated forecast-driver interview in CEP v1.0. Questions below are reconstructed from `docs/Forecasting_Assumptions.md` and related methodology docs for call use — do not present them as frozen CEP fields.

### How they forecast today

| # | Question | Answer |
|---|----------|--------|
| 6.1 | Who owns Forecast vs Budget vs Actual? | **Budget:** Priya (annual board). **Forecast:** Priya + Jordan (monthly reforecast). **Actual:** Alex (Controller) certifies close. |
| 6.2 | Combined cutover date (when Actual ends and Forecast begins)? | Month-end after books close (target BD+5). e.g. after Feb close certified, Forecast begins Mar 1. |
| 6.3 | Method today: driver-based, spreadsheet judgment, CRM pipeline-weighted, or mix? | **Budget + judgment.** Annual budget in Sheets; monthly forecast = budget ± judgment using HubSpot pipeline as a check, not a mechanical model. |
| 6.4 | Which scenarios do you need (Forecast / Budget / Upside / Downside)? | Day 1: **Forecast** and **Budget** only. Upside/Downside Phase 2. |
| 6.5 | How often do you refresh? What happens after close (Actual ending → next Forecast beginning)? | Refresh monthly after close. Actual locks; next month Forecast starts from certified ending ARR, cash, HC. |

### Drivers to confirm (map to platform assumptions)

| Area | Drivers confirmed |
|------|-------------------|
| Revenue / subscriptions | New logo ARR growth ~$150–200k/mo; expansion ~8% of starting ARR/quarter; gross churn target ~1.2%/mo; NRR ~110%; typical term **12 months**; little ramp (recognize ratably from start). |
| Pipeline / bookings | Stage win rates maintained in HubSpot; ASP ~$18k ACV mid-market; sales cycle ~45–60 days; pipeline coverage target 3×; closed-won ↔ Stripe new ARR recon by RevOps monthly. |
| Billings / rev rec | Mostly annual prepaid; PS <5% — exclude from ARR drivers. |
| Cash | DSO ~25 days (card-heavy); DPO ~30; min cash balance board target $4M. |
| Headcount / opex | Hiring plan by dept in annual budget; attrition ~12% annual; fully loaded cost from Rippling + burden %. |
| Marketing | Funnel used directionally; CAC payback tracked in Sheets — nice-to-have in SMPL, not blocking. |

---

## 7. Close / GL / data readiness *(Recommended — not formal CEP)*

> **Recommended addition.** Reconstructed from close / GL / reporting methodology docs. Useful for implementation blockers; not listed as CEP fields in v1.0.

| # | Question | Answer |
|---|----------|--------|
| 7.1 | Close calendar / SLA (e.g. business-day close)? | Soft close **BD+3**, hard close **BD+5**. Board pack BD+8. |
| 7.2 | First period of GL history available? Opening trial balance + ending retained earnings at cutoff? | QBO history from **Jan 2023**. Will provide TB + ending RE at SMPL cutoff month (implementation kickoff month-end). Simple single-entity — no RE_BASE complexity expected. |
| 7.3 | Chart of accounts → management reporting lines / EBITDA mapping? | Yes — existing board P&L mapping in Sheets (QBO accounts → Revenue, COGS, S&M, R&D, G&A, EBITDA). Will share workbook. |
| 7.4 | Multi-entity structure? Dept vs cost center mapping ready? | Single entity. Dept ↔ QBO Class mapping documented by Controller (1-pager). |
| 7.5 | Validation sources for ending ARR, revenue, headcount (what do you tie to today)? | ARR: Stripe Dashboard + RevOps workbook. Revenue: QBO P&L. HC: Rippling headcount report. |
| 7.6 | Who certifies Actual each month (Accounting / FP&A / RevOps)? | **Alex Chen (Controller)** certifies Actual; Priya signs off Forecast; Jordan signs ARR tie-out. |

### Accounting policy & close practice *(Score input — Recommended)*

> Each answer sets module status in the Readiness Score. The consequence column is what to tell the customer if the practice isn’t in place. **Customer action** means their team changes how data is recorded. **SMPL connector** means connecting another system closes the gap. SMPL never closes a gap by adjusting the customer’s data.

| # | Question | If not in place — reporting consequence | Improvement path | Answer |
|---|----------|------------------------------------------|------------------|--------|
| 7.7 | **Cost of revenue policy** — which costs, who approved? | Management P&L gross margin **PARTIAL** | Customer action | **In place.** AWS hosting, Support team payroll, third-party tools embedded in the product (Auth0, Segment). Approved by Priya Shah (VP Finance), documented in close binder. |
| 7.8 | **Payroll posted by department / cost center?** | Labor can’t be split; gross margin **PARTIAL** | Customer action | **Yes.** Rippling posts payroll JE by QBO Class (department). Support class maps to cost of revenue. |
| 7.9 | Shared-cost **allocations** — booked as JEs or kept outside the GL? | Allocations not shown | Customer action | **None.** No allocations today; costs sit where booked. Management P&L = income statement categories. |
| 7.10 | Expenses **accrued monthly**? | Timing swings; commentary confidence lowered | Customer action | **Mostly.** Vendor bills accrued monthly. **Exception:** contractor invoices booked when paid (see F1). |
| 7.11 | Accruals **reverse** next period, actuals coded to the same account / department? | Missing leg reported as a data gap | Customer action | **Yes** — QBO auto-reversing JEs; Alex codes actuals to the accrual’s account and class. |
| 7.12 | **Usage-based vendors** accrued on estimate and trued up? | True-ups show as unexplained swings | Customer action | **Yes** — AWS accrued from Cost Explorer estimate at BD+2, trued up on invoice. |
| 7.13 | **Year-end review adjustments** — restate or book to final month? Prior commentary? | Board history **PARTIAL** | Customer action | CPA **review** (not audit). Adjustments booked to **December**; prior months not restated. Board commentary for December notes the adjustments. |

---

## 8. Desired modules *(CEP)*

Select for implementation roadmap:

| Module | Include? (Y/N / Phase 2) |
|--------|--------------------------|
| Financial Reporting | **Y** |
| Board Reporting | **Y** |
| Executive Dashboards | **Y** |
| Cash Forecasting | **Y** (simple) |
| ARR Reporting | **Y** |
| MRR Reporting | **Y** |
| Pipeline Analytics | **Y** |
| Workforce Planning | Phase 2 |
| Scenario Planning | Phase 2 |
| Executive Commentary | Phase 2 |

---

## 9. Optional — CRM stages / headcount *(Gate examples from GPES)*

Ask only if CRM or HRIS is in scope and ambiguity appears after (or before) connect.

| # | Question | Answer |
|---|----------|--------|
| 9.1 | For any ambiguous CRM stage: does it mean Proposal vs Negotiate (or equivalent)? | HubSpot **Contract Sent** = Proposal (late stage). **Negotiation** is a separate stage after Contract Sent. No custom ambiguity beyond that. |
| 9.2 | Which employment statuses count as active headcount — Active only, or Active + Leave of Absence? | **Active only** Day 1. LOA excluded from HC metrics. |
| 9.3 | Should contractors be included in headcount? | **No** (aligns with 5.7). |
| 9.4 | Allocate employee costs to GL cost centers for Department Expense Forecasting? | Yes when Workforce / dept expense forecasting turns on — **Phase 2**. Rippling dept → QBO Class already mapped. |

---

## 10. Platform access acknowledgment *(Recommended)*

> SMPL assumes that everyone the customer gives platform access to may see the information being reported **and the detail underneath it** — including payroll-related GL lines, vendor-level transactions, and department spend. The customer decides who gets access.

| # | Question | Answer |
|---|----------|--------|
| 10.1 | Acknowledged: platform users can see reported numbers and the underlying detail, including payroll-related lines? | **Yes** — Priya Shah, 2026-03-12. |
| 10.2 | Who will get logins? | Finance (Priya, Alex, Morgan), CEO, RevOps (Jordan). Board members receive the exported board pack — **no board logins** Day 1. |
| 10.3 | Who on the customer side approves new access? | Priya Shah. |

---

## 11. Systems & data review — findings and sign-off *(completed after connect)*

> Completed by SMPL after systems connect and the first data pull, then reviewed with the customer’s finance lead. Any failed readiness gate, or any **PARTIAL / UNAVAILABLE** status on a module the customer expects Day 1, must go to SMPL leadership **before** implementation continues. That way the path forward is agreed up front and the resulting reporting limits are understood and signed off.

**Readiness Score summary** *(illustrative)*

| Field | Value |
|-------|-------|
| Readiness gates (Section 0) | **Pass** |
| Overall Readiness Score | **~90%** |
| Modules READY | Financial Reporting, Board Reporting, Executive Dashboards, ARR / MRR Reporting, Pipeline Analytics, Cash Forecasting |
| Modules PARTIAL (and why) | None of the Day-1 modules. Executive Commentary (Phase 2) would be PARTIAL on contractor spend until F1 is fixed. |
| Modules UNAVAILABLE (and why) | None |
| Biggest next improvement and expected score change | Customer action — accrue contractor invoices monthly (F1); small lift, mainly commentary confidence |

**Findings**

| # | Finding | Area (question ref) | Reporting consequence | Path | Customer owner | Target date |
|---|---------|---------------------|-----------------------|------|----------------|-------------|
| F1 | Contractor invoices booked when paid, not accrued | 7.10 | Contractor spend is lumpy month to month; variance commentary flags it as timing rather than explaining it | **Customer action** — accrue contractors monthly from April close | Alex Chen | 2026-05-05 (April close) |

**Sign-off**

| Role | Name | Date |
|------|------|------|
| Customer finance lead (owns books and fixes) | Priya Shah | 2026-03-26 |
| SMPL engagement lead | *(SMPL)* | 2026-03-26 |
| SMPL leadership review | Not required — gates passed, no Day-1 module PARTIAL | — |

---

## Call-time shortlist (~15 min) — how this sample maps

**Must cover (CEP + gates):**  
Covered: data ownership accepted + readiness gates pass → single-entity USD snapshot → Stripe/HubSpot/QBO/Rippling owners → one ARR/MRR/churn set → trials & past_due excluded → no usage → simple ARR methodology → rev-rec & renewal/cancel → SoA → modules → FYE Dec 31.

**Should cover if time:**  
Pipeline stages clear; contractors out of HC; single Stripe live account; cost of revenue policy in place with payroll by class; access acknowledged.

**Recommended extras (label clearly):**  
Forecast = Budget + judgment; monthly refresh after BD+5 close; simple GL history from 2023; no allocations; contractor accrual gap (F1).

---

## Source map

| Content | Source | Status |
|---------|--------|--------|
| Sections 1–3, 5, 8, SoA | `backend/tmp/impl-docs/CEP_v1.0.txt` | Formal CEP |
| Section 4 ARR gates | `backend/tmp/impl-docs/phase3/SMPL_GPES_001_SaaS_Golden_Path_v1.1.txt` + `backend/tmp/impl-docs/SMPL_CKR_Billing_Registry_v0.2.txt` | Formal gate / CKR |
| Section 6 Forecasting | `docs/Forecasting_Assumptions.md` (+ reporting methodology) | **Recommended — not CEP** |
| Section 7 Close / GL | `docs/Close_Process.md`, close/GL readiness materials | **Recommended — not CEP** |
| Section 9 CRM / HC | GPES HubSpot + Rippling gate examples | Documented examples |
| Data ownership, Section 0 gates, 7.7–7.13, Sections 10–11 | SMPL onboarding policy; accounting-quality inputs to the Readiness Score | **Recommended — not CEP** |
| Readiness Score (Section 11) | `backend/tmp/impl-docs/SMPL_AI_Agent_Playbooks_v1.0.txt` (CAL.4–CAL.7) + GPES Stage 7 | Methodology spec |

---

*SAMPLE — fictional customer for illustration. CEP remains the evolving implementation record after systems connect.*
