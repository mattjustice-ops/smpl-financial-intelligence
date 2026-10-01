/**
 * Budget full-plan Monte Carlo: seeded sampler reproducibility, correlation
 * handling, and the Budget Engine wiring to server-issued inputs.
 *
 * Usage: node scripts/verify-plan-assurance-mc.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
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
check('full-plan MC draws from the seeded sampler', /SMPLPlanMc\.createLeverSampler\(\{ seed, correlations: corr \}\)/.test(mcFn));
check('full-plan MC uses supplied priors, not hard-coded vols', /inputs\.priors/.test(mcFn) && !/yoyPp:\s*3\.2/.test(mcFn));
check('full-plan MC never uses Math.random', !/Math\.random/.test(mcFn));
check('suite runs full-plan first and packet model only on failure',
  /mc = await runScenarioMonteCarloAsync\([\s\S]*?\} catch \(e\) \{[\s\S]*?fetchServerMonteCarlo\(/.test(html));
check('summary records seed, correlations, engine and inputs hash',
  /seed: mc && mc\.seed != null/.test(html) && /inputs_hash: mc \?/.test(html) && /engine: mc \?/.test(html));

if (failed) {
  console.error(`\n${failed} check(s) failed.`);
  process.exit(1);
}
console.log('\nAll plan-assurance Monte Carlo checks passed.');
