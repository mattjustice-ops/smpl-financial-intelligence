/**
 * Starter content for Sanity seed (3 cornerstone posts + ~20 glossary terms).
 * Imported by scripts/seed-sanity.mjs — edit here, then re-run seed.
 */

let keySeq = 0;
function key(prefix = "k") {
  keySeq += 1;
  return `${prefix}${keySeq}`;
}

function blocks(...paragraphs) {
  return paragraphs.map((text) => ({
    _type: "block",
    _key: key("b"),
    style: "normal",
    markDefs: [],
    children: [{ _type: "span", _key: key("s"), text, marks: [] }],
  }));
}

function h2(text) {
  return {
    _type: "block",
    _key: key("h"),
    style: "h2",
    markDefs: [],
    children: [{ _type: "span", _key: key("s"), text, marks: [] }],
  };
}

export const author = {
  _id: "author-smpl-team",
  _type: "author",
  name: "SMPL.ai Team",
  role: "Product & FP&A",
};

export const categories = [
  {
    _id: "category-board-reporting",
    _type: "category",
    title: "Board reporting",
    slug: { _type: "slug", current: "board-reporting" },
  },
  {
    _id: "category-close",
    _type: "category",
    title: "Close",
    slug: { _type: "slug", current: "close" },
  },
  {
    _id: "category-ai-commentary",
    _type: "category",
    title: "AI commentary",
    slug: { _type: "slug", current: "ai-commentary" },
  },
];

export const posts = [
  {
    _id: "post-board-numbers-need-evidence",
    _type: "post",
    title: "Why board numbers need evidence, not another dashboard",
    slug: { _type: "slug", current: "board-numbers-need-evidence" },
    excerpt:
      "Boards do not need more charts. They need every ARR, cash, and P&L figure tied to a source and a close decision.",
    publishedAt: "2026-07-01T12:00:00.000Z",
    author: { _type: "reference", _ref: "author-smpl-team" },
    categories: [{ _type: "reference", _ref: "category-board-reporting" }],
    seoTitle: "Board Numbers Need Evidence, Not Another Dashboard | SMPL.ai",
    seoDescription:
      "Why SaaS board packages fail when dashboards replace governed close evidence — and how to fix the trust gap.",
    body: [
      ...blocks(
        "Most SaaS board decks fail the same way: the story looks polished, but nobody can answer “where did this number come from?” in under a minute. Another dashboard does not fix that. Evidence does.",
        "Evidence means the ARR line ties to the subscription ledger, the cash bridge ties to the GL, and the variance narrative cites the same locked period the CFO signed. Without that chain, the board is reading a marketing artifact — not a financial operating system.",
      ),
      h2("Dashboards optimize for browsing"),
      ...blocks(
        "Dashboards are great for exploration. Boards need decision artifacts: a freeze pack, an MD&A draft that cites locked metrics, and a clear trail from source systems through validation.",
        "If your close still lives in a week of spreadsheet archaeology, adding a BI tile only speeds up the wrong loop.",
      ),
      h2("What “board-ready” actually means"),
      ...blocks(
        "Board-ready is not a visual style. It is a governance state: Load → Validate → Lock → Freeze, with commentary that finance will sign because the numbers are already certified.",
        "Want to see that workflow on your data? Book a demo — we walk the evidence trail, not a slide template.",
      ),
    ],
  },
  {
    _id: "post-saas-close-load-validate-lock-freeze",
    _type: "post",
    title: "SaaS close: Load → Validate → Lock → Freeze",
    slug: { _type: "slug", current: "saas-close-load-validate-lock-freeze" },
    excerpt:
      "A practical close operating model for SaaS finance: ingest sources, validate tie-outs, lock the period, then freeze the board pack.",
    publishedAt: "2026-07-08T12:00:00.000Z",
    author: { _type: "reference", _ref: "author-smpl-team" },
    categories: [{ _type: "reference", _ref: "category-close" }],
    seoTitle: "SaaS Close: Load → Validate → Lock → Freeze | SMPL.ai",
    seoDescription:
      "How SaaS FP&A teams run a governed month-end close from source load through freeze pack — without another spreadsheet scramble.",
    body: [
      ...blocks(
        "Month-end for SaaS finance is not “export everything and hope.” It is a sequence of states. Skip a state and the board package inherits silent errors.",
      ),
      h2("Load"),
      ...blocks(
        "Pull subscriptions, invoices, GL balances, payroll, and pipeline into one governed model. Partial loads create false confidence — treat completeness as a gate, not a nice-to-have.",
      ),
      h2("Validate"),
      ...blocks(
        "Run tie-outs: ARR vs billing, deferred vs cash, headcount vs OpEx, waterfall components that reconcile to ending ARR. Failures stay visible until resolved.",
      ),
      h2("Lock"),
      ...blocks(
        "Lock the reporting period so metrics stop drifting while commentary is written. Lock is a decision, not a folder rename.",
      ),
      h2("Freeze"),
      ...blocks(
        "Freeze the board package and MD&A against the locked numbers. After freeze, changes require an explicit reopen — not a quiet overwrite.",
        "If your team still rediscovers this sequence every month, book a walkthrough of Load → Validate → Lock → Freeze on SMPL.ai.",
      ),
    ],
  },
  {
    _id: "post-ai-commentary-finance-will-sign",
    _type: "post",
    title: "AI commentary that finance will actually sign",
    slug: { _type: "slug", current: "ai-commentary-finance-will-sign" },
    excerpt:
      "Finance will not sign chatbot prose. They will sign commentary that cites locked metrics, variance drivers, and evidence.",
    publishedAt: "2026-07-15T12:00:00.000Z",
    author: { _type: "reference", _ref: "author-smpl-team" },
    categories: [{ _type: "reference", _ref: "category-ai-commentary" }],
    seoTitle: "AI Commentary That Finance Will Actually Sign | SMPL.ai",
    seoDescription:
      "How to use AI for MD&A and board narrative without inventing numbers — cite locked close metrics and keep humans in the sign-off loop.",
    body: [
      ...blocks(
        "Generic AI writing fails finance for one reason: it invents fluency where there should be citations. CFOs sign numbers and the story about those numbers — not plausible paragraphs.",
      ),
      h2("Start from locked metrics"),
      ...blocks(
        "Commentary should only draft after Validate + Lock. The model’s job is to explain what already happened in the governed dataset: NRR movement, waterfall bridges, cash burn, hiring pace.",
      ),
      h2("Keep humans as the signatory"),
      ...blocks(
        "AI drafts. Controllers edit. CFOs certify. That chain is the product. “Certified accuracy” claims without a close process are marketing — avoid them.",
        "See AI commentary grounded in your freeze pack — request a quote or book a demo when you are ready to replace spreadsheet narrative with signed evidence.",
      ),
    ],
  },
];

