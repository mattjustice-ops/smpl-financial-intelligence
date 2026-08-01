"""Prompt 5 gold-reference script adaptation — same layout, new month data."""

from app.services.reporting.export.prompt5_narrative import PROMPT5_BOARD_NARRATIVE_RULES

PROMPT5_ADAPT_SYSTEM = """You adapt an existing PptxGenJS board deck script for a new close period.

This is script adaptation (Option 1): the reference script defines layout and styling.
Your job is to substitute fresh data from the JSON payload — not to redesign the deck in Python.

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
   Replace every Key Takeaways bullet, risk/opportunity detail+action line, board-action
   copy, and slide commentary string using the BOARD NARRATIVE DEPTH rules below and the
   CLOSE FREEZE / EVIDENCE / ATTRIBUTION / BOARD R&O SEED / GTM NARRATIVE / KEY TAKEAWAYS
   SEED packages in the user message. Every KT panel must have 3–5 filled bullets — if a
   slot would be blank, copy KEY TAKEAWAYS SEED verbatim. Label actuals ≤ close vs forecast
   after close; pipeline only from package pipeline/deal fields. GTM takeaways must cover
   closed-lost, slipped, coverage, action. Risks/Opps cards must rewrite from BOARD R&O SEED.
4. Causal language may only name ATTRIBUTION PACKAGE allowed_drivers; forward watch-outs
   must ground in forecast/pipeline allowlist entries. Rich story from packages + board
   R&O seed is required — never empty "-" risk details.
5. Apply LAYOUT LOCKS from the user message (KT under waterfalls on slides 3/7; YTD cash
   summary on slide 5; pipeline shape_bars with Begin+End; no overlapping funnel titles).
6. Use pptx.ShapeType / pptx.ChartType on the pptx instance — never pptxgen.ShapeType.
7. End with pptx.writeFile({ fileName: "OUTPUT.pptx" }). Return raw JavaScript only.

""" + PROMPT5_BOARD_NARRATIVE_RULES
