import { copyFileSync, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { patchBoardSampleHtml } from "./board-sample-patch.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const publicDir = join(root, "public", "board-sample");
const publicPath = join(publicDir, "index.html");
const canonicalDir = join(root, "canonical", "board-sample");
const canonicalPath = join(canonicalDir, "index.html");

const sources = [
  process.env.SMPL_BOARD_SAMPLE_SRC?.trim(),
  canonicalPath,
  publicPath,
  "C:\\Users\\mattj\\Downloads\\SMPL_Board_Platform_June2026 (10).html",
  join(process.env.USERPROFILE || "", "Downloads", "SMPL_Board_Platform_June2026 (10).html"),
].filter(Boolean);

function resolveSource() {
  for (const src of sources) {
    if (src && existsSync(src)) return src;
  }
  return null;
}

let src = resolveSource();
if (!src && existsSync(publicPath)) {
  src = publicPath;
  console.log(`Using existing public board sample (${statSync(publicPath).size} bytes)`);
}

if (src) {
  mkdirSync(publicDir, { recursive: true });
  mkdirSync(canonicalDir, { recursive: true });

  const raw = readFileSync(src, "utf-8");
  const html = patchBoardSampleHtml(raw);

  writeFileSync(publicPath, html, "utf-8");
  writeFileSync(canonicalPath, html, "utf-8");

  console.log(`Board sample ready (${html.length} bytes)`);
  console.log(`  public:    ${publicPath}`);
  console.log(`  canonical: ${canonicalPath}`);
  console.log(`  source:    ${src} (${statSync(src).size} bytes)`);
} else if (existsSync(publicPath)) {
  mkdirSync(canonicalDir, { recursive: true });
  copyFileSync(publicPath, canonicalPath);
  console.log(`Canonical mirror updated from public (${statSync(publicPath).size} bytes)`);
} else {
  console.warn("Board sample source not found — skipping (commit public/board-sample/index.html).");
  process.exit(0);
}
