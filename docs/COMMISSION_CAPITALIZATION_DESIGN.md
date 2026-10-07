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

**Payout sources:**
- 2026 Actual comes from the payout detail files.
- 2024–2025 comes from the bridge's commission cash, at summary level only. No rep detail exists for those years, and the gap will be flagged.
- Budget and Forecast are calculated as bookings × plan rate, using `*_bookings_summary` by type.

**Opening balance (Jan 2024):** a cohort ladder of pre-2024 payouts creates the opening asset, offset to opening equity.

**Cash recalibration:** the GL would start paying about $8.7M of commission cash over 30 months. The opening equity adjustment (currently $7.0M) is re-solved so that June 2026 cash stays about $30M and the $10M floor holds.

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

## 5. Decisions needed

1. **Amortization life for new-logo and expansion commissions.** The 13+ years implied by data isn't usable. Proposal: 60 months, with an option to derive it from logo churn per client and cap it.
2. **Renewal commissions:** expense under the 12-month expedient (proposed).
3. **Balance sheet and cash flow presentation:** new `deferred_commissions` columns (proposed) or fold into prepaids.
4. **Cash target:** recalibrate opening equity to keep June 2026 cash about $30M (proposed).
5. **CAC basis:** GAAP S&M (amortized), or cash commissions. Proposal: GAAP by default, with a cash variant shown.

## 6. Order of work

1. Code PR 1 (balance sheet line).
2. Data v6: build, tie-out and dry run; load only with explicit OK.
3. Code PRs 2–3 (cash forecast, drill-down).
4. Code PRs 4–5 (Budget Engine, Forecast Engine).
5. Code PRs 6–7 (validation, metrics and commentary).
