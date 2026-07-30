# SMPL.ai — Data Integrity & Tie-Out Framework
### For Cursor (build) + Claude API (runtime) + Finance Team (review)
### Zero-tolerance policy: every number displayed must trace to a warehouse row

> **Repo placement:** Normative **design target** under `docs/soc2/controls/`. See [README.md](./README.md) for product posture and honest implemented-vs-roadmap labels.  
> **Part 6 adaptation:** Day-to-day primary controls are **automated fail-closed gates** (not human sign-off before every send). Human checklist items → **IR / exceptions / periodic control testing**. Linked from [P15](../policies/P15_ai_llm_data_handling.md) §4.8.  
> **Customer statement construction:** For production GL → P&L / BS / CF builds (not demo seed), follow [financial_dashboard_cf_re_logic.md](./financial_dashboard_cf_re_logic.md).

---

## The Problem This Document Solves

Both Claude and Cursor can produce confident-looking outputs that are wrong.
Claude can hallucinate a number it doesn't have. Cursor can write code that
reads the wrong column, applies the wrong sign, or uses a stale cached value.
A CFO presenting phantom ARR to their board is a company-ending event for SMPL.

This document defines three layers of protection:
1. **Source tagging** — every number carries a provenance record
2. **Automated tie-out checks** — code that verifies outputs against source before display
3. **Human review artifacts** — a rendered tie-out report that Finance signs off on

---

## Part 1 — The Provenance Model

### Every number must have a source tag

Every value displayed in the Board Platform or Forecast Engine, and every number
Claude states in commentary or Copilot responses, must be traceable to exactly
one of these source types:

```
SOURCE_TYPE:
  WAREHOUSE   — read directly from a warehouse table/column
  COMPUTED    — derived mathematically from one or more WAREHOUSE values
  LEVER       — set by Finance team via a slider in the Forecast Engine
  BUDGET      — from the approved annual budget file (loaded once at year-start)
  DERIVED     — computed from COMPUTED values (e.g. margin = gp/revenue)
```

Values that are NOT acceptable:
```
PHANTOM     — stated with no traceable source (hallucination)
STALE       — from a prior period's cache that hasn't been refreshed
ESTIMATED   — approximated without disclosure
HARDCODED   — typed into code rather than read from data
```

### The source metadata object

Every data payload sent to Claude (in `CP_DATA`, `AI_CTX`, or any API context)
must include a `_sources` object that maps every metric to its warehouse origin:

```javascript
CP_DATA = {
  // The actual values Claude uses for commentary and answers
  arr_eop:          86100000,
  net_new_arr:       2655000,
  revenue:           7412000,
  gross_margin_pct:     0.792,
  ebitda:           -1297000,
  ending_cash:      70612000,
  nrr:                 1.008,
  headcount:             137,

  // The provenance record — Claude must only state values found here
  _sources: {
    arr_eop: {
      table:   'arr_waterfall',
      column:  'ending_arr',
      period:  '2026-06',
      org_id:  '<org_uuid>',
      value:   86100000,
      loaded_at: '2026-07-05T14:23:11Z',
      is_final: true
    },
    net_new_arr: {
      table:   'arr_waterfall',
      column:  'net_new_arr',
      period:  '2026-06',
      org_id:  '<org_uuid>',
      value:   2655000,
      loaded_at: '2026-07-05T14:23:11Z',
      is_final: true
    },
    revenue: {
      table:   'income_statement',
      column:  'revenue',
      period:  '2026-06',
      org_id:  '<org_uuid>',
      value:   7412000,
      loaded_at: '2026-07-05T14:23:11Z',
      is_final: true
    },
    gross_margin_pct: {
      source_type: 'COMPUTED',
      formula:     'gross_profit / revenue',
      inputs: {
        gross_profit: { table:'income_statement', column:'gross_profit', value:5874000 },
        revenue:      { table:'income_statement', column:'revenue',       value:7412000 }
      },
      computed_value: 0.7924,
      period: '2026-06'
    },
    ebitda: {
      table:   'income_statement',
      column:  'ebitda',
      period:  '2026-06',
      org_id:  '<org_uuid>',
      value:   -1297000,
      loaded_at: '2026-07-05T14:23:11Z',
      is_final: true
    },
    ending_cash: {
      // TWO sources — bank soft check (~$1000 timing) is NOT statement “rounding”
      // Closed-actuals CFS / BS cash identities still fail-closed at $1.00 (TOL_ACTUALS)
      primary: {
        table:  'bank_account_balances',
        column: 'ending_balance',
        date:   '2026-06-30',
        value:  70612000
      },
      secondary: {
        table:  'cash_flow_statement',
        column: 'ending_cash',
        period: '2026-06',
        value:  70612122
      },
      reconciliation_gap: 122,   // bank_timing_soft — flag if > $1000; not “rounding”
      value_used: 70612000       // bank balance is source of truth
    },
    nrr: {
      source_type: 'COMPUTED',
      formula:     '(beginning_arr + expansion + reactivation - contraction - churn) / beginning_arr',
      period:      '2026-06',
      computed_value: 1.0080
    },
    headcount: {
      table:   'headcount_plan',
      column:  'headcount_ending',
      period:  '2026-06',
      dept:    'ALL',
      value:   137,
      note:    'From Forecast_Headcount_Plan.csv June row — includes overhead not in Actual_Employees.csv'
    }
  }
}
```

