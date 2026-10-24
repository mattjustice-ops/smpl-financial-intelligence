// SMPL MD&A package export: every view x comparison with approved one-paragraph commentary, net income walks,
// labor bridges, the next-month watch list, last month's scoring, tie-outs and the package stamp.
// Output: a JSON package that the workbook renderer (build_mdna_workbook.py) lays out. Amounts in integer cents.
const fs = require("fs");
const crypto = require("crypto");
const { makeEngine } = require("./flux_engine.js");
const { makeUi } = require("./flux_ui.js");

const dir = process.argv[2] || "./flux_export";
const D = JSON.parse(fs.readFileSync(dir + "/flux_data.json", "utf8"));
const E = makeEngine(D), U = makeUi(E, D);
const P = D.last;                                   // the closed month the package is for (Aug 2026)
const M = D.months;

// ---------------------------------------------------------------------------------------------
// Comparisons in the package
// ---------------------------------------------------------------------------------------------
const COMPS = [
  { key: "MOM", short: "MoM", tab: "MoM", c: E.comparison(P, "MOM") },
  { key: "QOQ", short: "QoQ", tab: "QoQ", c: E.comparison(P, "QOQ") },
  { key: "YOY", short: "YoY", tab: "YoY", c: E.comparison(P, "YOY") },
  { key: "YTD", short: "YTD", tab: "YTD", c: E.comparison(P, "YTD") },
  { key: "BUD_M", short: "vs Budget (month)", tab: "Budget M", c: E.comparison(P, "PLAN", "B26_V1", "MONTH") },
  { key: "BUD_YTD", short: "vs Budget (YTD)", tab: "Budget YTD", c: E.comparison(P, "PLAN", "B26_V1", "YTD") },
  { key: "FC_M", short: "vs Forecast 7+5 (month)", tab: "Forecast M", c: E.comparison(P, "PLAN", "F26_7P5", "MONTH") },
];
const VIEWS = [["IS", "Income statement"], ["MP", "Management P&L"], ["GL", "GL detail"], ["BS", "Balance sheet"], ["CF", "Cash flow"]];
const APPROVER = { by: "J. Patel, Controller", at: "2026-09-10" };
const REVIEWER = { MOM: ["MC", "2026-09-08"], QOQ: ["MC", "2026-09-09"], YOY: ["MC", "2026-09-09"], YTD: ["MC", "2026-09-09"],
  BUD_M: ["AR", "2026-09-09"], BUD_YTD: ["AR", "2026-09-09"], FC_M: ["AR", "2026-09-09"] };

// The reviewer's explanation of the uncategorized journal (the Needs-explanation edit) in every paragraph that flags it.
function explainJournal(text) {
  return text
    .replace(/JE-2026-08-114 needs an explanation before review\./, "Reviewer: JE-2026-08-114 is the August outside-legal accrual true-up; it has been recategorized to outside legal.")
    .replace(/Other items include journal JE-2026-08-114, posted without a category; it needs an explanation before review\./,
      "Other items include JE-2026-08-114, the August outside-legal accrual true-up, since recategorized to outside legal.");
}

// Rows in presentation order: statement lines, with GL lines beneath the lines built from them.
function rowsFor(view) {
  const T = U.tree(view).nodes, out = [];
  const inLayout = new Set(U.LAYOUT[view].map((x) => x[0]));
  for (const [nid, depth, style] of U.LAYOUT[view]) {
    out.push({ nid, level: 0, style });
    const n = T[nid];
    if (n.kind === "leaf") continue;
    const kids = Object.keys(n.children);
    if (kids.every((k) => T[k].kind === "leaf")) for (const k of kids) if (!inLayout.has(k)) out.push({ nid: k, level: 1, style: "leaf" });
  }
  return out;
}

