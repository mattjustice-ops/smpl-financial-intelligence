/**
 * Publish FISoD SEO package:
 * - Jul 30 posts (seoTitle leads with FISoD; slug unchanged)
 * - Jul 29 + finance-os posts (internal links with FISoD / segregation of duties)
 * - Glossary terms: FISoD + Segregation of duties
 * - Live patches for explainable-ai + financial-data-governance (no seed files)
 *
 * Usage (from frontend/):
 *   node scripts/publish-fisod-seo.mjs
 *   # or: npm run publish:fisod-seo
 */

import { createClient } from "@sanity/client";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { july30Posts } from "../sanity/seed/july30-posts.mjs";
import { july29Posts } from "../sanity/seed/july29-posts.mjs";
import { financeOsPosts } from "../sanity/seed/finance-os-posts.mjs";
import { glossaryTerms } from "../sanity/seed/content.mjs";

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

let keySeq = 0;
function key(prefix = "k") {
  keySeq += 1;
  return `${prefix}${keySeq}`;
}

/** Minimal markdown → Portable Text block with link support. */
function paragraphWithLinks(text) {
  const markDefs = [];
  const children = [];
  const re = /(\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      children.push({
        _type: "span",
        _key: key("s"),
        text: text.slice(last, m.index),
        marks: [],
      });
    }
    const token = m[0];
    if (token.startsWith("**")) {
      children.push({
        _type: "span",
        _key: key("s"),
        text: token.slice(2, -2),
        marks: ["strong"],
      });
    } else {
      const linkMatch = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      const markKey = key("l");
      markDefs.push({
        _type: "link",
        _key: markKey,
        href: linkMatch[2],
      });
      children.push({
        _type: "span",
        _key: key("s"),
        text: linkMatch[1],
        marks: [markKey],
      });
    }
    last = m.index + token.length;
  }
  if (last < text.length) {
    children.push({
      _type: "span",
      _key: key("s"),
      text: text.slice(last),
      marks: [],
    });
  }
  return {
    _type: "block",
    _key: key("b"),
    style: "normal",
    markDefs,
    children,
  };
}

async function upsertPosts(posts, label) {
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
  for (const doc of posts) tx.createOrReplace(doc);
  for (const id of draftIds) tx.delete(id);
  await tx.commit();
  console.log(`Published ${posts.length} ${label} posts → ${projectId}/${dataset}`);
  for (const p of posts) console.log(`  /blog/${p.slug.current}`);
}

async function upsertGlossary() {
  const terms = glossaryTerms.filter((t) =>
    ["glossary-fisod", "glossary-segregation-of-duties"].includes(t._id),
  );
  if (terms.length !== 2) {
    throw new Error("Expected glossary-fisod and glossary-segregation-of-duties in content.mjs");
  }
  const tx = client.transaction();
  for (const doc of terms) tx.createOrReplace(doc);
  await tx.commit();
  console.log("Published glossary terms:");
  for (const t of terms) console.log(`  /glossary/${t.slug.current}`);
}

/**
 * Insert a FISoD paragraph once into posts that have no seed file in-repo.
 * Idempotent: skips if body already mentions the FISoD blog path.
 */
async function patchLivePostLink({ slug, afterKey, markdown }) {
  const post = await client.fetch(
    `*[_type=="post" && slug.current==$slug][0]{_id, "slug": slug.current, body}`,
    { slug },
  );
  if (!post?._id) {
    console.warn(`Skip patch: post not found (${slug})`);
    return;
  }
  const bodyText = JSON.stringify(post.body || []);
  if (bodyText.includes("/blog/financial-intelligence-segregation-of-duties")) {
    console.log(`Skip patch (already linked): /blog/${slug}`);
    return;
  }
  const hasAnchor = (post.body || []).some((b) => b?._key === afterKey);
  if (!hasAnchor) {
    console.warn(`Skip patch: anchor _key ${afterKey} missing on ${slug}`);
    return;
  }
  const block = paragraphWithLinks(markdown);
  await client
    .patch(post._id)
    .insert("after", `body[_key=="${afterKey}"]`, [block])
    .commit({ autoGenerateArrayKeys: false });
  console.log(`Patched FISoD link into /blog/${slug} (after ${afterKey})`);
}

async function main() {
  const fisod = july30Posts.find(
    (p) => p.slug.current === "financial-intelligence-segregation-of-duties",
  );
  if (!fisod) throw new Error("FISoD post missing from july30 seed");
  if (fisod.slug.current !== "financial-intelligence-segregation-of-duties") {
    throw new Error("Refusing to change FISoD slug");
  }
  if (!String(fisod.seoTitle || "").includes("FISoD")) {
    throw new Error("FISoD seoTitle must include FISoD");
  }

  await upsertPosts(july30Posts, "july30");
  await upsertPosts(july29Posts, "july29");
  await upsertPosts(financeOsPosts, "finance-os");
  await upsertGlossary();

  await patchLivePostLink({
    slug: "explainable-ai-in-finance",
    afterKey: "b649",
    markdown:
      "That separation — deterministic calculation first, AI interpretation second — is what we call [Financial Intelligence Segregation of Duties (FISoD)](/blog/financial-intelligence-segregation-of-duties): segregation of duties applied to finance AI.",
  });
  await patchLivePostLink({
    slug: "financial-data-governance-saas-finance",
    afterKey: "b1018",
    markdown:
      "We've named the AI side of that discipline [Financial Intelligence Segregation of Duties (FISoD)](/blog/financial-intelligence-segregation-of-duties) — segregation of duties for finance AI, so models explain trusted results rather than creating and validating their own.",
  });

  const confirm = await client.fetch(
    `{
      "fisod": *[_type=="post" && slug.current=="financial-intelligence-segregation-of-duties"][0]{
        title, "slug": slug.current, seoTitle, seoDescription
      },
      "glossary": *[_type=="glossaryTerm" && slug.current in ["fisod","segregation-of-duties"]]{
        term, "slug": slug.current, shortDefinition
      }
    }`,
  );
  console.log("Confirmed:", JSON.stringify(confirm, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
