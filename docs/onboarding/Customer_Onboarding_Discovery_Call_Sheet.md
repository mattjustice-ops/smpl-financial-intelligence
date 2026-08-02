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

**Do not ask on this call:** API scopes, auth methods, field mappings, custom fields, pipeline inventories, currencies, org hierarchies — those are auto-discovered after connect.

**Capture style:** Decision + owner (who confirmed) + date. Prefer “accept SMPL default” over inventing policy on the fly.

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

## Call-time shortlist (~15 min)

**Must cover (CEP + gates):**  
Company snapshot → systems & owners → ARR/MRR/churn definitions → trials / past_due / usage min-vs-overage → ARR methodology → rev-rec & renewal/cancel → systems of record → modules → FYE/currency/entities.

**Should cover if time:**  
Pipeline stage meanings · headcount/contractor · multi-account billing · live-only data.

**Recommended extras (label clearly):**  
How Forecast is built today · trusted drivers · multiple ARR intents · close calendar + GL cutoff artifacts.

---

## Source map

| Content | Source | Status |
|---------|--------|--------|
| Sections 1–3, 5, 8, SoA | `backend/tmp/impl-docs/CEP_v1.0.txt` | Formal CEP |
| Section 4 ARR gates | `backend/tmp/impl-docs/phase3/SMPL_GPES_001_SaaS_Golden_Path_v1.1.txt` + `backend/tmp/impl-docs/SMPL_CKR_Billing_Registry_v0.2.txt` | Formal gate / CKR |
| Section 6 Forecasting | `docs/Forecasting_Assumptions.md` (+ reporting methodology) | **Recommended — not CEP** |
| Section 7 Close / GL | `docs/Close_Process.md`, close/GL readiness materials | **Recommended — not CEP** |
| Section 9 CRM / HC | GPES HubSpot + Rippling gate examples | Documented examples |

---

*Internal working sheet for customer discovery. CEP remains the evolving implementation record after systems connect.*
