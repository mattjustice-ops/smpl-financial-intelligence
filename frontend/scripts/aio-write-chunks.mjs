/**
 * Dump window.__AIO_PAYLOAD from stdin JSON (PowerShell-friendly).
 * Usage: node scripts/aio-write-chunks.mjs path/to/payload.json
 * Or:    Get-Content payload.json | node scripts/aio-write-chunks.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const out = path.join(root, "tmp", "aio_chunks.json");
const arg = process.argv[2];
let raw;
if (arg && arg !== "-") {
  raw = fs.readFileSync(arg, "utf8");
} else {
  raw = fs.readFileSync(0, "utf8");
}
// strip BOM
if (raw.charCodeAt(0) === 0xfeff) raw = raw.slice(1);
const data = JSON.parse(raw);
if (!data.queryId || !Array.isArray(data.b64Chunks)) {
  console.error("bad payload");
  process.exit(1);
}
fs.writeFileSync(out, JSON.stringify(data));
console.log(`wrote ${data.queryId} chunks=${data.b64Chunks.length}`);
