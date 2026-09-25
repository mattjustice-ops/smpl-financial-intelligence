/**
 * After CDP sets window.__aio_parts, agent saves JSON.stringify(parts) to tmp/_aio_parts.json
 * Then: node scripts/aio-finish-parts.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const partsPath = path.join(root, "tmp", "_aio_parts.json");
const raw = fs.readFileSync(partsPath, "utf8").trim();
const parts = JSON.parse(raw);
const b64 = (Array.isArray(parts) ? parts : parts.parts || []).join("").replace(/\s+/g, "");
fs.writeFileSync(path.join(root, "tmp", "last.b64"), b64);
const r = spawnSync("node", ["scripts/aio-save-b64-and-post.mjs", b64], {
  cwd: root,
  encoding: "utf8",
  maxBuffer: 20 * 1024 * 1024,
});
process.stdout.write(r.stdout || "");
process.stderr.write(r.stderr || "");
process.exit(r.status ?? 1);
