# Sales commissions: ASC 340-40 capitalization — design

Status: draft for review. Nothing here is built or loaded yet.

## 1. Accounting rule

ASC 340-40 (issued with ASC 606) applies to every company reporting under US GAAP, public or private. IFRS 15 is substantially the same.

- **Capitalize** the incremental costs of obtaining a contract, meaning costs that wouldn't exist without the deal (sales commissions). Capitalize only if they're expected to be recovered.
- **Amortize** on a systematic basis that matches how the related service is delivered.
  - This includes anticipated renewals when the renewal commission is not commensurate with the initial one.
  - In that case the amortization period is the expected customer life, often 3–6 years in SaaS practice, capped by product and technology life.
- **Practical expedient:** expense immediately if the amortization period would be 12 months or less.
- **Presentation:** a deferred commissions asset (current and noncurrent), with amortization in S&M. Payouts are operating cash out, and the change in the asset is an operating working-capital line.
- **Impairment:** write down the asset if its carrying amount exceeds the remaining consideration, net of costs.
- **Tax:** generally deductible when paid, so the asset has a deferred tax liability.

What differs by company, and so must be configurable rather than hard-coded:

| Area | Typical variation |
|---|---|
| Basis | GAAP vs. cash/tax basis; many pre-audit companies expense as paid, then adopt retroactively |
| What is incremental | Commissions and accelerators yes; base salary no; manager overrides, SPIFs and payroll taxes are policy judgments |
| Amortization period | Contract term vs. expected customer life (commensurate test); portfolio vs. contract level |
| Payout timing | At booking, invoice or cash collection; monthly or quarterly; draws; clawback windows (accrued commissions liability if lagged) |
| Renewal commissions | Usually 12-month terms, so they're expensed under the expedient |

## 2. What the v5 dataset shows today (files, Oct 7 2026)

| | 2024 | 2025 | 2026 H1 |
|---|---|---|---|
| Commission cash in `Actual_cash_flow_bridge` | $2,994,004 | $3,152,318 | $1,805,612 |
| Payout detail (new + expansion + renewal) | not in data | not in data | $2,545,663 |
| GL 6200 Sales Commissions | $0 | $0 | $136,866 |

- **No commission expense in the GL.** Commissions aren't in any other S&M account either. There is no deferred commissions asset or accrued commissions liability.
- **The bridge doesn't add up.** It pays commission cash that the GL never pays, and makes up the difference with a negative `other_operating_cash_out`.
- **Renewal commissions are missing from the bridge.** The bridge carries only new-business payouts, so renewal commissions (about $0.74M, Jan–May 2026) are left out.
- **The renewal plan is missing.** `PLAN-RENEWAL` (2%) is used by `Actual_renewal_commissions` but isn't in `*_commission_plans`.
- **Payouts are paid at booking.** `payout_date` is the last day of the booking month, so there's no accrued liability.
- **The commensurate test isn't met.** New business pays 10% (15% accelerated) and expansion 6% (7.8%), against 2% on renewals. So new and expansion commissions amortize over customer life, and renewal commissions are expensed.

Illustrative straight-line result. It assumes pre-2024 payouts were steady at the January 2024 level.

| Life | 2025 amortization vs. cash | Asset at Jun 2026 |
|---|---|---|
| 36 months | $2.97M vs. $3.15M | $4.8M |
| 48 months | $2.96M vs. $3.15M | $6.3M |
| 60 months | $2.95M vs. $3.15M | $7.8M |

The dataset's gross dollar churn of 5–7% a year implies a life of 13+ years. That isn't a credible amortization period, so the life has to be a policy cap.

## 3. Data: what the GL update would contain

**Policy lives on the commission plan.** Add columns to `{v}_commission_plans`:
- `capitalize` (Y/N)
- `amortization_months`
- `payout_basis` (booking / invoice / collection)
- `payout_lag_months`

Also add the missing `PLAN-RENEWAL` row, with `capitalize = N`. This keeps every number sourced from data, and different clients can set different policies.

**Accounts:**
- 1250 Deferred Commissions – Current
- 1550 Deferred Commissions – Noncurrent
- 6200 Sales Commissions – Amortization
- 6210 Sales Commissions – Expensed (renewals and other items under the expedient)
- 2150 Accrued Commissions, only if a plan has a payout lag

