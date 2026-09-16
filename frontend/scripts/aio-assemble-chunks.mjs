/**
 * Assemble chunks written as tmp/aio_chunk_NN.txt into aio_chunks.json then import.
 * Meta: tmp/aio_chunk_meta.json { queryId, queryText, n }
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const tmp = path.join(root, "tmp");
const meta = JSON.parse(fs.readFileSync(path.join(tmp, "aio_chunk_meta.json"), "utf8"));
const b64Chunks = [];
for (let i = 0; i < meta.n; i++) {
  const p = path.join(tmp, `aio_chunk_${String(i).padStart(3, "0")}.txt`);
  b64Chunks.push(fs.readFileSync(p, "utf8").trim());
}
const payload = { queryId: meta.queryId, queryText: meta.queryText, b64Chunks };
fs.writeFileSync(path.join(tmp, "aio_chunks.json"), JSON.stringify(payload));
const r = spawnSync("node", ["scripts/aio-save-import-one.mjs"], {
  cwd: root,
  encoding: "utf8",
  shell: true,
  env: process.env,
});
process.stdout.write(r.stdout || "");
process.stderr.write(r.stderr || "");
process.exit(r.status ?? 1);
