/**
 * The exec-summary verdict was hardcoded prose and kept asserting cash at 2.2x budget
 * after the re-anchor. Pull boardExecVerdict out of the board HTML and check that each
 * clause tracks the KPIs it claims to describe.
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import vm from "vm";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const html = fs.readFileSync(path.join(__dirname, "../public/board/index.html"), "utf8");

function extract(name) {
  const start = html.indexOf(`function ${name}(`);
  if (start < 0) throw new Error(`${name} not found in board/index.html`);
  let i = html.indexOf("{", start);
  let depth = 0;
  for (let j = i; j < html.length; j++) {
    if (html[j] === "{") depth++;
    else if (html[j] === "}") {
      depth--;
      if (depth === 0) return html.slice(start, j + 1);
    }
  }
  throw new Error(`unbalanced braces reading ${name}`);
}

const sandbox = { window: {}, console };
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(
  `
  const MON_ABBR = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const MON_FULL = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  let CLOSE_MONTH = '2026-06';
  const fM = (v,d) => {
    if (v==null || Number.isNaN(v)) return '-';
    var abs = Math.abs(v), neg = v < 0;
    if (abs >= 1e6) return (neg?'-$':'$') + (abs/1e6).toFixed(d) + 'M';
    if (abs >= 1e3) return (neg?'-$':'$') + (abs/1e3).toFixed(0) + 'K';
    return (neg?'-$':'$') + abs.toFixed(d) + 'M';
  };
  const fM1 = v => fM(v, 1);
  ${extract("boardCloseParts")}
  ${extract("boardExecVerdict")}
  `,
  sandbox,
);

let failures = 0;
function check(name, cond, detail) {
  if (cond) console.log(`OK    ${name}`);
  else {
    failures++;
    console.log(`FAIL  ${name}\n        ${detail}`);
  }
}

function verdict(k, closeMonth = "2026-06", nnAct = null) {
  sandbox.CLOSE_MONTH = closeMonth;
  vm.runInContext(`CLOSE_MONTH = ${JSON.stringify(closeMonth)};`, sandbox);
  sandbox.window.NN_ACT = nnAct || [];
  return sandbox.boardExecVerdict(k);
}

// Live June-2026 production shape: cash back in line with budget after the re-anchor.
const live = {
  idx: 5,
  arrVar: 0.58,
  nn: 1.31,
  gmVarPp: 0.4,
  cashAct: 50.26,
  cashBud: 49.1,
  ebitdaAct: 0.6615,
  ebitdaBud: 0.6475,
};
const nnYear = [0.9, 1.0, 1.1, 1.2, 1.25, 1.31];
const s = verdict(live, "2026-06", nnYear);
console.log(`\n  live: ${s}\n`);
check("no stale 2.2x cash claim when cash is in line", !s.includes("2.2\u00d7"), s);
check("cash reads as in line with budget", s.includes("cash in line with budget"), s);
check("ARR variance is the real number", s.includes("$0.6M ahead of plan") || s.includes("$0.58M ahead of plan"), s);
check("June close frames as H1", s.startsWith("H1 closed"), s);

// Cash genuinely well above budget should still say so.
const rich = verdict({ ...live, cashAct: 108.0, cashBud: 49.1 }, "2026-06", nnYear);
check("a real 2.2x cash position is still reported", rich.includes("2.2\u00d7 budget"), rich);

// Cash below budget must not be narrated as headroom.
const poor = verdict({ ...live, cashAct: 30.0, cashBud: 49.1, gmVarPp: -0.6 }, "2026-06", nnYear);
check("cash below budget is called out", poor.includes("% below budget"), poor);
check("downside does not claim headroom", !poor.includes("headroom"), poor);
check("margin compression is named", poor.includes("margin compression"), poor);

// The superlative must only appear in the month that is actually the strongest.
const notBest = verdict({ ...live, nn: 0.95 }, "2026-06", [0.9, 1.4, 1.1, 1.2, 1.25, 0.95]);
check("no false record-month claim", !notBest.includes("strongest net new"), notBest);
check("reports the actual net new instead", notBest.includes("net new ARR of"), notBest);

const isBest = verdict(live, "2026-06", nnYear);
check("records the record month when true", isBest.includes("strongest net new ARR month"), isBest);

// ARR behind plan must flip the wording.
const behind = verdict({ ...live, arrVar: -1.4 }, "2026-06", nnYear);
check("behind plan is stated as behind", behind.includes("behind plan"), behind);

// Period framing follows the close month.
check("December closes frame as FY", verdict(live, "2026-12", nnYear).startsWith("FY closed"), "");
const march = verdict(live, "2026-03", nnYear);
check("a mid-quarter close names the month", march.startsWith("March closed"), march);
check("horizon after March is H1", march.includes("H1 headroom"), march);

// EBITDA behind budget keeps the monitoring clause.
const ebitDown = verdict({ ...live, ebitdaAct: 0.5, ebitdaBud: 0.7 }, "2026-06", nnYear);
check("EBITDA shortfall warrants monitoring", ebitDown.includes("warrants monitoring"), ebitDown);

// $14.0K on $647.5K of budget is rounding, not a story.
check("immaterial EBITDA variance is left out", !s.includes("EBITDA"), s);
check("no $0.0M artefacts anywhere", !s.includes("$0.0M"), s);
const ebitUp = verdict({ ...live, ebitdaAct: 0.9, ebitdaBud: 0.7 }, "2026-06", nnYear);
check("material EBITDA beat is reported", ebitUp.includes("EBITDA $0.2M ahead"), ebitUp);
// Sub-$0.1M variances are the ones fM1 flattens to $0.0M; those must render in K.
const ebitSmall = verdict({ ...live, ebitdaAct: 0.62, ebitdaBud: 0.7 }, "2026-06", nnYear);
check("sub-$0.1M shortfall still narrated", ebitSmall.includes("warrants monitoring"), ebitSmall);
const arrSmall = verdict({ ...live, arrVar: 0.042 }, "2026-06", nnYear);
check("small ARR variance renders in K", arrSmall.includes("ARR $42K ahead of plan"), arrSmall);

// Missing inputs must not emit "undefined" or "NaN".
const sparse = verdict({ idx: 0 }, "2026-06", []);
check("degrades cleanly with no KPIs", !/undefined|NaN/.test(sparse), sparse);

console.log(
  failures ? `\n${failures} check(s) failed` : "\nAll exec-verdict checks passed",
);
process.exit(failures ? 1 : 0);