// Future impacts for a line as of the close: next month's effect on the line, its items, then later months; plus
// how the impacts noted at the prior close played out (leaves). Same for every comparison of the package.
const IMP = {}; for (const v of ["GL", "IS", "MP"]) IMP[v] = E.impactsByNode(v, P);
const SCORES = E.scoreImpacts(P);
const FUT = {}; for (const it of D.future) FUT[it.id] = it;
const mon = (p) => E.mlabel(M.indexOf(p)).slice(0, 3);
function impactText(view, nid) {
  if (!IMP[view]) return null;
  const T = U.tree(view).nodes, imp = IMP[view], nx = M[P + 1];
  const coefs = {};
  const walkL = (x, cf) => { const n = T[x]; if (n.kind === "leaf") coefs[x] = (coefs[x] || 0) + cf; else for (const k in n.children) walkL(k, cf * n.children[k]); };
  walkL(nid, 1);
  const groups = {}, order = [];
  for (const leaf in coefs) for (const e of imp.lists[leaf] || []) {
    const it = FUT[e.id], g = it.group || it.id;
    if (!groups[g]) { groups[g] = { it, amt: {} }; order.push(g); }
    for (const p in e.amt) groups[g].amt[p] = (groups[g].amt[p] || 0) + coefs[leaf] * e.amt[p];
  }
  const next = [], later = [];
  for (const g of order) {
    const x = groups[g], ps = Object.keys(x.amt).filter((p) => x.amt[p]).sort();
    if (!ps.length) continue;
    const tag = x.it.status === "Open" ? "; suggested" : "";
    if (x.amt[nx]) next.push({ t: x.it.title + " (" + U.fmtK(x.amt[nx], true) + "k" + tag + ")", o: -Math.abs(x.amt[nx]) });
    else {
      const vals = ps.map((p) => x.amt[p]), same = vals.every((v) => v === vals[0]);
      const when = ps.length === 1 ? mon(ps[0]) : same ? mon(ps[0]) + " on" : mon(ps[0]) + "–" + mon(ps[ps.length - 1]);
      const a = ps.length === 1 ? U.fmtK(vals[0], true) + "k" : same ? U.fmtK(vals[0], true) + "k/mo" : U.fmtK(vals.reduce((q, r) => q + r, 0), true) + "k total";
      later.push({ t: x.it.title + " (" + when + ", " + a + tag + ")", o: ps[0] });
    }
  }
  next.sort((a, b) => a.o - b.o); later.sort((a, b) => (a.o < b.o ? -1 : a.o > b.o ? 1 : 0));
  const total = imp.res[nid][nx] || 0;
  const parts = [];
  if (next.length) parts.push(mon(nx) + " " + U.fmtK(total, true) + "k: " + next.slice(0, 3).map((x) => x.t).join("; ") + (next.length > 3 ? "; and " + (next.length - 3) + " more" : "") + ".");
  if (later.length) parts.push("Later: " + later.slice(0, 2).map((x) => x.t).join("; ") + (later.length > 2 ? "; and " + (later.length - 2) + " more" : "") + ".");
  if (T[nid].kind === "leaf") {
    const sel = T[nid].sel.slice(0, 2).join("|");
    const sc = SCORES.filter((x) => D.views.GL.nodes[x.line].sel.slice(0, 2).join("|") === sel);
    if (sc.length) parts.push("Noted at " + E.mlabel(P - 1).slice(0, 3) + " close: " + sc.map((x) => x.title + ", " + x.outcome.toLowerCase() + " (expected " + U.fmtK(x.expected, true) + "k, actual " + U.fmtK(x.actual, true) + "k)").join("; ") + ".");
  }
  return { nextTotal: total, text: parts.join(" ") };
}
const IMPACT_CACHE = {};

