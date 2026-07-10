const pptxgen = require("pptxgenjs");
const pptx = new pptxgen();

pptx.layout = "LAYOUT_WIDE";

// ─── THEME ───────────────────────────────────────────────────────────────────
const BG       = "070d18";
const ACCENT   = "00d4aa";
const WHITE    = "ffffff";
const MUTED    = "8ab4c4";
const SURFACE  = "1a2535";
const ROW_A    = "0d1520";
const ROW_B    = "111d2e";
const QUARTER  = "Q2";
const YEAR     = "2026";
const FOOTER_TXT = `SMPL · Board Operating Review · ${QUARTER} ${YEAR} · CONFIDENTIAL`;

// ─── HELPERS ─────────────────────────────────────────────────────────────────
function addBackground(slide) {
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: BG }, line: { color: BG } });
}

function addFooter(slide, slideNum) {
  slide.addText(FOOTER_TXT, { x: 0.3, y: 7.22, w: 10, h: 0.22, fontSize: 9, color: MUTED, fontFace: "Calibri", align: "left" });
  slide.addText(String(slideNum), { x: 12.73, y: 7.22, w: 0.3, h: 0.22, fontSize: 9, color: MUTED, fontFace: "Calibri", align: "right" });
}

function addSectionLabel(slide, label) {
  slide.addText(label, { x: 0.3, y: 0.18, w: 4, h: 0.2, fontSize: 10, color: ACCENT, fontFace: "Calibri", bold: false });
}

function addTitle(slide, title, subtitle) {
  slide.addText(title, { x: 0.3, y: 0.42, w: 12.73, h: 0.42, fontSize: 28, color: WHITE, fontFace: "Calibri", bold: true });
  if (subtitle) {
    slide.addText(subtitle, { x: 0.3, y: 0.88, w: 12.73, h: 0.22, fontSize: 11, color: MUTED, fontFace: "Calibri" });
  }
}

function addKpiCard(slide, x, y, w, h, value, label, variance) {
  slide.addShape(pptx.ShapeType.rect, { x, y, w, h, fill: { color: SURFACE }, line: { color: SURFACE } });
  slide.addText(value, { x: x + 0.15, y: y + 0.12, w: w - 0.3, h: 0.52, fontSize: 32, color: ACCENT, fontFace: "Calibri", bold: true, align: "center" });
  slide.addText(label, { x: x + 0.15, y: y + 0.66, w: w - 0.3, h: 0.2, fontSize: 9, color: WHITE, fontFace: "Calibri", align: "center" });
  if (variance) {
    slide.addText(variance, { x: x + 0.15, y: y + 0.88, w: w - 0.3, h: 0.18, fontSize: 9, color: MUTED, fontFace: "Calibri", align: "center" });
  }
}

function addKeyTakeaways(slide, x, y, w, h, bullets) {
  slide.addShape(pptx.ShapeType.rect, { x, y, w, h, fill: { color: SURFACE }, line: { color: SURFACE } });
  slide.addText("Key Takeaways", { x: x + 0.15, y: y + 0.1, w: w - 0.3, h: 0.22, fontSize: 10, color: ACCENT, fontFace: "Calibri", bold: true });
  const bulletObjs = bullets.map(b => ({ text: b, options: { fontSize: 10, color: WHITE, fontFace: "Calibri", bullet: { type: "bullet" }, paraSpaceAfter: 4 } }));
  slide.addText(bulletObjs, { x: x + 0.15, y: y + 0.35, w: w - 0.3, h: h - 0.45, valign: "top" });
}

function varColor(v) {
  if (!v) return WHITE;
  if (v.startsWith("+")) return ACCENT;
  if (v.startsWith("-")) return "ff6b6b";
  return WHITE;
}

// ─── SLIDE 1 — TITLE ─────────────────────────────────────────────────────────
(function() {
  const slide = pptx.addSlide();
  addBackground(slide);

  slide.addText("SMPL.ai", { x: 0, y: 1.8, w: 13.33, h: 0.7, fontSize: 48, color: ACCENT, fontFace: "Calibri", bold: true, align: "center" });
  slide.addText("Board Operating Review", { x: 0, y: 2.55, w: 13.33, h: 0.5, fontSize: 32, color: WHITE, fontFace: "Calibri", bold: true, align: "center" });
  slide.addText("Q2 2026  ·  June 2026 Close", { x: 0, y: 3.12, w: 13.33, h: 0.35, fontSize: 18, color: MUTED, fontFace: "Calibri", align: "center" });

  slide.addShape(pptx.ShapeType.rect, { x: 4.5, y: 3.6, w: 4.33, h: 0.03, fill: { color: ACCENT }, line: { color: ACCENT } });

  slide.addText("AI Operating System for SaaS Finance Teams", { x: 0, y: 3.78, w: 13.33, h: 0.28, fontSize: 13, color: MUTED, fontFace: "Calibri", align: "center" });
  slide.addText("Series B  ·  Fiscal Year Jan–Dec 2026  ·  CONFIDENTIAL", { x: 0, y: 4.15, w: 13.33, h: 0.24, fontSize: 11, color: MUTED, fontFace: "Calibri", align: "center" });

  addFooter(slide, 1);
})();

