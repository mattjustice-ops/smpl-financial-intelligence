/**
 * The Forecast Engine's ARR at default levers (smpl-pipeline.js over its embedded SRC and the loaded forecast
 * months in shared/smpl-demo-seed.js) must equal the Board's ARR waterfall, month by month.
 * Run from frontend/: node scripts/verify-pipeline-arr.mjs
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import vm from "vm";

const dir = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(dir, "../public");
const fcHtml = fs.readFileSync(path.join(publicDir, "forecast-engine/index.html"), "utf8");
const boardHtml = fs.readFileSync(path.join(publicDir, "board/index.html"), "utf8");

function lineValue(source, prefix) {
  const line = source.split("\n").find((l) => l.startsWith(prefix));
  if (!line) return undefined;
  return new Function("return (" + line.slice(prefix.length).replace(/\r$/, "").replace(/;$/, "") + ");")();
}

const SRC = lineValue(fcHtml, "const SRC=");
const seedBox = {};
seedBox.window = seedBox;
vm.createContext(seedBox);
vm.runInContext(fs.readFileSync(path.join(publicDir, "shared/smpl-demo-seed.js"), "utf8"), seedBox);
const baseline = seedBox.SMPL_BASELINE_ENGINE;
const wfMatch = boardHtml.match(/var SMPL_DEMO_WF_TABLE=(\{[\s\S]*?\n\});/);
const closeMatch = boardHtml.match(/^var CLOSE_MONTH = '(\d{4}-\d{2})';/m);
if (!SRC || !baseline || !wfMatch || !closeMatch) {
  console.error("FAIL: could not read SRC, seed SMPL_BASELINE_ENGINE, SMPL_DEMO_WF_TABLE or CLOSE_MONTH");
  process.exit(1);
}
const wf = new Function("return (" + wfMatch[1] + ");")();
const close = closeMatch[1];
const year = close.slice(0, 4);
const ALL_P = Array.from({ length: 12 }, (_, i) => `${year}-${String(i + 1).padStart(2, "0")}`);

const sandbox = {};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(publicDir, "shared/smpl-pipeline.js"), "utf8"), sandbox);
sandbox.SMPL_BASELINE_ENGINE = baseline;
const r = sandbox.SMPLPipeline.computeArrSeries(ALL_P, close, sandbox.SMPLPipeline.DEFAULT_LEVERS, SRC);

let failed = 0;
ALL_P.forEach((p, i) => {
  const got = r.byPeriod[p] && r.byPeriod[p].arr_eop;
  const want = wf.Ending[i];
  const ok = got != null && want != null && Math.abs(got - want) <= 1;
  if (!ok) failed++;
  console.log(`${ok ? "OK  " : "FAIL"} ${p} Forecast Engine ARR ${got} vs Board waterfall ${want}`);
});

delete sandbox.SMPL_BASELINE_ENGINE;
const deals = sandbox.SMPLPipeline.computeArrSeries(ALL_P, close, sandbox.SMPLPipeline.DEFAULT_LEVERS, SRC);
console.log(
  `info: open deals alone (probability-weighted, no loaded forecast months) imply ${ALL_P[11]} ARR ${(deals.decEop / 1e6).toFixed(2)}M ` +
    `vs loaded forecast ${(wf.Ending[11] / 1e6).toFixed(2)}M`,
);

if (failed) process.exit(1);
console.log(`OK: Board and Forecast Engine agree on ARR every month (${ALL_P[11]} ${(wf.Ending[11] / 1e6).toFixed(2)}M)`);
