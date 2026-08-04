/**
 * Upsert the Aug 4 blog posts (no-standard ARR + GRR vs NRR).
 * Order in seed: no-standard-arr-calculation first, then grr-vs-nrr.
 *
 * Usage (from frontend/):
 *   node scripts/publish-aug4-posts.mjs
 *   # or: npm run publish:aug4-posts
 */

import { createClient } from "@sanity/client";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { aug4Posts } from "../sanity/seed/aug4-posts.mjs";

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

async function main() {
  for (const doc of aug4Posts) {
    if (doc._id.includes(".")) {
      throw new Error(`Seed doc ${doc._id} uses '.' — use hyphens.`);
    }
  }

  const slugs = aug4Posts.map((p) => p.slug.current);
  const draftIds = await client.fetch(
    `*[_type == "post" && slug.current in $slugs && _id in path("drafts.**")]._id`,
    { slugs },
  );

  // Publish in seed order so no-standard lands before grr-vs-nrr.
  const tx = client.transaction();
  for (const doc of aug4Posts) {
    tx.createOrReplace(doc);
  }
  for (const id of draftIds) {
    tx.delete(id);
  }
  await tx.commit();

  console.log(`Published ${aug4Posts.length} posts → ${projectId}/${dataset}`);
  for (const p of aug4Posts) {
    console.log(`  /blog/${p.slug.current}`);
  }
  if (draftIds.length) {
    console.log(`Deleted ${draftIds.length} draft(s).`);
  }

  const confirm = await client.fetch(
    `*[_type == "post" && slug.current in $slugs]{title, "slug": slug.current, publishedAt, seoTitle, seoDescription, "categories": categories[]->title}`,
    { slugs },
  );
  console.log("Confirmed:", JSON.stringify(confirm, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
