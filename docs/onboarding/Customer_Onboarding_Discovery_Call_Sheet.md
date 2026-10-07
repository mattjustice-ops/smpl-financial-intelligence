# Customer Onboarding — Discovery Call Sheet

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
| 0.1 | Are the books kept on an **accrual basis** (not cash or tax basis)? | Yes | |
| 0.2 | Which **single book of record** should SMPL report from (e.g. GAAP books — not tax books, a bank-feed spreadsheet, or an investor-adjusted copy)? Who owns it? | One named book + owner | |
| 0.3 | Are the books **closed monthly**, with a named close owner and a target close day? | Yes | |
| 0.4 | Can the finance lead walk through the most recent month’s income statement and explain the material lines? | Yes | |
| 0.5 | Does the customer accept the data-ownership terms above? | Yes | |

---

## 1. Company overview *(CEP)*

| # | Question | Notes / answer |
|---|----------|----------------|
| 1.1 | Company name (legal or preferred operating)? | |
| 1.2 | Industry? | Tunes benchmark / definition defaults |
| 1.3 | Business model? | SaaS subscription / usage-based / hybrid / services |
| 1.4 | Headquarters? | |
| 1.5 | Operating countries / entities? | |
| 1.6 | Primary reporting currency? | Consolidated FI reporting |
| 1.7 | Approximate revenue range? | Order of magnitude only |
| 1.8 | Approximate employee count? | Order of magnitude only |
| 1.9 | Fiscal year end? | Anchors all period reporting |

---

## 2. Connected systems *(CEP)*

For each relevant system (ERP, CRM, Billing, HRIS, Payroll, Planning, Data Warehouse, BI, other):

| # | Question | Notes / answer |
|---|----------|----------------|
| 2.1 | Vendor? | SYSTEM-VERIFIED after connect |
| 2.2 | Current version (if known)? | Leave blank if unknown |
| 2.3 | Primary business owner? | Accountable person, not tech admin |
| 2.4 | Implementation contact? | Access provisioning / connector setup |

Skip technical connector detail here.

---

## 3. Business definitions *(CEP)*

Customer-specific definition **or** accept SMPL standard default:

| # | Metric / concept | Decision (custom / SMPL default) |
|---|------------------|----------------------------------|
| 3.1 | Active Customer | |
| 3.2 | **ARR** | |
| 3.3 | **MRR** | |
| 3.4 | Churn | |
| 3.5 | Expansion | |
| 3.6 | Contraction | |
| 3.7 | Renewal | |
| 3.8 | Bookings | |
| 3.9 | Qualified Pipeline | |
| 3.10 | Active Employee | |
| 3.11 | Contractor | |
| 3.12 | FTE | |

**Also ask *(CEP + FIE intent):*** Do you report more than one ARR to different audiences (e.g. Board / Investor / Operational / Sales)? If yes, which is canonical for SMPL Day 1?

**Also ask *(Recommended — Score input):*** Do you report **adjusted profitability metrics** (e.g. Adjusted EBITDA, contribution margin) differently by audience? For each, capture the audience, the add-backs, and who owns the definition. All versions come from the same book of record plus documented adjustments — SMPL does not keep separate P&L copies.

| Audience | Metric name | Add-backs / adjustments | Definition owner |
|----------|-------------|-------------------------|------------------|
| Internal management | | | |
| Investor / board | | | |
| Lender / covenant | | | |

---

## 4. ARR / subscription policy decisions — hard gates *(Gate)*

These come from the **Subscription Normalization Gate** (GPES Stripe reference + Billing CKR). ARR Movement is blocked until resolved. Defaults below are SMPL defaults — confirm explicitly; trial treatment is the most common ARR disagreement.

| # | Gate question | SMPL default | Customer answer |
|---|---------------|--------------|-----------------|
| 4.1 | Include **trialing** subscriptions in ARR? | **Exclude** | |
| 4.2 | Include **past_due / unpaid** subscriptions in ARR? | **Exclude** | |
| 4.3 | **Usage-based ARR policy** (only if metered pricing exists): are committed minimums in ARR? Uncommitted overages? | N/A if no metered pricing | |
| 4.4 | If usage exists: pricing method? | per-unit / tiered / volume | |

**Related billing decisions *(Gate / Billing CKR Implementation Decision Flow):***

| # | Question | Answer |
|---|----------|--------|
| 4.5 | Is Billing the authoritative source for subscriptions, or is there a separate CPQ / contract system? | |
| 4.6 | Multiple subscription items / add-ons — how should they aggregate into ARR? | |
| 4.7 | Multiple billing accounts / sites (regional / product) — consolidation strategy? | |
| 4.8 | Non-card methods (ACH / invoice) present? Settlement lag / banking pairing needed? | |
| 4.9 | Live-only data confirmed (exclude test / sandbox)? | Enforced automatically for Stripe (`livemode`); still confirm expectation |
| 4.10 | Reactivation vs New Business dormancy window? | SCBM default **90 days** unless overridden |

