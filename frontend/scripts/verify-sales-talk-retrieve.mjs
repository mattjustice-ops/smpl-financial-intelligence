/**
 * Assert Sales Talk Track retrieval picks the right cards for high-signal queries.
 * Run: node --experimental-strip-types scripts/verify-sales-talk-retrieve.mjs
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const kb = JSON.parse(
  readFileSync(join(root, "content/sales-kb/knowledge_base.json"), "utf8"),
);

const retrieveUrl = pathToFileURL(join(root, "lib/sales-talk/retrieve.ts")).href;
const { retrieveSalesAnswers, scoreEntry, tokenize } = await import(retrieveUrl);

function topIds(question, limit = 5) {
  const all = kb.entries
    .map((entry) => ({ id: entry.id, score: scoreEntry(question, entry) }))
    .sort((a, b) => b.score - a.score);
  return all.slice(0, limit);
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

const moatQuery = "what is your moat?";
console.log("tokens:", tokenize(moatQuery));
console.log("top matches for", JSON.stringify(moatQuery));
for (const row of topIds(moatQuery)) {
  console.log(`  ${row.score.toFixed(3)}  ${row.id}`);
}

const moatMatches = retrieveSalesAnswers(moatQuery, kb.entries, { limit: 3 });
assert(moatMatches.length >= 1, "moat query should match at least one entry");
assert(
  moatMatches[0].entry.id === "differentiator-three-principles",
  `expected differentiator-three-principles, got ${moatMatches[0].entry.id}`,
);
assert(
  moatMatches.every((m) => m.entry.id !== "implementation-security"),
  "moat query must not surface implementation-security",
);

const archMatches = retrieveSalesAnswers("architecture as a moat", kb.entries, {
  limit: 3,
});
assert(
  archMatches[0]?.entry.id === "differentiator-three-principles",
  `architecture-as-moat expected differentiator, got ${archMatches[0]?.entry.id}`,
);

const advMatches = retrieveSalesAnswers("what is your competitive advantage?", kb.entries, {
  limit: 3,
});
assert(
  advMatches[0]?.entry.id === "differentiator-three-principles",
  `competitive advantage expected differentiator, got ${advMatches[0]?.entry.id}`,
);

const implMatches = retrieveSalesAnswers("how long is implementation?", kb.entries, {
  limit: 3,
});
assert(
  implMatches[0]?.entry.id === "implementation-security",
  `implementation query expected implementation-security, got ${implMatches[0]?.entry.id}`,
);

const implEntry = kb.entries.find((e) => e.id === "implementation-security");
assert(implEntry, "implementation-security entry missing");
assert(
  !JSON.stringify(implEntry).toLowerCase().includes("moat"),
  "implementation-security must not contain 'moat'",
);

const diffEntry = kb.entries.find((e) => e.id === "differentiator-three-principles");
for (const kw of ["moat", "competitive advantage", "defensibility", "hard to copy"]) {
  assert(
    (diffEntry.keywords ?? []).some((k) => k.toLowerCase().includes(kw)),
    `differentiator missing keyword: ${kw}`,
  );
}

console.log("\nOK — retrieval assertions passed.");
