"""Shared board-narrative depth + craft criteria for Prompt 5 (fresh + adapt).

Stolen shape from board regenerate (BOARD_DECK_SLIDE_SYSTEM_PROMPT) and Copilot
(PRIMARY DRIVER / ROOT CAUSE / RECOMMENDED ACTION). KPI/table cells stay numbers.

Authoring principle: Claude generates the deck (layout, charts, commentary).
Board / R&O / GTM / KT blocks in the user message are **evidence inputs** Claude
may cite when authoring — never a template of blank slots to fill, and never a
post-process source that patches emptied takeaways after soft-strip.
"""

# Asserted by tests — keep phrases stable.
PROMPT5_CRAFT_CRITERIA = """\
CRAFT CRITERIA (when you choose X, do Y — generative authorship, not slot-fill)
You author the deck. Packages below are evidence you may use — do NOT treat them
as blank fields to copy into, and do NOT leave placeholders for a later refill.

When you use a WATERFALL (ARR / pipeline shape_bars):
- Additive begin→end flow with real beginning value (never start at 0/blank).
- Category labels on the x-axis baseline (bar.category at bar.category_y) —
  NOT stacked under value labels / under bars.
- Use addShape rectangles from shape_bars; never addChart for waterfalls.

When you provide KEY TAKEAWAYS:
- Author 3–5 complete insight bullets (BOARD NARRATIVE DEPTH shape).
- Never emit blank, lone "—", or empty placeholder takeaways.
- Give the panel enough vertical space; no overlapping text with charts/bridge/footer.
- Soft-strip may redact unmatched $/% tokens inside a bullet — keep the prose.

When laying out ANY slide:
- No colliding labels (e.g. period title + section label sharing coordinates).
- No commentary into the footer band (content y+h ≤ 6.85; footer y=7.05).
- KT under waterfalls goes FULL WIDTH below the chart (slides 3/7), not cramped
  beside the bridge.

When showing CLOSED-MONTH financials (periods ≤ close_period, e.g. June Actual):
- Label and source as Actuals — never Forecast-with-validation-fail for closed months.
- Appendix CFS Actual column = periods ≤ close_month only (never Forecast scenario).
"""

PROMPT5_BOARD_NARRATIVE_RULES = """\
BOARD NARRATIVE DEPTH (Key Takeaways, risks/opps detail, board-action copy, slide
commentary bullets — NOT KPI value cells or table number cells)
Management sees ONLY this deck. Narrative must be extremely insightful but succinct —
board-ready, not one-line "a number changed" stubs and not KPI essays in cells.

Shape every Key Takeaways / commentary block as 3–5 insight bullets:
1. PRIMARY DRIVER + VARIANCE CONTEXT — period actual vs budget (or prior), $/% delta,
   and the allowlisted operational driver from the ATTRIBUTION PACKAGE / freeze.
2. RETENTION / PIPELINE QUALITY — N$R, G$R, expansion vs churn, coverage, created /
   slipped / deferred pipeline when those fields exist in the package (label pipeline
   as pipeline, not actual revenue).
3. OPERATIONAL ROOT CAUSE — what moved in the bridges/waterfalls/GL mix (freeze +
   allowlisted drivers only); if no allowlisted cause fits, restate the variance
   without inventing a story.
4. FORWARD READ — label Actual (periods ≤ close_period) vs Forecast/outlook (after
   close) vs Pipeline; one concrete implication for H2 / next quarter.
5. RECOMMENDED BOARD ACTION — one crisp next step when evidence supports it
   (required on Strategic Assessment + Board Actions; include when natural elsewhere).

Bullet craft (match regenerate / Copilot depth, PPTX-succinct):
- Prefer 3–5 bullets per Key Takeaways panel (slide 3 may use 3–4 if space-tight).
- Each bullet is one complete board sentence, ~28–45 words — not a 8-word delta stub.
- Always include current-period actual, budget, and variance ($) when metrics support it.
- Favorable: lead with the positive signal. Unfavorable: driver + next-quarter
  expectation in the same bullet.
- Lead with the most important signal, not chronology. No two bullets may repeat
  the same fact. Never start two consecutive bullets with the same word.
- Cite _sources keys on material $ / % in takeaway/narrative bullets where feasible
  (e.g. "$7.41M (income_statement.revenue)"). Citations belong in narrative only.
- Never invent metrics, deal names, or causal drivers outside the packages.
- Never use the word "significant" — use the number. No filler ("it is worth noting").
- Never leave a takeaway slot blank or as lone "—" — author the bullet or omit the panel.

GTM / PIPELINE TAKEAWAYS (when that slide exists — craft criteria):
- Follow GTM NARRATIVE REQUIREMENTS in the user message: closed-lost actual vs budget,
  slipped pipeline, coverage vs ending ARR, and a recommended board action.
- Match Copilot depth using gtm_performance + pipeline waterfall evidence — not a
  single closed-won stub. Author the bullets; do not paste evidence lines as slot-fill.

RISKS / OPPORTUNITIES CARDS (when Strategic Assessment includes them):
- Author cards using BOARD R&O EVIDENCE / risks_and_opportunities payload as input
  (board platform risk matrix). Each card keeps: severity, title, detail with
  driver+$, action line.
- Do NOT emit thin fillers ("Close validation", "Deferred pipeline" one-liners, or
  detail "-"). Adapt evidence prose for PPTX brevity; keep the insight.

KPI / TABLE CELLS (strict — separate from narrative):
- Value cells and table number cells = numbers (or "—") ONLY, copied verbatim from
  the DATA PAYLOAD / EVIDENCE PACKAGE.
- Do NOT put (source.key) parentheses, prose commentary, or don't-know essays inside
  KPI value cells or period_matrix / bridge / P&L table number cells.
- Soft-fail / zero-missing bridge lines → "—" — never a narrative explanation in the cell.
"""
