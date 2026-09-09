/**
 * Convert blog article markdown (headings, paragraphs, blockquotes, lists) to Sanity blockContent.
 */

let keySeq = 0;
function key(prefix = "k") {
  keySeq += 1;
  return `${prefix}${keySeq}`;
}

/** Reset keys between documents so blocks stay deterministic within one import. */
export function resetBlockKeys() {
  keySeq = 0;
}

/** Parse inline markdown: **strong**, *em*, `code`, [label](href) */
export function parseInline(text) {
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

const TABLE_DIVIDER = /^\|[\s:|-]+\|$/;

function parseTableRow(line) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

/**
 * @param {string} markdown
 * @param {{ tableCaptions?: string[] }} [options] Captions applied to GFM tables in document order.
 */
export function markdownToBlocks(markdown, options = {}) {
  const tableCaptions = options.tableCaptions ?? [];
  let tableIndex = 0;
  const lines = markdown.split(/\r?\n/);
  const blocks = [];
  let paragraphBuffer = [];

  function flushParagraph() {
    if (paragraphBuffer.length === 0) return;
    const text = paragraphBuffer.join(" ").trim();
    paragraphBuffer = [];
    if (text) blocks.push(block("normal", text));
  }

  for (let i = 0; i < lines.length; ) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      flushParagraph();
      i += 1;
      continue;
    }

    if (trimmed.startsWith("## ")) {
      flushParagraph();
      blocks.push(block("h2", trimmed.slice(3)));
      i += 1;
      continue;
    }

    if (trimmed.startsWith("### ")) {
      flushParagraph();
      blocks.push(block("h3", trimmed.slice(4)));
      i += 1;
      continue;
    }

    if (
      trimmed.startsWith("|") &&
      i + 1 < lines.length &&
      TABLE_DIVIDER.test(lines[i + 1].trim())
    ) {
      flushParagraph();
      const header = parseTableRow(trimmed);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        rows.push(parseTableRow(lines[i]));
        i += 1;
      }
      const caption = tableCaptions[tableIndex];
      tableIndex += 1;
      blocks.push({
        _type: "comparisonTable",
        _key: key("t"),
        ...(caption ? { caption } : {}),
        rowHeader: header[0],
        columns: header.slice(1),
        showLegend: false,
        rows: rows.map((cells) => ({
          _type: "comparisonRow",
          _key: key("r"),
          capability: cells[0],
          marks: cells.slice(1),
        })),
      });
      continue;
    }

    if (trimmed.startsWith(">")) {
      flushParagraph();
      let quoteText = trimmed.replace(/^>\s?/, "");
      i += 1;
      while (i < lines.length && lines[i].trim().startsWith(">")) {
        quoteText += ` ${lines[i].trim().replace(/^>\s?/, "")}`;
        i += 1;
      }
      blocks.push(block("blockquote", quoteText));
      continue;
    }

    if (/^\d+\.\s/.test(trimmed)) {
      flushParagraph();
      blocks.push(
        block("normal", trimmed.replace(/^\d+\.\s+/, ""), {
          listItem: "number",
          level: 1,
        }),
      );
      i += 1;
      continue;
    }

    if (trimmed.startsWith("- ")) {
      flushParagraph();
      blocks.push(
        block("normal", trimmed.slice(2), { listItem: "bullet", level: 1 }),
      );
      i += 1;
      continue;
    }

    paragraphBuffer.push(trimmed);
    i += 1;
  }

  flushParagraph();
  return blocks;
}

/** Extract article body from SMPL blog draft markdown. */
export function extractArticleMarkdown(fullText) {
  const articleStart = fullText.indexOf("\n# Article\n");
  if (articleStart === -1) {
    throw new Error("Missing # Article section");
  }
  let body = fullText.slice(articleStart + "\n# Article\n".length);
  const stopMarkers = [
    "\n---\n\n# Remaining deliverables",
    "\n---\n\n*SMPL.ai",
  ];
  for (const marker of stopMarkers) {
    const idx = body.indexOf(marker);
    if (idx !== -1) body = body.slice(0, idx);
  }
  const footerMatch = body.match(
    /\n---\n\n(\*SMPL\.ai[\s\S]*?\[[^\]]+\]\([^)]+\)\.\*)\s*$/,
  );
  if (footerMatch) {
    body = body.slice(0, footerMatch.index);
    body += `\n\n${footerMatch[1]}`;
  }
  return body.trim();
}

/** Parse deliverables block from SMPL blog draft markdown. */
export function parseDeliverables(fullText) {
  const deliverables = {};
  const slugMatch = fullText.match(/\*\*1\. URL slug:\*\* `([^`]+)`/);
  const seoTitleMatch = fullText.match(
    /\*\*2\. SEO title[^:]*:\*\* (.+)/,
  );
  const metaMatch = fullText.match(/\*\*3\. Meta description:\*\* (.+)/);
  const h1Match = fullText.match(/\*\*4\. H1:\*\* (.+)/);
  if (slugMatch) deliverables.slug = slugMatch[1];
  if (seoTitleMatch) deliverables.seoTitle = seoTitleMatch[1].trim();
  if (metaMatch) deliverables.excerpt = metaMatch[1].trim();
  if (h1Match) deliverables.title = h1Match[1].trim();
  return deliverables;
}

/** Apply ordered [from, to] string replacements before markdown conversion. */
export function applyLinkInjections(text, injections) {
  let out = text;
  for (const [from, to] of injections) {
    if (out.includes(from)) out = out.replace(from, to);
  }
  return out;
}
