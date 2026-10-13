/**
 * Budget Engine payroll load comes from the loaded payroll policies: employer tax, health premium per head,
 * 401(k) match at the register's realized rate, merit month and rate, bonus payout terms and severance weeks.
 * No typed rates stand in for them; overrides default to null; gaps are flagged.
 *
 * Usage: node scripts/verify-budget-payroll-policies.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, '..');
const repo = path.join(root, '..');
const require = createRequire(import.meta.url);
const wg = require(path.join(root, 'public/shared/smpl-workforce-groups.js'));

let failed = 0;
function check(name, ok, detail = '') {
  if (ok) console.log(`  ok  ${name}`);
  else {
    failed += 1;
    console.error(`  FAIL ${name}${detail ? ` — ${detail}` : ''}`);
  }
}

const be = fs.readFileSync(path.join(root, 'public/budget-engine/index.html'), 'utf8');

/** Source of `function name(...) { ... }` from the Budget Engine, braces balanced. */
function fnSource(name) {
  const start = be.indexOf(`function ${name}(`);
  if (start < 0) return null;
  let depth = 0;
  for (let i = be.indexOf('{', start); i < be.length; i++) {
    if (be[i] === '{') depth += 1;
    else if (be[i] === '}' && --depth === 0) return be.slice(start, i + 1);
  }
  return null;
}

console.log('no typed payroll loads');
for (const k of ['meritPct', 'payrollTaxPct', 'healthPerHeadMonthly', 'k401Pct']) {
  check(`STATE.${k} defaults to the loaded policy (null)`, new RegExp(`\\n  ${k}: null,`).test(be));
  check(`reset clears ${k} to null`, new RegExp(`STATE\\.${k} = null;`).test(be));
}
for (const name of ['benefitsPct', 'benefitsLoadPct', 'bonusPayoutMonth', 'meritImpactMonth', 'HC_BONUS_CASH_MONTH',
  'hcMeritFactor', 'hcBonusPayoutMonth', 'priorBonusCash', 'bonusCash', 'setBenefits', 'setK401', 'setPayrollTax']) {
  check(`no ${name}`, !new RegExp(`\\b${name}\\b`).test(be));
}
check('no typed RIF severance weeks', !/weeks:\s*\d/.test(be));
check('commission payroll tax falls back to the policy, not a typed rate',
  /const policyTax = hcPayrollRates\(\)\.taxRate;/.test(be) && !/STATE\.payrollTaxPct \|\| 0/.test(be));
check('policy gaps are flagged on the Headcount tab', /msgs\.push\(\.\.\.hcPolicyFlags\(\)\);/.test(be));
check('payroll load uses the policy rates', /const rates = hcPayrollRates\(\);/.test(be)
  && /\(wages \+ bonusAccrual \+ severanceAmt\) \* \(rates\.taxRate \|\| 0\)/.test(be)
  && /\(onStaffFirst\[d\.key\] \|\| 0\) \* \(rates\.health\[moIdx\] \|\| 0\)/.test(be)
  && /\(wages \+ bonusAccrual\) \* \(rates\.k401Rate \|\| 0\)/.test(be));