function lineRecord(view, comp, res, nid, level, style) {
  const T = U.tree(view).nodes, node = T[nid], r = res[nid];
  const { tpl, disp } = U.draft(view, nid, r, comp.c, res);
  let text = U.segments(tpl, r, disp).map((s) => s.t).join("");
  let source = "Template";
  const explained = explainJournal(text);
  let tplFinal = tpl, unmatched = [];
  if (explained !== text) {
    const rt = U.retokenize(explained, r, disp);
    tplFinal = rt.tpl; unmatched = rt.unmatched; text = explained; source = "Edited by reviewer";
  }
  let ex = 0; for (const i of r.items) ex += i.amount;
  let lx = 0; for (const rw of disp.rows) lx += rw.exact;
  let rollOk = true;
  if (node.kind !== "leaf") {
    let sv = 0, sc = 0;
    for (const k in node.children) { sv += node.children[k] * res[k].var; sc += node.children[k] * res[k].cur; }
    rollOk = sv === r.var && sc === r.cur;
  }
  const tc = U.tieCheck(tplFinal, disp);
  const inScope = E.required(view, node, r) || (view === "GL" && node.kind === "leaf" && r.items.some((i) => i.cat === "UNATTRIBUTED"));
  const [rb, ra] = REVIEWER[comp.key];
  return {
    nid, label: node.label, level, style, kind: node.kind, sign: node.sign,
    children: node.kind === "leaf" ? [] : Object.entries(node.children),
    cur: r.cur, cmp: r.cmp, var: r.var, varShown: disp.target, fu: U.fav(node, r), text, source,
    drivers: disp.rows.map((rw) => ({ label: rw.item && rw.item.cat === "LINE" ? U.sentenceLabel(rw.label) : rw.label, shown: rw.shown, exact: rw.exact })),
    lineBased: U.isLineBased(view, nid),
    inScope, reviewedBy: inScope ? rb : null, reviewedAt: inScope ? ra : null,
    impact: (IMPACT_CACHE[view + "|" + nid] = IMPACT_CACHE[view + "|" + nid] || impactText(view, nid)),
    driversOk: ex === r.var && lx === r.var, rollOk, paraOk: tc.ok && !unmatched.length
  };
}

// Net income walk by component lines (formulas flattened): comparison NI + steps = current NI.
function walk(view, res) {
  const T = U.tree(view).nodes, root = D.views[view].root, out = [];
  const comp = (x, cf) => { for (const k in T[x].children) { const c = cf * T[x].children[k]; if (T[k].kind === "formula") comp(k, c); else out.push({ nid: k, label: T[k].label, coef: c, step: c * res[k].var }); } };
  comp(root, 1);
  return { start: res[root].cmp, end: res[root].cur, steps: out };
}

// ---------------------------------------------------------------------------------------------
// Statement checks for the sign-off (T27)
// ---------------------------------------------------------------------------------------------
function statementChecks(c, all) {
  const same = (a, b) => a.cur === b.cur && a.cmp === b.cmp;
  const out = [];
  const gl = all.GL, is = all.IS, mp = all.MP, bs = all.BS, cf = all.CF;
  out.push({ t: "Net income agrees: GL = income statement = management P&L", ok: same(gl["GL.NI"], is["IS.NI"]) && same(is["IS.NI"], mp["MP.NI"]) });
  out.push({ t: "Allocations net to zero (operating income agrees across views)", ok: same(is["IS.OI"], mp["MP.OI"]) && same(gl["GL.OI"], is["IS.OI"]) });
  if (bs) out.push({ t: "Balance sheet balances (assets = liabilities + equity)", ok: same(bs["BS.TA"], bs["BS.TLE"]) });
  else out.push({ t: "Balance sheet: not in " + D.plans[c.version].label, na: true });
  if (cf) {
    const first = c.cur[0], last = c.cur[c.cur.length - 1];
    const cash = E.computeBs(E.comparison(last, "CUSTOM", null, null, first - 1));
    out.push({ t: "Cash flow ties to the change in cash; cash-flow net income = income statement", ok: cash["BS.1000"].var === cf["CF.NET"].cur && cf["CF.NI"].cur === is["IS.NI"].cur });
  } else out.push({ t: "Cash flow: not in " + D.plans[c.version].label, na: true });
  return out;
}