**Monthly entries:**
- **Payout, capitalized plans:** debit 1250/1550, credit cash.
- **Payout, expensed plans:** debit 6210, credit cash.
- **Amortization:** debit 6200, credit 1250, straight-line by monthly cohort.
- **Reclass:** move the next 12 months of amortization from 1550 to 1250.

**Payout sources (as built in v6):**
- 2026 Actual comes from the payout detail files: new business and expansion Jan–Jun, renewals Jan–May.
- Every other month, including 2024–2025, Budget, Forecast and June 2026 renewals, is estimated:
  - new business and expansion = ARR waterfall × the plan's 2026 effective rate (0.14924 for new business, 0.07560 for expansion);
  - renewals = beginning ARR × the Jan–May 2026 renewal share (9.4875% a month) × 2%.
- The ARR waterfall is used because the Budget and Forecast `bookings_summary` files don't tie to their waterfalls (flagged).
- Every estimated row names its source in `{v}_commission_schedule.csv`.

**Opening balance (Jan 2024):** a cohort ladder of pre-2024 payouts creates the opening asset, offset to opening equity.

**Cash recalibration (as built):**
- Opening Jan 2024 cash rises by $9,535,241.36. That is the commission cash paid Feb 2024–Jun 2026, less the v5 6200 expense it replaces.
- Opening equity rises by that amount plus the $2,823,928.44 opening asset.
- June 2026 cash is unchanged, and the lowest Actual cash is $20.1M.
- Budget and Forecast Dec 2026 cash become $27.6M and $28.7M (was about $31M), because payouts are now cash out in full.

**Statement effects:**
- Net income falls by about $3M a year (amortization plus expensed renewals), because today the GL books almost none of this expense.
- The bridge's `other_operating_cash_out` should stop being negative for this reason. The separate payroll gap remains.

**Tie-out checks:** add these to `v5_tie_out.py`, carried into v6:
- payouts = capitalized + expensed;
- each period: change in deferred commissions = capitalized − amortization;
- current portion = next-12-month amortization;
- bridge commission cash = all payouts.

**Schema question:** the balance sheet and cash flow statement files have no deferred commissions columns. Either add `deferred_commissions` (BS) and `change_in_deferred_commissions` (CFS), or fold both into prepaids. See decision 3.

## 4. Code changes (one PR each)

1. **GL balance sheet** (`gl_balance_sheet.py`).
   - Map an expense_type of "deferred commissions" to a new `deferred_commissions` line, as operating working capital.
   - Today a noncurrent asset would land in `other_assets`, whose change is classified as investing. That's wrong for commissions.
2. **Cash forecast** (`forecast_cash_flow_engine`, bridge).
   - Commission cash = bookings × plan rate, shifted by the payout lag.
   - The `commission_pct_of_sm` driver (Actual 13.5%, Forecast 8%) applies a percentage to S&M expense, which no longer equals cash once commissions are capitalized. Keep it only as a labeled fallback when no bookings are loaded.
3. **Cash waterfall drill-down** (`cash_flow_gl_drilldown_service`). Commission cash drills into payout detail, not GL expense rows.
4. **Budget Engine.**
   - Commission cost = planned bookings (ARR bridge new / expansion / renewal) × plan rate. Reconcile it to the variable on-target earnings (variable OTE) input, which equals rate × quota.
   - Add a deferred commissions roll-forward (beginning balance from the loaded Dec close + capitalized − amortization). The P&L shows amortization and cash shows payouts.
   - Add a change-in-deferred-commissions line to cash from operations, and a balance sheet line.
5. **Forecast Engine.** Same roll-forward; it has no commission logic today.
6. **Client validation and readiness.** Detect policy from the chart of accounts (is a deferred commissions asset present?). Check that comp-system payouts tie to the change in deferred commissions + amortization + expensed + the change in accrued commissions. Flag payouts with no GL counterpart, which is our current state.
7. **Metrics and commentary.** State the CAC, payback and magic-number basis. Make the MD&A S&M commentary explain amortization vs. cash.

## 5. Decisions (accepted)

