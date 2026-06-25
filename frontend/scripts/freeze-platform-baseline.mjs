/**
 * One-shot sync: copy current public/ platform files → canonical/ and refresh MANIFEST.
 * Run from frontend/: node scripts/freeze-platform-baseline.mjs
 */
import { copyFileSync, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "url";
import { spawnSync } from "node:child_process";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const canonicalRoot = join(root, "canonical");

const PLATFORM_FILES = [
  "board/index.html",
  "board/pin_coordinates.json",
  "board/projection_params.json",
  "board/us_emea_basemap.svg",
  "forecast-engine/index.html",
  "shared/board-data.js",
  "shared/board-hydrate.js",
  "shared/smpl-skin.js",
  "shared/smpl-outlook.js",
  "shared/smpl-demo-seed.js",
  "shared/smpl-pipeline.js",
  "shared/smpl-bootstrap-demo.js",
  "shared/smpl-bootstrap-pipeline.js",
];

function copy(rel) {
  const from = join(root, "public", rel);
  const to = join(canonicalRoot, rel);
  if (!existsSync(from)) throw new Error("Missing " + from);
  mkdirSync(dirname(to), { recursive: true });
  copyFileSync(from, to);
  console.log("  copied", rel, "(" + statSync(to).size + " bytes)");
}

console.log("=== Freeze platform baseline (public → canonical) ===");
spawnSync(process.execPath, [join(root, "scripts/extract-demo-seed.mjs")], {
  cwd: root,
  stdio: "inherit",
});
for (const rel of PLATFORM_FILES) copy(rel);

const boardHtml = readFileSync(join(canonicalRoot, "board/index.html"), "utf8");
const forecastHtml = readFileSync(join(canonicalRoot, "forecast-engine/index.html"), "utf8");
const manifest = {
  label: "May 2026 demo-ready platform baseline (Board + Forecast Engine)",
  updated: new Date().toISOString().slice(0, 10),
  boardMarker:
    (boardHtml.match(/<!--\s*(SMPL_LIVE_BOARD[^>]*)\s*-->/) || [])[1] || "SMPL_LIVE_BOARD v2",
  forecastMarker:
    (forecastHtml.match(/<!--\s*(forecast-engine stability[^\n>]*)\s*-->/) || [])[1] ||
    "forecast-engine stability",
  files: PLATFORM_FILES,
  resetCommand: "npm run reset:platform",
  snapshotCommand: "npm run snapshot:platform",
  notes:
    "Live warehouse hydration, Claude commentary/copilot, exec summary tab links, MD&A + variance exports.",
};
writeFileSync(join(canonicalRoot, "MANIFEST.json"), JSON.stringify(manifest, null, 2) + "\n", "utf8");
console.log("Wrote canonical/MANIFEST.json");
console.log("Done. Commit frontend/canonical/ when ready.");
