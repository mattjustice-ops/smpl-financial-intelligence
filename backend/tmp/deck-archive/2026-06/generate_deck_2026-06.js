const pptxgen = require("pptxgenjs");
const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";

// ─── THEME ───────────────────────────────────────────────────────────────────
const C = {
  bg: "070d18", surface: "111d2e", surfaceAlt: "0d1520",
  cyan: "00d4aa", amber: "f59e0b", red: "ef4444", green: "22c55e",
  darkGreen: "166534", deepRed: "991b1b",
  white: "ffffff", muted: "6b8ca8", divider: "1a2e42"
};

const Q = "Q2"; const YEAR = "2026"; const MONTH = "June 2026";
const footerBase = `SMPL · Board Operating Review · ${Q} ${YEAR} · CONFIDENTIAL`;

function addFooter(slide, n) {
  slide.addText(`${footerBase}  ${n}/11`, {
    x: 0.35, y: 7.05, w: 12.63, h: 0.22,
    fontSize: 7.5, color: C.muted, fontFace: "Calibri", align: "center"
  });
}

function addSectionLabel(slide, text, x, y, w) {
  slide.addText(text.toUpperCase(), {
    x, y, w, h: 0.2, fontSize: 9, bold: true, color: C.cyan,
    fontFace: "Calibri", align: "left"
  });
}

function addSlideBackground(slide) {
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: C.bg } });
}

function addDivider(slide, x, y, w) {
  slide.addShape(pptx.ShapeType.rect, { x, y, w, h: 0.03, fill: { color: C.divider } });
}