// ─── SLIDE 2 — EXECUTIVE SUMMARY ─────────────────────────────────────────────
(function() {
  const slide = pptx.addSlide();
  addBackground(slide);
  addSectionLabel(slide, "EXECUTIVE SUMMARY");
  addTitle(slide, "Q2 2026 Board Snapshot", "June 2026 Close  ·  All figures USD  ·  Actuals vs Budget");

  // Full-width period matrix table
  const tableData = [
    [
      { text: "Metric", options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "left" } },
      { text: "CM Actual", options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right" } },
      { text: "CM vs Budget", options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right" } },
      { text: "QTD Actual", options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right" } },
      { text: "YTD Actual", options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right" } },
      { text: "YTD vs Budget", options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right" } },
      { text: "FY Outlook", options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right" } },
    ]
  ];

  const rows = [
    ["Ending ARR",         "$85.31M", "+$413.1K / +0.5%", "$250.14M", "$483.77M", "+0.4%",  "$85.31M"],
    ["Revenue",            "$2.20M",  "-$110.2K / -4.8%", "$6.18M",   "$11.51M",  "-4.8%",  "$25.88M"],
    ["EBITDA",             "$661.5K", "+$14.0K / +2.2%",  "$2.03M",   "$3.87M",   "+1.6%",  "$7.46M"],
    ["Gross Margin %",     "0.0%",    "—",                 "54.6%",    "54.8%",    "—",      "54.8%"],
    ["Ending Cash",        "$48.43M", "+$16.98M / +54.0%","$177.04M", "$334.86M", "+144.5%","$48.43M"],
    ["Pipeline Created",   "$5.40M",  "+$92.8K / +1.7%",  "$5.40M",   "$5.40M",   "-79.9%", "$5.40M"],
  ];

  rows.forEach((r, i) => {
    const bg = i % 2 === 0 ? ROW_A : ROW_B;
    const varCM = r[2];
    const varYTD = r[5];
    tableData.push([
      { text: r[0], options: { color: WHITE, fontSize: 9, fontFace: "Calibri", align: "left", fill: { color: bg } } },
      { text: r[1], options: { color: WHITE, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[2], options: { color: varColor(varCM), fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[3], options: { color: WHITE, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[4], options: { color: WHITE, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[5], options: { color: varColor(varYTD), fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[6], options: { color: WHITE, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
    ]);
  });

  slide.addTable(tableData, {
    x: 0.3, y: 1.18, w: 12.73, h: 2.1,
    colW: [2.2, 1.5, 2.0, 1.5, 1.5, 1.5, 1.53],
    fill: { color: SURFACE },
    border: { type: "none" },
    rowH: 0.28,
  });

  // KPI chips
  addKpiCard(slide, 0.3,  3.45, 2.9, 1.2, "$85.31M", "Ending ARR (June 2026)", "vs budget +$413.1K / +0.5%");
  addKpiCard(slide, 3.5,  3.45, 2.9, 1.2, "$48.43M", "Ending Cash", "vs budget +$16.98M / +54.0%");
  addKpiCard(slide, 6.7,  3.45, 2.9, 1.2, "$661.5K", "EBITDA (CM)", "vs budget +$14.0K / +2.2%");
  addKpiCard(slide, 9.9,  3.45, 2.83,1.2, "54.8%",   "YTD Gross Margin %", "on budget 54.8%");

  // Key Takeaways
  addKeyTakeaways(slide, 0.3, 4.82, 12.73, 2.35, [
    "Ending ARR of $85.31M beat budget by +$413.1K (+0.5%), with YTD ARR of $483.77M tracking +$1.84M ahead of budget.",
    "Revenue of $2.20M in June trailed budget by -$110.2K (-4.8%); YTD revenue of $11.51M is -$575.7K (-4.8%) vs budget.",
    "EBITDA of $661.5K in June exceeded budget by +$14.0K (+2.2%); YTD EBITDA of $3.87M is +$59.1K (+1.6%) ahead.",
    "Ending cash of $48.43M is +$16.98M (+54.0%) above budget of $31.46M, providing strong liquidity headroom.",
    "YTD pipeline created of $5.40M is -$21.51M (-79.9%) vs budget; pipeline coverage stands at 3.0x closed won.",
  ]);

  addFooter(slide, 2);
})();

// ─── SLIDE 3 — ARR ANALYSIS ───────────────────────────────────────────────────
(function() {
  const slide = pptx.addSlide();
  addBackground(slide);
  addSectionLabel(slide, "ARR ANALYSIS");
  addTitle(slide, "ARR Bridge — June 2026", "Monthly ARR waterfall  ·  Actual vs Budget  ·  USD");

  // Waterfall bridge table
  const hdr = [
    { text: "ARR Component",    options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: SURFACE } } },
    { text: "Actual",           options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "Budget",           options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "Variance",         options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
  ];

  const bridgeRows = [
    ["Beginning ARR (BOP)",  "$83.44M",  "—",          "—"],
    ["New Business",         "$1.68M",   "$1.77M",     "-$90.0K"],
    ["Expansion",            "$869.1K",  "$912.6K",    "-$43.5K"],
    ["Reactivation",         "$142.9K",  "—",          "—"],
    ["Contraction",          "-$313.7K", "—",          "—"],
    ["Churn",                "-$520.2K", "-$546.2K",   "+$26.0K"],
    ["Net New ARR",          "$1.68M",   "$1.77M",     "-$90.0K"],
    ["Ending ARR (EOP)",     "$85.31M",  "$84.89M",    "+$413.1K"],
  ];

  const tableData = [hdr];
  bridgeRows.forEach((r, i) => {
    const bg = i % 2 === 0 ? ROW_A : ROW_B;
    const isTotal = r[0].startsWith("Ending") || r[0].startsWith("Net New");
    tableData.push([
      { text: r[0], options: { color: isTotal ? ACCENT : WHITE, fontSize: 9, fontFace: "Calibri", bold: isTotal, align: "left",  fill: { color: bg } } },
      { text: r[1], options: { color: WHITE,                     fontSize: 9, fontFace: "Calibri", bold: isTotal, align: "right", fill: { color: bg } } },
      { text: r[2], options: { color: MUTED,                     fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[3], options: { color: varColor(r[3]),             fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
    ]);
  });

  slide.addTable(tableData, {
    x: 0.3, y: 1.18, w: 7.5, h: 2.7,
    colW: [3.0, 1.5, 1.5, 1.5],
    fill: { color: SURFACE },
    border: { type: "none" },
    rowH: 0.3,
  });

  // Retention metrics table
  const retHdr = [
    { text: "Retention Metric", options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: SURFACE } } },
    { text: "Value",            options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
  ];
  const retRows = [
    ["G$R (Gross Retention Rate)", "1.0%"],
    ["Pipeline Coverage",          "3.0x"],
    ["Closed Won (CM)",            "$1.80M"],
  ];
  const retTable = [retHdr];
  retRows.forEach((r, i) => {
    const bg = i % 2 === 0 ? ROW_A : ROW_B;
    retTable.push([
      { text: r[0], options: { color: WHITE, fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: bg } } },
      { text: r[1], options: { color: WHITE, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
    ]);
  });

  slide.addTable(retTable, {
    x: 8.1, y: 1.18, w: 4.93, h: 1.3,
    colW: [3.2, 1.73],
    fill: { color: SURFACE },
    border: { type: "none" },
    rowH: 0.3,
  });

  // KPI cards
  addKpiCard(slide, 8.1,  2.65, 2.35, 1.2, "$85.31M", "Ending ARR", "vs budget +$413.1K");
  addKpiCard(slide, 10.68, 2.65, 2.35, 1.2, "$1.68M",  "New Business ARR", "vs budget -$90.0K");

  // Key Takeaways
  addKeyTakeaways(slide, 0.3, 4.05, 12.73, 2.35, [
    "Ending ARR of $85.31M exceeded budget of $84.89M by +$413.1K (+0.5%), driven by better-than-expected retention.",
    "New Business ARR of $1.68M came in -$90.0K below budget of $1.77M; expansion of $869.1K trailed budget by -$43.5K.",
    "Churn of $520.2K was favorable vs budget of $546.2K by +$26.0K, reflecting improved retention in the month.",
    "Reactivation of $142.9K and contraction of $313.7K are not budgeted line items; net new ARR of $1.68M vs $1.77M budget.",
    "G$R of 1.0% and pipeline coverage of 3.0x; N$R is not available for this period.",
  ]);

  addFooter(slide, 3);
})();

// ─── SLIDE 4 — P&L REVIEW ────────────────────────────────────────────────────
(function() {
  const slide = pptx.addSlide();
  addBackground(slide);
  addSectionLabel(slide, "P&L REVIEW");
  addTitle(slide, "Income Statement Highlights", "CM / QTD / YTD  ·  Actual vs Budget  ·  USD");

  // P&L variance table
  const hdr = [
    { text: "Line Item",      options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: SURFACE } } },
    { text: "CM Actual",      options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "CM Budget",      options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "CM Variance",    options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "QTD Actual",     options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "YTD Actual",     options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "YTD Budget",     options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "YTD Variance",   options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
  ];

  const plRows = [
    ["Revenue",         "$2.20M",  "$2.32M",  "-$110.2K", "$6.18M",  "$11.51M", "$12.09M", "-$575.7K"],
    ["Gross Margin %",  "0.0%",    "0.0%",    "—",        "54.6%",   "54.8%",   "54.8%",   "—"],
    ["EBITDA",          "$661.5K", "$647.5K", "+$14.0K",  "$2.03M",  "$3.87M",  "$3.81M",  "+$59.1K"],
  ];

  const tableData = [hdr];
  plRows.forEach((r, i) => {
    const bg = i % 2 === 0 ? ROW_A : ROW_B;
    tableData.push([
      { text: r[0], options: { color: WHITE,          fontSize: 9, fontFace: "Calibri", bold: true, align: "left",  fill: { color: bg } } },
      { text: r[1], options: { color: WHITE,          fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[2], options: { color: MUTED,          fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[3], options: { color: varColor(r[3]), fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[4], options: { color: WHITE,          fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[5], options: { color: WHITE,          fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[6], options: { color: MUTED,          fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[7], options: { color: varColor(r[7]), fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
    ]);
  });

  slide.addTable(tableData, {
    x: 0.3, y: 1.18, w: 12.73, h: 1.3,
    colW: [1.8, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4, 1.43],
    fill: { color: SURFACE },
    border: { type: "none" },
    rowH: 0.3,
  });

  // FY Outlook mini table
  const fyHdr = [
    { text: "FY 2026 Outlook",  options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: SURFACE } } },
    { text: "Outlook",          options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "Budget",           options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "Variance",         options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
  ];
  const fyRows = [
    ["Revenue",     "$25.88M", "$26.54M", "-$652.3K"],
    ["EBITDA",      "$7.46M",  "$7.79M",  "-$328.7K"],
    ["Gross Margin %", "54.8%","54.8%",   "—"],
  ];
  const fyTable = [fyHdr];
  fyRows.forEach((r, i) => {
    const bg = i % 2 === 0 ? ROW_A : ROW_B;
    fyTable.push([
      { text: r[0], options: { color: WHITE,          fontSize: 9, fontFace: "Calibri", bold: true, align: "left",  fill: { color: bg } } },
      { text: r[1], options: { color: WHITE,          fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[2], options: { color: MUTED,          fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[3], options: { color: varColor(r[3]), fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
    ]);
  });

  slide.addTable(fyTable, {
    x: 0.3, y: 2.72, w: 7.0, h: 1.3,
    colW: [2.2, 1.6, 1.6, 1.6],
    fill: { color: SURFACE },
    border: { type: "none" },
    rowH: 0.3,
  });

  // KPI cards
  addKpiCard(slide, 7.6,  2.72, 2.35, 1.2, "$2.20M",  "Revenue (CM)", "vs budget -$110.2K / -4.8%");
  addKpiCard(slide, 10.28,2.72, 2.75, 1.2, "$661.5K", "EBITDA (CM)",  "vs budget +$14.0K / +2.2%");

  // Key Takeaways
  addKeyTakeaways(slide, 0.3, 4.1, 12.73, 2.35, [
    "CM revenue of $2.20M missed budget by -$110.2K (-4.8%); YTD revenue of $11.51M is -$575.7K (-4.8%) behind budget.",
    "EBITDA of $661.5K in June beat budget by +$14.0K (+2.2%); YTD EBITDA of $3.87M is +$59.1K (+1.6%) ahead of budget.",
    "Gross margin of 54.8% YTD is exactly on budget; CM gross margin of 0.0% reflects timing of cost recognition.",
    "FY 2026 revenue outlook of $25.88M is -$652.3K (-2.5%) below budget of $26.54M based on current run rate.",
    "FY 2026 EBITDA outlook of $7.46M is -$328.7K (-4.2%) below budget of $7.79M; margin profile remains stable.",
  ]);

  addFooter(slide, 4);
})();

// ─── SLIDE 5 — CASH & LIQUIDITY ───────────────────────────────────────────────
(function() {
  const slide = pptx.addSlide();
  addBackground(slide);
  addSectionLabel(slide, "CASH & LIQUIDITY");
  addTitle(slide, "Cash Position & Liquidity", "June 2026 Close  ·  USD  ·  Actual vs Budget");

  // Left: Cash bridge
  slide.addText("June 2026 Cash Bridge", { x: 0.3, y: 1.18, w: 5.9, h: 0.25, fontSize: 11, color: ACCENT, fontFace: "Calibri", bold: true });

  const bridgeHdr = [
    { text: "Item",    options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: SURFACE } } },
    { text: "Amount",  options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
  ];
  const bridgeItems = [
    ["Beginning Cash (BOP)",       "$48.02M"],
    ["Collections",                "$6.81M"],
    ["Payroll",                    "$0.00"],
    ["Vendor Payments",            "$0.00"],
    ["Commissions",                "$0.00"],
    ["CapEx",                      "-$220.0K"],
    ["Ending Cash (EOP) — Actual", "$48.43M"],
    ["Ending Cash (EOP) — Budget", "$31.46M"],
  ];
  const bridgeTable = [bridgeHdr];
  bridgeItems.forEach((r, i) => {
    const bg = i % 2 === 0 ? ROW_A : ROW_B;
    const isTotal = r[0].includes("Ending");
    bridgeTable.push([
      { text: r[0], options: { color: isTotal ? ACCENT : WHITE, fontSize: 9, fontFace: "Calibri", bold: isTotal, align: "left",  fill: { color: bg } } },
      { text: r[1], options: { color: isTotal ? ACCENT : WHITE, fontSize: 9, fontFace: "Calibri", bold: isTotal, align: "right", fill: { color: bg } } },
    ]);
  });

  slide.addTable(bridgeTable, {
    x: 0.3, y: 1.47, w: 5.9, h: 2.7,
    colW: [3.8, 2.1],
    fill: { color: SURFACE },
    border: { type: "none" },
    rowH: 0.3,
  });

  // Right: Ending cash comparison
  slide.addText("Ending Cash — Actual vs Budget", { x: 6.5, y: 1.18, w: 6.53, h: 0.25, fontSize: 11, color: ACCENT, fontFace: "Calibri", bold: true });

  const cashHdr = [
    { text: "Period",   options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: SURFACE } } },
    { text: "Actual",   options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "Budget",   options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "Variance", options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
  ];
  const cashRows = [
    ["CM (June 2026)",  "$48.43M",  "$31.46M",  "+$16.98M"],
    ["YTD (Jan–Jun)",   "$334.86M", "$136.95M", "+$197.91M"],
    ["FY 2026 Outlook", "$48.43M",  "$289.63M", "-$241.20M"],
  ];
  const cashTable = [cashHdr];
  cashRows.forEach((r, i) => {
    const bg = i % 2 === 0 ? ROW_A : ROW_B;
    cashTable.push([
      { text: r[0], options: { color: WHITE,          fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: bg } } },
      { text: r[1], options: { color: WHITE,          fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[2], options: { color: MUTED,          fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[3], options: { color: varColor(r[3]), fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
    ]);
  });

  slide.addTable(cashTable, {
    x: 6.5, y: 1.47, w: 6.53, h: 1.3,
    colW: [2.0, 1.5, 1.5, 1.53],
    fill: { color: SURFACE },
    border: { type: "none" },
    rowH: 0.3,
  });

  // KPI cards right side
  addKpiCard(slide, 6.5,  2.95, 3.1, 1.2, "$48.43M", "Ending Cash (CM)", "vs budget +$16.98M / +54.0%");
  addKpiCard(slide, 9.93, 2.95, 3.1, 1.2, "$38.43M", "Cash Headroom vs Floor", "floor: $10.00M");

  // Key Takeaways
  addKeyTakeaways(slide, 0.3, 4.32, 12.73, 2.35, [
    "Ending cash of $48.43M is +$16.98M (+54.0%) above budget of $31.46M, supported by $6.81M in collections.",
    "Cash headroom above the $10.00M floor is $38.43M, providing approximately 3.8x coverage of the minimum threshold.",
    "YTD collections of $58.82M drove YTD ending cash of $334.86M, +$197.91M (+144.5%) above YTD budget of $136.95M.",
    "CapEx of $220.0K in June was the only cash outflow; payroll, vendor payments, and commissions recorded at $0.00.",
    "FY 2026 cash outlook of $48.43M is -$241.20M (-83.3%) below budget of $289.63M; requires FY cash model review.",
  ]);

  addFooter(slide, 5);
})();

// ─── SLIDE 6 — CASH FLOW STATEMENT ───────────────────────────────────────────
(function() {
  const slide = pptx.addSlide();
  addBackground(slide);
  addSectionLabel(slide, "CASH FLOW STATEMENT");
  addTitle(slide, "YTD Indirect Cash Flow Statement", "Jan–Jun 2026  ·  Actual vs Budget  ·  USD");

  const hdr = [
    { text: "Line Item",                  options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: SURFACE } } },
    { text: "YTD Actual",                 options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "YTD Budget",                 options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "Variance",                   options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
  ];

  const cfsRows = [
    { label: "Net Income",                    actual: "$2.43M",    budget: "$2.36M",    section: false },
    { label: "Depreciation & Amortization",   actual: "$591.8K",   budget: "$621.3K",   section: false },
    { label: "Change in Accounts Receivable", actual: "$2.19M",    budget: "-$1.88M",   section: false },
    { label: "Change in Deferred Revenue",    actual: "$232.0K",   budget: "$249.2K",   section: false },
    { label: "Change in Accounts Payable",    actual: "$373.5K",   budget: "$917.7K",   section: false },
    { label: "Change in Prepaids",            actual: "$75.0K",    budget: "$75.0K",    section: false },
    { label: "Cash from Operations (CFO)",    actual: "$5.90M",    budget: "$2.35M",    section: true  },
    { label: "CapEx",                         actual: "-$335.5K",  budget: "-$352.3K",  section: false },
    { label: "Cash from Investing (CFI)",     actual: "-$335.5K",  budget: "-$352.3K",  section: true  },
    { label: "Net Change in Cash",            actual: "$4.96M",    budget: "$1.39M",    section: true  },
    { label: "Ending Cash",                   actual: "$50.26M",   budget: "$48.17M",   section: true  },
  ];

  function calcVar(a, b) {
    // Simple string-based variance display — do not recalculate, just show delta label
    const varMap = {
      "Net Income":                    "+$70.0K",
      "Depreciation & Amortization":   "-$29.5K",
      "Change in Accounts Receivable": "+$4.07M",
      "Change in Deferred Revenue":    "-$17.2K",
      "Change in Accounts Payable":    "-$544.2K",
      "Change in Prepaids":            "$0.0K",
      "Cash from Operations (CFO)":    "+$3.55M",
      "CapEx":                         "+$16.8K",
      "Cash from Investing (CFI)":     "+$16.8K",
      "Net Change in Cash":            "+$3.57M",
      "Ending Cash":                   "+$2.09M",
    };
    return varMap[a] || "—";
  }

  const tableData = [hdr];
  cfsRows.forEach((r, i) => {
    const bg = i % 2 === 0 ? ROW_A : ROW_B;
    const v = calcVar(r.label, null);
    tableData.push([
      { text: r.label, options: { color: r.section ? ACCENT : WHITE, fontSize: 9, fontFace: "Calibri", bold: r.section, align: "left",  fill: { color: bg } } },
      { text: r.actual, options: { color: r.section ? ACCENT : WHITE, fontSize: 9, fontFace: "Calibri", bold: r.section, align: "right", fill: { color: bg } } },
      { text: r.budget, options: { color: MUTED,                       fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: v,        options: { color: varColor(v),                  fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
    ]);
  });

  slide.addTable(tableData, {
    x: 0.3, y: 1.18, w: 12.73, h: 3.6,
    colW: [5.5, 2.4, 2.4, 2.43],
    fill: { color: SURFACE },
    border: { type: "none" },
    rowH: 0.3,
  });

  // Summary note
  slide.addShape(pptx.ShapeType.rect, { x: 0.3, y: 4.95, w: 12.73, h: 0.5, fill: { color: SURFACE }, line: { color: SURFACE } });
  slide.addText("Note: YTD Cash Flow Statement covers Jan–Jun 2026 (6 periods). Stock-based compensation and beginning cash are not available in this period. CFF not applicable.", {
    x: 0.5, y: 5.0, w: 12.33, h: 0.35, fontSize: 9, color: MUTED, fontFace: "Calibri", italic: true
  });

  // Key observations (no KPI cards per archetype)
  addKeyTakeaways(slide, 0.3, 5.6, 12.73, 1.57, [
    "YTD CFO of $5.90M beat budget of $2.35M by +$3.55M, driven by $2.19M favorable AR change vs budget of -$1.88M.",
    "Net income of $2.43M exceeded budget of $2.36M by +$70.0K; D&A of $591.8K was -$29.5K below budget.",
    "YTD ending cash of $50.26M is +$2.09M above budget of $48.17M on the cash flow statement basis.",
  ]);

  addFooter(slide, 6);
})();

// ─── SLIDE 7 — GTM PERFORMANCE ───────────────────────────────────────────────
(function() {
  const slide = pptx.addSlide();
  addBackground(slide);
  addSectionLabel(slide, "GTM PERFORMANCE");
  addTitle(slide, "Go-to-Market Performance", "June 2026  ·  Pipeline, Spend & Efficiency  ·  USD");

  // Channel table
  const hdr = [
    { text: "Channel",          options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: SURFACE } } },
    { text: "Spend (Actual)",   options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "Spend (Budget)",   options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "MQLs",             options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "Pipeline ($M)",    options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "Efficiency",       options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "Win Rate %",       options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
  ];

  const tableData = [hdr];
  // Single channel: Other
  tableData.push([
    { text: "Other",    options: { color: WHITE, fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: ROW_A } } },
    { text: "$0.05M",   options: { color: WHITE, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: ROW_A } } },
    { text: "$0.07M",   options: { color: MUTED, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: ROW_A } } },
    { text: "119",      options: { color: WHITE, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: ROW_A } } },
    { text: "$5.40M",   options: { color: WHITE, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: ROW_A } } },
    { text: "108.0x",   options: { color: ACCENT,fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: ROW_A } } },
    { text: "33.3%",    options: { color: WHITE, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: ROW_A } } },
  ]);
  // Totals row
  tableData.push([
    { text: "Total / Blended", options: { color: ACCENT, fontSize: 9, fontFace: "Calibri", bold: true, align: "left",  fill: { color: ROW_B } } },
    { text: "$0.05M",          options: { color: ACCENT, fontSize: 9, fontFace: "Calibri", bold: true, align: "right", fill: { color: ROW_B } } },
    { text: "$0.07M",          options: { color: MUTED,  fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: ROW_B } } },
    { text: "119",             options: { color: ACCENT, fontSize: 9, fontFace: "Calibri", bold: true, align: "right", fill: { color: ROW_B } } },
    { text: "$5.40M",          options: { color: ACCENT, fontSize: 9, fontFace: "Calibri", bold: true, align: "right", fill: { color: ROW_B } } },
    { text: "108.0x",          options: { color: ACCENT, fontSize: 9, fontFace: "Calibri", bold: true, align: "right", fill: { color: ROW_B } } },
    { text: "33.3%",           options: { color: ACCENT, fontSize: 9, fontFace: "Calibri", bold: true, align: "right", fill: { color: ROW_B } } },
  ]);

  slide.addTable(tableData, {
    x: 0.3, y: 1.18, w: 12.73, h: 1.0,
    colW: [2.2, 1.7, 1.7, 1.3, 1.7, 1.7, 1.43],
    fill: { color: SURFACE },
    border: { type: "none" },
    rowH: 0.3,
  });

  // Pipeline summary table
  const pipeHdr = [
    { text: "Pipeline Metric",     options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: SURFACE } } },
    { text: "CM Actual",           options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "CM Budget",           options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "CM Variance",         options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "YTD Actual",          options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "YTD vs Budget",       options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
  ];
  const pipeRows = [
    ["Pipeline Created (flow)", "$5.40M", "$5.31M", "+$92.8K", "$5.40M", "-79.9%"],
    ["Closed Won",              "$1.80M", "—",       "—",       "—",      "—"],
    ["Pipeline Coverage",       "3.0x",   "—",       "—",       "—",      "—"],
  ];
  const pipeTable = [pipeHdr];
  pipeRows.forEach((r, i) => {
    const bg = i % 2 === 0 ? ROW_A : ROW_B;
    pipeTable.push([
      { text: r[0], options: { color: WHITE,          fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: bg } } },
      { text: r[1], options: { color: WHITE,          fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[2], options: { color: MUTED,          fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[3], options: { color: varColor(r[3]), fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[4], options: { color: WHITE,          fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[5], options: { color: varColor(r[5]), fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
    ]);
  });

  slide.addTable(pipeTable, {
    x: 0.3, y: 2.42, w: 9.5, h: 1.3,
    colW: [2.5, 1.5, 1.5, 1.5, 1.5, 1.0],
    fill: { color: SURFACE },
    border: { type: "none" },
    rowH: 0.3,
  });

  // Efficiency KPI cards
  addKpiCard(slide, 10.08, 2.42, 2.95, 1.2, "108.0x", "Blended Efficiency", "pipeline per $1 spend");
  addKpiCard(slide, 10.08, 3.78, 2.95, 1.2, "33.3%",  "Best Win Rate", "channel: Other");

  // Key Takeaways
  addKeyTakeaways(slide, 0.3, 3.78, 9.5, 2.57, [
    "CM pipeline created of $5.40M beat budget of $5.31M by +$92.8K (+1.7%); YTD pipeline of $5.40M is -79.9% vs budget.",
    "Blended GTM efficiency of 108.0x reflects $5.40M pipeline generated on $0.05M of spend in the month.",
    "119 MQLs generated in June across the Other channel with a 33.3% win rate and $1.80M closed won.",
    "Pipeline coverage of 3.0x provides near-term visibility; slipped pipeline of $9.87M requires Q3 re-staging.",
    "Total GTM spend of $0.05M was -$0.02M below budget of $0.07M; spend efficiency favorable but pipeline YTD gap is material.",
  ]);

  addFooter(slide, 7);
})();

// ─── SLIDE 8 — GTM FUNNEL ────────────────────────────────────────────────────
(function() {
  const slide = pptx.addSlide();
  addBackground(slide);
  addSectionLabel(slide, "GTM FUNNEL");
  addTitle(slide, "Sales Funnel & Channel Summary", "June 2026  ·  MQL → Closed Won  ·  USD");

  // Funnel metrics table
  const funnelHdr = [
    { text: "Funnel Stage",       options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: SURFACE } } },
    { text: "CM Value",           options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "Notes",              options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: SURFACE } } },
  ];
  const funnelRows = [
    ["MQLs Generated",          "119",      "All from Other channel"],
    ["Pipeline Created",        "$5.40M",   "CM actual; budget $5.31M"],
    ["Closed Won",              "$1.80M",   "CM closed won ARR"],
    ["Win Rate",                "33.3%",    "Best channel: Other"],
    ["Pipeline Coverage",       "3.0x",     "vs closed won $1.80M"],
    ["Blended Efficiency",      "108.0x",   "Pipeline per $1 of spend"],
    ["GTM Spend (Actual)",      "$0.05M",   "vs budget $0.07M"],
  ];
  const funnelTable = [funnelHdr];
  funnelRows.forEach((r, i) => {
    const bg = i % 2 === 0 ? ROW_A : ROW_B;
    funnelTable.push([
      { text: r[0], options: { color: WHITE, fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: bg } } },
      { text: r[1], options: { color: ACCENT,fontSize: 9, fontFace: "Calibri", bold: true, align: "right", fill: { color: bg } } },
      { text: r[2], options: { color: MUTED, fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: bg } } },
    ]);
  });

  slide.addTable(funnelTable, {
    x: 0.3, y: 1.18, w: 6.5, h: 2.5,
    colW: [2.5, 1.5, 2.5],
    fill: { color: SURFACE },
    border: { type: "none" },
    rowH: 0.32,
  });

  // YTD pipeline summary
  const ytdHdr = [
    { text: "Pipeline Metric",   options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: SURFACE } } },
    { text: "YTD Actual",        options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "YTD Budget",        options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
    { text: "YTD Variance",      options: { bold: true, color: ACCENT, fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: SURFACE } } },
  ];
  const ytdRows = [
    ["Pipeline Created (flow)", "$5.40M",  "$26.91M", "-$21.51M"],
    ["FY Outlook Pipeline",     "$5.40M",  "$57.03M", "-$51.63M"],
  ];
  const ytdTable = [ytdHdr];
  ytdRows.forEach((r, i) => {
    const bg = i % 2 === 0 ? ROW_A : ROW_B;
    ytdTable.push([
      { text: r[0], options: { color: WHITE,          fontSize: 9, fontFace: "Calibri", align: "left",  fill: { color: bg } } },
      { text: r[1], options: { color: WHITE,          fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[2], options: { color: MUTED,          fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
      { text: r[3], options: { color: varColor(r[3]), fontSize: 9, fontFace: "Calibri", align: "right", fill: { color: bg } } },
    ]);
  });

  slide.addTable(ytdTable, {
    x: 7.1, y: 1.18, w: 5.93, h: 1.0,
    colW: [2.3, 1.2, 1.2, 1.23],
    fill: { color: SURFACE },
    border: { type: "none" },
    rowH: 0.3,
  });

  // KPI cards right
  addKpiCard(slide, 7.1,  2.35, 2.85, 1.2, "119",     "MQLs (CM)", "Other channel");
  addKpiCard(slide, 10.18,2.35, 2.85, 1.2, "$1.80M",  "Closed Won (CM)", "win rate 33.3%");

  // Key Takeaways
  addKeyTakeaways(slide, 0.3, 3.85, 12.73, 2.57, [
    "119 MQLs generated in June 2026 from the Other channel, converting at a 33.3% win rate to $1.80M closed won.",
    "CM pipeline of $5.40M beat budget of $5.31M by +$92.8K; YTD pipeline of $5.40M is -$21.51M (-79.9%) behind budget.",
    "Pipeline coverage of 3.0x on $1.80M closed won; slipped pipeline of $9.87M requires Q3 re-staging with owners.",
    "FY 2026 pipeline outlook of $5.40M is -$51.63M (-90.5%) below FY budget of $57.03M — a critical gap to address.",
    "GTM spend of $0.05M vs budget of $0.07M was favorable; efficiency of 108.0x reflects high pipeline yield per dollar.",
  ]);

  addFooter(slide, 8);
})();

// ─── SLIDE 9 — STRATEGIC ASSESSMENT ──────────────────────────────────────────
(function() {
  const slide = pptx.addSlide();
  addBackground(slide);
  addSectionLabel(slide, "STRATEGIC ASSESSMENT");
  addTitle(slide, "Risks & Opportunities", "Q2 2026  ·  Medium-priority items requiring board awareness");

  const risks = [
    {
      type: "RISK",
      title: "Deferred Pipeline",
      detail: "Slipped pipeline of $9.87M requires Q3 coverage review and re-staging of opportunities with validated next steps and owners.",
      level: "MEDIUM",
    },
    {
      type: "RISK",
      title: "Revenue vs Budget",
      detail: "Revenue trailed budget by -$110.2K (-4.8%) in June. Validate expansion timing and churn pockets before next board distribution.",
      level: "MEDIUM",
    },
  ];

  const opps = [
    {
      type: "OPP",
      title: "Cash Forecast Upside",
      detail: "Ending cash of $48.43M is +$16.98M (+54