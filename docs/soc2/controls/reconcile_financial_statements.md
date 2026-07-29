# Reconcile Financial Statement Data — Forecast Engine vs Board Platform

> **Normative investigation / control prompt** under `docs/soc2/controls/`.  
> **Not SOC 2 certification.** Shipping status: demo seed divergence is a known `data_mismatch` until both platforms read one warehouse actuals table.  
> Related: [data_sources_tieout_prompt.md](./data_sources_tieout_prompt.md), [data_integrity_framework.md](./data_integrity_framework.md), [README.md](./README.md).  
> Customer / production CF+RE construction (not this demo inventory): [financial_dashboard_cf_re_logic.md](./financial_dashboard_cf_re_logic.md).

## Severity bands for closed actuals (Matt bar)

Use these labels for **closed-month actuals** statement tie-outs (FE ↔ Board, warehouse ↔ statement, identity checks). Do **not** call multi-hundred or multi-thousand gaps “rounding.”

| |Δ| (absolute) | Label | Meaning |
|---|---|---|
| `Δ = 0` | `exact` | Exact match |
| `\|Δ\| ≤ $0.01` | `rounding` | Cent-level rounding only |
| `$0.01 < \|Δ\| ≤ $1.00` | `investigate` | Weird — investigate; product hard-fail is **> $1.00** (`TOLERANCE = 1.00`) |
| `\|Δ\| > $1.00` | `significant_miss` / `data_mismatch` | Reconciliation gap — **not** rounding. Multi-thousand = significant miss |

**Product alignment:** Backend financial statement validation fails closed when `|variance| > $1.00`. Do not loosen that gate.

**Do not confuse with soft checks:** Bank vs CFS timing gaps and million-scale **display** precision are separate soft checks — they are **not** a license to label statement actuals misses as rounding. See [data_sources_tieout_prompt.md](./data_sources_tieout_prompt.md) Part 3 preface.

---

## Summary

**Note: this document was corrected after initial analysis misdiagnosed the Deferred Revenue discrepancy. The Forecast Engine's $1.12M figure is correct; the Board Platform's $50.9M figure is the bug. See the Deferred Revenue root cause section below for the evidence.**

**Severity labeling corrected 2026-07-29:** earlier drafts marked Revenue / COGS / GP / CFO / Ending Cash as “✅ rounding only” despite deltas of hundreds to thousands of dollars. Those are `significant_miss` / `data_mismatch`. Only CapEx is an exact match in the June 2026 cross-platform diff below.

The two platforms are running on **two entirely separate, independently-generated June 2026 actuals datasets** — not the same data viewed through different lever/formula logic. A few line items are close in relative terms but still fail Matt’s actuals bar (e.g. Revenue Δ $225, EBITDA Δ $61). Others are off by enormous, structurally-impossible margins (Deferred Revenue off by $49.8M, R&D expense off by $1.5M, Beginning Cash off by $18M). This second category cannot be explained by forecast assumptions or lever settings — it means the two files were seeded with different source data for the same historical, already-closed month.

**This is worse than the ARR forecast issue from before** — that was one disconnected number. This is the full P&L, cash flow, and balance sheet running on two different ledgers for a month that already happened and should have exactly one correct, immutable value per line item.

**Do not invent fake equality** between FE and Board demo seeds to paper over divergence. Leave honest `data_mismatch` labels and deltas until a single authoritative actuals source is chosen (or Phase B warehouse shared read lands).

---

## Exact deltas — June 2026 actuals, Forecast Engine vs Board Platform

Computed directly from each file's own embedded data (`SRC.actuals['2026-06']` in the Forecast Engine vs `TS_DATA.Actual.is/cfs/bs['2026-06']` in the Board Platform). Not estimated — pulled and diffed programmatically.

### Income Statement

