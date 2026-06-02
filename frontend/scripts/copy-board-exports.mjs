import { copyFileSync, existsSync, mkdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const exportDir = join(root, "public", "board", "exports");

const assets = [
  {
    src:
      process.env.SMPL_BOARD_PPTX_SRC?.trim() ??
      "C:\\Users\\mattj\\OneDrive\\SMPL_Board_Review_May2026.pptx",
    dst: "SMPL_Board_Review_May2026.pptx",
  },
  {
    src:
      process.env.SMPL_MDA_XLSX_SRC?.trim() ??
      "C:\\Users\\mattj\\OneDrive\\SMPL_MDA_Package_May2026.xlsx",
    dst: "SMPL_MDA_Package_May2026.xlsx",
  },
];

mkdirSync(exportDir, { recursive: true });

for (const { src, dst } of assets) {
  const destPath = join(exportDir, dst);
  if (!existsSync(src)) {
    if (existsSync(destPath)) {
      console.log(`Board export already at ${destPath} (${statSync(destPath).size} bytes)`);
      continue;
    }
    console.warn(`Board export source not found: ${src}`);
    console.warn(`Commit ${destPath} for cloud deploy, or set env override before copy.`);
    continue;
  }
  copyFileSync(src, destPath);
  console.log(`Copied ${statSync(destPath).size} bytes to ${destPath}`);
}
