/**
 * Budget ARR plan seeded from loaded history, not typed constants:
 *  - growth lever starts at the loaded trajectory, Dec (BUDGET_YEAR-1) ÷ Dec (BUDGET_YEAR-2) − 1, until the planner sets it;
 *  - plan months follow the average month-of-year share of each ARR component across closed history years;
 *  - no typed within-quarter weights, month tilt, +20% seed or monthly-rate fallback.
 *
 * Usage: node scripts/verify-budget-arr-from-data.mjs
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

console.log('no typed ARR seeding');
check('no typed within-quarter close weights', !/quarterCloseWeights|0\.22, 0\.30, 0\.48/.test(be));
check('no typed month tilt or HC blend', !/0\.035 \* i|0\.85 \* s \+ 0\.15/.test(be));
check('no +20% mix seed constant', !/MIX_SEED_YOY_PCT/.test(be));
check('growth lever default is not a typed target', /yoyEndingArrGrowthPct: 0,/.test(be) && !/yoyEndingArrGrowthPct: 20/.test(be));
check('no typed monthly-rate fallback', !/nb: 0\.014, exp: 0\.007/.test(be));
check('dead weight helpers removed', !/function monthWeightsFromHeads|function smoothYearWeights|function monthWeightsCloseByHistQuarter/.test(be));
check('planner edit marks the lever as set', /window\.setYoyGrowth = function\(pct\) \{\s*STATE\._yoyUserSet = true;/.test(be));

const outlook = fs.readFileSync(path.join(root, 'public/shared/smpl-outlook.js'), 'utf8');
const canonOutlook = fs.readFileSync(path.join(root, 'canonical/shared/smpl-outlook.js'), 'utf8');
check('history year exposes ARR components', /nb: field\("arr", "arr_nb"\)/.test(outlook) && /churn: field\("arr", "arr_churn"\)/.test(outlook));
check('canonical smpl-outlook.js matches public', outlook === canonOutlook);

console.log('seasonality and growth from loaded history');
const names = ['normalizeWeights', 'closedHistoryYears', 'closedYearSeasonality', 'planMonthWeights',
  'loadedPriorDecEndingArr', 'loadedYoyPct', 'syncPlanAnchors'];
const sources = names.map(n => fnSource(be, n));
check('functions found', sources.every(Boolean), names.filter((n, i) => !sources[i]).join(', '));

const MIX_KEYS = ['nb', 'exp', 'react', 'cont', 'churn'];
const series = (vals) => Object.fromEntries(MIX_KEYS.map(k => [k, vals.slice()]));
function makeCtx(hist, { close = '2026-06', bop = 90e6, userSet = false, yoy = 0 } = {}) {
  const ctx = {
    BUDGET_YEAR: 2027,
    CLOSE_MONTH: close,
    MO: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    MIX_KEYS,
    BOP_LOCK: null,
    STATE: { _yoyUserSet: userSet, yoyEndingArrGrowthPct: yoy },
    loadedDecEndingArr: () => bop,
    getHistRow: () => null,
    window: { SMPLOutlook: { getHistoryYear: (y) => hist[y] || null } },
  };
  vm.runInNewContext(`${sources.join('\n')}
    this.api = { closedHistoryYears, closedYearSeasonality, planMonthWeights, loadedYoyPct, syncPlanAnchors,
      get bop() { return BOP_LOCK; } };`, ctx);
  return ctx;
}

const flat = Array(12).fill(1);
const backLoaded = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 9];
const hist = {
  2024: { ...series(flat), eop: [...Array(11).fill(null), 62.5e6] },
  2025: { ...series(backLoaded), eop: [...Array(11).fill(null), 75e6] },
  2026: { ...series([...Array(6).fill(1), ...Array(6).fill(null)]), eop: Array(12).fill(null) },
};
const a = makeCtx(hist).api;
const years = a.closedHistoryYears();
check('closed years exclude the open budget-minus-one year', JSON.stringify(years) === '[2024,2025]', JSON.stringify(years));
const w = a.planMonthWeights('nb');
const expectDec = (1 / 12 + 9 / 20) / 2;
check('month weights average each closed year\'s monthly share', Math.abs(w[11] - expectDec) < 1e-12 && Math.abs(w.reduce((s, v) => s + v, 0) - 1) < 1e-12,
  `Dec ${w[11]} vs ${expectDec}`);

a.syncPlanAnchors();
const ctxSeed = makeCtx(hist);
ctxSeed.api.syncPlanAnchors();
check('growth seeded from the loaded trajectory (90.0 ÷ 75.0 − 1 = 20%)', Math.abs(ctxSeed.STATE.yoyEndingArrGrowthPct - 20) < 1e-9,
  String(ctxSeed.STATE.yoyEndingArrGrowthPct));
const ctxUser = makeCtx(hist, { userSet: true, yoy: 12.5 });
ctxUser.api.syncPlanAnchors();
check('planner-set growth is kept on reload', ctxUser.STATE.yoyEndingArrGrowthPct === 12.5);
const ctxNoPrior = makeCtx({});
ctxNoPrior.api.syncPlanAnchors();
check('no prior Dec ARR → trajectory not loaded, lever at 0 (flagged)', ctxNoPrior.api.loadedYoyPct() === null && ctxNoPrior.STATE.yoyEndingArrGrowthPct === 0);
const even = ctxNoPrior.api.planMonthWeights('nb');
check('no closed year → even months (flagged), not a typed shape', even.every(v => Math.abs(v - 1 / 12) < 1e-12));
check('ARR tab flags missing closed-year history', /No closed year of ARR history loaded/.test(be));

if (failed) {
  console.error(`\n${failed} check(s) failed`);
  process.exit(1);
}
console.log('\nall budget ARR-from-data checks passed');