// ---------------------------------------------------------------------------------------------
// Executive summary: written by the AI from approved lines; validated (numbers only via tokens) and tied
// (every net-income component cited once, so the cited amounts add up to the net income change).
// Tokens: {{Lk}} signed variance, {{Lk_abs}} unsigned, {{Lk.pct_abs}} unsigned %, {{Lk.dN}} displayed driver N of line k.
// ---------------------------------------------------------------------------------------------
const SUMMARY_LINES = [["IS", "IS.NI"], ["IS", "IS.REV.TOTAL"], ["IS", "IS.COR.TOTAL"], ["IS", "IS.OPX.TOTAL"], ["IS", "IS.OPX.SM"],
  ["IS", "IS.OPX.RD"], ["IS", "IS.OPX.GA"], ["GL", "GL.COMP"], ["IS", "IS.GP"], ["MP", "MP.CM2"]];
function summaryPacket(comp, all, recs) {
  return SUMMARY_LINES.map(([v, nid], i) => {
    const rec = recs[v].find((x) => x.nid === nid);
    const r = all[v][nid];
    const { disp } = U.draft(v, nid, r, comp.c, all[v]);
    return { id: "L" + (i + 1), view: v, nid, label: rec.label, rec, r, disp };
  });
}
const STOKEN = /\{\{L(\d+)(_abs)?(?:\.(pct_abs|d\d+))?\}\}/g;
function renderSummary(tpl, packet) {
  return tpl.replace(STOKEN, (m, k, abs, sub) => {
    const L = packet[parseInt(k, 10) - 1];
    if (!L) return "[?]";
    if (!sub) return abs ? U.fmtK(Math.abs(L.disp.target), false) + "k" : U.fmtK(L.disp.target, true) + "k";
    if (sub === "pct_abs") return U.pctStr(Math.abs(L.r.var), L.r.cmp).replace("+", "");
    const rw = L.disp.rows[parseInt(sub.slice(1), 10) - 1];
    return rw ? U.fmtK(rw.shown, true) + "k" : "[?]";
  });
}
function checkSummary(tpl, packet) {
  const errs = [];
  let m;
  const re = new RegExp(STOKEN.source, "g");
  const seenNi = {};
  while ((m = re.exec(tpl))) {
    const k = parseInt(m[1], 10), L = packet[k - 1];
    if (!L) { errs.push("unknown line L" + k); continue; }
    if (!L.rec.reviewedBy && L.rec.inScope) errs.push(L.label + " is not approved");
    if (m[3] && m[3][0] === "d" && !L.disp.rows[parseInt(m[3].slice(1), 10) - 1]) errs.push("unknown driver " + m[0]);
    if (k === 1 && m[3] && m[3][0] === "d") { const n = parseInt(m[3].slice(1), 10); if (seenNi[n]) errs.push("net income component cited twice"); seenNi[n] = true; }
  }
  const ni = packet[0];
  let sum = 0;
  for (const rw of ni.disp.rows) { if (rw.shown === 0) continue; if (!seenNi[rw.idx]) errs.push("net income component d" + rw.idx + " not cited"); else sum += rw.shown; }
  if (!errs.length && sum !== ni.disp.target) errs.push("cited components don't add up to the net income change");
  // numbers outside tokens: same rule as line commentary
  const vocab = packet.map((L) => U.vocabFor(L.nid, L.view, L.r, L.disp)).join(" | ");
  const [ok, why] = E.validateAiText(tpl.replace(new RegExp(STOKEN.source, "g"), " "), [], vocab);
  if (!ok) errs.push(why);
  return { ok: !errs.length, errs, sum, target: ni.disp.target };
}

