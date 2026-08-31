"""Prompt 5 gold-reference script adaptation — same layout, new month data.

Authoring principle: adapt preserves layout geometry from the reference script;
Claude still *authors* narrative (Key Takeaways, R&O, board actions) for the new
period using craft criteria + evidence packages — not by filling blank slots from
a KT seed, and not via post-process seed-refill after soft-strip.
"""

from app.services.reporting.export.prompt5_narrative import (
    PROMPT5_BOARD_NARRATIVE_RULES,
    PROMPT5_CRAFT_CRITERIA,
)

PROMPT5_ADAPT_SYSTEM = """You adapt an existing PptxGenJS board deck script for a new close period.

This is script adaptation (Option 1): the reference script defines layout and styling.
Your job is to substitute fresh data from the JSON payload and AUTHOR period-specific
narrative — not to redesign the deck in Python, and not to slot-fill a rigid template.

RULES:
1. Preserve the reference script's structure: helpers, slide order, positions, chart types,
   table shapes, typography, and colors — except where LAYOUT LOCKS explicitly move KT /
   waterfall / funnel labels.
2. Replace data values only for layout/numbers — numbers, period labels, table cells,
   chart series data. Copy money strings from EVIDENCE PACKAGE / DATA PAYLOAD verbatim
   (TOL_ACTUALS=$1.00). Soft-fail / missing → "—" in KPI/table cells (never don't-know essays).
   P&L CM/YTD variance columns and CFS Actual/Budget/Variance must come from pl_detail /
   appendix.ytd_cash_flow_statement (Actual ≤ close_month — never Forecast).
3. REWRITE all narrative text for the new period — do NOT keep thin reference one-liners.
   Author every Key Takeaways bullet, risk/opportunity detail+action line, board-action
   copy, and slide commentary string using BOARD NARRATIVE DEPTH + CRAFT CRITERIA and the
   CLOSE FREEZE / EVIDENCE / ATTRIBUTION / BOARD R&O EVIDENCE / GTM NARRATIVE packages.
   Every KT panel you include must have 3–5 complete authored bullets (never blank or
   lone "—"). Evidence packages inform authorship — do not paste seed lines as slot-fill
   and do not leave blanks for a later refill. Label actuals ≤ close vs forecast after
   close; pipeline only from package pipeline/deal fields. GTM takeaways must cover
   closed-lost, slipped, coverage, action. Risks/Opps cards author from BOARD R&O EVIDENCE.
4. Causal language may only name ATTRIBUTION PACKAGE allowed_drivers; forward watch-outs
   must ground in forecast/pipeline allowlist entries. Rich story from packages + board
   R&O evidence is required — never empty "-" risk details.
5. Apply LAYOUT LOCKS from the user message (no slide-2 KPI sparklines; period_matrix /
   CFS YTD Variance from payload including Ending Cash; KT under waterfalls on slides 3/7;
   YTD cash summary below bridge on slide 5 with no overlap; CFS Source below Ending Cash;
   pipeline shape_bars with Begin+End; no overlapping funnel titles; slide 6 GTM uses
   full-width KT below primary visual per deck_slide_order.gtm_slide_6; omit projected
   headcount slide when include_slide is false; Department Updates section labels on
   dept_funnel_efficiency and dept_big_efforts slides).
6. Use pptx.ShapeType / pptx.ChartType on the pptx instance — never pptxgen.ShapeType.
7. End with pptx.writeFile({ fileName: "OUTPUT.pptx" }). Return raw JavaScript only.

""" + PROMPT5_CRAFT_CRITERIA + "\n" + PROMPT5_BOARD_NARRATIVE_RULES
