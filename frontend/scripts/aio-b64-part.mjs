/**
 * Append one b64 part then optionally assemble.
 * Usage:
 *   node scripts/aio-b64-part.mjs 0 <part>
 *   node scripts/aio-b64-part.mjs --finish   # decode+post when all parts written
 *   node scripts/aio-b64-part.mjs --reset N  # reset expecting N parts
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const metaPath = path.join(root, "tmp", "_b64_parts_meta.json");
const partDir = path.join(root, "tmp", "_b64_parts");

const cmd = process.argv[2];
if (cmd === "--reset") {
  const n = Number(process.argv[3] || 0);
  fs.rmSync(partDir, { recursive: true, force: true });
  fs.mkdirSync(partDir, { recursive: true });
  fs.writeFileSync(metaPath, JSON.stringify({ n, got: [] }));
  console.log(JSON.stringify({ reset: true, n }));
  process.exit(0);
}

if (cmd === "--finish") {
  const meta = JSON.parse(fs.readFileSync(metaPath, "utf8"));
  const parts = [];
  for (let i = 0; i < meta.n; i++) {
    const p = path.join(partDir, `${i}.txt`);
    if (!fs.existsSync(p)) {
      console.error("missing part", i);
      process.exit(1);
    }
    parts.push(fs.readFileSync(p, "utf8").trim());
  }
  const b64 = parts.join("");
  fs.writeFileSync(path.join(root, "tmp", "last.b64"), b64);
  const r = spawnSync("node", ["scripts/aio-from-b64.mjs"], {
    cwd: root,
    encoding: "utf8",
    input: b64,
  });
  process.stdout.write(r.stdout || "");
  process.stderr.write(r.stderr || "");
  process.exit(r.status ?? 1);
}

const i = Number(cmd);
const part = process.argv[3] || "";
if (!Number.isFinite(i) || !part) {
  console.error("Usage: node scripts/aio-b64-part.mjs <i> <part> | --reset N | --finish");
  process.exit(1);
}
fs.mkdirSync(partDir, { recursive: true });
fs.writeFileSync(path.join(partDir, `${i}.txt`), part);
const meta = fs.existsSync(metaPath)
  ? JSON.parse(fs.readFileSync(metaPath, "utf8"))
  : { n: 0, got: [] };
if (!meta.got.includes(i)) meta.got.push(i);
fs.writeFileSync(metaPath, JSON.stringify(meta));
console.log(JSON.stringify({ saved: i, got: meta.got.length, n: meta.n, len: part.length }));
