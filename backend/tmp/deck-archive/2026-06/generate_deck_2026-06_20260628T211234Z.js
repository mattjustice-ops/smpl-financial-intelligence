const pptxgen = require("pptxgenjs");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";

const BG = "070d18";
const SURFACE = "111d2e";
const SURFACE_ALT = "0d1520";
const CYAN = "00d4aa";
const AMBER = "f59e0b";
const RED = "ef4444";
const GREEN = "22c55e";
const WHITE = "ffffff";
const MUTED = "6b8ca8";
const DIVIDER = "1a2e42";

const Q = "Q2";
const YEAR = "2026";
const MONTH = "June";
const FOOTER_BASE = `SMPL · Board Operating Review · ${Q} ${YEAR} · CONFIDENTIAL`;

function addSlideBackground(slide) {
  slide.addShape(pptx.ShapeType.rect, {
    x: 0, y: 0, w: 13.33, h: 7.5,
    fill: { color: BG },
    line: { color: BG }
  });
}

function addFooter(slide, slideNum, confidential) {
  const txt = confidential
    ? `${FOOTER_BASE}  ${slideNum}/11`
    : `SMPL · Board Operating Review · ${Q} ${YEAR} · ${slideNum}/11`;
  slide.addText(txt, {
    x: 0.35, y: 7.05, w: 12.63, h: 0.25,
    fontSize: 7, color: MUTED, fontFace: "Calibri", align: "center"
  });
}

function addSectionLabel(slide, text, x, y, w) {
  slide.addText(text, {
    x, y, w, h: 0.2,
    fontSize: 9, color: CYAN, fontFace: "Calibri", bold: true,
    charSpacing: 2
  });
}

function addDividerLine(slide, x, y, w) {
  slide.addShape(pptx.ShapeType.rect, {
    x, y, w, h: 0,
    line: { color: DIVIDER, width: 0.75 }
  });
}

function kpiCard(slide, x, y, w, h, label, value, sub1, sub2, valueColor) {
  slide.addShape(pptx.ShapeType.rect, {
    x, y, w, h,
    fill: { color: SURFACE },
    line: { color: DIVIDER, width: 0.5 }
  });
  slide.addText(label, {
    x: x + 0.1, y: y + 0.07, w: w - 0.2, h: 0.18,
    fontSize: 7.5, color: MUTED, fontFace: "Calibri", bold: true, charSpacing: 1
  });
  slide.addText(value, {
    x: x + 0.1, y: y + 0.27, w: w - 0.2, h: 0.28,
    fontSize: 15, color: valueColor || CYAN, fontFace: "Calibri", bold: true
  });
  if (sub1) {
    slide.addText(sub1, {
      x: x + 0.1, y: y + 0.56, w: w - 0.2, h: 0.16,
      fontSize: 7.5, color: MUTED, fontFace: "Calibri"
    });
  }
  if (sub2) {
    slide.addText(sub2, {
      x: x + 0.1, y: y + 0.72, w: w - 0.2, h: 0.16,
      fontSize: 7.5, color: MUTED, fontFace: "Calibri"
    });
  }
}

// ─── SLIDE 1: TITLE ───────────────────────────────────────────────────────────
{
  const slide = pptx.addSlide();
  addSlideBackground(slide);

  slide.addShape(pptx.ShapeType.rect, {
    x: 0, y: 0, w: 0.06, h: 7.5,
    fill: { color: CYAN }, line: { color: CYAN }
  });

  slide.addText("SMPL.ai", {
    x: 0.55, y: 1.8, w: 8, h: 0.9,
    fontSize: 52, color: WHITE, fontFace: "Calibri", bold: true
  });

  slide.addText("AI Operating System for SaaS Finance Teams", {
    x: 0.55, y: 2.75, w: 9, h: 0.35,
    fontSize: 13, color: MUTED, fontFace: "Calibri"
  });

  slide.addText("Board Operating Review", {
    x: 0.55, y: 3.25, w: 9, h: 0.55,
    fontSize: 26, color: CYAN, fontFace: "Calibri", bold: true
  });

  slide.addText(`${Q} ${YEAR} · ${MONTH} ${YEAR} · Series B`, {
    x: 0.55, y: 3.88, w: 9, h: 0.3,
    fontSize: 12, color: MUTED, fontFace: "Calibri"
  });

  addDividerLine(slide, 0.55, 4.3, 6);

  addFooter(slide, 1, false);
}

