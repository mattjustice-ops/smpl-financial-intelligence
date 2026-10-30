/**
 * The executive summary no longer carries the H1 verdict sentence or the
 * Validation Engine handoff. Those belonged to other pages.
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const html = fs.readFileSync(
  path.join(path.dirname(fileURLToPath(import.meta.url)), "../public/board/index.html"),
  "utf8",
);

const gone = [
  "function boardExecVerdict",
  "function boardCashContinuityHtml",
  "H1 closed",
  "Open Validation Engine",
  "Cash continuity",
];
const found = gone.filter((phrase) => html.includes(phrase));
if (found.length) {
  console.log("FAIL  executive summary still contains: " + found.join("; "));
  process.exit(1);
}
console.log("OK    executive summary leaves the verdict and validation handoff off the page");
