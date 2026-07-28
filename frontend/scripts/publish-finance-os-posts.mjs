/**
 * Upsert only the Finance OS category posts (does not re-seed the whole corpus).
 *
 * Usage (from frontend/):
 *   node scripts/publish-finance-os-posts.mjs
 */

import { createClient } from "@sanity/client";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { financeOsPosts } from "../sanity/seed/finance-os-posts.mjs";

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
  for (const doc of financeOsPosts) {
    if (doc._id.includes(".")) {
      throw new Error(`Seed doc ${doc._id} uses '.' — use hyphens.`);
    }
  }

  // Drop any draft scaffolding if Studio created drafts for these slugs.
  const slugs = financeOsPosts.map((p) => p.slug.current);
  const draftIds = await client.fetch(
    `*[_type == "post" && slug.current in $slugs && _id in path("drafts.**")]._id`,
    { slugs },
  );

  const tx = client.transaction();
  for (const doc of financeOsPosts) {
    tx.createOrReplace(doc);
  }
  for (const id of draftIds) {
    tx.delete(id);
  }
  await tx.commit();

  console.log(
    `Published ${financeOsPosts.length} posts → ${projectId}/${dataset}`,
  );
  for (const p of financeOsPosts) {
    console.log(`  /blog/${p.slug.current}`);
  }
  if (draftIds.length) {
    console.log(`Deleted ${draftIds.length} draft(s).`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
