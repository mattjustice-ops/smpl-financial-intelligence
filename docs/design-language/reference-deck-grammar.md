# Reference deck grammar (extracted)

Source index: `docs/reference-decks/INDEX.md`

## What we systematize

| Pattern | Grammar element | Template |
|---------|-----------------|----------|
| Green section band | Section context | `section_transition` |
| KPI row + TY/Plan/LY table | Executive scan | `executive_scorecard` |
| Commentary left, table right | Bookings narrative | `story_slide` + footer |
| 65/35 table + orange column | Channel by source | `marketing_source` |
| ARR rollforward columns | Waterfall + retention rows | `story_slide` + `arr_waterfall` primitive |
| Cash line + covenant subtext | Liquidity story | `cash_trend` |
| Strategy bullets | Board decisions | `risk_matrix` |
| Dense Excel grids | **Not** board slides | `compact_table` appendix |

## What we do NOT copy

- Literal slide duplication
- Verbatim commentary from customer decks
- Manual red highlight boxes (use KPI `tone` instead)
- Photo/glare Excel screenshots as layouts

## Inference goal

Encode **HOW** executive SaaS presentations communicate:

- hierarchy before decoration
- one decision per slide
- variance columns (vs budget, Y/Y) in tables not in chart junk
- appendix for drilldown, not the board band
