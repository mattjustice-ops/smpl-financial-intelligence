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
  const slide = pptx.addSlide();
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
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 2);

  addSectionLabel(slide, "Executive Dashboard", 0.35, 0.35, 5);
  slide.addText("Executive Dashboard — June 2026", { x: 0.35, y: 0.55, w: 9, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });

  // Row 1: 5 KPI cards
  const cards = [
    { label: "Ending ARR", value: "$85.31M", sub: "vs bud $84.89M  +0.5%" },
    { label: "Revenue (CM)", value: "$2.20M", sub: "vs bud $2.32M  -4.8%", vc: C.amber },
    { label: "Ending Cash", value: "$48.43M", sub: "vs bud $31.46M  +54.0%" },
    { label: "Gross Margin %", value: "70.0%", sub: "vs bud 70.0%  on target" },
    { label: "EBITDA (CM)", value: "$661.5K", sub: "vs bud $647.5K  +2.2%" }
  ];
  const cw = 2.45; const ch = 1.0; const cy = 0.95;
  cards.forEach((c, i) => {
    kpiCard(slide, 0.35 + i * (cw + 0.07), cy, cw, ch, c.label, c.value, c.sub, c.vc || C.cyan);
  });

  // No KPI sparklines / mini-charts under Ending ARR / Revenue / Ending Cash —
  // they crowd the cards and add no board value.

  addDivider(slide, 0.35, 2.10, 12.63);

  // Period matrix table
  const tblX = 0.35; const tblY = 2.20; const tblW = 7.2;
  addSectionLabel(slide, "Period Matrix", tblX, tblY, 4);

  const pmRows = [
    ["Metric", "CM Actual", "CM Budget", "CM Variance", "YTD Actual", "YTD Budget", "YTD Variance"],
    ["Ending ARR", "$85.31M", "$84.89M", "+$413.1K", "$85.31M", "$84.89M", "+$413.1K"],
    ["Revenue", "$2.20M", "$2.32M", "-$110.2K", "$11.51M", "$12.09M", "-$575.7K"],
    ["EBITDA", "$661.5K", "$647.5K", "+$14.0K", "$3.87M", "$3.81M", "+$59.1K"],
    ["Gross Margin %", "70.0%", "70.0%", "—", "70.8%", "70.8%", "—"],
    ["Ending Cash", "$48.43M", "$31.46M", "+$16.98M", "$48.43M", "$31.46M", "+$16.98M"],
    ["Pipeline Created", "$5.40M", "$5.31M", "+$92.8K", "$5.40M", "$26.91M", "-$21.51M"]
  ];

  const colW = [1.6, 0.82, 0.82, 0.82, 0.82, 0.82, 0.82];
  const rowH = 0.28;
  pmRows.forEach((row, ri) => {
    row.forEach((cell, ci) => {
      const isHeader = ri === 0;
      const isVar = ci === 3 || ci === 6;
      let fc = C.white;
      if (isHeader) fc = C.muted;
      else if (isVar && cell.startsWith("+")) fc = C.green;
      else if (isVar && cell.startsWith("-")) fc = C.red;
      const xOff = colW.slice(0, ci).reduce((a, b) => a + b, 0);
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
    "1. ARR reached $85.31M, +$413.1K vs budget; MoM growth +2.2% from $83.44M in May.",
    "2. Revenue $2.20M CM, -4.8% vs budget; YTD $11.51M tracks -4.8% behind $12.09M budget.",
    "3. EBITDA $661.5K CM beat budget by +$14.0K; YTD $3.87M ahead +$59.1K.",
    "4. Cash $48.43M, +54.0% vs budget $31.46M; strong liquidity headroom of $38.43M above floor.",
    "5. FY ARR outlook $90.29M vs $96.10M budget; pipeline coverage 3.0x supports H2 ramp."
  ];
  bullets2.forEach((b, i) => {
    slide.addText(b, { x: ktX + 0.15, y: ktY + 0.35 + i * 0.75, w: 4.93, h: 0.65, fontSize: 9, color: C.white, fontFace: "Calibri", valign: "top", wrap: true });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 3 — ARR ANALYSIS (waterfall with addShape ONLY)
// ═══════════════════════════════════════════════════════════════════════════════
{
  const slide = pptx.addSlide();
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
    const yPct = 1 - (tick - yMin) / (yMax - yMin);
    const yPos = chartAreaY + yPct * chartAreaH;
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
    const labelY = bar.label_position === "above" ? bar.y - 0.22 : bar.y + bar.h + 0.04;
    const lc = bar.color === "991b1b" ? C.red : (bar.color === "166534" ? C.green : C.cyan);
    slide.addText(bar.label, { x: bar.x - 0.05, y: labelY, w: bar.w + 0.1, h: 0.2, fontSize: 7.5, color: lc, fontFace: "Calibri", align: "center", bold: true });
    // Category labels on shared x-axis baseline (not under each bar).
    slide.addText(bar.category, { x: bar.x - 0.05, y: axisY, w: bar.w + 0.1, h: 0.28, fontSize: 7, color: C.muted, fontFace: "Calibri", align: "center", wrap: true });
  });

  addDivider(slide, 7.1, 1.05, 0.03);
  slide.addShape(pptx.ShapeType.rect, { x: 7.05, y: 1.05, w: 0.03, h: 4.2, fill: { color: C.divider } });

  // Right panel — KPIs + bridge only (KT moves under waterfall for commentary space)
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
      const isHeader = ri === 0;
      const isVar = ci === 3;
      let fc = C.white;
      if (isHeader) fc = C.muted;
      else if (isVar && cell.startsWith("+")) fc = C.green;
      else if (isVar && cell.startsWith("-")) fc = C.red;
      const xOff = bColW.slice(0, ci).reduce((a, b) => a + b, 0);
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

  // Key Takeaways — full width under waterfall for more commentary space
  addDivider(slide, 0.35, 5.48, 12.63);
  addSectionLabel(slide, "Key Takeaways", 0.35, 5.55, 12.63);
  const bullets3 = [
    "1. Ending ARR $85.31M beat budget by +$413.1K; MoM growth +2.2% from $83.44M in May 2026.",
    "2. New Business $1.68M slightly below $1.77M budget; expansion $869.1K vs $912.6K budget.",
    "3. Churn $520.2K and contraction $313.7K both below budget — retention tracking favorably.",
    "4. FY ARR outlook $90.29M vs $96.10M budget; H2 ramp requires pipeline acceleration."
  ];
  bullets3.forEach((b, i) => {
    slide.addText(b, { x: 0.35, y: 5.75 + i * 0.28, w: 12.63, h: 0.26, fontSize: 9, color: C.white, fontFace: "Calibri", wrap: true });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 4 — P&L REVIEW
// ═══════════════════════════════════════════════════════════════════════════════
{
  const slide = pptx.addSlide();
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
      const isHeader = ri === 0;
      const isVar = ci === 3 || ci === 6;
      const isBold = ["Gross Profit", "EBITDA", "Net Income"].includes(row[0]);
      let fc = C.white;
      if (isHeader) fc = C.muted;
      else if (isVar && cell.startsWith("+")) fc = C.green;
      else if (isVar && cell.startsWith("-")) fc = C.red;
      const xOff = plColW.slice(0, ci).reduce((a, b) => a + b, 0);
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
    "1. Revenue $7.35M CM, -4.8% vs $7.72M budget; YTD $39.45M trails $41.42M by -$1.97M.",
    "2. Gross margin held at 70.0% CM and 70.8% YTD — in line with budget on both horizons.",
    "3. EBITDA $661.5K beat budget by +$14.0K; YTD $3.87M ahead +$59.1K reflecting cost discipline.",
    "4. S&M $2.50M and R&D $1.18M both -5.7% vs budget; opex leverage supporting margin.",
    "5. Net income $409.0K CM, +4.0% vs budget; YTD $2.43M ahead +$71.0K — profitable trajectory."
  ];
  bullets4.forEach((b, i) => {
    slide.addText(b, { x: ktX4 + 0.15, y: ktY4 + 0.35 + i * 0.82, w: 4.7, h: 0.72, fontSize: 9, color: C.white, fontFace: "Calibri", valign: "top", wrap: true });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 5 — CASH & LIQUIDITY
// ═══════════════════════════════════════════════════════════════════════════════
{
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 5);

  addSectionLabel(slide, "Cash & Liquidity", 0.35, 0.35, 5);
  slide.addText("Cash & Liquidity — June 2026", { x: 0.35, y: 0.55, w: 9, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });

  // Left: Cash bridge
  addSectionLabel(slide, "Monthly Cash Bridge", 0.35, 0.98, 5);
  const bridgeItems = [
    { label: "Beginning Cash", actual: "$48.02M", budget: "$29.60M", bold: true },
    { label: "Collections", actual: "$6.81M", budget: "$8.91M" },
    { label: "Payroll", actual: "$2.47M", budget: "$4.00M" },
    { label: "Vendor Payments", actual: "$3.66M", budget: "$1.40M" },
    { label: "Commissions", actual: "$199.9K", budget: "$370.8K" },
    { label: "Capex", actual: "$220.0K", budget: "$220.0K" },
    { label: "CFO", actual: "—", budget: "—" },
    { label: "Ending Cash", actual: "$50.26M", budget: "$48.17M", bold: true }
  ];
  const bHdr = ["Line Item", "Actual", "Budget"];
  const bCW = [2.0, 1.0, 1.0];
  [bHdr, ...bridgeItems.map(r => [r.label, r.actual, r.budget])].forEach((row, ri) => {
    row.forEach((cell, ci) => {
      const isHeader = ri === 0;
      const isBold = ri > 0 && bridgeItems[ri - 1].bold;
      const xOff = bCW.slice(0, ci).reduce((a, b) => a + b, 0);
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
  // Bridge: header @ 1.18 + 9 rows × 0.3 = last row ends ~3.88 → summary starts ≥ 4.05.
  const ytdSumY = 4.05;
  addSectionLabel(slide, "YTD Cash Summary", 0.35, ytdSumY, 4.2);
  slide.addShape(pptx.ShapeType.rect, { x: 0.35, y: ytdSumY + 0.20, w: 4.2, h: 1.35, fill: { color: C.surface }, line: { color: C.divider, width: 0.5 } });
  slide.addText("YTD Collections: $58.82M", { x: 0.45, y: ytdSumY + 0.28, w: 4.0, h: 0.28, fontSize: 10, color: C.white, fontFace: "Calibri", bold: true });
  slide.addText("YTD Ending Cash: $50.26M", { x: 0.45, y: ytdSumY + 0.58, w: 4.0, h: 0.28, fontSize: 10, color: C.cyan, fontFace: "Calibri", bold: true });
  slide.addText("YTD Ending Cash Budget: $31.46M", { x: 0.45, y: ytdSumY + 0.88, w: 4.0, h: 0.28, fontSize: 9, color: C.muted, fontFace: "Calibri" });
  slide.addText("Primary liquidity read for the close — update H2 collections model.", {
    x: 0.45, y: ytdSumY + 1.18, w: 4.0, h: 0.28, fontSize: 8, color: C.muted, fontFace: "Calibri", wrap: true
  });

  // Right: 2x2 KPI grid + Key Takeaways (box ends above footer)
  const rx5 = 4.85;
  addSectionLabel(slide, "Cash KPIs", rx5, 0.98, 8.1);
  const cashKpis = [
    { label: "Ending Cash (CM)", value: "$50.26M", sub: "vs bud $48.17M  +4.3%" },
    { label: "YTD Collections", value: "$58.82M", sub: "Jan–Jun actual" },
    { label: "FY Cash Outlook", value: "$49.92M", sub: "vs bud $23.85M  +109.3%" },
    { label: "YTD Ending Cash", value: "$50.26M", sub: "vs bud $48.17M" }
  ];
  const ckw = 4.0;
  cashKpis.forEach((k, i) => {
    kpiCard(slide, rx5 + (i % 2) * (ckw + 0.12), 1.18 + Math.floor(i / 2) * 1.08, ckw, 0.98, k.label, k.value, k.sub, C.cyan);
  });

  addDivider(slide, rx5, 3.38, 8.1);
  addSectionLabel(slide, "Key Takeaways", rx5, 3.45, 8.1);
  slide.addShape(pptx.ShapeType.rect, { x: rx5, y: 3.65, w: 8.1, h: 2.95, fill: { color: C.surface }, line: { color: C.divider, width: 0.5 } });
  const bullets5 = [
    "1. Ending cash $50.26M, +4.3% vs $48.17M budget; MoM bridge shows collections vs outflows.",
    "2. YTD collections $58.82M; YTD ending cash $50.26M is the primary liquidity summary.",
    "3. Collections $6.81M CM vs $8.91M budget; H2 model should assume moderation vs Q1 spike.",
    "4. FY cash outlook $49.92M vs $23.85M budget — +109.3% upside from disciplined spend.",
    "5. Maintain $10.00M floor; deploy excess only against board-approved investments."
  ];
  bullets5.forEach((b, i) => {
    slide.addText(b, { x: rx5 + 0.15, y: 3.72 + i * 0.54, w: 7.8, h: 0.5, fontSize: 8.5, color: C.white, fontFace: "Calibri", valign: "top", wrap: true });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 6 — GTM PERFORMANCE
// ═══════════════════════════════════════════════════════════════════════════════
{
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 6);

  addSectionLabel(slide, "GTM & Pipeline Performance", 0.35, 0.35, 5);
  slide.addText("GTM & Pipeline Performance — June 2026", { x: 0.35, y: 0.55, w: 9, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });
  // Funnel section label sits BELOW the title (never overlap "June 2026")
  addSectionLabel(slide, "Marketing Funnel", 0.35, 0.92, 3.8);

  // Top 4 KPI cards
  const gtmCards = [
    { label: "Total Pipeline", value: "$5.40M", sub: "CM created  vs bud $5.31M" },
    { label: "Total MQLs", value: "119", sub: "CM  best: Organic Search" },
    { label: "Closed Won", value: "$1.80M", sub: "CM ARR closed" },
    { label: "Blended Efficiency", value: "60.7x", sub: "pipeline per $ spend" }
  ];
  const gcw = 3.1;
  gtmCards.forEach((c, i) => {
    kpiCard(slide, 0.35 + i * (gcw + 0.07), 1.12, gcw, 0.90, c.label, c.value, c.sub, C.cyan);
  });

  addDivider(slide, 0.35, 2.0, 12.63);

  // Channel table
  addSectionLabel(slide, "Channel Performance", 0.35, 2.08, 8);
  const gtmHdr = ["Channel", "Spend (Act)", "Spend (Bud)", "Pipeline (Act)", "MQLs", "Efficiency", "Win Rate"];
  const gtmData = [
    ["Paid Social", "$12K", "$2K", "$524K", "28", "44.5x", "10.6%"],
    ["Paid Search", "$8K", "$8K", "$508K", "19", "63.7x", "3.3%"],
    ["Content Syndication", "$7K", "$9K", "$310K", "17", "43.5x", "9.1%"],
    ["Organic Search", "$5K", "$7K", "$443K", "13", "81.2x", "23.8%"],
    ["Outbound", "$5K", "$8K", "$484K", "12", "96.1x", "8.1%"]
  ];
  const gColW = [1.8, 1.0, 1.0, 1.1, 0.7, 1.0, 0.85];
  [gtmHdr, ...gtmData].forEach((row, ri) => {
    row.forEach((cell, ci) => {
      const isHeader = ri === 0;
      const xOff = gColW.slice(0, ci).reduce((a, b) => a + b, 0);
      let fc = C.white;
      if (isHeader) fc = C.muted;
      else if (ci === 5) {
        const val = parseFloat(cell);
        fc = val >= 80 ? C.green : val >= 60 ? C.cyan : C.amber;
      }
      slide.addShape(pptx.ShapeType.rect, {
        x: 0.35 + xOff, y: 2.28 + ri * 0.28, w: gColW[ci], h: 0.28,
        fill: { color: ri % 2 === 0 ? C.surface : C.surfaceAlt },
        line: { color: C.divider, width: 0.3 }
      });
      slide.addText(cell, {
        x: 0.35 + xOff + 0.05, y: 2.28 + ri * 0.28, w: gColW[ci] - 0.05, h: 0.28,
        fontSize: 8.5, color: fc, fontFace: "Calibri", valign: "middle", bold: isHeader
      });
    });
  });

  addDivider(slide, 0.35, 3.75, 12.63);

  // Efficiency bar chart
  addSectionLabel(slide, "Channel Efficiency (Pipeline / Spend)", 0.35, 3.82, 8);
  const channels = [
    { name: "Content Syndication", eff: 43.5 },
    { name: "Paid Social", eff: 44.5 },
    { name: "Paid Search", eff: 63.7 },
    { name: "Organic Search", eff: 81.2 },
    { name: "Outbound", eff: 96.1 }
  ];
  slide.addChart(pptx.ChartType.bar, [{
    name: "Efficiency (x)",
    labels: channels.map(c => c.name),
    values: channels.map(c => c.eff)
  }], {
    x: 0.35, y: 4.0, w: 7.5, h: 2.65,
    barDir: "bar",
    showLegend: false, showTitle: false, showValue: true,
    dataLabelFontSize: 8, dataLabelColor: C.white,
    chartColors: [C.amber, C.amber, C.cyan, C.green, C.green],
    plotArea: { fill: { color: C.surface } },
    chartArea: { fill: { color: C.surface }, border: { color: C.surface } },
    valAxisMinVal: 0, valAxisMaxVal: 110,
    catAxisLabelColor: C.muted, catAxisLabelFontSize: 8,
    valAxisLabelColor: C.muted, valAxisLabelFontSize: 8
  });

  // Key Takeaways right
  const ktX6 = 8.1;
  addSectionLabel(slide, "Key Takeaways", ktX6, 3.82, 5.0);
  slide.addShape(pptx.ShapeType.rect, { x: ktX6, y: 4.0, w: 5.0, h: 2.65, fill: { color: C.surface }, line: { color: C.divider, width: 0.5 } });
  const bullets6 = [
    "1. Outbound leads efficiency at 96.1x; Organic Search 81.2x with best win rate 23.8%.",
    "2. Paid Social spend $12K vs $2K budget — overspend warrants reallocation review.",
    "3. Total pipeline $5.40M vs $5.31M budget; YTD pipeline -79.9% vs $26.91M budget.",
    "4. MQL volume 119 CM; pipeline coverage 3.0x supports near-term ARR targets.",
    "5. Content Syndication lowest efficiency 43.5x — consider budget shift to Outbound."
  ];
  bullets6.forEach((b, i) => {
    slide.addText(b, { x: ktX6 + 0.15, y: 4.12 + i * 0.48, w: 4.7, h: 0.42, fontSize: 8.5, color: C.white, fontFace: "Calibri", valign: "top", wrap: true });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 7 — PIPELINE WATERFALL (additive Begin → End)
// ═══════════════════════════════════════════════════════════════════════════════
{
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 7);

  addSectionLabel(slide, "Pipeline Waterfall", 0.35, 0.35, 5);
  slide.addText("Pipeline Waterfall — June 2026", { x: 0.35, y: 0.55, w: 9, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });
  slide.addText("Begin Pipeline → flows → Ending Pipeline ($M ARR)", { x: 0.35, y: 0.88, w: 7, h: 0.2, fontSize: 9, color: C.muted, fontFace: "Calibri" });

  // Additive shape_bars: Begin + Created − Closed Won − Closed Lost − Slipped → End
  const pipeBars = [
    { x: 0.55, y: 1.55, w: 0.85, h: 3.05, color: "00d4aa", label: "$180.77M", label_position: "above", category: "Begin Pipeline" },
    { x: 1.55, y: 1.55, w: 0.85, h: 0.18, color: "166534", label: "+$5.40M", label_position: "above", category: "Created" },
    { x: 2.55, y: 1.67, w: 0.85, h: 0.06, color: "991b1b", label: "-$1.80M", label_position: "below", category: "Closed Won" },
    { x: 3.55, y: 1.55, w: 0.85, h: 0.28, color: "991b1b", label: "-$7.91M", label_position: "below", category: "Closed Lost" },
    { x: 4.55, y: 1.55, w: 0.85, h: 0.35, color: "991b1b", label: "-$9.87M", label_position: "below", category: "Slipped" },
    { x: 5.55, y: 1.78, w: 0.85, h: 2.82, color: "00d4aa", label: "$166.59M", label_position: "above", category: "End Pipeline" }
  ];
  const pipeAxisY = 4.75;
  pipeBars.forEach(bar => {
    slide.addShape(pptx.ShapeType.rect, {
      x: bar.x, y: bar.y, w: bar.w, h: bar.h,
      fill: { color: bar.color },
      line: { color: bar.color, width: 0.5 }
    });
    const labelY = bar.label_position === "above" ? bar.y - 0.22 : bar.y + bar.h + 0.02;
    const lc = bar.color === "991b1b" ? C.red : (bar.color === "166534" ? C.green : C.cyan);
    slide.addText(bar.label, { x: bar.x - 0.05, y: labelY, w: bar.w + 0.1, h: 0.2, fontSize: 7.5, color: lc, fontFace: "Calibri", align: "center", bold: true });
    slide.addText(bar.category, { x: bar.x - 0.08, y: pipeAxisY, w: bar.w + 0.16, h: 0.35, fontSize: 7, color: C.muted, fontFace: "Calibri", align: "center", wrap: true });
  });

  // Right KPIs + bridge
  const rx7 = 7.25;
  addSectionLabel(slide, "Pipeline KPIs", rx7, 1.05, 5.7);
  const pipeKpis = [
    { label: "Ending Pipeline", value: "$166.59M", sub: "vs beginning $180.77M" },
    { label: "Pipeline Created", value: "$5.40M", sub: "vs bud $5.31M  +$92.8K" },
    { label: "Closed Lost", value: "$7.91M", sub: "vs bud — review losses" },
    { label: "Slipped Pipeline", value: "$9.87M", sub: "vs bud $3.18M  -$6.69M" }
  ];
  pipeKpis.forEach((k, i) => {
    kpiCard(slide, rx7 + (i % 2) * 2.95, 1.28 + Math.floor(i / 2) * 1.0, 2.8, 0.92, k.label, k.value, k.sub, C.cyan);
  });

  addSectionLabel(slide, "Pipeline Bridge", rx7, 3.4, 5.7);
  const pipeBridge = [
    ["Component", "Actual", "Budget", "Variance"],
    ["Beginning Pipeline", "$180.77M", "—", "—"],
    ["Created", "$5.40M", "$5.31M", "+$92.8K"],
    ["Closed Won", "-$1.80M", "-$1.77M", "—"],
    ["Closed Lost", "-$7.91M", "-$2.22M", "—"],
    ["Slipped", "-$9.87M", "-$3.18M", "-$6.69M"],
    ["Ending Pipeline", "$166.59M", "—", "—"]
  ];
  const pbW = [1.55, 1.0, 1.0, 1.0];
  pipeBridge.forEach((row, ri) => {
    row.forEach((cell, ci) => {
      const isHeader = ri === 0;
      let fc = isHeader ? C.muted : C.white;
      if (!isHeader && ci === 3 && cell.startsWith("+")) fc = C.green;
      if (!isHeader && ci === 3 && cell.startsWith("-")) fc = C.red;
      const xOff = pbW.slice(0, ci).reduce((a, b) => a + b, 0);
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
    "1. Beginning pipeline $180.77M → ending $166.59M; additive bridge includes created, won, lost, slipped.",
    "2. Created $5.40M; closed won $1.80M; closed lost $7.91M — run a structured loss review.",
    "3. Slipped pipeline $9.87M vs $3.18M budget; re-stage with owners before H2 forecast lock.",
    "4. Pipeline coverage 3.0x supports H2 ramp; prioritize enterprise conversion velocity."
  ];
  bullets7.forEach((b, i) => {
    slide.addText(b, { x: 0.35, y: 5.48 + i * 0.32, w: 12.63, h: 0.3, fontSize: 9, color: C.white, fontFace: "Calibri", wrap: true });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 8 — STRATEGIC ASSESSMENT
// ═══════════════════════════════════════════════════════════════════════════════
{
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 8);

  addSectionLabel(slide, "Strategic Assessment", 0.35, 0.35, 5);
  slide.addText("Risks & Opportunities — June 2026", { x: 0.35, y: 0.55, w: 9, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });

  addDivider(slide, 0.35, 0.92, 12.63);

  // Risks column
  addSectionLabel(slide, "⚠ Risks", 0.35, 1.0, 6.1);
  const risks = [
    { level: "MEDIUM", title: "Deferred Pipeline", detail: "Slipped pipeline $9.87M requires next-quarter coverage review.", action: "Re-stage opportunities with validated next steps and owners.", impact: "$9.87M" },
    { level: "MEDIUM", title: "Revenue vs Budget", detail: "Revenue trailed budget in close month. Validate expansion timing and churn pockets before board distribution.", action: "Review expansion timing and churn pockets.", impact: "" },
    { level: "MEDIUM", title: "Close Validation", detail: "Validation status: FAIL. Confirm tie-outs before distribution.", action: "Finance to certify waterfall and GL reconciliations.", impact: "" },
    { level: "MEDIUM", title: "Data Gaps", detail: "No Forecast ARR waterfall rows for 2026-06; no Forecast revenue line for 2026-06.", action: "Reload missing CSV sources and re-run validation.", impact: "" }
  ];
  risks.forEach((r, i) => {
    const ry = 1.22 + i * 1.35;
    slide.addShape(pptx.ShapeType.rect, { x: 0.35, y: ry, w: 6.1, h: 1.25, fill: { color: C.surface }, line: { color: C.red, width: 1 } });
    slide.addShape(pptx.ShapeType.rect, { x: 0.35, y: ry, w: 0.75, h: 0.22, fill: { color: C.deepRed } });
    slide.addText(r.level, { x: 0.38, y: ry + 0.02, w: 0.7, h: 0.18, fontSize: 7, bold: true, color: C.white, fontFace: "Calibri" });
    slide.addText(r.title, { x: 1.15, y: ry + 0.02, w: 5.2, h: 0.22, fontSize: 9.5, bold: true, color: C.red, fontFace: "Calibri" });
    slide.addText(r.detail, { x: 0.45, y: ry + 0.28, w: 5.9, h: 0.45, fontSize: 8.5, color: C.white, fontFace: "Calibri", wrap: true });
    slide.addText(`Action: ${r.action}`, { x: 0.45, y: ry + 0.75, w: 5.9, h: 0.22, fontSize: 8, color: C.muted, fontFace: "Calibri", wrap: true });
    if (r.impact) slide.addText(`Impact: ${r.impact}`, { x: 0.45, y: ry + 0.98, w: 5.9, h: 0.2, fontSize: 8, color: C.amber, fontFace: "Calibri", bold: true });
  });

  // Opportunities column
  addSectionLabel(slide, "✦ Opportunities", 6.85, 1.0, 6.1);
  const opps = [
    { level: "MEDIUM", title: "Liquidity Headroom", detail: "Cash $50.26M provides runway for strategic investments.", action: "Prioritize high-ROI GTM and product bets with board approval.", upside: "$40.26M" },
    { level: "MEDIUM", title: "Cash Forecast Upside", detail: "FY cash outlook $49.92M vs $23.85M budget — +109.3% above plan.", action: "Confirm ending cash ties to balance sheet; deploy excess strategically.", upside: "+$26.07M" },
    { level: "MEDIUM", title: "Channel Reallocation", detail: "Outbound 96.1x and Organic Search 81.2x efficiency — shift budget from underperformers.", action: "Reallocate Paid Social overspend to Outbound and Organic Search.", upside: "" },
    { level: "MEDIUM", title: "ARR Retention", detail: "Churn $520.2K and contraction $313.7K both below budget — retention outperforming.", action: "Invest in expansion motion to accelerate N$R above 100%.", upside: "" }
  ];
  opps.forEach((o, i) => {
    const oy = 1.22 + i * 1.35;
    slide.addShape(pptx.ShapeType.rect, { x: 6.85, y: oy, w: 6.1, h: 1.25, fill: { color: C.surface }, line: { color: C.green, width: 1 } });
    slide.addShape(pptx.ShapeType.rect, { x: 6.85, y: oy, w: 0.75, h: 0.22, fill: { color: C.darkGreen } });
    slide.addText(o.level, { x: 6.88, y: oy + 0.02, w: 0.7, h: 0.18, fontSize: 7, bold: true, color: C.white, fontFace: "Calibri" });
    slide.addText(o.title, { x: 7.65, y: oy + 0.02, w: 5.2, h: 0.22, fontSize: 9.5, bold: true, color: C.green, fontFace: "Calibri" });
    slide.addText(o.detail, { x: 6.95, y: oy + 0.28, w: 5.9, h: 0.45, fontSize: 8.5, color: C.white, fontFace: "Calibri", wrap: true });
    slide.addText(`Action: ${o.action}`, { x: 6.95, y: oy + 0.75, w: 5.9, h: 0.22, fontSize: 8, color: C.muted, fontFace: "Calibri", wrap: true });
    if (o.upside) slide.addText(`Upside: ${o.upside}`, { x: 6.95, y: oy + 0.98, w: 5.9, h: 0.2, fontSize: 8, color: C.cyan, fontFace: "Calibri", bold: true });
  });

  // Center divider
  slide.addShape(pptx.ShapeType.rect, { x: 6.62, y: 1.0, w: 0.03, h: 5.7, fill: { color: C.divider } });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 9 — FINANCIAL OUTLOOK
// ═══════════════════════════════════════════════════════════════════════════════
{
  const slide = pptx.addSlide();
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
    ["FY Revenue", "$25.88M", "$26.54M"],
    ["FY Gross Margin %", "70.4%", "70.9%"],
    ["FY EBITDA", "$7.46M", "$7.79M"],
    ["Ending Cash (Dec EoY)", "$49.92M", "$23.85M"]
  ];
  const fyColW = [3.2, 2.0, 2.0];
  fyRows.forEach((row, ri) => {
    row.forEach((cell, ci) => {
      const isHeader = ri === 0;
      const xOff = fyColW.slice(0, ci).reduce((a, b) => a + b, 0);
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
    { title: "ARR & GTM", detail: "FY ARR outlook $90.29M vs $96.10M budget; pipeline 3.0x coverage supports H2 ramp." },
    { title: "Profitability", detail: "YTD gross margin 70.8% on budget; EBITDA $3.87M ahead +$59.1K — sustain discipline." },
    { title: "Cash & Runway", detail: "Cash $48.43M, +54.0% vs budget; FY outlook $49.92M — deploy strategically." },
    { title: "Workforce", detail: "EOY forecast 16 headcount; open reqs 0 — hiring plan approval required next cycle." }
  ];
  h2.forEach((p, i) => {
    slide.addShape(pptx.ShapeType.rect, { x: rx9, y: 1.15 + i * 1.1, w: 5.0, h: 1.0, fill: { color: C.surface }, line: { color: C.cyan, width: 0.5 } });
    slide.addText(p.title, { x: rx9 + 0.12, y: 1.18 + i * 1.1, w: 4.76, h: 0.25, fontSize: 9.5, bold: true, color: C.cyan, fontFace: "Calibri" });
    slide.addText(p.detail, { x: rx9 + 0.12, y: 1.44 + i * 1.1, w: 4.76, h: 0.65, fontSize: 8.5, color: C.white, fontFace: "Calibri", wrap: true });
  });

  addDivider(slide, rx9, 5.55, 5.0);
  addSectionLabel(slide, "Key Takeaways", rx9, 5.62, 5.0);
  const bullets9 = [
    "1. FY ARR outlook $90.29M, -6.0% vs $96.10M budget; H2 acceleration required to close gap.",
    "2. FY revenue $25.88M vs $26.54M budget; -2.5% gap manageable with pipeline conversion.",
    "3. Cash outlook $49.92M vs $23.85M budget — +109.3% upside enables strategic investment.",
    "4. EBITDA $7.46M FY outlook vs $7.79M budget; profitability trajectory intact."
  ];
  bullets9.forEach((b, i) => {
    slide.addText(b, { x: rx9, y: 5.78 + i * 0.25, w: 5.0, h: 0.23, fontSize: 8, color: C.white, fontFace: "Calibri", wrap: true });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 10 — BOARD ACTIONS
// ═══════════════════════════════════════════════════════════════════════════════
{
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 10);

  addSectionLabel(slide, "Board Actions", 0.35, 0.35, 5);
  slide.addText("Board Actions — June 2026", { x: 0.35, y: 0.55, w: 9, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });
  addDivider(slide, 0.35, 0.92, 12.63);

  const actions = [
    { number: "01", type: "FOR APPROVAL", title: "Approve June 2026 financial close package", owner: "CFO", due: "Board meeting" },
    { number: "02", type: "FOR APPROVAL", title: "Approve updated FY ARR outlook and GTM plan", owner: "CEO / CRO", due: "Next board cycle" },
    { number: "03", type: "FOR APPROVAL", title: "Approve headcount and hiring plan adjustments", owner: "CFO / CHRO", due: "Next board cycle" },
    { number: "04", type: "FOR DISCUSSION", title: "Pipeline coverage and channel efficiency reallocation", owner: "CRO", due: "Operating review" }
  ];

  const positions = [
    { x: 0.35, y: 1.05 },
    { x: 6.84, y: 1.05 },
    { x: 0.35, y: 4.0 },
    { x: 6.84, y: 4.0 }
  ];

  actions.forEach((a, i) => {
    const pos = positions[i];
    const cw = 6.14; const ch = 2.7;
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
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addFooter(slide, 11);

  addSectionLabel(slide, "Appendix A", 0.35, 0.35, 5);
  slide.addText("YTD Cash Flow Statement — Jan–Jun 2026", { x: 0.35, y: 0.55, w: 12, h: 0.35, fontSize: 22, bold: true, color: C.white, fontFace: "Calibri" });
  addDivider(slide, 0.35, 0.92, 12.63);

  const cfsRows = [
    { label: "Beginning Cash", actual: "$45.30M", budget: "$46.77M", variance: "-$1.47M", bold: true },
    { label: "Net Income", actual: "$2.43M", budget: "$2.36M", variance: "+$70.0K" },
    { label: "Depreciation & Amortization", actual: "$591.8K", budget: "$621.3K", variance: "-$29.5K" },
    { label: "Stock-Based Compensation", actual: "n/a", budget: "n/a", variance: "—" },
    { label: "Change in Accounts Receivable", actual: "$2.19M", budget: "-$1.88M", variance: "+$4.07M" },
    { label: "Change in Deferred Revenue", actual: "$232.0K", budget: "$249.2K", variance: "-$17.2K" },
    { label: "Change in Accounts Payable", actual: "$373.5K", budget: "$917.7K", variance: "-$544.2K" },
    { label: "Change in Prepaids", actual: "$75.0K", budget: "$75.0K", variance: "$0.0K" },
    { label: "Cash from Operations (CFO)", actual: "$5.90M", budget: "$2.35M", variance: "+$3.55M", bold: true },
    { label: "Capex", actual: "-$335.5K", budget: "-$352.3K", variance: "+$16.8K" },
    { label: "Cash from Investing (CFI)", actual: "-$335.5K", budget: "-$352.3K", variance: "+$16.8K", bold: true },
    { label: "Cash from Financing (CFF)", actual: "n/a", budget: "n/a", variance: "—" },
    { label: "Net Change in Cash", actual: "$4.96M", budget: "$1.39M", variance: "+$3.57M", bold: true },
    { label: "Ending Cash", actual: "$50.26M", budget: "$48.17M", variance: "+$2.09M", bold: true }
  ];

  const cfsHdr = ["Line Item", "YTD Actual", "YTD Budget", "YTD Variance"];
  const cfsColW = [5.5, 2.2, 2.2, 2.2];
  const cfsX = 0.35; const cfsY = 1.05;

  [cfsHdr, ...cfsRows.map(r => [r.label, r.actual, r.budget, r.variance])].forEach((row, ri) => {
    row.forEach((cell, ci) => {
      const isHeader = ri === 0;
      const rowData = ri > 0 ? cfsRows[ri - 1] : null;
      const isBold = rowData && rowData.bold;
      const isVar = ci === 3;
      let fc = C.white;
      if (isHeader) fc = C.muted;
      else if (isVar && typeof cell === "string" && cell.startsWith("+")) fc = C.green;
      else if (isVar && typeof cell === "string" && cell.startsWith("-")) fc = C.red;
      const xOff = cfsColW.slice(0, ci).reduce((a, b) => a + b, 0);
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

  // Source note — MUST sit below Ending Cash row (cfsY + 15 rows × 0.3 = 5.55).
  const cfsSourceY = cfsY + (cfsRows.length + 1) * 0.3 + 0.08;
  slide.addText("Source: build_ts_data.cfs  |  Period: Jan–Jun 2026  |  Currency: USD", {
    x: 0.35, y: cfsSourceY, w: 12.63, h: 0.22, fontSize: 7.5, color: C.muted, fontFace: "Calibri"
  });

  // Data gaps note
  slide.addShape(pptx.ShapeType.rect, { x: 0.35, y: cfsSourceY + 0.28, w: 12.63, h: 0.55, fill: { color: C.surfaceAlt }, line: { color: C.amber, width: 0.5 } });
  slide.addText("YTD Actual column uses Actual CFS for periods ≤ close_month (never Forecast). Validation notes belong in Risks — do not substitute Forecast into this table.", {
    x: 0.5, y: cfsSourceY + 0.33, w: 12.3, h: 0.45, fontSize: 8, color: C.muted, fontFace: "Calibri", wrap: true
  });

  // Headcount note
  slide.addShape(pptx.ShapeType.rect, { x: 0.35, y: cfsSourceY + 0.92, w: 12.63, h: 0.36, fill: { color: C.surfaceAlt }, line: { color: C.muted, width: 0.5 } });
  slide.addText("⚠ Headcount: Current month actual = 0 — verify headcount_plan / workforce tables loaded. EOY forecast = 16 headcount (integers, not dollars).", {
    x: 0.5, y: cfsSourceY + 0.96, w: 12.3, h: 0.28, fontSize: 8, color: C.muted, fontFace: "Calibri", wrap: true
  });
}

pptx.writeFile({ fileName: "C:/Users/mattj/AppData/Local/Temp/smpl-deck-znbbp6p2/mda_deck_2026-06.pptx" });