// ---------------------------------------------------------------------------------------------
// Build
// ---------------------------------------------------------------------------------------------
const summaries = fs.existsSync("./exec_summaries.json") ? JSON.parse(fs.readFileSync("./exec_summaries.json", "utf8")) : {};
const pkg = { comparisons: [] };
const dump = process.argv.includes("--dump");
for (const comp of COMPS) {
  const c = comp.c, cid = E.compId(c);
  const all = {}, recs = {};
  for (const [v] of VIEWS) {
    const res = U.results(v, c);
    all[v] = res;
    recs[v] = res ? rowsFor(v).map((x) => lineRecord(v, comp, res, x.nid, x.level, x.style)) : null;
  }
  const walks = { IS: walk("IS", all.IS), MP: walk("MP", all.MP) };
  const checks = statementChecks(c, all);
  let lines = 0, drvBad = 0, rollBad = 0, paraBad = 0, scope = 0;
  for (const [v] of VIEWS) if (recs[v]) for (const x of recs[v]) { lines++; if (!x.driversOk) drvBad++; if (!x.rollOk) rollBad++; if (x.inScope) { scope++; if (!x.paraOk) paraBad++; } }
  checks.unshift({ t: "Commentary amounts add up to each variance · " + scope + " lines in scope", ok: paraBad === 0 });
  checks.unshift({ t: "Roll-ups equal the sum of their lines", ok: rollBad === 0 });
  checks.unshift({ t: "Drivers sum to every line's variance · " + lines + " lines", ok: drvBad === 0 });
  const packet = summaryPacket(comp, all, recs);
  if (dump) {
    console.log("\n=== " + comp.short + " · " + c.label + " ===");
    for (const L of packet) console.log("  " + L.id + " " + L.label + "  var " + U.fmtK(L.disp.target, true) + "k  rows: " +
      L.disp.rows.map((rw) => "d" + rw.idx + " " + (rw.item && rw.item.cat === "LINE" ? U.sentenceLabel(rw.label) : rw.label) + " " + U.fmtK(rw.shown, true)).join(" | ") + "\n      " + L.rec.text);
  }
  const st = summaries[comp.key];
  let summary = null;
  if (st) {
    const chk = checkSummary(st, packet);
    summary = { tpl: st, text: renderSummary(st, packet), ok: chk.ok, errs: chk.errs, sum: chk.sum, target: chk.target,
      cited: packet[0].disp.rows.filter((rw) => rw.shown !== 0).map((rw) => ({ label: U.sentenceLabel(rw.label), shown: rw.shown })) };
  }
  const kpi = (v, nid) => ({ label: U.tree(v).nodes[nid].label, cur: all[v][nid].cur, cmp: all[v][nid].cmp, var: all[v][nid].var, fu: U.fav(U.tree(v).nodes[nid], all[v][nid]) });
  pkg.comparisons.push({
    key: comp.key, short: comp.short, tab: comp.tab, label: c.label, cid,
    curLabel: c.cur.length === 1 ? E.mlabel(c.cur[0]) : (c.preset === "QOQ" ? "Jul–Aug 2026" : "YTD Aug 2026"),
    cmpLabel: c.scn !== "ACT" ? D.plans[c.version].label + (c.basis === "YTD" ? " YTD" : "") : c.cmp.length === 1 ? E.mlabel(c.cmp[0]) : (c.preset === "QOQ" ? "Apr–May 2026" : "YTD Aug 2025"),
    bsLabels: c.bs ? [E.mlabel(c.bs[0]), c.bs[1] >= 0 ? E.mlabel(c.bs[1]) : "Opening"] : null,
    views: Object.fromEntries(VIEWS.map(([v, label]) => [v, recs[v] ? { label, rows: recs[v] } : { label, rows: null, na: "Not in " + D.plans[c.version].label }])),
    walks, checks, allOk: checks.every((x) => x.ok || x.na),
    approval: { status: "Approved", by: APPROVER.by, at: APPROVER.at, reviewed: scope, inScope: scope },
    kpis: [kpi("IS", "IS.REV.TOTAL"), kpi("IS", "IS.GP"), kpi("IS", "IS.OPX.TOTAL"), kpi("IS", "IS.OI"), kpi("IS", "IS.NI"), kpi("MP", "MP.CM2")],
    summary
  });
}

