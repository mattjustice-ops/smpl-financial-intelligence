/**
 * Budget Engine P&L and cash drivers come from the loaded GL and statements: department lines from GL expense
 * types, stock comp from the GL, cost of revenue / D&A / interest / tax / capex / prepaids from the prior year,
 * and no typed dollar amounts or rates standing in for them.
 *
 * Usage: node scripts/verify-budget-gl-plan.mjs
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

console.log('budget engine has no typed spend or rates');
check('no typed flatMonthly amounts', !/flatMonthly:\s*[\d.]/.test(be));
check('no typed G&A pay shares', !/payShare:\s*[\d.]/.test(be));
check('no percent-of-pay lines', !/\bpctPay\b/.test(be) && !/\bplRates\b/.test(be));
for (const k of ['cogsPctRev', 'capexPctRev', 'prepaidMonthlyDelta', 'taxRatePct']) {
  check(`STATE.${k} defaults to data (null)`, new RegExp(`\\n  ${k}: null,`).test(be));
}
for (const k of ['sbcPctRev', 'arPctRev', 'apPctOpex', 'planArPct', 'planApPct']) {
  check(`no ${k}`, !new RegExp(`\\b${k}\\b`).test(be));
}
check('no typed D&A or interest', !/const da = \d/.test(be) && !/const interest = \d/.test(be));
check('no typed tax rate', !/pretax \* 0\.\d/.test(be));
check('no cash target text', !/\$30M Dec cash/.test(be));

console.log('quarter cash columns roll forward');
{
  const start = be.indexOf('function quarterCfCtxCell(');
  let depth = 0, end = -1;
  for (let i = be.indexOf('{', start); i < be.length; i++) {
    if (be[i] === '{') depth += 1;
    else if (be[i] === '}' && --depth === 0) { end = i + 1; break; }
  }
  const ctx = {
    fmtM: v => (v / 1e6).toFixed(2),
    rows: {
      '2026-01': { beginning_cash: 29.47e6, ending_cash: 28.79e6, net_change: -0.68e6 },
      '2026-02': { beginning_cash: 28.79e6, ending_cash: 27.87e6, net_change: -0.92e6 },
      '2026-03': { beginning_cash: 27.87e6, ending_cash: 29.08e6, net_change: 1.21e6 },
    },
  };
  ctx.tsStmtRow = p => ctx.rows[p] || null;
  vm.runInNewContext(`${be.slice(start, end)}; this.f = quarterCfCtxCell;`, ctx);
  const q = { months: ['2026-01', '2026-02', '2026-03'] };
  const beg = Number(ctx.f(q, { k: 'beginning_cash' })), net = Number(ctx.f(q, { k: 'net_change' })), endC = Number(ctx.f(q, { k: 'ending_cash' }));
  check('quarter opens at its first month and closes at its last', beg === 29.47 && endC === 29.08, `${beg} / ${endC}`);
  check('quarter beginning + net change = ending', Math.abs(beg + net - endC) < 0.011, `${beg} + ${net} vs ${endC}`);
}

console.log('budget engine reads the GL and statements');
check('department lines come from GL expense types', /function plGlSectionLines\(/.test(be) && /getWarehouseGlExpenseTypes/.test(be));
check('G&A split by run-rate GL wages', /function plGaSections\(/.test(be) && /PL_GL_WAGES_TYPE/.test(be));
check('stock comp scales with planned heads', /from === 'gl_sbc'/.test(be) && /HC_BOP_LOCK\[sec\.hcKey\]/.test(be));
check('cost of revenue rate from the prior year', /priorYearPctRev\('is', 'cogs'\)/.test(be));
check('capex rate from the prior year', /priorYearPctRev\('cfs', 'capex'\)/.test(be));
check('D&A and interest at the prior-year run-rate', /priorYearIsRunRate\('da'\)/.test(be) && /priorYearIsRunRate\('interest'\)/.test(be));
check('prepaids from loaded balance sheets', /getLoadedStatementRow\(p, 'bs'/.test(be));
check('cash add-back uses planned stock comp', /const sbc = r\.sbc \|\| 0;/.test(be));
check('missing drivers are flagged', /statement drivers not loaded/.test(be) && /Cash-flow drivers not loaded/.test(be)
  && /expense type for \$\{plRunRateLabel\(\)\} is not loaded/.test(be));

console.log('payroll types match the backend GL payroll mapping');
const py = fs.readFileSync(path.join(repo, 'backend/app/services/workforce/gl_payroll.py'), 'utf8');
const pySet = name => {
  const m = new RegExp(`${name} = frozenset\\(\\{([^}]*)\\}\\)`).exec(py);
  return m ? [...m[1].matchAll(/"([^"]+)"/g)].map(x => x[1]) : null;
};
const backendPay = ['WAGES_TYPES', 'BONUS_TYPES', 'BENEFITS_TYPES', 'COMMISSION_TYPES'].map(pySet);
check('backend payroll type sets found', backendPay.every(Boolean));
const elsewhere = /const PL_GL_PLANNED_ELSEWHERE = new Set\(\[([\s\S]*?)\]\);/.exec(be);
check('PL_GL_PLANNED_ELSEWHERE defined', !!elsewhere);
if (elsewhere && backendPay.every(Boolean)) {
  const fe = new Set([...elsewhere[1].matchAll(/'([^']+)'/g)].map(x => x[1].toLowerCase()));
  const missing = backendPay.flat().filter(t => !fe.has(t));
  check('every backend payroll type is planned on Headcount or commissions', missing.length === 0, missing.join(', '));
  check('marketing programs are planned on GTM', fe.has('marketing programs'));
}

console.log('outlook exposes GL expense types');
for (const rel of ['public/shared/smpl-outlook.js', 'canonical/shared/smpl-outlook.js']) {
  const src = fs.readFileSync(path.join(root, rel), 'utf8');
  check(`${rel} hydrates gl_expense_types`, /TS_BLOCKS = \[[^\]]*"gl_expense_types"/.test(src));
}
check('canonical smpl-outlook.js matches public',
  fs.readFileSync(path.join(root, 'public/shared/smpl-outlook.js'), 'utf8')
  === fs.readFileSync(path.join(root, 'canonical/shared/smpl-outlook.js'), 'utf8'));

const win = { SMPL_CLOSE_MONTH: '2026-06', addEventListener() {}, removeEventListener() {} };
win.window = win;
vm.runInNewContext(fs.readFileSync(path.join(root, 'public/shared/smpl-outlook.js'), 'utf8'), { window: win, console });
const SO = win.SMPLOutlook;
check('getWarehouseGlExpenseTypes exported', typeof SO.getWarehouseGlExpenseTypes === 'function');
check('getLoadedStatementRow exported', typeof SO.getLoadedStatementRow === 'function');
win.SMPL_DEMO_TS_DATA = {
  Actual: { gl_expense_types: { '2026-05': { 'ga|Finance|Software': 10 } }, bs: { '2026-05': { prepaids: 7 } } },
  Forecast: { gl_expense_types: { '2026-11': { 'ga|Finance|Software': 20 } }, bs: { '2026-12': { prepaids: 9 } } },
};
win.SMPL_HISTORY = { bs: { '2025-12': { prepaids: 5 } } };
check('closed month reads Actual', SO.getWarehouseGlExpenseTypes('2026-05', '2026-06')['ga|Finance|Software'] === 10);
check('open month reads Forecast', SO.getWarehouseGlExpenseTypes('2026-11', '2026-06')['ga|Finance|Software'] === 20);
check('month not loaded reads null', SO.getWarehouseGlExpenseTypes('2026-08', '2026-06') === null);
check('statement row reads HISTORY for prior years', SO.getLoadedStatementRow('2025-12', 'bs', '2026-06').prepaids === 5);
check('statement row reads Forecast after close', SO.getLoadedStatementRow('2026-12', 'bs', '2026-06').prepaids === 9);

console.log('backend sends GL expense types');
const payload = fs.readFileSync(path.join(repo, 'backend/app/services/reporting/three_statement_payload.py'), 'utf8');
check('scenario block includes gl_expense_types', /"gl_expense_types":/.test(payload) && /build_expense_type_rows\(/.test(payload));

if (failed) {
  console.error(`\n${failed} check(s) failed`);
  process.exit(1);
}
console.log('\nall budget GL plan checks passed');
