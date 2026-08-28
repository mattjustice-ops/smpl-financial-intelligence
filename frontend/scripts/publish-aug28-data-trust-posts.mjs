/**
 * Publish connected-systems + financial-data-validation cluster posts (Aug 28).
 * Reads Matt's markdown drafts; preserves voice; minimal series/cluster links.
 *
 * Usage (from frontend/):
 *   node scripts/publish-aug28-data-trust-posts.mjs
 */

import { createClient } from "@sanity/client";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

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

let keySeq = 0;
function key(prefix = "k") {
  keySeq += 1;
  return `${prefix}${keySeq}`;
}

function parseInline(text) {
  const markDefs = [];
  const children = [];
  const re =
    /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
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
    } else if (token.startsWith("*")) {
      children.push({
        _type: "span",
        _key: key("s"),
        text: token.slice(1, -1),
        marks: ["em"],
      });
    } else if (token.startsWith("`")) {
      children.push({
        _type: "span",
        _key: key("s"),
        text: token.slice(1, -1),
        marks: ["code"],
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
  if (children.length === 0) {
    children.push({ _type: "span", _key: key("s"), text: "", marks: [] });
  }
  return { children, markDefs };
}

function block(style, text, extras = {}) {
  const { children, markDefs } = parseInline(text);
  return {
    _type: "block",
    _key: key("b"),
    style,
    markDefs,
    children,
    ...extras,
  };
}

function parseArticle(md) {
  let text = md.replace(/^<!--[\s\S]*?-->\s*/m, "");
  const metaMatch = text.match(
    /^# Meta\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)$/m,
  );
  if (!metaMatch) throw new Error("Could not find # Meta block");
  const metaRaw = metaMatch[1];
  let body = metaMatch[2];

  const meta = {};
  for (const line of metaRaw.split(/\r?\n/)) {
    const m = line.match(/^\-\s+\*\*([^*]+):\*\*\s+(.+?)\s*$/);
    if (!m) continue;
    const k = m[1].trim().toLowerCase();
    let v = m[2].trim();
    if (v.startsWith("`") && v.endsWith("`")) v = v.slice(1, -1);
    meta[k] = v;
  }

  body = body.replace(/\n---\s*\n+\*Internal glossary[\s\S]*$/i, "");
  body = body.trim();

  return { meta, body };
}

function normalizeCtaLine(line) {
  let t = line.trim();
  if (t.startsWith("*") && t.endsWith("*") && !t.startsWith("**")) {
    t = t.slice(1, -1).trim();
  }
  t = t.replace(/\]\(http:\/\/www\.smpl-ai\.com\/?\)/g, "](https://www.smpl-ai.com)");
  t = t.replace(
    /\]\(http:\/\/www\.smpl-ai\.com\)/g,
    "](https://www.smpl-ai.com)",
  );
  return t;
}

function mdToBlocks(bodyMd) {
  const lines = bodyMd.split(/\r?\n/);
  const blocks = [];
  let i = 0;

  function flushParagraph(buf) {
    const text = normalizeCtaLine(buf.join(" ").replace(/\s+/g, " ").trim());
    if (text) blocks.push(block("normal", text));
  }

  while (i < lines.length) {
    const trimmed = lines[i].trim();

    if (!trimmed || trimmed === "---") {
      i += 1;
      continue;
    }

    if (trimmed.startsWith("### ")) {
      blocks.push(block("h3", trimmed.slice(4).trim()));
      i += 1;
      continue;
    }
    if (trimmed.startsWith("## ")) {
      blocks.push(block("h2", trimmed.slice(3).trim()));
      i += 1;
      continue;
    }

    if (trimmed.startsWith("- ")) {
      while (i < lines.length && lines[i].trim().startsWith("- ")) {
        blocks.push(
          block("normal", lines[i].trim().slice(2).trim(), {
            listItem: "bullet",
            level: 1,
          }),
        );
        i += 1;
      }
      continue;
    }

    const buf = [trimmed];
    i += 1;
    while (i < lines.length) {
      const next = lines[i].trim();
      if (!next || next === "---") break;
      if (
        next.startsWith("## ") ||
        next.startsWith("### ") ||
        next.startsWith("- ")
      ) {
        break;
      }
      buf.push(next);
      i += 1;
    }
    flushParagraph(buf);
  }

  return blocks;
}

