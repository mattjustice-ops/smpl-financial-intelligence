# Financial Dashboard — Cash Flow & Retained Earnings Logic

> **Scope: customer / production GL construction methodology**
>
> This document is the **authoritative construction methodology** for building three-statement
> financials (P&L, balance sheet, cash flow) from a customer GL / warehouse for **onboarding,
> production statement construction, and Q&A bot source material**.
>
> **Does not change** current SMPL Demo Co / Board Platform / Forecast Engine demo dashboard
> behavior. Demo and lab surfaces may retain known seed exceptions and “all tie as is” with
> documented `data_mismatch` inventory — do **not** rewrite demo HTML/JS/seed data to match
> this methodology. Customer builds **must** follow this doc.
>
> **Cutoff date is per-org, not fixed.** October 2022 appears below only as a **pedagogical
> example**. Parameterize each customer as:
>
> | Parameter | Meaning |
> |---|---|
> | `gl_activity_start_period` | First period for which GL activity is queried (not company inception) |
> | Opening trial balance | Point-in-time TB as of the day before `gl_activity_start_period` |
> | `RE_BASE` | Known ending retained earnings as of that same cutoff |
>
> Related: [reconcile_financial_statements.md](./reconcile_financial_statements.md) (demo FE↔Board
> inventory), [data_integrity_framework.md](./data_integrity_framework.md), [README.md](./README.md).

---

Generic, company-agnostic reference for building a three-statement financial dashboard
from a GL database (Sage, NetSuite, QuickBooks, etc.) where data is queried from a
**cutoff date** (`gl_activity_start_period`) rather than company inception.

Warehouse / BI tools may expose opaque column IDs. This doc uses **semantic names**
(`pl_rollup`, `bs_rollup`, `scf_rollup`, `dept`, etc.). Map them to the customer’s
actual warehouse columns at onboarding.

---

## Core Problem: GL queries return activity, not balances

When you query a GL system for a date range, you get **changes** — debits and credits
for that period. To show ending balances, you must add those changes to a known opening
balance at your cutoff date.

This applies to both the balance sheet and retained earnings. It is the root cause of
most balance sheet errors in dashboards built from GL exports.

---

## Part 1: Retained Earnings

### The Rule

**Never use the GL balance of the Retained Earnings account directly.**

The GL balance of account 3300 (or equivalent) accumulates all historical journal entries
including year-end close entries, AJEs, and reclassifications that do not match a simple
accumulation of monthly net income. Use the GL balance only as a check — never as the
displayed value.

Instead, compute rolling RE explicitly:

```
RE(month M) = RE_BASE + SUM(net_income for all months from cutoff through M-1)
```

Where:
- `RE_BASE` = the known ending RE balance as of the cutoff (day before `gl_activity_start_period`)
- The sum runs through month **M−1** because the balance sheet convention is:
  RE shown in month M = **opening** RE for month M = RE after all prior periods have closed

### Display Convention

| Balance Sheet Line | Value |
|---|---|
| Retained Earnings | `RE_BASE + SUM(NI, cutoff through M−1)` |
| Net Income (Loss) | Current month NI only |
| Total Equity | Retained Earnings + Net Income + all other equity accounts |

These two lines must be one combined row (not two separate subtotals) to avoid
double-counting in the equity total.

### Implementation Pattern

```javascript
// Step 1: RE_BASE from opening TB / known close as of cutoff (example value only)
const RE_BASE = -11983671.24;  // org-specific; set from opening TB

// Step 2: Walk ALL months from gl_activity_start_period forward, accumulating ending RE
const endingRE = {};
let re = RE_BASE;
for (const mo of allMonthsSorted) {
  re += niByMonth[mo] || 0;
  endingRE[mo] = re;
}

// Step 3: For each display month, opening RE = prior month's ending RE
for (let i = 0; i < allMonthsSorted.length; i++) {
  const mo = allMonthsSorted[i];
  const prior = allMonthsSorted[i - 1];
  displayRE[mo]  = prior !== undefined ? endingRE[prior] : RE_BASE;
  displayNI[mo]  = niByMonth[mo] || 0;
}
```

### Computing Net Income From GL

**Critical gotcha:** In most GL systems (including Sage), ALL P&L amounts are stored
as **positive numbers** regardless of type — revenue, COGS, and expenses are all positive.
A raw `SUM()` across all P&L entries gives a wildly wrong answer (roughly 2× revenue).

You must categorize each rollup key and apply signs explicitly:

```javascript
const rev  = REVENUE_KEYS.reduce((s, k) => s + (byRollup[k] || 0), 0);
const cogs = COGS_KEYS.reduce((s, k)    => s + (byRollup[k] || 0), 0);
const opex = OPEX_KEYS.reduce((s, k)    => s + (byRollup[k] || 0), 0);
const da   = byRollup[DA_KEY] || 0;
const oi   = OI_KEYS.reduce((s, k) => s + (byRollup[k] || 0), 0)
           - da
           - OE_KEYS.reduce((s, k) => s + (byRollup[k] || 0), 0);
ni = rev - cogs - opex + oi;
```

NI will be negative for a loss-making company. RE will grow more negative over time.

---

## Part 2: Cash Flow Statement (Indirect Method)

### Structure

```
Net Income (Loss)
Add back non-cash items:
  + Depreciation & Amortization
  + Stock-Based Compensation
  + Capitalized Contract Cost amortization (net)
  + Software capitalization / amortization activity
  + Non-cash interest expense
  + Change in fair value of warrants / derivatives
Changes in working capital:
  - Increase in AR                   (asset up = cash use)
  - Increase in Prepaid/Other assets (asset up = cash use)
  + Increase in AP                   (liability up = cash source)
  + Increase in Accrued liabilities  (liability up = cash source)
  + Increase in Deferred Revenue     (liability up = cash source)
= Cash from Operations (CFO)

Investing Activities:
  - Capital expenditures / software capitalization (additions to fixed assets)
  - Deposits and long-term prepaid (changes in non-current assets)
= Cash from Investing

Financing Activities:
  - Equity issuances (changes in equity accounts, net of non-cash items)
  - Debt proceeds / repayments (changes in note payable accounts)
= Cash from Financing

Net Change in Cash = CFO + Investing + Financing
Ending Cash = Beginning Cash + Net Change
```

