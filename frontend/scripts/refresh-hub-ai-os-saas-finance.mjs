/**
 * Refresh hub post ai-operating-system-for-saas-finance from draft #1.
 * Patches existing Sanity document by slug — does NOT create a new slug/URL.
 *
 * Usage (from frontend/):
 *   node scripts/refresh-hub-ai-os-saas-finance.mjs
 */

import { createClient } from "@sanity/client";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");

const SLUG = "ai-operating-system-for-saas-finance";
const DOC_ID = "post-ai-operating-system-for-saas-finance";

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

function mdToBlocks(bodyMd) {
  const lines = bodyMd.split(/\r?\n/);
  const blocks = [];
  let i = 0;

  function flushParagraph(buf) {
    const text = buf.join(" ").replace(/\s+/g, " ").trim();
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

/**
 * Merged hub body: draft #1 strengths + live SaaS hub specificity.
 * Keeps slug/URL. No em dashes. Preserves Related reading + SMPL section.
 */
const BODY_MD = `
## Most SaaS companies do not have a software shortage

Walk into almost any growing SaaS company and look at what Finance already has.

An ERP records accounting activity and holds the general ledger. A CRM manages customers, opportunities, and pipeline. A billing platform runs the recurring revenue infrastructure. An HRIS holds people, compensation, and headcount. A planning tool supports budgeting and forecasting. A BI platform visualizes whatever it is pointed at. And now a growing collection of AI copilots answer questions about the information they are handed.

That is a substantial stack. Every one of those systems is good at the job it was built for.

And yet Finance still spends an enormous share of every reporting cycle extracting data, reconciling systems against each other, validating numbers, assembling packages, and explaining what changed. The tools multiplied. The manual work did not go away.

That is the puzzle worth understanding, because it explains why buying another tool has so often failed to fix it. (If you want the broader case for the category, we have written separately on [why finance needs an operating system](/blog/why-finance-needs-an-operating-system) and [the rise of the finance operating system](/blog/rise-of-the-finance-operating-system).)

## Finance became the integration layer

Here is what actually happened.

Each system holds a genuine piece of the financial story, and no system holds the whole thing. The ERP knows what was recognized but not what is in pipeline. The CRM knows bookings but not cash. Billing knows invoices but not headcount. Planning knows the model but only whatever was loaded into it.

To answer any real question about the business, someone has to bring those pieces together, resolve the places where they disagree, apply the company's own definitions, and produce a single coherent view.

That someone is Finance. Not as a strategic choice, but by default, because Finance is the only function accountable for the whole picture.

**So the integration layer in most growing companies is not software. It is people, working in spreadsheets, on a deadline, every period.**

An AI operating system for SaaS finance is what you get when you decide that layer should be a system instead.

## Definition

**An AI operating system for Finance is a governed financial intelligence layer that connects data across business systems, applies trusted financial definitions and methodologies, and uses automation and AI to produce reporting, forecasting, analysis, and decision support.**

Three parts of that definition carry the weight.

**Governed** means the data is validated, reconciled, and consistent before anything is calculated on top of it.

**Trusted financial definitions and methodologies** means the company's own rules for how metrics are computed, applied the same way every period.

**Automation and AI** come last, operating on that foundation rather than in place of it.

The ordering is the whole idea.

## Why SaaS finance is different

Every finance function spans multiple systems. In SaaS the dependency is unusually acute, for structural reasons.

The metrics that define a SaaS business cannot be produced from the general ledger alone. ARR and MRR depend on subscription and contract data. NRR and GRR require customer-level movement over time. Churn, expansion, contraction, and reactivation depend on how the CRM and billing system recorded events that accounting sees only in aggregate. Revenue forecasting needs pipeline. Cash forecasting needs billing timing and collections behavior. Headcount planning needs the HRIS. Board reporting needs all of it together.

So a SaaS finance team is not occasionally cross-system. It is cross-system on nearly every question it gets asked.

Take ARR. Is a signed-but-not-yet-live contract in ARR? Some teams say yes at signature, some at activation. How does a ramp deal that starts at $50K and steps to $200K count in month one? What about a usage-based component that varies month to month? Each answer is defensible. Each produces a different number.

The same ambiguity runs through the whole list:

- Expansion vs. contraction depends on where you draw the line between a genuine upsell and a contractual true-up.
- Churn can be logo churn, gross revenue churn, or net of expansion: three different numbers, all called "churn."
- Deferred revenue depends on billing terms and recognition treatment that live in different systems than the bookings that created it.
- Bookings vs. ARR vs. recognized revenue are three views of the same contract on three different clocks, and confusing them is the most common error in SaaS reporting.

These are not obscure edge cases. They are the headline numbers on every board slide. And because each is computed across multiple systems with no shared definition, the same metric can legitimately come out differently depending on who built the report and which system they started from.

Which means SaaS finance has a specific, acute need: these concepts require consistent business definitions across every report. ARR has to mean the same thing in the board deck, the investor update, the forecast, and the KPI dashboard, or the numbers will not tie, and the board will notice.

Add to that the reporting expectations that arrive early in a SaaS company's life, often from investors and lenders before the finance team has grown past a few people, and you have a function that must produce institutional-quality output across many systems with very little capacity. That is the sharpest version of the problem this category addresses.

## How this differs from the tools Finance already has

The category is easiest to understand by what it is not.

**It is not an ERP.** An ERP is the system of record for accounting. It holds the general ledger, maintains the audit trail, and is where transactions live. An operating system layer reads from it and reconciles against it. It does not replace it and does not post to it.

**It is not FP&A or planning software.** Planning tools are built for budgeting, modeling, and forecasting, and they generally assume that trustworthy data arrives as an input. The operating system layer is concerned with producing that trustworthy input in the first place, and it spans more than planning.

**It is not a BI platform.** BI visualizes data it is given. It is agnostic about whether the underlying numbers are reconciled or whether the definitions behind them are consistent. Charts do not confer trust.

**It is not a generic AI copilot.** A copilot answers questions about the context it receives. If the context is incomplete or unreconciled, the answer will be fluent and unreliable, which in Finance is worse than no answer.

**It is not a data warehouse.** A warehouse consolidates and stores data. That is necessary and it is not sufficient. A warehouse does not know what your company means by expansion ARR, does not enforce that definition, and does not produce a board package.

**It is not another spreadsheet.** The spreadsheet is where most of this actually happens today, and it is the thing the category is meant to replace as the governance layer. Spreadsheets are unmatched for flexibility and carry no governance, no enforced definitions, no reproducibility. (We have made the fuller case for [why spreadsheet reconciliation carries a hidden cost](/blog/hidden-cost-spreadsheet-reconciliation).)

A compact way to hold all of that:

*Planning tools plan. Ledgers record. Copilots answer questions about what they are given. A Finance operating system governs the financial context across systems first, then applies automation and AI.*

## The canonical financial intelligence model

The mechanism that makes this work has a name worth knowing: the canonical financial intelligence model.

Every operational system speaks its own language. The CRM speaks in opportunities, stages, and close dates. The billing system speaks in invoices, plans, and payment schedules. The general ledger speaks in accounts, journals, and postings. The HRIS speaks in employees, roles, and costs. Each vocabulary is correct for its own purpose, and none of them is the language of financial decision-making.

Finance, meanwhile, needs one consistent language: ARR, NRR, deferred revenue, margin, runway. Metrics that do not live natively in any single system because they are derived across all of them.

A canonical financial intelligence model is the translation layer. It is a single, authoritative representation of the business into which every source system is mapped and reconciled. Once data lands in that model, a customer is one customer, not four records with four IDs. ARR is one definition, not three interpretations. Every downstream number inherits from that shared foundation.

This is what makes consistency structural rather than heroic. When the board deck, the investor update, the forecast, and the KPI dashboard all compute from the same canonical model, they cannot disagree, because they are drawing from one definition rather than five separate exports. In short: a finance operating system gives every financial metric a common language, and the canonical model is that language, made concrete.

This is also the difference between connecting systems and governing them. Piping data into one place does not reconcile it. The canonical model is where the reconciliation and standardization actually happen. (It is the same principle behind [why a single source of truth for FP&A is a governed layer, not just a warehouse](/blog/single-source-of-truth-fpa).)

## Deterministic finance and explainable AI

Finance needs both kinds of computation, applied to different problems.

### Deterministic calculations

**Deterministic** means the same inputs always produce the same output. Your ARR calculation should be deterministic. So should revenue recognition, reconciliation logic, and anything that ties. These are the numbers people sign their names to, and they need to be reproducible in March exactly as they were in February.

Determinism is the bedrock of trust because it makes numbers reproducible and therefore defensible. When a director asks how a figure was computed, "the same way it is computed every period, and here is the trail" is an answer. "The model produced it" is not. Determinism also requires complete traceability: every figure has to walk back to the source transactions behind it, or reproducibility means nothing.

### Explainable AI

**Probabilistic** describes how AI models work. They interpret, weigh, and generate. That is exactly what you want for explaining why margin moved or spotting something unusual across forty accounts, and exactly what you do not want deciding what ARR is.

AI is genuinely useful for turning reconciled figures into language a board can read: explaining what moved, summarizing variances, surfacing trends. But AI must explain financial results, not generate financial numbers. A plausible-looking ARR figure with no grounding in your actual data is the fastest way to destroy trust.

The mistake is not using one or the other. It is using the wrong one for the job. An operating system approach keeps them in their proper places: deterministic logic establishes what happened, AI helps you understand why and what to look at next. (We have gone deeper on this boundary in [why AI should explain financial results, not create them](/blog/explainable-ai-in-finance) and named the control principle [Financial Intelligence Segregation of Duties (FISoD)](/blog/financial-intelligence-segregation-of-duties).)

## Why governance comes before intelligence

The instinct with any new AI capability is to point it at the data and see what it says. In Finance, that sequence is backwards, and the reason is specific rather than philosophical.

AI applied to unreconciled data does not fail loudly. It fails persuasively. It produces a well-written explanation of a number that was wrong before the model ever saw it. The output looks like analysis and carries the confidence of analysis without the reliability of it.

Governance first means the AI is reasoning about numbers that have already been validated, reconciled, and calculated according to the company's own rules. The intelligence layer is then genuinely useful, because it is interpreting something true.

This is why the category is not simply "AI for Finance." Adding AI is easy. Establishing the financial context it needs is the hard part, and it is the part that determines whether the AI is worth anything.

If the underlying data is fragmented, adding an AI tool adds a layer on top of the fragmentation. It does not resolve it. What you get is faster access to inconsistent information, and often several tools producing different confident answers to the same question. Finance then has a new reconciliation problem, this time between AI outputs rather than spreadsheets. The only durable fix is to solve the data and definitional problem underneath.

## What a finance operating system actually does

Because everything computes from one governed, canonical foundation, a finance operating system powers:

- Executive reporting: the coherent view of performance leadership acts on, consistent across every audience.
- Forecasting: built on trustworthy actuals rather than a hand-assembled starting point.
- Board packages: where every number ties to every other number and traces to source.
- Scenario planning: modeled from a reconciled base, so the assumptions rest on solid ground.
- KPI reporting: the same metric meaning the same thing in every dashboard, every period.
- AI-generated financial commentary: grounded in the engine's computed results, not independently produced.

These are not six separate tools bolted together. They are six outputs of one governed foundation. That is what "operating system" means here: not another application in the stack, but the layer underneath the applications that makes all of them trustworthy at once.

The point is where finance capacity gets spent. In most growing companies, the majority of the reporting cycle goes to assembling a trustworthy view of the business, and whatever time remains goes to analyzing it. An operating system approach inverts that ratio. It does not remove the need for finance judgment. It removes the need for finance professionals to act as the integration layer, which is the least valuable use of the skills they were hired for.

## Is an AI operating system right for your finance team?

Not every finance team needs this yet, and it is worth being honest about that. A few signals that suggest you do:

- Your headline metrics do not always tie across reports. If ARR in the board deck and ARR in the investor update sometimes differ, you have a definition problem a canonical model is built to fix.
- Answering a basic executive question takes days, not minutes. If "why did gross margin move?" kicks off a multi-system assembly project, the integration burden has outgrown manual methods.
- Your close depends on one or two people who hold the model in their heads. That is key-person risk with a resignation letter attached.
- You cannot trace a board number to source quickly. If following a figure back to the underlying contracts takes more than a minute, traceability is missing where it matters most.
- You are considering AI for finance. If you are evaluating AI tools, the prerequisite is governed data underneath them. Otherwise you are automating the production of confident mistakes.

If none of these resonate, if you are early enough that one person genuinely holds a consistent picture, you may not need this layer yet. The need tends to arrive with scale: more systems, more people producing numbers, more contract complexity, and a board that has started asking harder questions.

## How is an AI operating system for Finance different from FP&A software?

The clearest distinction is scope and starting point.

FP&A software is built primarily for planning: budgets, forecasts, models, and scenarios. It is generally designed on the assumption that reliable data will be loaded into it, and its value is in what you do with that data once it arrives.

An AI operating system for Finance starts a layer lower. Its first job is producing the reliable, governed, cross-system financial foundation in the first place, including the reconciliation and definitional work that usually happens manually before anything reaches a planning tool. From there it supports reporting, analysis, and decision support as well as planning.

They are not mutually exclusive, and this is not a claim that planning tools are deficient at what they do. It is a difference in where in the workflow each one operates.

## Does an AI operating system replace the ERP?

No.

The ERP is the system of record for accounting. It maintains the general ledger, holds the audit trail, and is where transactions are posted. That role should not move, and a company should be skeptical of anything suggesting otherwise.

An operating system layer sits above the ERP. It reads from it, reconciles it against other systems, and uses it as an authoritative source. It does not post transactions to the general ledger and it is not the book of record.

The same applies to the CRM, the billing platform, and the HRIS. Each remains the system of record for its domain. The operating system layer creates intelligence across them.

## Frequently asked questions

**What is an AI operating system for Finance?**
A governed financial intelligence layer that connects data across business systems, applies trusted financial definitions and methodologies, and uses automation and AI to produce reporting, forecasting, analysis, and decision support.

**How is it different from FP&A software?**
FP&A software is built mainly for planning and generally assumes trustworthy data as an input. An operating system layer starts lower, producing the governed cross-system financial foundation itself, and supports reporting and analysis in addition to planning.

**How does AI fit into financial reporting?**
AI works best after the numbers are established. Deterministic logic produces the figures; AI explains variances, surfaces anomalies, drafts narrative, and helps explore scenarios. AI should analyze financial truth rather than create it.

**Why does financial data governance matter for AI?**
Because AI applied to unreconciled data produces confident, well-written, unreliable answers. Governance, meaning validation, reconciliation, consistent definitions, and traceability, is what makes an AI-generated financial answer defensible.

**Does it replace ERP, CRM, billing, or HRIS systems?**
No. Those remain the systems of record for their domains. An operating system layer reads and reconciles across them and does not post to the general ledger.

**What types of companies benefit most?**
Companies whose finance function depends on data spread across several operating systems. Growing SaaS companies are a particularly strong fit, because SaaS metrics such as ARR, NRR, churn, and expansion inherently require CRM, billing, ERP, and HRIS data together.

## Related reading

Two practical follow-ons from this category: [why AI vs. automation is the wrong question for Finance](/blog/ai-vs-automation-finance) and [build vs. buy for Finance AI](/blog/build-vs-buy-finance-ai). On data trust: [connected systems vs. trusted financial data](/blog/connected-systems-financial-data) and [financial data validation](/blog/financial-data-validation).

## Where SMPL.ai fits

SMPL.ai is an example of this emerging category: an AI operating system built for growth-stage SaaS finance teams.

SMPL is browser-based and reads and reconciles data from your connected systems (billing, CRM, and the general ledger) into a canonical financial intelligence model that standardizes business definitions across the company. From that foundation it computes the SaaS metrics that matter (the ARR waterfall, NRR and GRR, deferred revenue, recognized revenue, cash, headcount as a driver) deterministically and with complete traceability, so any figure walks back to the transactions behind it.

SMPL reads from your systems but does not write back to your ERP or accounting systems; there is no autonomous accounting and no automatic journal entries. Your books stay yours. The close is governed through a Load → Validate → Lock → Freeze sequence so numbers are stable once finalized, and customer data is encrypted in transit and at rest. The AI explains the results the engine computed rather than generating financial numbers of its own.

The specifics matter less than the shape. A governed layer that connects your systems, gives every metric a common language, and keeps AI explaining rather than inventing: that is the category, and it is where SaaS finance is heading regardless of vendor.

If you would like to see it on your own numbers (reconciled to one model, traceable to source, fast enough to answer a director in the room), [book a demo](https://www.smpl-ai.com/book-demo) and we will walk it on data that looks like yours.
`.trim();

const NEW_EXCERPT =
  "An AI operating system for SaaS finance is a governed financial intelligence layer that connects ERP, CRM, and billing data, applies trusted definitions, and uses automation and AI for reporting and analysis.";

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
  const existing = await client.fetch(
    `*[_type == "post" && slug.current == $slug][0]{
      _id, title, "slug": slug.current, excerpt, seoTitle, seoDescription, publishedAt
    }`,
    { slug: SLUG },
  );

  if (!existing) {
    console.error(`Hub not found for slug ${SLUG}`);
    process.exit(1);
  }
  if (existing._id !== DOC_ID && existing._id !== `drafts.${DOC_ID}`) {
    console.warn(`Unexpected _id ${existing._id}; patching by fetched id.`);
  }
  if (existing.slug !== SLUG) {
    console.error("Slug mismatch — aborting to avoid URL change.");
    process.exit(1);
  }

  keySeq = 0;
  const body = mdToBlocks(BODY_MD);
  const joined = body
    .map((b) => {
      const text = b.children?.map((c) => c.text).join("") || "";
      const hrefs = (b.markDefs || []).map((d) => d.href || "").join(" ");
      return `${text} ${hrefs}`;
    })
    .join("\n");

  // Safety checks
  const required = [
    "So the integration layer in most growing companies is not software. It is people, working in spreadsheets, on a deadline, every period.",
    "An AI operating system for Finance is a governed financial intelligence layer that connects data across business systems, applies trusted financial definitions and methodologies, and uses automation and AI to produce reporting, forecasting, analysis, and decision support.",
    "It is not an ERP.",
    "It is not FP&A or planning software.",
    "It is not a BI platform.",
    "It is not a generic AI copilot.",
    "It is not a data warehouse.",
    "/blog/ai-vs-automation-finance",
    "/blog/build-vs-buy-finance-ai",
    "/blog/connected-systems-financial-data",
    "/blog/financial-data-validation",
    "Why SaaS finance is different",
    "Does an AI operating system replace the ERP?",
    "How is an AI operating system for Finance different from FP&A software?",
  ];
  for (const needle of required) {
    if (!joined.includes(needle)) {
      throw new Error(`Missing required content: ${needle.slice(0, 80)}`);
    }
  }
  if (/Internal glossary|ai-operating-system-for-finance(?!-saas)/i.test(joined)) {
    throw new Error("Cruft or wrong slug leaked into body");
  }
  // Forbid em dashes in body text (draft style)
  if (joined.includes("\u2014") || joined.includes("—")) {
    const idx = joined.indexOf("—");
    throw new Error(
      `Em dash found near: ${joined.slice(Math.max(0, idx - 40), idx + 40)}`,
    );
  }

  const patchId = existing._id.startsWith("drafts.")
    ? existing._id.replace(/^drafts\./, "")
    : existing._id;

  // Patch only content fields; never touch slug
  await client
    .patch(patchId)
    .set({
      body,
      excerpt: NEW_EXCERPT,
      seoDescription: NEW_EXCERPT,
      // Keep title + seoTitle (SaaS-specific SEO)
    })
    .commit();

  // Clean draft if Studio left one
  const draftId = `drafts.${patchId}`;
  const draftExists = await client.fetch(`defined(*[_id == $id][0]._id)`, {
    id: draftId,
  });
  if (draftExists) {
    await client.delete(draftId);
    console.log(`Deleted draft ${draftId}`);
  }

  const confirm = await client.fetch(
    `*[_type == "post" && slug.current == $slug][0]{
      _id, title, "slug": slug.current, excerpt, seoTitle, seoDescription,
      "bodyCount": count(body),
      "hasIntegrationLine": body[].children[].text match "*integration layer in most growing companies is not software*",
      "hasDefinition": body[].children[].text match "*governed financial intelligence layer that connects data across business systems*",
      "hasRelatedAiVs": body[].markDefs[].href match "*ai-vs-automation-finance*",
      "hasRelatedBuild": body[].markDefs[].href match "*build-vs-buy-finance-ai*",
      "hasRelatedConnected": body[].markDefs[].href match "*connected-systems-financial-data*",
      "hasRelatedValidation": body[].markDefs[].href match "*financial-data-validation*",
      "h2s": body[style == "h2"].children[].text
    }`,
    { slug: SLUG },
  );

  console.log(`Patched ${patchId} → ${projectId}/${dataset}`);
  console.log(`Live URL: https://www.smpl-ai.com/blog/${SLUG}`);
  console.log("Confirmed:", JSON.stringify(confirm, null, 2));

  if (confirm.slug !== SLUG) {
    throw new Error("CRITICAL: slug changed");
  }
  const allSlugs = await client.fetch(
    `count(*[_type == "post" && slug.current == "ai-operating-system-for-finance"])`,
  );
  if (allSlugs > 0) {
    console.warn(
      "Note: a separate post with draft #1 slug may already exist; this script did not create one.",
    );
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
