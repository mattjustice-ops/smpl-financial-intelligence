/**
 * Post capture from tmp/_b64_parts_in.json: { parts: string[] }
 * Or from tmp/last.b64 via aio-save-b64-and-post.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const inPath = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.join(root, "tmp", "_b64_parts_in.json");
const j = JSON.parse(fs.readFileSync(inPath, "utf8"));
const b64 = (j.parts || []).join("").trim().replace(/\s+/g, "");
if (!b64) {
  console.error("no parts");
  process.exit(1);
}
fs.writeFileSync(path.join(root, "tmp", "last.b64"), b64);
const r = spawnSync("node", ["scripts/aio-save-b64-and-post.mjs", b64], {
  cwd: root,
  encoding: "utf8",
  maxBuffer: 20 * 1024 * 1024,
});
process.stdout.write(r.stdout || "");
process.stderr.write(r.stderr || "");
process.exit(r.status ?? 1);