### The Opening Balance Offset

For any account whose history you're querying from a cutoff (not inception), the
ending balance is:

```
ending_balance[acct][period] = OPENING[acct] + SUM(GL activity from cutoff through period)
```

Where `OPENING[acct]` = the known ending balance of that account as of the cutoff date
(from the opening trial balance). **This must be added for every account that has
pre-cutoff history** — including cash, AR, AP, deferred revenue, equity accounts, and
especially fixed assets with accumulated depreciation.

Failing to add the opening balance is the most common source of wrong BS / CF numbers
when querying from a non-inception cutoff.

### Working Capital Formula

```javascript
// Asset accounts: increase in asset = use of cash (subtract delta)
for (const acct of WC_ASSET_ACCOUNTS) {
  const delta = endingBal(acct, curPeriod) - endingBal(acct, priorPeriod);
  wc -= delta;
}

// Liability accounts: increase in liability = source of cash (subtract delta,
// but liabilities are credit-normal so their "increase" is a more-negative or
// more-positive number depending on sign convention — normalize first)
for (const acct of WC_LIABILITY_ACCOUNTS) {
  const delta = endingBal(acct, curPeriod) - endingBal(acct, priorPeriod);
  wc -= delta;  // same sign as assets if liabilities are stored positive-normal
                // flip to: wc += delta  if liabilities are stored credit-normal (negative)
}
```

Sign convention note: If your GL stores liabilities as negative (credit-normal), a
"growing" liability means the balance becomes more negative — `delta` is negative —
so subtracting it adds to CFO (correct). Confirm your convention before coding.

### Dept 299 ("Balance Sheet Activity") — The Non-Cash Tag

All GL entries for a given account can be split into:
- **Non-cash / purely-BS activity** — tagged with department `299` (label: "Balance Sheet Activity")
- **Operating or cash activity** — all other department tags

This tagging convention is the mechanism that makes the CF statement correct for
**mixed accounts** — accounts where some activity is non-cash and some is cash:

| Account type | Example | Dept 299 entries | Other dept entries |
|---|---|---|---|
| Accrued commissions | 2500 | Accrual entries (non-cash) | Commission payments (cash out) |
| Capitalized software | 1750 | Write-offs / non-cash adj | Actual capitalization purchases |
| APIC / equity | 3311 | SBC expense offset (non-cash) | Equity issuance for cash |

**The split rule:**
```
Total BS change for account = non_cash_change (dept 299) + cash_change (other depts)
Non-cash addback to CFO = sum of dept-299 activity across non-cash accounts
Working capital change   = total BS change minus the dept-299 portion
```

For accounts that are exclusively non-cash (e.g., APIC-SBC acct 3311, APIC-Series modifications
acct 3305), 100% of the activity is dept 299 and none enters working capital.

For accounts like deferred commissions, the WC computation should only include the
non-dept-299 (cash-affecting) portion, and the dept-299 portion flows through the
non-cash addback line (cap_comm_net).

**In the SCF query** (GL entries tagged `pl_rollup = 'SCF'`), filtering by
`dept = 'Balance Sheet Activity'` (dept 299) isolates the non-cash equity entries
(e.g., Series Preferred APIC modification) that are invisible to both the P&L query
and the regular BS query.

```javascript
// From SCF query results, isolate dept-299 non-cash items by account
if (acct === '3305' && dept === 'Balance Sheet Activity') {
  scf3305ByMo[mo] = (scf3305ByMo[mo] || 0) + amt;
}
// Total SCF non-cash (all accounts, dept 299)
scfNonCashByMo[mo] = (scfNonCashByMo[mo] || 0) + amt;
```

### Non-Cash Items: The Three Categories

**Category 1 — Captured by BS delta automatically**
These show up as changes in BS accounts and are already reflected in working capital:
- Accrued expenses, AP, deferred revenue

**Category 2 — Require explicit add-back; NOT captured by WC**
These are P&L expenses that did not consume cash. Must be added back to NI explicitly:
- D&A — P&L expense with no cash counterpart (BS counterpart is accum depr, tracked separately)
- Stock-based compensation — P&L expense offsetting an APIC credit (BS equity change)
- Non-cash interest — P&L expense offsetting a note discount or warrant liability
- Fair value changes on warrant liabilities — P&L with BS liability counterpart

**Category 3 — GL-tagged SCF items; missed by both BS query and P&L query**
Some transactions are tagged with a separate SCF rollup in the GL and don't appear
in either the P&L rollup filter or the BS rollup filter. Examples:
- Equity-to-equity reclassifications with cash flow statement impact (e.g., Series APIC modifications)
- Capitalized commission amortization entries tagged directly to SCF

To capture these, run a third query filtered to `pl_rollup = 'SCF'` and accumulate
separately. Then add to the non-cash subtotal:

```javascript
// Third query: accounts tagged SCF (not P&L, not Balance Sheet)
nc.special_noncash = scfActivityByMonth[period] || 0;
noncash_total += nc.special_noncash;
```

### Quarterly Roll-Up Requirement

**Every detail field must be initialized AND accumulated in the quarterly aggregation.**
If only totals (`noncash_total`, `wc_total`) are tracked in the quarter object and
individual lines (`da`, `stock_comp`, `series_seed_apic`, etc.) are not, quarterly CF
will show blank/dashes for detail lines while the totals appear correct.

Pattern:

```javascript
if (!qtrs[q]) qtrs[q] = {
  beg_cash: d.beg_cash, end_cash: 0, net_cash: 0, ni: 0,
  noncash_total: 0, da: 0, stock_comp: 0, special_noncash: 0, /* ...all detail fields */
  wc_total: 0, wc_ar: 0, wc_prepaid: 0, wc_ap: 0, wc_accrued: 0, wc_deferred_rev: 0,
  cfo: 0, investing_total: 0, financing_total: 0
};
const qt = qtrs[q];
qt.ni += ni;
qt.da += (d.da || 0);
qt.stock_comp += (d.stock_comp || 0);
qt.special_noncash += (d.special_noncash || 0);
qt.noncash_total += (d.noncash_total || 0);
qt.wc_ar += (d.wc_ar || 0);
/* ... every other detail field ... */
qt.cfo += ni + (d.noncash_total || 0) + (d.wc_total || 0);
qt.end_cash = d.end_cash;
qt.net_cash = qt.end_cash - qt.beg_cash;
```

### Verification Chain

A correct CF statement satisfies all three checks simultaneously:

```
1. CFO = NI + noncash_total + wc_total
2. net_cash = CFO + investing_total + financing_total
3. end_cash = beg_cash + net_cash
4. end_cash = SUM(cash account balances at period end)   ← ties to BS
```

Check 4 ties CF to the balance sheet. If it fails, something is missing from either
the CF (a cash-affecting transaction not classified) or the BS cash group (missing account).

---

## Part 3: Common Failures and Fixes

| Symptom | Root Cause | Fix |
|---|---|---|
| RE drifts vs Excel over time | Using GL balance of 3300 instead of rolling computation | Compute RE from RE_BASE + accumulated NI |
| NI is wrong by ~2× revenue | Raw SUM of all P&L amounts | Categorize by rollup, apply formula explicitly |
| BS doesn't balance | Opening balances missing for pre-cutoff accounts | Add OPENING[acct] offset to every BS account balance |
| CF end_cash ≠ BS cash | Missing GL-tagged SCF transactions | Run third query for SCF rollup; include in non-cash |
| Quarterly CF shows dashes | Detail fields not in quarter init/accumulation | Add every render-line field to both init object and accumulation block |
| Non-cash addback doubles WC | Same account in both WC loop and non-cash | Exclude non-cash counterpart accounts from WC (e.g., exclude cap comm asset from prepaid WC) |
| Balance sheet balance off by NI | RE and NI counted as two separate subtotals | Combine into one equity row with two sub-rows |
| Wrong balances when using warehouse/GL activity only | Forgot OPENING offset | Always: balance = cumulative_GL_activity + OPENING[acct] |

---

## Part 4: Toggle — Model View vs. Audited FS View

Some companies present D&A differently in their management model vs. audited financials:

- **Model view:** D&A shown as a single line below EBITDA (in Other Income/Expense)
- **Audit view:** D&A reclassified into OpEx by department (R&D / S&M / G&A)

### Implementation

Pre-compute both dept breakdowns at data load time. Do **not** re-query on toggle —
toggle just swaps which pre-built object is used.

```javascript
// At load time, build two versions
const deptModel = buildDepts(rows, excludeDA = true);   // D&A excluded from dept totals
const deptAudit = buildDepts(rows, excludeDA = false);  // D&A included in dept totals

store.month[mo] = {
  ...baseMetrics,
  depts:       deptModel,   // used when toggle = 'model'
  depts_audit: deptAudit,   // used when toggle = 'audit'
};

// At render time
function activePL(month) {
  const d = store.month[month];
  return (ACTIVE_VIEW === 'audit' && d.depts_audit)
    ? { ...d, depts: d.depts_audit }
    : d;
}
```

Remove any `LIVE_LOADED` guard from the toggle setter — the toggle must work even
before live data loads (baked fallback must also have both dept objects).

---

## Part 5: The Rollup Mapping System

### Why It Exists

GL systems store transactions by account number and department. They do not
natively know whether account 1300 belongs on the balance sheet, maps to "Prepaid" on
the CF working capital section, or whether account 3311 is a non-cash equity item.

That classification lives in a **separate mapping table** maintained by the accounting
team. Every time a new GL account is created, it gets a row added to this table with
three rollup assignments. The data warehouse joins the mapping table to raw GL activity
before exposing it to BI / reporting, so every query automatically gets the rollup columns.

### The Three Rollup Columns

| Column (semantic) | Purpose | Example values |
|---|---|---|
| **P&L Rollup** (`pl_rollup`) | Which income statement line this account feeds, or which BS bucket it belongs to | `'Revenue - Direct'`, `'Gross Pay'`, `'Stock Compensation'`, `'Balance Sheet'`, `'SCF'` |
| **BS Rollup** (`bs_rollup`) | Whether this account is an income statement item (`'P&L'`) or a BS category | `'P&L'`, `NULL` (for BS-only accounts), `'Cash'`, `'Accounts Receivable'`, `'Equity'` |
| **SCF Rollup** (`scf_rollup`) | Which cash flow statement section / line this account maps to | `'Operating - Non-cash'`, `'Working Capital - AR'`, `'Investing'`, `'Financing'`, etc. |

> **Note:** The P&L Rollup column does double duty. For income statement accounts it
> holds the specific IS line (`'Revenue - Direct'`, `'COGS - Hosting'`). For balance
> sheet accounts it holds the BS bucket (`'Balance Sheet'`). For equity-side non-cash
> items that flow directly to CF, it holds `'SCF'`. This is how the three warehouse
> queries filter to the right subset of GL data.

### How to Query Each Statement

