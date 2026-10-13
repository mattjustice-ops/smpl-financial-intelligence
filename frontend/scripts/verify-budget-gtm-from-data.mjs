/**
 * Budget Engine GTM funnel comes from loaded data: FY ratios from the prior year's totals (marketing-
 * sourced share of NB, pipeline coverage, avg opportunity, MQL→opp, ACV), monthly CPL and MQL phasing
 * from the same month a year earlier, and channels/mix from the loaded GL program types.
 * No typed rates, channels or coverage stand in for them; gaps are null and flagged.
 *
 * Usage: node scripts/verify-budget-gtm-from-data.mjs
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

console.log('no typed GTM rates, channels or coverage');
for (const name of ['DEFAULT_GTM_RATES', 'GTM_CHANNELS', 'gtmChannelCplByPeriod', 'getGtmChannelCpl',
  'defaultGtmChannelCpl', 'channelCplInput', 'updateGtmChannelCpl', 'channelMqls', 'fyChMql']) {
  check(`no ${name}`, !new RegExp(`\\b${name}\\b`).test(be));
}
check('pipeline coverage override defaults to null', /\n  pipelineCoverageMult: null,/.test(be));
check('no typed coverage fallback', !/pipelineCoverageMult \|\| \d/.test(be) && !/pipelineMin: \d/.test(be));
check('no typed channel mix or CPL', !/defaultMix:|defaultCpl:/.test(be));
check('Marketing P&L channel lines come from the loaded GL program types',
  /plSection\('mkt', 'Marketing', 'marketing', plGroupDepts\('marketing'\), \(\) => gtmChannels\(\)\.map/.test(be));
check('GTM data gaps are rendered', /const flags = gtmDataFlags\(\);/.test(be));
check('assurance packet sends the effective and loaded coverage',
  /pipelineCoverage: pipelineCoverage\(\),/.test(be) && /pipelineMin: priorYearCoverage\(\),/.test(be));
check('Monte Carlo shocks the effective coverage', /const baseCov = pipelineCoverage\(\);/.test(be));
const outlook = fs.readFileSync(path.join(root, 'public/shared/smpl-outlook.js'), 'utf8');
check('shared loader exposes GL program rows', /getLoadedProgramRow: getLoadedProgramRow,/.test(outlook));
const canon = fs.readFileSync(path.join(root, 'canonical/shared/smpl-outlook.js'), 'utf8');
check('canonical smpl-outlook.js matches public', canon === outlook);

console.log('funnel math from loaded data');
const names = ['padMo', 'plLineSlug', 'loadedProgramByType', 'gtmChannels', 'loadedAvgAcv', 'gtmLoadedMonth',
  'gtmYearFunnel', 'gtmLoadedFyRates', 'priorYearCoverage', 'pipelineCoverage', 'gtmFyRates',
  'computeGtmFyFunnel', 'gtmMonthRatesFromHist', 'getGtmRates', 'defaultGtmChannelMix', 'getGtmChannelMix',
  'normalizeGtmChannelMix', 'allocateGtmChannels', 'computeGtmPlan', 'gtmDataFlags'];
const srcs = names.map(fnSource);
check('GTM functions found', srcs.every(Boolean), names.filter((n, i) => !srcs[i]).join(', '));
const constSrc = (name) => {
  const m = be.match(new RegExp(`const ${name} = [\\s\\S]*?;\\r?\\n`));
  return m ? m[0] : null;
};
const consts = ['GTM_FY_RATE_KEYS', 'GTM_MONTH_RATE_KEYS', 'GTM_RATE_LABELS', 'MO'].map(constSrc);
check('GTM constants found', consts.every(Boolean));

const months = (y) => Array.from({ length: 12 }, (_, i) => `${y}-${String(i + 1).padStart(2, '0')}`);
const PRIOR = months(2026);
const BUD_P = months(2027);
const funnel = {};
const programs = {};
const hist = {};
PRIOR.forEach((p, i) => {
  // Same-month ratios deliberately differ month to month; the plan must size on the year's totals.
  const opps = 40 + i * 2;
  funnel[p] = { mqls: 300 + i * 20, opportunities_created: opps, pipeline_arr_created: opps * (90000 + i * 5000), closed_won_arr: opps * 30000 };
  programs[p] = { 'sm|Marketing|Paid Search': 60000 + i * 1000, 'sm|Marketing|Events and Webinars': 40000, 'sm|Demand Gen|Paid Search': 10000 };
  hist[p] = { nb: 2_000_000 + i * 50000 };
});
const sum = (k, src = funnel) => PRIOR.reduce((s, p) => s + src[p][k], 0);
const FY = {
  mqls: sum('mqls'), opps: sum('opportunities_created'), pipe: sum('pipeline_arr_created'), won: sum('closed_won_arr'), nb: sum('nb', hist),
};
const ctx = {
  BUD_P, BUDGET_YEAR: 2027, CLOSE_MONTH: '2026-06',
  STATE: { pipelineCoverageMult: null, gtmFyOverrides: {}, gtmRatesByPeriod: {}, gtmChannelMixByPeriod: {}, _gtmCommittedMqls: null },
  window: {
    SMPL_OUTLOOK_PAYLOAD: { SRC: { gtm: { avg_acv: 148000 } } },
    SMPLOutlook: { getLoadedProgramRow: (p) => programs[p] || null },
  },
  loadedFunnel: (p) => funnel[p] || null,
  loadedProgramSpend: (p) => (programs[p] ? Object.values(programs[p]).reduce((a, b) => a + b, 0) : null),
  getHistRow: (p) => hist[p] || null,
  computeBudgetArr: () => Object.fromEntries(BUD_P.map((p, i) => [p, { nb: 2_400_000 + (i % 3 === 2 ? 900_000 : 0) }])),
};
vm.runInNewContext(`
  ${consts.join('\n')}
  let _gtmChannelsCache = { key: null, list: [] };
  ${srcs.join('\n')}
  this.api = { gtmChannels, gtmLoadedFyRates, gtmMonthRatesFromHist, priorYearCoverage, pipelineCoverage, gtmFyRates, computeGtmPlan, gtmDataFlags };
`, ctx);
const api = ctx.api;
const near = (a, b, tol = 1e-9) => a != null && Math.abs(a - b) <= tol * Math.max(1, Math.abs(b));

const chans = api.gtmChannels().map(c => c.key);
check('channels are the loaded GL program types', JSON.stringify(chans) === JSON.stringify(['Events and Webinars', 'Paid Search']), JSON.stringify(chans));
const fy = api.gtmLoadedFyRates();
check('sourced share = FY funnel closed-won ÷ FY NB ARR', near(fy.sourcedShare, FY.won / FY.nb));
check('coverage = FY pipeline ÷ FY closed-won', near(fy.coverage, FY.pipe / FY.won) && near(api.priorYearCoverage(), FY.pipe / FY.won));
check('avg opportunity = FY pipeline ÷ FY opportunities', near(fy.oppSize, FY.pipe / FY.opps));
check('MQL→opp = FY opportunities ÷ FY MQLs', near(fy.mqlOpp, FY.opps / FY.mqls));
check('ACV from the loaded closed deals', fy.avgAcv === 148000);
const m3 = api.gtmMonthRatesFromHist('2027-03');
check('monthly CPL = same month GL program spend ÷ MQLs', near(m3.cpl, ctx.loadedProgramSpend('2026-03') / funnel['2026-03'].mqls));
check('MQL phasing = same month share of FY MQLs', near(m3.mqlShare, funnel['2026-03'].mqls / FY.mqls));

const plan = api.computeGtmPlan();
const budNb = BUD_P.reduce((s, p) => s + ctx.computeBudgetArr()[p].nb, 0);
const fyMqls = BUD_P.reduce((s, p) => s + plan[p].mqls, 0);
check('FY MQLs = FY NB × last year\'s MQLs per NB dollar', near(fyMqls, budNb * FY.mqls / FY.nb, 1e-9), `${fyMqls} vs ${budNb * FY.mqls / FY.nb}`);
check('monthly MQLs follow last year\'s curve, not NB timing',
  BUD_P.every((p, i) => near(plan[p].mqls / fyMqls, funnel[PRIOR[i]].mqls / FY.mqls)));
const fySpend = BUD_P.reduce((s, p) => s + plan[p].spend, 0);
const priorSpend = PRIOR.reduce((s, p) => s + ctx.loadedProgramSpend(p), 0);
check('program spend scales last year\'s spend by NB growth', near(fySpend, priorSpend * budNb / FY.nb, 1e-9), `${fySpend} vs ${priorSpend * budNb / FY.nb}`);
const jan = plan['2027-01'];
check('spend = MQLs × same-month CPL and fully posts to channels', near(jan.spend, jan.mqls * api.gtmMonthRatesFromHist('2027-01').cpl)
  && near(jan.spend, jan.spendSized));
const janSpend = ctx.loadedProgramSpend('2026-01');
const searchShare = (programs['2026-01']['sm|Marketing|Paid Search'] + programs['2026-01']['sm|Demand Gen|Paid Search']) / janSpend;
check('channel mix = prior-year same-month GL share', near(jan.channels['Paid Search'].mix, searchShare));
check('no gaps flagged when everything is loaded', api.gtmDataFlags().length === 0, api.gtmDataFlags().join(' | '));

ctx.STATE.pipelineCoverageMult = FY.pipe / FY.won * 1.2;
ctx.STATE.gtmFyOverrides = { mqlOpp: FY.opps / FY.mqls / 2 };
const scaled = BUD_P.reduce((s, p) => s + api.computeGtmPlan()[p].mqls, 0);
check('coverage and ratio overrides flow through', near(scaled, fyMqls * 1.2 * 2, 1e-9), `${scaled} vs ${fyMqls * 2.4}`);
ctx.STATE.pipelineCoverageMult = null;
ctx.STATE.gtmFyOverrides = {};

delete funnel['2026-05'];
ctx.STATE.gtmRatesByPeriod = {};
ctx.STATE.gtmChannelMixByPeriod = {};
const gapPlan = api.computeGtmPlan();
check('an incomplete prior year leaves the funnel unsized, not filled',
  BUD_P.every(p => gapPlan[p].mqls === null && gapPlan[p].spend === 0) && api.pipelineCoverage() === null);
const flags = api.gtmDataFlags();
check('the missing month is flagged', flags.some(m => /2026 funnel or GL program spend is not fully loaded \(May\)/.test(m)), flags.join(' | '));

for (const p of PRIOR) { delete funnel[p]; delete programs[p]; }
ctx.STATE.gtmRatesByPeriod = {};
ctx.STATE.gtmChannelMixByPeriod = {};
const none = api.gtmDataFlags();
check('no channels flagged', none.some(m => /No GL marketing program spend loaded for 2026/.test(m)), none.join(' | '));

console.log('CS demand: planned expansion unless a churn-cover floor is set');
check('no typed churn-cover multiplier', /csChurnCoverageMult: null,/.test(be) && !/csChurnCoverageMult: \d/.test(be));
check('no floor while unset', /const csFloor = STATE\.csChurnCoverageMult != null \? churnBase \* STATE\.csChurnCoverageMult : 0;/.test(be));
check('no raw multiplier formatting', !/STATE\.csChurnCoverageMult\.toFixed/.test(be.replace(fnSource('csChurnCoverLabel') || '', '')));
const coverCtx = { STATE: { csChurnCoverageMult: null } };
vm.runInNewContext(`${fnSource('csChurnCoverLabel')}\nthis.label = csChurnCoverLabel;`, coverCtx);
check('unset reads "not set"', coverCtx.label() === 'not set');
coverCtx.STATE.csChurnCoverageMult = 1.2;
check('set reads the multiple', coverCtx.label() === '1.20×');

console.log('backend assurance rules match');
const constraints = fs.readFileSync(path.join(repo, 'backend/app/services/predictive_planning/constraints.py'), 'utf8');
check('no channel MQL identity rule', !/gtm_mql/.test(constraints));
check('pipeline floor comes from the packet', /params=\{"min_multiple": None\}/.test(constraints));

if (failed) {
  console.error(`\n${failed} check(s) failed`);
  process.exit(1);
}
console.log('\nall budget GTM-from-data checks passed');
