/**
 * Publish Sep 1, 2026 blog cluster: data bullwhip effect + FP&A platform for SaaS.
 *
 * Usage (from frontend/):
 *   node scripts/publish-sep1-posts.mjs
 *   npm run publish:sep1-posts
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
    file: "sep1-data-bullwhip-effect-finance.md",
    _id: "post-data-bullwhip-effect-finance",
    publishedAt: "2026-09-01T16:00:00.000Z",
    categories: ["category-trust-reporting"],
    linkInjections: [
      [
        "Lee, Padmanabhan and Whang made it widely known in a 1997 Sloan Management Review article.",
        "[Lee, Padmanabhan and Whang made it widely known in a 1997 Sloan Management Review article](https://sloanreview.mit.edu/article/the-bullwhip-effect-in-supply-chains/).",
      ],
      [
        "Finance becomes the human integration layer, resolving these differences manually, every period, forever.",
        "Finance becomes [the human integration layer](/blog/ai-operating-system-for-saas-finance), resolving these differences manually, every period, forever.",
      ],
      [
        "**A modern FP&A platform should not only help Finance model the future. It should help Finance reliably understand the present.**",
        "**[A modern FP&A platform](/blog/fpa-platform-saas) should not only help Finance model the future. It should help Finance reliably understand the present.**",
      ],
    ],
  },
  {
    file: "sep1-fpa-platform-saas.md",
    _id: "post-fpa-platform-saas",
    publishedAt: "2026-09-01T18:00:00.000Z",
    categories: ["category-trust-reporting"],
    linkInjections: [
      [
        "If the present is assembled by hand every month from four systems that disagree, a better modeling engine does not fix much.",
        "If the present is assembled by hand every month from [four systems that disagree](/blog/data-bullwhip-effect-finance), a better modeling engine does not fix much.",
      ],
      [
        "And ask what happens when systems disagree, because they will.",
        "And ask [what happens when systems disagree](/blog/data-bullwhip-effect-finance), because they will.",
      ],
      [
        "The reason we built it around that sequence is the argument in this article.",
        "The reason we built it around that sequence is the argument in this article and in our guide to [an AI operating system for SaaS finance](/blog/ai-operating-system-for-saas-finance).",
      ],
    ],
  },
];

function buildPost(spec) {
  const path = resolve(sourceDir, spec.file);
  const fullText = readFileSync(path, "utf8");
  const meta = parseDeliverables(fullText);
  let articleMd = extractArticleMarkdown(fullText);
  articleMd = applyLinkInjections(articleMd, spec.linkInjections);
  resetBlockKeys();
  const body = markdownToBlocks(articleMd);

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

async function main() {
  const posts = postSpecs.map(buildPost);

  for (const doc of posts) {
    if (doc._id.includes(".")) {
      throw new Error(`Seed doc ${doc._id} uses '.' — use hyphens.`);
    }
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

  console.log(`Published ${posts.length} posts → ${projectId}/${dataset}`);
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