---

## 5. Business policies *(CEP)*

| # | Policy | Decision |
|---|--------|----------|
| 5.1 | Revenue recognition approach | |
| 5.2 | **ARR methodology** (how annual recurring revenue is calculated) | |
| 5.3 | Usage-based billing — exists? how treated in reporting? | Aligns with gate 4.3 |
| 5.4 | Trial handling | Aligns with gate 4.1 |
| 5.5 | Renewal treatment (vs new bookings) | |
| 5.6 | Cancellation policy (impact on churn / ARR) | |
| 5.7 | Contractor policy (included in headcount metrics?) | |
| 5.8 | Department ownership rules (cost / spend attribution) | |
| 5.9 | Cost center ownership rules | |
| 5.10 | Multi-entity reporting rollup | |

### System of authority *(CEP)*

Which connected system is authoritative for each:

Customer · Product · Employee · Department · Cost Center · Opportunity · Subscription · Invoice · Revenue · Headcount · Compensation

| Concept | System of record |
|---------|------------------|
| | |
| | |

---

## 6. Forecasting methodology *(Recommended — not formal CEP)*

> **Recommended addition.** CEP lists Cash Forecasting / Scenario Planning as desired modules only. There is no dedicated forecast-driver interview in CEP v1.0. Questions below are reconstructed from `docs/Forecasting_Assumptions.md` and related methodology docs for call use — do not present them as frozen CEP fields.

### How they forecast today

| # | Question | Answer |
|---|----------|--------|
| 6.1 | Who owns Forecast vs Budget vs Actual? | |
| 6.2 | Combined cutover date (when Actual ends and Forecast begins)? | |
| 6.3 | Method today: driver-based, spreadsheet judgment, CRM pipeline-weighted, or mix? | |
| 6.4 | Which scenarios do you need (Forecast / Budget / Upside / Downside)? | |
| 6.5 | How often do you refresh? What happens after close (Actual ending → next Forecast beginning)? | |

### Drivers to confirm (map to platform assumptions)

Ask which they trust and can supply; skip what is irrelevant:

| Area | Drivers to confirm |
|------|--------------------|
| Revenue / subscriptions | New logo ARR growth; expansion rate; gross churn; NRR target; typical contract term (12/24/36); revenue ramp months |
| Pipeline / bookings | Win rates by stage; ASP by segment; sales cycle; quota attainment; pipeline coverage; closed-won ↔ new ARR tie-out |
| Billings / rev rec | Billings growth; recognition pattern; professional services % |
| Cash | DSO / DPO; collection lag; minimum cash balance |
| Headcount / opex | Hiring plan by dept; attrition; fully loaded cost |
| Marketing | Funnel rates (MQL→SQL→Opp); CAC payback if used |

---

## 7. Close / GL / data readiness *(Recommended — not formal CEP)*

> **Recommended addition.** Reconstructed from close / GL / reporting methodology docs. Useful for implementation blockers; not listed as CEP fields in v1.0.

| # | Question | Answer |
|---|----------|--------|
| 7.1 | Close calendar / SLA (e.g. business-day close)? | |
| 7.2 | First period of GL history available? Opening trial balance + ending retained earnings at cutoff? | |
| 7.3 | Chart of accounts → management reporting lines / EBITDA mapping? | |
| 7.4 | Multi-entity structure? Dept vs cost center mapping ready? | |
| 7.5 | Validation sources for ending ARR, revenue, headcount (what do you tie to today)? | |
| 7.6 | Who certifies Actual each month (Accounting / FP&A / RevOps)? | |

### Accounting policy & close practice *(Score input — Recommended)*

> Each answer sets module status in the Readiness Score. The consequence column is what to tell the customer if the practice isn’t in place. **Customer action** means their team changes how data is recorded. **SMPL connector** means connecting another system closes the gap. SMPL never closes a gap by adjusting the customer’s data.