---

## Part 2 — Claude's Runtime Rules (API System Prompt Enforcement)

### The system prompt that governs every Claude API call in SMPL

This prompt is prepended to every API call — Copilot queries, commentary
generation, and close roller calls. It enforces source discipline at the
model level.

```
SYSTEM PROMPT — SMPL DATA INTEGRITY RULES

You are SMPL's financial intelligence assistant. You have access to financial
data for {org_name} for the period ending {CLOSE_MONTH}.

CRITICAL RULES — violating these rules produces outputs that cannot be used:

1. ONLY STATE VALUES FROM _sources
   Every number you include in a response MUST appear in the _sources object
   provided in the context. If a user asks for a metric not in _sources,
   say: "I don't have {metric} in the current data package. Finance would
   need to add it to the next close package."
   NEVER estimate, interpolate, or recall a number from training data.

2. CITE THE SOURCE WHEN STATING A NUMBER
   Every number must be followed by its source in parentheses.
   Format: "$86.1M (arr_waterfall.ending_arr, period 2026-06)"
   In narrative responses, cite at least once per paragraph.
   In Copilot chat, cite the first occurrence of each metric.

3. NEVER DO MATH ON STATED VALUES
   If a user asks "what's the difference between ARR and budget?" and budget
   is not in _sources, do not compute it. Say: "Budget ARR for June is not
   in the current data package."
   Only perform math that is explicitly defined in _sources as a COMPUTED value.

4. FLAG STALE DATA
   If _sources shows loaded_at more than 48 hours ago, prefix your response:
   "Note: this data was loaded {X} hours ago. Values may not reflect today's
   position. Finance should confirm before using in board materials."

5. FLAG UNRECONCILED CASH
   If _sources.ending_cash.reconciliation_gap > 1000, prefix cash statements:
   "Note: bank balance ($X) and CFS ending cash ($Y) differ by $Z.
   Finance should reconcile before confirming this figure."

6. NEVER STATE FORWARD-LOOKING NUMBERS AS FACTS
   Forecast values (period > {CLOSE_MONTH}) are projections based on
   Finance's lever assumptions, not confirmed actuals. Always use language
   like "the current forecast shows", "based on current assumptions",
   "the model projects" — never "will be" or "is expected to be" as if certain.

7. THREE-PART RESPONSE FORMAT (Copilot only)
   Every Copilot answer must follow:
   PART 1: The direct answer with the sourced number
   PART 2: The root cause connecting operational metric to financial outcome
   PART 3: One specific recommended action

8. RESPONSE SELF-CHECK
   Before finalizing any response, verify:
   □ Every number appears in _sources
   □ Every number is cited with table.column and period
   □ No forecasts stated as facts
   □ No estimates or interpolations
   □ Stale data flagged if loaded_at > 48 hours
```

### What Claude does when asked about a metric it doesn't have

```
User: "What's our CAC by channel?"

Claude: "CAC by channel isn't in the current data package for June 2026.
The package includes marketing spend totals and pipeline created by channel
(marketing_spend.amount_spent and marketing_spend.pipeline_arr_created),
but customer acquisition cost requires new customer count by source channel,
which isn't currently loaded.

To add CAC to the package, Finance would need to include:
  - closed_won_arr by source channel (from opportunities table)
  - customer count by source channel

Would you like me to answer with pipeline efficiency (pipeline per dollar
spent) as a proxy? That IS in the current package."
```

This response is honest, traceable, and actionable — not a hallucinated number.

---

## Part 3 — Cursor's Build-Time Rules

### Every rendered value must have a data-source attribute

Cursor must add `data-source` attributes to every DOM element that displays
a financial number. This creates a machine-readable provenance trail that
can be audited without reading the code.

