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
| **Readiness gate** | Books-quality prerequisite (Section 0). If any gate fails, onboarding pauses — no Readiness Score is produced until the customer resolves it |
| **Score input** | Accounting-policy answer that sets module status (READY / PARTIAL / UNAVAILABLE) in the Readiness Score and names the improvement path |

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
| 0.1 | Are the books kept on an **accrual basis** (not cash or tax basis)? | Yes | **Yes — accrual, US GAAP**, all three subsidiaries. |
| 0.2 | Which **single book of record** should SMPL report from? Who owns it? | One named book + owner | NetSuite multi-book has a **primary US GAAP book** and a secondary tax book. **SMPL reports from the primary GAAP book only**, consolidated to Holdings USD. Owner: Pat Morales (Corp Controller). The Anaplan board P&L is a *view*, not a book (see 7.9). |
| 0.3 | Are the books **closed monthly**, with a named close owner and a target close day? | Yes | **Yes** — entity close BD+5, consolidated BD+8; Pat Morales owns. |
| 0.4 | Can the finance lead walk through the most recent month’s income statement and explain the material lines? | Yes | **Yes** — Pat walked the consolidated IS; Riley explained the bridge to the Anaplan board P&L. |
| 0.5 | Does the customer accept the data-ownership terms above? | Yes | **Yes** — Sam Okonkwo (CFO), 2026-03-18. |

**Gate result: PASS.** (Tax book explicitly excluded — confirmed not to be sent or reconciled.)

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

**Also ask *(Recommended — Score input):*** Do you report **adjusted profitability metrics** (e.g. Adjusted EBITDA, contribution margin) differently by audience? For each, capture the audience, the add-backs, and who owns the definition. All versions come from the same book of record plus documented adjustments — SMPL does not keep separate P&L copies.

| Audience | Metric name | Add-backs / adjustments | Definition owner |
|----------|-------------|-------------------------|------------------|
| Internal management | Management EBITDA | Reported EBITDA, presented after shared-cost allocations (see 7.9) | Riley Cho (FP&A) |
| Investor / board | Adjusted EBITDA | Add back stock-based comp, restructuring, M&A transaction costs | Sam Okonkwo (CFO) |
| Lender / covenant | Covenant EBITDA | Per credit agreement §1.1: SBC + non-recurring add-backs, **capped at 15%** of EBITDA; trailing 12 months | Pat Morales + Sam Okonkwo |

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
| 4.10 | Winback window? | **6 months** (enterprise sales cycles / seasonal API customers). A customer who cancels and returns within 6 months is a winback (Reactivation); after that, new business flagged as a returning customer. Confirmed: Casey / Riley. |
| 4.11 | Paused subscriptions in ARR? | **Removes ARR.** Seasonal API customers pause in Zuora; ARR drops to zero until they restart, and a restart is never new business. Zuora carries the pause status, so restarts can be told apart from winbacks. |

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

### Accounting policy & close practice *(Score input — Recommended)*

> Each answer sets module status in the Readiness Score. The consequence column is what to tell the customer if the practice isn’t in place. **Customer action** means their team changes how data is recorded. **SMPL connector** means connecting another system closes the gap. SMPL never closes a gap by adjusting the customer’s data.

| # | Question | If not in place — reporting consequence | Improvement path | Answer |
|---|----------|------------------------------------------|------------------|--------|
| 7.7 | **Cost of revenue policy** — which costs, who approved? | Management P&L gross margin **PARTIAL** | Customer action | **In place.** Hosting / compute (AWS, GCP), third-party API costs (Twilio), COGS-Support department, technical account managers, PS delivery labor (PS cost of revenue). Approved by Sam; reviewed annually with auditors. |
| 7.8 | **Payroll posted by department / cost center?** | Labor can’t be split; gross margin **PARTIAL** | Customer action | **US / UK: yes** — Workday Payroll posts by NetSuite Department. **EU contractors via remote.com: no** — one summary invoice per month to “Contract Labor,” mixing support and engineering contractors (see F1). |
| 7.9 | Shared-cost **allocations** — booked as JEs or kept outside the GL? | Allocations not shown | Customer action | **Outside the GL.** FP&A applies quarterly allocation keys in Anaplan (shared platform engineering → cost of revenue / R&D; facilities → departments). Nothing is booked in NetSuite (see F2). |
| 7.10 | Expenses **accrued monthly**? | Timing swings; commentary confidence lowered | Customer action | **US: monthly.** **UK / DE: quarterly** for professional fees and some SaaS vendors (see F3). |
| 7.11 | Accruals **reverse** next period, actuals coded to the same account / department? | Missing leg reported as a data gap | Customer action | **Yes** — NetSuite auto-reversing JEs. Coding matches for US; UK occasionally codes actuals to G&A when the accrual sat in the department (part of F3). |
| 7.12 | **Usage-based vendors** accrued on estimate and trued up? | True-ups show as unexplained swings | Customer action | **Yes** — AWS / GCP / Twilio accrued from usage dashboards at BD+2 by Finance Systems (Noah Berg); trued up on invoice. Messaging-heavy months swing — commentary nets the three legs. |
| 7.13 | **Year-end audit adjustments** — restate or book to final month? Prior commentary? | Board history **PARTIAL** | Customer action | **Big-4 audit.** Adjustments booked to NetSuite **adjustment period 13** (FYE Jan 31); prior months **not restated**. Board pack shows FY total incl. period 13; prior monthly commentary stands as reported with a note. |

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

