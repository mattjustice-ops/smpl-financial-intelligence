/**
 * Oct 8, 2026: buyer’s guide date and three product links.
 *
 * Sets publishedAt from 2026-09-09T15:00:00.000Z to 2026-09-30T15:00:00.000Z
 * (the September 30 content update; the visible date still said September 9).
 * Wraps existing phrases. Paragraph text is unchanged.
 *   "board reporting"            -> /saas-board-reporting
 *   first "Plan Assurance"       -> /budgeting-and-plan-assurance
 *   "ARR, retention, bookings"   -> /arr-revenue-cash-headcount
 *
 * Usage (from frontend/):
 *   node scripts/publish-oct8-guide-links.mjs --dry-run
 *   node scripts/publish-oct8-guide-links.mjs
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

const SLUG = "best-fpa-software-saas-companies";
const OLD_DATE = "2026-09-09T15:00:00.000Z";
const NEW_DATE = "2026-09-30T15:00:00.000Z";

const LINKS = [
  { blockKey: "b219", spanKey: "s218", anchor: "board reporting", href: "/saas-board-reporting", markKey: "lBoard" },
  { blockKey: "b222", spanKey: "s221", anchor: "Plan Assurance", href: "/budgeting-and-plan-assurance", markKey: "lPlan" },
  { blockKey: "b228", spanKey: "s227", anchor: "ARR, retention, bookings", href: "/arr-revenue-cash-headcount", markKey: "lArr" },
];

const blockText = (b) => (b.children ?? []).map((c) => c.text ?? "").join("");

function linkFirst(block, { spanKey, anchor, href, markKey }) {
  if ((block.markDefs ?? []).some((d) => d.href === href)) return { block, status: "already" };
  const span = (block.children ?? []).find((c) => c._key === spanKey);
  if (!span) throw new Error(`${block._key}: span ${spanKey} missing`);
  const at = (span.text ?? "").indexOf(anchor);
  if (at < 0) throw new Error(`${block._key}: anchor not in ${spanKey}`);
  if ((span.marks ?? []).length) throw new Error(`${block._key}: ${spanKey} already has marks`);

  const pieces = [
    { text: span.text.slice(0, at), marks: [] },
    { text: anchor, marks: [markKey] },
    { text: span.text.slice(at + anchor.length), marks: [] },
  ].filter((p) => p.text);

  const children = block.children.flatMap((c) =>
    c._key !== spanKey
      ? [c]
      : pieces.map((p, i) => ({ ...c, _key: `${c._key}${i}`, text: p.text, marks: p.marks })),
  );
  const next = {
    ...block,
    markDefs: [...(block.markDefs ?? []), { _type: "link", _key: markKey, href }],
    children,
  };
  if (blockText(next) !== blockText(block)) throw new Error(`${block._key}: text would change`);
  return { block: next, status: "plan" };
}

async function main() {
  const post = await client.fetch(
    `*[_type == "post" && slug.current == $slug && !(_id in path("drafts.**"))][0]{_id, _rev, publishedAt, body}`,
    { slug: SLUG },
  );
  if (!post) throw new Error("Post not found");
  const draft = await client.fetch(`defined(*[_id == $id][0]._id)`, { id: `drafts.${post._id}` });
  if (draft) throw new Error("Unpublished Studio draft exists; publish or discard it first");

  const dateStatus =
    post.publishedAt === NEW_DATE ? "already" : post.publishedAt === OLD_DATE ? "plan" : "mismatch";
  if (dateStatus === "mismatch") {
    throw new Error(`publishedAt is ${post.publishedAt}, expected ${OLD_DATE} or ${NEW_DATE}`);
  }
  console.log(`date  ${dateStatus}: ${post.publishedAt} -> ${NEW_DATE}`);

  const body = post.body.map((b) => ({ ...b }));
  for (const link of LINKS) {
    const index = body.findIndex((b) => b._key === link.blockKey);
    if (index < 0) throw new Error(`Block ${link.blockKey} missing`);
    const result = linkFirst(body[index], link);
    body[index] = result.block;
    console.log(`link  ${result.status}: "${link.anchor}" -> ${link.href}`);
  }

  if (dryRun) {
    console.log("\nDry run: nothing written.");
    return;
  }

  let patch = client.patch(post._id).ifRevisionId(post._rev);
  if (dateStatus === "plan") patch = patch.set({ publishedAt: NEW_DATE });
  if (LINKS.some((link) => !(post.body.find((b) => b._key === link.blockKey)?.markDefs ?? []).some((d) => d.href === link.href))) {
    patch = patch.set({ body });
  }
  await patch.commit();

  const saved = await client.fetch(
    `*[_id == $id][0]{ publishedAt, body[]{ _key, children[]{ text }, markDefs[]{ href } } }`,
    { id: post._id },
  );
  if (saved.publishedAt !== NEW_DATE) throw new Error(`publishedAt saved as ${saved.publishedAt}`);
  for (const link of LINKS) {
    const block = saved.body.find((b) => b._key === link.blockKey);
    const hrefs = (block?.markDefs ?? []).map((d) => d.href);
    if (!hrefs.includes(link.href)) throw new Error(`Missing ${link.href} on ${link.blockKey}`);
    const text = (block.children ?? []).map((c) => c.text ?? "").join("");
    if (!text.includes(link.anchor)) throw new Error(`Anchor missing after save: ${link.anchor}`);
  }
  console.log(`Committed ${SLUG}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
