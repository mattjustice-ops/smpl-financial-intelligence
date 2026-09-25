/**
 * Write window.__aio_b64 parts from argv JSON array, then post via aio-post-json.
 * Usage:
 *   node scripts/aio-save-b64-and-post.mjs   # reads tmp/last.b64 (base64 of payload JSON)
 * Or pipe b64 on stdin.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
let b64 = process.argv[2] || "";
if (!b64) b64 = fs.readFileSync(0, "utf8");
b64 = b64.trim().replace(/\s+/g, "");
const p = JSON.parse(Buffer.from(b64, "base64").toString("utf8"));
fs.writeFileSync(path.join(root, "tmp", "_last_capture_in.json"), JSON.stringify(p));
const r = spawnSync("node", ["scripts/aio-post-json.mjs", "tmp/_last_capture_in.json"], {
  cwd: root,
  encoding: "utf8",
});
process.stdout.write(r.stdout || "");
process.stderr.write(r.stderr || "");
process.exit(r.status ?? 1);
