/**
 * Budget Analytics (Plan Assurance predictive) shows only dollars the plan or the stress suite produced:
 *  - lever ledger rows come from live stress cases; upside only where a sensitivity run measured it;
 *  - offsets size only the program-spend cut (the risk policy share of loaded FY program spend); the rest read "not estimated";
 *  - rails and levers come from the risk policy; an unanswered one is reported as not set;
 *  - the corridor fan is the Monte Carlo monthly cash percentiles, or no fan before scenarios run;
 *  - no detection-latency registry, typed offset amplitudes, typed lever rows or cushion-scaled fallbacks.
 *
 * Usage: node scripts/verify-budget-analytics-from-data.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, '..');

let failed = 0;
function check(name, ok, detail = '') {
  if (ok) console.log(`  ok  ${name}`);
  else {
    failed += 1;
    console.error(`  FAIL ${name}${detail ? ` — ${detail}` : ''}`);
  }
}

const be = fs.readFileSync(path.join(root, 'public/budget-engine/index.html'), 'utf8');

function fnSource(src, name) {
  const start = src.indexOf(`function ${name}(`);
  if (start < 0) return null;
  let depth = 0;
  for (let i = src.indexOf('{', start); i < src.length; i++) {
    if (src[i] === '{') depth += 1;
    else if (src[i] === '}' && --depth === 0) return src.slice(start, i + 1);
  }
  return null;
}

console.log('no invented Analytics dollars');
check('detection-latency registry removed', !/PA_LEVER_LATENCY|paLatencyModel|renderPaLatency/.test(be));
check('no typed offset amplitudes', !/3\.2 \* scale|2\.4 \* scale|3\.3 \* scale|1\.9 \* scale/.test(be));
check('no cushion-scaled lever band or fallbacks', !/function paCaseDnM|band \* 0\.\d+|cush \* 0\.18/.test(be));
check('no typed flat lever rows', !/dn: -0\.9, up: 0\.8|dn: -0\.6, up: 0\.5|dn: -0\.5, up: 0\.6/.test(be));
check('no mirrored upside multiplier', !/Math\.abs\((dn|winDn|churnDn|attrDn|growthDn|cplDn)\) \* 0\.\d+/.test(be));
check('no typed illustrative cash fan', !/function approxCashBands|dec \* 0\.28|outer \* 0\.42/.test(be));
check('no typed CPL trip fallback', !/\/ 100\)\)\) : 24/.test(be));
check('no typed +3.9pp attrition trip', !/\+3\.9pp/.test(be));
check('no dead no-op renderers', !/function renderPa(StressLanding|Tolerance|CashTolerance|StressTiming|StartCurve|CashStartCurve|DecisionCards|DurationGrid|CashDuration)\(/.test(be));

const names = ['paPolicy', 'paPolicyNotSet', 'paPolicyPct', 'paPolicyGaps', 'paPolicyLeversTxt', 'paFindCase', 'buildCraftLevers', 'paMcCashFan', 'renderPaOffsets', 'renderPaTrips', 'buildMonthlyCashBands', 'pctlSorted',
  'salesAttritionRates', 'salesAttritionLabel'];
const sources = names.map(n => fnSource(be, n));
check('functions found', sources.every(Boolean), names.filter((n, i) => !sources[i]).join(', '));

const measuredAttr = {
  window: ['2025-07', '2026-06'],
  nb: { exits: 2, avg_heads: 16.75, rate: 2 / 16.75 },
  cs: { exits: 0, avg_heads: 12.33, rate: 0 },
  combined: { exits: 2, avg_heads: 29.08, rate: 2 / 29.08 },
};
let teamInputs = { attrition: measuredAttr };
const ctx = {
  STATE: { salesAttritionPct: null, _attrShockPp: 0 },
  BUD_P: Array.from({ length: 12 }, (_, i) => `2027-${String(i + 1).padStart(2, '0')}`),
  salesTeamInputs: () => teamInputs,
  policy: { cash_watch_shortfall: 0.25, cash_alarm_shortfall: 0.5, program_cut: 0.15, dso_improvement_days: 5 },
};
ctx.window = { SMPLOutlook: {
  getRiskPolicyValue: (k) => (ctx.policy[k] ?? null),
  riskPolicyNotSet: (k) => `Risk policy not set (${k})`,
} };
vm.runInNewContext(`${sources.join('\n')}
  this.api = { buildCraftLevers, paMcCashFan, renderPaOffsets, renderPaTrips, buildMonthlyCashBands, salesAttritionRates };`, ctx);
const api = ctx.api;

console.log('lever ledger from the live suite');
check('no suite → no levers', api.buildCraftLevers(null).length === 0);
const suite = {
  cases: [
    { id: 'cpl_p15', dCash: -1.2e6, status: 'hold' },
    { id: 'cpl_p30', dCash: -2.5e6, status: 'watch' },
    { id: 'churn_x14', dCash: -0.4e6, status: 'hold' },
  ],
  sens: { cpl: [{ x: 0.85, dCash: 1.1e6 }, { x: 1.0, dCash: 0 }], yoy: [{ x: 3, dCash: -0.8e6 }] },
};
const levers = api.buildCraftLevers(suite);
check('only levers with a live case are shown', levers.length === 2, levers.map(l => l.tech).join(', '));
const cpl = levers.find(l => l.tech === 'Blended CPL');
check('CPL downside = worst of its live cases', cpl && Math.abs(cpl.dn - -2.5) < 1e-9, cpl && String(cpl.dn));
check('CPL upside = measured −15% sensitivity', cpl && Math.abs(cpl.up - 1.1) < 1e-9 && cpl.tier === 'break');
const churn = levers.find(l => l.tech === 'Churn mix ×1.4');
check('no sensitivity → upside null, hold case → flat', churn && churn.up === null && churn.tier === 'flat');

console.log('offsets and trips from loaded plan');
const live = { plan: Array(12).fill(30), floor: 10, spend: Array(12).fill(1) };
const off = api.renderPaOffsets(live, 'plain');
check('program cut sized at the policy 15% of loaded FY program spend', /\+1\.8M/.test(off) && /Program spend cut = 15% \(risk policy\)/.test(off));
check('other offsets not estimated', (off.match(/not estimated/g) || []).length === 2);
check('DSO lever reads the policy days; no unsized renewal-pricing row', /Collect 5 days faster/.test(off) && !/renewal pricing/i.test(off));
ctx.policy = {};
const offUnset = api.renderPaOffsets(live, 'plain');
check('program cut not set → not sized, and said so', !/\+\d/.test(offUnset) && /Program spend cut not sized: Risk policy not set \(program_cut\)/.test(offUnset));
const tripsUnset = api.renderPaTrips(live, 'tech');
check('rails not set → floor-only cash trip', /min\(cash\) < floor/.test(tripsUnset) && !/endCash ≤/.test(tripsUnset)
  && /Risk policy not set \(cash_watch_shortfall\)/.test(tripsUnset));
ctx.policy = { cash_watch_shortfall: 0.25, cash_alarm_shortfall: 0.5, program_cut: 0.15, dso_improvement_days: 5 };
check('cash trip reads the policy rails and levers', /Dec cash vs −25% \/ −50% \/ floor/.test(api.renderPaTrips(live, 'tech'))
  && /endCash ≤ 75% of plan/.test(api.renderPaTrips(live, 'tech')) && /Program spend −15%, HC defer, DSO −5 days/.test(api.renderPaTrips(live, 'tech')));
const noFloor = api.renderPaOffsets({ ...live, floor: null, spend: [] }, 'plain');
check('no spend and no floor → nothing sized, flagged', !/\+\d/.test(noFloor) && /not loaded/.test(noFloor) && /No cash floor loaded/.test(noFloor));
const trips = api.renderPaTrips(live, 'plain');
check('CPL trip threshold from cushion ÷ spend, no 15–40% clamp', /~167% over plan/.test(trips) && !/Math\.max\(15, Math\.min\(40/.test(be));
check('attrition trip reads each group\'s measured rate', /planned attrition \(closers 11\.9% · CS 0\.0%\)/.test(trips));

console.log('sales / CS attrition from the loaded roster');
check('no typed 5% attrition default', !/salesAttritionPct: 5\b/.test(be) && /salesAttritionPct: null,/.test(be));
check('stress cases shock on top of the plan rate, never from a 0 base', !/\(STATE\.salesAttritionPct \|\| 0\) \+/.test(be)
  && !/snap\.salesAttritionPct \|\| 0/.test(be));
check('attrition stress cases only run when attrition is measured',
  (be.match(/needsAttrition: true/g) || []).length === 2 && /\.filter\(d => !d\.needsAttrition \|\| attrMeasured\)/.test(be));
let r = api.salesAttritionRates();
check('measured: closers and CS each at their own rate', r.source === 'measured' && Math.abs(r.nb - 200 / 16.75) < 1e-9 && r.cs === 0);
ctx.STATE._attrShockPp = 4;
r = api.salesAttritionRates();
check('stress adds percentage points to each group', Math.abs(r.nb - (200 / 16.75 + 4)) < 1e-9 && r.cs === 4);
ctx.STATE._attrShockPp = -1;
check('a negative draw never takes a group below 0%', api.salesAttritionRates().cs === 0);
ctx.STATE._attrShockPp = 0;
ctx.STATE.salesAttritionPct = 8;
r = api.salesAttritionRates();
check('lever overrides both groups', r.source === 'lever' && r.nb === 8 && r.cs === 8 && /attrition \(8\.0%\)/.test(api.renderPaTrips(live, 'plain')));
ctx.STATE.salesAttritionPct = null;
teamInputs = { attrition: null };
check('not measured → no rate, trip says so', api.salesAttritionRates() === null && /Attrition is not measured/.test(api.renderPaTrips(live, 'plain')));
teamInputs = { attrition: measuredAttr };
const tripsNoFloor = api.renderPaTrips({ ...live, floor: null }, 'tech');
check('no floor → CPL trip not computed, flagged', /Not computed: cash floor or program spend not loaded/.test(tripsNoFloor));

console.log('corridor fan from Monte Carlo');
check('no Monte Carlo → no fan', api.paMcCashFan(null) === null && api.paMcCashFan({ cashPath: { monthly: [] } }) === null);
const paths = Array.from({ length: 101 }, (_, k) => Array.from({ length: 12 }, (_, m) => (20 + k / 10 + m) * 1e6));
const monthly = api.buildMonthlyCashBands(paths, 10e6);
check('monthly bands carry P05/P25/P75/P95', monthly.length === 12 && ['p05', 'p25', 'p75', 'p95'].every(k => monthly[0][k] != null));
const fan = api.paMcCashFan({ cashPath: { monthly } });
check('fan = P05–P95 and P25–P75 of draws in $M', fan && fan.outer.label === 'P05–P95 of draws' && fan.inner
  && Math.abs(fan.outer.lo[0] - monthly[0].p05 / 1e6) < 1e-9 && Math.abs(fan.inner.hi[11] - monthly[11].p75 / 1e6) < 1e-9);
const serverMonthly = monthly.map(m => ({ p10: m.p10, p50: m.p50, p90: m.p90 }));
const sFan = api.paMcCashFan({ cashPath: { monthly: serverMonthly } });
check('server fallback → P10–P90 outer only', sFan && sFan.outer.label === 'P10–P90 of draws' && sFan.inner === null);
check('corridor flags a missing fan', /No likelihood fan yet/.test(be));

if (failed) {
  console.error(`\n${failed} check(s) failed`);
  process.exit(1);
}
console.log('\nall budget Analytics-from-data checks passed');