// ─── SLIDE 2: EXECUTIVE SUMMARY ───────────────────────────────────────────────
{
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addSectionLabel(slide, "EXECUTIVE SUMMARY", 0.35, 0.55, 4);
  slide.addText("Executive Summary — June 2026", {
    x: 0.35, y: 0.75, w: 12.63, h: 0.4,
    fontSize: 22, color: WHITE, fontFace: "Calibri", bold: true
  });
  addDividerLine(slide, 0.35, 1.18, 12.63);

  // Row 1: 5 KPI cards
  const cardW = 2.4;
  const cardH = 1.0;
  const cardY = 1.25;
  const cardGap = 0.08;
  const cards = [
    { label: "ENDING ARR", value: "$85.31M", sub1: "Budget: $84.89M", sub2: "vs Budget: +$413.1K (+0.5%)", vc: CYAN },
    { label: "REVENUE (CM)", value: "$2.20M", sub1: "Budget: $2.32M", sub2: "vs Budget: -4.8%", vc: AMBER },
    { label: "ENDING CASH", value: "$48.43M", sub1: "Budget: $31.46M", sub2: "vs Budget: +$16.98M (+54.0%)", vc: GREEN },
    { label: "GROSS MARGIN %", value: "70.0%", sub1: "Budget: 70.0%", sub2: "CM Actual", vc: CYAN },
    { label: "EBITDA (CM)", value: "$661.5K", sub1: "Budget: $647.5K", sub2: "vs Budget: +$14.0K (+2.2%)", vc: GREEN }
  ];
  cards.forEach((c, i) => {
    kpiCard(slide, 0.35 + i * (cardW + cardGap), cardY, cardW, cardH, c.label, c.value, c.sub1, c.sub2, c.vc);
  });

  // Row 2 left: period matrix table
  const tblX = 0.35;
  const tblY = 2.38;
  const tblW = 7.2;
  addSectionLabel(slide, "PERIOD MATRIX", tblX, tblY, 3);

  const headers = ["Metric", "CM Actual", "QTD Actual", "YTD Actual", "FY Outlook", "YTD vs Budget"];
  const rows = [
    ["Ending ARR", "$85.31M", "$85.31M", "$85.31M", "$90.29M", "+0.5%"],
    ["Revenue", "$2.20M", "$6.18M", "$11.51M", "$25.88M", "-4.8%"],
    ["EBITDA", "$661.5K", "$2.03M", "$3.87M", "$7.46M", "+1.6%"],
    ["Gross Margin %", "70.0%", "70.7%", "70.8%", "70.4%", "—"],
    ["Ending Cash", "$48.43M", "$48.43M", "$48.43M", "$49.92M", "+54.0%"],
  ];

  const hdrRow = headers.map((h, i) => ({
    text: h,
    options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri", align: i === 0 ? "left" : "center" }
  }));

  const tableRows = [hdrRow];
  rows.forEach(r => {
    tableRows.push(r.map((cell, i) => {
      let color = MUTED;
      if (i === 5) {
        color = cell.startsWith("+") ? GREEN : cell.startsWith("-") ? RED : MUTED;
      } else if (i > 0) {
        color = WHITE;
      }
      return { text: cell, options: { color, fontSize: 7.5, fontFace: "Calibri", align: i === 0 ? "left" : "center", fill: i % 2 === 0 ? SURFACE : SURFACE_ALT } };
    }));
  });

  slide.addTable(tableRows, {
    x: tblX, y: tblY + 0.22, w: tblW, h: 1.6,
    border: { color: DIVIDER, pt: 0.5 },
    rowH: 0.26
  });

  // Row 2 right: Key Takeaways
  const ktX = 7.75;
  const ktY = 2.38;
  addSectionLabel(slide, "KEY TAKEAWAYS", ktX, ktY, 5);
  const takeaways = [
    "ARR reached $85.31M, +$413.1K vs budget — expansion and new business tracking on plan.",
    "Revenue $2.20M CM, -4.8% vs budget; YTD $11.51M vs $12.09M budget reflects timing.",
    "EBITDA $661.5K CM, +2.2% vs budget; YTD $3.87M ahead of budget by +$59.1K.",
    "Cash $48.43M YTD, +$16.98M vs budget — strong collections and payroll efficiency.",
    "FY ARR outlook $90.29M vs $96.10M budget; pipeline coverage at 3.0x requires H2 acceleration."
  ];
  takeaways.forEach((t, i) => {
    slide.addText(`• ${t}`, {
      x: ktX, y: ktY + 0.25 + i * 0.38, w: 5.2, h: 0.35,
      fontSize: 8, color: MUTED, fontFace: "Calibri", wrap: true
    });
  });

  // Row 3: 4 bottom KPI cards
  const bCardW = 2.95;
  const bCardH = 0.75;
  const bCardY = 6.05;
  const bCards = [
    { label: "YTD REVENUE", value: "$11.51M", sub1: "Budget: $12.09M  |  Var: -4.8%", vc: AMBER },
    { label: "YTD EBITDA", value: "$3.87M", sub1: "Budget: $3.81M  |  Var: +1.6%", vc: GREEN },
    { label: "FY ARR OUTLOOK", value: "$90.29M", sub1: "Budget: $96.10M  |  Var: -6.0%", vc: CYAN },
    { label: "FY CASH EOY", value: "$49.92M", sub1: "Budget: $23.85M  |  Var: +109.3%", vc: GREEN }
  ];
  bCards.forEach((c, i) => {
    slide.addShape(pptx.ShapeType.rect, {
      x: 0.35 + i * (bCardW + 0.1), y: bCardY, w: bCardW, h: bCardH,
      fill: { color: SURFACE }, line: { color: DIVIDER, width: 0.5 }
    });
    slide.addText(c.label, {
      x: 0.45 + i * (bCardW + 0.1), y: bCardY + 0.06, w: bCardW - 0.2, h: 0.18,
      fontSize: 7, color: MUTED, fontFace: "Calibri", bold: true, charSpacing: 1
    });
    slide.addText(c.value, {
      x: 0.45 + i * (bCardW + 0.1), y: bCardY + 0.25, w: bCardW - 0.2, h: 0.28,
      fontSize: 16, color: c.vc, fontFace: "Calibri", bold: true
    });
    slide.addText(c.sub1, {
      x: 0.45 + i * (bCardW + 0.1), y: bCardY + 0.54, w: bCardW - 0.2, h: 0.16,
      fontSize: 7, color: MUTED, fontFace: "Calibri"
    });
  });

  addFooter(slide, 2, true);
}

