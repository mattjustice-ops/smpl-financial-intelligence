/**
 * Budget full-plan Monte Carlo: seeded sampler reproducibility, correlation
 * handling, the Budget Engine wiring to server-issued inputs, and how Budget
 * and Forecast bind persisted assessments to saved versions.
 *
 * Usage: node scripts/verify-plan-assurance-mc.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, '..');
const require = createRequire(import.meta.url);
const mc = require(path.join(root, 'public/shared/smpl-plan-mc.js'));

let failed = 0;
function check(name, ok, detail = '') {
  if (ok) console.log(`  ok  ${name}`);
  else {
    failed += 1;
    console.error(`  FAIL ${name}${detail ? ` — ${detail}` : ''}`);
  }
}

const PRIORS = { yoyPp: 1.7392, cplLog: 0.28, attrPp: 2.5, pipe: 0.55 };

/** Toy plan: same lever transforms as runScenarioMonteCarloAsync, simple outcome. */
function runToyPlan({ seed, priors, correlations, n = 1000 }) {
  const sampler = mc.createLeverSampler({ seed, correlations });
  const arr = [];
  let miss = 0;
  for (let i = 0; i < n; i++) {
    const z = sampler.next();
    const yoy = Math.max(0, 20 + z.yoyPp * priors.yoyPp);
    const cpl = Math.exp(z.cplLog * priors.cplLog);
    const pipe = Math.max(1, 3 + z.pipe * priors.pipe);
    const dec = 90e6 * (1 + yoy / 100) * (1 - 0.1 * (cpl - 1) + 0.01 * (pipe - 3));
    arr.push(dec);
    if (dec < 108e6 * 0.995) miss += 1;
  }
  const mean = arr.reduce((a, b) => a + b, 0) / n;
  const sd = Math.sqrt(arr.reduce((a, v) => a + (v - mean) ** 2, 0) / (n - 1));
  return { n, mean, sd, pMiss: miss / n };
}

function sampleCorr(seed, correlations, a, b, n = 20000) {
  const s = mc.createLeverSampler({ seed, correlations });
  const xs = [], ys = [];
  for (let i = 0; i < n; i++) {
    const z = s.next();
    xs.push(z[a]);
    ys.push(z[b]);
  }
  const mx = xs.reduce((p, v) => p + v, 0) / n;
  const my = ys.reduce((p, v) => p + v, 0) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) {
    sxy += (xs[i] - mx) * (ys[i] - my);
    sxx += (xs[i] - mx) ** 2;
    syy += (ys[i] - my) ** 2;
  }
  return sxy / Math.sqrt(sxx * syy);
}

console.log('Plan Assurance full-plan Monte Carlo checks');

check('sampler contract name matches backend SAMPLER', mc.SAMPLER === 'mulberry32_box_muller_cholesky_v1');
check('lever order matches backend LEVERS', mc.LEVERS.join(',') === 'yoyPp,cplLog,attrPp,pipe');

const a = runToyPlan({ seed: 42, priors: PRIORS, correlations: {} });
const b = runToyPlan({ seed: 42, priors: PRIORS, correlations: {} });
check('same seed + same inputs => identical summary', JSON.stringify(a) === JSON.stringify(b));

const c = runToyPlan({ seed: 43, priors: PRIORS, correlations: {} });
check('different seed => different draws', JSON.stringify(a) !== JSON.stringify(c));

const wider = runToyPlan({ seed: 42, priors: { ...PRIORS, yoyPp: 3.2 }, correlations: {} });
check('priors drive the spread (yoyPp 3.2 wider than 1.74)', wider.sd > a.sd, `${wider.sd} vs ${a.sd}`);

const corrA = runToyPlan({ seed: 42, priors: PRIORS, correlations: { 'yoyPp:cplLog': 0.6 } });
const corrB = runToyPlan({ seed: 42, priors: PRIORS, correlations: { 'yoyPp:cplLog': 0.6 } });
check('same seed + same correlations => identical summary', JSON.stringify(corrA) === JSON.stringify(corrB));
check('correlations change the joint outcome', JSON.stringify(corrA) !== JSON.stringify(a));

const ident = mc.createLeverSampler({ seed: 9, correlations: {} });
const u = mc.mulberry32(9);
const raw = () => {
  let x = 0, y = 0;
  while (x === 0) x = u();
  while (y === 0) y = u();
  return Math.sqrt(-2 * Math.log(x)) * Math.cos(2 * Math.PI * y);
};
const z0 = ident.next();
const e0 = [raw(), raw(), raw(), raw()];
check('no correlations => independent draws in lever order',
  mc.LEVERS.every((k, i) => Math.abs(z0[k] - e0[i]) < 1e-12));