/** Minimal cluster link edits — preserve Matt's voice */
function applyClusterLinks(slug, body) {
  let out = body;

  out = out.replace(
    /\/blog\/ai-operating-system-for-finance/g,
    "/blog/ai-operating-system-for-saas-finance",
  );

  if (slug === "connected-systems-financial-data") {
    // value-gap link already in opening; hub link fixed above
  }

  if (slug === "financial-data-validation") {
    out = out.replace(
      /Most companies have invested in getting their financial data connected\./,
      "Most companies have invested in getting their [financial data connected](/blog/connected-systems-financial-data).",
    );
  }

  return out;
}

function relatedReadingBlocks(slug) {
  keySeq = 9000;
  if (slug === "connected-systems-financial-data") {
    return [
      block("h2", "Related reading"),
      block(
        "normal",
        "Earlier in this thread: [Finance has adopted AI — so where is the value?](/blog/finance-ai-value-gap). Next: [financial data validation](/blog/financial-data-validation). Cornerstone: [AI operating system for SaaS finance](/blog/ai-operating-system-for-saas-finance).",
      ),
    ];
  }
  return [
    block("h2", "Related reading"),
    block(
      "normal",
      "Series context: [connected systems vs. trusted financial data](/blog/connected-systems-financial-data), [finance AI value gap](/blog/finance-ai-value-gap), [AI vs. automation in finance](/blog/ai-vs-automation-finance), and [financial data governance](/blog/financial-data-governance-saas-finance).",
    ),
  ];
}

function metaGet(meta, ...keys) {
  for (const k of keys) {
    const hit = Object.entries(meta).find(
      ([key]) => key === k || key.startsWith(k),
    );
    if (hit) return hit[1];
  }
  return undefined;
}

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

const HUB_ID = "post-ai-operating-system-for-saas-finance";
const HUB_SPOKE_MARKER = "connected-systems-financial-data";

function hubRelatedReadingBlocks() {
  keySeq = 9000;
  return [
    block("h2", "Related reading"),
    block(
      "normal",
      "Two practical follow-ons from this category: [why AI vs. automation is the wrong question for Finance](/blog/ai-vs-automation-finance) and [build vs. buy for Finance AI](/blog/build-vs-buy-finance-ai). On data trust: [connected systems vs. trusted financial data](/blog/connected-systems-financial-data) and [financial data validation](/blog/financial-data-validation).",
    ),
  ];
}

async function patchHubRelated() {
  const hub = await client.fetch(`*[_id == $id][0]{_id, body}`, {
    id: HUB_ID,
  });
  if (!hub?.body) {
    console.warn("Hub not found; skip outbound related patch.");
    return false;
  }
  const joined = hub.body
    .map((b) => {
      const text = b.children?.map((c) => c.text).join("") || "";
      const hrefs = (b.markDefs || []).map((d) => d.href || "").join(" ");
      return `${text} ${hrefs}`;
    })
    .join("\n");
  if (joined.includes(HUB_SPOKE_MARKER)) {
    console.log("Hub already links to Aug 28 spokes; skip related patch.");
    return false;
  }

  const relatedIdx = hub.body.findIndex((b) => {
    const t = b.children?.map((c) => c.text).join("") || "";
    return b.style === "h2" && /Related reading/i.test(t);
  });
  if (relatedIdx < 0) {
    const idx = hub.body.findIndex((b) => {
      const t = b.children?.map((c) => c.text).join("") || "";
      return b.style === "h2" && /Where SMPL\.ai fits/i.test(t);
    });
    const insertAt = idx >= 0 ? idx : hub.body.length;
    const nextBody = [
      ...hub.body.slice(0, insertAt),
      ...hubRelatedReadingBlocks(),
      ...hub.body.slice(insertAt),
    ];
    await client.patch(HUB_ID).set({ body: nextBody }).commit();
    console.log("Inserted hub Related reading with Aug 28 spokes.");
    return true;
  }

  const nextH2Idx = hub.body.findIndex(
    (b, i) => i > relatedIdx && b.style === "h2",
  );
  const insertEnd = nextH2Idx >= 0 ? nextH2Idx : hub.body.length;
  const nextBody = [
    ...hub.body.slice(0, relatedIdx),
    ...hubRelatedReadingBlocks(),
    ...hub.body.slice(insertEnd),
  ];
  await client.patch(HUB_ID).set({ body: nextBody }).commit();
  console.log("Patched hub Related reading with Aug 28 spokes.");
  return true;
}

