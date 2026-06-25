import { readFileSync, writeFileSync, mkdirSync, copyFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { patchBoardSampleHtml } from "./board-sample-patch.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = "C:\\Users\\mattj\\Downloads\\SMPL_Board_Platform_June2026 (6).html";
const publicPath = join(root, "public", "board-sample", "index.html");
const canonicalPath = join(root, "canonical", "board-sample", "index.html");
const sourceCopy = join(root, "canonical", "board-sample", "SMPL_Board_Platform_June2026.html");

if (!existsSync(src)) {
  console.error("Source not found:", src);
  process.exit(1);
}

mkdirSync(dirname(publicPath), { recursive: true });
mkdirSync(dirname(canonicalPath), { recursive: true });

const raw = readFileSync(src, "utf-8");
const html = patchBoardSampleHtml(raw);

writeFileSync(publicPath, html, "utf-8");
writeFileSync(canonicalPath, html, "utf-8");
copyFileSync(src, sourceCopy);

console.log("OK", html.length, "bytes");
console.log("Fraunces:", html.includes("Fraunces"));
console.log("MD&A Deck:", html.includes("MD&A Deck"));
console.log("No footer exports:", !html.includes("MD&A Narrative"));
