/**
 * Publish Sep 9, 2026 blog cluster: best FP&A software buyer's guide + AI cost structure.
 *
 * Usage (from frontend/):
 *   node scripts/publish-sep9-posts.mjs --dry-run
 *   node scripts/publish-sep9-posts.mjs
 *   npm run publish:sep9-posts
 */

import { createClient } from "@sanity/client";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import {
  applyLinkInjections,
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

const sourceDir = resolve(root, "sanity/seed/source");

const postSpecs = [
  {
    file: "sep9-best-fpa-software-saas-companies.md",
    _id: "post-best-fpa-software-saas-companies",
    publishedAt: "2026-09-09T15:00:00.000Z",
    categories: ["category-trust-reporting"],
    linkInjections: [],
  },
  {
    file: "sep9-ai-costs-saas-fpa.md",
    _id: "post-ai-costs-saas-fpa",
    publishedAt: "2026-09-09T17:00:00.000Z",
    categories: ["category-ai-in-fpa"],
    linkInjections: [],
    tableCaptions: [
      "Illustrative AI cost sensitivity: baseline versus higher adoption, holding ARR constant at $20M.",
    ],
  },
];

function buildPost(spec) {
  const path = resolve(sourceDir, spec.file);
  const fullText = readFileSync(path, "utf8");
  const meta = parseDeliverables(fullText);

  for (const field of ["slug", "seoTitle", "excerpt", "title"]) {
    if (!meta[field]) throw new Error(`${spec.file}: missing ${field}`);
  }

  let articleMd = extractArticleMarkdown(fullText);
  articleMd = applyLinkInjections(articleMd, spec.linkInjections);
  resetBlockKeys();
  const body = markdownToBlocks(articleMd, {
    tableCaptions: spec.tableCaptions,
  });

  return {
    _id: spec._id,
    _type: "post",
    title: meta.title,
    slug: { _type: "slug", current: meta.slug },
    excerpt: meta.excerpt,
    publishedAt: spec.publishedAt,
    author: { _type: "reference", _ref: "author-smpl-team" },
    categories: spec.categories.map((ref) => ({
      _type: "reference",
      _ref: ref,
    })),
    seoTitle: meta.seoTitle,
    seoDescription: meta.excerpt,
    body,
  };
}

function summarize(doc) {
  const counts = {};
  const links = new Set();
  for (const b of doc.body) {
    const kind =
      b._type === "block" ? (b.listItem ? `list:${b.listItem}` : b.style) : b._type;
    counts[kind] = (counts[kind] || 0) + 1;
    for (const def of b.markDefs ?? []) {
      if (def._type === "link") links.add(def.href);
    }
  }
  console.log(`\n--- ${doc.slug.current} ---`);
  console.log(`  title:      ${doc.title}`);
  console.log(`  seoTitle:   ${doc.seoTitle} (${doc.seoTitle.length})`);
  console.log(`  excerpt:    ${doc.excerpt.length} chars`);
  console.log(`  blocks:     ${JSON.stringify(counts)}`);
  console.log(`  links:`);
  for (const href of [...links].sort()) console.log(`    ${href}`);
  const tables = doc.body.filter((b) => b._type === "comparisonTable");
  for (const t of tables) {
    console.log(
      `  table: rowHeader="${t.rowHeader}" columns=${JSON.stringify(t.columns)} rows=${t.rows.length}`,
    );
    console.log(
      `    sample: ${t.rows[0].capability} | ${t.rows[0].marks.join(" | ")}`,
    );
  }
}

async function main() {
  const posts = postSpecs.map(buildPost);

  for (const doc of posts) {
    if (doc._id.includes(".")) {
      throw new Error(`Seed doc ${doc._id} uses '.' — use hyphens.`);
    }
    summarize(doc);
  }

  if (dryRun) {
    console.log("\nDry run: nothing written.");
    return;
  }

  const slugs = posts.map((p) => p.slug.current);
  const draftIds = await client.fetch(
    `*[_type == "post" && slug.current in $slugs && _id in path("drafts.**")]._id`,
    { slugs },
  );

  const tx = client.transaction();
  for (const doc of posts) {
    tx.createOrReplace(doc);
  }
  for (const id of draftIds) {
    tx.delete(id);
  }
  await tx.commit();

  console.log(`\nPublished ${posts.length} posts → ${projectId}/${dataset}`);
  for (const p of posts) {
    console.log(`  /blog/${p.slug.current}`);
  }
  if (draftIds.length) {
    console.log(`Deleted ${draftIds.length} draft(s).`);
  }

  const confirm = await client.fetch(
    `*[_type == "post" && slug.current in $slugs]{title, "slug": slug.current, publishedAt, seoTitle}`,
    { slugs },
  );
  console.log("Confirmed:", JSON.stringify(confirm, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