// ─── SLIDE 3: ARR ANALYSIS ────────────────────────────────────────────────────
{
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addSectionLabel(slide, "ARR ANALYSIS", 0.35, 0.55, 4);
  slide.addText("ARR Analysis — June 2026", {
    x: 0.35, y: 0.75, w: 12.63, h: 0.4,
    fontSize: 22, color: WHITE, fontFace: "Calibri", bold: true
  });
  addDividerLine(slide, 0.35, 1.18, 12.63);

  // Clustered column chart
  const chartData = [
    {
      name: "Actual ($M)",
      labels: ["Beginning ARR", "+ New Business", "+ Expansion", "+ Reactivation", "− Contraction", "− Churn", "Ending ARR"],
      values: [83.445, 1.685, 0.869, 0.143, -0.314, -0.52, 85.308]
    },
    {
      name: "Budget ($M)",
      labels: ["Beginning ARR", "+ New Business", "+ Expansion", "+ Reactivation", "− Contraction", "− Churn", "Ending ARR"],
      values: [82.939, 1.769, 0.913, 0.15, -0.329, -0.546, 84.895]
    }
  ];

  slide.addChart(pptx.ChartType.bar, chartData, {
    x: 0.35, y: 1.28, w: 6.0, h: 3.2,
    barDir: "col",
    barGrouping: "clustered",
    chartColors: [CYAN, AMBER],
    showLegend: true,
    legendPos: "b",
    legendColor: WHITE,
    legendFontSize: 8,
    legendFontFace: "Calibri",
    catAxisLabelColor: MUTED,
    valAxisLabelColor: MUTED,
    catAxisLabelFontSize: 7,
    valAxisLabelFontSize: 7,
    catAxisLabelFontFace: "Calibri",
    valAxisLabelFontFace: "Calibri",
    valAxisTitle: "ARR ($M)",
    showValAxisTitle: true,
    valAxisTitleColor: MUTED,
    valAxisTitleFontSize: 8,
    plotAreaBkgndColor: BG,
    chartAreaBkgndColor: BG,
    dataLabelFontSize: 0,
    showValue: false
  });

  // Right KPI cards
  const rX = 6.55;
  const rKpiW = 3.1;
  const rKpiH = 0.82;
  const rKpis = [
    { label: "ENDING ARR", value: "$85.31M", sub1: "Budget: $84.89M", sub2: "Var: +$413.1K (+0.5%)", vc: CYAN },
    { label: "NET NEW ARR", value: "$1.68M", sub1: "Budget: $1.77M", sub2: "Var: -$84.2K", vc: AMBER },
    { label: "EXPANSION", value: "$869.1K", sub1: "Budget: $912.6K", sub2: "Var: -$43.5K", vc: CYAN },
    { label: "CHURN", value: "$520.2K", sub1: "Budget: $546.2K", sub2: "Var: -$26.0K (favorable)", vc: RED }
  ];
  rKpis.forEach((c, i) => {
    kpiCard(slide, rX, 1.28 + i * (rKpiH + 0.08), rKpiW, rKpiH, c.label, c.value, c.sub1, c.sub2, c.vc);
  });

  // ARR Bridge table
  addSectionLabel(slide, "ARR BRIDGE", 0.35, 4.6, 3);
  const bridgeHeaders = [
    [
      { text: "Component", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri" } },
      { text: "Actual", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri", align: "center" } },
      { text: "Budget", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri", align: "center" } },
      { text: "Variance", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri", align: "center" } }
    ]
  ];
  const bridgeRows = [
    ["Beginning ARR", "$83.44M", "$82.94M", "+$506.2K"],
    ["New Business", "$1.68M", "$1.77M", "-$84.2K"],
    ["Expansion", "$869.1K", "$912.6K", "-$43.5K"],
    ["Reactivation", "$142.9K", "$150.0K", "-$7.1K"],
    ["Contraction", "$313.7K", "$329.3K", "-$15.7K"],
    ["Churn", "$520.2K", "$546.2K", "-$26.0K"],
    ["Ending ARR", "$85.31M", "$84.89M", "+$413.1K"]
  ];
  const bridgeTableRows = [...bridgeHeaders];
  bridgeRows.forEach((r, ri) => {
    bridgeTableRows.push(r.map((cell, ci) => {
      let color = ci === 0 ? WHITE : ci === 3 ? (cell.startsWith("+") ? GREEN : RED) : MUTED;
      return { text: cell, options: { color, fontSize: 7.5, fontFace: "Calibri", align: ci === 0 ? "left" : "center", fill: ri % 2 === 0 ? SURFACE : SURFACE_ALT } };
    }));
  });
  slide.addTable(bridgeTableRows, {
    x: 0.35, y: 4.82, w: 6.0, h: 1.65,
    border: { color: DIVIDER, pt: 0.5 },
    rowH: 0.22
  });

  // Key Takeaways
  addSectionLabel(slide, "KEY TAKEAWAYS", 6.55, 4.6, 5);
  const arrTakeaways = [
    "Ending ARR $85.31M, +$413.1K vs budget — new business and expansion both near plan.",
    "Churn $520.2K vs $546.2K budget — favorable by $26.0K; retention holding.",
    "G$R 99.4%; pipeline coverage 3.0x supports near-term ARR targets.",
    "FY ARR outlook $90.29M vs $96.10M budget — H2 acceleration required."
  ];
  arrTakeaways.forEach((t, i) => {
    slide.addText(`• ${t}`, {
      x: 6.55, y: 4.82 + i * 0.38, w: 6.4, h: 0.35,
      fontSize: 8, color: MUTED, fontFace: "Calibri", wrap: true
    });
  });

  addFooter(slide, 3, true);
}

// ─── SLIDE 4: P&L ─────────────────────────────────────────────────────────────
{
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addSectionLabel(slide, "P&L REVIEW", 0.35, 0.55, 4);
  slide.addText("P&L Review — June 2026", {
    x: 0.35, y: 0.75, w: 12.63, h: 0.4,
    fontSize: 22, color: WHITE, fontFace: "Calibri", bold: true
  });
  addDividerLine(slide, 0.35, 1.18, 12.63);

  // 4 KPI strip
  const plKpis = [
    { label: "REVENUE (CM)", value: "$2.20M", sub1: "Budget: $2.32M  |  Var: -4.8%", vc: AMBER },
    { label: "GROSS MARGIN (CM)", value: "70.0%", sub1: "Budget: 70.0%", vc: CYAN },
    { label: "EBITDA (CM)", value: "$661.5K", sub1: "Budget: $647.5K  |  Var: +2.2%", vc: GREEN },
    { label: "NET INCOME (CM)", value: "$409.0K", sub1: "Budget: $393.4K  |  Var: +4.0%", vc: GREEN }
  ];
  plKpis.forEach((c, i) => {
    kpiCard(slide, 0.35 + i * 3.12, 1.28, 2.95, 0.75, c.label, c.value, c.sub1, null, c.vc);
  });

  // P&L Detail table
  addSectionLabel(slide, "P&L DETAIL", 0.35, 2.15, 3);
  const plHeaders = [
    [
      { text: "Line Item", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri" } },
      { text: "CM Actual", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri", align: "center" } },
      { text: "CM Budget", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri", align: "center" } },
      { text: "CM Variance", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri", align: "center" } },
      { text: "YTD Actual", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri", align: "center" } },
      { text: "YTD Budget", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri", align: "center" } },
      { text: "YTD Variance", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri", align: "center" } }
    ]
  ];
  const plRows = [
    ["Revenue", "$2.20M", "$2.32M", "-$110.2K", "$11.51M", "$12.09M", "-$575.7K"],
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
  const plTableRows = [...plHeaders];
  plRows.forEach((r, ri) => {
    plTableRows.push(r.map((cell, ci) => {
      let color = WHITE;
      if (ci === 0) color = WHITE;
      else if (ci === 3 || ci === 6) {
        color = cell.startsWith("+") ? GREEN : cell.startsWith("-") ? RED : MUTED;
      } else {
        color = MUTED;
      }
      return { text: cell, options: { color, fontSize: 7.5, fontFace: "Calibri", align: ci === 0 ? "left" : "center", fill: ri % 2 === 0 ? SURFACE : SURFACE_ALT } };
    }));
  });
  slide.addTable(plTableRows, {
    x: 0.35, y: 2.35, w: 8.5, h: 3.8,
    border: { color: DIVIDER, pt: 0.5 },
    rowH: 0.34
  });

  // Key Takeaways right
  addSectionLabel(slide, "KEY TAKEAWAYS", 9.05, 2.15, 4);
  const plTakeaways = [
    "Revenue $2.20M CM, -4.8% vs budget; YTD $11.51M vs $12.09M budget.",
    "Gross margin held at 70.0% CM and 70.8% YTD — in line with budget.",
    "EBITDA $661.5K CM, +2.2% vs budget; operating leverage improving.",
    "S&M $2.50M vs $2.65M budget — efficiency gains supporting margin.",
    "Net income $409.0K CM, +4.0% vs budget; YTD $2.43M vs $2.36M."
  ];
  plTakeaways.forEach((t, i) => {
    slide.addText(`• ${t}`, {
      x: 9.05, y: 2.35 + i * 0.52, w: 3.9, h: 0.48,
      fontSize: 8, color: MUTED, fontFace: "Calibri", wrap: true
    });
  });

  addFooter(slide, 4, true);
}

// ─── SLIDE 5: CASH ────────────────────────────────────────────────────────────
{
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addSectionLabel(slide, "CASH & LIQUIDITY", 0.35, 0.55, 4);
  slide.addText("Cash & Liquidity — June 2026", {
    x: 0.35, y: 0.75, w: 12.63, h: 0.4,
    fontSize: 22, color: WHITE, fontFace: "Calibri", bold: true
  });
  addDividerLine(slide, 0.35, 1.18, 12.63);

  // YTD Cash summary strip
  const cashKpis = [
    { label: "ENDING CASH (CM)", value: "$50.26M", sub1: "Budget: $48.17M", vc: GREEN },
    { label: "ENDING CASH (YTD)", value: "$48.43M", sub1: "Budget: $31.46M  |  +54.0%", vc: GREEN },
    { label: "CASH HEADROOM", value: "$38.43M", sub1: "Floor: $10.00M", vc: CYAN },
    { label: "YTD COLLECTIONS", value: "$58.82M", sub1: "CM Collections: $6.81M", vc: CYAN }
  ];
  cashKpis.forEach((c, i) => {
    kpiCard(slide, 0.35 + i * 3.12, 1.28, 2.95, 0.75, c.label, c.value, c.sub1, null, c.vc);
  });

  // Cash bridge table
  addSectionLabel(slide, "CASH BRIDGE — JUNE 2026", 0.35, 2.15, 5);
  const cashBridgeHeaders = [
    [
      { text: "Line Item", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 8, fontFace: "Calibri" } },
      { text: "Actual", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 8, fontFace: "Calibri", align: "center" } },
      { text: "Budget", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 8, fontFace: "Calibri", align: "center" } }
    ]
  ];
  const cashBridgeRows = [
    ["Beginning cash", "$48.02M", "$29.60M"],
    ["Collections", "$6.81M", "$8.91M"],
    ["Payroll", "$2.47M", "$4.00M"],
    ["Vendor payments", "$3.66M", "$1.40M"],
    ["Commissions", "$199.9K", "$370.8K"],
    ["Capex", "$220.0K", "$220.0K"],
    ["Ending cash", "$50.26M", "$48.17M"]
  ];
  const cashTableRows = [...cashBridgeHeaders];
  cashBridgeRows.forEach((r, ri) => {
    cashTableRows.push(r.map((cell, ci) => ({
      text: cell,
      options: {
        color: ci === 0 ? WHITE : MUTED,
        fontSize: 8, fontFace: "Calibri",
        align: ci === 0 ? "left" : "center",
        fill: ri % 2 === 0 ? SURFACE : SURFACE_ALT,
        bold: ri === 6
      }
    })));
  });
  slide.addTable(cashTableRows, {
    x: 0.35, y: 2.35, w: 5.5, h: 2.2,
    border: { color: DIVIDER, pt: 0.5 },
    rowH: 0.28
  });

  // Right KPI cards
  const cashRKpis = [
    { label: "FY CASH EOY OUTLOOK", value: "$49.92M", sub1: "Budget: $23.85M", sub2: "Var: +$26.07M (+109.3%)", vc: GREEN },
    { label: "BEGINNING CASH (CM)", value: "$48.02M", sub1: "Prior month ending", vc: CYAN },
    { label: "CAPEX (CM)", value: "$220.0K", sub1: "Budget: $220.0K", vc: MUTED },
    { label: "CASH FLOOR", value: "$10.00M", sub1: "Headroom: $38.43M", vc: AMBER }
  ];
  cashRKpis.forEach((c, i) => {
    kpiCard(slide, 6.1, 2.35 + i * 0.9, 3.1, 0.82, c.label, c.value, c.sub1, c.sub2 || null, c.vc);
  });

  // Key Takeaways
  addSectionLabel(slide, "KEY TAKEAWAYS", 9.4, 2.15, 3.5);
  const cashTakeaways = [
    "Ending cash $50.26M CM, +$2.09M vs budget of $48.17M.",
    "YTD ending cash $48.43M vs $31.46M budget — +54.0% favorable.",
    "Cash headroom $38.43M above $10.00M floor — strong liquidity position.",
    "FY cash outlook $49.92M vs $23.85M budget — +109.3% upside."
  ];
  cashTakeaways.forEach((t, i) => {
    slide.addText(`• ${t}`, {
      x: 9.4, y: 2.35 + i * 0.52, w: 3.55, h: 0.48,
      fontSize: 8, color: MUTED, fontFace: "Calibri", wrap: true
    });
  });

  addFooter(slide, 5, true);
}

// ─── SLIDE 6: GTM PERFORMANCE ─────────────────────────────────────────────────
{
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addSectionLabel(slide, "GTM & MARKETING PERFORMANCE", 0.35, 0.55, 6);
  slide.addText("GTM & Marketing Performance — June 2026", {
    x: 0.35, y: 0.75, w: 12.63, h: 0.4,
    fontSize: 22, color: WHITE, fontFace: "Calibri", bold: true
  });
  addDividerLine(slide, 0.35, 1.18, 12.63);

  // KPI strip
  const gtmKpis = [
    { label: "TOTAL MQLs", value: "119", sub1: "June 2026", vc: CYAN },
    { label: "PIPELINE CREATED", value: "$5.40M", sub1: "Budget $57.03M  (-79.9% YTD)", vc: CYAN },
    { label: "TOTAL SPEND", value: "$50K", sub1: "Blended Efficiency: 60.7x", vc: AMBER },
    { label: "CLOSED WON", value: "$1.80M", sub1: "Best Win Rate: Organic 23.8%", vc: GREEN }
  ];
  gtmKpis.forEach((c, i) => {
    kpiCard(slide, 0.35 + i * 3.12, 1.28, 2.95, 0.75, c.label, c.value, c.sub1, null, c.vc);
  });

  // Channel table
  addSectionLabel(slide, "CHANNEL PERFORMANCE", 0.35, 2.15, 5);
  const gtmTblHeaders = [
    [
      { text: "Channel", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri" } },
      { text: "Spend (Act)", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri", align: "center" } },
      { text: "Spend (Bud)", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri", align: "center" } },
      { text: "Pipeline (Act)", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri", align: "center" } },
      { text: "MQLs", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri", align: "center" } },
      { text: "Efficiency", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri", align: "center" } },
      { text: "Win Rate", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 7.5, fontFace: "Calibri", align: "center" } }
    ]
  ];
  const gtmChannelRows = [
    ["Paid Social", "$12K", "$2K", "$524K", "28", "44.5x", "10.6%"],
    ["Paid Search", "$8K", "$8K", "$508K", "19", "63.7x", "3.3%"],
    ["Content Syndication", "$7K", "$9K", "$310K", "17", "43.5x", "9.1%"],
    ["Organic Search", "$5K", "$7K", "$443K", "13", "81.2x", "23.8%"],
    ["Outbound", "$5K", "$8K", "$484K", "12", "96.1x", "8.1%"]
  ];
  const gtmTableRows = [...gtmTblHeaders];
  gtmChannelRows.forEach((r, ri) => {
    gtmTableRows.push(r.map((cell, ci) => ({
      text: cell,
      options: {
        color: ci === 0 ? WHITE : MUTED,
        fontSize: 7.5, fontFace: "Calibri",
        align: ci === 0 ? "left" : "center",
        fill: ri % 2 === 0 ? SURFACE : SURFACE_ALT
      }
    })));
  });
  slide.addTable(gtmTableRows, {
    x: 0.35, y: 2.35, w: 6.5, h: 1.8,
    border: { color: DIVIDER, pt: 0.5 },
    rowH: 0.3
  });

  // Clustered column chart: Pipeline vs Spend
  const gtmChartData = [
    {
      name: "Pipeline ($M)",
      labels: ["Paid Social", "Paid Search", "Content Syndication", "Organic Search", "Outbound"],
      values: [0.524, 0.508, 0.31, 0.443, 0.484]
    },
    {
      name: "Spend ($M)",
      labels: ["Paid Social", "Paid Search", "Content Syndication", "Organic Search", "Outbound"],
      values: [0.012, 0.008, 0.007, 0.005, 0.005]
    }
  ];

  slide.addChart(pptx.ChartType.bar, gtmChartData, {
    x: 7.0, y: 2.35, w: 6.0, h: 3.5,
    barDir: "col",
    barGrouping: "clustered",
    chartColors: [CYAN, AMBER],
    showLegend: true,
    legendPos: "b",
    legendColor: WHITE,
    legendFontSize: 8,
    legendFontFace: "Calibri",
    catAxisLabelColor: MUTED,
    valAxisLabelColor: MUTED,
    catAxisLabelFontSize: 7,
    valAxisLabelFontSize: 7,
    catAxisLabelFontFace: "Calibri",
    valAxisLabelFontFace: "Calibri",
    valAxisTitle: "Amount ($M)",
    showValAxisTitle: true,
    valAxisTitleColor: MUTED,
    valAxisTitleFontSize: 8,
    plotAreaBkgndColor: BG,
    chartAreaBkgndColor: BG,
    showValue: false
  });

  addSectionLabel(slide, "KEY TAKEAWAYS", 0.35, 4.25, 5);
  const gtmTakeaways = [
    "Outbound leads efficiency at 96.1x pipeline/spend; Organic Search best win rate 23.8%.",
    "Total pipeline created $5.40M CM; blended efficiency 60.7x across all channels.",
    "Paid Social highest MQL volume (28) but lowest win rate (10.6%) — review qualification.",
    "Pipeline coverage 3.0x — adequate near-term; H2 ramp required for FY targets."
  ];
  gtmTakeaways.forEach((t, i) => {
    slide.addText(`• ${t}`, {
      x: 0.35, y: 4.45 + i * 0.38, w: 6.5, h: 0.35,
      fontSize: 8, color: MUTED, fontFace: "Calibri", wrap: true
    });
  });

  addFooter(slide, 6, true);
}

// ─── SLIDE 7: GTM FUNNEL ──────────────────────────────────────────────────────
{
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addSectionLabel(slide, "GTM FUNNEL ANALYSIS", 0.35, 0.55, 5);
  slide.addText("GTM Funnel Analysis — YTD Jan–Jun 2026", {
    x: 0.35, y: 0.75, w: 12.63, h: 0.4,
    fontSize: 22, color: WHITE, fontFace: "Calibri", bold: true
  });
  addDividerLine(slide, 0.35, 1.18, 12.63);

  // Coverage summary strip
  const funnelKpis = [
    { label: "YTD MQLs", value: "721", sub1: "Q1: 362  |  Q2: 359", vc: CYAN },
    { label: "YTD SQLs", value: "251", sub1: "Q1: 126  |  Q2: 125", vc: CYAN },
    { label: "YTD PIPELINE ARR", value: "$27.90M", sub1: "Q1: $12.15M  |  Q2: $15.75M", vc: AMBER },
    { label: "YTD CLOSED WON ARR", value: "$9.30M", sub1: "Q1: $4.05M  |  Q2: $5.25M", vc: GREEN }
  ];
  funnelKpis.forEach((c, i) => {
    kpiCard(slide, 0.35 + i * 3.12, 1.28, 2.95, 0.75, c.label, c.value, c.sub1, null, c.vc);
  });

  // Q1 table
  addSectionLabel(slide, "Q1 2026 FUNNEL", 0.35, 2.15, 4);
  const funnelHeaders = (label) => [[
    { text: label, options: { bold: true, color: CYAN, fill: SURFACE_ALT, fontSize: 8, fontFace: "Calibri" } },
    { text: "Actual", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 8, fontFace: "Calibri", align: "center" } },
    { text: "Budget", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 8, fontFace: "Calibri", align: "center" } }
  ]];

  const q1Rows = [
    ["MQLs", "362", "0"],
    ["SQLs", "126", "—"],
    ["SALs", "100", "—"],
    ["Opportunities", "45", "—"],
    ["Pipeline ARR", "$12.15M", "$0.00"],
    ["Closed Won ARR", "$4.05M", "$0.00"],
    ["Spend", "$144.8K", "$0.00"]
  ];
  const q1TableRows = [...funnelHeaders("Q1 Metric")];
  q1Rows.forEach((r, ri) => {
    q1TableRows.push(r.map((cell, ci) => ({
      text: cell,
      options: { color: ci === 0 ? WHITE : MUTED, fontSize: 8, fontFace: "Calibri", align: ci === 0 ? "left" : "center", fill: ri % 2 === 0 ? SURFACE : SURFACE_ALT }
    })));
  });
  slide.addTable(q1TableRows, {
    x: 0.35, y: 2.35, w: 3.8, h: 2.3,
    border: { color: DIVIDER, pt: 0.5 },
    rowH: 0.3
  });

  // Q2 table
  addSectionLabel(slide, "Q2 2026 FUNNEL", 4.35, 2.15, 4);
  const q2Rows = [
    ["MQLs", "359", "0"],
    ["SQLs", "125", "—"],
    ["SALs", "97", "—"],
    ["Opportunities", "42", "—"],
    ["Pipeline ARR", "$15.75M", "$0.00"],
    ["Closed Won ARR", "$5.25M", "$0.00"],
    ["Spend", "$146.0K", "$0.00"]
  ];
  const q2TableRows = [...funnelHeaders("Q2 Metric")];
  q2Rows.forEach((r, ri) => {
    q2TableRows.push(r.map((cell, ci) => ({
      text: cell,
      options: { color: ci === 0 ? WHITE : MUTED, fontSize: 8, fontFace: "Calibri", align: ci === 0 ? "left" : "center", fill: ri % 2 === 0 ? SURFACE : SURFACE_ALT }
    })));
  });
  slide.addTable(q2TableRows, {
    x: 4.35, y: 2.35, w: 3.8, h: 2.3,
    border: { color: DIVIDER, pt: 0.5 },
    rowH: 0.3
  });

  // YTD table
  addSectionLabel(slide, "YTD 2026 FUNNEL", 8.35, 2.15, 4);
  const ytdFunnelRows = [
    ["MQLs", "721", "0"],
    ["SQLs", "251", "—"],
    ["SALs", "197", "—"],
    ["Opportunities", "87", "—"],
    ["Pipeline ARR", "$27.90M", "$0.00"],
    ["Closed Won ARR", "$9.30M", "$0.00"],
    ["Spend", "$290.8K", "$0.00"]
  ];
  const ytdFunnelTableRows = [...funnelHeaders("YTD Metric")];
  ytdFunnelRows.forEach((r, ri) => {
    ytdFunnelTableRows.push(r.map((cell, ci) => ({
      text: cell,
      options: { color: ci === 0 ? WHITE : MUTED, fontSize: 8, fontFace: "Calibri", align: ci === 0 ? "left" : "center", fill: ri % 2 === 0 ? SURFACE : SURFACE_ALT }
    })));
  });
  slide.addTable(ytdFunnelTableRows, {
    x: 8.35, y: 2.35, w: 4.6, h: 2.3,
    border: { color: DIVIDER, pt: 0.5 },
    rowH: 0.3
  });

  // Key Takeaways
  addSectionLabel(slide, "KEY TAKEAWAYS", 0.35, 4.75, 5);
  const funnelTakeaways = [
    "YTD MQLs 721 — Q1 362 and Q2 359 showing consistent top-of-funnel volume.",
    "YTD pipeline ARR $27.90M; closed won $9.30M — conversion rate tracking.",
    "YTD spend $290.8K generating $27.90M pipeline — strong efficiency.",
    "Budget pipeline data not loaded; re-stage with marketing ops for H2 planning."
  ];
  funnelTakeaways.forEach((t, i) => {
    slide.addText(`• ${t}`, {
      x: 0.35, y: 4.95 + i * 0.38, w: 12.63, h: 0.35,
      fontSize: 8, color: MUTED, fontFace: "Calibri", wrap: true
    });
  });

  addFooter(slide, 7, true);
}

// ─── SLIDE 8: RISKS & OPPORTUNITIES ──────────────────────────────────────────
{
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addSectionLabel(slide, "RISKS & OPPORTUNITIES", 0.35, 0.55, 6);
  slide.addText("Risks & Opportunities — June 2026", {
    x: 0.35, y: 0.75, w: 12.63, h: 0.4,
    fontSize: 22, color: WHITE, fontFace: "Calibri", bold: true
  });
  addDividerLine(slide, 0.35, 1.18, 12.63);

  // Risks left
  addSectionLabel(slide, "RISKS", 0.35, 1.28, 3);
  const risks = [
    { title: "Deferred Pipeline", detail: "Slipped pipeline $9.87M requires next-quarter coverage review.", action: "Re-stage opportunities with validated next steps and owners.", impact: "$9.87M" },
    { title: "Revenue vs Budget", detail: "Revenue trailed budget in the close month. Validate expansion timing and churn pockets before board distribution.", action: "Review expansion timing and churn pockets.", impact: "" },
    { title: "Close Validation", detail: "Validation status: fail. Confirm tie-outs before distribution.", action: "Finance to certify waterfall and GL reconciliations.", impact: "" },
    { title: "Data Gaps", detail: "No Forecast ARR waterfall rows for 2026-06. No Forecast revenue line for 2026-06.", action: "Finance to certify waterfall and GL reconciliations.", impact: "" }
  ];
  risks.forEach((r, i) => {
    const cardY = 1.5 + i * 1.3;
    slide.addShape(pptx.ShapeType.rect, {
      x: 0.35, y: cardY, w: 6.1, h: 1.18,
      fill: { color: SURFACE }, line: { color: RED, width: 0.75 }
    });
    slide.addShape(pptx.ShapeType.rect, {
      x: 0.35, y: cardY, w: 0.06, h: 1.18,
      fill: { color: RED }, line: { color: RED }
    });
    slide.addText("MEDIUM RISK", {
      x: 0.5, y: cardY + 0.06, w: 2, h: 0.16,
      fontSize: 6.5, color: RED, fontFace: "Calibri", bold: true, charSpacing: 1
    });
    slide.addText(r.title, {
      x: 0.5, y: cardY + 0.22, w: 5.8, h: 0.22,
      fontSize: 10, color: WHITE, fontFace: "Calibri", bold: true
    });
    slide.addText(r.detail, {
      x: 0.5, y: cardY + 0.44, w: 5.8, h: 0.32,
      fontSize: 7.5, color: MUTED, fontFace: "Calibri", wrap: true
    });
    slide.addText(`Action: ${r.action}${r.impact ? "  |  Impact: " + r.impact : ""}`, {
      x: 0.5, y: cardY + 0.9, w: 5.8, h: 0.2,
      fontSize: 7, color: AMBER, fontFace: "Calibri", italic: true
    });
  });

  // Opportunities right
  addSectionLabel(slide, "OPPORTUNITIES", 6.75, 1.28, 5);
  const opps = [
    { title: "Liquidity Headroom", detail: "Cash $50.26M provides runway for strategic investments.", action: "Prioritize high-ROI GTM and product bets with board approval.", upside: "$40.26M" },
    { title: "Cash Forecast Upside", detail: "Confirm ending cash ties to balance sheet cash in Validation tab.", action: "Review.", upside: "" },
    { title: "SaaS MD&A Summary", detail: "Review Validation Checks before board distribution.", action: "Review.", upside: "" },
    { title: "Resolve Data Gaps", detail: "No Forecast ARR waterfall rows for 2026-06. No Forecast revenue line for 2026-06. Resolve failed validations and reload missing CSV sources.", action: "Resolve failed validations and reload missing CSV sources.", upside: "" }
  ];
  opps.forEach((o, i) => {
    const cardY = 1.5 + i * 1.3;
    slide.addShape(pptx.ShapeType.rect, {
      x: 6.75, y: cardY, w: 6.2, h: 1.18,
      fill: { color: SURFACE }, line: { color: GREEN, width: 0.75 }
    });
    slide.addShape(pptx.ShapeType.rect, {
      x: 6.75, y: cardY, w: 0.06, h: 1.18,
      fill: { color: GREEN }, line: { color: GREEN }
    });
    slide.addText("MEDIUM OPP", {
      x: 6.9, y: cardY + 0.06, w: 2, h: 0.16,
      fontSize: 6.5, color: GREEN, fontFace: "Calibri", bold: true, charSpacing: 1
    });
    slide.addText(o.title, {
      x: 6.9, y: cardY + 0.22, w: 5.9, h: 0.22,
      fontSize: 10, color: WHITE, fontFace: "Calibri", bold: true
    });
    slide.addText(o.detail, {
      x: 6.9, y: cardY + 0.44, w: 5.9, h: 0.32,
      fontSize: 7.5, color: MUTED, fontFace: "Calibri", wrap: true
    });
    slide.addText(`Action: ${o.action}${o.upside ? "  |  Upside: " + o.upside : ""}`, {
      x: 6.9, y: cardY + 0.9, w: 5.9, h: 0.2,
      fontSize: 7, color: CYAN, fontFace: "Calibri", italic: true
    });
  });

  addFooter(slide, 8, true);
}

// ─── SLIDE 9: FINANCIAL OUTLOOK ───────────────────────────────────────────────
{
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addSectionLabel(slide, "FINANCIAL OUTLOOK", 0.35, 0.55, 5);
  slide.addText("Financial Outlook — FY 2026", {
    x: 0.35, y: 0.75, w: 12.63, h: 0.4,
    fontSize: 22, color: WHITE, fontFace: "Calibri", bold: true
  });
  addDividerLine(slide, 0.35, 1.18, 12.63);

  // Line chart: Ending ARR Actual, Budget, Outlook
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const actualArr = [76.31, 77.815, 79.505, 81.385, 83.445, 85.308021, null, null, null, null, null, null];
  const budgetArr = [76.2263, 77.63875, 79.22765, 80.99755, 82.93875, 84.894922, 86.950304, 88.907781, 90.720006, 92.571464, 94.320414, 96.098088];
  const outlookArr = [76.31, 77.815, 79.505, 81.385, 83.445, 85.308021, 86.292802, 87.132856, 87.828763, 88.513816, 89.196397, 90.291802];

  const lineChartData = [
    { name: "Actual ($M)", labels: months, values: actualArr },
    { name: "Budget ($M)", labels: months, values: budgetArr },
    { name: "Outlook ($M)", labels: months, values: outlookArr }
  ];

  slide.addChart(pptx.ChartType.line, lineChartData, {
    x: 0.35, y: 1.28, w: 8.0, h: 2.8,
    chartColors: [CYAN, AMBER, MUTED],
    lineDataSymbol: "none",
    showLegend: true,
    legendPos: "b",
    legendColor: WHITE,
    legendFontSize: 8,
    legendFontFace: "Calibri",
    catAxisLabelColor: MUTED,
    valAxisLabelColor: MUTED,
    catAxisLabelFontSize: 7,
    valAxisLabelFontSize: 7,
    catAxisLabelFontFace: "Calibri",
    valAxisLabelFontFace: "Calibri",
    valAxisTitle: "Ending ARR ($M)",
    showValAxisTitle: true,
    valAxisTitleColor: MUTED,
    valAxisTitleFontSize: 8,
    plotAreaBkgndColor: BG,
    chartAreaBkgndColor: BG,
    showValue: false,
    lineSize: 2
  });

  // FY Outlook summary table
  addSectionLabel(slide, "FY 2026 OUTLOOK SUMMARY", 0.35, 4.18, 5);
  const outlookHeaders = [
    [
      { text: "Metric", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 8, fontFace: "Calibri" } },
      { text: "Outlook", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 8, fontFace: "Calibri", align: "center" } },
      { text: "Budget", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 8, fontFace: "Calibri", align: "center" } },
      { text: "Note", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 8, fontFace: "Calibri" } }
    ]
  ];
  const outlookRows = [
    ["Ending ARR (Dec EoY)", "$90.29M", "$96.10M", "Point-in-time Dec — never sum monthly ARR"],
    ["FY Revenue", "$25.88M", "$26.54M", "Outlook = Actual closed months + Forecast open months"],
    ["FY Gross Margin %", "70.4%", "70.9%", "Computed independently — do not copy same value"],
    ["FY EBITDA", "$7.46M", "$7.79M", ""],
    ["Ending Cash (Dec EoY)", "$49.92M", "$23.85M", "Point-in-time Dec ending cash"]
  ];
  const outlookTableRows = [...outlookHeaders];
  outlookRows.forEach((r, ri) => {
    outlookTableRows.push(r.map((cell, ci) => ({
      text: cell,
      options: { color: ci === 0 ? WHITE : ci === 3 ? MUTED : MUTED, fontSize: 7.5, fontFace: "Calibri", align: ci === 0 ? "left" : ci === 3 ? "left" : "center", fill: ri % 2 === 0 ? SURFACE : SURFACE_ALT }
    })));
  });
  slide.addTable(outlookTableRows, {
    x: 0.35, y: 4.38, w: 8.0, h: 1.8,
    border: { color: DIVIDER, pt: 0.5 },
    rowH: 0.3
  });

  // H2 Priorities right
  addSectionLabel(slide, "H2 PRIORITIES", 8.55, 1.28, 4);
  const h2Priorities = [
    { title: "ARR & GTM", detail: "FY ARR outlook $90.29M vs $96.10M budget. Pipeline coverage 3.0x — accelerate H2 new business and expansion." },
    { title: "Profitability", detail: "YTD gross margin 70.8%, EBITDA $3.87M ahead of budget by +$59.1K. Maintain cost discipline while investing in growth." },
    { title: "Cash & Runway", detail: "Cash $48.43M YTD, FY outlook $49.92M vs $23.85M budget. Headroom $38.43M above floor — deploy strategically." },
    { title: "Workforce", detail: "EOY forecast headcount 16. Verify headcount plan and open reqs before next board cycle." }
  ];
  h2Priorities.forEach((p, i) => {
    slide.addShape(pptx.ShapeType.rect, {
      x: 8.55, y: 1.5 + i * 1.2, w: 4.4, h: 1.08,
      fill: { color: SURFACE }, line: { color: DIVIDER, width: 0.5 }
    });
    slide.addShape(pptx.ShapeType.rect, {
      x: 8.55, y: 1.5 + i * 1.2, w: 0.06, h: 1.08,
      fill: { color: CYAN }, line: { color: CYAN }
    });
    slide.addText(p.title, {
      x: 8.7, y: 1.55 + i * 1.2, w: 4.1, h: 0.22,
      fontSize: 10, color: CYAN, fontFace: "Calibri", bold: true
    });
    slide.addText(p.detail, {
      x: 8.7, y: 1.78 + i * 1.2, w: 4.1, h: 0.7,
      fontSize: 7.5, color: MUTED, fontFace: "Calibri", wrap: true
    });
  });

  // Key Takeaways
  addSectionLabel(slide, "KEY TAKEAWAYS", 0.35, 6.28, 5);
  const outlookTakeaways = [
    "FY ARR outlook $90.29M vs $96.10M budget — -6.0% gap requires H2 pipeline acceleration.",
    "FY revenue outlook $25.88M vs $26.54M budget — -2.5% manageable with H2 execution.",
    "Cash outlook $49.92M vs $23.85M budget — +109.3% upside enables strategic investment.",
    "FY EBITDA $7.46M vs $7.79M budget — profitability on track despite revenue headwind."
  ];
  outlookTakeaways.forEach((t, i) => {
    slide.addText(`• ${t}`, {
      x: 0.35, y: 6.45 + i * 0.18, w: 8.0, h: 0.17,
      fontSize: 7.5, color: MUTED, fontFace: "Calibri", wrap: true
    });
  });

  addFooter(slide, 9, true);
}

// ─── SLIDE 10: BOARD ACTIONS ──────────────────────────────────────────────────
{
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addSectionLabel(slide, "BOARD ACTIONS", 0.35, 0.55, 4);
  slide.addText("Board Actions — Q2 2026", {
    x: 0.35, y: 0.75, w: 12.63, h: 0.4,
    fontSize: 22, color: WHITE, fontFace: "Calibri", bold: true
  });
  addDividerLine(slide, 0.35, 1.18, 12.63);

  const actions = [
    { number: "01", type: "FOR APPROVAL", title: "Approve June 2026 financial close package", owner: "CFO", due: "Board meeting", color: CYAN },
    { number: "02", type: "FOR APPROVAL", title: "Approve updated FY ARR outlook and GTM plan", owner: "CEO / CRO", due: "Next board cycle", color: CYAN },
    { number: "03", type: "FOR APPROVAL", title: "Approve headcount and hiring plan adjustments", owner: "CFO / CHRO", due: "Next board cycle", color: AMBER },
    { number: "04", type: "FOR DISCUSSION", title: "Pipeline coverage and channel efficiency reallocation", owner: "CRO", due: "Operating review", color: AMBER }
  ];

  const cardW = 5.9;
  const cardH = 2.3;
  const positions = [
    { x: 0.35, y: 1.5 },
    { x: 6.55, y: 1.5 },
    { x: 0.35, y: 4.05 },
    { x: 6.55, y: 4.05 }
  ];

  actions.forEach((a, i) => {
    const pos = positions[i];
    slide.addShape(pptx.ShapeType.rect, {
      x: pos.x, y: pos.y, w: cardW, h: cardH,
      fill: { color: SURFACE }, line: { color: a.color, width: 0.75 }
    });
    slide.addShape(pptx.ShapeType.rect, {
      x: pos.x, y: pos.y, w: 0.06, h: cardH,
      fill: { color: a.color }, line: { color: a.color }
    });
    slide.addText(a.number, {
      x: pos.x + 0.2, y: pos.y + 0.15, w: 0.6, h: 0.5,
      fontSize: 28, color: a.color, fontFace: "Calibri", bold: true
    });
    slide.addText(a.type, {
      x: pos.x + 0.85, y: pos.y + 0.15, w: 4.8, h: 0.22,
      fontSize: 8, color: a.color, fontFace: "Calibri", bold: true, charSpacing: 1
    });
    slide.addText(a.title, {
      x: pos.x + 0.2, y: pos.y + 0.7, w: 5.5, h: 0.6,
      fontSize: 13, color: WHITE, fontFace: "Calibri", bold: true, wrap: true
    });
    slide.addText(`Owner: ${a.owner}`, {
      x: pos.x + 0.2, y: pos.y + 1.45, w: 3, h: 0.25,
      fontSize: 9, color: MUTED, fontFace: "Calibri"
    });
    slide.addText(`Due: ${a.due}`, {
      x: pos.x + 0.2, y: pos.y + 1.75, w: 5.5, h: 0.25,
      fontSize: 9, color: MUTED, fontFace: "Calibri"
    });
  });

  addFooter(slide, 10, true);
}

// ─── SLIDE 11: APPENDIX A — YTD CFS ──────────────────────────────────────────
{
  const slide = pptx.addSlide();
  addSlideBackground(slide);
  addSectionLabel(slide, "APPENDIX A", 0.35, 0.55, 4);
  slide.addText("YTD Cash Flow Statement — Jan–Jun 2026", {
    x: 0.35, y: 0.75, w: 12.63, h: 0.4,
    fontSize: 22, color: WHITE, fontFace: "Calibri", bold: true
  });
  addDividerLine(slide, 0.35, 1.18, 12.63);

  const cfsHeaders = [
    [
      { text: "Line Item", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 8.5, fontFace: "Calibri" } },
      { text: "Actual", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 8.5, fontFace: "Calibri", align: "center" } },
      { text: "Budget", options: { bold: true, color: WHITE, fill: SURFACE_ALT, fontSize: 8.5, fontFace: "Calibri", align: "center" } }
    ]
  ];

  const cfsRows = [
    ["Beginning Cash", "$45.30M", "$46.77M", false],
    ["Net Income", "$2.43M", "$2.36M", false],
    ["Depreciation & Amortization", "$591.8K", "$621.3K", false],
    ["Stock-Based Compensation", "n/a", "n/a", false],
    ["Change in AR", "$2.19M", "-$1.88M", false],
    ["Change in Deferred Revenue", "$232.0K", "$249.2K", false],
    ["Change in AP", "$373.5K", "$917.7K", false],
    ["Change in Prepaids", "$75.0K", "$75.0K", false],
    ["Cash from Operations (CFO)", "$5.90M", "$2.35M", true],
    ["Capex", "-$335.5K", "-$352.3K", false],
    ["Cash from Investing (CFI)", "-$335.5K", "-$352.3K", true],
    ["Cash from Financing (CFF)", "n/a", "n/a", false],
    ["Net Change in Cash", "$4.96M", "$1.39M", true],
    ["Ending Cash", "$50.26M", "$48.17M", true]
  ];

  const cfsTableRows = [...cfsHeaders];
  cfsRows.forEach((r, ri) => {
    const isBold = r[3];
    cfsTableRows.push([
      { text: r[0], options: { color: WHITE, fontSize: 8.5, fontFace: "Calibri", bold: isBold, fill: ri % 2 === 0 ? SURFACE : SURFACE_ALT } },
      { text: r[1], options: { color: isBold ? CYAN : MUTED, fontSize: 8.5, fontFace: "Calibri", bold: isBold, align: "center", fill: ri % 2 === 0 ? SURFACE : SURFACE_ALT } },
      { text: r[2], options: { color: isBold ? AMBER : MUTED, fontSize: 8.5, fontFace: "Calibri", bold: isBold, align: "center", fill: ri % 2 === 0 ? SURFACE : SURFACE_ALT } }
    ]);
  });

  slide.addTable(cfsTableRows, {
    x: 0.35, y: 1.3, w: 12.63, h: 5.5,
    border: { color: DIVIDER, pt: 0.5 },
    rowH: 0.36,
    colW: [7.0, 2.8, 2.83]
  });

  addFooter(slide, 11, true);
}

pptx.writeFile({ fileName: "C:/Users/mattj/AppData/Local/Temp/smpl-deck-o14gjbqv/mda_deck_2026-06.pptx" });