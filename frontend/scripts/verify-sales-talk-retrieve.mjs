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

function assertTop(question, expectedId, label = question) {
  const matches = retrieveSalesAnswers(question, kb.entries, { limit: 3 });
  assert(matches.length >= 1, `${label}: expected a match`);
  assert(
    matches[0].entry.id === expectedId,
    `${label}: expected ${expectedId}, got ${matches[0].entry.id} (top: ${topIds(question)
      .map((r) => r.id)
      .join(", ")})`,
  );
  return matches;
}

const moatQuery = "what is your moat?";
console.log("tokens:", tokenize(moatQuery));
console.log("top matches for", JSON.stringify(moatQuery));
for (const row of topIds(moatQuery)) {
  console.log(`  ${row.score.toFixed(3)}  ${row.id}`);
}

assertTop(moatQuery, "architecture-as-moat", "moat");
assert(
  retrieveSalesAnswers(moatQuery, kb.entries, { limit: 3 }).every(
    (m) => m.entry.id !== "implementation-security",
  ),
  "moat query must not surface implementation-security",
);
assert(
  retrieveSalesAnswers(moatQuery, kb.entries, { limit: 3 })[0].entry.id !==
    "differentiator-three-principles",
  "moat query must not win with differentiator-three-principles",
);

assertTop("architecture as a moat", "architecture-as-moat");
assertTop("what is your competitive advantage?", "architecture-as-moat");
assertTop("competitive moat", "architecture-as-moat");
assertTop("what makes you different?", "differentiator-three-principles");
assertTop("how are you different?", "differentiator-three-principles");
assertTop("how long is implementation?", "implementation-security");

const implEntry = kb.entries.find((e) => e.id === "implementation-security");
assert(implEntry, "implementation-security entry missing");
assert(
  !JSON.stringify(implEntry).toLowerCase().includes("moat"),
  "implementation-security must not contain 'moat'",
);

const moatEntry = kb.entries.find((e) => e.id === "architecture-as-moat");
assert(moatEntry, "architecture-as-moat entry missing");
for (const kw of ["moat", "competitive advantage", "defensibility", "hard to copy", "architecture as a moat"]) {
  assert(
    (moatEntry.keywords ?? []).some((k) => k.toLowerCase().includes(kw)),
    `architecture-as-moat missing keyword: ${kw}`,
  );
}

const diffEntry = kb.entries.find((e) => e.id === "differentiator-three-principles");
assert(diffEntry, "differentiator-three-principles entry missing");
assert(
  !(diffEntry.keywords ?? []).some((k) => k.toLowerCase() === "moat"),
  "differentiator must not keyword bare 'moat'",
);
for (const kw of ["what makes you different", "differentiator", "differentiation"]) {
  assert(
    (diffEntry.keywords ?? []).some((k) => k.toLowerCase().includes(kw)),
    `differentiator missing keyword: ${kw}`,
  );
}

// Security / AI / compete / SEO regressions from user testing
assertTop("how do you handle AI security", "ai-data-handling");
assertTop("AI security", "ai-data-handling");
assertTop("is our data secure", "security-trust-overview");
assertTop("data security", "security-trust-overview");
assertTop("why you vs Power BI", "compete-power-bi");
assertTop("why not just use ChatGPT", "compete-chatgpt");
assertTop("SEO tags", "seo-marketing-site");
assertTop("what SEO tags do you use", "seo-marketing-site");
assertTop("why not Tableau", "compete-tableau");
assertTop("why not Snowflake", "compete-snowflake");
assertTop("why not just use Excel", "compete-excel");

const aiEntry = kb.entries.find((e) => e.id === "ai-data-handling");
assert(
  (aiEntry.keywords ?? []).some((k) => k.toLowerCase() === "ai security"),
  "ai-data-handling must keyword 'ai security'",
);
const trustEntry = kb.entries.find((e) => e.id === "security-trust-overview");
assert(
  (trustEntry.keywords ?? []).some((k) => k.toLowerCase() === "data security"),
  "security-trust-overview must keyword 'data security'",
);

console.log("\nOK — retrieval assertions passed.");
