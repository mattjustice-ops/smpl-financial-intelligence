/**
 * Forecast Engine values come from the loaded data:
 *  - headcount plan changes are priced at each team's loaded cost per head (actual GL payroll ÷ actual
 *    month-end heads through close) and RIF severance at the close roster's average base;
 *  - the pipeline coverage floor is the closed months' pipeline created ÷ closed-won ARR;
 *  - no typed per-head rates, coverage, minimum or year fallbacks.
 *
 * Usage: node scripts/verify-forecast-from-data.mjs
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

const fe = fs.readFileSync(path.join(root, 'public/forecast-engine/index.html'), 'utf8');
const canon = fs.readFileSync(path.join(root, 'canonical/forecast-engine/index.html'), 'utf8');
check('canonical Forecast Engine matches public', canon === fe);

function fnSource(name) {
  const start = fe.indexOf(`function ${name}(`);
  if (start < 0) return null;
  let depth = 0;
  for (let i = fe.indexOf('{', start); i < fe.length; i++) {
    if (fe[i] === '{') depth += 1;
    else if (fe[i] === '}' && --depth === 0) return fe.slice(start, i + 1);
  }
  return null;
}

console.log('no typed values');
for (const name of ['FC_PL_AVG_ANNUAL', 'FC_PL_CORP_BONUS', 'FC_PL_BONUS_PCT', 'FC_PL_TAX_PCT', 'FC_PL_BEN_PCT',
  'FC_PL_K401_PCT', 'FC_PL_NB_OTE', 'FC_PL_CS_OTE']) {
  check(`no ${name}`, !new RegExp(`\\b${name}\\b`).test(fe));
}
check('no typed coverage minimum', !/pipelineMin: \d/.test(fe) && /pipelineMin: fcLoadedCoverageMin\(\),/.test(fe));
check('no typed coverage fallback', !/pipelineCoverage\) \|\| \d/.test(fe) && !/pipelineCoverage\)\s*\|\|\s*\d/.test(fe));
check('no typed year fallback', !/\|\| 20\d\d\b/.test(fe));
check('no typed close-month index fallback', !/CLOSE_MO_IDX : \d/.test(fe));
check('chart text reads the loaded year and cash, not typed values',
  !/Cash builds from \$\d/.test(fe) && !/full year 20\d\d[."]/.test(fe) && /\$\{cashAria\}/.test(fe));
check('cash chart leaves months not loaded empty instead of 0', !/end_cash\/1e6\|\|0/.test(fe));
check('cost gaps are rendered on P&L and Headcount', (fe.match(/fcHcCostGaps\(\)/g) || []).length >= 2);

console.log('headcount change pricing from loaded payroll');
const names = ['fcHcMapDept', 'fcHcCostRates', 'fcHcCostGaps', 'computeFcHcComp', 'fcLoadedCoverageMin'];
const srcs = names.map(fnSource);
check('functions found', srcs.every(Boolean), names.filter((n, i) => !srcs[i]).join(', '));
const depts = fe.match(/const FC_HC_DEPTS = \[[\s\S]*?\];/);
check('FC_HC_DEPTS found', !!depts);

const months = Array.from({ length: 12 }, (_, i) => `2026-${String(i + 1).padStart(2, '0')}`);
const wf = {
  months,
  heads: { Sales: months.map(() => 50), Engineering: months.map(() => 40), Product: months.map(() => 10), Marketing: months.map(() => 20) },
  payroll_by_team: {
    Sales: months.map((_, i) => (i < 6 ? 900000 + i * 10000 : null)),
    Engineering: months.map((_, i) => (i < 6 ? 800000 : null)),
    Product: months.map((_, i) => (i < 6 ? 200000 : null)),
    Marketing: months.map((_, i) => (i < 6 ? 300000 : null)),
  },
  roster: [
    { dept: 'Sales', base: 120000 }, { dept: 'Sales', base: 130000 },
    { dept: 'Engineering', base: 170000 }, { dept: 'Product', base: 150000 },
    { dept: 'Marketing', base: 110000 },
  ],
};
let rifs = [];
const ctx = {
  ALL_P: months,
  getCloseMonth: () => '2026-06',
  fcWorkforce: () => wf,
  fcWfMonthValue: (series, p) => { const i = months.indexOf(p); return i >= 0 && series && series[i] != null ? series[i] : null; },
  fcHcRifsForPeriod: (p) => rifs.filter(r => r.period === p),
  fcGtmFunnelRates: () => ({ winRate: 0.3 }),
  computeFcHcPlan: () => Object.fromEntries(months.map(p => [p, { ending: { sales: 52, cs: 0, marketing: 21, rd: 50, ga: 0 } }])),
};
vm.runInNewContext(`
  ${depts ? depts[0] : ''}
  ${srcs.join('\n')}
  this.api = { fcHcCostRates, fcHcCostGaps, computeFcHcComp, fcLoadedCoverageMin };
`, ctx);
const api = ctx.api;
const near = (a, b) => a != null && Math.abs(a - b) <= 1e-6 * Math.max(1, Math.abs(b));

const rates = api.fcHcCostRates();
const salesPay = [0, 1, 2, 3, 4, 5].reduce((s, i) => s + 900000 + i * 10000, 0);
check('cost per head = actual GL payroll ÷ actual heads through close', near(rates.sales.monthlyPerHead, salesPay / (50 * 6)));
check('R&D pools Engineering and Product', near(rates.rd.monthlyPerHead, (800000 + 200000) * 6 / (50 * 6)));
check('severance base = close roster average base', near(rates.sales.annualBase, 125000) && near(rates.rd.annualBase, 160000));
check('groups with no payroll are null, not filled', rates.cs.monthlyPerHead === null && rates.ga.monthlyPerHead === null);
const gaps = api.fcHcCostGaps();
check('unpriced groups are flagged', gaps.some(g => /Sales - Customer Success: no actual GL payroll/.test(g)) && gaps.some(g => /G&A/.test(g)), gaps.join(' | '));

rifs = [{ period: '2026-09', dept: 'sales', heads: 2, weeks: 4 }];
const comp = api.computeFcHcComp();
check('payroll = heads × loaded cost per head', near(comp['2026-09'].payroll.sales, 52 * rates.sales.monthlyPerHead));
check('RIF severance = heads × weekly base × weeks', near(comp['2026-09'].severance.sales, 2 * (125000 / 52) * 4));
check('unpriced group costs $0 (flagged above)', comp['2026-09'].payroll.cs === 0);

console.log('pipeline coverage floor');
check('floor = 1 ÷ loaded win rate (pipeline created ÷ closed-won)', near(api.fcLoadedCoverageMin(), 1 / 0.3));
ctx.fcGtmFunnelRates = () => ({ winRate: null });
vm.runInNewContext('this.api.fcLoadedCoverageMin = fcLoadedCoverageMin;', ctx);
check('no loaded win rate → no floor', api.fcLoadedCoverageMin() === null);

console.log('lever ledger from the live suite');
check('no mirrored upside multiplier', !/Math\.abs\((l\.)?dn\) \* 0\.\d+/.test(fe) && !/upLevers/.test(fe));
const ledgerSrc = fnSource('renderFcLeverLedger');
check('renderFcLeverLedger found', !!ledgerSrc);
const lctx = { fcEsc: (s) => String(s == null ? '' : s) };
vm.runInNewContext(`${ledgerSrc}\nthis.render = renderFcLeverLedger;`, lctx);
const ledger = lctx.render({
  cases: [
    { id: 'top_deal_slip', label: 'Top deal slips', dCash: -2.4e6, dArr: -3e6, status: 'watch' },
    { id: 'renewal_miss', label: 'Renewal miss', dCash: -0.2e6, dArr: -0.3e6, status: 'hold' },
  ],
}, 'plain');
check('downside-only cases show no upside', /-2\.4M<\/b> \/ —/.test(ledger) && !/\+\d+\.\dM/.test(ledger));
check('no upside group without a measured upside', !/Pull these to get ahead/.test(ledger));
const ledgerUp = lctx.render({ cases: [{ id: 'x', label: 'Collections pull-in', dCash: 1.5e6, status: 'hold' }] }, 'plain');
check('positive case Δ cash is the upside', /\+\$1\.5M upside/.test(ledgerUp));

console.log('cash corridor fan and P(cash ≤ 75% plan) from Monte Carlo');
check('no typed illustrative fan or fan-implied probability', !/function fcApproxCashBands|function fcPWatch25FromFan|Math\.abs\(dec\) \* 0\.25/.test(fe));
check('no normal-curve pWatch fill with a 2% floor', !/Math\.max\(0\.02, 1 - p\)/.test(fe));
check('Monte Carlo result is never overwritten by the view', !/mc\.cash\.pWatch = /.test(fe));
const bandsSrc = fnSource('fcResolveCorridorBands');
const cashSrc = fnSource('fcCashToM');
check('fcResolveCorridorBands found', !!bandsSrc && !!cashSrc);
const bctx = { CLOSE_MO_IDX: 5, window: {} };
vm.runInNewContext(`${cashSrc}\n${bandsSrc}\nthis.bands = fcResolveCorridorBands;`, bctx);
const packet = { cashByMonth: Array.from({ length: 12 }, (_, i) => (30 + i) * 1e6), cashFloor: 10e6 };
const none = bctx.bands(packet, null);
check('no Monte Carlo → no fan, probability not shown', none.ok && none.p10 === null && none.p25 === null && none.pWatch === null);
const monthlyMc = packet.cashByMonth.map(v => ({ p10: v - 1e6, p25: v - 0.5e6, p50: v, p75: v + 0.5e6, p90: v + 1e6 }));
const narrow = bctx.bands(packet, { mc: { cash: { pWatch: 0 }, cashPath: { monthly: monthlyMc } } });
check('narrow Monte Carlo band is drawn as measured (open months)', narrow.usedMcPath && narrow.p10.length === 6
  && Math.abs(narrow.p10[0] - 35) < 1e-9 && Math.abs(narrow.p75[5] - 41.5) < 1e-9);
check('measured 0% stays 0%', narrow.pWatch === 0);
const noQuart = bctx.bands(packet, { mc: { cash: {}, cashPath: { monthly: monthlyMc.map(m => ({ p10: m.p10, p90: m.p90 })) } } });
check('no P25/P75 → no inner band (no midpoint fill)', noQuart.p10 && noQuart.p25 === null && noQuart.pWatch === null);

console.log('stress cases on the Forecast\'s own ARR → P&L → cash rules');
check('no typed cash / EBITDA per ARR conversion', !/cashPerArr|ebitdaPerArr|function fcCashPathFromArrMiss|function fcScaleCashPath|function fcNnBridge/.test(fe));
check('no typed fallback dollars for empty books', !/wtdNb \* 0\.(2|18)\b|fyChurn\) \|\| 0\) \* 0\.(35|4)\b|openWtdPipe \* 0\.15|renGross \* 0\.08|coverNow - pipe\) \* 0\.045/.test(fe));
check('no typed renewal rate or deal-probability defaults', !/renWtd \/ renGross : 0\.95|Number\(d\.prob\) != null|Number\(d\.(risk|health)\) != null/.test(fe));
const stressNames = ['fcStressConversion', 'fcShockFromArrMiss', 'fcPathStats', 'fcDealKind', 'buildFcScenarioCaseDefs'];
const stressSrc = stressNames.map(fnSource);
check('stress functions found', stressSrc.every(Boolean), stressNames.filter((n, i) => !stressSrc[i]).join(', '));
const allP = Array.from({ length: 12 }, (_, i) => `2026-${String(i + 1).padStart(2, '0')}`);
const sctx = {
  ALL_P: allP, FC_P: allP.slice(6),
  getOutlookIS: () => ({ revenue: 100, cogs: 30 }),
  levers: { nb: 1, exp: 1, cogs: null },
  fcWcState: { dso: null, dpo: null },
  fcRecSvcPct: () => 0,
};
sctx.getLevers = () => sctx.levers;
vm.runInNewContext(`${stressSrc.join('\n')}
  this.shock = fcShockFromArrMiss; this.defs = buildFcScenarioCaseDefs;`, sctx);
const sBase = { cashByMonth: Array(12).fill(20e6), decArr: 90e6, bopArr: 75e6, fyNb: 8e6, fyChurn: 2e6, fyEbitda: 5e6 };
const s1 = sctx.shock(sBase, [{ period: '2026-07', arr: 1.2e6, kind: 'nb' }]);
check('ARR miss removes ending ARR and NB', s1 && near(s1.decArr, 88.8e6) && near(s1.fyNb, 6.8e6) && near(s1.fyNn, 13.8e6));
check('EBITDA = lost subscription revenue (ARR ÷ 12 from booking month) × (1 − loaded COGS ratio)', s1 && near(5e6 - s1.fyEbitda, 6 * 100000 * 0.7));
check('Dec cash = − cumulative gross profit + receivable not yet collected (Net 30)', s1 && near(s1.endCash - 20e6, -420000 + 100000));
check('closed months untouched', s1 && s1.cashByMonth.slice(0, 6).every(v => v === 20e6));
sctx.fcWcState = { dso: 45, dpo: 30 };
const s2 = sctx.shock(sBase, [{ period: '2026-07', arr: 1.2e6, kind: 'churn' }]);
check('DSO / DPO levers time receivables and payables', s2 && near(s2.endCash - 20e6, -420000 + 150000 - 30000) && near(s2.fyChurn, 3.2e6));
sctx.levers = { nb: 0.8, exp: 1, cogs: null };
const s3 = sctx.shock(sBase, [{ period: '2026-07', arr: 1.2e6, kind: 'nb' }]);
check('NB attainment lever scales what the forecast counts', s3 && near(s3.decArr, 90e6 - 0.96e6));
sctx.getOutlookIS = () => ({ revenue: 100 });
sctx.levers = { nb: 1, exp: 1, cogs: null };
check('no loaded COGS ratio → no shock and no cases (not a silent hold)', sctx.shock(sBase, [{ period: '2026-07', arr: 1e6, kind: 'nb' }]) === null && sctx.defs({}).length === 0);
sctx.getOutlookIS = () => ({ revenue: 100, cogs: 30 });
const s4 = sctx.shock({ cashByMonth: Array(12).fill(20e6), decArr: 90e6 }, [{ period: '2026-07', arr: 1e6, kind: 'nb' }]);
check('unloaded base values stay unloaded under stress (no $0 / 0% fill)', s4 && s4.fyMkt === null && s4.yoyGrowthPct === null
  && s4.fyEbitda === null && s4.fyNn === null && s4.fyNb === null && s4.fyChurn === null && near(s4.decArr, 89e6));
const s5 = sctx.shock(Object.assign({ fyMkt: 11e6, yoyGrowthPct: 22 }, sBase), [{ period: '2026-07', arr: 1e6, kind: 'nb' }]);
check('loaded program spend and plan growth carry through unchanged', s5 && s5.fyMkt === 11e6 && s5.yoyGrowthPct === 22);

console.log('CPL trip from Dec cash cushion ÷ open-month program spend');
check('no typed 15–40% clamp on the CPL trip', !/Math\.max\(15, Math\.min\(40/.test(fe));
check('trip and offsets read the same open-month spend', (fe.match(/fcOpenProgramSpend\(\) \/ 1e6/g) || []).length === 2);
const tripsSrc = fnSource('renderFcPaTrips');
const openSrc = fnSource('fcOpenProgramSpend');
check('renderFcPaTrips / fcOpenProgramSpend found', !!tripsSrc && !!openSrc);
const spendByMonth = { '2026-07': 2e6, '2026-08': 4e6 };
const tctx = { fcEsc: (s) => String(s == null ? '' : s), fcFloorTxt: () => '', FC_P: ['2026-07', '2026-08'],
  fcGtmAllocate: (p) => ({ spendTot: spendByMonth[p] }),
  policy: { cash_watch_shortfall: 0.25, cash_alarm_shortfall: 0.5, program_cut: 0.15, dso_improvement_days: 5 } };
tctx.window = { SMPLOutlook: {
  getRiskPolicyValue: (k) => (tctx.policy[k] ?? null),
  riskPolicyNotSet: (k) => `Risk policy not set (${k})`,
} };
const policySrc = ['fcPolicy', 'fcPolicyNotSet', 'fcPolicyPct', 'fcPolicyGaps', 'fcPolicyLeversTxt'].map(fnSource).join('\n');
vm.runInNewContext(`${policySrc}\n${openSrc}\n${tripsSrc}\nthis.trips = renderFcPaTrips;`, tctx);
const railsTrip = tctx.trips({ cashByMonth: Array(12).fill(22e6), cashFloor: 10e6 }, 'tech');
check('cash trip reads the policy rails and levers', /Dec cash vs −25% \/ −50% \/ floor/.test(railsTrip)
  && /endCash ≤ 75% of plan/.test(railsTrip) && /Program spend −15%, HC defer, DSO −5 days/.test(railsTrip));
tctx.policy = {};
const unsetTrip = tctx.trips({ cashByMonth: Array(12).fill(22e6), cashFloor: 10e6 }, 'tech');
check('policy not set → floor-only trip, levers say so', /min\(cash\) &lt; floor|min\(cash\) < floor/.test(unsetTrip)
  && /Risk policy not set \(program_cut\)/.test(unsetTrip) && !/−25%/.test(unsetTrip));
tctx.policy = { cash_watch_shortfall: 0.25, cash_alarm_shortfall: 0.5, program_cut: 0.15, dso_improvement_days: 5 };
const decCash = (m) => ({ cashByMonth: Array(12).fill(m * 1e6), cashFloor: 10e6 });
check('wide cushion is shown as computed (above 40%)', /CPL > \+200% vs plan on open-month spend/.test(tctx.trips(decCash(22), 'tech')));
check('thin cushion is shown as computed (below 15%)', /CPL > \+5% vs plan/.test(tctx.trips(decCash(10.3), 'tech')));
tctx.FC_P = [];
check('no open-month spend → not computed', /Not computed: cash floor or open-month program spend not loaded/.test(tctx.trips(decCash(22), 'tech')));

if (failed) {
  console.error(`\n${failed} check(s) failed`);
  process.exit(1);
}
console.log('\nall forecast-from-data checks passed');
