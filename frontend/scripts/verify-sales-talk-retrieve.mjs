/**
 * Assert Sales Talk Track retrieval picks the right cards for high-signal queries.
 * Run from frontend/: node --experimental-strip-types scripts/verify-sales-talk-retrieve.mjs
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
const { retrieveSalesAnswers, scoreEntry, tokenize, debugMatchingIntents } =
  await import(retrieveUrl);

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
  assert(matches.length >= 1, `${label}: expected a match (intents: ${debugMatchingIntents(question).join(",") || "none"}; top: ${topIds(question).map((r) => r.id).join(", ")})`);
  assert(
    matches[0].entry.id === expectedId,
    `${label}: expected ${expectedId}, got ${matches[0].entry.id} (score ${matches[0].score.toFixed(2)}; intents: ${debugMatchingIntents(question).join(",") || "none"}; top: ${topIds(question)
      .map((r) => `${r.id}:${r.score.toFixed(1)}`)
      .join(", ")})`,
  );
  return matches;
}

function assertNotTop(question, bannedId, label = question) {
  const matches = retrieveSalesAnswers(question, kb.entries, { limit: 3 });
  assert(
    !matches.some((m) => m.entry.id === bannedId) || matches[0].entry.id !== bannedId,
    `${label}: must not win with ${bannedId}`,
  );
  if (matches[0]) {
    assert(
      matches[0].entry.id !== bannedId,
      `${label}: must not win with ${bannedId}`,
    );
  }
}

// --- Core regressions ---
const moatQuery = "what is your moat?";
console.log("tokens:", tokenize(moatQuery));
console.log("top matches for", JSON.stringify(moatQuery));
for (const row of topIds(moatQuery)) {
  console.log(`  ${row.score.toFixed(3)}  ${row.id}`);
}

assertTop(moatQuery, "architecture-as-moat", "moat");
assertNotTop(moatQuery, "implementation-security");
assertNotTop(moatQuery, "differentiator-three-principles");

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
for (const kw of [
  "moat",
  "competitive advantage",
  "defensibility",
  "hard to copy",
  "architecture as a moat",
]) {
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

// --- Paraphrase fixes (user-reported wrong cards) ---
assertTop("why would we use your company", "why-us");
assertTop("why use SMPL", "why-us");
assertTop("why your company", "why-us");
assertTop("why use your company", "why-us");
assertTop("why don't we just build ourselves", "build-vs-buy");
assertTop("why dont we just build ourselves", "build-vs-buy");
assertTop("why build it ourselves", "build-vs-buy");
assertTop("should we build", "build-vs-buy");
assertTop("what is your moat", "architecture-as-moat");
assertNotTop("why would we use your company", "tenant-isolation");
assertNotTop("why would we use your company", "per-org-tenant-environment");
assertNotTop("why don't we just build ourselves", "platform-features-overview");
assertNotTop("why build it ourselves", "team");

// --- Security / AI / compete / SEO regressions ---
assertTop("how do you handle AI security", "ai-security");
assertTop("AI security", "ai-security");
assertTop("what are you doing for AI security?", "ai-security");
assertTop("do you train AI on our data", "ai-training");
assertTop("do you train on our data", "ai-training");
assertTop("can AI hallucinate", "ai-hallucinations");
assertTop("how do you prevent hallucinations", "ai-hallucinations");
assertTop("Tell me about your system architecture", "system-architecture");
assertTop("what is your system architecture", "system-architecture");
assertTop("tech stack", "system-architecture");
assertTop("why not mosaic", "compete-mosaic");
assertTop("why not mosiac", "compete-mosaic");
assertTop("is our data secure", "security-trust-overview");
assertTop("data security", "security-trust-overview");
assertTop("why you vs Power BI", "compete-power-bi");
assertTop("why not just use ChatGPT", "compete-chatgpt");
assertTop("SEO tags", "seo-marketing-site");
assertTop("what SEO tags do you use", "seo-marketing-site");
assertTop("why not Tableau", "compete-tableau");
assertTop("why not Snowflake", "compete-snowflake");
assertTop("why not just use Excel", "compete-excel");

// --- Laundry list ---
assertTop("What is your moat?", "architecture-as-moat");
assertTop("Why not Cube", "compete-cube");
assertTop("Why not Pigment", "compete-pigment");
assertTop("Why not Anaplan", "compete-anaplan");
assertTop("Why not Mosaic", "compete-mosaic");
assertTop("Why not Rillet", "compete-rillet");
assertTop("Why not Tableau", "compete-tableau");
assertTop("Why not Power BI", "compete-power-bi");
assertTop("How accurate is AI?", "ai-accuracy");
assertTop("Can AI hallucinate? How prevent?", "ai-hallucinations");
assertTop("Do you train on our data?", "ai-training");
assertTop("What happens after implementation?", "after-implementation");
assertTop(
  "Can I customize metrics / define ARR differently / change methodology?",
  "customize-metrics-methodology",
);
assertTop("How long until value?", "time-to-value");
assertTop("What if my data is bad?", "data-quality-bad-data");
assertTop("What happens if NetSuite changes?", "netsuite-schema-change");
assertTop("Can you support custom objects?", "custom-objects");
assertTop("Can I export everything?", "export-capabilities");
assertTop("Do you replace Excel / FP&A / NetSuite?", "replace-boundaries");
assertTop("Can I use my own warehouse?", "own-warehouse");
assertTop("How do you calculate NRR / GRR?", "nrr-grr-calculation");
assertTop(
  "How do you build forecasts? What assumptions configurable?",
  "forecast-assumptions",
);
assertTop("Can the board / auditors trust the numbers?", "board-auditor-trust");
assertTop("How do I trace every calculation?", "calculation-traceability");
assertTop("How do you validate imports / detect bad data?", "import-validation");
assertTop(
  "How does AI generate commentary? How verified?",
  "ai-commentary-capabilities",
);
assertTop(
  "Can AI explain variance / answer executive questions?",
  "ai-executive-qa",
);
assertTop("What happens if confidence is low?", "confidence-signal");

// Entry presence + honesty checks
for (const id of [
  "why-us",
  "build-vs-buy",
  "compete-pigment",
  "compete-anaplan",
  "ai-accuracy",
  "after-implementation",
  "customize-metrics-methodology",
  "time-to-value",
  "data-quality-bad-data",
  "netsuite-schema-change",
  "custom-objects",
  "export-capabilities",
  "replace-boundaries",
  "own-warehouse",
  "nrr-grr-calculation",
  "forecast-assumptions",
  "board-auditor-trust",
  "calculation-traceability",
  "import-validation",
  "ai-executive-qa",
]) {
  assert(kb.entries.some((e) => e.id === id), `missing entry ${id}`);
}

const aiTraining = kb.entries.find((e) => e.id === "ai-training");
assert(
  /do not use customer data to train/i.test(aiTraining.answer),
  "ai-training must clearly say we do not train on customer data",
);

const sysArch = kb.entries.find((e) => e.id === "system-architecture");
assert(
  !/freeze|lock ladder/i.test(sysArch.answer),
  "system-architecture must not use freeze/lock jargon",
);

for (const e of kb.entries) {
  if ((e.tone ?? "external_safe") !== "external_safe") continue;
  if (e.confidence === "do-not-answer") continue;
  assert(
    !/\bfreeze\b|\block ladder\b/i.test(e.answer),
    `${e.id} external_safe answer must not use freeze/lock jargon`,
  );
}

assert(
  retrieveSalesAnswers("Tell me about your system architecture", kb.entries, {
    limit: 3,
  })[0].entry.id !== "architecture-as-moat",
  "system architecture must not win with architecture-as-moat",
);

console.log("\nOK — retrieval assertions passed.");
