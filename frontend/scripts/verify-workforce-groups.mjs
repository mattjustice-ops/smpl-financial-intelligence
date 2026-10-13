/**
 * Workforce groups and the Budget Engine's beginning headcount: the shared department mapping, the start table
 * built from the year-end roster, the Forecast Engine using the same departments, and the Budget Engine reading
 * levels and pay from the roster instead of typed tables.
 *
 * Usage: node scripts/verify-workforce-groups.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, '..');
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

console.log('groups');
check('groupOf maps income-statement departments',
  wg.groupOf('Sales') === 'sales' && wg.groupOf('Customer Success') === 'cs' && wg.groupOf('Marketing') === 'marketing'
  && wg.groupOf('Engineering') === 'rd' && wg.groupOf('Product') === 'rd'
  && wg.groupOf('Finance') === 'ga' && wg.groupOf('G&A') === 'ga' && wg.groupOf('Support') === 'ga');
check('groupOf leaves unknown departments unmapped', wg.groupOf('Legal') === null && wg.groupOf('') === null);
const allDepts = wg.GROUPS.flatMap(g => g.depts);
check('each department belongs to one group', new Set(allDepts).size === allDepts.length);

const gv = wg.groupValues({ Engineering: [5, 6], Product: [2, null], Legal: [1, 1], Sales: [null, 3] }, 1);
check('groupValues sums loaded departments in a group', gv.values.rd === 6, JSON.stringify(gv.values));
check('groupValues keeps null where no department has a value', gv.values.marketing === null && gv.values.ga === null);
check('groupValues counts a department with a value', gv.values.sales === 3);
check('groupValues lists unmapped departments', gv.unmapped.length === 1 && gv.unmapped[0] === 'Legal');

console.log('levels');
const sorted = ['L10', wg.NO_LEVEL, 'L2', 'L9', 'L3'].sort(wg.levelOrder);
check('levels sort numerically with no level last', sorted.join(',') === `L2,L3,L9,L10,${wg.NO_LEVEL}`, sorted.join(','));

console.log('start table');
const rows = [
  { id: 'E1', dept: 'Engineering', lvl: 'L5', base: 150000, bonus: 15000 },
  { id: 'E2', dept: 'Engineering', lvl: 'L5', base: 130000, bonus: 13000 },
  { id: 'E3', dept: 'Product', lvl: 'L7', base: 200000, bonus: 0 },
  { id: 'E4', dept: 'Sales', lvl: 'L4', base: 90000, bonus: 0 },
  { id: 'E5', dept: 'Support', lvl: '', base: 60000, bonus: 3000 },
  { id: 'E6', dept: 'Finance', lvl: 'L6', base: null, bonus: 0 },
  { id: 'E7', dept: 'Legal', lvl: 'L6', base: 180000, bonus: 0 },
];
const t = wg.startTable(rows);
check('total counts mapped employees only', t.total === 6, String(t.total));
check('heads by group and level', t.heads.rd.L5 === 2 && t.heads.rd.L7 === 1 && t.heads.sales.L4 === 1);
check('salary is the level average base', t.comp.rd.L5.salary === 140000, String(t.comp.rd.L5.salary));
check('bonus % is level bonus over level base', Math.abs(t.comp.rd.L5.bonusPct - 10) < 1e-9, String(t.comp.rd.L5.bonusPct));
check('levels come from the data, lowest first', t.levels.rd.join(',') === 'L5,L7' && t.levels.ga.join(',') === `L6,${wg.NO_LEVEL}`, JSON.stringify(t.levels));
check('missing level is counted and kept as a head', t.missingLevel === 1 && t.heads.ga[wg.NO_LEVEL] === 1);
check('missing base is counted, adds a head and no pay', t.missingBase === 1 && t.heads.ga.L6 === 1 && t.comp.ga.L6.salary === 0);
check('unmapped departments are listed, not counted', t.unmapped.join(',') === 'Legal');
check('a group with no rows has no levels', t.levels.marketing.length === 0 && t.levels.cs.length === 0);
check('hire dates kept by group; missing ones counted',
  wg.startTable([{ dept: 'Sales', lvl: 'L4', base: 1, hire: '2024-02-01' }, { dept: 'Sales', lvl: 'L4', base: 1, hire: '' }])
    .hires.sales.join(',') === '2024-02-01' && t.missingHire === 6);
const empty = wg.startTable([]);
check('no roster gives an empty table', empty.total === 0 && wg.GROUPS.every(g => empty.levels[g.key].length === 0));

console.log('forecast engine uses the same departments');
for (const rel of ['public/forecast-engine/index.html', 'canonical/forecast-engine/index.html']) {
  const html = fs.readFileSync(path.join(root, rel), 'utf8');
  const block = /const FC_HC_DEPTS = \[([\s\S]*?)\];/.exec(html);
  check(`${rel} defines FC_HC_DEPTS`, !!block);
  if (!block) continue;
  const fc = {};
  for (const m of block[1].matchAll(/key:\s*'(\w+)'[^\n]*?srcDepts:\s*\[([^\]]*)\]/g)) {
    fc[m[1]] = [...m[2].matchAll(/'([^']+)'/g)].map(x => x[1]);
  }
  for (const g of wg.GROUPS) {
    check(`${rel} ${g.key} departments match`, JSON.stringify(fc[g.key]) === JSON.stringify(g.depts),
      `${JSON.stringify(fc[g.key])} vs ${JSON.stringify(g.depts)}`);
  }
  check(`${rel} has no extra groups`, Object.keys(fc).length === wg.GROUPS.length, Object.keys(fc).join(','));
}

console.log('budget engine reads levels and pay from the roster');
const be = fs.readFileSync(path.join(root, 'public/budget-engine/index.html'), 'utf8');
check('loads the shared workforce groups', /<script src="\/shared\/smpl-workforce-groups\.js[^"]*"><\/script>/.test(be));
for (const name of ['HC_LEVELS', 'HC_COMP_DEFAULTS', 'HC_ROLLUP', 'avgCost', 'corpBonus', 'hcStartByLevel', 'hcCompByLevel',
  'updateHcStart', 'updateHcSalary', 'updateHcBonusPct', 'seedHcComp']) {
  check(`no ${name}`, !new RegExp(`\\b${name}\\b`).test(be));
}
check('beginning heads come from the year-end roster', /wf\.year_end_roster/.test(be) && /wf\.year_end_month/.test(be));
check('roster gaps are flagged on the Headcount tab', /function hcDataFlags\(/.test(be) && /\$\{hcDataFlags\(\)\}/.test(be));
check('dept-total hires spread over roster levels', !/\.l3\b/.test(be));
check('non-sales hires default to the prior-year net-add pace',
  /function hcPriorYearNetAdds\(/.test(be) && /const annual = hcPriorYearNetAdds\(d\.key\)/.test(be)
  && /STATE\.hcHiresSeeded = true/.test(be) && /\$\{hcNetAddsSummary\(\)\}/.test(be));
check('reset reseeds hires from the data', /STATE\.hcHiresByLevel = \{\};\s*STATE\.hcHiresSeeded = false;/.test(be));

if (failed) {
  console.error(`\n${failed} check(s) failed`);
  process.exit(1);
}
console.log('\nall workforce group checks passed');
