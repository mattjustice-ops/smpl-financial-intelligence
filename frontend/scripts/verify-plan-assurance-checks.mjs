/**
 * Plan Assurance checks compare like with like:
 *  - jan_hc: the Budget's January opening heads (what the plan starts from) vs the prior-December
 *    forecast ending heads; the Forecast's close-month plan heads vs the loaded close total.
 *  - sm_tie: GTM program spend = what posts to the Marketing P&L channel lines, and that sits inside
 *    income-statement S&M. No implied S&M from a prior-year share.
 *  - cash_floor: the Budget floor is the loaded cash flow bridge `cash_floor`; none loaded is flagged.
 *  - grr_floor: plan average GRR vs the prior year's measured average (worst months as context), not a policy band.
 *  - bench: checked only against a loaded bench-cover target.
 *  - packet Monte Carlo: levers move loaded packet fields through identities; residual noise is the
 *    measured actual-minus-budget CFO spread; anything not loaded is reported, not defaulted.
 * The Budget Engine fallback and the backend registry must agree.
 *
 * Usage: node scripts/verify-plan-assurance-checks.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, '..');
const repo = path.join(root, '..');

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

console.log('Budget Engine opening heads');
const hcPlan = fnSource(be, 'computeHcPlan') || '';
check('HC plan records opening heads per dept and in total',
  /row\.bop\[d\.key\] = d\.fromSales/.test(hcPlan) && /row\.bopTotal \+= row\.bop\[d\.key\];/.test(hcPlan));
check('Sales and CS opening heads come from the Sales plan', /bopSalesDept: bopAes \+ team\.other\.sales,/.test(be)
  && /bopCsDept: bopCs \+ team\.other\.cs,/.test(be));
const packetSrc = fnSource(be, 'buildBudgetAssurancePacket') || '';
check('packet sends Jan opening heads, not Jan ending heads',
  /const janHc = hc\[jan\]\.bopTotal;/.test(packetSrc) && !/hc\[jan\]\.headsTotal/.test(packetSrc));
check('lock is the prior-December forecast ending heads', /const janHcExpected = hcBopTotal\(\);/.test(packetSrc));
check('packet sends program posted to the Marketing P&L', /fyPlProgram,/.test(packetSrc) && !/fyGtmSm/.test(be));
check('no implied S&M heuristic', !/\bmktSmShare\b/.test(be) && !/row\.smTotal = /.test(be));

console.log('Budget Engine risk rules');
const rules = fnSource(be, 'runBudgetRiskChecks');
const posted = fnSource(be, 'mktProgramPosted');
check('rule functions found', !!rules && !!posted);
const ctx = {
  BUDGET_YEAR: 2027,
  fmtM: v => `$${(v / 1e6).toFixed(2)}M`,
  fmtN: v => String(Math.round(v)),
  PL_DEPTS: [{ key: 'marketing', sections: [{ key: 'mkt', lines: [
    { k: 'wages', from: 'hc_wages' },
    { k: 'ch_paid_search', from: 'gtm_channel', channel: 'Paid Search' },
    { k: 'ch_events', from: 'gtm_channel', channel: 'Events' },
    { k: 'gl_software', from: 'gl' },
  ] }] }],
  window: { SMPLOutlook: {
    getRiskPolicyValue: k => (ctx.policy ? ctx.policy[k] ?? null : null),
    riskPolicyNotSet: k => `Risk policy not set (${k})`,
  } },
  policy: { floor_hard_breach_share: 0.85 },
};
vm.runInNewContext(`
  ${fnSource(be, 'paPolicy')}
  ${fnSource(be, 'paPolicyNotSet')}
  ${fnSource(be, 'plAllLines')}
  ${posted}
  ${rules}
  this.api = { runBudgetRiskChecks, mktProgramPosted };
`, ctx);
const { runBudgetRiskChecks, mktProgramPosted } = ctx.api;

const plRow = { depts: { marketing: { lines: { wages: 900, ch_paid_search: 300, ch_events: 200, gl_software: 50 } } } };
check('posted program sums only the channel lines', mktProgramPosted(plRow) === 500, String(mktProgramPosted(plRow)));

const healthy = () => ({
  budget_year: 2027, yoyGrowthPct: 20, bopArr: 90e6, decArr: 108e6, targetArr: 108e6, fyNn: 18e6,
  fyRev: 99e6, fyEbitda: 4e6, endCash: 14e6, cashFloor: 10e6, minCash: 11.5e6, minCashPeriod: '2027-07',
  fyMkt: 12e6, fyMql: 24000, fySpendId: 12e6, mixDevMax: 0.001, avgGrr: 0.94, minGrr: 0.93,
  grrFloorAvg: 0.94, grrFloorMin: 0.925,
  salesEnd: 42, csEnd: 18, aeNeeded: 40, csNeeded: 17, coverPct: 65, hirePct: 35, benchTarget: 60,
  janHc: 268, janHcExpected: 268, decHc: 300, pipelineCoverage: 3.3, pipelineMin: 3.3,
  fyIsSm: 37e6, fyPlProgram: 12e6,
});
const byId = p => Object.fromEntries(runBudgetRiskChecks(p).map(r => [r.id, r]));

check('opening heads on the lock pass', byId(healthy()).jan_hc.severity === 'ok');
check('Jan ending heads above the lock would have failed; opening heads are what is compared',
  byId({ ...healthy(), janHc: 274 }).jan_hc.severity === 'high');
check('missing lock is not sized, not passed', byId({ ...healthy(), janHcExpected: null }).jan_hc === undefined);
check('program posted and inside S&M passes', byId(healthy()).sm_tie.severity === 'ok');
check('program not fully posted fails', byId({ ...healthy(), fyPlProgram: 11.95e6 }).sm_tie.severity === 'high');
const over = byId({ ...healthy(), fyIsSm: 11e6 }).sm_tie;
check('program above IS S&M fails', over.severity === 'high' && /exceeds IS S&M/.test(over.title));
check('unsized P&L is not passed', byId({ ...healthy(), fyPlProgram: null }).sm_tie === undefined);
check('spend = MQL x CPL passes when sized', byId(healthy()).gtm_spend.severity === 'ok');
check('unsized GTM spend is not passed', byId({ ...healthy(), fySpendId: null, fyMql: null }).gtm_spend === undefined);
check('packet sends unsized MQLs and spend identity as null, not 0',
  /const fyMql = gtmSized \? /.test(packetSrc) && /const fySpendId = gtmSized \? /.test(packetSrc)
  && !/gtm\[p\]\.mqls \|\| 0/.test(packetSrc));

console.log('Budget Engine cash floor');
check('packet floor comes from the loaded cash flow bridge', /const cashFloor = budgetCashFloor\(\);/.test(packetSrc));
check('no typed floor default or $10M fallbacks',
  !/cashFloorDec|10000000|\|\| 1e7|live\.floor \|\| 10|live\.floor : 10|: 10\)\.toFixed/.test(be));
const floorFn = fnSource(be, 'budgetCashFloor');
const bridge = {
  Budget: { '2026-11': { cash_floor: 9e6 }, '2026-12': { cash_floor: 10e6 } },
  Forecast: { '2026-12': { cash_floor: 8e6 } },
};
const floorCtx = (rows) => {
  const c = {
    CLOSE_MONTH: '2026-06',
    allOutlookPeriods: () => ['2026-10', '2026-11', '2026-12'],
    window: { SMPLOutlook: { getCashBridgeRow: (p, sc) => (rows[sc] && rows[sc][p]) || null } },
  };
  vm.runInNewContext(`${floorFn}\nthis.f = budgetCashFloor;`, c);
  return c.f();
};
check('latest Budget bridge row wins', floorCtx(bridge) === 10e6, String(floorCtx(bridge)));
check('Forecast bridge used when no Budget floor', floorCtx({ Forecast: bridge.Forecast }) === 8e6);
check('no bridge floor → null, not filled', floorCtx({}) === null);
const noFloor = byId({ ...healthy(), cashFloor: null });
check('no floor is flagged, never passed', noFloor.cash_floor.severity === 'medium' && /No cash floor loaded/.test(noFloor.cash_floor.title)
  && noFloor.cash_path === undefined);
check('floor breach past the hard-breach share (risk policy) is high', byId({ ...healthy(), endCash: 8e6, minCash: 7e6 }).cash_floor.severity === 'high');
check('floor breach inside the hard-breach share is medium', byId({ ...healthy(), endCash: 9e6, minCash: 7e6 }).cash_floor.severity === 'medium');
ctx.policy = {};
const noShare = byId({ ...healthy(), endCash: 8e6, minCash: 7e6 }).cash_floor;
check('hard-breach share not set → not escalated, and said so', noShare.severity === 'medium' && /Risk policy not set \(floor_hard_breach_share\)/.test(noShare.detail));
ctx.policy = { floor_hard_breach_share: 0.85 };

console.log('GRR vs measured history; bench only against a loaded target');
check('GRR at measured history passes', byId(healthy()).grr_floor.severity === 'ok');
check('GRR below measured average warns', byId({ ...healthy(), avgGrr: 0.935 }).grr_floor.severity === 'medium');
check('a gap under the 0.1pp shown is rounding, not a warning', byId({ ...healthy(), avgGrr: 0.9396 }).grr_floor.severity === 'ok');
const worstOnly = byId({ ...healthy(), minGrr: 0.92 }).grr_floor;
check('worst month is context, not the gate', worstOnly.severity === 'ok' && /worst month 92\.0% vs 92\.5% measured/.test(worstOnly.detail));
const noHist = byId({ ...healthy(), grrFloorAvg: null, grrFloorMin: null }).grr_floor;
check('no measured history is flagged, never passed', noHist.severity === 'medium' && /GRR history not loaded/.test(noHist.title));
check('no typed GRR policy band', !/0\.92\b|>= 0\.90|>= 0\.85|policy ≥/.test(rules));
check('packet floors come from the prior year', /grrFloorAvg: histGrr\.avg,/.test(packetSrc) && /const histGrr = priorYearGrr\(\);/.test(packetSrc));
const grrFn = fnSource(be, 'priorYearGrr');
const hist = { '2026-01': { grr: 0.99 }, '2026-02': { grr: 0.97 }, '2026-03': { grr: null } };
const grrCtx = { CTX_QUARTERS: [{ months: ['2026-01', '2026-02', '2026-03'] }], getHistRow: p => hist[p] || null };
vm.runInNewContext(`${grrFn}\nthis.f = priorYearGrr;`, grrCtx);
const g = grrCtx.f();
check('prior-year GRR = average and worst loaded month', Math.abs(g.avg - 0.98) < 1e-12 && g.min === 0.97);
grrCtx.getHistRow = () => null;
check('no history → nulls', grrCtx.f().avg === null && grrCtx.f().min === null);
check('bench against a loaded target', byId(healthy()).bench.severity === 'ok');
check('no bench target → not checked', byId({ ...healthy(), benchTarget: null }).bench === undefined && !/benchTarget : 60/.test(be));

console.log('Forecast Engine');
for (const rel of ['public/forecast-engine/index.html', 'canonical/forecast-engine/index.html']) {
  const fe = fs.readFileSync(path.join(root, rel), 'utf8');
  check(`${rel}: GRR floors from the prior year's loaded actuals`,
    /grrFloorAvg: histGrr\.avg,/.test(fe) && /const histGrr = fcPriorYearGrr\(year\);/.test(fe));
  check(`${rel}: lock is the loaded close total, not the packet's own value`,
    !/janHcExpected: janHc/.test(fe) && /janHcExpected = getCloseHc\(\);/.test(fe)
    && /janHc = closeRow\.headsTotal != null \? closeRow\.headsTotal : null;/.test(fe));
}

console.log('backend matches');
const read = rel => fs.readFileSync(path.join(repo, rel), 'utf8');
const constraints = read('backend/app/services/predictive_planning/constraints.py');
const feasibility = read('backend/app/services/predictive_planning/feasibility.py');
const schema = read('backend/app/schemas/predictive_planning.py');
check('sm_tie reads program, posted and IS S&M',
  /reads=\("fy_mkt", "fy_pl_program", "fy_is_sm"\)/.test(constraints) && /params=\{"abs_tolerance": 1\.0\},\s*reads=\("fy_mkt"/.test(constraints));
check('no implied-S&M field or ratio left', !/fy_gtm_sm|fyGtmSm|ratio_ceiling|MKT_SM_RATIO/.test(constraints + feasibility + schema));
check('schema accepts fyPlProgram', /fy_pl_program: float \| None = Field\(default=None, alias="fyPlProgram"\)/.test(schema));
check('no hard-coded year in the HC lock message', !/Dec'26/.test(feasibility));
check('no typed GRR or bench policy in the registry',
  /params=\{"avg_floor": None, "display_tolerance": 0\.0005\}/.test(constraints) && /params=\{"target_pct": None, "slack_pp": 0\.5\}/.test(constraints)
  && /"grr_floor": \{"avg_floor": "grr_floor_avg"\}/.test(constraints));
check('schema accepts the measured GRR floors', /alias="grrFloorAvg"/.test(schema) && /alias="grrFloorMin"/.test(schema));
check('backend gtm_spend skips missing inputs instead of reading them as 0',
  /def _eval_gtm_spend[\s\S]*?if identity is None or actual is None:\s*return None/.test(feasibility)
  && !/_get\(p, "fy_spend_id"\) or 0\.0/.test(feasibility));

console.log('packet Monte Carlo moves the plan through identities on loaded fields');
const mcPy = read('backend/app/services/predictive_planning/monte_carlo.py');
check('server model has no typed elasticities, residual share or fallbacks',
  !/cashResidMo|cash_resid_mo|cpl_drag|pipe_boost|flow_scale|or 20\.0|or 3\.0|or 10\.0|250_?000/.test(mcPy));
check('schema accepts the identity inputs',
  ['closeMonthIdx', 'programByMonth', 'openNb', 'cfoPlanErrorSd'].every(a => schema.includes(`alias="${a}"`)));
check('Budget packet sends program at planned MQLs, open new business and the measured CFO error',
  /programByMonth = gtmSized \? BUD_P\.map\(p => gtm\[p\]\.mqls \* Number\(gtm\[p\]\.rates\.cpl\)\) : null/.test(packetSrc)
  && /openNb: fyNb,/.test(packetSrc) && /cfoPlanErrorSd,/.test(packetSrc));
check('Budget fallback reads the server alarm rail instead of a typed 0',
  /pAlarm: r\.cash\.pAlarm/.test(be) && !/pAlarm: 0,/.test(be) && !/pWatch25|pAlarm50/.test(be + mcPy));

const outlookSrc = fs.readFileSync(path.join(root, 'public/shared/smpl-outlook.js'), 'utf8');
const cfoCtx = { window: {} };
cfoCtx.window.location = { search: '' };
cfoCtx.window.addEventListener = () => {};
cfoCtx.window.SMPL_CLOSE_MONTH = '2026-04';
cfoCtx.window.SMPL_DEMO_TS_DATA = {
  Actual: { periods: ['2026-01', '2026-02', '2026-03', '2026-04', '2026-05'], cfs: {
    '2026-01': { cfo: 110 }, '2026-02': { cfo: 90 }, '2026-03': { cfo: 130 }, '2026-04': { cfo: 70 }, '2026-05': { cfo: 9999 },
  } },
  Budget: { cfs: { '2026-01': { cfo: 100 }, '2026-02': { cfo: 100 }, '2026-03': { cfo: 100 }, '2026-04': { cfo: 100 }, '2026-05': { cfo: 100 } } },
};
vm.runInNewContext(outlookSrc, cfoCtx);
const cfoSd = cfoCtx.window.SMPLOutlook.getCfoPlanErrorSd();
const errs = [10, -10, 30, -30];
const errMu = errs.reduce((a, b) => a + b, 0) / errs.length;
const wantSd = Math.sqrt(errs.reduce((s, v) => s + (v - errMu) ** 2, 0) / (errs.length - 1));
check('CFO plan error = sd of actual minus budget over closed months only', Math.abs(cfoSd - wantSd) < 1e-9, String(cfoSd));
cfoCtx.window.SMPL_CLOSE_MONTH = '2026-02';
check('fewer than 3 closed months → null, not a typed spread', cfoCtx.window.SMPLOutlook.getCfoPlanErrorSd() === null);

console.log('Monte Carlo lever priors are the server fit, never typed');
const seedFit = { priors: { yoyPp: 1.5 }, prior_source: 'history_partial', correlations: {}, method_card: {} };
const liveFit = { priors: { yoyPp: 2.5, attrPp: 9 }, prior_source: 'history_fit', correlations: {}, method_card: {} };
const priorsCtx = { window: { location: { search: '' }, addEventListener: () => {}, SMPL_DEMO_MC_PRIORS: seedFit } };
vm.runInNewContext(outlookSrc, priorsCtx);
check('signed out → the fit the demo seed carries', priorsCtx.window.SMPLOutlook.getLoadedMcPriors() === seedFit);
priorsCtx.window.SMPL_OUTLOOK_PAYLOAD = { MC_PRIORS: liveFit };
check('live outlook → its MC_PRIORS', priorsCtx.window.SMPLOutlook.getLoadedMcPriors() === liveFit);
priorsCtx.window.SMPL_OUTLOOK_PAYLOAD = {};
check('live outlook without MC_PRIORS → null, not the demo fit', priorsCtx.window.SMPLOutlook.getLoadedMcPriors() === null);
const feSrc = fs.readFileSync(path.join(root, 'public/forecast-engine/index.html'), 'utf8');
for (const [label, src] of [['Budget', be], ['Forecast', feSrc]]) {
  check(`${label}: no typed lever priors and no browser-built prior history`,
    !/DEFAULT_PRIORS|yoyPp: 3\.2|cplLog: 0\.28|AssuranceHistoryForPriors|getGtmPriorHistory|history: build/.test(src));
  check(`${label}: server-unreachable fallback draws the loaded outlook's fit`, /getLoadedMcPriors\(\)/.test(src));
}
check('Budget draws only levers with a fitted prior and reports ARR miss and AE short only when drawn',
  /SMPLPlanMc\.drawnPriors\(inputs\.priors, budgetLevers\)/.test(be) && /policy\.arrOn = bridgeKeys\.some\(shock\)/.test(be) && /policy\.aeOn = shock\('attrPp'\) \|\| shock\('attainPp'\)/.test(be)
  && /pAeShort: policy\.aeOn \? pAeShort \/ n : null/.test(be));
const seedText = fs.readFileSync(path.join(root, 'public/shared/smpl-demo-seed.js'), 'utf8');
check('demo seed carries the server fit', /g\.SMPL_DEMO_MC_PRIORS = \{"priors":/.test(seedText));
const planMcSrc = fs.readFileSync(path.join(root, 'public/shared/smpl-plan-mc.js'), 'utf8');
const planMcCtx = { window: {} };
vm.runInNewContext(planMcSrc, planMcCtx);
const planMc = planMcCtx.window.SMPLPlanMc;
const drawn = planMc.drawnPriors({ yoyPp: 2, cplLog: null, attrPp: -1, pipe: 'x' });
check('only finite, non-negative priors are drawn', JSON.stringify(drawn) === '{"yoyPp":2}', JSON.stringify(drawn));
check('correlations on an undrawn lever are dropped',
  JSON.stringify(planMc.drawnCorrelations({ 'yoyPp:pipe': 0.4, 'yoyPp:attrPp': 0.2 }, { yoyPp: 1, attrPp: 1 })) === '{"yoyPp:attrPp":0.2}');

console.log('stress severities and trip-wires measured from closed history');
const mhCtx = { window: { location: { search: '' }, addEventListener: () => {} } };
vm.runInNewContext(outlookSrc, mhCtx);
const measure = mhCtx.window.SMPLOutlook.measureHistory;
const mhMonths = [], mhBook = {};
const qWin = [0.30, 0.25, 0.35, 0.30, 0.20, 0.30, 0.40, 0.30];
const qNn = [100, 110, 120, 130, 120, 140, 150, 160];
for (let q = 0; q < 8; q++) {
  for (let k = 0; k < 3; k++) {
    const p = `${2024 + Math.floor(q / 4)}-${String((q % 4) * 3 + k + 1).padStart(2, '0')}`;
    mhMonths.push({ p, bop: 1000, nb: 10, exp: 5 + q, out: 2 + (q % 2), nn: qNn[q] / 3 });
    mhBook[p] = { begin: 300 + q * 10, won: qWin[q] * 100, lost: (1 - qWin[q]) * 100 };
  }
}
mhMonths.push({ p: '2026-01', bop: 1000, nb: 1, exp: 0, out: 0, nn: 1 });
const mh = measure(mhMonths, mhBook);
const mu = xs => xs.reduce((a, b) => a + b, 0) / xs.length;
const sdv = xs => Math.sqrt(xs.reduce((s, v) => s + (v - mu(xs)) ** 2, 0) / (xs.length - 1));
const yoy = [120 / 100, 140 / 110, 150 / 120, 160 / 130];
check('partial quarter excluded; span covers full quarters only', mh.quarters === 8 && mh.span === '2024-01 to 2025-12', mh.span);
check('NB attainment stress = 1 − worst/mean closed-quarter win rate', Math.abs(mh.nbShare - (1 - 0.20 / mu(qWin))) < 1e-12, String(mh.nbShare));
check('growth haircut = 1 − worst/mean net new vs the same quarter a year earlier', Math.abs(mh.nnShare - (1 - Math.min(...yoy) / mu(yoy))) < 1e-12, String(mh.nnShare));
check('win-rate trip = one standard deviation of closed-quarter win rate, in points', Math.abs(mh.winTripPp - sdv(qWin) * 100) < 1e-9, String(mh.winTripPp));
const outQ = [0, 1, 2, 3, 4, 5, 6, 7].map(q => 3 * (2 + (q % 2)) / 1000);
check('churn trip = 1 + σ/μ of closed-quarter (churn + contraction) / BoP', Math.abs(mh.churnTripX - (1 + sdv(outQ) / mu(outQ))) < 1e-12, String(mh.churnTripX));
const thinMh = measure(mhMonths.slice(0, 9), mhBook);
check('fewer than four closed quarters → every severity and trip-wire is null, not typed',
  thinMh.quarters === 3 && ['nbShare', 'expShare', 'nnShare', 'peakShare', 'coverShare', 'winTripPp', 'churnTripX', 'coverTripShare'].every(k => thinMh[k] === null));
check('no pipeline book → win-rate and coverage not measured', measure(mhMonths, null).winTripPp === null && measure(mhMonths, null).coverShare === null);
check('Budget growth start curve and trip-wires read measured history, no typed haircut or trip values',
  /const haircut = hist\.nnShare;/.test(be) && !/haircut = 0\.\d/.test(be) && !/1\.5pp|1\.5 points|1\.10×|a tenth worse/.test(be)
  && /hist\.winTripPp/.test(be) && /hist\.churnTripX/.test(be) && /getLoadedPipelineBook\(\)/.test(be));
const seedSrc = fs.readFileSync(path.join(root, 'public/shared/smpl-demo-seed.js'), 'utf8');
check('demo seed carries the pipeline book the signed-out Budget measures win rate from', /g\.SMPL_DEMO_PIPELINE_BOOK = \{"\d{4}-\d{2}"/.test(seedSrc));

for (const rel of ['public/forecast-engine/index.html', 'canonical/forecast-engine/index.html']) {
  const fe = fs.readFileSync(path.join(root, rel), 'utf8');
  check(`${rel}: stress severities and trip-wires read measured history, none typed`,
    /SMPLOutlook\.measureHistory\(months, SRC\.pipeline_book\)/.test(fe)
    && /byPeriod\('nb', hist\.nbShare, 'nb'\)/.test(fe) && /hist\.winTripPp/.test(fe) && /hist\.churnTripX/.test(fe) && /hist\.coverTripShare/.test(fe)
    && !/1\.5pp|1\.10×|slips a turn|FC_MIN_HISTORY_QUARTERS/.test(fe));
  check(`${rel}: client fallback has no typed elasticities or residual share`,
    !/cashResidMo|cplDrag|pipeBoost|flowScale|Math\.max\(250000/.test(fe));
  check(`${rel}: packet sends program by month, open new business and the measured CFO error`,
    /programByMonth = ALL_P\.map\(p => fcGtmAllocate\(p\)\.spendTot\);/.test(fe) && /if \(p > close\) openNb \+= fcArrComponent\(p, 'nb'\);/.test(fe)
    && /cfoPlanErrorSd: window\.SMPLOutlook/.test(fe) && /cashByMonth\.push\(cash\);/.test(fe));
  const mcCtx = { window: { SMPLPlanMc: planMc, SMPLOutlook: {
    getRiskPolicyValue: k => (mcCtx.policy[k] ?? null),
    riskPolicyNotSet: k => `Risk policy not set (${k})`,
  } }, policy: { arr_miss_tolerance: 0.005, cash_watch_shortfall: 0.25, cash_alarm_shortfall: 0.5 } };
  check(`${rel}: loads the shared lever sampler`, /<script src="\/shared\/smpl-plan-mc\.js\?v=\d+"><\/script>/.test(fe));
  vm.runInNewContext(`
    ${fe.match(/const FC_MC_METHOD = [^\n]+/)[0]}
    ${['fcPolicy', 'fcPolicyNotSet', 'fcMcPctl', 'fcMcMean', 'fcMcSd', 'fcMcHist', 'fcMcRng', 'fcMcGauss', 'fcMcNum', 'fcMcStats', 'runFcPacketMonteCarlo', 'fcMcHoldShare']
      .map(n => fnSource(fe, n)).join('\n')}
    this.api = { runFcPacketMonteCarlo, fcMcHoldShare };
  `, mcCtx);
  const { runFcPacketMonteCarlo, fcMcHoldShare } = mcCtx.api;
  const bare = runFcPacketMonteCarlo({ cashByMonth: Array(12).fill(12e6) }, { n: 200, seed: 1 });
  check(`${rel}: nothing loaded → no ARR, AE or floor rates and a flat path`,
    bare.arr === null && bare.p_arr_miss === null && bare.p_ae_short === null && bare.p_cash_below_floor === null
    && bare.cash.sd === 0 && bare.method_notes.some(n => /ARR is not simulated/.test(n)));
  check(`${rel}: no measured rail → hold share not shown`,
    fcMcHoldShare({ arr: null, cash: {}, p_arr_miss: null, p_cash_below_floor: null, p_ops_liquidity: null }) === null);
  const resid = runFcPacketMonteCarlo({ cashByMonth: Array(12).fill(12e6), endCash: 12e6, closeMonthIdx: 5, cfoPlanErrorSd: 2e5 }, { n: 4000, seed: 3 });
  check(`${rel}: closed months pinned; open-month noise is the measured CFO error`,
    resid.cash_path.monthly.slice(0, 6).every(m => m.p10 === 12e6 && m.p90 === 12e6)
    && Math.abs(resid.cash.sd / (2e5 * Math.sqrt(6)) - 1) < 0.06, String(resid.cash.sd));
  const growth = runFcPacketMonteCarlo({ bopArr: 90e6, decArr: 108e6, targetArr: 108e6, closeMonthIdx: 5 }, { n: 4000, seed: 2, priors: { yoyPp: 4 } });
  check(`${rel}: growth moves Dec ARR by BOP x shock over the open months`,
    Math.abs(growth.arr.sd / (90e6 * 0.04 * 0.5) - 1) < 0.06 && growth.p_arr_miss != null, String(growth.arr.sd));
  const plan = { bopArr: 90e6, decArr: 108e6, targetArr: 108e6, closeMonthIdx: 5, salesEnd: 40, aeNeeded: 38 };
  const unfitted = runFcPacketMonteCarlo(plan, { n: 300, seed: 4 });
  check(`${rel}: no fitted prior → no lever drawn, ARR miss and AE short not reported, and said so`,
    JSON.stringify(unfitted.sig) === '{}' && unfitted.p_arr_miss === null && unfitted.p_ae_short === null
    && unfitted.method_notes.some(n => /No ARR lever is drawn/.test(n)) && unfitted.method_notes.some(n => /Sales attrition is not drawn/.test(n))
    && unfitted.method_notes.some(n => /Not drawn \(no fitted prior\): ARR growth, cost per lead, sales attrition, pipeline coverage/.test(n)));
  const attrOnly = runFcPacketMonteCarlo(plan, { n: 300, seed: 4, priors: { attrPp: 10 } });
  check(`${rel}: a fitted attrition prior reports AE short only`,
    attrOnly.p_ae_short != null && attrOnly.p_arr_miss === null && JSON.stringify(attrOnly.sig) === '{"attrPp":10}');
  const corr = runFcPacketMonteCarlo({ ...plan, openNb: 20e6, pipelineCoverage: 3 },
    { n: 4000, seed: 5, priors: { yoyPp: 4, pipe: 0.5 }, correlations: { 'yoyPp:pipe': 0.9, 'yoyPp:attrPp': 0.5 } });
  check(`${rel}: fitted correlations between drawn levers are applied; pairs with an undrawn lever are dropped`,
    JSON.stringify(corr.correlations) === '{"yoyPp:pipe":0.9}' && corr.method_notes.some(n => /Correlated levers: yoyPp:pipe ρ=0\.90/.test(n)));
  mcCtx.policy = {};
  const unset = runFcPacketMonteCarlo({ bopArr: 90e6, decArr: 108e6, targetArr: 108e6, closeMonthIdx: 5, cashByMonth: Array(12).fill(12e6), endCash: 12e6, cashFloor: 5e6 }, { n: 500, seed: 2, priors: { yoyPp: 4 } });
  check(`${rel}: risk policy not set → ARR miss, watch, alarm and liquidity rates not reported, and said so`,
    unset.p_arr_miss === null && unset.cash.pWatch === null && unset.cash.pAlarm === null && unset.p_ops_liquidity === null
    && ['arr_miss_tolerance', 'cash_watch_shortfall', 'cash_alarm_shortfall'].every(k => unset.method_notes.some(n => n.includes(`Risk policy not set (${k})`))));
}

if (failed) {
  console.error(`\n${failed} check(s) failed`);
  process.exit(1);
}
console.log('\nall plan assurance check verifications passed');
