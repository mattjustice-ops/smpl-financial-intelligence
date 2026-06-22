import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const boardHtml = fs.readFileSync(
  path.join(__dirname, "../public/board/index.html"),
  "utf8"
);

const wfMatch =
  boardHtml.match(/const WF_TABLE = (\{[\s\S]*?\n\});[\r\n]+window\.SMPL_DEMO_WF_TABLE/) ||
  boardHtml.match(/const WF_TABLE = (\{[\s\S]*?\n\});/);
const tsMatch =
  boardHtml.match(/const TS_DATA=(\{[\s\S]*?\});[\r\n]+window\.SMPL_DEMO_TS_DATA/) ||
  boardHtml.match(/const TS_DATA=(\{[\s\S]*?\});[\r\n]+function tsGetPeriods/);

if (!wfMatch || !tsMatch) {
  console.error("Failed to extract demo constants", { wf: !!wfMatch, ts: !!tsMatch });
  process.exit(1);
}

const out = `/* Shared demo warehouse — single source for Board + Forecast Engine */
(function (g) {
  g.SMPL_DEMO_WF_TABLE = ${wfMatch[1]};
  g.SMPL_DEMO_TS_DATA = ${tsMatch[1]};
  if (g.SMPLOutlook && g.SMPLOutlook.registerDemoData) {
    g.SMPLOutlook.registerDemoData(g.SMPL_DEMO_TS_DATA, g.SMPL_DEMO_WF_TABLE);
  }
})(typeof window !== "undefined" ? window : globalThis);
`;

const target = path.join(__dirname, "../public/shared/smpl-demo-data.js");
fs.writeFileSync(target, out);
console.log("Wrote", target, out.length, "bytes");
