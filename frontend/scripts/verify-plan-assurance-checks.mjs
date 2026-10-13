/**
 * Plan Assurance checks compare like with like:
 *  - jan_hc: the Budget's January opening heads (what the plan starts from) vs the prior-December
 *    forecast ending heads; the Forecast's close-month plan heads vs the loaded close total.
 *  - sm_tie: GTM program spend = what posts to the Marketing P&L channel lines, and that sits inside
 *    income-statement S&M. No implied S&M from a prior-year share.
 *  - cash_floor: the Budget floor is the loaded cash flow bridge `cash_floor`; none loaded is flagged.
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
};
vm.runInNewContext(`
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
check('floor breach still fails', byId({ ...healthy(), endCash: 8e6, minCash: 7e6 }).cash_floor.severity === 'high');

console.log('Forecast Engine');
for (const rel of ['public/forecast-engine/index.html', 'canonical/forecast-engine/index.html']) {
  const fe = fs.readFileSync(path.join(root, rel), 'utf8');
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

if (failed) {
  console.error(`\n${failed} check(s) failed`);
  process.exit(1);
}
console.log('\nall plan assurance check verifications passed');
