# Customer Onboarding — Discovery Call Sheet

**SAMPLE — illustrative only; not a real customer.**  
**Persona:** Northwind Platforms (complex / multi-nuance SaaS)  
**Filled for:** showing customers what complete answers look like when policy edges matter  
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

**Sample capture metadata**

| Field | Value |
|-------|-------|
| Call date | 2026-03-18 |
| Confirmed by | Sam Okonkwo (CFO) |
| Also present | Riley Cho (FP&A), Casey Nguyen (RevOps), Pat Morales (Corp Controller), Drew Kim (Billing Ops) |
| Day-1 ARR intent | **Board / Investor ARR is canonical** (excludes uncommitted usage; see §3 & §4) |

---

## 1. Company overview *(CEP)*

| # | Question | Notes / answer |
|---|----------|----------------|
| 1.1 | Company name (legal or preferred operating)? | **Northwind Platforms Holdings, Inc.** (operating: Northwind Platforms) |
| 1.2 | Industry? | B2B SaaS — developer platform / API infrastructure |
| 1.3 | Business model? | **Hybrid:** committed SaaS platform fees + **usage-based** API overages + professional services (~12–15% of revenue for implementations). ARR policy must separate committed vs usage (see gates). |
| 1.4 | Headquarters? | Chicago, IL, USA |
| 1.5 | Operating countries / entities? | **Three entities:** (1) Northwind Platforms Holdings, Inc. (US parent), (2) Northwind Platforms UK Ltd, (3) Northwind Platforms GmbH (Germany). Selling in US, UK, EU, ANZ. Intercompany licensing + local billing entities. |
| 1.6 | Primary reporting currency? | **USD consolidated** for board / investor FI. Local books in USD, GBP, EUR. FX translation for consolidation (month-end rate for P&L; they already do this in NetSuite). |
| 1.7 | Approximate revenue range? | ~$55–65M ARR (Board definition); total revenue higher with usage + PS |
| 1.8 | Approximate employee count? | ~280 W-2 + ~45 long-term contractors (eng / CS surge) |
| 1.9 | Fiscal year end? | **January 31** (FY ends Jan 31; e.g. FY26 = Feb 1 2025 – Jan 31 2026) |

---

## 2. Connected systems *(CEP)*

For each relevant system (ERP, CRM, Billing, HRIS, Payroll, Planning, Data Warehouse, BI, other):

| System type | 2.1 Vendor | 2.2 Version (if known) | 2.3 Primary business owner | 2.4 Implementation contact |
|-------------|------------|------------------------|----------------------------|----------------------------|
| Billing | **Stripe** (US + EU accounts) + legacy **Zuora** for ~8% of UK enterprise (sunset 2026 H2) | Stripe current; Zuora Central | Drew Kim (Billing Ops) | Drew Kim + Stripe TAM |
| CRM | **Salesforce** Sales Cloud | Enterprise | Casey Nguyen (RevOps) | Casey Nguyen |
| CPQ / Contracts | Salesforce CPQ + Ironclad | Current | Casey Nguyen | Legal Ops (Mei Tran) |
| ERP / GL | **NetSuite** OneWorld (US / UK / DE subsidiaries) | 2024.2 | Pat Morales (Corp Controller) | Finance Systems (Noah Berg) |
| HRIS | **Workday** HCM | Current | Avery Brooks (People) | Avery Brooks |
| Payroll | Workday Payroll (US); remote.com (UK/EU contractors & some EOR) | — | Avery Brooks | Avery Brooks |
| Planning | Anaplan (annual) + FP&A Sheets bridge | — | Riley Cho (FP&A) | Riley Cho |
| Data Warehouse | Snowflake | — | Data Eng (Chris Park) | Chris Park |
| BI | Tableau + board pack in Sheets | — | Riley Cho | — |

Skip technical connector detail here. **Note for impl:** Day 1 billing authority = Stripe live accounts; Zuora ARR as Phase 1.5 overlay or manual bridge until sunset.

---

## 3. Business definitions *(CEP)*

Customer-specific definition **or** accept SMPL standard default:

| # | Metric / concept | Decision (custom / SMPL default) |
|---|------------------|----------------------------------|
| 3.1 | Active Customer | Paying **billing account** with committed platform subscription in good standing. Ultimate parent hierarchy used for logo metrics (Salesforce Account hierarchy); ARR rolls at billing-account grain then rolls to parent for logo NRR. |
| 3.2 | **ARR** | **Custom — dual intent (see below).** Board ARR = annualized **committed** recurring platform fees + **committed usage minimums**; exclude uncommitted overages, trials, and PS. Sales “ARR” in Salesforce often includes first-year overage estimates — **not** Day-1 SMPL canonical. |
| 3.3 | **MRR** | Board ARR ÷ 12. Same inclusions as Board ARR. |
| 3.4 | Churn | Gross ARR churn = lost committed ARR from cancels / non-renewals. Logo churn at ultimate parent. Downgrade of committed min without full cancel = contraction, not churn. |
| 3.5 | Expansion | Increase in committed ARR (seats, platform tier, higher usage minimum). Uncommitted overage spikes are **usage revenue**, not expansion ARR. |
| 3.6 | Contraction | Decrease in committed ARR while customer remains active. |
| 3.7 | Renewal | CPQ renewal opportunity type; committed ARR continuing. Multi-year renewals booked at annualized committed ARR for Board. |
| 3.8 | Bookings | Salesforce Closed-Won **ACV (Sales definition)** — may include estimated Year-1 usage; Finance reconciles Bookings → Board ARR with a known bridge. |
| 3.9 | Qualified Pipeline | Stages **Proposal**, **Negotiation**, **Verbal Commit**, **Contracting** — but see §9 for stage ambiguity. |
| 3.10 | Active Employee | Workday: Active + Paid Leave (include LOA in HC for board HC trend). Unpaid leave excluded. |
| 3.11 | Contractor | Workday contingent + remote.com; **include in “Total Workforce”** but report **Employees vs Contractors** as separate series. Board HC headline = Employees only unless labeled “workforce.” |
| 3.12 | FTE | Employees: FTE from Workday. Contractors: count as 1.0 headcount in contractor series, not in Employee FTE. |

**Also ask *(CEP + FIE intent):*** Do you report more than one ARR to different audiences (e.g. Board / Investor / Operational / Sales)? If yes, which is canonical for SMPL Day 1?

**Answer:** **Yes — three intents exist today:**

| Intent | Definition (summary) | Day-1 SMPL? |
|--------|----------------------|-------------|
| **Board / Investor ARR** | Committed platform + committed usage minimums; exclude trials, past_due (per gate), uncommitted overages, PS | **Canonical Day 1** |
| **Operational ARR** | Board ARR + in-grace past_due (collections view) — finance ops only | Phase 2 if needed |
| **Sales ARR / ACV** | CPQ ACV including estimated usage Year 1 | Stay in Salesforce; bridge report only |

Confirmed: Sam Okonkwo + Riley Cho, 2026-03-18.

---

## 4. ARR / subscription policy decisions — hard gates *(Gate)*

These come from the **Subscription Normalization Gate** (GPES Stripe reference + Billing CKR). ARR Movement is blocked until resolved. Defaults below are SMPL defaults — confirm explicitly; trial treatment is the most common ARR disagreement.

| # | Gate question | SMPL default | Customer answer |
|---|---------------|--------------|-----------------|
| 4.1 | Include **trialing** subscriptions in ARR? | **Exclude** | **Exclude from Board ARR** (accept SMPL). Exception: “design partner” trials that are invoiced at $0 but contractually committed — treat as **$0 ARR until first paid period** (still exclude). Confirmed: Drew / Riley. |
| 4.2 | Include **past_due / unpaid** subscriptions in ARR? | **Exclude** | **Board ARR: Exclude** (SMPL default). Ops may keep a shadow “collections ARR” that includes past_due <30 days — **not** Day-1 canonical. After 30 days past_due, Sales must re-forecast churn risk. Confirmed: Sam / Pat. |
| 4.3 | **Usage-based ARR policy** (only if metered pricing exists): are committed minimums in ARR? Uncommitted overages? | N/A if no metered pricing | **Committed usage minimums = IN Board ARR.** Uncommitted overages = **usage revenue / billings only**, not ARR. True-up invoices that increase the contractual minimum prospectively = expansion when amendment effective. |
| 4.4 | If usage exists: pricing method? | per-unit / tiered / volume | **Hybrid:** platform subscription (tiered seats) + metered API (**tiered** per-unit with monthly committed minimum). Volume discounts on overage tiers only. |

**Related billing decisions *(Gate / Billing CKR Implementation Decision Flow):***