| # | Question | If not in place — reporting consequence | Improvement path | Answer |
|---|----------|------------------------------------------|------------------|--------|
| 7.7 | **Cost of revenue policy:** which costs count as cost of revenue (e.g. hosting / compute, support, technical account managers, third-party tools needed to deliver the service)? Who approved it? | Management P&L gross margin is **PARTIAL** — gross margin shows only as booked on the income statement | Customer action: document and approve the policy | |
| 7.8 | Does the GL support that policy — is **payroll posted by department / cost center** (not as one summary entry), so cost-of-revenue roles can be separated? | Labor can’t be split between cost of revenue and OpEx; Management P&L gross margin stays **PARTIAL** | Customer action: post payroll journal entries by department (most payroll providers export this) | |
| 7.9 | Are shared costs (compute, support, TAMs, facilities) **allocated** across departments or into cost of revenue? Are allocations **booked as journal entries**, or kept in a spreadsheet outside the GL? | Allocations outside the GL can’t be shown; Management P&L presents costs where they are booked | Customer action: book allocations as journal entries each month | |
| 7.10 | Are expenses **accrued monthly**, or only at quarter-end / year-end? | Monthly variances swing on timing; commentary confidence **lowered** for affected lines | Customer action: accrue monthly | |
| 7.11 | Do accruals **reverse** in the following period, and is the actual invoice posted to the same account and department as the accrual? | Commentary nets accrual + reversal + actual together; a missing or mismatched leg is reported as a **data gap**, not narrated | Customer action: consistent reversal and coding | |
| 7.12 | **Usage-based vendors** (cloud, messaging, API, data): accrued on estimate and trued up? Who owns the estimate? | Same as 7.11 — true-ups show as unexplained swings until all legs are present | Customer action: documented estimate + true-up practice | |
| 7.13 | **Year-end audit / review adjustments:** restate prior months, book to the final month / adjustment period, or both? How is prior board commentary handled once numbers change? | Board history is **PARTIAL** — previously reported periods may change without an agreed treatment | Customer action: choose and document a policy | |

### Sales commissions — capitalized contract costs, ASC 340-40 *(Normalization gate — Recommended)*

> Under GAAP (ASC 340-40), commissions that are incremental costs of obtaining a contract are capitalized and amortized over the period of benefit, including expected renewals when renewal commissions are not commensurate. Contracts with a benefit period of a year or less may be expensed (practical expedient). Companies choose and document the amortization period, so the answers differ from company to company.
>
> **How SMPL uses the answers:** the Forecast and Budget engines read this policy; it is shown read-only and is not a lever. In the engines, commission **cash** follows payout timing (7.18), and commission **expense** follows amortization (7.15–7.17). Actuals come from the GL as booked.
>
> **How SMPL checks them:** after connect, each answer is compared with the GL and the payout export:
> - a deferred commissions asset exists if and only if commissions are capitalized;
> - commission expense is present;
> - the deferred balance is no larger than the stated amortization period allows;
> - an accrued commissions liability exists when payouts lag bookings;
> - payouts = commission expense + change in deferred commissions − change in accrued commissions, within 1% or $1,000.
>
> A conflict keeps Cash Forecasting, Scenario Planning and Board Reporting at **PARTIAL** until the customer corrects the books or the answer. Unanswered or "not sure" leaves the gate unresolved.

| # | Question | Choices | Answer |
|---|----------|---------|--------|
| 7.14 | **Sales commissions** on new and expansion contracts: capitalized and amortized, expensed as incurred, or no commissions? If unsure, confirm with the controller or auditor before go-live. | capitalized / expensed / no commissions / not sure | |
| 7.15 | If capitalized: **amortization period for new-business commissions**, in months, including expected renewals? | 12 / 24 / 36 / 48 / 60 / 72 / 84 | |
| 7.16 | If capitalized: **amortization period for expansion commissions**, in months? | 12 / 24 / 36 / 48 / 60 / 72 / 84 | |
| 7.17 | **Renewal commissions:** expensed under the 12-month practical expedient, capitalized, or not paid? | expensed / capitalized / not paid | |
| 7.18 | **When are commissions paid?** Drives forecast commission cash and whether an accrued commissions liability is expected. | month of booking / month after booking / quarter after booking / on customer payment | |
| 7.19 | **Employer payroll taxes on commissions:** expensed or capitalized with the commission? | expensed / capitalized | |
| 7.20 | **System of record for commission payouts** (comp tool such as CaptivateIQ, Spiff or Xactly; payroll export; spreadsheet; none)? Without payout detail, commission cash can be estimated but not checked. | comp tool / payroll export / spreadsheet / none | |
| 7.21 | **Winbacks** (a customer who ended their contract returns within the winback window, 4.10): commission only on ARR above what the customer paid before leaving, on all returned ARR, or none? A return after the window is new business and paid as new business. | above prior ARR / full amount / not paid | |
| 7.22 | **Restarts after a pause** (no time limit): commission only on ARR above the customer's ARR before the pause, on all of it, or none? | above prior ARR / full amount / not paid | |
| 7.23 | **Rate** on commissionable winback and restart ARR: the new-business rate or the expansion rate? | new business rate / expansion rate | |
| 7.24 | **Expansion after a contraction:** commission only on ARR above the customer's level before the contraction, or on all expansion? | above prior level / all expansion | |