```html
<!-- BAD — no provenance -->
<div class="kpi-val">$86.1M</div>

<!-- GOOD — source tagged -->
<div class="kpi-val"
     data-source="arr_waterfall.ending_arr"
     data-period="2026-06"
     data-loaded="2026-07-05T14:23Z"
     data-is-final="true">
  $86.1M
</div>

<!-- COMPUTED value — show formula -->
<div class="kpi-val"
     data-source="COMPUTED:gross_profit/revenue"
     data-inputs="income_statement.gross_profit,income_statement.revenue"
     data-period="2026-06">
  79.2%
</div>

<!-- FORECAST value — clearly marked -->
<div class="kpi-val"
     data-source="forecast_engine.computePeriod"
     data-period="2026-07"
     data-scenario="base"
     data-lever-state="nb=1.0,churn=1.0,cogs=0.29"
     data-is-forecast="true">
  $88.1M
</div>
```

### The audit overlay (Cursor must build this)

A hidden panel toggled by a keyboard shortcut (`Ctrl+Shift+A` or `Cmd+Shift+A`)
that reveals all `data-source` attributes inline next to their values.
Finance uses this during close review to verify every number.

```javascript
// Audit overlay toggle
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'A') {
    toggleAuditOverlay();
  }
});

function toggleAuditOverlay() {
  const isActive = document.body.classList.toggle('audit-mode');
  if (isActive) {
    // Show source tags next to every data-source element
    document.querySelectorAll('[data-source]').forEach(el => {
      const tag = document.createElement('span');
      tag.className = 'audit-tag';
      tag.textContent = `[${el.dataset.source} · ${el.dataset.period}]`;
      tag.style.cssText = 'font-size:8px;color:#BA7517;margin-left:4px;font-family:monospace';
      el.parentNode.insertBefore(tag, el.nextSibling);
    });
  } else {
    document.querySelectorAll('.audit-tag').forEach(t => t.remove());
  }
}
```

In audit mode, the dashboard looks like:
```
$86.1M [arr_waterfall.ending_arr · 2026-06]
79.2%  [COMPUTED:gross_profit/revenue · 2026-06]
$2.655M [arr_waterfall.net_new_arr · 2026-06]
```

---

## Part 4 — The Tie-Out Report

### What it is

A machine-generated HTML report produced by the close roller after every
monthly close. It proves — with specific row-level database citations — that
every number in the Board Platform matches the warehouse. Finance reviews
and signs off on this report before the dashboard goes live.

### How it's generated

```python
# In smpl_close_roller.py, after writing the new HTML file:
def generate_tieout_report(org_id, close_month, html_path, db_conn):
    """
    Reads every data-source attribute from the generated HTML,
    queries the warehouse for each cited value, and produces
    a tie-out report showing match/mismatch for every displayed number.
    """
    from bs4 import BeautifulSoup
    import json
    from datetime import datetime

    soup = BeautifulSoup(open(html_path).read(), 'html.parser')

    results = []
    elements = soup.find_all(attrs={"data-source": True})

    for el in elements:
        source    = el['data-source']
        period    = el.get('data-period', close_month)
        displayed = el.get_text().strip()
        is_fc     = el.get('data-is-forecast') == 'true'

        if source.startswith('COMPUTED:'):
            # For computed values, verify the formula
            result = verify_computed(source, period, org_id, db_conn, displayed)
        elif is_fc:
            # For forecast values, verify against Forecast Engine output
            result = verify_forecast(source, period, org_id, db_conn, displayed)
        else:
            # For actual values, query the warehouse directly
            result = verify_warehouse(source, period, org_id, db_conn, displayed)

        results.append(result)

    # Generate the report
    passed  = [r for r in results if r['status'] == 'PASS']
    failed  = [r for r in results if r['status'] == 'FAIL']
    warnings= [r for r in results if r['status'] == 'WARN']

    report = {
        'org_id':       org_id,
        'close_month':  close_month,
        'generated_at': datetime.utcnow().isoformat(),
        'html_file':    html_path,
        'summary': {
            'total_checks': len(results),
            'passed':       len(passed),
            'failed':       len(failed),
            'warnings':     len(warnings),
            'pass_rate':    f"{len(passed)/len(results)*100:.1f}%"
        },
        'failures':  failed,
        'warnings':  warnings,
        'all_checks': results
    }

    # Block deployment if any FAIL
    if failed:
        raise ValueError(
            f"TIE-OUT FAILED: {len(failed)} values don't match warehouse.\n"
            f"Report: {report_path}\n"
            f"Failing checks:\n" +
            "\n".join(f"  {r['source']}: displayed={r['displayed']} "
                     f"warehouse={r['warehouse_value']} diff={r['diff']}"
                     for r in failed)
        )

    return report


def verify_warehouse(source, period, org_id, db_conn, displayed):
    """Query warehouse and compare to displayed value."""
    table, column = source.split('.')
    cursor = db_conn.cursor()
    cursor.execute(
        f"SELECT {column} FROM {table} "
        f"WHERE organization_id=%s AND period=%s",
        (org_id, period)
    )
    row = cursor.fetchone()
    if not row:
        return {
            'status':          'FAIL',
            'source':          source,
            'period':          period,
            'displayed':       displayed,
            'warehouse_value': None,
            'diff':            'NO ROW FOUND',
            'message':         f"No row in {table} for org={org_id} period={period}"
        }

    warehouse_raw  = row[0]
    displayed_num  = parse_display_value(displayed)  # "$86.1M" → 86100000
    warehouse_num  = float(warehouse_raw)
    diff           = abs(displayed_num - warehouse_num)
    # Display / UI soft check only (million-scale presentation). Do NOT use this
    # as closed-actuals statement tolerance — statement identities use TOL_ACTUALS=$1.00
    # (|Δ|≤$0.01 = rounding label; >$1 = significant_miss / FAIL).
    tolerance      = max(1000, abs(warehouse_num) * 0.001)  # display_precision soft band

    return {
        'status':          'PASS' if diff <= tolerance else 'FAIL',
        'source':          source,
        'period':          period,
        'displayed':       displayed,
        'warehouse_value': warehouse_raw,
        'displayed_parsed':displayed_num,
        'diff':            diff,
        'tolerance':       tolerance,
        'tolerance_kind':  'display_precision',  # not statement rounding
        'query':           f"SELECT {column} FROM {table} WHERE org='{org_id}' AND period='{period}'"
    }
```

