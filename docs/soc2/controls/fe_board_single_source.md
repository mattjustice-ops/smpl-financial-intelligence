# Production FE ↔ Board single-source (confirmed in code)

> **Not SOC 2 certification.** Control note for production/customer hydrate path.  
> Demo dual-seed inventory remains in [reconcile_financial_statements.md](./reconcile_financial_statements.md) — **do not reseed demos to fake equality.**

---

## Verdict (2026-07-30)

**On the production/customer path, Board Platform and Forecast Engine UI both hydrate from the same warehouse outlook API.**

```
warehouse tables
  (actual_income_statement, actual_balance_sheet, actual_mrr_waterfall)
        │
        ▼
build_unified_outlook_payload  →  TS_DATA + SRC + ARR_WATERFALL + …
        │
        ▼
GET /api/v1/reporting/outlook
        │
        ▼
SMPLOutlook.hydrate  →  Board (TS_DATA) + FE (SRC.actuals + TS_DATA merge)
```

| Question | Answer |
|----------|--------|
| Same API both call? | **Yes** — `/api/v1/reporting/outlook` |
| Same builder? | **Yes** — `build_unified_outlook_payload` in `three_statement_payload.py` |
| Same warehouse tables for statement actuals? | **Yes** — IS + BS (+ MRR for SRC/waterfall); CFS derived from IS+BS |
| Freeze pack = UI statement hydrate? | **No** — freeze is Copilot / MD&A / export context |
| Offline demo single-source? | **No** — dual seeds; known `data_mismatch` (leave alone) |

---

## Automated guard

| Piece | Location |
|-------|----------|
| Diff helper | `diff_outlook_ts_src_actuals` / `assert_outlook_ts_src_actuals_aligned` |
| Tolerance | **$1.00** (`OUTLOOK_TS_SRC_MONEY_TOLERANCE`) — same product bar |
| Regression test | `backend/tests/test_outlook_ts_src_actuals_alignment.py` |

The guard compares Board `TS_DATA.Actual` vs FE `SRC.actuals` for shared fields (revenue, opex, cash, deferred_rev, ending_cash, …). It fails if either side is missing when the other has a value, or if `|Δ| > $1`.

**Out of scope:** FE embedded `SRC` vs Board embedded `TS_DATA` demo constants. Those stay documented mismatches.

---

## Remaining risks (honest)

1. Frontend **merge-not-replace** can leave demo residue when a warehouse period is empty.
2. FE display may prefer TS while levers/`computePeriod` read `SRC.actuals` — both should match after a full live hydrate; partial hydrate can diverge.
3. Field alias bugs (`deferred_rev` / `dr`) can look like source divergence — the guard checks both.

---

_End of FE↔Board single-source note_