## 10. Platform access acknowledgment *(Recommended)*

> SMPL assumes that everyone the customer gives platform access to may see the information being reported **and the detail underneath it** — including payroll-related GL lines, vendor-level transactions, and department spend. The customer decides who gets access.

| # | Question | Answer |
|---|----------|--------|
| 10.1 | Acknowledged: platform users can see reported numbers and the underlying detail, including payroll-related lines? | **Yes** — Sam Okonkwo, 2026-03-18. Noted that department payroll lines (e.g. small teams) can imply individual comp; customer accepts and will limit logins accordingly. |
| 10.2 | Who will get logins? | Finance (Sam, Pat, Riley, Noah), RevOps (Casey), Billing Ops (Drew), CEO, department heads (read-only). **Board members: read-only logins** for the board pack. |
| 10.3 | Who on the customer side approves new access? | Sam Okonkwo (CFO); Pat Morales as backup. |

---

## 11. Systems & data review — findings and sign-off *(completed after connect)*

> Completed by SMPL after systems connect and the first data pull, then reviewed with the customer’s finance lead. Any failed readiness gate, or any **PARTIAL / UNAVAILABLE** status on a module the customer expects Day 1, must go to SMPL leadership **before** implementation continues. That way the path forward is agreed up front and the resulting reporting limits are understood and signed off.

**Readiness Score summary** *(illustrative)*

| Field | Value |
|-------|-------|
| Readiness gates (Section 0) | **Pass** |
| Overall Readiness Score | **~74%** |
| Modules READY | Financial Reporting (consolidated), Executive Dashboards, MRR Reporting, Cash Forecasting, Scenario Planning |
| Modules PARTIAL (and why) | **Board Reporting** — Management P&L gross margin can’t reflect EU contractor labor split (F1) or Anaplan allocations (F2). **ARR Reporting** — Zuora UK bridge until sunset. **Pipeline Analytics** — “Contracting” stage split pending (9.1). **Workforce Planning** — DE cost centers (7.4). |
| Modules UNAVAILABLE (and why) | None Day 1. Executive Commentary (Phase 2) would be PARTIAL for UK / DE lines until F3 is fixed. |
| Biggest next improvement and expected score change | **Customer action** — book monthly allocation JEs in NetSuite (F2): Board Reporting → READY, largest single lift. **SMPL connector** — NetSuite ARM subledger lifts rev-rec detail. |

**Findings**

| # | Finding | Area (question ref) | Reporting consequence | Path | Customer owner | Target date |
|---|---------|---------------------|-----------------------|------|----------------|-------------|
| F1 | remote.com EU contractors posted as one monthly summary invoice; support and engineering mixed | 7.8 | EU support labor can’t be shown in cost of revenue; Management gross margin is overstated vs. the board pack | **Customer action** — split the remote.com JE by department at posting | Pat Morales | May close (BD+8) |
| F2 | Allocations applied in Anaplan, not booked in NetSuite | 7.9 | SMPL Management P&L shows costs as booked; gross margin and department opex will **not** match the Anaplan board P&L until allocations are booked | **Customer action** — monthly allocation JE in NetSuite from FY27 Q2. Until then: **accept limitation**, with a labeled bridge note in the board pack | Riley Cho (keys) + Pat Morales (JE) | FY27 Q2 (May 2026 close) |
| F3 | UK / DE accrue some vendors quarterly; UK actuals occasionally coded to G&A | 7.10–7.11 | Monthly variances on those lines are timing-driven; commentary flags them as data gaps rather than explaining them | **Customer action** — monthly accruals + coding check in UK / DE close checklist | Pat Morales | FY27 Q3 (Aug 2026 close) |
| F4 | Zuora UK subscriptions outside Stripe until sunset | 4.5, 4.7 | Board ARR for UK enterprise relies on the FP&A bridge workbook the customer maintains | **Accept limitation** until Zuora sunset (2026 H2) | Drew Kim | 2026 H2 |

**Sign-off**

| Role | Name | Date |
|------|------|------|
| Customer finance lead (owns books and fixes) | Sam Okonkwo (CFO); Pat Morales (Corp Controller) | 2026-04-02 |
| SMPL engagement lead | *(SMPL)* | 2026-04-02 |
| SMPL leadership review | **Required** — Board Reporting PARTIAL on a Day-1 module. Path agreed: F2 accepted as a labeled limitation until FY27 Q2. | 2026-04-01 |

---

## Call-time shortlist (~15 min) — how this sample maps

**Must cover (CEP + gates):**  
Covered: data ownership accepted + readiness gates pass (GAAP primary book; tax book excluded) → multi-entity + USD consol → Stripe/Salesforce/NetSuite/Workday (+ Zuora bridge) → **Board ARR canonical vs Sales ACV** → trials exclude / past_due exclude for Board → **committed min in ARR, overages out** → hybrid rev-rec → systems of record split CPQ vs billing → modules → FYE Jan 31.

**Should cover if time:**  
Pipeline stage “Contracting” ambiguity · contractors in workforce · multi Stripe accounts · invoice/ACH lag · 180-day reactivation · cost of revenue policy + EU contractor payroll gap · board logins acknowledged.

**Recommended extras (label clearly):**  
Driver-based forecast + four scenarios · close BD+8 · GL cutoff with **RE_BASE** for pre-OneWorld history · dual ARR intents documented · three EBITDA audiences · Anaplan allocations outside GL · quarterly UK/DE accruals · period-13 audit adjustments.

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