### The rendered tie-out report

The report renders as a standalone HTML file at:
`output/tieout_report_{org_id}_{close_month}.html`

Structure:

```html
SMPL.ai — Data Tie-Out Report
Organization: Acme Corp | Close Month: June 2026
Generated: 2026-07-05 14:23 UTC | File: SMPL_Board_Platform_202606.html

══════════════════════════════════════════════════════
SUMMARY
══════════════════════════════════════════════════════
Total checks:    247
✓ Passed:        244  (98.8%)
⚠ Warnings:        3  (cash reconciliation gap < $1K)
✗ Failed:          0

STATUS: APPROVED FOR DEPLOYMENT

══════════════════════════════════════════════════════
DETAILED RESULTS — by tab
══════════════════════════════════════════════════════

EXECUTIVE SUMMARY
─────────────────────────────────────────────────────
✓ ARR EOP          $86.1M   ← arr_waterfall.ending_arr | period=2026-06 | warehouse=$86,100,000
✓ Revenue          $7.412M  ← income_statement.revenue | period=2026-06 | warehouse=$7,412,000
✓ Gross Margin     79.2%    ← COMPUTED: gross_profit/revenue | 5,874,000/7,412,000=79.24% ✓
✓ Cash Balance     $70.61M  ← bank_account_balances.ending_balance | date=2026-06-30 | $70,612,000
⚠ Cash Balance             ← RECONCILIATION: bank=$70,612,000 vs CFS=$70,612,122 | gap=$122 (< $1K threshold ✓)
✓ NRR              100.8%   ← arr_waterfall.net_dollar_retention_rate | period=2026-06 | 1.0080 ✓

ARR WATERFALL
─────────────────────────────────────────────────────
✓ Jan Beginning    $75.0M   ← arr_waterfall.beginning_arr | period=2026-01 ✓
✓ Jan New Business $1.2M    ← arr_waterfall.new_business_arr | period=2026-01 ✓
✓ Jan Ending       $76.31M  ← arr_waterfall.ending_arr | period=2026-01 ✓
✓ Feb Beginning    $76.31M  ← arr_waterfall.beginning_arr | period=2026-02 ✓
  [ARR CHAIN CHECK: Jan ending=$76,310,000 = Feb beginning=$76,310,000 ✓]
... [continues for all 12 months × 7 rows]

[... all tabs shown ...]

══════════════════════════════════════════════════════
CLAUDE COMMENTARY VERIFICATION
══════════════════════════════════════════════════════
Every number stated in AI-generated commentary is verified here.

Executive Summary commentary:
  "June ARR of $86.10M exceeded budget by $1.21M"
  ✓ $86.10M ← arr_waterfall.ending_arr period=2026-06 ✓
  ✓ $1.21M  ← COMPUTED: 86,100,000 - 84,890,000 (budget.arr_ending) = 1,210,000 ✓

  "gross margin expanding 220bps to 79.2%"
  ✓ 79.2%   ← COMPUTED: 5,874,000/7,412,000 = 79.24% ✓
  ✓ 220bps  ← COMPUTED: 79.24% - 77.0% (budget.gross_margin_pct) = 224bps (displayed as 220bps) ✓
  ⚠ rounding: actual=224bps displayed=220bps — rounded to nearest 10bps [ACCEPTABLE]

  "EBITDA of -$1.30M trailed budget by $1.08M"
  ✓ -$1.30M ← income_statement.ebitda period=2026-06 = -1,297,000 (displayed as -$1.30M) ✓
  ✓ $1.08M  ← COMPUTED: 647,498 - (-1,297,000) = 1,944,498 [MISMATCH: displayed $1.08M]
  ✗ FAIL: commentary says budget EBITDA trailed by $1.08M but computation gives $1.94M
    Likely cause: commentary used old budget value. Correct: -$1.30M vs $0.65M budget = -$1.95M gap

══════════════════════════════════════════════════════
FINANCE REVIEW SIGN-OFF
══════════════════════════════════════════════════════
Reviewed by: _________________ Date: _____________
Approved for deployment: [ ] YES  [ ] NO
Notes: ________________________________________________
```

