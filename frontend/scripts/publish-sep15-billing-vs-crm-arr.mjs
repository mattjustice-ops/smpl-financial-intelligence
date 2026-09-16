/**
 * Publish Sep 15, 2026 pillar: Billing ARR vs CRM ARR.
 *
 * Usage (from frontend/):
 *   node scripts/publish-sep15-billing-vs-crm-arr.mjs --dry-run
 *   node scripts/publish-sep15-billing-vs-crm-arr.mjs
 *   npm run publish:billing-vs-crm-arr
 */

import { createClient } from "@sanity/client";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import {
  extractArticleMarkdown,
  markdownToBlocks,
  parseDeliverables,
  resetBlockKeys,
} from "./lib/markdown-to-sanity-blocks.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");
const dryRun = process.argv.includes("--dry-run");

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
if (!token && !dryRun) {
  console.error("Missing SANITY_API_WRITE_TOKEN");
  process.exit(1);
}

const client = createClient({
  projectId,
  dataset,
  apiVersion: "2025-01-01",
  token,
  useCdn: false,
});

const POST_ID = "post-billing-vs-crm-arr";
const SOURCE = resolve(
  root,
  "sanity/seed/source/sep15-billing-vs-crm-arr.md",
);

function buildPost() {
  const fullText = readFileSync(SOURCE, "utf8").replace(/\r\n/g, "\n");
  const meta = parseDeliverables(fullText);
  for (const field of ["slug", "seoTitle", "excerpt", "title"]) {
    if (!meta[field]) throw new Error(`Missing ${field}`);
  }
  resetBlockKeys();
  const body = markdownToBlocks(extractArticleMarkdown(fullText));
  return {
    _id: POST_ID,
    _type: "post",
    title: meta.title,
    slug: { _type: "slug", current: meta.slug },
    excerpt: meta.excerpt,
    publishedAt: "2026-09-15T16:00:00.000Z",
    author: { _type: "reference", _ref: "author-smpl-team" },
    categories: [{ _type: "reference", _ref: "category-arr-revenue" }],
    seoTitle: meta.seoTitle,
    seoDescription: meta.excerpt,
    body,
  };
}

function key(prefix = "r") {
  return `${prefix}${Math.random().toString(36).slice(2, 10)}`;
}

async function linkGlossary(postId) {
  const termIds = ["glossary-billing-arr", "glossary-crm-arr", "glossary-arr"];
  for (const termId of termIds) {
    const term = await client.fetch(`*[_id == $id][0]{relatedPosts}`, {
      id: termId,
    });
    if (!term) {
      console.warn(`  skip relatedPosts: missing ${termId}`);
      continue;
    }
    const existing = (term.relatedPosts || []).map((r) => r._ref);
    if (existing.includes(postId)) {
      console.log(`  relatedPosts already set: ${termId}`);
      continue;
    }
    await client
      .patch(termId)
      .setIfMissing({ relatedPosts: [] })
      .append("relatedPosts", [
        { _type: "reference", _ref: postId, _key: key() },
      ])
      .commit();
    console.log(`  linked ${termId} → ${postId}`);
  }
}

async function main() {
  const doc = buildPost();
  const linkCount = new Set();
  for (const b of doc.body) {
    for (const def of b.markDefs ?? []) {
      if (def._type === "link") linkCount.add(def.href);
    }
  }
  console.log(`Built ${doc.slug.current}: ${doc.body.length} blocks`);
  console.log(`SEO title (${doc.seoTitle.length}): ${doc.seoTitle}`);
  console.log("Links:");
  for (const href of [...linkCount].sort()) console.log(`  ${href}`);

  if (dryRun) {
    console.log("\nDry run: nothing written.");
    return;
  }

  await client.createOrReplace(doc);
  console.log(`\nPublished ${doc._id}`);
  await linkGlossary(doc._id);
  console.log("\nLive: https://www.smpl-ai.com/blog/billing-vs-crm-arr");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
