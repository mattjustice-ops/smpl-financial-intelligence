# Narrative pacing

## Story order (fixed)

GTM → Funnel → Pipeline → ARR → Revenue → Cash → Financials → Decisions

Defined in `board_semantic_mappings.NARRATIVE_SLIDE_ORDER` and `presentation/orchestration/story.py`.

## Section transitions

Inserted before `gtm_performance`, `arr_waterfall`, etc. when narrative threshold met (≥ 8 chars).

Template: `section_transition` — title, chain subtitle, one anchor KPI, short narrative.

## Density variation

| Phase | Density |
|-------|---------|
| Executive open | High signal — scorecard + 4 KPIs |
| GTM block | Medium — charts + channel tables |
| Finance block | Medium — bridges |
| Decisions | Low — callouts only |
| Appendix | High table density allowed |

## Cadence

- **No back-to-back dual tables** on executive band
- **Divider** before major section pivots (GTM → ARR)
- **Commentary column** on channel slides only (template-driven)