---

## Part 5 — Commentary Verification Protocol

### How to verify Claude's generated commentary

When the close roller calls Claude API to generate `AI_CTX` and commentary divs,
it must also generate a **verification manifest** that maps every number in the
commentary to its source.

```python
def generate_and_verify_commentary(cp_data, close_month, org_id):
    """
    Calls Claude API twice:
    1. Generate the commentary
    2. Extract every number stated and verify against _sources
    """

    # Step 1: Generate commentary
    commentary_response = claude_api.call(
        system=SYSTEM_PROMPT_WITH_INTEGRITY_RULES,
        messages=[{
            "role": "user",
            "content": f"Generate the executive summary commentary for {close_month}. "
                      f"Context: {json.dumps(cp_data)}"
        }]
    )
    commentary_text = commentary_response.content[0].text

    # Step 2: Extract and verify every number
    verification_response = claude_api.call(
        system="""You are a financial data auditor. Extract every specific number
        from the commentary and verify it against the provided _sources object.
        Return JSON: {
          "numbers_found": [
            {
              "stated_value": "$86.10M",
              "stated_context": "June ARR of $86.10M",
              "source_key": "arr_eop",
              "source_value": 86100000,
              "displayed_parsed": 86100000,
              "match": true,
              "diff": 0
            }
          ],
          "unverifiable": ["any number with no matching _sources key"],
          "all_verified": true
        }""",
        messages=[{
            "role": "user",
            "content": f"Commentary to verify:\n{commentary_text}\n\n"
                      f"Sources to check against:\n{json.dumps(cp_data['_sources'])}"
        }]
    )

    verification = json.loads(verification_response.content[0].text)

    # Block if any number is unverifiable
    if verification['unverifiable']:
        raise ValueError(
            f"COMMENTARY INTEGRITY FAILURE: {len(verification['unverifiable'])} "
            f"numbers stated with no source:\n"
            + "\n".join(f"  '{n}'" for n in verification['unverifiable'])
        )

    # Block if any number doesn't match (beyond statement TOL_ACTUALS / display soft rules)
    bad = [n for n in verification['numbers_found']
           if not n['match'] and n['diff'] > 10000]
    if bad:
        raise ValueError(
            f"COMMENTARY MISMATCH: {len(bad)} numbers don't match warehouse:\n"
            + "\n".join(f"  stated={n['stated_value']} warehouse={n['source_value']}"
                       for n in bad)
        )

    return commentary_text, verification
```

### The Copilot runtime verification

Every Copilot response at runtime must be verified before display:

```javascript
async function cpSend(userMessage) {
  // Build context from CP_DATA (includes _sources)
  const context = buildCopilotContext();

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-api-key': API_KEY },
    body: JSON.stringify({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 1000,
      system: COPILOT_SYSTEM_PROMPT,  // includes integrity rules
      messages: [
        { role: 'user', content: context + '\n\nQuestion: ' + userMessage }
      ]
    })
  });

  const data  = await response.json();
  const text  = data.content[0].text;

  // Extract all dollar amounts and percentages from response
  const numbers = extractNumbers(text);

  // Verify each against CP_DATA._sources
  const unverified = [];
  numbers.forEach(n => {
    const match = findInSources(n.parsed_value, CP_DATA._sources);
    if (!match) unverified.push(n.stated);
  });

  // If any number is unverified, append a warning to the response
  if (unverified.length > 0) {
    return text + `\n\n⚠️ Note: The following figures could not be verified against
    the current data package: ${unverified.join(', ')}. Please confirm with Finance
    before using in external materials.`;
  }

  return text;
}

function extractNumbers(text) {
  // Match $X.XM, X.X%, $XK, $XB patterns
  const patterns = [
    /\$(\d+\.?\d*)(K|M|B)/g,
    /(\d+\.?\d*)%/g,
    /\$(\d{1,3}(?:,\d{3})*)/g
  ];
  const found = [];
  patterns.forEach(p => {
    let m;
    while ((m = p.exec(text)) !== null) {
      found.push({ stated: m[0], parsed_value: parseDisplayValue(m[0]) });
    }
  });
  return found;
}

function findInSources(value, sources) {
  // Commentary soft match vs evidence — NOT closed-actuals statement tolerance.
  // Statement identities / FE↔Board actuals: TOL_ACTUALS = $1.00 (fail-closed).
  const TOLERANCE = Math.max(1000, Math.abs(value) * 0.01);
  return Object.values(sources).some(s => {
    const sv = s.value || s.computed_value || s.value_used;
    return sv && Math.abs(sv - value) <= TOLERANCE;
  });
}
```

