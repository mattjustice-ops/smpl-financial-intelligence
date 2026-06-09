import { copyFileSync, existsSync, mkdirSync, statSync, unlinkSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const exportDir = join(root, "public", "board", "exports");

const assets = [
  {
    src:
      process.env.SMPL_BOARD_PPTX_SRC?.trim() ??
      "C:\\Users\\mattj\\OneDrive\\SMPL_Board_Review_Q2_2026.pptx",
    dst: "SMPL_Board_Review_Q2_2026.pptx",
    fallbacks: ["C:\\Users\\mattj\\Downloads\\SMPL_Board_Review_Q2_2026.pptx"],
  },
  {
    src:
      process.env.SMPL_MDA_XLSX_SRC?.trim() ??
      "C:\\Users\\mattj\\OneDrive\\SMPL_MDA_Package_June2026.xlsx",
    dst: "SMPL_MDA_Package_June2026.xlsx",
    fallbacks: ["C:\\Users\\mattj\\Downloads\\SMPL_MDA_Package_June2026.xlsx"],
  },
];

const legacyFiles = [
  "SMPL_Board_Review_May2026.pptx",
  "SMPL_MDA_Package_May2026.xlsx",
];

mkdirSync(exportDir, { recursive: true });

function resolveSource(asset) {
  if (asset.src && existsSync(asset.src)) {
    return asset.src;
  }
  for (const fallback of asset.fallbacks) {
    if (existsSync(fallback)) {
      return fallback;
    }
  }
  return null;
}

for (const asset of assets) {
  const destPath = join(exportDir, asset.dst);
  const srcPath = resolveSource(asset);
  if (!srcPath) {
    if (existsSync(destPath)) {
      console.log(`Board export already at ${destPath} (${statSync(destPath).size} bytes)`);
      continue;
    }
    console.warn(`Board export source not found for ${asset.dst}`);
    console.warn(`Set env override or run: npm run update:board-june`);
    continue;
  }
  copyFileSync(srcPath, destPath);
  console.log(`Copied ${statSync(destPath).size} bytes to ${destPath}`);
}

for (const legacy of legacyFiles) {
  const legacyPath = join(exportDir, legacy);
  if (existsSync(legacyPath)) {
    unlinkSync(legacyPath);
    console.log(`Removed legacy export ${legacy}`);
  }
}
