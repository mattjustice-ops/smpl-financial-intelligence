/**
 * Guard: Board HTML must not ship stale dual-SoT Dec ARR ($97.5M) or
 * Headcount ARR/Employee $233K (conflicts with ~$628K from ARR_ACT / HC).
 * Pipeline SoT Dec ARR is ~$91.08M (see verify-pipeline-arr.mjs).
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const targets = [
  "public/board/index.html",
  "canonical/board/index.html",
];

const banned = [
  { re: /\$97\.5M/, label: "stale $97.5M H2/Dec ARR (use pipeline ~$91.1M)" },
  { re: /97\.5M is now tracking/, label: "stale ahead-of-budget H2 ARR claim" },
  { re: /kpi-val">\$233K</, label: "Headcount KPI $233K (use ARR_PER_EMP ~$628K)" },
  { re: /ARR per employee improved from \$218K to \$233K/, label: "stale HC aria $233K" },
  { re: /\[76\.3,77\.8,79\.5,81\.4,83\.5,85\.5,87\.7,89\.8,91\.7,93\.7,95\.6,97\.5\]/, label: "stale ARR_ALL ending 97.5" },
];

let failed = false;
for (const rel of targets) {
  const full = path.join(root, rel);
  if (!fs.existsSync(full)) {
    console.error("MISSING:", rel);
    failed = true;
    continue;
  }
  const html = fs.readFileSync(full, "utf8");
  for (const b of banned) {
    if (b.re.test(html)) {
      console.error(`FAIL ${rel}: ${b.label}`);
      failed = true;
    }
  }
}

if (failed) process.exit(1);
console.log("OK: Board HTML clear of known dual-SoT stale ARR/HC literals");
