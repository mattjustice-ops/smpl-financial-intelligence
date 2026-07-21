/**
 * Seed Sanity with cornerstone blog posts + glossary terms.
 *
 * Prerequisites:
 *   1. NEXT_PUBLIC_SANITY_PROJECT_ID + NEXT_PUBLIC_SANITY_DATASET in .env.local
 *   2. SANITY_API_WRITE_TOKEN (Editor+ token) in .env.local — never commit
 *   3. Schema deployed (open /studio once, or `npx sanity schema deploy`)
 *
 * Usage (from frontend/):
 *   npm run seed:sanity
 */

import { createClient } from "@sanity/client";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import {
  author,
  categories,
  glossaryTerms,
  posts,
} from "../sanity/seed/content.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");

function loadEnvLocal() {
  const envPath = resolve(root, ".env.local");
  if (!existsSync(envPath)) return;
  const text = readFileSync(envPath, "utf8");
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (!process.env[key]) process.env[key] = value;
  }
}

loadEnvLocal();

const projectId = process.env.NEXT_PUBLIC_SANITY_PROJECT_ID?.trim();
const dataset = process.env.NEXT_PUBLIC_SANITY_DATASET?.trim() || "production";
const token = process.env.SANITY_API_WRITE_TOKEN?.trim();

if (!projectId) {
  console.error("Missing NEXT_PUBLIC_SANITY_PROJECT_ID");
  process.exit(1);
}
if (!token) {
  console.error(
    "Missing SANITY_API_WRITE_TOKEN. Create an Editor token in Sanity → API → Tokens, then add it to frontend/.env.local",
  );
  process.exit(1);
}

const client = createClient({
  projectId,
  dataset,
  apiVersion: "2025-01-01",
  token,
  useCdn: false,
});

const docs = [author, ...categories, ...posts, ...glossaryTerms];

/**
 * Legacy dotted IDs fall outside Sanity's default public ACL grant
 * `_id in path("*")` (`.` is a path separator), so anonymous CDN reads
 * omit them with reason "permission". Delete after reseeding hyphenated IDs.
 */
const legacyDottedIds = [
  "author.smpl-team",
  "category.board-reporting",
  "category.close",
  "category.ai-commentary",
  "post.board-numbers-need-evidence",
  "post.saas-close-load-validate-lock-freeze",
  "post.ai-commentary-finance-will-sign",
  "glossary.arr",
  "glossary.mrr",
  "glossary.nrr",
  "glossary.grr",
  "glossary.deferred-revenue",
  "glossary.waterfall",
  "glossary.close",
  "glossary.mda",
  "glossary.freeze-pack",
  "glossary.combined-scenario",
  "glossary.bookings",
  "glossary.pipeline",
  "glossary.churn",
  "glossary.expansion",
  "glossary.contraction",
  "glossary.cac",
  "glossary.ltv",
  "glossary.burn-multiple",
  "glossary.runway",
  "glossary.gaap-revenue",
];

/** Retired cornerstone posts (hyphenated + drafts) — replace with new blog set. */
const retiredPostIds = [
  "post-board-numbers-need-evidence",
  "post-saas-close-load-validate-lock-freeze",
  "post-ai-commentary-finance-will-sign",
  "drafts.post-board-numbers-need-evidence",
  "drafts.post-saas-close-load-validate-lock-freeze",
  "drafts.post-ai-commentary-finance-will-sign",
  "drafts.post.board-numbers-need-evidence",
  "drafts.post.saas-close-load-validate-lock-freeze",
  "drafts.post.ai-commentary-finance-will-sign",
];

/** Retired glossary terms (IP / product-specific names). */
const retiredGlossaryIds = [
  "glossary-freeze-pack",
  "glossary-combined-scenario",
  "drafts.glossary-freeze-pack",
  "drafts.glossary-combined-scenario",
];

const retiredPostSlugs = [
  "board-numbers-need-evidence",
  "saas-close-load-validate-lock-freeze",
  "ai-commentary-finance-will-sign",
];

const retiredGlossarySlugs = ["freeze-pack", "combined-scenario"];

async function main() {
  console.log(`Seeding ${docs.length} documents → ${projectId}/${dataset}`);

  // Also delete any Studio-created docs that still use retired slugs.
  const [retiredPostsBySlug, retiredGlossaryBySlug] = await Promise.all([
    client.fetch(`*[_type == "post" && slug.current in $slugs]._id`, {
      slugs: retiredPostSlugs,
    }),
    client.fetch(`*[_type == "glossaryTerm" && slug.current in $slugs]._id`, {
      slugs: retiredGlossarySlugs,
    }),
  ]);

  const tx = client.transaction();
  for (const doc of docs) {
    if (doc._id.includes(".")) {
      throw new Error(
        `Seed doc ${doc._id} uses '.' — public ACL only grants path("*"). Use hyphens.`,
      );
    }
    tx.createOrReplace(doc);
  }
  for (const id of [
    ...legacyDottedIds,
    ...retiredPostIds,
    ...retiredGlossaryIds,
    ...retiredPostsBySlug,
    ...retiredGlossaryBySlug,
  ]) {
    tx.delete(id);
  }
  await tx.commit();
  console.log("Done. Publish is automatic for createOrReplace (published docs).");
  console.log(
    `Deleted legacy dotted IDs + retired posts/glossary (known ids + ${retiredPostsBySlug.length} posts / ${retiredGlossaryBySlug.length} glossary by slug).`,
  );
  console.log("Visit /blog and /glossary (or /studio to edit).");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