| Line item | Forecast Engine | Board Platform | Delta | Severity |
|---|---:|---:|---:|---|
| Revenue | $7,412,000 | $7,411,775 | $225 | `significant_miss` / `data_mismatch` |
| COGS | $1,537,000 | $1,541,649 | -$4,649 | `significant_miss` / `data_mismatch` |
| Gross Profit | $5,875,000 | $5,870,126 | $4,874 | `significant_miss` / `data_mismatch` |
| **S&M** | **$3,680,000** | **$3,150,004** | **$529,996** | `significant_miss` / `data_mismatch` |
| **R&D** | **$1,220,000** | **$2,757,180** | **-$1,537,180** | `significant_miss` / `data_mismatch` |
| **G&A** | **$810,000** | **$1,260,002** | **-$450,002** | `significant_miss` / `data_mismatch` |
| **Total OpEx** | **$5,710,000** | **$7,167,186** | **-$1,457,186** | `significant_miss` / `data_mismatch` |
| EBITDA | -$1,297,000 | -$1,297,061 | $61 | `significant_miss` / `data_mismatch` |
| D&A | $122,000 | $92,000 | $30,000 | `significant_miss` / `data_mismatch` |
| Net Income | -$1,454,000 | -$1,424,061 | -$29,939 | `significant_miss` / `data_mismatch` |

**Notable:** EBITDA is only $61 apart even though the OpEx line items underneath it are wildly different — Forecast Engine's S&M/R&D/G&A split is different from Board Platform's, but they happen to sum to nearly the same Total OpEx-equivalent. That does **not** make EBITDA “rounding” — $61 still fails the $1.00 actuals gate and remains `significant_miss`. Whoever seeded each dataset hit a similar EBITDA target via two completely different departmental allocations. That's not a coincidence worth relying on going forward.

### Cash Flow Statement

| Line item | Forecast Engine | Board Platform | Delta | Severity |
|---|---:|---:|---:|---|
| **Beginning Cash** | **$48,022,800** | **$66,037,122** | **-$18,014,322** | `significant_miss` / `data_mismatch` |
| CFO | $4,800,000 | $4,795,000 | $5,000 | `significant_miss` / `data_mismatch` |
| CapEx / CFI | -$220,000 | -$220,000 | $0 | `exact` |
| Net Change | $4,580,000 | $4,575,000 | $5,000 | `significant_miss` / `data_mismatch` |
| Ending Cash | $70,610,000 | $70,612,122 | -$2,122 | `significant_miss` / `data_mismatch` |
| Chg AR | -$200,000 | -$170,000 | -$30,000 | `significant_miss` / `data_mismatch` |
| **Chg DR** | **$0** | **$6,172,061** | **-$6,172,061** | `significant_miss` / `data_mismatch` |
| Chg AP | -$40,000 | $60,000 | -$100,000 | `significant_miss` / `data_mismatch` |

**This is the most informative discrepancy in the entire comparison.** Forecast Engine's Beginning Cash is $18M *lower* than Board Platform's, but Ending Cash is only ~$2k apart (still a `significant_miss`, not rounding). That means CFO/CFI alone cannot reconcile beginning to ending in the Forecast Engine the way they do in the Board Platform — the Forecast Engine's June cash roll-forward is structurally inconsistent with its own beginning balance (this was flagged and partially addressed in an earlier fix — see the "Cash Roll-Forward" section below, this is the same root issue surfacing again from a different angle).

### Balance Sheet

| Line item | Forecast Engine | Board Platform | Delta | Severity |
|---|---:|---:|---:|---|
| Cash | $70,610,000 | $70,612,122 | -$2,122 | `significant_miss` / `data_mismatch` |
| **AR** | **$1,040,000** | **$8,699,083** | **-$7,659,083** | `significant_miss` / `data_mismatch` |
| **AP** | **$520,000** | **$5,557,519** | **-$5,037,519** | `significant_miss` / `data_mismatch` |
| **Deferred Revenue** | **$1,120,000 ✅ correct** | **$50,917,501 ❌ bug** | **-$49,797,501** | `significant_miss` / `data_mismatch` — BP bug, not FE |
| Equity | $49,228,800 | $31,302,850 | $17,925,950 | `significant_miss` / `data_mismatch` |

### Remaining known demo mismatches (honest — do not reseed unless asked)

Until an authoritative source is chosen (options below), treat FE ↔ Board June 2026 gaps as **known `data_mismatch`**, not rounding:

| Area | Approx \|Δ\| | Notes |
|------|-------------:|-------|
| OpEx department split (S&M / R&D / G&A) | $0.5M–$1.5M | Different allocations; similar EBITDA coincidence |
| Beginning Cash | ~$18M | FE lower; ending cash still ~$2k apart |
| AR / AP / Equity | $5M–$18M | Independent demo seeds |
| Deferred Revenue / Chg DR | ~$50M / ~$6M | BP actuals scale bug + CFS not tying to BS |
| Revenue / COGS / GP / CFO / Ending Cash | $61–$5k | Fail `$1` actuals bar — label `significant_miss` |