---

## Part 6 — The Close Review Checklist

Finance runs this checklist every month before approving deployment.
This is the human layer that catches anything the automated checks miss.

```
SMPL CLOSE REVIEW CHECKLIST
Organization: _______________ Close Month: ___________
Reviewer: ___________________ Date: ________________

SECTION 1 — DATA INTEGRITY
[ ] 1.  Tie-out report generated (tieout_report_{org}_{month}.html)
[ ] 2.  Tie-out report shows 0 FAIL items
[ ] 3.  Tie-out warnings reviewed and documented
[ ] 4.  Cash reconciliation gap < $1,000 (bank vs CFS) — bank_timing_soft; not “rounding.” Statement CFS identities still ≤ $1.00
[ ] 5.  ARR chain verified: every month's ending = next month's beginning (TOL_ACTUALS $1.00; |Δ|≤$0.01 may label rounding)
[ ] 6.  Cash chain verified: every month's ending = next month's beginning (TOL_ACTUALS $1.00 — multi-$k gaps = significant_miss)

SECTION 2 — KEY METRICS SPOT CHECK
Verify these 5 numbers directly in the warehouse before approving:

  a. ARR EOP (CLOSE_MONTH):
     Dashboard shows: _________ Warehouse query result: _________  [ ] MATCH

  b. Revenue (CLOSE_MONTH):
     Dashboard shows: _________ Warehouse query result: _________  [ ] MATCH

  c. Ending Cash (CLOSE_MONTH):
     Dashboard shows: _________ Bank statement:         _________  [ ] MATCH

  d. Net New ARR (CLOSE_MONTH):
     Dashboard shows: _________ Warehouse query result: _________  [ ] MATCH

  e. Total Headcount (CLOSE_MONTH):
     Dashboard shows: _________ HRIS system:            _________  [ ] MATCH

SECTION 3 — COMMENTARY REVIEW
[ ] 7.  Commentary verification manifest generated and shows all_verified=true
[ ] 8.  Executive summary numbers spot-checked against Section 2 above
[ ] 9.  No "will be", "is expected to be", or future-certain language in actuals tabs
[ ] 10. Forecast language uses "projects", "models", "based on current assumptions"

SECTION 4 — FORECAST REASONABLENESS
[ ] 11. July beginning cash = June ending cash (cash chain enforced)
[ ] 12. July beginning ARR = June ending ARR (ARR chain enforced)
[ ] 13. Dec ARR forecast reviewed and approved by Finance lead
[ ] 14. No single forecast month shows ARR decline > 10% vs prior (flag for review)
[ ] 15. Cash does not go below $10M (cash floor) in any forecast month

SECTION 5 — BUDGET COMPARISON SANITY
[ ] 16. Budget values unchanged from prior month (budget never changes mid-year)
[ ] 17. All "vs budget" variances directionally correct (positive for outperformance)
[ ] 18. Budget scenario shows "Bdgt" label not "Fcst" in 3-Statement

SECTION 6 — DEPLOYMENT APPROVAL
[ ] 19. All above items checked
[ ] 20. Tie-out report signed off
[ ] 21. File deployed to Vercel: SMPL_Board_Platform_{CLOSE_MONTH}.html

Approved for deployment: _______________________ (Finance lead signature)
```

---

## Part 7 — Warehouse Queries for Manual Spot Check

Finance can run these queries directly against the warehouse to verify
any number shown in the dashboard. These should be accessible from
the Finance team's DB client.

