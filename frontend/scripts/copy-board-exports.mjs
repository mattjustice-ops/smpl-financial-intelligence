import { copyFileSync, existsSync, mkdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const sampleExportDir = join(root, "public", "board-sample", "exports");
const backendTemplateDir = join(root, "..", "backend", "templates", "board");

const assets = [
  {
    env: "SMPL_BOARD_PPTX_SRC",
    src:
      process.env.SMPL_BOARD_PPTX_SRC?.trim() ??
      "C:\\Users\\mattj\\OneDrive\\SMPL_Board_Review_Q2_2026.pptx",
    dst: "SMPL_Board_Review_Q2_2026.pptx",
    templateDst: "SMPL_Board_Review_Template.pptx",
    fallbacks: ["C:\\Users\\mattj\\Downloads\\SMPL_Board_Review_Q2_2026.pptx"],
  },
  {
    env: "SMPL_MDA_XLSX_SRC",
    src:
      process.env.SMPL_MDA_XLSX_SRC?.trim() ??
      "C:\\Users\\mattj\\OneDrive\\SMPL_MDA_Package_June2026.xlsx",
    dst: "SMPL_MDA_Package_June2026.xlsx",
    fallbacks: ["C:\\Users\\mattj\\Downloads\\SMPL_MDA_Package_June2026.xlsx"],
  },
];

mkdirSync(sampleExportDir, { recursive: true });
mkdirSync(backendTemplateDir, { recursive: true });

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
  const sampleDest = join(sampleExportDir, asset.dst);
  const srcPath = resolveSource(asset);
  if (!srcPath) {
    if (existsSync(sampleDest)) {
      console.log(`Board export already at ${sampleDest} (${statSync(sampleDest).size} bytes)`);
      continue;
    }
    console.warn(`Board export source not found for ${asset.dst}`);
    console.warn(`Set ${asset.env} or run: npm run copy:board-exports`);
    continue;
  }
  copyFileSync(srcPath, sampleDest);
  console.log(`Copied sample export to ${sampleDest}`);
  if (asset.templateDst) {
    const templatePath = join(backendTemplateDir, asset.templateDst);
    copyFileSync(srcPath, templatePath);
    console.log(`Copied template to ${templatePath} (used by live MD&A deck export)`);
  }
}
