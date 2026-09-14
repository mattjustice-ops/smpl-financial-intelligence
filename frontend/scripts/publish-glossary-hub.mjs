/**
 * Upsert expanded glossary hub terms into Sanity (bodies + clusters + related refs).
 * Does NOT delete Studio-only terms (e.g. FISoD).
 *
 * Two passes: (1) upsert docs without related refs, (2) patch related refs that exist.
 *
 * Usage (from frontend/):
 *   npm run publish:glossary-hub
 */

import { createClient } from "@sanity/client";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { glossaryTerms } from "../sanity/seed/glossary-hub.mjs";

const INDEXABLE_CHARS = 800;

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

function plainLen(body) {
  return (body || [])
    .map((b) => (b.children || []).map((c) => c.text || "").join(""))
    .join(" ").length;
}

async function main() {
  console.log(
    `Publishing ${glossaryTerms.length} glossary terms → ${projectId}/${dataset}`,
  );

  let thin = 0;

  // Pass 1: upsert content without related refs (avoids missing-ref errors on new slugs)
  for (const term of glossaryTerms) {
    const chars = plainLen(term.body);
    const slug = term.slug.current;
    if (chars < INDEXABLE_CHARS) {
      console.warn(`  ! ${slug}: ${chars} chars (< ${INDEXABLE_CHARS})`);
      thin += 1;
    } else {
      console.log(`  ✓ ${slug}: ${chars} chars [${term.cluster}]`);
    }

    const { relatedTerms, relatedPosts, ...rest } = term;
    await client.createOrReplace({
      ...rest,
      relatedTerms: [],
      relatedPosts: [],
    });
  }

  // Pass 2: attach related refs that exist in the dataset
  for (const term of glossaryTerms) {
    const relatedTermIds = (term.relatedTerms || []).map((r) => r._ref);
    const relatedPostIds = (term.relatedPosts || []).map((r) => r._ref);

    const existingTerms = relatedTermIds.length
      ? await client.fetch(`*[_id in $ids]._id`, { ids: relatedTermIds })
      : [];
    const existingPosts = relatedPostIds.length
      ? await client.fetch(`*[_id in $ids]._id`, { ids: relatedPostIds })
      : [];
    const termSet = new Set(existingTerms);
    const postSet = new Set(existingPosts);

    await client
      .patch(term._id)
      .set({
        relatedTerms: (term.relatedTerms || []).filter((r) =>
          termSet.has(r._ref),
        ),
        relatedPosts: (term.relatedPosts || []).filter((r) =>
          postSet.has(r._ref),
        ),
      })
      .commit();
  }

  console.log(
    `\nUpserted ${glossaryTerms.length} terms. Thin (warn only): ${thin}.`,
  );
  console.log("Visit https://www.smpl-ai.com/glossary after deploy/revalidate.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