> **How SMPL uses 7.21–7.24:** "above prior" rules need each customer's history. SMPL measures the share of returned and expansion ARR above the prior level from CRM Churn and Contraction opportunities and applies it to planned ARR; if the history isn't there, that commission is left out of the plan and named, not assumed. The engines' plan has one reactivation line, so winbacks and restarts must be paid the same way for reactivation commission to be computed. Answers are also checked against loaded payouts (for example, "not paid" while Reactivation payouts exist is a conflict).

---

## 8. Desired modules *(CEP)*

Select for implementation roadmap:

| Module | Include? (Y/N / Phase 2) |
|--------|--------------------------|
| Financial Reporting | |
| Board Reporting | |
| Executive Dashboards | |
| Cash Forecasting | |
| ARR Reporting | |
| MRR Reporting | |
| Pipeline Analytics | |
| Workforce Planning | |
| Scenario Planning | |
| Executive Commentary | |

---

## 9. Optional — CRM stages / headcount *(Gate examples from GPES)*

Ask only if CRM or HRIS is in scope and ambiguity appears after (or before) connect.

| # | Question | Answer |
|---|----------|--------|
| 9.1 | For any ambiguous CRM stage: does it mean Proposal vs Negotiate (or equivalent)? | Example: HubSpot “Contract Sent” |
| 9.2 | Which employment statuses count as active headcount — Active only, or Active + Leave of Absence? | |
| 9.3 | Should contractors be included in headcount? | |
| 9.4 | Allocate employee costs to GL cost centers for Department Expense Forecasting? | Can defer to Phase 2 |

---

## 10. Platform access acknowledgment *(Recommended)*

> SMPL assumes that everyone the customer gives platform access to may see the information being reported **and the detail underneath it** — including payroll-related GL lines, vendor-level transactions, and department spend. The customer decides who gets access.

| # | Question | Answer |
|---|----------|--------|
| 10.1 | Acknowledged: platform users can see reported numbers and the underlying detail, including payroll-related lines? | |
| 10.2 | Who will get logins (finance team, executives, department heads, board members)? | |
| 10.3 | Who on the customer side approves new access? | |

---

## 11. Systems & data review — findings and sign-off *(completed after connect)*

> Completed by SMPL after systems connect and the first data pull, then reviewed with the customer’s finance lead. Any failed readiness gate, or any **PARTIAL / UNAVAILABLE** status on a module the customer expects Day 1, must go to SMPL leadership **before** implementation continues. That way the path forward is agreed up front and the resulting reporting limits are understood and signed off.

**Readiness Score summary**

| Field | Value |
|-------|-------|
| Readiness gates (Section 0) | Pass / Fail — list any failures |
| Overall Readiness Score | % |
| Modules READY | |
| Modules PARTIAL (and why) | |
| Modules UNAVAILABLE (and why) | |
| Biggest next improvement (customer action or SMPL connector) and expected score change | |

**Findings**

| # | Finding | Area (question ref) | Reporting consequence | Path: Customer action / SMPL connector / Accept limitation | Customer owner | Target date |
|---|---------|---------------------|-----------------------|------------------------------------------------------------|----------------|-------------|
| F1 | | | | | | |
| F2 | | | | | | |

**Sign-off**

| Role | Name | Date |
|------|------|------|
| Customer finance lead (owns books and fixes) | | |
| SMPL engagement lead | | |
| SMPL leadership review (required if any gate failed or Day-1 module is PARTIAL / UNAVAILABLE) | | |

---

## Call-time shortlist (~15 min)

**Must cover (CEP + gates):**  
Data ownership + readiness gates (Section 0) → company snapshot → systems & owners → ARR/MRR/churn definitions → trials / past_due / usage min-vs-overage → ARR methodology → rev-rec & renewal/cancel → systems of record → modules → FYE/currency/entities.

**Should cover if time:**  
Pipeline stage meanings · headcount/contractor · multi-account billing · live-only data · cost of revenue policy + payroll by department (7.7–7.8) · commission capitalization policy and payout timing (7.14–7.20) · access acknowledgment (Section 10).

**Recommended extras (label clearly):**  
How Forecast is built today · trusted drivers · multiple ARR intents · adjusted metrics by audience · close calendar + GL cutoff artifacts · allocations, accrual / reversal practice, audit adjustments (7.9–7.13).

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
| 7.14–7.20 Sales commissions | ASC 340-40; `docs/COMMISSION_CAPITALIZATION_DESIGN.md` | **Recommended — not CEP** |
| Readiness Score (Section 11) | `backend/tmp/impl-docs/SMPL_AI_Agent_Playbooks_v1.0.txt` (CAL.4–CAL.7) + GPES Stage 7 | Methodology spec |

---

*Internal working sheet for customer discovery. CEP remains the evolving implementation record after systems connect.*
