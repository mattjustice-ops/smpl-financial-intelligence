/**
 * Submit URLs to IndexNow (Bing, Yandex, Seznam, Naver, ...).
 *
 * The key is read from the single public/<key>.txt file whose content equals
 * its filename stem; that file must be live on production before submitting.
 *
 * Run:
 *   node scripts/indexnow-submit.mjs https://www.smpl-ai.com/a https://www.smpl-ai.com/b
 *   node scripts/indexnow-submit.mjs --file urls.txt        (one URL per line)
 *   node scripts/indexnow-submit.mjs --endpoint https://www.bing.com/indexnow ...
 *   node scripts/indexnow-submit.mjs --dry-run ...
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HOST = "www.smpl-ai.com";
const DEFAULT_ENDPOINT = "https://api.indexnow.org/indexnow";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(__dirname, "..", "public");

function findKey() {
  const keys = fs
    .readdirSync(publicDir)
    .filter((name) => /^[a-zA-Z0-9-]{8,128}\.txt$/.test(name) && name !== "robots.txt")
    .map((name) => ({
      stem: name.slice(0, -4),
      body: fs.readFileSync(path.join(publicDir, name), "utf8").trim(),
    }))
    .filter(({ stem, body }) => stem === body);
  if (keys.length !== 1) {
    throw new Error(`Expected exactly one IndexNow key file in public/, found ${keys.length}`);
  }
  return keys[0].stem;
}

const args = process.argv.slice(2);
let endpoint = DEFAULT_ENDPOINT;
let dryRun = false;
const urls = [];
for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  if (arg === "--endpoint") endpoint = args[++i];
  else if (arg === "--dry-run") dryRun = true;
  else if (arg === "--file") {
    const lines = fs.readFileSync(args[++i], "utf8").split(/\r?\n/);
    urls.push(...lines.map((l) => l.trim()).filter((l) => l && !l.startsWith("#")));
  } else urls.push(arg);
}

if (urls.length === 0) {
  console.error("No URLs given.");
  process.exit(1);
}
const offHost = urls.filter((u) => new URL(u).host !== HOST);
if (offHost.length) {
  console.error(`URLs must be on ${HOST}:\n${offHost.join("\n")}`);
  process.exit(1);
}

const key = findKey();
const body = {
  host: HOST,
  key,
  keyLocation: `https://${HOST}/${key}.txt`,
  urlList: [...new Set(urls)],
};

if (dryRun) {
  console.log(JSON.stringify({ endpoint, ...body }, null, 2));
  process.exit(0);
}

const res = await fetch(endpoint, {
  method: "POST",
  headers: { "Content-Type": "application/json; charset=utf-8" },
  body: JSON.stringify(body),
});
const text = await res.text();
console.log(`${endpoint} -> HTTP ${res.status} ${res.statusText} (${body.urlList.length} URLs)`);
if (text) console.log(text);
// 200 = submitted, 202 = accepted (key validation pending).
process.exit(res.status === 200 || res.status === 202 ? 0 : 1);