// Labor bridges (§18): company bars roll hires, departures and mix into Headcount & mix; departments keep them.
function laborBridge(key, cKey) {
  const L = D.labor[key];
  const comp = pkg.comparisons.find((x) => x.key === cKey);
  const gl = comp.views.GL.rows;
  const depts = Object.keys(L);
  const ORDER = ["HIRES", "DEPARTURES", "OPENING_HC", "MIX", "TRANSFERS_NET", "RATE", "TIMING", "BENEFITS_TAXES", "ONE_TIME", "GL_RECON"];
  const byDept = depts.map((d) => {
    const row = gl.find((x) => x.nid === "GL.6000." + d);
    return { dept: d, name: D.dept_name[d] || d, start: row.cmp, end: row.cur, bars: ORDER.filter((b) => L[d][b]).map((b) => ({ key: b, label: D.lab_label[b], amt: L[d][b] })) };
  });
  const roll = {};
  for (const d of depts) for (const b in L[d]) { const k = D.lab_rollup[b] || b; roll[k] = (roll[k] || 0) + L[d][b]; }
  const CO = ["HEADCOUNT_MIX", "RATE", "TIMING", "BENEFITS_TAXES", "ONE_TIME", "GL_RECON"];
  const comp6000 = gl.find((x) => x.nid === "GL.COMP");
  const company = { start: comp6000.cmp, end: comp6000.cur, bars: CO.filter((b) => roll[b]).map((b) => ({ key: b, label: D.lab_label[b], amt: roll[b] })) };
  let s = company.start; for (const b of company.bars) s += b.amt;
  return { key, title: cKey === "MOM" ? "Compensation bridge, Jul 2026 → Aug 2026" : "Compensation bridge, Budget 2026 v1 → Aug 2026 actual",
    company, byDept, ties: s === company.end && byDept.every((d) => d.bars.reduce((a, b) => a + b.amt, d.start) === d.end) };
}
pkg.labor = [laborBridge("MOM", "MOM"), laborBridge("B26_V1", "BUD_M")];

