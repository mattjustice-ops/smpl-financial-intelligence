/**
 * Load tmp/_chunks_payload.json into chunk files + meta, then assemble+post.
 * Usage: node scripts/aio-load-chunks-payload.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const p = JSON.parse(
  fs.readFileSync(path.join(root, "tmp", "_chunks_payload.json"), "utf8"),
);
p.chunks.forEach((c, i) =>
  fs.writeFileSync(
    path.join(root, "tmp", `aio_chunk_${String(i).padStart(3, "0")}.txt`),
    c,
  ),
);
fs.writeFileSync(
  path.join(root, "tmp", "aio_chunk_meta.json"),
  JSON.stringify({
    queryId: p.queryId,
    queryText: p.queryText,
    n: p.chunks.length,
    batchName: p.batchName || "Full 46 - 2026-09-23",
    citationUrls: p.citationUrls || [],
  }),
);
const r = spawnSync("node", ["scripts/aio-assemble-from-tmp.mjs"], {
  cwd: root,
  encoding: "utf8",
});
process.stdout.write(r.stdout || "");
process.stderr.write(r.stderr || "");
process.exit(r.status ?? 1);