const articles = [
  {
    path: "c:\\Users\\mattj\\Downloads\\connected-systems-financial-data.md",
    _id: "post-connected-systems-financial-data",
    categoryRef: "category-ai-in-fpa",
    publishedAt: "2026-08-28T15:00:00.000Z",
  },
  {
    path: "c:\\Users\\mattj\\Downloads\\financial-data-validation.md",
    _id: "post-financial-data-validation",
    categoryRef: "category-ai-in-fpa",
    publishedAt: "2026-08-28T18:00:00.000Z",
  },
];

async function main() {
  const docs = [];

  for (const art of articles) {
    keySeq = 0;
    const md = readFileSync(art.path, "utf8");
    const { meta, body: rawBody } = parseArticle(md);
    const slug = metaGet(meta, "slug");
    const title = metaGet(meta, "on-page h1", "title");
    const seoTitleRaw = metaGet(meta, "meta / seo title", "seo title");
    const excerpt = metaGet(meta, "meta description", "description");
    if (!slug || !title || !excerpt) {
      throw new Error(
        `Missing meta in ${art.path}: ${JSON.stringify(meta, null, 2)}`,
      );
    }

    const body = applyClusterLinks(slug, rawBody);
    let bodyBlocks = mdToBlocks(body);

    // Insert Related reading before SMPL.ai CTA paragraph
    const ctaIdx = bodyBlocks.findIndex((b) => {
      const t = b.children?.map((c) => c.text).join("") || "";
      return /SMPL\.ai is an AI-powered financial intelligence platform/i.test(t);
    });
    const related = relatedReadingBlocks(slug);
    if (ctaIdx >= 0) {
      bodyBlocks = [
        ...bodyBlocks.slice(0, ctaIdx),
        ...related,
        ...bodyBlocks.slice(ctaIdx),
      ];
    } else {
      bodyBlocks = [...bodyBlocks, ...related];
    }

    const joined = bodyBlocks
      .map((b) => {
        const text = b.children?.map((c) => c.text).join("") || "";
        const hrefs = (b.markDefs || []).map((d) => d.href || "").join(" ");
        return `${text} ${hrefs}`;
      })
      .join("\n");
    if (/Internal glossary|Alternate titles/i.test(joined)) {
      throw new Error(`Cruft leaked into body for ${slug}`);
    }
    if (
      slug === "connected-systems-financial-data" &&
      !joined.includes("/blog/ai-operating-system-for-saas-finance")
    ) {
      throw new Error(`Missing hub link in ${slug}`);
    }
    if (
      slug === "financial-data-validation" &&
      !joined.includes("/blog/connected-systems-financial-data")
    ) {
      throw new Error(`Missing connected-systems link in ${slug}`);
    }

    const seoTitle = seoTitleRaw?.trim() || `${title} | SMPL.ai`;

    docs.push({
      _id: art._id,
      _type: "post",
      title,
      slug: { _type: "slug", current: slug },
      excerpt,
      publishedAt: art.publishedAt,
      author: { _type: "reference", _ref: "author-smpl-team" },
      categories: [{ _type: "reference", _ref: art.categoryRef }],
      seoTitle,
      seoDescription: excerpt,
      body: bodyBlocks,
    });
    console.log(
      `Prepared ${slug}: ${bodyBlocks.length} blocks, title="${title}"`,
    );
  }

  const slugs = docs.map((d) => d.slug.current);
  const draftIds = await client.fetch(
    `*[_type == "post" && slug.current in $slugs && _id in path("drafts.**")]._id`,
    { slugs },
  );

  const tx = client.transaction();
  for (const doc of docs) {
    tx.createOrReplace(doc);
  }
  for (const id of draftIds) {
    tx.delete(id);
  }
  await tx.commit();

  console.log(`Published ${docs.length} posts → ${projectId}/${dataset}`);
  for (const p of docs) {
    console.log(`  /blog/${p.slug.current}`);
  }
  if (draftIds.length) {
    console.log(`Deleted ${draftIds.length} draft(s).`);
  }

  await patchHubRelated();

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