// Watch list: future impacts as of the close (months after it), by line and month, with the net income effect.
{
  const imp = E.impactsByNode("GL", P);
  const T = D.views.GL.nodes;
  const months = [];
  for (let i = P + 1; i < M.length; i++) months.push(M[i]);
  const items = [];
  for (const it of D.future) {
    if (it.as_of > P || it.status === "Dismissed") continue;
    const ps = Object.keys(it.periods).filter((p) => p > M[P]);
    if (!ps.length) continue;
    const nid = Object.keys(T).find((k) => T[k].kind === "leaf" && T[k].sel[0] === it.leaf[0] && T[k].sel[1] === it.leaf[1]);
    const income = T[nid].sign === "INCOME";
    items.push({ id: it.id, group: it.group || it.id, title: it.title, line: T[nid].label, nid, type: it.type, source: it.source, status: it.status === "Open" ? "Suggested" : it.status,
      confidence: it.confidence, owner: it.owner, detail: it.detail || "", amounts: Object.fromEntries(ps.map((p) => [p, it.periods[p]])), niSign: income ? 1 : -1 });
  }
  pkg.watch = { asOf: E.mlabel(P), months: months.map((p) => ({ key: p, label: E.mlabel(M.indexOf(p)) })), items, niByMonth: imp.res["GL.NI"] };
}
// Last month's watch list, scored at this close.
{
  const sc = E.scoreImpacts(P);
  const by = E.scoreSummary(sc);
  let ea = 0, er = 0; for (const x of sc) { ea += Math.abs(x.expected); er += Math.abs(x.actual - x.expected); }
  pkg.scoring = { notedAt: E.mlabel(P - 1), month: E.mlabel(P), items: sc.map((x) => Object.assign({}, x, { lineLabel: D.views.GL.nodes[x.line].label })),
    byOwner: by, accuracyBp: ea ? Math.max(0, 10000 - Math.floor((er * 10000 + ea - 1) / ea)) : null };
}
// Package stamp: content hash over every amount and paragraph; the platform marks the package Replaced if any
// comparison in it is reopened after export.
{
  const h = crypto.createHash("sha256");
  for (const c of pkg.comparisons) for (const v in c.views) if (c.views[v].rows) for (const r of c.views[v].rows) h.update([c.cid, v, r.nid, r.cur, r.cmp, r.text].join("|"));
  const digest = h.digest("hex");
  pkg.stamp = {
    packageId: "MDA-US01-2026-08-001", entity: "US01", book: "GAAP_PRIMARY", currency: "USD", snapshot: "SNAP-US01-2026-08-003",
    period: E.mlabel(P), generatedAt: "2026-10-07 10:30 PT", generatedBy: "SMPL MD&A export v1", contentHash: digest.slice(0, 16),
    status: pkg.comparisons.every((c) => c.approval.status === "Approved") ? "Approved" : "Draft", approver: APPROVER
  };
}
const out = process.argv.includes("--out") ? process.argv[process.argv.indexOf("--out") + 1] : null;
if (out) { fs.writeFileSync(out, JSON.stringify(pkg)); console.log("wrote " + out); }
// Checks
let bad = 0;
for (const c of pkg.comparisons) {
  if (!c.allOk) { bad++; console.log("CHECK FAIL", c.short, c.checks.filter((x) => !x.ok && !x.na).map((x) => x.t)); }
  if (c.summary && !c.summary.ok) { bad++; console.log("SUMMARY FAIL", c.short, c.summary.errs); }
  for (const w of ["IS", "MP"]) { const W = c.walks[w]; let s = W.start; for (const x of W.steps) s += x.step; if (s !== W.end) { bad++; console.log("WALK FAIL", c.short, w); } }
}
for (const l of pkg.labor) if (!l.ties) { bad++; console.log("LABOR FAIL", l.key); }
// The summary checker must reject a typed amount, a missing net-income component and a line that does not exist.
{
  const comp = COMPS[0], all = {}, recs = {};
  for (const [v] of VIEWS) { all[v] = U.results(v, comp.c); recs[v] = rowsFor(v).map((x) => lineRecord(v, comp, all[v], x.nid, x.level, x.style)); }
  const pk = summaryPacket(comp, all, recs);
  const neg = [
    ["typed amount", "Net income fell 39.2k vs Jul 2026: {{L1.d1}}, {{L1.d2}}, {{L1.d3}}, {{L1.d4}}."],
    ["missing component", "Net income fell {{L1_abs}}: {{L1.d1}}, {{L1.d2}} and {{L1.d3}}."],
    ["unknown line", "Net income fell {{L1_abs}}: {{L1.d1}}, {{L1.d2}}, {{L1.d3}}, {{L1.d4}}; see {{L42}}."]
  ];
  for (const [name, t] of neg) { const r = checkSummary(t, pk); if (r.ok) { bad++; console.log("SUMMARY CHECK MISSED", name); } else console.log("summary checker rejects " + name + ": " + r.errs[0]); }
}
console.log("comparisons " + pkg.comparisons.length + ", rows " + pkg.comparisons.reduce((a, c) => a + Object.values(c.views).reduce((b, v) => b + (v.rows ? v.rows.length : 0), 0), 0) +
  ", summaries " + pkg.comparisons.filter((c) => c.summary).length + "/" + pkg.comparisons.length + " (" + pkg.comparisons.filter((c) => c.summary && c.summary.ok).length + " valid), labor bridges tie: " + pkg.labor.every((l) => l.ties) + ", failures " + bad);
process.exit(bad ? 1 : 0);
