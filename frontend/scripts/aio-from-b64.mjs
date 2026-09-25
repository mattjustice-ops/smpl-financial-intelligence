/**
 * Decode base64 JSON payload from stdin or argv, write _chunks_payload.json, assemble+post.
 * Usage: node scripts/aio-from-b64.mjs <b64>
 *    or: Get-Content tmp/last.b64 | node scripts/aio-from-b64.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
let b64 = process.argv[2] || "";
if (!b64) {
  b64 = fs.readFileSync(0, "utf8");
}
b64 = b64.trim().replace(/\s+/g, "");
const json = Buffer.from(b64, "base64").toString("utf8");
const p = JSON.parse(json);
fs.writeFileSync(path.join(root, "tmp", "_chunks_payload.json"), json);
const r = spawnSync("node", ["scripts/aio-load-chunks-payload.mjs"], {
  cwd: root,
  encoding: "utf8",
});
process.stdout.write(r.stdout || "");
process.stderr.write(r.stderr || "");
if (r.status) process.exit(r.status);
console.error(
  JSON.stringify({
    posted: p.queryId,
    len: (p.chunks || []).join("").length,
    smpl: /smpl/i.test((p.chunks || []).join("")),
  }),
);