console.log('policy rates from the payload');
const names = ['hcPolicy', 'hcPolicyNum', 'hcOverride', 'hcPayrollRates', 'hcPolicySeveranceWeeks', 'hcPolicyFlags'];
const srcs = names.map(fnSource);
check('policy functions found', srcs.every(Boolean), names.filter((n, i) => !srcs[i]).join(', '));
const BUD_P = Array.from({ length: 12 }, (_, i) => `2027-${String(i + 1).padStart(2, '0')}`);
const pol = (policy, value, from, to = null) => ({ policy, value, effective_from: from, effective_to: to, applies_to: '' });
const ctx = {
  BUD_P,
  STATE: { meritPct: null, payrollTaxPct: null, healthPerHeadMonthly: null, k401Pct: null },
  WF: {
    payroll_policies: {
      version: 'Forecast',
      policies: [
        pol('employer_payroll_tax_rate', 0.08, '2016-01'),
        pol('health_benefits_monthly', 1200, '2026-01', '2026-12'),
        pol('health_benefits_monthly', 1285, '2027-01', '2027-06'),
        pol('merit_increase_pct', 0.035, '2016-04'),
        pol('bonus_payout', 'monthly', '2016-01'),
        pol('severance_weeks_per_year', 2, '2016-01'),
        pol('severance_min_weeks', 4, '2016-01'),
        pol('severance_max_weeks', 26, '2016-01'),
      ],
      retirement_match_realized: { rate: 0.034, span: '2026-01 to 2026-12' },
    },
  },
  START: wg.startTable([
    { dept: 'Engineering', lvl: 'L5', base: 1, bonus: 0, hire: '2017-03-15' },
    { dept: 'Engineering', lvl: 'L5', base: 1, bonus: 0, hire: '2026-11-01' },
    { dept: 'Engineering', lvl: 'L5', base: 1, bonus: 0 },
  ]),
};
vm.runInNewContext(`
  function budgetWorkforce() { return WF; }
  function hcStart() { return START; }
  ${srcs.join('\n')}
  this.api = { hcPayrollRates, hcPolicySeveranceWeeks, hcPolicyFlags };
`, ctx);
const { hcPayrollRates, hcPolicySeveranceWeeks, hcPolicyFlags } = ctx.api;
let r = hcPayrollRates();
check('employer tax rate from the policy', r.taxRate === 0.08, String(r.taxRate));
check('health premium for the budget year, by month', r.health[0] === 1285 && r.health[5] === 1285, JSON.stringify(r.health));
check('health premium not loaded past its effective range', r.health[6] === null && r.health[11] === null);
check('401(k) at the register realized rate', r.k401Rate === 0.034);
check('merit rate and April month from the policy', r.meritRate === 0.035 && r.meritMonth === 3, `${r.meritRate} ${r.meritMonth}`);
check('bonus payout terms from the policy', r.loaded.bonusPayout === 'monthly');
const w = hcPolicySeveranceWeeks('rd', '2027-04', r);
check('severance weeks by completed service, within min/max, averaged', Math.abs(w - (20 + 4) / 2) < 1e-9, String(w));
check('employees without a hire date are counted as missing', ctx.START.missingHire === 1 && ctx.START.hires.rd.length === 2);
let flags = hcPolicyFlags();
check('health gap flagged with its months', flags.some(m => /Health premium policy is not loaded for 2027-07 to 2027-12/.test(m)), flags.join(' | '));
check('missing hire dates flagged', flags.some(m => /1 employee\(s\) have no hire date/.test(m)));

ctx.STATE.payrollTaxPct = 7.65;
ctx.STATE.healthPerHeadMonthly = 1000;
ctx.STATE.k401Pct = 3;
ctx.STATE.meritPct = 0;
r = hcPayrollRates();
check('overrides replace loaded values', Math.abs(r.taxRate - 0.0765) < 1e-12 && r.health.every(v => v === 1000)
  && r.k401Rate === 0.03 && r.meritRate === 0);
check('overrides keep the loaded values for display', r.loaded.taxRate === 0.08 && r.loaded.k401Rate === 0.034);

ctx.STATE.payrollTaxPct = ctx.STATE.healthPerHeadMonthly = ctx.STATE.k401Pct = ctx.STATE.meritPct = null;
ctx.WF.payroll_policies = undefined;
r = hcPayrollRates();
check('nothing loaded leaves every rate null', r.taxRate === null && r.k401Rate === null && r.meritRate === null
  && r.meritMonth === null && r.health.every(v => v === null) && r.sevPerYear === null);
flags = hcPolicyFlags();
for (const re of [/payroll tax rate policy is not loaded/, /401\(k\) match is not loaded/, /Merit policy is not loaded/,
  /Bonus payout policy is not loaded/, /Severance policy is not loaded/]) {
  check(`flag: ${re.source}`, flags.some(m => re.test(m)));
}

console.log('backend sends payroll policies');
const wfPy = fs.readFileSync(path.join(repo, 'backend/app/services/reporting/board_workforce.py'), 'utf8');
check('workforce payload includes payroll_policies', /"payroll_policies":/.test(wfPy) && /load_payroll_policies\(/.test(wfPy));
check('year-end roster rows carry hire dates', /"hire": e\.hire_date\.isoformat\(\)/.test(wfPy));
const polPy = fs.readFileSync(path.join(repo, 'backend/app/services/workforce/payroll_policies.py'), 'utf8');
check('policies read from the Forecast policy file', /PLAN_POLICY_VERSION = "Forecast"/.test(polPy)
  && /"forecast_payroll_policies"/.test(polPy));

if (failed) {
  console.error(`\n${failed} check(s) failed`);
  process.exit(1);
}
console.log('\nall budget payroll policy checks passed');