| # | Question | Answer |
|---|----------|--------|
| 4.5 | Is Billing the authoritative source for subscriptions, or is there a separate CPQ / contract system? | **Split authority:** Salesforce CPQ / Ironclad = commercial truth for enterprise amendments; **Stripe (and residual Zuora) = billing runtime.** Day-1 ARR from Stripe (+ Zuora bridge). Material CPQ vs Stripe mismatches escalate to Billing Ops weekly. |
| 4.6 | Multiple subscription items / add-ons — how should they aggregate into ARR? | Sum recurring committed items (platform + add-on modules + committed min line). Exclude metered overage line items, one-time PS, and setup fees. Multi-product customers: one ARR total; product split is analytical dimension Phase 2. |
| 4.7 | Multiple billing accounts / sites (regional / product) — consolidation strategy? | **Two live Stripe accounts** (US platform, EU platform) + Zuora UK. Consolidate to USD Board ARR. Same ultimate parent across accounts = one logo; ARR sums across billing accounts. |
| 4.8 | Non-card methods (ACH / invoice) present? Settlement lag / banking pairing needed? | Heavy **invoice / ACH / wire** for enterprise (~60%). Net-30/45 common. Cash forecast needs DSO by channel; banking pairing for large wires **yes** (NetSuite cash + bank feeds) — flag for cash module. |
| 4.9 | Live-only data confirmed (exclude test / sandbox)? | **Yes.** Both Stripe accounts livemode only. Zuora production tenant only. Sandbox / test customers tagged and excluded. |
| 4.10 | Reactivation vs New Business dormancy window? | **Override SCBM default → 180 days** (enterprise sales cycles / seasonal API customers). Return within 180 days = reactivation; after = new logo. Confirmed: Casey / Riley. |

---

## 5. Business policies *(CEP)*

| # | Policy | Decision |
|---|--------|----------|
| 5.1 | Revenue recognition approach | ASC 606; SSP for platform vs usage vs PS. Usage recognized as consumed; platform ratable; PS % complete or milestone. NetSuite ARM for large deals; Stripe billing for SMB. |
| 5.2 | **ARR methodology** (how annual recurring revenue is calculated) | Board: annualize committed recurring fees + committed usage minimums at subscription currency, translate to USD at month-end rate for consolidated ending ARR. Point-in-time month-end. Do **not** annualize trailing overage. |
| 5.3 | Usage-based billing — exists? how treated in reporting? | **Yes.** Committed min in ARR (4.3); overages in revenue/billings and cash, with a usage dashboard separate from ARR Movement. |
| 5.4 | Trial handling | 30-day self-serve trials + sales-assisted POCs. **Excluded from Board ARR** until paid conversion (4.1). |
| 5.5 | Renewal treatment (vs new bookings) | CPQ renewal opp type. Bookings ACV may include estimated usage; Board renewal ARR = committed only. Multi-year: ARR remains annualized committed, not TCV. |
| 5.6 | Cancellation policy (impact on churn / ARR) | Notice ≠ churn. ARR exits on **contractual end / entitlement end**. Enterprise early terminations with exit fees: exit fee ≠ ARR; remaining committed ARR drops on termination effective date. |
| 5.7 | Contractor policy (included in headcount metrics?) | **Split reporting:** Employee HC (board default) vs Contractor HC vs Total Workforce. Contractors **included** in workforce planning capacity views; **excluded** from “Employees” KPI. |
| 5.8 | Department ownership rules (cost / spend attribution) | Depts: Sales, Marketing, CS, Eng, Product, G&A, COGS-Support. Matrix exists for shared platform eng — FP&A allocation keys quarterly. |
| 5.9 | Cost center ownership rules | NetSuite Department + Class; Workday cost center must map 1:1 to NetSuite for dept expense forecast. Gaps known in EU — cleanup before Workforce module. |
| 5.10 | Multi-entity reporting rollup | Consolidate US + UK + DE to Holdings USD. Eliminations for intercompany license fees (Pat owns). Management view: consolidated + US-standalone for cash. |

### System of authority *(CEP)*

Which connected system is authoritative for each:

| Concept | System of record |
|---------|------------------|
| Customer | Salesforce Account (hierarchy / logo); Stripe/Zuora Customer (billing) |
| Product | Salesforce CPQ product catalog → Stripe Products (SKU sync owned by Billing Ops) |
| Employee | Workday |
| Department | Workday supervisory org → NetSuite Department |
| Cost Center | NetSuite (Class / Dept); Workday cost center must match |
| Opportunity | Salesforce |
| Subscription | **Stripe / Zuora** (billing); CPQ quote for commercial amendments |
| Invoice | Stripe / Zuora (customer invoice); NetSuite (accounting AR / revenue) |
| Revenue | **NetSuite** (recognized revenue & deferred) |
| Headcount | Workday (employees); remote.com + Workday contingent (contractors) |
| Compensation | Workday |

---

## 6. Forecasting methodology *(Recommended — not formal CEP)*

> **Recommended addition.** CEP lists Cash Forecasting / Scenario Planning as desired modules only. There is no dedicated forecast-driver interview in CEP v1.0. Questions below are reconstructed from `docs/Forecasting_Assumptions.md` and related methodology docs for call use — do not present them as frozen CEP fields.

### How they forecast today

| # | Question | Answer |
|---|----------|--------|
| 6.1 | Who owns Forecast vs Budget vs Actual? | **Budget:** Riley (FP&A) / Sam (CFO) — annual Anaplan. **Forecast:** Riley monthly driver-based reforecast. **Actual:** Pat Morales certifies consolidated Actual; Drew certifies billing subledgers. |
| 6.2 | Combined cutover date (when Actual ends and Forecast begins)? | After consolidated close (**BD+8** target). Forecast month begins day after certified Actual end. FYE Jan 31 complicates calendar packs — map SMPL periods to FY periods explicitly. |
| 6.3 | Method today: driver-based, spreadsheet judgment, CRM pipeline-weighted, or mix? | **Driver-based primary** (new logo committed ARR, expansion rate, gross churn, usage revenue separate) + **pipeline-weighted** check from Salesforce + judgment overlay for mega-deals. Anaplan for annual; Sheets bridge monthly. |
| 6.4 | Which scenarios do you need (Forecast / Budget / Upside / Downside)? | **All four Day 1:** Forecast (base), Budget, Upside (+15% new ARR / lower churn), Downside (usage recession / delayed enterprise). |
| 6.5 | How often do you refresh? What happens after close (Actual ending → next Forecast beginning)? | Full reforecast monthly post-close; flash update mid-month for Board if mega-deal slips. Actual locks; Forecast beginning ARR/cash/HC = certified endings; usage forecast re-seeded from last 3 months run-rate ≠ ARR. |

### Drivers to confirm (map to platform assumptions)

| Area | Drivers confirmed |
|------|-------------------|
| Revenue / subscriptions | New committed ARR growth plan by segment (SMB / Mid / Ent); expansion ~3% of starting committed ARR/mo; gross churn targets by segment; NRR target 115% Board; terms **12 / 24 / 36**; enterprise ramp 1–3 months for PS-attached deals (ARR starts when subscription live, not when PS completes). |
| Pipeline / bookings | Win rates by stage **but stage meanings ambiguous** (see §9); ASP by segment; Ent cycle 120–180 days; coverage 3.5× on Board ARR definition (not Sales ACV); closed-won ACV ↔ Board ARR bridge owned by RevOps + FP&A. |
| Billings / rev rec | Billings growth ≠ ARR (usage + terms); PS ~12–15% of revenue — forecast PS separately; recognition patterns from NetSuite ARM. |
| Cash | DSO 35–50 by channel; DPO ~45; FX cash in GBP/EUR; min consolidated cash $12M; wire pairing required. |
| Headcount / opex | Hiring plan by dept in Anaplan; attrition 15%; contractors as flexible capacity; fully loaded cost Workday + burden; EU cost center cleanup dependency. |
| Marketing | MQL→SQL→Opp rates in Salesforce; CAC payback used for Board; paid + PLG dual funnel. |

---

## 7. Close / GL / data readiness *(Recommended — not formal CEP)*

> **Recommended addition.** Reconstructed from close / GL / reporting methodology docs. Useful for implementation blockers; not listed as CEP fields in v1.0.

