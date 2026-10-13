/**
 * The close month comes from the loaded data everywhere:
 *  - hydrated outlook meta.close_month, else the demo seed's close, else the last Actual period loaded;
 *  - no typed close-month fallback in the engines, the board libraries or the outlook library;
 *  - with no data loaded, nothing is assumed (null / empty, and the engines stop at boot).
 *
 * Usage: node scripts/verify-close-month-from-data.mjs
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

const read = (rel) => fs.readFileSync(path.join(root, rel), 'utf8');
const files = [
  'shared/smpl-outlook.js', 'shared/board-data.js', 'shared/board-ledger.js', 'shared/board-hydrate.js',
  'shared/board-continuity.js', 'forecast-engine/index.html', 'budget-engine/index.html',
];

console.log('no typed close-month fallback');
const typedClose = /(\|\||\?\?)\s*['"]20\d\d-\d\d['"]|getActiveCloseMonth\(\s*['"]20\d\d|return\s+['"]20\d\d-\d\d['"]/;
for (const rel of files) {
  const src = read(`public/${rel}`);
  const m = src.match(typedClose);
  check(`${rel}`, !m, m && m[0]);
  if (fs.existsSync(path.join(root, `canonical/${rel}`))) {
    check(`canonical ${rel} matches public`, read(`canonical/${rel}`) === src);
  }
}
const be = read('public/budget-engine/index.html');
const fe = read('public/forecast-engine/index.html');
check('Budget Engine stops at boot with no close loaded', /if \(!CLOSE_MONTH\) throw new Error\('Budget Engine: no close month/.test(be));
check('Forecast Engine stops at boot with no close loaded', /if \(!cm\) throw new Error\('Forecast Engine: no close month/.test(fe));
check('engines resolve through the outlook library', /SMPLOutlook\.getActiveCloseMonth\(\)/.test(be) && /SMPLOutlook\.getActiveCloseMonth\(\)/.test(fe));
const board = read('public/board/index.html');
check('board snapshot close is written by the seed builder', /^var CLOSE_MONTH = '\d{4}-\d{2}';/m.test(board)
  && /var CLOSE_MONTH = '\$\{close\}';/.test(read('scripts/build-demo-seed-from-outlook.mjs')));

console.log('outlook library resolves the close from the data');
const outlookSrc = read('public/shared/smpl-outlook.js');
function outlook(win) {
  win.addEventListener = () => {};
  vm.runInNewContext(outlookSrc, { window: win, console });
  return win.SMPLOutlook;
}
const seeded = outlook({ SMPL_DEMO_TS_DATA: { Actual: { periods: ['2026-07', '2026-08', '2026-09'], is: {} }, Forecast: { is: {} } } });
check('before hydrate: last Actual period of the loaded data', seeded.getActiveCloseMonth() === '2026-09', String(seeded.getActiveCloseMonth()));
check('year periods follow that close', seeded.getOutlookYearPeriods({}).join(',') === Array.from({ length: 12 }, (_, i) => `2026-${String(i + 1).padStart(2, '0')}`).join(','));
const hydrated = outlook({ SMPL_CLOSE_MONTH: '2027-03', CLOSE_MONTH: '2027-03', SMPL_DEMO_TS_DATA: { Actual: { periods: ['2026-06'] } } });
check('hydrated close wins over the seed data', hydrated.getActiveCloseMonth() === '2027-03');
const empty = outlook({});
check('no data → no close (not a typed month)', empty.getActiveCloseMonth() === null);
check('no data → no year periods', Array.isArray(empty.getOutlookYearPeriods({})) && empty.getOutlookYearPeriods({}).length === 0);
check('no data → no alignment report', empty.buildAlignmentReport(null, null) === null);

if (failed) {
  console.error(`\n${failed} check(s) failed`);
  process.exit(1);
}
console.log('\nall close-month-from-data checks passed');