export const glossaryTerms = [
  {
    _id: "glossary-arr",
    term: "ARR",
    slug: "arr",
    shortDefinition:
      "Annual Recurring Revenue — normalized annual value of active subscription contracts.",
    body: blocks(
      "ARR annualizes recurring subscription revenue so growth and retention can be compared across months. Definitions vary (include usage? prepaid? multi-year discounts?) — document yours and keep it stable through close.",
    ),
  },
  {
    _id: "glossary-mrr",
    term: "MRR",
    slug: "mrr",
    shortDefinition: "Monthly Recurring Revenue — the monthly view of subscription recurring value.",
    body: blocks(
      "MRR is typically ARR / 12 under a consistent definition. Use MRR for month-over-month operating reviews and ARR for board-level annual framing.",
    ),
  },
  {
    _id: "glossary-nrr",
    term: "NRR",
    slug: "nrr",
    shortDefinition:
      "Net Revenue Retention — ending ARR from a starting cohort including expansion, contraction, and churn.",
    body: blocks(
      "NRR answers whether the installed base grows after expansion and churn. Pair it with GRR to separate expansion from retention quality.",
    ),
  },
  {
    _id: "glossary-grr",
    term: "GRR",
    slug: "grr",
    shortDefinition:
      "Gross Revenue Retention — retention of starting ARR before expansion credit.",
    body: blocks(
      "GRR excludes expansion so you can see contraction and churn clearly. Healthy SaaS businesses track both GRR and NRR every close.",
    ),
  },
  {
    _id: "glossary-deferred-revenue",
    term: "Deferred revenue",
    slug: "deferred-revenue",
    shortDefinition:
      "Liability for cash collected (or billed) before revenue is recognized under GAAP.",
    body: blocks(
      "Deferred revenue bridges billing and recognition. SaaS close must reconcile deferred balances to the subscription schedule and the GL.",
    ),
  },
  {
    _id: "glossary-waterfall",
    term: "Waterfall",
    slug: "waterfall",
    shortDefinition:
      "Bridge from beginning ARR to ending ARR via new, expansion, contraction, churn, and other movements.",
    body: blocks(
      "ARR waterfalls make growth composition visible. Every component should reconcile to the ending ARR total used in the board package.",
    ),
  },
  {
    _id: "glossary-close",
    term: "Close",
    slug: "close",
    shortDefinition:
      "The process of finalizing a reporting period’s financial and operating metrics for reporting.",
    body: blocks(
      "In SaaS FP&A, close covers more than GL close — ARR, pipeline, cash, and workforce metrics must land in a consistent period state before commentary.",
    ),
  },
  {
    _id: "glossary-mda",
    term: "MD&A",
    slug: "mda",
    shortDefinition:
      "Management’s Discussion & Analysis — narrative explaining results, drivers, and outlook.",
    body: blocks(
      "MD&A should cite locked metrics and known variances. AI can draft structure; finance owns the signed narrative.",
    ),
  },
  {
    _id: "glossary-freeze-pack",
    term: "Freeze pack",
    slug: "freeze-pack",
    shortDefinition:
      "The board/reporting package locked against a certified close period so numbers stop drifting.",
    body: blocks(
      "After freeze, changes require reopen. Freeze packs prevent silent edits between draft decks and the meeting the board actually sees.",
    ),
  },
  {
    _id: "glossary-combined-scenario",
    term: "Combined scenario",
    slug: "combined-scenario",
    shortDefinition:
      "A forecast view that blends actuals to date with forward assumptions into one continuous outlook.",
    body: blocks(
      "Combined scenarios help boards see year-to-date actuals plus remaining plan without switching workbooks. Document which levers drive the forward slice.",
    ),
  },
  {
    _id: "glossary-bookings",
    term: "Bookings",
    slug: "bookings",
    shortDefinition:
      "Contracted value signed in a period — often ACV or TCV depending on company definition.",
    body: blocks(
      "Bookings are not the same as ARR recognized. Align sales ops and finance on ACV vs ARR impact before board reporting.",
    ),
  },
  {
    _id: "glossary-pipeline",
    term: "Pipeline",
    slug: "pipeline",
    shortDefinition:
      "Open opportunities weighted or unweighted toward future bookings and ARR.",
    body: blocks(
      "Pipeline informs outlook but should not silently rewrite locked ARR. Keep pipeline attribution separate from certified close metrics.",
    ),
  },
  {
    _id: "glossary-churn",
    term: "Churn",
    slug: "churn",
    shortDefinition:
      "Lost recurring revenue (logo or dollar) from customers ending or reducing contracts.",
    body: blocks(
      "Distinguish logo churn from dollar churn, and gross churn from net. Waterfalls should show churn as an explicit bridge component.",
    ),
  },
  {
    _id: "glossary-expansion",
    term: "Expansion",
    slug: "expansion",
    shortDefinition:
      "Increase in recurring revenue from existing customers (upsell, seats, usage uplift under policy).",
    body: blocks(
      "Expansion drives NRR above 100%. Define whether usage overages count as recurring before they enter ARR.",
    ),
  },
  {
    _id: "glossary-contraction",
    term: "Contraction",
    slug: "contraction",
    shortDefinition:
      "Decrease in recurring revenue from existing customers who remain active at a lower level.",
    body: blocks(
      "Contraction is not full churn. Tracking it separately improves GRR diagnosis and renewal playbooks.",
    ),
  },
  {
    _id: "glossary-cac",
    term: "CAC",
    slug: "cac",
    shortDefinition: "Customer Acquisition Cost — sales and marketing spend to acquire a customer.",
    body: blocks(
      "CAC definitions differ (fully loaded vs paid media only). Publish the formula next to payback and LTV metrics in board materials.",
    ),
  },
  {
    _id: "glossary-ltv",
    term: "LTV",
    slug: "ltv",
    shortDefinition: "Lifetime Value — expected gross profit from a customer relationship.",
    body: blocks(
      "LTV depends on retention, expansion, and margin assumptions. Do not present LTV:CAC without stating those inputs.",
    ),
  },
  {
    _id: "glossary-burn-multiple",
    term: "Burn multiple",
    slug: "burn-multiple",
    shortDefinition:
      "Net burn divided by net new ARR — efficiency of growth spend in a period.",
    body: blocks(
      "Burn multiple is sensitive to ARR definition and one-time cash items. Pair it with runway and gross margin in board packs.",
    ),
  },
  {
    _id: "glossary-runway",
    term: "Runway",
    slug: "runway",
    shortDefinition: "Months of cash remaining at the current net burn rate.",
    body: blocks(
      "Runway should use a clear burn definition (operating vs total cash). Scenario runway belongs next to Combined scenario outlooks.",
    ),
  },
  {
    _id: "glossary-gaap-revenue",
    term: "GAAP revenue",
    slug: "gaap-revenue",
    shortDefinition:
      "Revenue recognized under ASC 606 / company accounting policy — distinct from ARR.",
    body: blocks(
      "Boards often see both ARR (operating) and GAAP revenue (accounting). Never interchange them without a bridge explanation.",
    ),
  },
];

// Attach slug objects for glossary seed
for (const term of glossaryTerms) {
  term._type = "glossaryTerm";
  term.slug = { _type: "slug", current: term.slug };
}
