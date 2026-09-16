import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const capturePath = path.join(root, "tmp", "aio_audits_capture.jsonl");
const progressPath = path.join(root, "tmp", "aio_run_progress.json");
const PORT = 3847;

fs.mkdirSync(path.join(root, "tmp"), { recursive: true });

const server = http.createServer((req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Access-Control-Allow-Private-Network", "true");
  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }
  if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    return;
  }
  if (req.method === "POST" && req.url === "/capture") {
    let body = "";
    req.on("data", (c) => (body += c));
    req.on("end", () => {
      try {
        const rec = JSON.parse(body);
        if (!rec.queryId || !rec.queryText || !rec.rawResponse) {
          res.writeHead(400);
          res.end("bad record");
          return;
        }
        fs.appendFileSync(capturePath, JSON.stringify(rec) + "\n");
        const p = fs.existsSync(progressPath)
          ? JSON.parse(fs.readFileSync(progressPath, "utf8"))
          : { done: [], failed: [] };
        if (!p.done.includes(rec.queryId)) p.done.push(rec.queryId);
        p.updatedAt = new Date().toISOString();
        fs.writeFileSync(progressPath, JSON.stringify(p, null, 2));
        console.log(`[capture] ${rec.queryId} len=${rec.rawResponse.length} done=${p.done.length}`);
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true, done: p.done.length }));
      } catch (e) {
        console.error(e);
        res.writeHead(500);
        res.end(String(e));
      }
    });
    return;
  }
  res.writeHead(404);
  res.end("not found");
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`AIO capture server on http://127.0.0.1:${PORT}/capture`);
});