1. **Amortization life:** 60 months for new-logo and expansion commissions.
2. **Renewal commissions:** expensed under the 12-month practical expedient.
3. **Presentation:**
   - Balance sheet: new `deferred_commissions_current` / `deferred_commissions_noncurrent` lines (GL 1250 / 1550).
   - Cash flow: `change_in_deferred_commissions` in operating cash flow.
4. **Cash target:** keep June 2026 Actual cash at about $30M. The v6 build leaves it unchanged at $30,138,650.97.
5. **CAC basis:** GAAP S&M by default, with a cash variant shown.
6. **Where the policy comes from:** the onboarding questionnaire, checked against the GL.
   - Engines show the policy read-only. Only forward levers are adjustable: rates, attainment, bookings mix and payout timing.
   - Actuals always come from the GL as booked.
7. **Verification is never minimized.** Every answer is checked against the books (section 7), and a conflict limits the affected modules until the customer resolves it.

## 6. Onboarding questionnaire (7.14–7.20)

| # | Question | Choices | Used by |
|---|---|---|---|
| 7.14 | Sales commissions on new / expansion contracts | capitalized / expensed / no commissions / not sure | engines, checks |
| 7.15 | Amortization months, new business (if capitalized) | 12–84 | engines (expense), amortization check |
| 7.16 | Amortization months, expansion (if capitalized) | 12–84 | engines, amortization check |
| 7.17 | Renewal commissions | expensed / capitalized / not paid | engines |
| 7.18 | When commissions are paid | month of booking / month after / quarter after / on customer payment | engines (cash timing), accrual check |
| 7.19 | Employer payroll tax on commissions | expensed / capitalized | engines |
| 7.20 | Payout system of record | comp tool / payroll export / spreadsheet / none | payout checks |

The questions form the "Commission Policy Gate". The gate is unresolved when 7.14 is "not sure", or when a required follow-up is unanswered. 7.15 and 7.16 are required only when commissions are capitalized. While the gate is unresolved, Cash Forecasting, Scenario Planning and Board Reporting stay PARTIAL.

## 7. Checks: questionnaire vs books

These run on every readiness load (#223). If a fact can't be read, that check is skipped, never assumed.

| Check | Conflict when |
|---|---|
| Deferred commissions in GL | capitalized but no asset; expensed / none but an asset exists |
| Commission expense in GL | commissions paid but no commission expense in 12 months; "no commissions" but expense exists |
| Amortization period vs GL | deferred balance is more months of commission expense than the stated period allows |
| Accrued commissions | payouts lag bookings but there is no accrued liability (an unexpected accrual is a review) |
| Payouts tie to GL | payouts ≠ expense + Δ deferred − Δ accrued, beyond 1% or $1,000 |
| Payout detail | payouts are said to be in a system but none are loaded (no system at all is a review) |

- **Today's production data (v5):** the deferred commissions and payout tie-out checks both conflict. Jan–May 2026 payouts are $2.20M against $0.10M booked.
- **v6:** all six checks pass, and payouts tie to the GL with a $0 difference.

Statements also fail validation on any GL balance sheet account the app can't classify, or any cash flow activity it can't place (#222). An unknown account can no longer hide in the totals.

## 8. Status

| Item | PR | State |
|---|---|---|
| Design | #220 | this doc |
| Data v6 scripts + tie-out | #221 | 0 failing checks; mutation test catches 10 of 10 planted errors |
| GL statements: deferred commissions lines, unclassified-account validations | #222 | needed before the v6 load |
| Readiness questionnaire + checks | #223 | stacked on #222 |
| v6 load | — | dry run after #222 deploys; commit only with Matt's OK |
| Cash forecast commission cash (bookings × rate, payout lag) and drill-down to payouts | next | |
| Budget Engine and Forecast Engine deferred commissions roll-forward | next | |
| Metrics (CAC GAAP and cash) and MD&A S&M commentary | next | |

## 9. Future list

- **Sandbox (policy what-if):** let a customer see their numbers under a different commission policy, such as an expensed vs capitalized comparison. It is not a core need, because companies with audited GAAP books already have a policy. It's worth having so we can say we support it.
- **Deferred tax** on deferred commissions (book/tax difference).
- **Impairment test** of the deferred commissions asset when plans or retention change.
- **Life from data:** derive the amortization period from logo churn per client, as a cross-check on the answer to 7.15.