const rho = sampleCorr(5, { 'yoyPp:cplLog': 0.8 }, 'yoyPp', 'cplLog');
check('rho=0.8 shows up in sampled shocks', Math.abs(rho - 0.8) < 0.03, `sample rho ${rho.toFixed(3)}`);
const rhoFree = sampleCorr(5, { 'yoyPp:cplLog': 0.8 }, 'attrPp', 'pipe');
check('unlisted pair stays independent', Math.abs(rhoFree) < 0.03, `sample rho ${rhoFree.toFixed(3)}`);

let threw = false;
try {
  mc.createLeverSampler({ seed: 1, correlations: { 'yoyPp:cplLog': 0.95, 'yoyPp:attrPp': 0.95, 'cplLog:attrPp': -0.95 } });
} catch {
  threw = true;
}
check('non positive-definite correlations are rejected (engine falls back)', threw);

const html = fs.readFileSync(path.join(root, 'public/budget-engine/index.html'), 'utf8');
check('Budget loads the shared sampler', /<script src="\/shared\/smpl-plan-mc\.js/.test(html));
check('Budget fetches server-issued inputs', /\/api\/v1\/predictive-planning\/mc-inputs/.test(html));
const mcFn = (html.match(/async function runScenarioMonteCarloAsync[\s\S]*?\r?\n}\r?\n/) || [''])[0];
check('found runScenarioMonteCarloAsync', mcFn.length > 0);
check('budget Monte Carlo runs the five scenario years',
  /pickMcScenario\(rng\)/.test(mcFn)
  && /stampScenario\(snap, planArr, planParts, planNet, hireHold, spec\)/.test(mcFn)
  && /mc\.prior_source = 'scenario_years'/.test(mcFn)
  && /STATE\._holdHireDemand = hireHold/.test(html)
  && !/createLeverSampler/.test(mcFn));
