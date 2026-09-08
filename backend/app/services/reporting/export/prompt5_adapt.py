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
   (TOL_ACTUALS=$1.00). "—" is permitted ONLY when the payload itself has no value for
   that cell — see DATA FIDELITY below. Never write a don't-know essay in a cell.
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
   pipeline shape_bars with Begin+End; no overlapping funnel titles).
6. Use pptx.ShapeType / pptx.ChartType on the pptx instance — never pptxgen.ShapeType.
7. SAFE AREA overrides "preserve the reference geometry". The slide is 13.33 x 7.50in
   and the footer sits at y 7.05. No shape may have y + h > 7.00. The reference script
   pitches Key Takeaways bullets at 0.55in boxes 0.60in apart, which puts a third
   bullet off the bottom of the slide — do not copy that pitch. Use h=0.20 on a 0.26
   pitch and check the last bullet: y0 + 0.28 + 0.26 * count <= 7.00. If the period's
   commentary needs more room than that allows, write fewer, denser bullets.
8. End with pptx.writeFile({ fileName: "OUTPUT.pptx" }). Return raw JavaScript only.

DATA FIDELITY (mandatory — a supplied value that renders as "—" is a defect)
A. When the payload gives a table its rows, render every row from those rows and no
   other source. The monthly cash bridge on slide 5 is cash_liquidity.bridge_table.rows:
   each entry has label / actual / budget already formatted as display strings. Emit them
   verbatim. Do not re-derive them, do not look for the underlying column names
   (payroll_cash_out, vendor_cash_out_n30, commission_cash_out), and do not substitute
   "—" for a row that carries a value. Payroll, Vendor payments, Commissions and Capex
   are populated every month; blanks in those cells have shipped to a board and been
   caught by the CFO, while the Key Takeaways on the same slide quoted the real figures.
B. "—" means the payload value is absent or null. It does not mean you could not find it.
   If a number appears anywhere in the payload for that cell, it must appear in the cell.
C. Never repeat one value down a per-item column. Efficiency and Win Rate on the GTM
   channel table are PER CHANNEL: if every channel would print the same figure you have
   picked up a blended total instead of the channel's own value — read the per-channel
   field, and if the payload genuinely has only a blended number, leave the per-channel
   cells "—" rather than stamping the blend onto every row and the TOTAL.
D. A TOTAL row must be the total of the rows above it as printed. If the column has
   values, total them; do not leave a TOTAL blank while its constituents carry numbers.
E. Numbers in narrative must match the numbers in the tables on the same slide. If a
   takeaway cites payroll or MQLs, the table must show the same figure.

""" + PROMPT5_CRAFT_CRITERIA + "\n" + PROMPT5_BOARD_NARRATIVE_RULES
