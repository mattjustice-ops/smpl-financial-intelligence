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

async function main() {
  console.log(`Seeding ${docs.length} documents → ${projectId}/${dataset}`);
  const tx = client.transaction();
  for (const doc of docs) {
    tx.createOrReplace(doc);
  }
  await tx.commit();
  console.log("Done. Publish is automatic for createOrReplace (published docs).");
  console.log("Visit /blog and /glossary (or /studio to edit).");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