```sql
-- Income Statement: filter on BS Rollup = 'P&L'
WHERE bs_rollup = 'P&L'
-- then group by pl_rollup to get 'Revenue - Direct', 'Gross Pay', etc.

-- Balance Sheet: filter on P&L Rollup = 'Balance Sheet'
WHERE pl_rollup = 'Balance Sheet'
-- (do NOT use bs_rollup != 'P&L' — NULL rows are excluded by != in SQL)

-- SCF non-cash equity items: filter on P&L Rollup = 'SCF'
WHERE pl_rollup = 'SCF'
-- these are non-cash entries not captured by either P&L or BS filters
```

### Account Mapping Examples

The table below shows representative GL accounts with their rollup assignments.
New accounts get a row added here whenever they are created in the GL system.

| Acct | Name | P&L Rollup | BS Rollup | SCF Rollup | Notes |
|---|---|---|---|---|---|
| 1100 | Operating Checking | Balance Sheet | NULL | Working Capital - Cash | Flows to BS cash group; CF derives cash change from opening→closing delta |
| 1300 | Prepaid Expenses | Balance Sheet | NULL | Working Capital - Prepaid | WC item in CFO |
| 1550 | Cap Contract Costs ST | Balance Sheet | NULL | Non-cash - Cap Comm | Excluded from WC; non-cash addback handles it separately |
| 1750 | Capitalized Software | Balance Sheet | NULL | Investing | Fixed asset additions → investing outflow |
| 1850 | Accum Amort - SW | Balance Sheet | NULL | Non-cash - SW Amort | Non-cash; offset to D&A addback |
| 2100 | Accounts Payable | Balance Sheet | NULL | Working Capital - AP | WC item in CFO |
| 2520 | Deferred Revenue | Balance Sheet | NULL | Working Capital - Def Rev | WC item in CFO |
| 2610 | Note Payable | Balance Sheet | NULL | Financing | Debt draws/repayments |
| 3100 | Common Stock | Balance Sheet | NULL | Financing - Equity | Cash equity issuances |
| 3311 | APIC - Stock Comp | Balance Sheet | Balance Sheet | Non-cash - SBC | **Dept 299 only** — non-cash offset to SBC expense; excluded from financing |
| 3305 | APIC - Series Modification | SCF | NULL | Non-cash - APIC Adj | **SCF rollup** — not captured by BS query; requires separate SCF query |
| 4100 | Revenue - Direct | Revenue - Direct | P&L | Operating - Revenue | Standard P&L; flows to IS revenue line |
| 5000 | COGS - Hosting | COGS - Hosting | P&L | Operating - CFO (via NI) | P&L cost line |
| 6100 | Wages Expense | Gross Pay | P&L | Operating - CFO (via NI) | P&L opex line; cash leaves via payroll (AP or direct) |
| 6205 | Stock-Based Comp Exp | Stock Compensation | P&L | Non-cash - SBC addback | P&L debit; the cash-free entry is offset by 3311 credit (dept 299) |
| 9120 | Depreciation Expense | Depreciation & Amortization | P&L | Non-cash - D&A addback | P&L below EBITDA; non-cash addback in CFO |
| 9110 | Non-cash Interest | Interest Expense (non-cash) | P&L | Non-cash - Interest | Accrued discount amortization; non-cash addback |

---

## Part 6: Worked Example — Opening Balance + Two Months

This example walks through a minimal set of accounts to show exactly how GL activity
flows into the three statements. All amounts are illustrative. The cutoff month
(October 2022) is an **example** of `gl_activity_start_period − 1`; substitute the
customer’s actual cutoff.

### Setup: Account Mapping

| Acct | Name | P&L Rollup | BS Rollup | Dept 299 rule |
|---|---|---|---|---|
| 1100 | Cash | Balance Sheet | NULL | N/A |
| 1300 | Prepaid | Balance Sheet | NULL | N/A |
| 2100 | Accounts Payable | Balance Sheet | NULL | N/A |
| 3100 | APIC - Common | Balance Sheet | NULL | Cash equity issuances |
| 3300 | Retained Earnings | Balance Sheet | NULL | Computed — never query directly |
| 3311 | APIC - SBC | Balance Sheet | Balance Sheet | Dept 299 only (non-cash) |
| 4100 | Revenue | Revenue - Direct | P&L | N/A |
| 6100 | Wages Expense | Gross Pay | P&L | N/A |
| 6205 | SBC Expense | Stock Compensation | P&L | Dept 299 (mirrors 3311) |
| 9120 | D&A Expense | Depreciation & Amortization | P&L | N/A |

---

### Opening Balances (example cutoff — Oct 31, 2022)

These are loaded into the `OPENING` constant from a point-in-time GL trial balance at
the cutoff date (day before `gl_activity_start_period`).

| Acct | Opening Balance | Sign |
|---|---|---|
| 1100 Cash | $500 | Debit normal (positive) |
| 1300 Prepaid | $100 | Debit normal (positive) |
| 2100 AP | $50 | Credit normal (negative in TB; shown positive in BS) |
| 3100 APIC | $1,000 | Credit normal |
| 3300 RE | −$450 | Accumulated deficit (`RE_BASE`) |

**Balance check:** Assets $600 = Liabilities + Equity $600 ✓ (`$50 + $1,000 − $450`)

---

### Month 1 GL Activity (November 2022 — first activity period)

These are the individual journal entry lines that hit the GL in November:

| Date | Acct | Dept | Amount (directional) | P&L Rollup | BS Rollup | Description |
|---|---|---|---|---|---|---|
| Nov | 4100 Revenue | — | +$200 | Revenue - Direct | P&L | Customer invoice |
| Nov | 1100 Cash | — | +$200 | Balance Sheet | NULL | Cash receipt from customer |
| Nov | 6100 Wages | G&A | +$150 | Gross Pay | P&L | Payroll expense |
| Nov | 1100 Cash | — | −$150 | Balance Sheet | NULL | Payroll cash out |
| Nov | 6205 SBC Exp | G&A | +$20 | Stock Compensation | P&L | Non-cash SBC entry |
| Nov | 3311 APIC-SBC | 299 | +$20 | Balance Sheet | Balance Sheet | Non-cash SBC offset |
| Nov | 9120 D&A | — | +$10 | Depreciation & Amortization | P&L | Monthly amortization |
| Nov | 1300 Prepaid | — | −$10 | Balance Sheet | NULL | Prepaid amortization |