```sql
-- 1. Verify ARR for any period
SELECT period, beginning_arr, new_business_arr, expansion_arr,
       reactivation_arr, contraction_arr, churn_arr,
       net_new_arr, ending_arr,
       net_dollar_retention_rate, gross_retention_rate,
       is_final
FROM arr_waterfall
WHERE organization_id = '{org_id}'
  AND period = '{close_month}'
ORDER BY period;

-- 2. Verify IS for any period
SELECT period, revenue, gross_profit,
       ROUND(gross_profit::numeric/NULLIF(revenue,0)*100,2) AS gm_pct,
       sales_and_marketing, research_and_development,
       general_and_administrative,
       (sales_and_marketing+research_and_development+general_and_administrative) AS total_opex,
       ebitda,
       ROUND(ebitda::numeric/NULLIF(revenue,0)*100,2) AS ebitda_margin,
       net_income,
       is_final
FROM income_statement
WHERE organization_id = '{org_id}'
  AND period = '{close_month}';

-- 3. Verify cash — bank vs CFS reconciliation
SELECT
  bab.ending_balance AS bank_balance,
  cfs.ending_cash    AS cfs_ending_cash,
  cfs.ending_cash - bab.ending_balance AS reconciliation_gap,
  cfs.beginning_cash,
  cfs.net_cash_from_operating_activities AS cfo,
  cfs.capital_expenditures AS capex,
  cfs.net_change_in_cash,
  cfs.reconciliation_gap AS stored_gap
FROM cash_flow_statement cfs
LEFT JOIN bank_account_balances bab
  ON bab.organization_id = cfs.organization_id
  AND bab.balance_date = (DATE_TRUNC('month', cfs.period::date)
                          + INTERVAL '1 month - 1 day')::date
WHERE cfs.organization_id = '{org_id}'
  AND cfs.period = '{close_month}';

-- 4. Verify ARR chain (every month's ending = next month's beginning)
SELECT
  a.period,
  a.ending_arr AS this_ending,
  b.beginning_arr AS next_beginning,
  a.ending_arr - b.beginning_arr AS chain_gap
FROM arr_waterfall a
JOIN arr_waterfall b
  ON b.organization_id = a.organization_id
  AND b.period = TO_CHAR(
    (TO_DATE(a.period, 'YYYY-MM') + INTERVAL '1 month'),
    'YYYY-MM'
  )
WHERE a.organization_id = '{org_id}'
ORDER BY a.period;
-- Expected: chain_gap = 0 for all rows

-- 5. Verify headcount
SELECT period, department, headcount_beginning, new_hires,
       attrition, headcount_ending, monthly_cash_payroll
FROM headcount_plan
WHERE organization_id = '{org_id}'
  AND period = '{close_month}'
ORDER BY department;

-- 6. Verify cash chain
SELECT
  a.period,
  a.ending_cash AS this_ending,
  b.beginning_cash AS next_beginning,
  a.ending_cash - b.beginning_cash AS chain_gap
FROM cash_flow_statement a
JOIN cash_flow_statement b
  ON b.organization_id = a.organization_id
  AND b.period = TO_CHAR(
    (TO_DATE(a.period, 'YYYY-MM') + INTERVAL '1 month'),
    'YYYY-MM'
  )
WHERE a.organization_id = '{org_id}'
ORDER BY a.period;
-- Expected: chain_gap ≈ 0 for all rows (TOL_ACTUALS ≤ $1.00; |Δ|≤$0.01 = rounding label only)
-- Multi-hundred / multi-thousand gaps = significant_miss / data_mismatch — NOT rounding

-- 7. Verify commentary numbers (run after commentary generation)
-- Paste any number from AI commentary and verify it exists in warehouse
SELECT 'arr_waterfall' AS source, period, ending_arr AS value
FROM arr_waterfall WHERE organization_id='{org_id}' AND period='{close_month}'
  AND ABS(ending_arr - {stated_value}) < 10000
UNION ALL
SELECT 'income_statement', period, revenue
FROM income_statement WHERE organization_id='{org_id}' AND period='{close_month}'
  AND ABS(revenue - {stated_value}) < 10000
UNION ALL
SELECT 'cash_flow_statement', period, ending_cash
FROM cash_flow_statement WHERE organization_id='{org_id}' AND period='{close_month}'
  AND ABS(ending_cash - {stated_value}) < 10000;
-- Soft commentary probe only. Closed-actuals statement fail-closed remains $1.00.
-- If this returns 0 rows: the stated number has no warehouse source — investigate
```

---

## Part 8 — What Happens When a Check Fails

### Automated failure (close roller blocks deployment)
```
ERROR: TIE-OUT FAILED for 2026-07 close
  [FAIL] Executive Summary ARR: displayed=$86.1M warehouse=$85,525,473 diff=$574,527
  [FAIL] Commentary states "$1.21M above budget" but budget.arr_ending not found in _sources

Action required:
  1. Check arr_waterfall.ending_arr for period 2026-06
  2. Confirm is_final=true for period 2026-06
  3. Re-run close roller after confirming data
  4. Do NOT manually edit the displayed value — fix the source data
```

### Manual check failure (Finance spots a discrepancy)
```
Finance review process:
  1. Note the discrepancy: "Dashboard ARR $86.1M but my report shows $85.5M"
  2. Run query 1 from Part 7 to check warehouse value
  3. If warehouse = $85.5M: the dashboard has a bug — check array index alignment
  4. If warehouse = $86.1M: Finance source data may be from a different extract
  5. Never: manually change the displayed value without fixing the source
  6. Never: mark the tie-out as approved if a discrepancy is unresolved
```

