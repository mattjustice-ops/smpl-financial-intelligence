/**
 * Sep 30, 2026 release: refresh four existing posts from their seed markdown
 * (SMPL-led implementation, customer-initiated refresh, ERP-consolidated results).
 *
 * Patches only title, excerpt, seoTitle, seoDescription, and body on the four
 * published documents below. slug, publishedAt, author, categories, mainImage,
 * and any other fields are left untouched. Refuses to run if any of the four
 * has an unpublished Studio draft.
 *
 * Usage (from frontend/):
 *   node scripts/publish-sep30-integrations-refresh.mjs --dry-run
 *   node scripts/publish-sep30-integrations-refresh.mjs
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

/** Link injections replay what the original publish scripts applied on top of the seed. */
const SPECS = [
  {
    _id: "post-best-fpa-software-saas-companies",
    file: "sep9-best-fpa-software-saas-companies.md",
    linkInjections: [],
  },
  {
    _id: "post-fpa-software-implementation",
    file: "sep15-fpa-software-implementation.md",
    linkInjections: [],
  },
  {
    _id: "post-fpa-platform-saas",
    file: "sep1-fpa-platform-saas.md",
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
  {
    _id: "post-billing-vs-crm-arr",
    file: "sep15-billing-vs-crm-arr.md",
    linkInjections: [],
  },
];

function build(spec) {
  const fullText = readFileSync(resolve(sourceDir, spec.file), "utf8").replace(/\r\n/g, "\n");
  const meta = parseDeliverables(fullText);
  for (const field of ["slug", "seoTitle", "excerpt", "title"]) {
    if (!meta[field]) throw new Error(`${spec.file}: missing ${field}`);
  }
  const articleMd = applyLinkInjections(extractArticleMarkdown(fullText), spec.linkInjections);
  resetBlockKeys();
  return {
    slug: meta.slug.replace(/^\/?blog\//, "").replace(/^\//, ""),
    fields: {
      title: meta.title,
      excerpt: meta.excerpt,
      seoTitle: meta.seoTitle,
      seoDescription: meta.excerpt,
      body: markdownToBlocks(articleMd),
    },
  };
}

function blockSig(b) {
  if (b._type === "comparisonTable") {
    const rows = (b.rows ?? []).map((r) => `${r.capability} | ${(r.marks ?? []).join(" | ")}`);
    return `[table ${b.rowHeader} | ${(b.columns ?? []).join(" | ")}] ${rows.join(" // ")}`;
  }
  if (b._type !== "block") return `[${b._type}]`;
  const defs = new Map((b.markDefs ?? []).map((d) => [d._key, d]));
  const text = (b.children ?? [])
    .map((c) => {
      const link = (c.marks ?? []).map((m) => defs.get(m)).find((d) => d?._type === "link");
      return link ? `[${c.text}](${link.href})` : c.text;
    })
    .join("");
  const kind = b.listItem ? `${b.listItem}` : b.style;
  return `${kind}: ${text}`;
}

function diff(a, b) {
  const n = a.length;
  const m = b.length;
  const dp = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const out = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) out.push(`  - ${a[i++]}`);
    else out.push(`  + ${b[j++]}`);
  }
  while (i < n) out.push(`  - ${a[i++]}`);
  while (j < m) out.push(`  + ${b[j++]}`);
  return out;
}

const hrefs = (body) =>
  new Set(body.flatMap((b) => (b.markDefs ?? []).filter((d) => d._type === "link").map((d) => d.href)));

async function main() {
  const plans = [];
  for (const spec of SPECS) {
    const live = await client.fetch(`*[_id == $id][0]`, { id: spec._id });
    if (!live) throw new Error(`${spec._id}: published document not found`);
    const hasDraft = await client.fetch(`defined(*[_id == $id][0]._id)`, { id: `drafts.${spec._id}` });
    if (hasDraft) throw new Error(`${spec._id} has an unpublished Studio draft; stopping without writing`);

    const next = build(spec);
    if (live.slug?.current !== next.slug) {
      throw new Error(`${spec._id}: live slug ${live.slug?.current} != seed slug ${next.slug}`);
    }

    console.log(`\n=== ${spec._id} (/blog/${next.slug}) rev ${live._rev}`);
    for (const f of ["title", "excerpt", "seoTitle", "seoDescription"]) {
      const same = live[f] === next.fields[f];
      console.log(`  ${f}: ${same ? "unchanged" : `CHANGED\n    live: ${live[f]}\n    seed: ${next.fields[f]}`}`);
    }
    console.log(
      `  preserved: publishedAt=${live.publishedAt} author=${live.author?._ref} categories=${(live.categories ?? []).map((c) => c._ref).join(",")} mainImage=${live.mainImage ? "yes" : "no"}`,
    );
    const lost = [...hrefs(live.body ?? [])].filter((h) => !hrefs(next.fields.body).has(h));
    const added = [...hrefs(next.fields.body)].filter((h) => !hrefs(live.body ?? []).has(h));
    console.log(`  links lost: ${lost.length ? lost.join(", ") : "none"}`);
    console.log(`  links added: ${added.length ? added.join(", ") : "none"}`);
    const d = diff((live.body ?? []).map(blockSig), next.fields.body.map(blockSig));
    console.log(`  body blocks: live ${live.body?.length ?? 0} -> seed ${next.fields.body.length}; ${d.length} changed lines`);
    for (const line of d) console.log(line);

    plans.push({ spec, live, next });
  }

  if (dryRun) {
    console.log("\nDry run: nothing written.");
    return;
  }

  const tx = client.transaction();
  for (const { spec, live, next } of plans) {
    tx.patch(spec._id, (p) => p.ifRevisionId(live._rev).set(next.fields));
  }
  await tx.commit();

  const confirm = await client.fetch(
    `*[_id in $ids]{_id, _rev, _updatedAt, title, "slug": slug.current, publishedAt, seoTitle, seoDescription, "blocks": count(body)}`,
    { ids: SPECS.map((s) => s._id) },
  );
  console.log("\nPublished:", JSON.stringify(confirm, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
