/**
 * Reset or snapshot the corrected Board + Forecast Engine platform baseline.
 *
 *   npm run reset:platform    — restore public/ from canonical/ (or git HEAD fallback)
 *   npm run snapshot:platform — freeze current public/ into canonical/ (after a good state)
 */
import { copyFileSync, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "url";
import { spawnSync } from "node:child_process";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = join(root, "..");
const canonicalRoot = join(root, "canonical");
const manifestPath = join(canonicalRoot, "MANIFEST.json");
const snapshot = process.argv.includes("--snapshot");

const PLATFORM_FILES = [
  { rel: "board/index.html", marker: "SMPL_LIVE_BOARD" },
  { rel: "board/pin_coordinates.json" },
  { rel: "board/projection_params.json" },
  { rel: "board/us_emea_basemap.svg" },
  { rel: "forecast-engine/index.html", marker: "forecast-engine stability" },
  { rel: "shared/board-data.js" },
  { rel: "shared/board-hydrate.js" },
  { rel: "shared/smpl-skin.js" },
  { rel: "shared/smpl-outlook.js" },
  { rel: "shared/smpl-demo-seed.js" },
];

function log(msg) {
  console.log(msg);
}

function publicPath(rel) {
  return join(root, "public", rel);
}

function canonicalPath(rel) {
  return join(canonicalRoot, rel);
}

function gitPath(rel) {
  return join("frontend", "public", rel).replace(/\\/g, "/");
}

function copyFile(fromPath, toPath, label) {
  if (!existsSync(fromPath)) {
    throw new Error(`Missing file: ${fromPath}`);
  }
  mkdirSync(dirname(toPath), { recursive: true });
  copyFileSync(fromPath, toPath);
  const rel = toPath.replace(root + "\\", "").replace(root + "/", "");
  log(`  ${label}  ${rel} (${statSync(toPath).size} bytes)`);
}

function validateMarkers(baseDir, label) {
  for (const entry of PLATFORM_FILES) {
    if (!entry.marker) continue;
    const path = join(baseDir, entry.rel);
    const text = readFileSync(path, "utf8");
    if (!text.includes(entry.marker)) {
      throw new Error(`${label} ${entry.rel} missing marker "${entry.marker}"`);
    }
  }
}

function canonicalComplete() {
  return PLATFORM_FILES.every((f) => existsSync(canonicalPath(f.rel)));
}

function writeManifest() {
  const boardHtml = readFileSync(canonicalPath("board/index.html"), "utf8");
  const forecastHtml = readFileSync(canonicalPath("forecast-engine/index.html"), "utf8");
  const manifest = {
    label: "June 2026 corrected platform baseline",
    updated: new Date().toISOString().slice(0, 10),
    boardMarker: (boardHtml.match(/<!--\s*(SMPL_LIVE_BOARD[^>]*)\s*-->/) || [])[1] || "SMPL_LIVE_BOARD v1",
    forecastMarker: (forecastHtml.match(/<!--\s*(forecast-engine stability[^\n>]*)\s*-->/) || [])[1] || "forecast-engine stability",
    files: PLATFORM_FILES.map((f) => f.rel),
    resetCommand: "npm run reset:platform",
    snapshotCommand: "npm run snapshot:platform",
  };
  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + "\n", "utf8");
  log(`Wrote frontend/canonical/MANIFEST.json`);
}

function runExtractDemoSeed() {
  const result = spawnSync(process.execPath, [join(root, "scripts/extract-demo-seed.mjs")], {
    cwd: root,
    stdio: "inherit",
  });
  if (result.status !== 0) {
    throw new Error("extract-demo-seed failed after reset");
  }
}

function restoreFromGit() {
  const paths = PLATFORM_FILES.map((f) => gitPath(f.rel));
  log("Canonical baseline incomplete — restoring from last committed git version…");
  const result = spawnSync("git", ["checkout", "HEAD", "--", ...paths], {
    cwd: repoRoot,
    stdio: "inherit",
  });
  if (result.status !== 0) {
    throw new Error("git checkout failed — commit a good platform state or run npm run snapshot:platform");
  }
}

function main() {
  log(snapshot ? "=== Snapshot platform baseline (public → canonical) ===" : "=== Reset platform baseline (canonical → public) ===");

  if (snapshot) {
    validateMarkers(join(root, "public"), "public");
    for (const entry of PLATFORM_FILES) {
      copyFile(publicPath(entry.rel), canonicalPath(entry.rel), "snapshot");
    }
    writeManifest();
    log("Snapshot complete. Commit frontend/canonical/ when ready.");
    return;
  }

  if (canonicalComplete()) {
    validateMarkers(canonicalRoot, "canonical");
    for (const entry of PLATFORM_FILES) {
      copyFile(canonicalPath(entry.rel), publicPath(entry.rel), "restore");
    }
  } else {
    restoreFromGit();
    validateMarkers(join(root, "public"), "public");
    log("Tip: run npm run snapshot:platform to freeze this state into frontend/canonical/ for faster resets.");
  }

  log("Regenerating smpl-demo-seed.js from restored board HTML…");
  runExtractDemoSeed();

  log("Reset complete.");
  log("  Board:    http://localhost:3002/board");
  log("  Forecast: http://localhost:3002/forecast-engine");
  log("Next: npm run verify:platform");
}

try {
  main();
} catch (err) {
  console.error(err.message || err);
  process.exit(1);
}
