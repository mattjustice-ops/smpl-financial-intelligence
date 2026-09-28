/**
 * Add contextual internal links to /blog/fpa-software-implementation from existing posts.
 * Wraps an existing phrase in each post with a link; paragraph text is unchanged.
 *
 * Usage (from frontend/):
 *   node scripts/link-fpa-software-implementation.mjs --dry-run
 *   node scripts/link-fpa-software-implementation.mjs
 */

import { createClient } from "@sanity/client";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

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

const TARGET = "/blog/fpa-software-implementation";

const LINKS = [
  { slug: "best-fpa-software-saas-companies", anchor: "Implementation timelines" },
  { slug: "fpa-platform-saas", anchor: "implementation work that happens once before go-live" },
  {
    slug: "data-bullwhip-effect-finance",
    anchor: "treated data preparation as a phase that happens before planning begins",
  },
  { slug: "financial-data-validation", anchor: "a systems implementation" },
];

const blockText = (b) => (b.children ?? []).map((c) => c.text ?? "").join("");

function linkBlock(block, anchor) {
  const matches = block.children.filter((c) => (c.text ?? "").includes(anchor));
  if (matches.length !== 1) return null;
  const span = matches[0];
  if (span.text.indexOf(anchor) !== span.text.lastIndexOf(anchor)) return null;

  const markKey = `implLink${block._key}`.slice(0, 24);
  const at = span.text.indexOf(anchor);
  const pieces = [
    { text: span.text.slice(0, at), marks: span.marks ?? [] },
    { text: anchor, marks: [...(span.marks ?? []), markKey] },
    { text: span.text.slice(at + anchor.length), marks: span.marks ?? [] },
  ].filter((p) => p.text);

  const children = block.children.flatMap((c) =>
    c._key !== span._key
      ? [c]
      : pieces.map((p, i) => ({ ...c, _key: `${c._key}${i}`, text: p.text, marks: p.marks })),
  );
  return {
    ...block,
    markDefs: [...(block.markDefs ?? []), { _type: "link", _key: markKey, href: TARGET }],
    children,
  };
}

async function main() {
  const planned = [];
  for (const { slug, anchor } of LINKS) {
    const post = await client.fetch(
      `*[_type == "post" && slug.current == $slug && !(_id in path("drafts.**"))][0]{_id, _rev, body}`,
      { slug },
    );
    if (!post) throw new Error(`Post not found: ${slug}`);

    const draft = await client.fetch(`defined(*[_id == $id][0]._id)`, { id: `drafts.${post._id}` });
    if (draft) throw new Error(`${slug} has an unpublished Studio draft; publish or discard it first`);

    if ((post.body ?? []).some((b) => (b.markDefs ?? []).some((d) => d.href === TARGET))) {
      console.log(`skip  ${slug}: already links to ${TARGET}`);
      continue;
    }

    const candidates = post.body.filter((b) => b._type === "block" && blockText(b).includes(anchor));
    if (candidates.length !== 1) {
      throw new Error(`${slug}: anchor must appear in exactly one block, found ${candidates.length}`);
    }
    const block = candidates[0];
    const next = linkBlock(block, anchor);
    if (!next) throw new Error(`${slug}: anchor is split across spans or repeated in the block`);
    if (blockText(next) !== blockText(block)) throw new Error(`${slug}: paragraph text would change`);

    planned.push({ slug, post, block, next });
    console.log(`plan  ${slug}: "${anchor}"`);
  }

  if (dryRun) {
    console.log("\nDry run: nothing written.");
    return;
  }

  for (const { slug, post, block, next } of planned) {
    await client
      .patch(post._id)
      .ifRevisionId(post._rev)
      .set({ [`body[_key=="${block._key}"]`]: next })
      .commit();
    const saved = await client.fetch(`*[_id == $id][0].body[_key == $key][0]`, {
      id: post._id,
      key: block._key,
    });
    if (!saved?.markDefs?.some((d) => d.href === TARGET) || blockText(saved) !== blockText(block)) {
      throw new Error(`${slug}: link not found after patch`);
    }
    console.log(`done  https://www.smpl-ai.com/blog/${slug}`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