#### November → Income Statement
(Filter: `bs_rollup = 'P&L'`, group by `pl_rollup`)

```
Revenue - Direct      $200
Gross Pay            ($150)
Stock Compensation    ($20)
                     -----
EBITDA               $  30
D&A                  ($10)
                     -----
Net Income           $  20
```

#### November → Balance Sheet
(Each account = OPENING + cumulative GL activity through Nov)

| Account | Opening | Nov Activity | Nov Ending |
|---|---|---|---|
| 1100 Cash | $500 | +$200 − $150 = +$50 | $550 |
| 1300 Prepaid | $100 | −$10 | $90 |
| **Total Assets** | **$600** | | **$640** |
| 2100 AP | $50 | $0 | $50 |
| 3100 APIC | $1,000 | $0 | $1,000 |
| 3311 APIC-SBC | $0 | +$20 | $20 |
| RE (computed) | −$450 | — | −$450 (opening RE for Nov) |
| Net Income | — | $20 | $20 |
| **Total L&E** | **$600** | | **$640** ✓ |

> RE for November = RE_BASE (−$450) because November is the first display month.
> Net Income ($20) is shown separately as the current-period line.

#### November → Cash Flow (Indirect Method)

```
Net Income                          $20

Non-cash addbacks:
  D&A (from P&L)                   +$10
  Stock Comp (from P&L)            +$20  ← add back; offset by 3311 change (dept 299)
                                   -----
  Non-cash subtotal                 $30

Working Capital changes:
  Prepaid (1300): $90 − $100 = −$10   → asset decreased → +$10 source of cash
  AP (2100):      $50 − $50  = $0     → no change
  Note: 3311 change is dept 299 → excluded from WC
                                   -----
  WC subtotal                        +$10

CFO = $20 + $30 + $10 = $60

Investing:   $0
Financing:   $0

Net Cash Change:  $60
Beginning Cash:  $500  (OPENING[1100])
Ending Cash:     $560

Verify vs BS cash:  $550  ← MISMATCH ✗
```

Wait — the BS shows cash of $550 but CF shows $560. The difference is $10 — the
prepaid amortization. This reveals a sign error in the WC treatment: the prepaid
**decreased** (asset went down) which is a source of cash → should be +$10 in WC.

Let's verify: starting prepaid $100, ending prepaid $90 → delta = −$10.
WC formula: `wc -= delta` → `wc -= (−10)` → `wc += 10` → correct, +$10.

Then CFO = $20 + $30 + $10 = $60, but net cash change from BS is $50 ($550 − $500).
The discrepancy: SBC ($20 non-cash) is being double-counted — the $20 add-back is
correct, but the 3311 change must be **excluded from WC** or it will offset incorrectly.

**Corrected CF:**
```
NI                   $20
+ D&A add-back       $10
+ SBC add-back       $20  (non-cash — offset by 3311 dept 299, excluded from WC)
Non-cash subtotal    $30

WC:
  Prepaid (1300)    +$10  (asset down = source of cash)
  AP (2100)         $ 0
  3311 APIC-SBC     excluded (dept 299 = non-cash, not WC)
WC subtotal         +$10

CFO = $20 + $30 + $10 = $60  ← still wrong?
```

Reconciling: the prepaid went down −$10 but the P&L already reflects the $10 D&A
expense in NI. So if we add the D&A back (+$10) AND count the prepaid decrease as
WC (+$10), we double-count the $10.

This surfaces the key principle: **prepaid amortization is a non-cash item too** —
the prepaid reduction is the BS counterpart to D&A, so it should NOT appear in WC.
Only prepaid changes from new cash payments or actual consumption separate from D&A
belong in WC.

Corrected CF (excluding amortized prepaid from WC):
```
NI                    $20
+ D&A add-back        $10   (non-cash; BS counterpart = 1300 decrease, excluded from WC)
+ SBC add-back        $20   (non-cash; BS counterpart = 3311 dept-299, excluded from WC)
Non-cash subtotal     $30

WC: $0 (no cash-affecting prepaid/AP changes this month)

CFO = $20 + $30 = $50 ✓
Beginning Cash: $500
Ending Cash:    $550 ✓  matches BS
```

> **Key lesson:** Every non-cash addback has a BS counterpart. That counterpart account
> must be excluded from working capital, or you double-count the adjustment. Dept 299
> is the systematic way to flag this exclusion — when a BS account moves only via
> dept-299 entries, its entire change is non-cash and it belongs in the addback section,
> not WC.

---

### Month 2 GL Activity (December 2022)

| Date | Acct | Dept | Amount | P&L Rollup | BS Rollup | Description |
|---|---|---|---|---|---|---|
| Dec | 4100 Revenue | — | +$300 | Revenue - Direct | P&L | Customer invoice |
| Dec | 1100 Cash | — | +$300 | Balance Sheet | NULL | Cash receipt |
| Dec | 6100 Wages | G&A | +$180 | Gross Pay | P&L | Payroll |
| Dec | 1100 Cash | — | −$180 | Balance Sheet | NULL | Payroll cash out |
| Dec | 2100 AP | — | +$40 | Balance Sheet | NULL | New vendor bill accrued |
| Dec | 6100 Wages | G&A | +$40 | Gross Pay | P&L | (accrued, not yet paid) |
| Dec | 6205 SBC Exp | G&A | +$20 | Stock Compensation | P&L | Non-cash SBC |
| Dec | 3311 APIC-SBC | 299 | +$20 | Balance Sheet | Balance Sheet | Non-cash SBC offset |
| Dec | 9120 D&A | — | +$10 | Depreciation & Amortization | P&L | Monthly amortization |
| Dec | 1300 Prepaid | — | −$10 | Balance Sheet | NULL | Prepaid amortization |

