import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const publicPath = join(root, "public", "board-sample", "index.html");
const canonicalPath = join(root, "canonical", "board-sample", "index.html");

if (!existsSync(publicPath)) {
  console.error("Missing public board sample:", publicPath);
  process.exit(1);
}

mkdirSync(dirname(canonicalPath), { recursive: true });
copyFileSync(publicPath, canonicalPath);
console.log("Copied board sample to", canonicalPath);