### Claude states a number Finance can't verify
```
CFO: "You said churn was $115K but our Salesforce shows $185K"

Claude (correct response):
  "The $115K figure comes from arr_waterfall.churn_arr for period 2026-06
  in the SMPL warehouse. If Salesforce shows $185K, there may be a
  reconciliation gap between how churn is defined in each system.

  Common causes:
  - Salesforce may include contraction ($225K) in its churn figure
  - The warehouse may be using a different churn definition (renewal churn
    vs non-start churn)
  - The data may not have been synced since the close was finalized

  Finance should reconcile arr_waterfall.churn_arr + arr_waterfall.contraction_arr
  ($115K + $225K = $340K total ARR loss) against Salesforce's gross churn.
  If they still don't match, the ingestion mapping for churn may need review."
```

---

## Part 9 — Implementation Checklist for Cursor

```
DATA INTEGRITY INFRASTRUCTURE — BUILD ORDER:

Phase 1: Source tagging (prerequisite for everything else)
[ ] 1.  Add data-source, data-period, data-is-final attributes to all
        KPI elements in Board Platform HTML
[ ] 2.  Add data-source attributes to all chart canvas elements
        (data-source = dataset name, data-labels = axis source)
[ ] 3.  Add data-source to all table cell elements in WF_TABLE,
        BRIDGE_DATA render, and 3-Statement table

Phase 2: _sources object in CP_DATA
[ ] 4.  Add _sources object to CP_DATA in Board Platform HTML
[ ] 5.  Update close roller to generate _sources from warehouse queries
[ ] 6.  Each _sources entry: table, column, period, org_id, value, loaded_at

Phase 3: Audit overlay
[ ] 7.  Implement audit overlay toggle (Cmd+Shift+A)
[ ] 8.  Overlay shows data-source tags inline next to values
[ ] 9.  Overlay color-codes: WAREHOUSE=teal, COMPUTED=blue, FORECAST=amber, BUDGET=gray

Phase 4: Tie-out report generation
[ ] 10. Add generate_tieout_report() to smpl_close_roller.py
[ ] 11. Report queries warehouse for every data-source attribute
[ ] 12. Report blocks deployment on any FAIL
[ ] 13. Report renders as standalone HTML at output/tieout_report_{org}_{month}.html

Phase 5: Commentary verification
[ ] 14. Add verify_commentary() to close roller using second Claude API call
[ ] 15. Verification manifest stored alongside commentary output
[ ] 16. Block commentary deployment if unverifiable numbers found

Phase 6: Copilot runtime verification
[ ] 17. Add extractNumbers() to Copilot response handler
[ ] 18. Add findInSources() to check against CP_DATA._sources
[ ] 19. Append warning to any response containing unverified numbers
[ ] 20. Log all unverified numbers to server for Finance review

Phase 7: Integrity rules in system prompt
[ ] 21. Add full integrity system prompt to all Claude API calls
[ ] 22. Include _sources in every API context payload
[ ] 23. Include loaded_at timestamp in _sources to enable staleness detection

Phase 8: Finance review tooling
[ ] 24. Add SQL query library (Part 7 queries) to Finance documentation
[ ] 25. Make close review checklist (Part 6) available as downloadable PDF
[ ] 26. Store signed-off tie-out reports in archive alongside close files
```

---

## Summary: The Four Guarantees

When this framework is fully implemented, SMPL provides four guarantees:

**Guarantee 1 — Traceability**
Every number displayed in the dashboard has a `data-source` attribute that
cites the exact warehouse table, column, period, and load timestamp.
Any number without a source tag is a build error, not a feature.

**Guarantee 2 — Verification**
The tie-out report proves — with live warehouse queries — that every displayed
value matches the source within defined tolerances. This report is generated
automatically and reviewed by Finance before every deployment.

**Guarantee 3 — Claude source discipline**
Claude's system prompt prohibits stating any number not found in `_sources`.
Every Claude response that contains numbers is verified by a second Claude API
call that extracts and cross-checks every figure. Unverifiable numbers trigger
a warning to the user.

**Guarantee 4 — Machine-primary release, human exception handling**
Release safety is machine-primary: automated fail-closed gates (provenance,
_sources, structural claim verify, freeze-ID binding, tie-out / second-pass
verification) are the day-to-day control, not a human re-checking every package
before it ships. The Finance review checklist and spot-check queries remain
required, but as periodic control testing and exception review — not as the
primary gate on every release. See README.md, "Adaptation of source Part 6,"
for the full rationale. Do not reintroduce "human review before every send" as
the primary control in this document, policy, sales language, or IR framing.

---

*SMPL.ai — We make finance simple.*
*Data Integrity Framework — zero-tolerance policy for phantom outputs*
*This document governs both build-time (Cursor) and runtime (Claude API) behavior*