#### December → Income Statement

```
Revenue               $300
Wages (cash)         ($180)
Wages (accrued)       ($40)
SBC                   ($20)
                      ----
EBITDA                $60
D&A                  ($10)
                      ----
Net Income            $50
```

#### December → Balance Sheet
(cumulative from opening through Dec)

| Account | Opening | After Nov | After Dec |
|---|---|---|---|
| 1100 Cash | $500 | $550 | $550 + $300 − $180 = **$670** |
| 1300 Prepaid | $100 | $90 | $90 − $10 = **$80** |
| **Total Assets** | $600 | $640 | **$750** |
| 2100 AP | $50 | $50 | $50 + $40 = **$90** |
| 3100 APIC | $1,000 | $1,000 | **$1,000** |
| 3311 APIC-SBC | $0 | $20 | $20 + $20 = **$40** |
| RE (opening for Dec) | — | — | **−$430** (= −$450 + $20 Nov NI) |
| Net Income | — | $20 | **$50** |
| **Total L&E** | $600 | $640 | **$750** ✓ |

> December opening RE = October RE_BASE (−$450) + November NI ($20) = −$430.
> This is the rolling RE computation — prior accumulated NI shifts into RE each month.

#### December → Cash Flow

```
NI                    $50
+ D&A add-back        $10   (non-cash; BS counterpart = prepaid decrease, excluded from WC)
+ SBC add-back        $20   (non-cash; BS counterpart = 3311 dept-299, excluded from WC)
Non-cash subtotal     $30

WC changes (cash-affecting only):
  AP (2100): Dec $90 − Nov $50 = +$40   → liability up = +$40 source of cash
WC subtotal           +$40

CFO = $50 + $30 + $40 = $120

Beginning Cash: $550 (Nov ending)
Ending Cash:    $670 ✓  matches BS cash
Net Change:     $120 ✓
```

> Note: the accrued payroll ($40) appears as both a P&L expense (reducing NI) and an AP
> increase (adding back in WC), netting to zero in CFO — as expected for an accrual not
> yet paid in cash.

---

## Part 7: What Warehouse GL Activity Looks Like (shape)

The following rows illustrate the **shape** of warehouse GL activity after the mapping
table is joined — semantic column names, rollup values, and dept tags. Amounts and
vendors are placeholders.

### How to read the columns

| Semantic column | What it contains |
|---|---|
| `account` | GL account number |
| `account_name` | Descriptive name in the GL chart of accounts |
| `posting_date` | Transaction date (used for period bucketing) |
| `pl_rollup` | IS line (`'Revenue - Direct'`) or BS class (`'Balance Sheet'`) or `'SCF'` for equity non-cash |
| `bs_rollup` | `'P&L'` for income statement accounts; granular BS category (`'Cash'`, `'Accounts Receivable'`, `'Equity'`, etc.) for others |
| `scf_rollup` | CF statement classification: `'P&L'`, `'Cash'`, `'Operations'`, `'Non-cash: Operating Adjustments'`, `'Financing'`, `'Investing'` |
| `dept` | Department tag — `'Balance Sheet Activity'` marks dept 299 (non-cash entries) |
| `vendor` | Vendor or payee name |
| `description` | Memo / journal entry description |
| `amount` | Directional amount — often all positive in the warehouse regardless of debit/credit |

---

### Sample Rows by Account Type

**Revenue (acct 4120 — Revenue - Direct)**
IS item: `bs_rollup = 'P&L'` routes it into the income statement query. `pl_rollup` gives the specific IS line.

| acct | acct_name | date | pl_rollup | bs_rollup | scf_rollup | dept | vendor | description | amount |
|---|---|---|---|---|---|---|---|---|---|
| 4120 | Revenue - Direct | 2026-01-31 | Revenue - Direct | P&L | P&L | *(null)* | *(null)* | Customer A: Monthly data mgmt services Jan 2026 | $10,000 |
| 4120 | Revenue - Direct | 2026-01-31 | Revenue - Direct | P&L | P&L | *(null)* | *(null)* | Customer B: Unlimited vCPU hours Jan 2026 | $38,000 |
| 4120 | Revenue - Direct | 2026-01-31 | Revenue - Direct | P&L | P&L | *(null)* | *(null)* | Customer C: Premium support Jan 2026 | $5,000 |

---

**COGS (acct 5110 — COGS - Compute)**
IS item, COGS dept. Multiple rows when compute cost is broken into billing sub-categories.

| acct | acct_name | date | pl_rollup | bs_rollup | scf_rollup | dept | vendor | description | amount |
|---|---|---|---|---|---|---|---|---|---|
| 5110 | COGS - Compute | 2026-01-31 | COGS - Hosting | P&L | P&L | COGS | Compute Vendor | Jan compute - Production (customer traffic) | $640,000 |
| 5110 | COGS - Compute | 2026-01-31 | COGS - Hosting | P&L | P&L | COGS | Compute Vendor | Jan compute - Production (shared infra) | $175,000 |
| 5110 | COGS - Compute | 2026-01-31 | COGS - Hosting | P&L | P&L | COGS | Compute Vendor | Jan compute - Internal (dev/test) | $50,000 |
| 5110 | COGS - Compute | 2026-01-31 | COGS - Hosting | P&L | P&L | COGS | Compute Vendor | Jan compute - Customer B | $5,000 |

---

**Wages (acct 6110 — Salaries & Wages)**
IS item, multiple depts. Note: negative rows are payroll reversals (prior-month PTO accrual reversed at month-open).

