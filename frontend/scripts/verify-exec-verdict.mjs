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

// Live June-2026 production shape.
const live = {
  idx: 5,
  arrVar: 0.42,
  nn: 1.86,
  gmVarPp: -0.02,
  cashAct: 29.99,
  cashBud: 30.64,
  ebitdaAct: -0.17,
  ebitdaBud: -0.015,
  arrYearEnd: 90.29,
  arrYearEndBud: 96.1,
};
const nnYear = [1.31, 1.5, 1.69, 1.88, 2.06, 1.86];
const s = verdict(live, "2026-06", nnYear);
console.log(`\n  live: ${s}\n`);
check("June close frames as H1", s.startsWith("H1 closed"), s);
check("ARR variance is the real number", s.includes("ARR $0.4M ahead of plan"), s);
check("margin within display precision reads on budget", s.includes("gross margin on budget"), s);
check("cash states its variance, not a band", s.includes("cash $0.7M below budget"), s);
check("EBITDA states its variance", s.includes("EBITDA $0.2M below budget"), s);
check("outlook is the Forecast against the Budget at year-end",
  s.includes("the Forecast ends the year at $90.3M ARR, $5.8M behind the $96.1M Budget"), s);
check("no unsupported claims", !/in line|headroom|hold H2|warrants monitoring|timing/.test(s), s);
check("no $0.0M artefacts anywhere", !s.includes("$0.0M"), s);

const rich = verdict({ ...live, cashAct: 108.0, cashBud: 49.1, gmVarPp: 0.6 }, "2026-06", nnYear);
check("cash above budget states the amount", rich.includes("cash $58.9M above budget"), rich);
check("margin above budget states the points", rich.includes("gross margin 0.6pp above budget"), rich);
const ahead = verdict({ ...live, arrYearEnd: 97.0 }, "2026-06", nnYear);
check("a Forecast ahead of Budget says ahead", ahead.includes("$0.9M ahead of the $96.1M Budget"), ahead);
const noBud = verdict({ ...live, arrYearEndBud: null }, "2026-06", nnYear);
check("no Budget year-end ARR, no outlook clause", !noBud.includes("Forecast ends"), noBud);
check("December close has no outlook clause", !verdict(live, "2026-12", nnYear).includes("Forecast ends"), "");

// The superlative must only appear in the month that is actually the strongest.
const notBest = verdict({ ...live, nn: 0.95 }, "2026-06", [0.9, 1.4, 1.1, 1.2, 1.25, 0.95]);
check("no false record-month claim", !notBest.includes("strongest net new"), notBest);
check("reports the actual net new instead", notBest.includes("net new ARR of"), notBest);
const isBest = verdict({ ...live, nn: 2.1 }, "2026-06", [1.31, 1.5, 1.69, 1.88, 2.06, 2.1]);
check("records the record month when true", isBest.includes("strongest net new ARR month"), isBest);

const behind = verdict({ ...live, arrVar: -1.4 }, "2026-06", nnYear);
check("behind plan is stated as behind", behind.includes("behind plan"), behind);

check("December closes frame as FY", verdict(live, "2026-12", nnYear).startsWith("FY closed"), "");
const march = verdict(live, "2026-03", nnYear);
check("a mid-quarter close names the month", march.startsWith("March closed"), march);

// Sub-$0.1M variances are the ones fM1 flattens to $0.0M; those must render in K.
const ebitSmall = verdict({ ...live, ebitdaAct: 0.62, ebitdaBud: 0.7 }, "2026-06", nnYear);
check("sub-$0.1M EBITDA variance renders in K", ebitSmall.includes("EBITDA $80K below budget"), ebitSmall);
const arrSmall = verdict({ ...live, arrVar: 0.042 }, "2026-06", nnYear);
check("small ARR variance renders in K", arrSmall.includes("ARR $42K ahead of plan"), arrSmall);
const flat = verdict({ ...live, cashAct: 30.64, ebitdaAct: -0.015, arrVar: 0.0002 }, "2026-06", nnYear);
check("variances under $1K read as on budget / on plan",
  flat.includes("cash on budget") && flat.includes("EBITDA on budget") && flat.includes("ARR on plan"), flat);

// Missing inputs must not emit "undefined" or "NaN".
const sparse = verdict({ idx: 0 }, "2026-06", []);
check("degrades cleanly with no KPIs", !/undefined|NaN/.test(sparse), sparse);

console.log(
  failures ? `\n${failures} check(s) failed` : "\nAll exec-verdict checks passed",
);
process.exit(failures ? 1 : 0);
