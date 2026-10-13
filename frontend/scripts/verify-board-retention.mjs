/**
 * Board retention is the loaded monthly NRR/GRR: the live RETENTION block when signed in, the
 * embedded seed when signed out, nothing otherwise. The seed must equal SRC.actuals retention.
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import vm from "vm";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");
let failures = 0;
function check(name, ok, detail = "") {
  if (ok) console.log(`OK    ${name}`);
  else {
    failures++;
    console.log(`FAIL  ${name}${detail ? `\n        ${detail}` : ""}`);
  }
}

function load(extra) {
  const win = { console, ...extra };
  win.window = win;
  vm.runInNewContext(fs.readFileSync(path.join(root, "public/shared/board-data.js"), "utf8"), win);
  return win;
}

const live = load({
  SMPL_OUTLOOK_PAYLOAD: { RETENTION: { Actual: { "2026-06": { nrr: 0.9981, grr: 0.9881 } }, Budget: { "2026-06": { nrr: 0.9963, grr: 0.9874 } } } },
  SMPL_DEMO_RETENTION: { Actual: { "2026-06": { nrr: 0.5, grr: 0.5 } } },
});
check("live Actual NRR comes from the payload", live.boardLoadedRetention("Actual", "2026-06", "nrr") === 0.9981);
check("live Budget GRR comes from the payload", live.boardLoadedRetention("Budget", "2026-06", "grr") === 0.9874);
check("a month not loaded is null", live.boardLoadedRetention("Actual", "2026-07", "nrr") === null);

const strict = load({ SMPL_OUTLOOK_PAYLOAD: {}, SMPL_DEMO_RETENTION: { Actual: { "2026-06": { nrr: 0.5 } } } });
check("live payload without RETENTION never falls back to the seed", strict.boardLoadedRetention("Actual", "2026-06", "nrr") === null);

const signedOut = load({ SMPL_DEMO_RETENTION: { Actual: { "2026-06": { nrr: 0.9981 } } } });
check("signed out reads the embedded seed", signedOut.boardLoadedRetention("Actual", "2026-06", "nrr") === 0.9981);

const html = fs.readFileSync(path.join(root, "public/board/index.html"), "utf8");
const seedLine = html.split("\n").find((l) => l.startsWith("var SMPL_DEMO_RETENTION="));
const srcLine = fs.readFileSync(path.join(root, "public/forecast-engine/index.html"), "utf8").split("\n").find((l) => l.startsWith("const SRC="));
check("board embeds a retention seed", !!seedLine);
if (seedLine && srcLine) {
  const seed = JSON.parse(seedLine.slice("var SMPL_DEMO_RETENTION=".length).replace(/;\s*$/, ""));
  const src = JSON.parse(srcLine.slice("const SRC=".length).replace(/;\s*$/, ""));
  const close = (html.match(/var CLOSE_MONTH\s*=\s*'(\d{4}-\d{2})'/) || [])[1];
  check("board snapshot close month found", !!close);
  const months = Object.keys(seed.Actual || {});
  const off = months.filter((p) => {
    const s = (src.actuals || {})[p] || {};
    return Math.abs(seed.Actual[p].nrr - s.nrr) > 1e-9 || Math.abs(seed.Actual[p].grr - s.grr) > 1e-9;
  });
  check("seeded Actual retention equals the seeded SRC.actuals", months.length > 0 && !off.length, off.join(", "));
  check("seed covers the close month", !close || !!(seed.Actual || {})[close], close);
  check("seed carries the Budget rate for the close month", !close || ((seed.Budget || {})[close] || {}).nrr != null, close);
}

console.log(failures ? `\n${failures} retention check(s) failed` : "\nAll board retention checks passed");
process.exit(failures ? 1 : 0);