| acct | acct_name | date | pl_rollup | bs_rollup | scf_rollup | dept | vendor | description | amount |
|---|---|---|---|---|---|---|---|---|---|
| 6110 | Salaries & Wages | 2026-01-01 | Gross Pay | P&L | P&L | R&D | Payroll Provider | Reversed — Monthly PTO Accrual | −$104,000 |
| 6110 | Salaries & Wages | 2026-01-01 | Gross Pay | P&L | P&L | S&M | Payroll Provider | Reversed — Monthly PTO Accrual | −$6,300 |
| 6110 | Salaries & Wages | 2026-01-01 | Gross Pay | P&L | P&L | G&A | Payroll Provider | Reversed — Monthly PTO Accrual | −$27,000 |
| 6110 | Salaries & Wages | 2026-01-31 | Gross Pay | P&L | P&L | R&D | Payroll Provider | Jan payroll — R&D headcount | $285,000 |
| 6350 | Contractors | 2026-01-01 | Gross Pay | P&L | P&L | R&D | Contractor Agency | *(null)* | $9,000 |

---

**Depreciation (acct 9120 — Depreciation)**
IS item, below EBITDA. The `DA_KEY` filter isolates this in the NI formula.

| acct | acct_name | date | pl_rollup | bs_rollup | scf_rollup | dept | vendor | description | amount |
|---|---|---|---|---|---|---|---|---|---|
| 9120 | Depreciation | 2026-01-01 | Depreciation & Amortization | P&L | P&L | G&A | *(null)* | Depreciation - Office furniture | $180 |

---

**Accounts Receivable (acct 1210)**
BS item. `pl_rollup = 'Balance Sheet'`; `bs_rollup = 'Accounts Receivable'`. Dept is null — AR has no department tag.

| acct | acct_name | date | pl_rollup | bs_rollup | scf_rollup | dept | vendor | description | amount |
|---|---|---|---|---|---|---|---|---|---|
| 1210 | Accounts Receivable | 2026-01-02 | Balance Sheet | Accounts Receivable | Operations | *(null)* | *(null)* | Customer B invoice posted | $48,000 |
| 1210 | Accounts Receivable | 2026-01-16 | Balance Sheet | Accounts Receivable | Operations | *(null)* | *(null)* | Customer B payment received | −$18,900 |
| 1210 | Accounts Receivable | 2026-01-30 | Balance Sheet | Accounts Receivable | Operations | *(null)* | *(null)* | Customer A payment received | −$137,000 |

---

**Prepaid Expenses (acct 1300)**
BS item. Positive rows = new prepaid bills entered; negative rows = monthly amortization. `bs_rollup = 'Prepaid Expenses'`.

| acct | acct_name | date | pl_rollup | bs_rollup | scf_rollup | dept | vendor | description | amount |
|---|---|---|---|---|---|---|---|---|---|
| 1300 | Prepaid Expenses | 2026-01-01 | Balance Sheet | Prepaid Expenses | Operations | S&M | Vendor A | Prepaid — annual event sponsorship | $4,800 |
| 1300 | Prepaid Expenses | 2026-01-01 | Balance Sheet | Prepaid Expenses | Operations | G&A | Insurance Co | Prepaid — foreign casualty insurance | −$230 |
| 1300 | Prepaid Expenses | 2026-01-01 | Balance Sheet | Prepaid Expenses | Operations | R&D | Software Vendor | Prepaid — annual license fee | −$1,950 |
| 1300 | Prepaid Expenses | 2026-01-01 | Balance Sheet | Prepaid Expenses | Operations | G&A | Accounting Firm | Prepaid — monthly outsourced accounting | −$9,000 |

---

**Accounts Payable (acct 2100)**
BS item. `bs_rollup = 'AP & Accrued Liabilities'`; `scf_rollup = 'Operations'` (WC item).

| acct | acct_name | date | pl_rollup | bs_rollup | scf_rollup | dept | vendor | description | amount |
|---|---|---|---|---|---|---|---|---|---|
| 2100 | Accounts Payable | 2025-12-01 | Balance Sheet | AP & Accrued Liabilities | Operations | G&A | Software Vendor A | *(null)* | $4,200 |
| 2100 | Accounts Payable | 2025-12-01 | Balance Sheet | AP & Accrued Liabilities | Operations | S&M | Event Vendor | *(null)* | $18,000 |
| 2100 | Accounts Payable | 2025-12-01 | Balance Sheet | AP & Accrued Liabilities | Operations | R&D | Contractor Agency | *(null)* | $9,000 |
| 2100 | Accounts Payable | 2025-12-03 | Balance Sheet | AP & Accrued Liabilities | Operations | G&A | Payroll Provider | *(null)* | $31,000 |
| 2100 | Accounts Payable | 2025-12-03 | Balance Sheet | AP & Accrued Liabilities | Operations | G&A | Payroll Provider | *(null)* | −$7,000 |

---

**Deferred Revenue (acct 2520)**
BS item. `bs_rollup = 'Deferred Revenue'`; `scf_rollup = 'Operations'`.

| acct | acct_name | date | pl_rollup | bs_rollup | scf_rollup | dept | vendor | description | amount |
|---|---|---|---|---|---|---|---|---|---|
| 2520 | Deferred Revenue | 2025-12-01 | Balance Sheet | Deferred Revenue | Operations | *(null)* | *(null)* | *(null)* | $18,900 |
| 2520 | Deferred Revenue | 2025-12-01 | Balance Sheet | Deferred Revenue | Operations | *(null)* | *(null)* | Reversed — Customer A revenue accrual | $15,000 |
| 2520 | Deferred Revenue | 2025-12-31 | Balance Sheet | Deferred Revenue | Operations | *(null)* | *(null)* | *(null)* | $160,000 |

---

