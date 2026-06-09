import { copyFileSync, createWriteStream, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { get } from "node:https";
import { patchBoardExportHandlers } from "./patch-board-exports.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const exportDir = join(root, "public", "board", "exports");
const htmlDst = join(root, "public", "board", "index.html");

const htmlSrc =
  process.env.SMPL_BOARD_HTML_SRC?.trim() ??
  "C:\\Users\\mattj\\Downloads\\SMPL_Board_Platform_June2026 (6).html";

const exportAssets = [
  {
    name: "SMPL_Board_Review_Q2_2026.pptx",
    env: "SMPL_BOARD_PPTX_SRC",
    url: "https://d.docs.live.net/c0ecbdc24dae9ab7/SMPL_Board_Review_Q2_2026.pptx",
    localCandidates: [
      "C:\\Users\\mattj\\OneDrive\\SMPL_Board_Review_Q2_2026.pptx",
      "C:\\Users\\mattj\\Downloads\\SMPL_Board_Review_Q2_2026.pptx",
    ],
  },
  {
    name: "SMPL_MDA_Package_June2026.xlsx",
    env: "SMPL_MDA_XLSX_SRC",
    url: "https://d.docs.live.net/c0ecbdc24dae9ab7/SMPL_MDA_Package_June2026.xlsx",
    localCandidates: [
      "C:\\Users\\mattj\\OneDrive\\SMPL_MDA_Package_June2026.xlsx",
      "C:\\Users\\mattj\\Downloads\\SMPL_MDA_Package_June2026.xlsx",
    ],
  },
];

function log(message) {
  console.log(message);
}

function resolveSource(asset) {
  const envPath = process.env[asset.env]?.trim();
  if (envPath && existsSync(envPath)) {
    return envPath;
  }
  for (const candidate of asset.localCandidates) {
    if (existsSync(candidate)) {
      return candidate;
    }
  }
  return null;
}

function downloadFile(url, destPath) {
  return new Promise((resolve, reject) => {
    const file = createWriteStream(destPath);
    get(url, (response) => {
      if (response.statusCode && response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
        file.close();
        downloadFile(response.headers.location, destPath).then(resolve).catch(reject);
        return;
      }
      if (response.statusCode !== 200) {
        file.close();
        reject(new Error(`HTTP ${response.statusCode} for ${url}`));
        return;
      }
      response.pipe(file);
      file.on("finish", () => file.close(() => resolve(destPath)));
    }).on("error", reject);
  });
}

async function copyExportAsset(asset) {
  const destPath = join(exportDir, asset.name);
  const localSource = resolveSource(asset);

  if (localSource) {
    copyFileSync(localSource, destPath);
    log(`Copied export ${asset.name} from ${localSource} (${statSync(destPath).size} bytes)`);
    return true;
  }

  if (existsSync(destPath) && statSync(destPath).size > 1024) {
    log(`Export already present: ${destPath} (${statSync(destPath).size} bytes)`);
    return true;
  }

  try {
    await downloadFile(asset.url, destPath);
    if (statSync(destPath).size < 1024) {
      throw new Error("Downloaded file looks too small (auth page?)");
    }
    log(`Downloaded export ${asset.name} (${statSync(destPath).size} bytes)`);
    return true;
  } catch (error) {
    log(`WARN: Could not fetch ${asset.name}: ${error.message}`);
    log(`      Set ${asset.env} or place the file in Downloads/OneDrive, then re-run.`);
    return false;
  }
}

function copyBoardHtml() {
  mkdirSync(dirname(htmlDst), { recursive: true });

  if (!existsSync(htmlSrc)) {
    if (existsSync(htmlDst)) {
      log(`Board HTML already at ${htmlDst} (${statSync(htmlDst).size} bytes)`);
      return true;
    }
    throw new Error(`Board HTML source not found: ${htmlSrc}`);
  }

  const raw = readFileSync(htmlSrc, "utf8");
  const patched = patchBoardExportHandlers(raw);
  writeFileSync(htmlDst, patched, "utf8");
  log(`Wrote board HTML to ${htmlDst} (${statSync(htmlDst).size} bytes)`);
  return true;
}

async function main() {
  mkdirSync(exportDir, { recursive: true });

  log("=== Update June 2026 board package ===");
  copyBoardHtml();

  const exportResults = [];
  for (const asset of exportAssets) {
    exportResults.push(await copyExportAsset(asset));
  }

  if (exportResults.every(Boolean)) {
    log("All board assets ready.");
    log("Local:  http://localhost:3002/board");
    log("Prod:   https://smpl-financial-intelligence.vercel.app/board");
    log("Next: commit public/board/* and deploy to Vercel.");
    return;
  }

  log("");
  log("HTML updated, but one or more export files are missing.");
  log("Copy the PPTX/XLSX locally, then re-run: npm run update:board-june");
  process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
