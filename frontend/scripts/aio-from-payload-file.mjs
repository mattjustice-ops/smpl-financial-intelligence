/**
 * Poll CDP-style: read tmp/aio_payload_raw.txt (UTF-8 JSON string of {queryId,queryText,b64Chunks})
 * write tmp/aio_chunks.json and run import.
 * Also accepts writing payload via: node scripts/aio-from-payload-file.mjs <file>
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const src = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.join(root, "tmp", "aio_payload_raw.txt");
let raw = fs.readFileSync(src, "utf8");
if (raw.charCodeAt(0) === 0xfeff) raw = raw.slice(1);
raw = raw.trim();
// tolerate wrapping quotes from PowerShell
if (raw.startsWith('"') && raw.endsWith('"')) {
  raw = JSON.parse(raw);
} else {
  JSON.parse(raw); // validate
}
const out = path.join(root, "tmp", "aio_chunks.json");
if (typeof raw === "string") {
  fs.writeFileSync(out, raw);
} else {
  fs.writeFileSync(out, JSON.stringify(raw));
}
const r = spawnSync("node", ["scripts/aio-save-import-one.mjs"], {
  cwd: root,
  encoding: "utf8",
  shell: true,
  env: process.env,
});
process.stdout.write(r.stdout || "");
process.stderr.write(r.stderr || "");
process.exit(r.status ?? 1);