**APIC — Stock Comp (acct 3311) — the classic dept 299 non-cash entry**
BS item. `pl_rollup = 'Balance Sheet'` so it is captured by the BS query. `bs_rollup = 'Equity'`. `scf_rollup = 'Non-cash: Operating Adjustments'`. Crucially, `dept = 'Balance Sheet Activity'` (dept 299) — every row is non-cash, so the entire change in this account is excluded from WC and flows through as a non-cash addback.

| acct | acct_name | date | pl_rollup | bs_rollup | scf_rollup | dept | vendor | description | amount |
|---|---|---|---|---|---|---|---|---|---|
| 3311 | APIC - Stock Comp | 2026-01-31 | Balance Sheet | Equity | Non-cash: Operating Adjustments | **Balance Sheet Activity** | *(null)* | Monthly stock comp expense | $73,000 |
| 3311 | APIC - Stock Comp | 2025-12-31 | Balance Sheet | Equity | Non-cash: Operating Adjustments | **Balance Sheet Activity** | *(null)* | Monthly stock comp expense | $70,000 |
| 3311 | APIC - Stock Comp | 2025-12-31 | Balance Sheet | Equity | Non-cash: Operating Adjustments | **Balance Sheet Activity** | *(null)* | True-up SBC to agree to equity report | $4,500 |

The matching P&L entry (acct 6205 SBC Expense, `bs_rollup = 'P&L'`, `pl_rollup = 'Stock Compensation'`) is captured by the P&L query and reduces NI. The 3311 entry here is the offsetting BS credit — captured by the BS query, dept 299, excluded from WC, added back in non-cash.

---

**APIC — Series Modification (acct 3305) — the SCF rollup non-cash entry**
`pl_rollup = 'SCF'` — this is the key difference from 3311. It does **not** appear in the BS query (`pl_rollup = 'Balance Sheet'`) and does **not** appear in the P&L query (`bs_rollup = 'P&L'`). It is only captured by the third query (`pl_rollup = 'SCF'`). The dept 299 row is the non-cash addback; the null-dept rows are the equity reclassification entries.

| acct | acct_name | date | pl_rollup | bs_rollup | scf_rollup | dept | vendor | description | amount |
|---|---|---|---|---|---|---|---|---|---|
| 3305 | Series Preferred - APIC | 2025-12-31 | **SCF** | Equity | Financing | **Balance Sheet Activity** | *(null)* | Recognize increase in value — Series modification | $1,944,000 |
| 3305 | Series Preferred - APIC | 2025-12-31 | **SCF** | Equity | Financing | *(null)* | *(null)* | Reclass APIC between preferred series (reverse issuance) | −$163,000 |
| 3305 | Series Preferred - APIC | 2025-12-31 | **SCF** | Equity | Financing | *(null)* | *(null)* | Reclass APIC between preferred series (reverse issuance) | −$261,000 |

---

**Common Stock (acct 3100) — cash equity issuances**
`pl_rollup = 'SCF'` (equity accounts that drive financing cash). `scf_rollup = 'Financing'`. These entries record the par-value portion of option exercises; the APIC portion goes to a separate account.

| acct | acct_name | date | pl_rollup | bs_rollup | scf_rollup | dept | vendor | description | amount |
|---|---|---|---|---|---|---|---|---|---|
| 3100 | Common Stock | 2024-12-31 | SCF | Equity | Financing | *(null)* | *(null)* | Employee A options exercised | $2 |
| 3100 | Common Stock | 2024-11-14 | SCF | Equity | Financing | *(null)* | *(null)* | Employee B options exercised | $0.23 |

---

### Summary: How rollup values map to query filters

| `pl_rollup` | `bs_rollup` | Captured by | CF treatment |
|---|---|---|---|
| `'Revenue - Direct'` (or any IS line) | `'P&L'` | P&L query | Via NI |
| `'Balance Sheet'` | `'Cash'`, `'AR'`, `'Prepaid'`, etc. | BS query | WC change (cash-affecting activity) |
| `'Balance Sheet'` | `'Equity'` | BS query | Non-cash addback (if dept = 'Balance Sheet Activity') or financing (if dept ≠ 299) |
| `'SCF'` | `'Equity'` | SCF query only | Non-cash addback (if dept 299) or financing/reclassification (if null dept) |

> The reason three queries are needed: `pl_rollup = 'SCF'` accounts like 3305 are
> excluded from both the P&L filter (`bs_rollup = 'P&L'`) and the BS filter
> (`pl_rollup = 'Balance Sheet'`). Without the third query, their non-cash impact
> is silently omitted from CFO.

---

## Quick Reference: What to Query, What to Compute

| Data | Source | Notes |
|---|---|---|
| Monthly NI | GL P&L query → apply sign formula | Never raw sum |
| Retained Earnings | RE_BASE + accumulated NI | Never GL balance of RE account |
| BS account balances | GL BS query cumulative + OPENING offset | Every account needs opening offset |
| Non-cash P&L items | GL P&L query (D&A, SBC, etc.) | Identify by rollup key |
| SCF-tagged non-cash | Separate GL SCF query | Missed by both P&L and BS filters |
| Financing activities | BS equity + debt account deltas | Exclude non-cash equity accounts (e.g., APIC-SBC) |
| Ending cash | BS cash account sum | Must equal beg_cash + net_change |

---

## Demo / lab carve-out

| Surface | Policy |
|---|---|
| SMPL Demo Co Board / Forecast Engine / seed actuals | **Unchanged** by this doc. Known exceptions stay documented in [reconcile_financial_statements.md](./reconcile_financial_statements.md). |
| Customer onboarding & production GL → statements | **Must** follow this methodology (`gl_activity_start_period`, opening TB, `RE_BASE`, three-rollup queries, dept-299 / SCF rules). |
| Q&A / Copilot source material (customer orgs) | Prefer this doc + org mapping table over demo seed formulas. |
