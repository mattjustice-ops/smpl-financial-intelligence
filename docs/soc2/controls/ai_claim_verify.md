# P15 AI claim-verify — coverage checklist (founder review)

> **Not SOC 2 certification.** Product integrity gate for AI-stated numbers vs engine evidence.  
> **Branch note:** This branch (`feat/p15-citation-drivers-sources-meta`): **post-LLM citation check**, richer warehouse tags (`loaded_at` / `org_id` / `is_final`), multi-driver AND rule (see attribution doc).  
> **Policy:** [P15 §4.7 / §4.8](../policies/P15_ai_llm_data_handling.md) · **Status snapshot:** [README.md](./README.md)  
> **Non-numeric drivers:** [ai_attribution_verify.md](./ai_attribution_verify.md)

---

## 1. What shipped (this increment)

| Path | Behavior | Code |
|------|----------|------|
| `/api/v1/commentary/generate` | Numeric verify → attribution verify → **citation verify** → soft strip / don't-know | `service.py`, `citation_verify.py`, `claim_verify.py` |
| MD&A Prompt 2 | Nested string numeric + attribution + **citation** walk; hard block if variance fully wiped | `prompt2_mda_package.py` |
| Board Copilot | Numeric + attribution + **citation** on answer; live packages carry org/loaded_at tags | `board_platform_routes.py` |
| **`_sources` warehouse tags** | Every source tag includes `org_id` / `loaded_at` / `is_final` (honest nulls when unknown) | `claim_verify.build_source_record` |
| **Post-LLM citation check** | Material money/%/Nx must cite `_sources` key, `table.column`, `formula_id`, or path | `citation_verify.py` |

Reusable helpers: `claim_verify.py`, `citation_verify.py`, `attribution_verify.py`

---

## 2. Algorithm (short)

1. Build evidence values + `_sources` (with warehouse tags).
2. Prompt embeds the same package.
3. Extract numeric claims; match within **$1.00** / ratio tolerances.
4. Attribution allowlist check (multi-driver AND → all required).
5. Citation check: each material money/%/Nx cites a `_sources` token (inline or `citations[].label`).
6. Fail closed → don't-know / omit (Prompt 2 may hard-block).

### Agreed citation formats

| Form | Example |
|------|---------|
| Evidence key | `$110,000 (mrr_waterfall.ending_mrr)` |
| Key + period | `$86.1M (arr_waterfall.ending_arr, period 2026-06)` |
| table.column | `$7.4M (income_statement.revenue)` |
| Structured list | `citations[].label = "mrr_waterfall.ending_mrr"` |

### Tolerances (do not loosen)

| Kind | Constant | Value |
|------|----------|-------|
| Money / actuals | `TOL_ACTUALS` | **$1.00** |
| Ratios | `TOL_RATIO` | `0.0005` |
| Percent points | `TOL_PERCENT_POINTS` | `0.05` |

---

## 3. Coverage map

| Surface | Status | Notes |
|---------|--------|-------|
| Commentary generate | **Live** | Numeric → attribution → citation |
| MD&A Prompt 2 | **Live** | Citation + hard block when variance fully wiped |
| Copilot | **Live** | Citation on answer text |
| Prompt 5 / board bullets | Prior numeric/attribution only | Citation gate not on PPTX literals this slice |
| Warehouse tags | **Live (honest nulls)** | Freeze: org + loaded_at + is_final=true; live Copilot: org + loaded_at + is_final=false |
| DOM `data-source` overlay | **Other agent** | Do not touch FE/board HTML in this slice |

---

## 4. Tests

| File | Covers |
|------|--------|
| `tests/test_claim_verify.py` | Numeric verify + `_sources` builders |
| `tests/test_citation_verify.py` | Inline/structured citation; warehouse tags |
| `tests/test_attribution_verify.py` | Multi-driver AND/comma require-all |
| `tests/test_commentary_service.py` | Happy path with `_sources` cites |

---

## 5. Matt review checklist

- [ ] Confirm citation formats are the right bar
- [ ] Confirm warehouse tags with honest nulls are acceptable
- [ ] Confirm **$1.00** bar unchanged
- [ ] Merge when review OK — not SOC 2 certified

---

_End of AI claim-verify coverage checklist_
