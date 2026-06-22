import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import vm from "vm";

const dir = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(dir, "../public");
const html = fs.readFileSync(path.join(publicDir, "forecast-engine/index.html"), "utf8");

function extractSrcLiteral(source) {
  const marker = "const SRC=";
  const start = source.indexOf(marker);
  if (start < 0) return null;
  const brace = source.indexOf("{", start);
  if (brace < 0) return null;
  let depth = 0;
  let inStr = false;
  let strCh = "";
  let esc = false;
  for (let i = brace; i < source.length; i++) {
    const c = source[i];
    if (inStr) {
      if (esc) {
        esc = false;
        continue;
      }
      if (c === "\\") {
        esc = true;
        continue;
      }
      if (c === strCh) inStr = false;
      continue;
    }
    if (c === '"' || c === "'") {
      inStr = true;
      strCh = c;
      continue;
    }
    if (c === "{") depth++;
    else if (c === "}") {
      depth--;
      if (depth === 0 && source[i + 1] === ";") return source.slice(brace, i + 1);
    }
  }
  return null;
}

const srcLiteral = extractSrcLiteral(html);
if (!srcLiteral) {
  console.error("FAIL: could not extract SRC");
  process.exit(1);
}

const sandbox = { globalThis: {} };
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(publicDir, "shared/smpl-pipeline.js"), "utf8"), sandbox);
sandbox.SRC = vm.runInContext(`(${srcLiteral})`, sandbox);

const ALL_P = Array.from({ length: 12 }, (_, i) => `2026-${String(i + 1).padStart(2, "0")}`);
const r = sandbox.SMPLPipeline.computeArrSeries(ALL_P, "2026-06");
const dec = r.decEop;
const jun = r.byPeriod["2026-06"]?.arr_eop;
const wfDec = 97560000;

console.log("Pipeline Dec ARR:", dec, `(${(dec / 1e6).toFixed(2)}M)`);
console.log("Pipeline Jun ARR:", jun, `(${(jun / 1e6).toFixed(2)}M)`);
console.log("WF_TABLE Dec (stale demo):", wfDec, `(${(wfDec / 1e6).toFixed(2)}M)`);

if (Math.abs(dec - wfDec) < 1000) {
  console.error("FAIL: pipeline matches stale WF_TABLE — unexpected");
  process.exit(1);
}
if (dec < 90000000 || dec > 92000000) {
  console.error("FAIL: Dec ARR outside expected ~91.1M band:", dec);
  process.exit(1);
}
console.log("OK: Board and Forecast Engine should both show", (dec / 1e6).toFixed(2) + "M Dec at default levers");
