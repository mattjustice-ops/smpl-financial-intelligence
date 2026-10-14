/**
 * The Forecast and Budget Engines read their cash rails, severity cutoffs, case bands and management
 * levers from the company's plan risk policy (outlook RISK_POLICY, onboarding 7.43–7.58):
 *  - every key the engines read exists in the backend policy;
 *  - SMPLOutlook returns the declared value, or null (never a default) when unanswered;
 *  - the classifiers, severity rules and rails move with the policy and skip a cutoff that is not set;
 *  - no typed rail, band or lever is left in either engine.
 *
 * Usage: node scripts/verify-risk-policy-engines.mjs
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

const read = (rel) => fs.readFileSync(path.join(repo, rel), 'utf8');
const be = read('frontend/public/budget-engine/index.html');
const fe = read('frontend/public/forecast-engine/index.html');
const outlookSrc = read('frontend/public/shared/smpl-outlook.js');
const policyPy = read('backend/app/services/readiness/plan_risk_policy.py');

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

console.log('policy keys');
const backendKeys = new Map([...policyPy.matchAll(/\("([a-z_]+)", "(7\.\d\d)", "(share|count|amount)"\)/g)].map(m => [m[1], m[2]]));
check('backend policy lists 7.43–7.58', backendKeys.size === 16 && backendKeys.get('cash_watch_shortfall') === '7.43'
  && backendKeys.get('case_overspend_watch') === '7.58', String(backendKeys.size));
const usedKeys = new Set();
for (const src of [be, fe]) {
  for (const m of src.matchAll(/(?:paPolicy|fcPolicy|paPolicyNotSet|fcPolicyNotSet)\('([a-z_]+)'\)/g)) usedKeys.add(m[1]);
  for (const m of src.matchAll(/(?:PA|FC)_SEVERITY_POLICY = \[([^\]]+)\]/g)) {
    for (const k of m[1].matchAll(/'([a-z_]+)'/g)) usedKeys.add(k[1]);
  }
}
const unknown = [...usedKeys].filter(k => !backendKeys.has(k));
check('every key the engines read is a backend policy key', usedKeys.size >= 12 && !unknown.length, unknown.join(', '));

console.log('SMPLOutlook accessors');
const policy = {
  values: {
    cash_watch_shortfall: 0.25, cash_alarm_shortfall: 0.5, floor_hard_breach_share: 0.85,
    p_floor_watch: 0.05, p_floor_break: 0.15, p_cash_watch_watch: 0.12, p_cash_watch_break: 0.35,
    p_arr_miss_watch: 0.25, arr_miss_tolerance: 0.005, named_breaks_for_break: 2, program_cut: 0.15,
    dso_improvement_days: 5, case_cash_watch: 0.05, case_watch_amount: 1000000, case_break_amount: 2500000,
    case_overspend_watch: 0.2,
  },
  questions: Object.fromEntries(backendKeys),
  missing: [],
  conflicts: [],
};
const ctx = { window: { location: { search: '' }, addEventListener: () => {} } };
vm.runInNewContext(outlookSrc, ctx);
const O = ctx.window.SMPLOutlook;
check('accessors exported', typeof O.getRiskPolicyValue === 'function' && typeof O.riskPolicyNotSet === 'function');
check('no policy loaded → null', O.getRiskPolicyValue('cash_watch_shortfall') === null);
check('not-set text without a policy', O.riskPolicyNotSet('cash_watch_shortfall') === 'Risk policy not set');
ctx.window.SMPL_RISK_POLICY = policy;
check('declared value returned', O.getRiskPolicyValue('cash_alarm_shortfall') === 0.5 && O.getRiskPolicyValue('case_break_amount') === 2500000);
check('not-set text names the question', O.riskPolicyNotSet('program_cut') === 'Risk policy not set (onboarding 7.53)');
check('outlook hydrate carries RISK_POLICY', /global\.SMPL_RISK_POLICY = data\.RISK_POLICY \|\| null;/.test(outlookSrc));

const beFns = ['paPolicy', 'paPolicyNotSet', 'paPolicyPct', 'paPolicyGaps', 'paPolicySeverity', 'paCashRails',
  'paMcHoldShare', 'classifyScenarioOutcome'];
const feFns = ['fcPolicy', 'fcPolicyNotSet', 'fcPolicyPct', 'fcPolicyAmt', 'fcPolicySeverity', 'fcCashRailsM',
  'fcClassifyScenarioOutcome'];
const beSrc = beFns.map(n => fnSource(be, n));
const feSrc = feFns.map(n => fnSource(fe, n));
check('Budget policy functions found', beSrc.every(Boolean), beFns.filter((n, i) => !beSrc[i]).join(', '));
check('Forecast policy functions found', feSrc.every(Boolean), feFns.filter((n, i) => !feSrc[i]).join(', '));
vm.runInNewContext(
  `${beSrc.join('\n')}\n${feSrc.join('\n')}\n` +
  `this.api = { paPolicySeverity, paCashRails, paMcHoldShare, classifyScenarioOutcome, fcPolicySeverity, fcCashRailsM, fcClassifyScenarioOutcome };`,
  ctx,
);
const api = ctx.api;

console.log('Budget Engine reads the policy');
const base = { endCash: 20e6, cashFloor: 5e6, targetArr: 100e6, fyMkt: 10e6, fyEbitda: 1e6 };
const shock = (o) => ({ endCash: 20e6, minCash: 15e6, decArr: 100e6, fyMkt: 10e6, fyEbitda: 1e6, ...o });
check('cash drop at the alarm share breaks', api.classifyScenarioOutcome(base, shock({ endCash: 10e6 })).breaks.includes('Cash down ≥50% vs plan'));
const w = api.classifyScenarioOutcome(base, shock({ endCash: 19e6 }));
check('cash drop at the case watch share is a watch', w.status === 'watch' && w.watches.includes('Cash down ≥5% vs plan'));
check('drop under the case watch share holds', api.classifyScenarioOutcome(base, shock({ endCash: 19.1e6 })).status === 'ok');
check('ARR miss uses the tolerance', api.classifyScenarioOutcome(base, shock({ decArr: 99.4e6 })).watches.length === 1
  && api.classifyScenarioOutcome(base, shock({ decArr: 99.6e6 })).watches.length === 0);
check('overspend watch uses 7.58', api.classifyScenarioOutcome(base, shock({ fyMkt: 12.1e6 })).watches.includes('Marketing spend +20%')
  && api.classifyScenarioOutcome(base, shock({ fyMkt: 11.9e6 })).status === 'ok');
check('severity: named breaks at the policy count break', api.paPolicySeverity(2, 0, 0, 0) === 'break' && api.paPolicySeverity(1, 0, 0, 0) === 'watch');
check('severity: probabilities at the cutoffs', api.paPolicySeverity(0, 0.15, 0, 0) === 'break' && api.paPolicySeverity(0, 0.05, 0, 0) === 'watch'
  && api.paPolicySeverity(0, 0, 0.35, 0) === 'break' && api.paPolicySeverity(0, 0, 0.12, 0) === 'watch'
  && api.paPolicySeverity(0, 0, 0, 0.25) === 'watch' && api.paPolicySeverity(0, 0.04, 0.11, 0.24) === 'hold');
check('severity: an unmeasured rate is not tested', api.paPolicySeverity(0, null, null, null) === 'hold');
const rails = api.paCashRails([40, 30, 20], 5);
check('rails = plan less the policy shares', rails.watch[2] === 15 && rails.alarm[2] === 10);
const rails12 = api.paCashRails(Array(12).fill(20), 5);
check('Dec rails', rails12.watchDec === 15 && rails12.alarmDec === 10);
check('Forecast severity matches Budget severity',
  [[2, 0, 0, 0], [0, 0.15, 0, 0], [0, 0, 0.12, 0], [0, 0.04, 0.11, 0.24]].every(a => api.fcPolicySeverity(...a) === api.paPolicySeverity(...a)));

console.log('Forecast Engine reads the policy');
const fbase = { endCash: 20e6, cashFloor: 5e6, decArr: 100e6, fyEbitda: 1e6 };
const fshock = (o) => ({ endCash: 20e6, minCash: 15e6, decArr: 100e6, fyEbitda: 1e6, ...o });
check('case break amount', api.fcClassifyScenarioOutcome(fbase, fshock({ decArr: 97.4e6 })).status === 'break');
check('case watch amount', api.fcClassifyScenarioOutcome(fbase, fshock({ decArr: 98.9e6 })).status === 'watch'
  && api.fcClassifyScenarioOutcome(fbase, fshock({ decArr: 99.1e6 })).status === 'ok');
check('case cash watch share', api.fcClassifyScenarioOutcome(fbase, fshock({ endCash: 19.05e6 })).status === 'ok'
  && api.fcClassifyScenarioOutcome({ ...fbase, endCash: 10e6 }, fshock({ endCash: 9.5e6 })).status === 'watch');
check('Forecast rails', api.fcCashRailsM([20], 5).watch[0] === 15 && api.fcCashRailsM([20], 5).alarm[0] === 10);

console.log('unanswered policy is reported, not defaulted');
ctx.window.SMPL_RISK_POLICY = { values: Object.fromEntries(Object.keys(policy.values).map(k => [k, null])), questions: policy.questions };
check('no alarm or case watch → a 60% cash drop is not banded', api.classifyScenarioOutcome(base, shock({ endCash: 8e6 })).status === 'ok');
check('no tolerance → ARR miss not tested', api.classifyScenarioOutcome(base, shock({ decArr: 50e6 })).watches.length === 0);
check('floor breach still breaks', api.classifyScenarioOutcome(base, shock({ endCash: 4e6 })).status === 'break');
const none = api.paCashRails(Array(12).fill(20), 5);
check('no rails drawn', none.watch === null && none.alarm === null && none.watchDec === null && none.floor === 5);
check('severity: only a named break moves it', api.paPolicySeverity(5, 0.9, 0.9, 0.9) === 'watch' && api.paPolicySeverity(0, 0.9, 0.9, 0.9) === 'hold');
check('Forecast bands not set → hold', api.fcClassifyScenarioOutcome(fbase, fshock({ decArr: 90e6 })).status === 'ok');
check('hold share skips unmeasured rates', api.paMcHoldShare({ arr: { pMiss: null }, cash: { pBreak: 0.1, pWatch: null }, pOpsRisk: null }) === 0.9
  && api.paMcHoldShare({ arr: {}, cash: {} }) === null);

console.log('no typed rails, bands or levers left');
const typed = [
  [/pWatch25|pAlarm50|p_cash_watch_25/, 'old 25%/50% key names'],
  [/CASH_WATCH_PCT|FC_MATERIAL_|FC_CASH_WATCH/, 'typed case bands'],
  [/targetArr \* 0\.995/, 'typed 0.5% ARR tolerance'],
  [/fySpend \* 0\.15|openSpend \* 0\.15/, 'typed 15% program cut'],
  [/planDec \* 0\.(25|5)\b|dec \* 0\.(25|5)\b/, 'typed cash rails'],
  [/drop >= 0\.(25|50)|dropPct >= 0\.(25|50)|cashDropPct >= 0\.50/, 'typed drop cutoffs'],
  [/cashFloor \* 0\.85/, 'typed hard-breach share'],
  [/fyMkt \* 1\.2/, 'typed overspend watch'],
  [/Raise renewal pricing/, 'unsized renewal-pricing offset'],
  [/≥\$2\.5M|≥\$1M|≥3% cash|±5% ≈ noise|25%\/50% cash rails|\$1M \/ 3%|less than a million|impactM >= 1\.0/, 'typed band captions or $1M bar'],
  [/Math\.abs\(c\.d(Arr|Ebitda) \|\| 0\) \* 0\.\d+/, 'typed case impact weight'],
];
for (const [re, what] of typed) {
  const hits = [['Budget', be], ['Forecast', fe]].filter(([, s]) => re.test(s)).map(([n]) => n);
  check(`no ${what}`, !hits.length, hits.join(', '));
}

console.log('demo seed carries the company policy');
const seed = read('frontend/public/shared/smpl-demo-seed.js');
const seedLine = seed.split('\n').find(l => l.includes('g.SMPL_RISK_POLICY = '));
let seedPolicy = null;
try { seedPolicy = seedLine ? JSON.parse(seedLine.slice(seedLine.indexOf('g.SMPL_RISK_POLICY = ') + 'g.SMPL_RISK_POLICY = '.length, seedLine.lastIndexOf(';'))) : null; } catch { seedPolicy = null; }
check('seed sets SMPL_RISK_POLICY only when no live outlook did', !!seedLine && /if \(g\.SMPL_RISK_POLICY === undefined\)/.test(seedLine));
check('seed policy answers every backend question with no conflicts', !!seedPolicy
  && [...backendKeys.keys()].every(k => seedPolicy.values[k] != null) && !(seedPolicy.conflicts || []).length);

console.log('canonical copies match');
for (const rel of ['forecast-engine/index.html', 'shared/smpl-outlook.js', 'shared/smpl-demo-seed.js']) {
  const pub = read(`frontend/public/${rel}`);
  const can = read(`frontend/canonical/${rel}`);
  check(`canonical ${rel} = public`, pub === can);
}

if (failed) {
  console.error(`\n${failed} check(s) failed`);
  process.exit(1);
}
console.log('\nall risk policy checks passed');