check('budget draw is the ten levers', mc.BUDGET_LEVERS.join(',') === 'nbLog,expLog,contLog,churnLog,billPp,cogsPp,cplLog,pipe,attrPp,attainPp');
{
  const ranked = mc.rankDriverEffects([
    { z: { nbLog: 1, cplLog: 0 }, cash: 5 },
    { z: { nbLog: -1, cplLog: 0 }, cash: -5 },
    { z: { nbLog: 0, cplLog: 1 }, cash: 1 },
    { z: { nbLog: 0, cplLog: -1 }, cash: -1 },
    { z: { nbLog: 1, cplLog: 1 }, cash: 6 },
    { z: { nbLog: -1, cplLog: -1 }, cash: -6 },
  ], ['nbLog', 'cplLog']);
  check('cash rank puts the larger lever first', ranked.main[0].key === 'nbLog' && Math.abs(ranked.main[0].dollarsPerSd) > Math.abs(ranked.main[1].dollarsPerSd));
}
check('full-plan MC takes its seed from the run, not a typed volatility', /inputs\.seed/.test(mcFn) && !/yoyPp:\s*3\.2/.test(mcFn));
check('full-plan MC never uses Math.random', !/Math\.random/.test(mcFn));
{
  const start = html.indexOf('function mcShareRng');
  const end = html.indexOf('async function runScenarioMonteCarloAsync');
  const ctx = { Math };
  vm.runInNewContext(html.slice(start, end), ctx);
  const rng = ctx.mcShareRng(42);
  const counts = { normal: 0, soft: 0, hard: 0 };
  let outside = 0;
  for (let i = 0; i < 1000; i++) {
    const picked = ctx.pickGrowthShare(rng);
    counts[picked.name] += 1;
    const band = { normal: [0.75, 1.25], soft: [0.40, 0.75], hard: [0, 0.40] }[picked.name];
    if (!band || picked.share < band[0] - 1e-9 || picked.share > band[1] + 1e-9) outside += 1;
  }
  check('1,000 seeded draws stay inside the growth bands', outside === 0, JSON.stringify(counts));
  check('the tested-year mix is about 70/20/10',
    Math.abs(counts.normal - 700) < 40 && Math.abs(counts.soft - 200) < 40 && Math.abs(counts.hard - 100) < 30,
    JSON.stringify(counts));
  const flat = ctx.bridgeForGrowthShare({ nb: 80, exp: 40, react: 0, cont: 10, churn: 10 }, 100, 0);
  const flatNet = flat.nb + flat.exp + flat.react - flat.cont - flat.churn;
  check('a zero share lands flat by cutting new business before the rest of the bridge',
    Math.abs(flatNet) < 1e-6 && flat.nb === 0 && flat.churn === 10 && flat.cont === 10);
  const mktRng = ctx.mcShareRng(42);
  let mktOutside = 0;
  let mktSum = 0;
  for (let i = 0; i < 1000; i++) {
    ctx.pickGrowthShare(mktRng);
    const mkt = ctx.pickTestingMarketing(mktRng);
    if (mkt < 0.5 - 1e-9 || mkt > 1.5 + 1e-9) mktOutside += 1;
    mktSum += mkt;
  }
  check('marketing is drawn on its own, from half the plan to half again', mktOutside === 0);
  check('marketing is centered on the plan', Math.abs(mktSum / 1000 - 1) < 0.05);
  const seen = {};
  const scenarioRng = ctx.mcShareRng(7);
  for (let i = 0; i < 1000; i++) seen[ctx.pickMcScenario(scenarioRng).id] = true;
  check('draws land on all five scenario years',
    ['paid_channels', 'demand_dries', 'reps_leave', 'customers_leave', 'cash_slower'].every(id => seen[id]));
  const paid = ctx.buildScenarioSpec('paid_channels', () => 1, 1, 40);
  check('a full year of expensive channels cuts growth and raises lead cost', paid.share < 1 && paid.cpl === 1.6);
  const half = ctx.pickScenarioTiming(() => 0);
  check('a six-month year that starts in January is half a year', half.months === 6 && half.weight === 0.5);
}
check('suite runs full-plan first and packet model only on failure',
  /mc = await runScenarioMonteCarloAsync\([\s\S]*?\} catch \(e\) \{[\s\S]*?fetchServerMonteCarlo\(/.test(html));
check('summary records seed, correlations, engine and inputs hash',
  /seed: mc && mc\.seed != null/.test(html) && /inputs_hash: mc \?/.test(html) && /engine: mc \?/.test(html));

const fc = fs.readFileSync(path.join(root, 'public/forecast-engine/index.html'), 'utf8');
const fcCanonical = fs.readFileSync(path.join(root, 'canonical/forecast-engine/index.html'), 'utf8');
check('Budget persists only when the plan matches the saved version',
  /persist: !!versionId/.test(html) && /budget_version_id: versionId/.test(html)
  && /_warehouseBudgetVersionFp === paPacketFingerprint\(packet\)/.test(html));
check('Budget save assesses the saved packet against the new version',
  /STATE\._warehouseBudgetVersionFp = paPacketFingerprint\(savedPacket\)/.test(html)
  && /fetchPlanAssessment\(\{ packet: savedPacket, orgId, simulation \}\)/.test(html));
check('Forecast persists only when the forecast matches the saved version',
  /persist: !!forecastVersionId/.test(fc) && /b\.fp === fcPaPacketFingerprint\(packet\)/.test(fc));
check('Forecast save assesses the saved packet against the new version',
  /forecast_version_id: draft\.id/.test(fc) && /fcSavePaBinding\(draft\.id, savedPacket, orgId\)/.test(fc));
check('Forecast reuses a simulation only for the same packet',
  /window\._forecastMcFp === planFp/.test(fc));
check('Forecast never keys assessments off an unset global version id', !/_warehouseForecastVersionId/.test(fc));
check('re-assessing the same version + simulation does not persist a duplicate',
  /persist: !!versionId && !prior/.test(html) && /persist: !!forecastVersionId && !prior/.test(fc));
check('canonical Forecast Engine matches public copy', fc === fcCanonical);

// Static handlers win over the /api/v1 rewrite in next.config.js, so these
// calls carry the session user to the API instead of bypassing auth.
for (const route of ['assess', 'simulate', 'mc-inputs', 'constraints', 'assessments']) {
  const file = path.join(root, `app/api/v1/predictive-planning/${route}/route.ts`);
  const src = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';
  check(`/predictive-planning/${route} goes through the authenticated proxy`,
    src.includes(`proxyToBackendAuthed(request, "/api/v1/predictive-planning/${route}")`));
}

if (failed) {
  console.error(`\n${failed} check(s) failed.`);
  process.exit(1);
}
console.log('\nAll plan-assurance Monte Carlo checks passed.');