---

## Root cause — confirmed, not speculative

**Correction to an earlier read of this issue: the Forecast Engine's $1,120,000 Deferred Revenue figure is correct. The Board Platform's $50,917,501 figure is the bug.** Initial analysis assumed the Forecast Engine was misreferencing a field; checking the actual growth trajectory in both files proves the opposite.

**Evidence — Forecast Engine's `dr` field is a believable, smoothly-growing balance:**
```
2026-01: $944,000
2026-02: $976,000
2026-03: $1,024,000
2026-04: $1,072,000
2026-05: $1,120,000
2026-06: $1,120,000
```
This is what a real deferred revenue balance looks like for a company this size — steady, gradual growth.

**Evidence — Board Platform's `deferred_rev` field jumps 40x then collapses, within its own data:**
```
2026-01: $25,047,137
2026-02: $27,625,966
2026-03: $40,274,328
2026-04: $43,423,192
2026-05: $46,979,276   ← this happens to match the Forecast Engine's dr_waterfall.beg_dr,
                          which is what caused the earlier mis-diagnosis
2026-06: $50,917,501
---
2026-07: $1,230,528    ← FORECAST month, same file, same field — drops 40x in one month
2026-08: $1,261,536
2026-09: $1,289,280
```

**No real company's deferred revenue balance drops 40x between June actual and July forecast.** This is a scale error contained entirely within the Board Platform's `TS_DATA.Actual.bs` dataset — the actuals months were generated with deferred revenue roughly 40x too large, and the forecast months (generated separately) use the correct, much smaller scale. The two halves of the Board Platform's own data don't agree with each other.

**Further confirmation — the Board Platform's own CFS doesn't reconcile with its own BS:**

| Period | BS deferred_rev period-over-period change | CFS chg_dr (same file) | Match? |
|---|---:|---:|---|
| Feb | $2,578,829 | $2,663,786 | ❌ `data_mismatch` |
| Mar | $12,648,362 | $16,032,317 | ❌ `data_mismatch` |
| Apr | $3,148,864 | -$3,132,663 | ❌ `data_mismatch` (opposite sign) |
| May | $3,556,083 | $4,453,199 | ❌ `data_mismatch` |
| Jun | $3,938,225 | $6,172,061 | ❌ `data_mismatch` |

None of these tie, including one month (April) where the BS shows deferred revenue *increasing* while the CFS shows a *decrease* of similar magnitude — a sign-flip error, not just a scale error. This confirms the issue is isolated to the Board Platform's `TS_DATA.Actual` dataset (specifically the `bs.deferred_rev` and `cfs.chg_dr` fields for Jan–Jun) and is not present in the Forecast Engine.

**The earlier instinct to "fix" the Forecast Engine's BS to pull from `dr_waterfall.end_dr` was wrong and should not be implemented — that would have replaced a correct $1.12M figure with an unrelated, much larger waterfall number that doesn't represent the same thing.** The `dr_waterfall` object models something else (likely an illustrative/placeholder large-account billing schedule) and was a coincidental near-match to the Board Platform's May figure, not a meaningful connection.

**Action: regenerate `TS_DATA.Actual.bs[period].deferred_rev` and `TS_DATA.Actual.cfs[period].chg_dr` for all six actual months (Jan–Jun) in the Board Platform file, scaled consistently with the Forecast Engine's pattern (~$900K–$1.2M range) and internally reconciled so each month's BS change in deferred revenue equals that month's CFS chg_dr exactly.** Do not touch the Forecast Engine's `actuals[period].dr` field — it's already correct. (Reseed only when Matt asks — this prompt documents truth; it does not auto-paper over seeds.)

---

## Root cause — Beginning Cash / AR / AP / OpEx split

These do **not** have a traceable "right field, wrong place" explanation the way Deferred Revenue does — both files contain plausible-looking but mutually exclusive numbers for the same actual, closed month. This indicates the two datasets were generated independently (e.g., by two separate prompts/sessions building synthetic demo data) rather than derived from one shared source of truth.

There is no way to determine from the data alone which file's numbers are "correct" — they're both internally consistent fabricated demo data, just not consistent *with each other*. This needs a decision, not a debugging fix:

### Decide which dataset is authoritative
- **Option A:** Board Platform's `TS_DATA.Actual` becomes the single source of truth for all six closed actual months (Jan–Jun). Forecast Engine's `SRC.actuals` gets regenerated/replaced to match it exactly, line for line.
- **Option B:** Forecast Engine's `SRC.actuals` becomes the source of truth instead, and Board Platform's `TS_DATA.Actual` gets replaced.
- **Option C (recommended for the real build):** Neither hardcoded dataset survives — both platforms eventually read actuals from the same backend/warehouse table once Phase B ships, making this entire class of bug structurally impossible going forward. The reconciliation work below is a stopgap to get the demo consistent until that's true.

**Do not average, blend, or "split the difference" between the two datasets.** A historical month's actuals have one correct value per line item. Picking a source and propagating it exactly is the only valid approach.

---

## What needs to happen, in order

1. **Pick the authoritative actuals source for the remaining unresolved fields** (Beginning Cash, AR, AP, OpEx department split — see decision options above). Deferred Revenue is no longer part of this decision — it's resolved: Forecast Engine is correct, Board Platform needs to be fixed to match.
2. **Regenerate `TS_DATA.Actual.bs[period].deferred_rev` for Jan–Jun** in the Board Platform to be consistent with the Forecast Engine's $900K–$1.2M range, growing smoothly month over month the same way the Forecast Engine's `actuals[period].dr` does.
3. **Regenerate `TS_DATA.Actual.cfs[period].chg_dr` for Jan–Jun** so that each month's value equals that month's deferred_rev change on the BS exactly — confirmed broken even within the Board Platform's own file (see self-reconciliation table above), independent of any cross-file comparison.
4. **Regenerate whichever of Beginning Cash / AR / AP / OpEx split is deemed non-authoritative** for all six closed months (Jan–Jun), not just June — if June is wrong, the whole H1 dataset is suspect.
5. **Re-run the cash roll-forward validation** from the existing "formulaic CFS" work (Beginning + Net Change = Ending, chained month to month) against the corrected dataset.
6. **Re-run the ARR forecast reconciliation** from the separate Cursor prompt already provided — that issue is independent of this one but touches the same files and should be fixed in the same pass.

---

## Open question to resolve before closing this out

The Forecast Engine's `SRC.dr_waterfall` object (beg_dr/billings/recognized/end_dr, values in the $14M–$47M range across forecast months) does not correspond to the corrected, properly-scaled Deferred Revenue figures (~$900K–$1.4M range) used everywhere else in both files. Confirm what `dr_waterfall` is actually meant to model — if it's unused placeholder/illustrative data, consider removing it to avoid future confusion (it was the direct cause of the earlier mis-diagnosis in this exact investigation). If it models something real (e.g., a specific large-account or annual-billing cohort tracked separately from the aggregate BS deferred revenue balance), it should be clearly labeled as such and kept out of any general BS/CFS field-mapping logic.

---

## Validation checklist

- [ ] Single authoritative actuals dataset chosen and documented for the remaining unresolved fields (Beginning Cash, AR, AP, OpEx department split)
- [ ] Board Platform's `TS_DATA.Actual.bs[period].deferred_rev` regenerated for Jan–Jun to match Forecast Engine's scale (~$900K–$1.2M)
- [ ] Board Platform's `TS_DATA.Actual.cfs[period].chg_dr` regenerated so it equals each month's BS deferred_rev change exactly — verify within the Board Platform's own file, not just against the Forecast Engine
- [ ] All six closed months (Jan–Jun 2026) match within severity bands between both platforms — Revenue, COGS, GP, S&M, R&D, G&A, EBITDA, D&A, Net Income, Beginning/Ending Cash, AR, AP, Deferred Revenue, Equity (`\|Δ\| ≤ $0.01` rounding; `\|Δ\| > $1` = fail / `significant_miss`)
- [ ] Cash roll-forward (Beginning + Net Change = Ending) ties for every actual month in both platforms (`TOLERANCE = $1.00`)
- [ ] Total Assets = Total Liabilities + Equity for every actual month, post-fix
- [ ] Re-verify the ARR forecast reconciliation (separate prompt) wasn't broken by this data change
- [ ] Confirm whether `SRC.dr_waterfall` in the Forecast Engine is needed/used anywhere else before deciding whether to remove it (see open question above)
- [ ] Severity language in docs/UI never calls multi-thousand actuals gaps “rounding”

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-29 | Ingested from Matt Downloads; severity relabeled to Matt bar ($0.01 rounding / ≤$1 investigate / >$1 significant_miss); remaining demo gaps documented honestly without reseeding |

---

_End of reconcile financial statements prompt_
