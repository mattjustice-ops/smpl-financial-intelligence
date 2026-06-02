import { copyFileSync, existsSync, mkdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const src =
  process.env.SMPL_BOARD_HTML_SRC?.trim() ??
  "C:\\Users\\mattj\\Downloads\\SMPL_Board_Platform_May2026 (5).html";
const dst = join(root, "public", "board", "index.html");

mkdirSync(dirname(dst), { recursive: true });

if (!existsSync(src)) {
  if (existsSync(dst)) {
    console.log(`Board HTML already at ${dst} (${statSync(dst).size} bytes)`);
    process.exit(0);
  }
  console.warn(`Board HTML source not found: ${src}`);
  console.warn("Run locally with your Downloads export, then commit public/board/index.html for cloud deploy.");
  process.exit(0);
}

copyFileSync(src, dst);
console.log(`Copied ${statSync(dst).size} bytes to ${dst}`);
