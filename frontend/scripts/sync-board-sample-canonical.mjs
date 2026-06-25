import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(root, "public", "board-sample", "index.html");
const dstDir = join(root, "canonical", "board-sample");
const dst = join(dstDir, "index.html");

if (!existsSync(src)) {
  console.error("Missing:", src);
  process.exit(1);
}

mkdirSync(dstDir, { recursive: true });
copyFileSync(src, dst);
console.log("Copied board sample to canonical:", dst);