function kpiCard(slide, x, y, w, h, label, value, sub, valueColor) {
  slide.addShape(pptx.ShapeType.rect, { x, y, w, h, fill: { color: C.surface }, line: { color: C.divider, width: 0.5 } });
  slide.addText(label.toUpperCase(), { x: x + 0.1, y: y + 0.08, w: w - 0.2, h: 0.18, fontSize: 7.5, color: C.muted, fontFace: "Calibri", bold: true });
  slide.addText(value, { x: x + 0.1, y: y + 0.26, w: w - 0.2, h: 0.42, fontSize: 22, bold: true, color: valueColor || C.cyan, fontFace: "Calibri" });
  if (sub) slide.addText(sub, { x: x + 0.1, y: y + 0.68, w: w - 0.2, h: 0.2, fontSize: 8, color: C.muted, fontFace: "Calibri" });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 1 — TITLE COVER
// ═══════════════════════════════════════════════════════════════════════════════
{
  let slide = pptx.addSlide();
  addSlideBackground(slide);
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 0.04, fill: { color: C.cyan } });
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 7.46, w: 13.33, h: 0.04, fill: { color: C.cyan } });

  slide.addText("SMPL.ai", { x: 0, y: 2.2, w: 13.33, h: 0.6, fontSize: 36, bold: true, color: C.cyan, fontFace: "Calibri", align: "center" });
  slide.addText("AI Operating System for SaaS Finance Teams", { x: 0, y: 2.85, w: 13.33, h: 0.3, fontSize: 12, color: C.muted, fontFace: "Calibri", align: "center" });
  slide.addShape(pptx.ShapeType.rect, { x: 4.165, y: 3.28, w: 5.0, h: 0.02, fill: { color: C.divider } });
  slide.addText("Board Operating Review", { x: 0, y: 3.45, w: 13.33, h: 0.55, fontSize: 28, bold: true, color: C.white, fontFace: "Calibri", align: "center" });
  slide.addText(`${Q} ${YEAR} · ${MONTH} · Series B`, { x: 0, y: 4.05, w: 13.33, h: 0.3, fontSize: 12, color: C.muted, fontFace: "Calibri", align: "center" });

  slide.addText(`SMPL · Board Operating Review · ${Q} ${YEAR} · 1/11`, {
    x: 0.35, y: 7.05, w: 12.63, h: 0.22, fontSize: 7.5, color: C.muted, fontFace: "Calibri", align: "center"
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 2 — EXECUTIVE DASHBOARD
// ═══════════════════════════════════════════════════════════════════════════════
{
  slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 2);

  addSectionLabel(slide, "Executive Dashboard", 0.35, 0.35, 5);
  slide.addText("Executive Dashboard — June 2026", { x: 0.35, y: 0.55, w: 9, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });

  // Row 1: 5 KPI cards
  const cards = [
    { label: "Ending ARR", value: "$85.31M", sub: "vs bud $84.89M  +0.5%" },
    { label: "Revenue (CM)", value: "$7.35M", sub: "vs bud $7.72M  -4.8%", vc: C.amber },
    { label: "Ending Cash", value: "$30.00M", sub: "vs bud $31.46M  -4.6%", vc: C.amber },
    { label: "Gross Margin %", value: "70.0%", sub: "vs bud 70.0%  on target" },
    { label: "EBITDA (CM)", value: "$661.5K", sub: "vs bud $647.5K  +2.2%" }
  ];
  let cw = 2.45; const ch = 1.0; const cy = 0.95;
  cards.forEach((c, i) => {
    kpiCard(slide, 0.35 + i * (cw + 0.07), cy, cw, ch, c.label, c.value, c.sub, c.vc || C.cyan);
  });

  addDivider(slide, 0.35, 2.10, 12.63);

  // Period matrix table
  const tblX = 0.35; const tblY = 2.20; const tblW = 7.2;
  addSectionLabel(slide, "Period Matrix", tblX, tblY, 4);

  const pmRows = [
    ["Metric", "CM Actual", "CM Budget", "CM Variance", "YTD Actual", "YTD Budget", "YTD Variance"],
    ["Ending ARR", "$85.31M", "$84.89M", "+$413.1K", "$85.31M", "$84.89M", "+$413.1K"],
    ["Revenue", "$7.35M", "$7.72M", "-$367.5K", "$39.45M", "$41.42M", "-$1.97M"],
    ["EBITDA", "$661.5K", "$647.5K", "+$14.0K", "$3.87M", "$3.81M", "+$59.1K"],
    ["Gross Margin %", "70.0%", "70.0%", "—", "70.8%", "70.8%", "—"],
    ["Ending Cash", "$30.00M", "$31.46M", "-$1.46M", "$30.00M", "$31.46M", "-$1.46M"],
    ["Pipeline Created", "$9.19M", "$10.32M", "-$1.13M", "$51.18M", "$51.96M", "-$780.2K"]
  ];

  const colW = [1.6, 0.82, 0.82, 0.82, 0.82, 0.82, 0.82];
  const rowH = 0.28;
  pmRows.forEach((row, ri) => {
    row.forEach((cell, ci) => {
      let isHeader = ri === 0;
      let isVar = ci === 3 || ci === 6;
      let fc = C.white;
      if (isHeader) fc = C.muted;
      else if (isVar && cell.startsWith("+")) fc = C.green;
      else if (isVar && cell.startsWith("-")) fc = C.red;
      let xOff = colW.slice(0, ci).reduce((a, b) => a + b, 0);
      slide.addShape(pptx.ShapeType.rect, {
        x: tblX + xOff, y: tblY + 0.22 + ri * rowH, w: colW[ci], h: rowH,
        fill: { color: ri % 2 === 0 ? C.surface : C.surfaceAlt },
        line: { color: C.divider, width: 0.3 }
      });
      slide.addText(cell, {
        x: tblX + xOff + 0.05, y: tblY + 0.22 + ri * rowH, w: colW[ci] - 0.05, h: rowH,
        fontSize: 8, color: fc, fontFace: "Calibri", valign: "middle",
        bold: isHeader
      });
    });
  });

  // Key Takeaways
  const ktX = 7.75; const ktY = 2.20;
  addSectionLabel(slide, "Key Takeaways", ktX, ktY, 5);
  slide.addShape(pptx.ShapeType.rect, { x: ktX, y: ktY + 0.22, w: 5.23, h: 4.2, fill: { color: C.surface }, line: { color: C.divider, width: 0.5 } });
  const bullets2 = [
    "1. ARR $85.31M beat budget +$413.1K; MoM growth +2.2% reflects steady new business and expansion momentum.",
    "2. Revenue $7.35M CM trails budget -4.8%; YTD $39.45M behind -$1.97M. Conversion of ending pipeline $8.27M critical for H2 ramp.",
    "3. EBITDA $661.5K beat budget +$14.0K; YTD $3.87M ahead +$59.1K. Opex discipline (S&M -5.7%, R&D -5.7%) sustaining profitability.",
    "4. Cash $30.00M vs budget $31.46M; YTD collections $55.66M support liquidity. H2 collections expected to moderate 40% vs Q1 average.",
    "5. FY ARR outlook $90.29M vs $96.10M budget; pipeline coverage 3.0x. Prioritize enterprise conversion and channel reallocation to Outbound/Partner."
  ];
  bullets2.forEach((b, i) => {
    slide.addText(b, { x: ktX + 0.15, y: ktY + 0.35 + i * 0.80, w: 4.93, h: 0.72, fontSize: 8.5, color: C.white, fontFace: "Calibri", valign: "top", wrap: true });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 3 — ARR ANALYSIS (waterfall with addShape ONLY)
// ═══════════════════════════════════════════════════════════════════════════════
{
  slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 3);

  addSectionLabel(slide, "ARR Analysis", 0.35, 0.35, 5);
  slide.addText("ARR Analysis — June 2026", { x: 0.35, y: 0.55, w: 9, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });
  slide.addText("Begin ARR → components → Ending ARR ($M)", { x: 0.35, y: 0.88, w: 7, h: 0.2, fontSize: 9, color: C.muted, fontFace: "Calibri" });

  // Waterfall chart area using shape_bars
  const shapeBars = [
    { x: 0.548, y: 3.33, w: 0.547, h: 1.72, color: "00d4aa", label: "$83.44M", label_position: "above", category: "Begin ARR" },
    { x: 1.491, y: 2.49, w: 0.547, h: 0.84, color: "166534", label: "+$1.68M", label_position: "above", category: "New Business" },
    { x: 2.434, y: 2.05, w: 0.547, h: 0.435, color: "166534", label: "+$0.87M", label_position: "above", category: "Expansion" },
    { x: 3.377, y: 1.98, w: 0.547, h: 0.07, color: "166534", label: "+$0.14M", label_position: "above", category: "Reactivation" },
    { x: 4.319, y: 2.135, w: 0.547, h: 0.155, color: "991b1b", label: "-$0.31M", label_position: "below", category: "Contraction" },
    { x: 5.262, y: 2.395, w: 0.547, h: 0.26, color: "991b1b", label: "-$0.52M", label_position: "below", category: "Churn" },
    { x: 6.205, y: 2.395, w: 0.547, h: 2.655, color: "00d4aa", label: "$85.31M", label_position: "above", category: "End ARR" }
  ];

  // Y-axis gridlines
  const chartAreaX = 0.35; const chartAreaY = 1.05; const chartAreaH = 4.0;
  const yMin = 80; const yMax = 88;
  [80, 82, 84, 86, 88].forEach(tick => {
    let yPct = 1 - (tick - yMin) / (yMax - yMin);
    let yPos = chartAreaY + yPct * chartAreaH;
    slide.addShape(pptx.ShapeType.rect, { x: chartAreaX, y: yPos, w: 6.6, h: 0.01, fill: { color: C.divider } });
    slide.addText(`$${tick}M`, { x: 0.0, y: yPos - 0.1, w: 0.45, h: 0.2, fontSize: 7, color: C.muted, fontFace: "Calibri", align: "right" });
  });

  const axisY = 5.15;
  shapeBars.forEach(bar => {
    slide.addShape(pptx.ShapeType.rect, {
      x: bar.x, y: bar.y, w: bar.w, h: bar.h,
      fill: { color: bar.color },
      line: { color: bar.color, width: 0.5 }
    });
    let labelY = bar.label_position === "above" ? bar.y - 0.22 : bar.y + bar.h + 0.04;
    let lc = bar.color === "991b1b" ? C.red : (bar.color === "166534" ? C.green : C.cyan);
    slide.addText(bar.label, { x: bar.x - 0.05, y: labelY, w: bar.w + 0.1, h: 0.2, fontSize: 7.5, color: lc, fontFace: "Calibri", align: "center", bold: true });
    slide.addText(bar.category, { x: bar.x - 0.05, y: axisY, w: bar.w + 0.1, h: 0.28, fontSize: 7, color: C.muted, fontFace: "Calibri", align: "center", wrap: true });
  });

  addDivider(slide, 7.1, 1.05, 0.03);
  slide.addShape(pptx.ShapeType.rect, { x: 7.05, y: 1.05, w: 0.03, h: 4.2, fill: { color: C.divider } });

  // Right panel — KPIs + bridge only
  const rx = 7.25;
  addSectionLabel(slide, "ARR KPIs", rx, 1.05, 5.7);

  const arrKpis = [
    { label: "Ending ARR", value: "$85.31M", sub: "vs bud $84.89M  +$413.1K" },
    { label: "Net New ARR", value: "$1.68M", sub: "vs bud $1.77M  -$84.2K", vc: C.amber },
    { label: "G$R", value: "99.4%", sub: "Gross Retention" },
    { label: "Pipeline Coverage", value: "3.0x", sub: "vs ending ARR" }
  ];
  arrKpis.forEach((k, i) => {
    kpiCard(slide, rx + (i % 2) * 2.95, 1.28 + Math.floor(i / 2) * 1.08, 2.8, 0.98, k.label, k.value, k.sub, k.vc || C.cyan);
  });

  // Bridge table
  addSectionLabel(slide, "ARR Bridge", rx, 3.52, 5.7);
  const bridgeRows = [
    ["Component", "Actual", "Budget", "Variance"],
    ["Beginning ARR", "$83.44M", "$82.94M", "+$506.2K"],
    ["New Business", "$1.68M", "$1.77M", "-$84.2K"],
    ["Expansion", "$869.1K", "$912.6K", "-$43.5K"],
    ["Reactivation", "$142.9K", "$150.0K", "-$7.1K"],
    ["Contraction", "$313.7K", "$329.3K", "-$15.7K"],
    ["Churn", "$520.2K", "$546.2K", "-$26.0K"],
    ["Ending ARR", "$85.31M", "$84.89M", "+$413.1K"]
  ];
  const bColW = [1.5, 1.0, 1.0, 1.0];
  bridgeRows.forEach((row, ri) => {
    row.forEach((cell, ci) => {
      isHeader = ri === 0;
      isVar = ci === 3;
      fc = C.white;
      if (isHeader) fc = C.muted;
      else if (isVar && cell.startsWith("+")) fc = C.green;
      else if (isVar && cell.startsWith("-")) fc = C.red;
      xOff = bColW.slice(0, ci).reduce((a, b) => a + b, 0);
      slide.addShape(pptx.ShapeType.rect, {
        x: rx + xOff, y: 3.72 + ri * 0.22, w: bColW[ci], h: 0.22,
        fill: { color: ri % 2 === 0 ? C.surface : C.surfaceAlt },
        line: { color: C.divider, width: 0.3 }
      });
      slide.addText(cell, {
        x: rx + xOff + 0.05, y: 3.72 + ri * 0.22, w: bColW[ci] - 0.05, h: 0.22,
        fontSize: 7.5, color: fc, fontFace: "Calibri", valign: "middle", bold: isHeader
      });
    });
  });

  // Key Takeaways — full width under waterfall
  addDivider(slide, 0.35, 5.48, 12.63);
  addSectionLabel(slide, "Key Takeaways", 0.35, 5.55, 12.63);
  const bullets3 = [
    "1. Ending ARR $85.31M beat budget +$413.1K; MoM growth +2.2% from $83.44M in May driven by new business and expansion.",
    "2. New Business $1.68M slightly below $1.77M budget; expansion $869.1K vs $912.6K budget reflects timing in enterprise segment.",
    "3. Churn $520.2K and contraction $313.7K both below budget — retention tracking favorably with G$R 99.4% and N$R 100%+.",
    "4. FY ARR outlook $90.29M vs $96.10M budget; H2 ramp requires pipeline acceleration and enterprise close velocity improvement."
  ];
  bullets3.forEach((b, i) => {
    slide.addText(b, { x: 0.35, y: 5.75 + i * 0.28, w: 12.63, h: 0.26, fontSize: 9, color: C.white, fontFace: "Calibri", wrap: true });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 4 — P&L REVIEW
// ═══════════════════════════════════════════════════════════════════════════════
{
  slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 4);

  addSectionLabel(slide, "P&L Review", 0.35, 0.35, 5);
  slide.addText("P&L Review — June 2026", { x: 0.35, y: 0.55, w: 9, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });

  // Top 4 KPI cards
  const plCards = [
    { label: "Revenue (CM)", value: "$7.35M", sub: "vs bud $7.72M  -4.8%", vc: C.amber },
    { label: "Gross Margin %", value: "70.0%", sub: "vs bud 70.0%  on target" },
    { label: "EBITDA (CM)", value: "$661.5K", sub: "vs bud $647.5K  +2.2%" },
    { label: "Net Income (CM)", value: "$409.0K", sub: "vs bud $393.4K  +4.0%" }
  ];
  const pcw = 3.1;
  plCards.forEach((c, i) => {
    kpiCard(slide, 0.35 + i * (pcw + 0.07), 0.95, pcw, 0.98, c.label, c.value, c.sub, c.vc || C.cyan);
  });

  addDivider(slide, 0.35, 2.0, 12.63);

  // P&L detail table
  const plHeaders = ["Line Item", "CM Actual", "CM Budget", "CM Variance", "YTD Actual", "YTD Budget", "YTD Variance"];
  const plRows = [
    ["Revenue", "$7.35M", "$7.72M", "-$367.5K", "$39.45M", "$41.42M", "-$1.97M"],
    ["COGS", "$2.20M", "$2.32M", "-$110.2K", "$11.51M", "$12.09M", "-$575.7K"],
    ["Gross Profit", "$5.14M", "$5.40M", "-$257.2K", "$27.94M", "$29.33M", "-$1.40M"],
    ["Gross Margin %", "70.0%", "70.0%", "—", "70.8%", "70.8%", "—"],
    ["S&M", "$2.50M", "$2.65M", "-$151.2K", "$13.41M", "$14.22M", "-$811.5K"],
    ["R&D", "$1.18M", "$1.25M", "-$71.1K", "$6.31M", "$6.69M", "-$381.9K"],
    ["G&A", "$808.5K", "$857.4K", "-$48.9K", "$4.34M", "$4.60M", "-$262.5K"],
    ["EBITDA", "$661.5K", "$647.5K", "+$14.0K", "$3.87M", "$3.81M", "+$59.1K"],
    ["D&A", "$110.2K", "$115.8K", "-$5.5K", "$591.8K", "$621.3K", "-$29.6K"],
    ["Net Income", "$409.0K", "$393.4K", "+$15.6K", "$2.43M", "$2.36M", "+$71.0K"]
  ];
  const plColW = [1.55, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95];
  const plTblX = 0.35; const plTblY = 2.1;

  [plHeaders, ...plRows].forEach((row, ri) => {
    row.forEach((cell, ci) => {
      isHeader = ri === 0;
      isVar = ci === 3 || ci === 6;
      let isBold = ["Gross Profit", "EBITDA", "Net Income"].includes(row[0]);
      fc = C.white;
      if (isHeader) fc = C.muted;
      else if (isVar && cell.startsWith("+")) fc = C.green;
      else if (isVar && cell.startsWith("-")) fc = C.red;
      xOff = plColW.slice(0, ci).reduce((a, b) => a + b, 0);
      slide.addShape(pptx.ShapeType.rect, {
        x: plTblX + xOff, y: plTblY + ri * 0.28, w: plColW[ci], h: 0.28,
        fill: { color: ri % 2 === 0 ? C.surface : C.surfaceAlt },
        line: { color: C.divider, width: 0.3 }
      });
      slide.addText(cell, {
        x: plTblX + xOff + 0.05, y: plTblY + ri * 0.28, w: plColW[ci] - 0.05, h: 0.28,
        fontSize: 8.5, color: fc, fontFace: "Calibri", valign: "middle",
        bold: isHeader || isBold
      });
    });
  });

  // Key Takeaways right panel
  const ktX4 = 8.0; const ktY4 = 2.1;
  addSectionLabel(slide, "Key Takeaways", ktX4, ktY4, 5.0);
  slide.addShape(pptx.ShapeType.rect, { x: ktX4, y: ktY4 + 0.22, w: 5.0, h: 4.5, fill: { color: C.surface }, line: { color: C.divider, width: 0.5 } });
  const bullets4 = [
    "1. Revenue $7.35M CM trails budget -4.8%; YTD $39.45M behind -$1.97M. Expansion timing and new logo conversion critical for H2 close.",
    "2. Gross margin held at 70.0% CM and 70.8% YTD — in line with budget on both horizons; COGS discipline intact.",
    "3. EBITDA $661.5K beat budget +$14.0K; YTD $3.87M ahead +$59.1K. S&M and R&D both -5.7% vs budget reflecting opex leverage.",
    "4. Net income $409.0K CM, +4.0% vs budget; YTD $2.43M ahead +$71.0K — profitability trajectory remains intact despite revenue headwind.",
    "5. Board action: validate P&L tie-out and approve H2 revenue acceleration plan with enterprise focus and channel reallocation."
  ];
  bullets4.forEach((b, i) => {
    slide.addText(b, { x: ktX4 + 0.15, y: ktY4 + 0.35 + i * 0.82, w: 4.7, h: 0.72, fontSize: 8.5, color: C.white, fontFace: "Calibri", valign: "top", wrap: true });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 5 — CASH & LIQUIDITY
// ═══════════════════════════════════════════════════════════════════════════════
{
  slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 5);

  addSectionLabel(slide, "Cash & Liquidity", 0.35, 0.35, 5);
  slide.addText("Cash & Liquidity — June 2026", { x: 0.35, y: 0.55, w: 9, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });

  // Left: Cash bridge
  addSectionLabel(slide, "Monthly Cash Bridge", 0.35, 0.98, 5);
  const bridgeItems = [
    { label: "Beginning Cash", actual: "$29.50M", budget: "$29.60M", bold: true },
    { label: "Collections", actual: "$7.13M", budget: "$8.91M" },
    { label: "Payroll", actual: "$2.47M", budget: "$4.00M" },
    { label: "Vendor Payments", actual: "$3.66M", budget: "$1.40M" },
    { label: "Commissions", actual: "$199.9K", budget: "$370.8K" },
    { label: "Capex", actual: "$147.0K", budget: "$220.0K" },
    { label: "Ending Cash", actual: "$30.00M", budget: "$31.46M", bold: true }
  ];
  const bHdr = ["Line Item", "Actual", "Budget"];
  const bCW = [2.0, 1.0, 1.0];
  [bHdr, ...bridgeItems.map(r => [r.label, r.actual, r.budget])].forEach((row, ri) => {
    row.forEach((cell, ci) => {
      isHeader = ri === 0;
      isBold = ri > 0 && bridgeItems[ri - 1].bold;
      xOff = bCW.slice(0, ci).reduce((a, b) => a + b, 0);
      slide.addShape(pptx.ShapeType.rect, {
        x: 0.35 + xOff, y: 1.18 + ri * 0.3, w: bCW[ci], h: 0.3,
        fill: { color: ri % 2 === 0 ? C.surface : C.surfaceAlt },
        line: { color: C.divider, width: 0.3 }
      });
      slide.addText(cell, {
        x: 0.35 + xOff + 0.05, y: 1.18 + ri * 0.3, w: bCW[ci] - 0.05, h: 0.3,
        fontSize: 8.5, color: isHeader ? C.muted : C.white, fontFace: "Calibri",
        valign: "middle", bold: isHeader || isBold
      });
    });
  });

  // YTD cash summary — MUST sit below the bridge Ending Cash row (no overlap).
  const ytdSumY = 4.05;
  addSectionLabel(slide, "YTD Cash Summary", 0.35, ytdSumY, 4.2);
  slide.addShape(pptx.ShapeType.rect, { x: 0.35, y: ytdSumY + 0.20, w: 4.2, h: 1.35, fill: { color: C.surface }, line: { color: C.divider, width: 0.5 } });
  slide.addText("YTD Collections: $55.66M", { x: 0.45, y: ytdSumY + 0.28, w: 4.0, h: 0.28, fontSize: 10, color: C.white, fontFace: "Calibri", bold: true });
  slide.addText("YTD Ending Cash: $30.00M", { x: 0.45, y: ytdSumY + 0.58, w: 4.0, h: 0.28, fontSize: 10, color: C.cyan, fontFace: "Calibri", bold: true });
  slide.addText("YTD Ending Cash Budget: $31.46M", { x: 0.45, y: ytdSumY + 0.88, w: 4.0, h: 0.28, fontSize: 9, color: C.muted, fontFace: "Calibri" });

  // Right: Key Takeaways
  const ktX5 = 4.8; const ktY5 = 0.98;
  addSectionLabel(slide, "Key Takeaways", ktX5, ktY5, 8.2);
  slide.addShape(pptx.ShapeType.rect, { x: ktX5, y: ktY5 + 0.22, w: 8.18, h: 4.65, fill: { color: C.surface }, line: { color: C.divider, width: 0.5 } });
  const bullets5 = [
    "1. Ending cash $30.00M vs budget $31.46M; collections $7.13M below budget $8.91M reflect timing of annual billing concentration.",
    "2. YTD collections $55.66M support strong liquidity; cash headroom $20.00M above $10.00M floor provides strategic flexibility.",
    "3. Payroll $2.47M vs budget $4.00M; vendor payments $3.66M above budget $1.40M. Timing variance expected to normalize in H2.",
    "4. FY cash outlook $32.02M vs $23.85M budget; +34.3% upside enables strategic investment. H2 collections expected to moderate 40% vs Q1 average.",
    "5. Board action: confirm ending cash ties to balance sheet; update H2 collections model for annual billing concentration and deploy excess strategically."
  ];
  bullets5.forEach((b, i) => {
    slide.addText(b, { x: ktX5 + 0.15, y: ktY5 + 0.35 + i * 0.88, w: 7.88, h: 0.80, fontSize: 8.5, color: C.white, fontFace: "Calibri", valign: "top", wrap: true });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 6 — GTM / MARKETING FUNNEL
// ═══════════════════════════════════════════════════════════════════════════════
{
  slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 6);

  addSectionLabel(slide, "GTM Performance", 0.35, 0.35, 5);
  slide.addText("GTM Performance — June 2026", { x: 0.35, y: 0.55, w: 9, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });

  // Marketing funnel section
  addSectionLabel(slide, "Marketing Funnel", 0.35, 0.98, 5);
  const funnelData = [
    { stage: "MQLs", actual: "423", budget: "151", var: "+272" },
    { stage: "SQLs", actual: "178", budget: "—", var: "—" },
    { stage: "SALs", actual: "100", budget: "—", var: "—" },
    { stage: "Opps Created", actual: "53", budget: "—", var: "—" },
    { stage: "Pipeline Created", actual: "$9.19M", budget: "$10.32M", var: "-$1.13M" },
    { stage: "Closed Won", actual: "$3.53M", budget: "—", var: "—" }
  ];
  const funnelCols = ["Stage", "Actual", "Budget", "Variance"];
  const funnelColW = [1.8, 1.2, 1.2, 1.2];
  [funnelCols, ...funnelData.map(r => [r.stage, r.actual, r.budget, r.var])].forEach((row, ri) => {
    row.forEach((cell, ci) => {
      isHeader = ri === 0;
      xOff = funnelColW.slice(0, ci).reduce((a, b) => a + b, 0);
      fc = C.white;
      if (isHeader) fc = C.muted;
      else if (ci === 3 && cell.startsWith("+")) fc = C.green;
      else if (ci === 3 && cell.startsWith("-")) fc = C.red;
      slide.addShape(pptx.ShapeType.rect, {
        x: 0.35 + xOff, y: 1.18 + ri * 0.28, w: funnelColW[ci], h: 0.28,
        fill: { color: ri % 2 === 0 ? C.surface : C.surfaceAlt },
        line: { color: C.divider, width: 0.3 }
      });
      slide.addText(cell, {
        x: 0.35 + xOff + 0.05, y: 1.18 + ri * 0.28, w: funnelColW[ci] - 0.05, h: 0.28,
        fontSize: 8.5, color: fc, fontFace: "Calibri", valign: "middle", bold: isHeader
      });
    });
  });

  // Channel efficiency table
  addSectionLabel(slide, "Channel Efficiency", 0.35, 3.0, 5);
  const channelData = [
    { channel: "Paid Search", spend: "$85K", pipeline: "$470K", efficiency: "5.5x", wr: "30.0%" },
    { channel: "Paid Social", spend: "$59K", pipeline: "$323K", efficiency: "5.5x", wr: "30.0%" },
    { channel: "Organic Search", spend: "$53K", pipeline: "$294K", efficiency: "5.5x", wr: "30.0%" },
    { channel: "Partner", spend: "$53K", pipeline: "$294K", efficiency: "5.5x", wr: "30.0%" },
    { channel: "Outbound", spend: "$48K", pipeline: "$264K", efficiency: "5.5x", wr: "30.0%" },
    { channel: "TOTAL", spend: "$534K", pipeline: "$2.94M", efficiency: "5.5x", wr: "—" }
  ];
  const chanCols = ["Channel", "Spend", "Pipeline", "Efficiency", "Win Rate"];
  const chanColW = [1.5, 0.9, 1.0, 1.0, 0.9];
  [chanCols, ...channelData.map(r => [r.channel, r.spend, r.pipeline, r.efficiency, r.wr])].forEach((row, ri) => {
    row.forEach((cell, ci) => {
      isHeader = ri === 0;
      isBold = ri === channelData.length;
      xOff = chanColW.slice(0, ci).reduce((a, b) => a + b, 0);
      slide.addShape(pptx.ShapeType.rect, {
        x: 0.35 + xOff, y: 3.2 + ri * 0.26, w: chanColW[ci], h: 0.26,
        fill: { color: ri % 2 === 0 ? C.surface : C.surfaceAlt },
        line: { color: C.divider, width: 0.3 }
      });
      slide.addText(cell, {
        x: 0.35 + xOff + 0.04, y: 3.2 + ri * 0.26, w: chanColW[ci] - 0.04, h: 0.26,
        fontSize: 8, color: isHeader ? C.muted : C.white, fontFace: "Calibri", valign: "middle",
        bold: isHeader || isBold
      });
    });
  });

  // Right: Key Takeaways
  const ktX6 = 5.8; const ktY6 = 0.98;
  addSectionLabel(slide, "Key Takeaways", ktX6, ktY6, 7.2);
  slide.addShape(pptx.ShapeType.rect, { x: ktX6, y: ktY6 + 0.22, w: 7.18, h: 5.8, fill: { color: C.surface }, line: { color: C.divider, width: 0.5 } });
  const bullets6 = [
    "1. MQLs 423 vs budget 151; +180% above plan reflects strong demand generation. SQL conversion 42% and SAL conversion 56% track favorably.",
    "2. Closed-lost $4.56M vs budget $4.85M; -5.9% variance. Run structured loss review to identify competitive/pricing pressure and deal quality issues.",
    "3. Slipped pipeline $1.09M vs budget $1.16M; re-stage with owners and validate next steps before H2 forecast lock.",
    "4. All channels blended 5.5x efficiency; Paid Search/Social absorb 50% of spend at sub-6% win rates. Partner and Outbound severely under-invested.",
    "5. Board action: approve budget-neutral $0.96M reallocation from Paid to Partner/Referral for est. +$5M pipeline at 5x+ efficiency."
  ];
  bullets6.forEach((b, i) => {
    slide.addText(b, { x: ktX6 + 0.15, y: ktY6 + 0.35 + i * 1.08, w: 6.88, h: 0.98, fontSize: 8.5, color: C.white, fontFace: "Calibri", valign: "top", wrap: true });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 7 — PIPELINE WATERFALL
// ═══════════════════════════════════════════════════════════════════════════════
{
  slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 7);

  addSectionLabel(slide, "Pipeline Analysis", 0.35, 0.35, 5);
  slide.addText("Pipeline Waterfall — June 2026", { x: 0.35, y: 0.55, w: 9, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });
  slide.addText("Begin Pipeline → flows → Ending Pipeline ($M ARR)", { x: 0.35, y: 0.88, w: 7, h: 0.2, fontSize: 9, color: C.muted, fontFace: "Calibri" });

  // Pipeline waterfall using shape_bars
  const pipeShapeBars = [
    { x: 0.581, y: 3.055, w: 0.638, h: 1.545, color: "00d4aa", label: "$8.27M", label_position: "above", category: "Begin Pipeline", category_y: 4.68 },
    { x: 1.681, y: 1.338, w: 0.638, h: 1.717, color: "166534", label: "+$9.19M", label_position: "above", category: "Created", category_y: 4.68 },
    { x: 2.781, y: 1.34, w: 0.638, h: 0.66, color: "991b1b", label: "-$3.53M", label_position: "below", category: "Closed Won", category_y: 4.68 },
    { x: 3.881, y: 1.999, w: 0.638, h: 0.852, color: "991b1b", label: "-$4.56M", label_position: "below", category: "Closed Lost", category_y: 4.68 },
    { x: 4.981, y: 2.851, w: 0.638, h: 0.204, color: "991b1b", label: "-$1.09M", label_position: "below", category: "Slipped", category_y: 4.68 },
    { x: 6.081, y: 3.055, w: 0.638, h: 1.545, color: "00d4aa", label: "$8.27M", label_position: "above", category: "End Pipeline", category_y: 4.68 }
  ];

  // Y-axis gridlines
  const pipeChartX = 0.35; const pipeChartY = 1.05; const pipeChartH = 3.55;
  const pipeYMin = 0; const pipeYMax = 19;
  [0, 5, 10, 15, 19].forEach(tick => {
    yPct = 1 - (tick - pipeYMin) / (pipeYMax - pipeYMin);
    yPos = pipeChartY + yPct * pipeChartH;
    slide.addShape(pptx.ShapeType.rect, { x: pipeChartX, y: yPos, w: 6.6, h: 0.01, fill: { color: C.divider } });
    slide.addText(`$${tick}M`, { x: 0.0, y: yPos - 0.1, w: 0.45, h: 0.2, fontSize: 7, color: C.muted, fontFace: "Calibri", align: "right" });
  });

  const pipeAxisY = 4.68;
  pipeShapeBars.forEach(bar => {
    slide.addShape(pptx.ShapeType.rect, {
      x: bar.x, y: bar.y, w: bar.w, h: bar.h,
      fill: { color: bar.color },
      line: { color: bar.color, width: 0.5 }
    });
    labelY = bar.label_position === "above" ? bar.y - 0.22 : bar.y + bar.h + 0.02;
    lc = bar.color === "991b1b" ? C.red : (bar.color === "166534" ? C.green : C.cyan);
    slide.addText(bar.label, { x: bar.x - 0.05, y: labelY, w: bar.w + 0.1, h: 0.2, fontSize: 7.5, color: lc, fontFace: "Calibri", align: "center", bold: true });
    slide.addText(bar.category, { x: bar.x - 0.08, y: pipeAxisY, w: bar.w + 0.16, h: 0.35, fontSize: 7, color: C.muted, fontFace: "Calibri", align: "center", wrap: true });
  });

  // Right KPIs + bridge
  const rx7 = 7.25;
  addSectionLabel(slide, "Pipeline KPIs", rx7, 1.05, 5.7);
  const pipeKpis = [
    { label: "Ending Pipeline", value: "$8.27M", sub: "vs begin $8.27M" },
    { label: "Pipeline Created", value: "$9.19M", sub: "vs bud $10.32M  -$1.13M", vc: C.amber },
    { label: "Closed Lost", value: "$4.56M", sub: "vs bud $4.85M  -$289K" },
    { label: "Slipped Pipeline", value: "$1.09M", sub: "vs bud $1.16M  -$70K" }
  ];
  pipeKpis.forEach((k, i) => {
    kpiCard(slide, rx7 + (i % 2) * 2.95, 1.28 + Math.floor(i / 2) * 1.0, 2.8, 0.92, k.label, k.value, k.sub, k.vc || C.cyan);
  });

  addSectionLabel(slide, "Pipeline Bridge", rx7, 3.4, 5.7);
  const pipeBridge = [
    ["Component", "Actual", "Budget", "Variance"],
    ["Beginning Pipeline", "$8.27M", "$8.68M", "—"],
    ["Created", "$9.19M", "$10.32M", "-$1.13M"],
    ["Closed Won", "-$3.53M", "—", "—"],
    ["Closed Lost", "-$4.56M", "-$4.85M", "—"],
    ["Slipped", "-$1.09M", "-$1.16M", "—"],
    ["Ending Pipeline", "$8.27M", "$9.27M", "-$1.00M"]
  ];
  const pbW = [1.55, 1.0, 1.0, 1.0];
  pipeBridge.forEach((row, ri) => {
    row.forEach((cell, ci) => {
      isHeader = ri === 0;
      fc = isHeader ? C.muted : C.white;
      if (!isHeader && ci === 3 && cell.startsWith("+")) fc = C.green;
      if (!isHeader && ci === 3 && cell.startsWith("-")) fc = C.red;
      xOff = pbW.slice(0, ci).reduce((a, b) => a + b, 0);
      slide.addShape(pptx.ShapeType.rect, {
        x: rx7 + xOff, y: 3.6 + ri * 0.22, w: pbW[ci], h: 0.22,
        fill: { color: ri % 2 === 0 ? C.surface : C.surfaceAlt },
        line: { color: C.divider, width: 0.3 }
      });
      slide.addText(cell, {
        x: rx7 + xOff + 0.04, y: 3.6 + ri * 0.22, w: pbW[ci] - 0.04, h: 0.22,
        fontSize: 7.5, color: fc, fontFace: "Calibri", valign: "middle", bold: isHeader
      });
    });
  });

  // Key Takeaways full width BELOW waterfall
  addDivider(slide, 0.35, 5.2, 12.63);
  addSectionLabel(slide, "Key Takeaways", 0.35, 5.28, 12.63);
  const bullets7 = [
    "1. Beginning pipeline $8.27M → ending $8.27M; additive bridge shows created $9.19M offset by closed won $3.53M, lost $4.56M, slipped $1.09M.",
    "2. Closed-lost $4.56M vs budget $4.85M; -5.9% variance. Validate loss reasons (competitive, pricing, timing) and update deal qualification criteria.",
    "3. Slipped pipeline $1.09M vs budget $1.16M; re-stage with owners and confirm next steps before H2 forecast lock to avoid further slippage.",
    "4. Pipeline coverage 3.0x vs ending ARR $85.31M supports H2 ramp; prioritize enterprise conversion velocity and deal cycle acceleration."
  ];
  bullets7.forEach((b, i) => {
    slide.addText(b, { x: 0.35, y: 5.48 + i * 0.32, w: 12.63, h: 0.30, fontSize: 9, color: C.white, fontFace: "Calibri", wrap: true });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 8 — STRATEGIC ASSESSMENT
// ═══════════════════════════════════════════════════════════════════════════════
{
  slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 8);

  addSectionLabel(slide, "Strategic Assessment", 0.35, 0.35, 5);
  slide.addText("Risks & Opportunities — June 2026", { x: 0.35, y: 0.55, w: 9, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });

  addDivider(slide, 0.35, 0.92, 12.63);

  // Risks column
  addSectionLabel(slide, "⚠ Risks", 0.35, 1.0, 6.1);
  const risks = [
    { level: "HIGH", title: "Paid Channel Inefficiency", detail: "Paid Search + Social absorb $144K (50% of spend) at 5.5x efficiency and 30% win rates. Estimated annual drag $2–3M vs Partner/Referral alternatives at 5.8x+ efficiency.", action: "Reallocate $0.96M from Paid to Partner/Referral; quantify $2–3M annual drag vs high-efficiency channels.", impact: "$2–3M annual drag" },
    { level: "HIGH", title: "SMB Churn Concentration", detail: "78% of gross churn is SMB. G$R could deteriorate 30–50bps in H2, impacting ARR by ~$0.8M and pushing N$R below 100%. Targeted CSM intervention required before Q3 renewal cycle.", action: "Run SMB renewal cohort analysis before Q3; CSM intervention on at-risk accounts to protect G$R/N$R.", impact: "~$0.8M ARR / N$R <100%" },
    { level: "MEDIUM", title: "New Logo $325K Behind Plan", detail: "Deal timing slippage in 20+ seat segment. Close rates improving (Q2: 13%) but volume trailing. H2 new business revenue at risk if enterprise pipeline doesn't convert within cycle.", action: "Prioritize enterprise close plans; validate 20+ seat segment conversion within the H2 cycle.", impact: "$325K behind plan" },
    { level: "MEDIUM", title: "H2 Collections Moderation", detail: "March's $13.6M collections spike reflects annual billing concentration. H2 monthly collections expected at $6–8M — a 40% reduction from Q1 average. Cash model needs H2 update.", action: "Update H2 cash model for $6–8M monthly collections (~40% below Q1 avg).", impact: "H2 collections ~40% vs Q1" }
  ];
  risks.forEach((r, i) => {
    const ry = 1.22 + i * 1.35;
    slide.addShape(pptx.ShapeType.rect, { x: 0.35, y: ry, w: 6.1, h: 1.25, fill: { color: C.surface }, line: { color: C.red, width: 1 } });
    slide.addShape(pptx.ShapeType.rect, { x: 0.35, y: ry, w: 0.75, h: 0.22, fill: { color: C.deepRed } });
    slide.addText(r.level, { x: 0.38, y: ry + 0.02, w: 0.7, h: 0.18, fontSize: 7, bold: true, color: C.white, fontFace: "Calibri" });
    slide.addText(r.title, { x: 1.15, y: ry + 0.02, w: 5.2, h: 0.22, fontSize: 9.5, bold: true, color: C.red, fontFace: "Calibri" });
    slide.addText(r.detail, { x: 0.45, y: ry + 0.28, w: 5.9, h: 0.45, fontSize: 8, color: C.white, fontFace: "Calibri", wrap: true });
    slide.addText(`Action: ${r.action}`, { x: 0.45, y: ry + 0.75, w: 5.9, h: 0.22, fontSize: 7.5, color: C.muted, fontFace: "Calibri", wrap: true });
    if (r.impact) slide.addText(`Impact: ${r.impact}`, { x: 0.45, y: ry + 0.98, w: 5.9, h: 0.2, fontSize: 8, color: C.amber, fontFace: "Calibri", bold: true });
  });

  // Opportunities column
  addSectionLabel(slide, "✦ Opportunities", 6.85, 1.0, 6.1);
  const opps = [
    { level: "HIGH", title: "Partner + Referral Reallocation", detail: "Partner and Referral channels severely under-invested. Budget-neutral $0.96M reallocation from Paid could generate est. +$5M pipeline at 5x+ efficiency and 59–66% win rates.", action: "Approve budget-neutral $0.96M shift from Paid to Partner/Referral for est. +$5M pipeline.", upside: "+$5M pipeline / 5x+ efficiency" },
    { level: "HIGH", title: "Expansion ARR Momentum", detail: "Expansion outperformed budget 4 of 5 months at $869.1K vs $912.6K budget. CS-led enterprise expansion plays could add $0.5–1.0M ARR per quarter at near-zero incremental CAC.", action: "Fund CS-led enterprise expansion plays targeting $0.5–1.0M ARR/quarter.", upside: "$0.5–1.0M ARR/quarter" },
    { level: "MEDIUM", title: "Annual Contract Expansion", detail: "Annual billing penetration in mid-market adds est. $5–8M to YE 2026 cash. Include annual terms in all mid-market renewals and new business starting Q3. Revenue recognition neutral.", action: "Mandate annual terms on mid-market renewals/NB starting Q3 (est. +$5–8M YE cash).", upside: "$5–8M YE 2026 cash" },
    { level: "MEDIUM", title: "Operating Leverage Improvement", detail: "Revenue +5.0% MoM vs headcount +2.3% YoY. If maintained through H2, EBITDA margin improvement of 150–200bps is achievable without headcount reduction — purely through GTM efficiency gains.", action: "Hold opex/headcount discipline; capture 150–200bps EBITDA margin via GTM efficiency through H2.", upside: "150–200bps EBITDA margin" }
  ];
  opps.forEach((o, i) => {
    const oy = 1.22 + i * 1.35;
    slide.addShape(pptx.ShapeType.rect, { x: 6.85, y: oy, w: 6.1, h: 1.25, fill: { color: C.surface }, line: { color: C.green, width: 1 } });
    slide.addShape(pptx.ShapeType.rect, { x: 6.85, y: oy, w: 0.75, h: 0.22, fill: { color: C.darkGreen } });
    slide.addText(o.level, { x: 6.88, y: oy + 0.02, w: 0.7, h: 0.18, fontSize: 7, bold: true, color: C.white, fontFace: "Calibri" });
    slide.addText(o.title, { x: 7.65, y: oy + 0.02, w: 5.2, h: 0.22, fontSize: 9.5, bold: true, color: C.green, fontFace: "Calibri" });
    slide.addText(o.detail, { x: 6.95, y: oy + 0.28, w: 5.9, h: 0.45, fontSize: 8, color: C.white, fontFace: "Calibri", wrap: true });
    slide.addText(`Action: ${o.action}`, { x: 6.95, y: oy + 0.75, w: 5.9, h: 0.22, fontSize: 7.5, color: C.muted, fontFace: "Calibri", wrap: true });
    if (o.upside) slide.addText(`Upside: ${o.upside}`, { x: 6.95, y: oy + 0.98, w: 5.9, h: 0.2, fontSize: 8, color: C.cyan, fontFace: "Calibri", bold: true });
  });

  // Center divider
  slide.addShape(pptx.ShapeType.rect, { x: 6.62, y: 1.0, w: 0.03, h: 5.7, fill: { color: C.divider } });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 9 — FINANCIAL OUTLOOK
// ═══════════════════════════════════════════════════════════════════════════════
{
  slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 9);

  addSectionLabel(slide, "Financial Outlook", 0.35, 0.35, 5);
  slide.addText("Financial Outlook — FY 2026", { x: 0.35, y: 0.55, w: 9, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });

  // FY ARR trend line chart
  const months12 = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const arrActual = [76.31, 77.82, 79.51, 81.39, 83.45, 85.31, null, null, null, null, null, null];
  const arrOutlook = [76.31, 77.82, 79.51, 81.39, 83.45, 85.31, 86.29, 87.13, 87.83, 88.51, 89.20, 90.29];
  const arrBudget = [76.23, 77.64, 79.23, 81.00, 82.94, 84.89, 86.95, 88.91, 90.72, 92.57, 94.32, 96.10];

  slide.addChart(pptx.ChartType.line, [
    { name: "Actual ARR ($M)", labels: months12, values: arrActual.map(v => v === null ? undefined : v) },
    { name: "Outlook ARR ($M)", labels: months12, values: arrOutlook },
    { name: "Budget ARR ($M)", labels: months12, values: arrBudget }
  ], {
    x: 0.35, y: 0.95, w: 7.5, h: 3.5,
    showLegend: true, legendPos: "b", legendFontSize: 8, legendColor: C.muted,
    showTitle: false, showValue: false,
    chartColors: [C.cyan, C.amber, C.muted],
    lineDataSymbol: "circle", lineDataSymbolSize: 4,
    plotArea: { fill: { color: C.surface } },
    chartArea: { fill: { color: C.surface }, border: { color: C.surface } },
    valAxisMinVal: 74, valAxisMaxVal: 98,
    catAxisLabelColor: C.muted, catAxisLabelFontSize: 8,
    valAxisLabelColor: C.muted, valAxisLabelFontSize: 8
  });

  // FY outlook summary table
  addSectionLabel(slide, "FY 2026 Outlook Summary", 0.35, 4.52, 7.5);
  const fyRows = [
    ["Metric", "Outlook", "Budget"],
    ["Ending ARR (Dec EoY)", "$90.29M", "$96.10M"],
    ["FY Revenue", "$87.35M", "$91.24M"],
    ["FY Gross Margin %", "70.8%", "70.8%"],
    ["FY EBITDA", "$7.46M", "$7.79M"],
    ["Ending Cash (Dec EoY)", "$32.02M", "$23.85M"]
  ];
  const fyColW = [3.2, 2.0, 2.0];
  fyRows.forEach((row, ri) => {
    row.forEach((cell, ci) => {
      isHeader = ri === 0;
      xOff = fyColW.slice(0, ci).reduce((a, b) => a + b, 0);
      slide.addShape(pptx.ShapeType.rect, {
        x: 0.35 + xOff, y: 4.72 + ri * 0.28, w: fyColW[ci], h: 0.28,
        fill: { color: ri % 2 === 0 ? C.surface : C.surfaceAlt },
        line: { color: C.divider, width: 0.3 }
      });
      slide.addText(cell, {
        x: 0.35 + xOff + 0.05, y: 4.72 + ri * 0.28, w: fyColW[ci] - 0.05, h: 0.28,
        fontSize: 8.5, color: isHeader ? C.muted : C.white, fontFace: "Calibri",
        valign: "middle", bold: isHeader
      });
    });
  });

  // Right panel: H2 priorities + Key Takeaways
  const rx9 = 8.1;
  addSectionLabel(slide, "H2 Priorities", rx9, 0.95, 5.0);
  const h2 = [
    { title: "ARR & GTM", detail: "FY ARR outlook $90.29M vs $96.10M budget; pipeline 3.0x coverage supports H2 ramp. Prioritize enterprise conversion." },
    { title: "Profitability", detail: "YTD gross margin 70.8% on budget; EBITDA $3.87M ahead +$59.1K — sustain opex discipline through H2." },
    { title: "Cash & Runway", detail: "Cash $30.00M, -4.6% vs budget; FY outlook $32.02M — deploy strategically for GTM and product bets." },
    { title: "Workforce", detail: "EOY forecast 11 headcount; open reqs 0 — hiring plan approval required next cycle for H2 execution." }
  ];
  h2.forEach((p, i) => {
    slide.addShape(pptx.ShapeType.rect, { x: rx9, y: 1.15 + i * 1.1, w: 5.0, h: 1.0, fill: { color: C.surface }, line: { color: C.cyan, width: 0.5 } });
    slide.addText(p.title, { x: rx9 + 0.12, y: 1.18 + i * 1.1, w: 4.76, h: 0.25, fontSize: 9.5, bold: true, color: C.cyan, fontFace: "Calibri" });
    slide.addText(p.detail, { x: rx9 + 0.12, y: 1.44 + i * 1.1, w: 4.76, h: 0.65, fontSize: 8, color: C.white, fontFace: "Calibri", wrap: true });
  });

  addDivider(slide, rx9, 5.55, 5.0);
  addSectionLabel(slide, "Key Takeaways", rx9, 5.62, 5.0);
  const bullets9 = [
    "1. FY ARR outlook $90.29M, -6.0% vs $96.10M budget; H2 acceleration required. Pipeline coverage 3.0x supports ramp if conversion improves.",
    "2. FY revenue $87.35M vs $91.24M budget; -4.3% gap. Expansion momentum and new logo conversion critical for H2 close.",
    "3. Cash outlook $32.02M vs $23.85M budget — +34.3% upside enables strategic investment in GTM and product. H2 collections expected to moderate.",
    "4. EBITDA $7.46M FY outlook vs $7.79M budget; profitability trajectory intact. Operating leverage from revenue growth and opex discipline."
  ];
  bullets9.forEach((b, i) => {
    slide.addText(b, { x: rx9, y: 5.78 + i * 0.28, w: 5.0, h: 0.26, fontSize: 8, color: C.white, fontFace: "Calibri", wrap: true });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 10 — BOARD ACTIONS
// ═══════════════════════════════════════════════════════════════════════════════
{
  slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 10);

  addSectionLabel(slide, "Board Actions", 0.35, 0.35, 5);
  slide.addText("Board Actions — June 2026", { x: 0.35, y: 0.55, w: 9, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });
  addDivider(slide, 0.35, 0.92, 12.63);

  const actions = [
    { number: "01", type: "FOR APPROVAL", title: "Approve June 2026 financial close and P&L tie-out", owner: "CFO", due: "Board meeting" },
    { number: "02", type: "FOR APPROVAL", title: "Approve channel reallocation: $0.96M from Paid to Partner/Referral", owner: "CRO", due: "Next board cycle" },
    { number: "03", type: "FOR APPROVAL", title: "Approve updated FY ARR outlook ($90.29M) and H2 GTM plan", owner: "CEO / CRO", due: "Next board cycle" },
    { number: "04", type: "FOR DISCUSSION", title: "SMB churn mitigation and CSM intervention strategy for Q3 renewals", owner: "VP CS", due: "Operating review" }
  ];

  const positions = [
    { x: 0.35, y: 1.05 },
    { x: 6.84, y: 1.05 },
    { x: 0.35, y: 4.0 },
    { x: 6.84, y: 4.0 }
  ];

  actions.forEach((a, i) => {
    const pos = positions[i];
    cw = 6.14; const ch = 2.7;
    const isApproval = a.type === "FOR APPROVAL";
    slide.addShape(pptx.ShapeType.rect, { x: pos.x, y: pos.y, w: cw, h: ch, fill: { color: C.surface }, line: { color: isApproval ? C.cyan : C.amber, width: 1.5 } });
    slide.addText(a.number, { x: pos.x + 0.2, y: pos.y + 0.15, w: 1.2, h: 0.9, fontSize: 52, bold: true, color: C.cyan, fontFace: "Calibri", alpha: 40 });
    slide.addShape(pptx.ShapeType.rect, { x: pos.x + 1.5, y: pos.y + 0.18, w: 1.8, h: 0.26, fill: { color: isApproval ? C.cyan : C.amber } });
    slide.addText(a.type, { x: pos.x + 1.52, y: pos.y + 0.19, w: 1.76, h: 0.22, fontSize: 7.5, bold: true, color: C.bg, fontFace: "Calibri" });
    slide.addText(a.title, { x: pos.x + 0.2, y: pos.y + 0.55, w: cw - 0.4, h: 0.7, fontSize: 14, bold: true, color: C.white, fontFace: "Calibri", wrap: true });
    slide.addText(`Owner: ${a.owner}`, { x: pos.x + 0.2, y: pos.y + 1.35, w: cw - 0.4, h: 0.28, fontSize: 9.5, color: C.muted, fontFace: "Calibri" });
    slide.addText(`Due: ${a.due}`, { x: pos.x + 0.2, y: pos.y + 1.65, w: cw - 0.4, h: 0.28, fontSize: 9.5, color: C.muted, fontFace: "Calibri" });
    addDivider(slide, pos.x + 0.2, pos.y + 2.0, cw - 0.4);
    const statusText = isApproval ? "Requires board vote" : "Discussion item — no vote required";
    slide.addText(statusText, { x: pos.x + 0.2, y: pos.y + 2.1, w: cw - 0.4, h: 0.28, fontSize: 8.5, color: isApproval ? C.cyan : C.amber, fontFace: "Calibri" });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 11 — APPENDIX A: YTD CASH FLOW STATEMENT
// ═══════════════════════════════════════════════════════════════════════════════
{
  slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 11);

  addSectionLabel(slide, "Appendix A", 0.35, 0.35, 5);
  slide.addText("YTD Cash Flow Statement — Jan–Jun 2026", { x: 0.35, y: 0.55, w: 12, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });
  addDivider(slide, 0.35, 0.92, 12.63);

  const cfsRows = [
    { label: "Beginning Cash", actual: "$25.74M", budget: "$25.74M", variance: "+$0.00", bold: true },
    { label: "Net Income", actual: "$2.43M", budget: "$2.36M", variance: "+$71.0K" },
    { label: "Depreciation & Amortization", actual: "$591.8K", budget: "$621.3K", variance: "-$29.6K" },
    { label: "Stock-Based Compensation", actual: "$394.5K", budget: "$414.2K", variance: "-$19.7K" },
    { label: "Change in Accounts Receivable", actual: "$3.35M", budget: "$2.89M", variance: "+$453.2K" },
    { label: "Change in Deferred Revenue", actual: "$276.0K", budget: "$292.4K", variance: "-$16.4K" },
    { label: "Change in Accounts Payable", actual: "-$1.91M", budget: "-$3.50M", variance: "+$1.59M" },
    { label: "Change in Prepaids", actual: "-$90.0K", budget: "-$90.0K", variance: "+$0.00" },
    { label: "Cash from Operations (CFO)", actual: "$5.05M", budget: "$2.99M", variance: "+$2.05M", bold: true },
    { label: "Capex", actual: "-$789.0K", budget: "-$828.4K", variance: "+$39.4K" },
    { label: "Cash from Investing (CFI)", actual: "-$789.0K", budget: "-$828.4K", variance: "+$39.4K", bold: true },
    { label: "Cash from Financing (CFF)", actual: "$0.00", budget: "$0.00", variance: "n/a" },
    { label: "Net Change in Cash", actual: "$4.26M", budget: "$2.17M", variance: "+$2.09M", bold: true },
    { label: "Ending Cash", actual: "$30.00M", budget: "$27.91M", variance: "+$2.09M", bold: true }
  ];

  const cfsHdr = ["Line Item", "YTD Actual", "YTD Budget", "YTD Variance"];
  const cfsColW = [5.5, 2.2, 2.2, 2.2];
  const cfsX = 0.35; const cfsY = 1.05;

  [cfsHdr, ...cfsRows.map(r => [r.label, r.actual, r.budget, r.variance])].forEach((row, ri) => {
    row.forEach((cell, ci) => {
      isHeader = ri === 0;
      const rowData = ri > 0 ? cfsRows[ri - 1] : null;
      isBold = rowData && rowData.bold;
      isVar = ci === 3;
      fc = C.white;
      if (isHeader) fc = C.muted;
      else if (isVar && typeof cell === "string" && cell.startsWith("+")) fc = C.green;
      else if (isVar && typeof cell === "string" && cell.startsWith("-")) fc = C.red;
      xOff = cfsColW.slice(0, ci).reduce((a, b) => a + b, 0);
      slide.addShape(pptx.ShapeType.rect, {
        x: cfsX + xOff, y: cfsY + ri * 0.3, w: cfsColW[ci], h: 0.3,
        fill: { color: ri % 2 === 0 ? C.surface : C.surfaceAlt },
        line: { color: C.divider, width: 0.3 }
      });
      slide.addText(cell, {
        x: cfsX + xOff + 0.08, y: cfsY + ri * 0.3, w: cfsColW[ci] - 0.08, h: 0.3,
        fontSize: 8.5, color: fc, fontFace: "Calibri", valign: "middle",
        bold: isHeader || isBold
      });
    });
  });

  // Source note — MUST sit below Ending Cash row
  const cfsSourceY = cfsY + (cfsRows.length + 1) * 0.3 + 0.08;
  slide.addText("Source: build_ts_data.cfs  |  Period: Jan–Jun 2026  |  Currency: USD  |  Actual CFS for periods ≤ close_month (never Forecast)",
    {
      x: 0.35, y: cfsSourceY, w: 12.63, h: 0.22, fontSize: 7.5, color: C.muted, fontFace: "Calibri"
    });

  // Data notes
  slide.addShape(pptx.ShapeType.rect, { x: 0.35, y: cfsSourceY + 0.28, w: 12.63, h: 0.5, fill: { color: C.surfaceAlt }, line: { color: C.muted, width: 0.5 } });
  slide.addText("YTD Actual uses Actual CFS for periods ≤ close_month (2026-06). Budget column is Budget scenario only. Variance = Actual − Budget.",
    {
      x: 0.5, y: cfsSourceY + 0.32, w: 12.3, h: 0.42, fontSize: 8, color: C.muted, fontFace: "Calibri", wrap: true
    });
}

pptx.writeFile({ fileName: "C:/Users/mattj/AppData/Local/Temp/smpl-deck-g56pndfx/mda_deck_2026-06.pptx" });