# Chart styling

## Allowed primitives

| Primitive | Type | Max categories | Max series |
|-----------|------|----------------|------------|
| `executive_kpi_trend` | line | 8 | 2 |
| `arr_waterfall` | column | 7 | 1 |
| `funnel_conversion` | column | 6 | 1 |
| `pipeline_movement_bridge` | column | 7 | 1 |
| `revenue_bridge` | column | 7 | 2 |
| `cash_bridge` | line | 8 | 2 |
| `headcount_bridge` | column | 7 | 1 |
| `department_spend` | column | 7 | 1 |

## Composition rules

- **Axis restraint** — Y-axis label only when unit is non-obvious (% ARR, FTE)
- **Legend** — off for single-series waterfalls; on for dual actual/forecast lines
- **Labels** — category labels horizontal; max 7 periods on executive band
- **No inference** — slide_id selects primitive; title keywords are fallback only for legacy paths

## Sizing

Charts render inside `visual_zone_chart()` box only — never auto-expand into footer.