| # | Question | Answer |
|---|----------|--------|
| 7.1 | Close calendar / SLA (e.g. business-day close)? | Entity soft close BD+5; **consolidated hard close BD+8**; Board pack BD+10. FYE January adds extended close (~BD+12). |
| 7.2 | First period of GL history available? Opening trial balance + ending retained earnings at cutoff? | NetSuite history from **Feb 2022** (post-OneWorld go-live). For SMPL cutoff: provide **opening TB per entity**, consolidated TB, and **ending retained earnings (RE)** at cutoff. Awareness: prior systems (legacy QuickBooks US pre-2022) will use **RE_BASE / opening RE** treatment — do not reload pre-OneWorld detail. Pat to supply RE_BASE memo. |
| 7.3 | Chart of accounts → management reporting lines / EBITDA mapping? | NetSuite financial report layouts exist; management EBITDA bridge in Anaplan. Will export CoA → SMPL reporting line map (includes usage revenue vs subscription revenue vs PS). |
| 7.4 | Multi-entity structure? Dept vs cost center mapping ready? | Three subsidiaries + consol. Dept mapping ~90% ready; **DE cost centers incomplete** — Phase 1 FI can roll entity/consol; dept expense forecasting waits on EU CC cleanup. |
| 7.5 | Validation sources for ending ARR, revenue, headcount (what do you tie to today)? | Board ARR: FP&A Stripe+Zuora workbook. Revenue: NetSuite consolidated P&L. HC: Workday census. Bookings: Salesforce — bridge, not tie, to ARR. |
| 7.6 | Who certifies Actual each month (Accounting / FP&A / RevOps)? | **Pat Morales** certifies consolidated Actual; **Riley** certifies Forecast & Board ARR; **Casey** certifies pipeline; **Drew** certifies billing subledger completeness. |

---

## 8. Desired modules *(CEP)*

Select for implementation roadmap:

| Module | Include? (Y/N / Phase 2) |
|--------|--------------------------|
| Financial Reporting | **Y** (multi-entity consol) |
| Board Reporting | **Y** |
| Executive Dashboards | **Y** |
| Cash Forecasting | **Y** (multi-currency / DSO) |
| ARR Reporting | **Y** (Board canonical + Sales bridge later) |
| MRR Reporting | **Y** |
| Pipeline Analytics | **Y** (after stage gate) |
| Workforce Planning | **Y** (employees + contractor split) |
| Scenario Planning | **Y** (Forecast / Budget / Upside / Downside) |
| Executive Commentary | Phase 2 |

---

## 9. Optional — CRM stages / headcount *(Gate examples from GPES)*

Ask only if CRM or HRIS is in scope and ambiguity appears after (or before) connect.

| # | Question | Answer |
|---|----------|--------|
| 9.1 | For any ambiguous CRM stage: does it mean Proposal vs Negotiate (or equivalent)? | **Yes — ambiguity called out.** Salesforce stage **“Contracting”** mixes legal redlines (Negotiate) and “sent for signature” (late Proposal). Decision: split into **Contracting – Commercial** (= Negotiate) and **Contracting – Signature** (= Proposal/Commit) before pipeline weighting goes live. Until then, weight **Contracting** as Negotiate (lower win rate). Confirmed: Casey, 2026-03-18. |
| 9.2 | Which employment statuses count as active headcount — Active only, or Active + Leave of Absence? | **Active + Paid Leave** for Employee HC. Unpaid leave / terminated excluded. |
| 9.3 | Should contractors be included in headcount? | **Yes in Workforce / contractor series; No in Employee HC** (see 5.7). ~45 contractors material to capacity planning. |
| 9.4 | Allocate employee costs to GL cost centers for Department Expense Forecasting? | **Y for US/UK Day 1**; **DE deferred** until cost center mapping complete. Workday → NetSuite allocation required for dept expense forecast. |

---

## Call-time shortlist (~15 min) — how this sample maps

**Must cover (CEP + gates):**  
Covered: multi-entity + USD consol → Stripe/Salesforce/NetSuite/Workday (+ Zuora bridge) → **Board ARR canonical vs Sales ACV** → trials exclude / past_due exclude for Board → **committed min in ARR, overages out** → hybrid rev-rec → systems of record split CPQ vs billing → modules → FYE Jan 31.

**Should cover if time:**  
Pipeline stage “Contracting” ambiguity · contractors in workforce · multi Stripe accounts · invoice/ACH lag · 180-day reactivation.

**Recommended extras (label clearly):**  
Driver-based forecast + four scenarios · close BD+8 · GL cutoff with **RE_BASE** for pre-OneWorld history · dual ARR intents documented.

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

*SAMPLE — fictional customer for illustration. CEP remains the evolving implementation record after systems connect.*
