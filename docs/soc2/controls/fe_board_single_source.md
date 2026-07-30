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

## Automated guards

| Piece | Location |
|-------|----------|
| Diff helper | `diff_outlook_ts_src_actuals` / `assert_outlook_ts_src_actuals_aligned` |
| Tolerance | **$1.00** (`OUTLOOK_TS_SRC_MONEY_TOLERANCE`) — same product bar |
| Regression test | `backend/tests/test_outlook_ts_src_actuals_alignment.py` |
| Hydrate residue regression | `frontend/scripts/verify-outlook-hydrate.mjs` (`npm run verify:outlook-hydrate`) |

The guard compares Board `TS_DATA.Actual` vs FE `SRC.actuals` for shared fields (revenue, opex, cash, deferred_rev, ending_cash, …). It fails if either side is missing when the other has a value, or if `|Δ| > $1`.

**Out of scope:** FE embedded `SRC` vs Board embedded `TS_DATA` demo constants. Those stay documented mismatches.

---

## Hydrate merge behavior (fixed this increment)

`SMPLOutlook.applyOutlook` / `mergeTsData` / `mergeActuals`:

1. **Full period-row replace** for every live period that has values — never `Object.assign` demo fields onto a live row.
2. **Prune closed Actual residue** — when live Actual has ≥1 populated period, delete target Actual (TS) / SRC.actuals periods `≤ close_month` that the warehouse did not send.
3. **Empty live Actual does not wipe demo** — incomplete/offline warehouse still keeps embedded demo (status stays warn).
4. **No demo reseed** to fake ties.

Code: `frontend/canonical/shared/smpl-outlook.js` and `frontend/public/shared/smpl-outlook.js`.

---

## Remaining risks (honest)

1. Forecast / Budget scenarios are not pruned the same way as closed Actuals (by design — forward demo scaffolding may remain until live forecast arrives).
2. FE display may prefer TS while levers/`computePeriod` read `SRC.actuals` — both should match after a full live hydrate; partial hydrate now replaces/prunes closed Actuals on both.
3. Field alias bugs (`deferred_rev` / `dr`) can look like source divergence — the backend guard checks both.

---

## UI provenance overlay (2026-07-30)

Board + Forecast Engine material KPIs attach `data-source` / `data-period` / `title` / `aria-label` after hydrate (and on tab render).

| Piece | Location |
|-------|----------|
| Shared module | `frontend/public/shared/smpl-provenance.js` (+ canonical) |
| Prefer hydrate `_sources` | `SMPLProvenance.ingestOutlook` reads `payload._sources` / `meta._sources` / `evidence_package._sources` when present; else field catalog |
| Audit overlay | `Ctrl+Shift+A` / `Cmd+Shift+A` toggles inline source tags |
| Client tie-out | `runTieOut()` — **partial** Rule C (TS↔SRC Actuals) + ARR A2/A3 when SRC has `arr_*`; **not** full Rule Sets A–F |
| Publish gate | Live hydrate + FAIL → block MD&A export (`board-hydrate.js`) and FINAL forecast promote; demo/offline warns only |
| Regression | `npm run verify:provenance` |

**Limitation:** Full warehouse-vs-DOM `runTieOut()` A–F and HTML tie-out report remain roadmap. Demo dual seeds stay mismatched on purpose — do not reseed.

---

_End of FE↔Board single-source note_
