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

if (failed) {
  console.error(`\n${failed} check(s) failed`);
  process.exit(1);
}
console.log('\nall forecast-from-data checks passed');
