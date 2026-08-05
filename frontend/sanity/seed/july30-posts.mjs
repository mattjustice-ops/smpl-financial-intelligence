/**
 * Blog posts: financial data translation + FISoD.
 * Published via scripts/publish-july30-posts.mjs
 *
 * Content as written from Downloads drafts. Schema-only adaptations:
 * - Converted markdown text-tables to bullet comparisons (no comparisonTable)
 * - Dropped internal glossary footer notes and HTML draft comments
 */

let keySeq = 0;
function key(prefix = "k") {
  keySeq += 1;
  return `${prefix}${keySeq}`;
}

/** Parse inline markdown: **strong**, *em*, `code`, [label](href) */
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

function p(text) {
  return block("normal", text);
}

function h2(text) {
  return block("h2", text);
}

function h3(text) {
  return block("h3", text);
}

function bullet(text) {
  return block("normal", text, { listItem: "bullet", level: 1 });
}

export const july30Posts = [
  {
    _id: "post-financial-data-translation",
    _type: "post",
    title: "Financial Data Needs Translation, Not Integration",
    slug: { _type: "slug", current: "financial-data-translation" },
    excerpt:
      "Integration moves data; translation creates meaning. Why connected systems still produce conflicting reports — and how finance turns operational data into one financial story.",
    publishedAt: "2026-07-30T17:00:00.000Z",
    author: { _type: "reference", _ref: "author-smpl-team" },
    categories: [{ _type: "reference", _ref: "category-trust-reporting" }],
    seoTitle: "Financial Data Needs Translation, Not Integration | SMPL.ai",
    seoDescription:
      "Integration moves data; translation creates meaning. Why connected systems still produce conflicting reports — and how finance turns operational data into one financial story.",
    body: [
      h2("You've integrated everything. Why are you still reconciling?"),
      p(
        "Nearly every finance organization has invested heavily in integrations, and for good reason. Salesforce connects to NetSuite. The billing platform connects to the ERP. Marketing platforms connect to the CRM. Product analytics flow into the data warehouse. On paper, the systems are wired together, and data moves between them automatically.",
      ),
      p("And yet finance teams still spend days every month reconciling numbers."),
      p(
        "If integration were the answer, that wouldn't be happening. A fully integrated stack would produce numbers that agree, and the monthly reconciliation marathon would have disappeared. It hasn't — at most companies it's gotten longer as more systems joined the stack. That's a clue worth following, because it means the problem finance is trying to solve is not the problem integration solves.",
      ),
      p(
        "The issue isn't that the systems aren't connected. It's that connecting them doesn't make them mean the same thing. And that gap — between data being *moved* and data being *understood* — is where the reconciliation work lives.",
      ),
      p(
        "Here's the reframe at the center of this article: **integration moves data. Translation creates meaning.** Finance doesn't need more of the first. It needs more of the second. This piece is about why that distinction matters, and why the finance teams that fix reporting won't necessarily buy more software — they'll build a common financial language.",
      ),

      h2("Integration moves data. Translation creates meaning."),
      p(
        "Start with what integration actually does. An integration is a pipe. It takes a record from one system and delivers it to another. That's genuinely valuable — without it, finance would be exporting CSVs and pasting them by hand. Integration solved the *movement* problem, and it solved it well.",
      ),
      p(
        'But movement isn\'t meaning. When a "Closed Won" opportunity flows from Salesforce into another system, the integration faithfully delivers the record. What it doesn\'t deliver is an answer to the question finance actually cares about: is this recognized revenue? Is it ARR? When does the cash arrive? The pipe carries the data; it doesn\'t carry the financial interpretation, because that interpretation was never in the source system to begin with.',
      ),
      p("This is the crux. Every business system speaks its own language:"),
      bullet("**Salesforce speaks opportunities.**"),
      bullet("**HubSpot speaks leads.**"),
      bullet("**Stripe speaks subscriptions and payments.**"),
      bullet("**NetSuite speaks accounting transactions.**"),
      bullet("**Workday speaks employees.**"),
      bullet("**Product platforms speak usage.**"),
      p(
        "Each language is correct and complete for its own purpose. But none of them is the language of financial decision-making. And finance carries the responsibility of translating each of these operational languages into one trusted financial language — the language of ARR, revenue, margin, cash, and retention that executives, boards, and investors actually use.",
      ),
      p(
        "Integration connects the languages. It doesn't translate between them. That's a different job, and it's the one that's been missing.",
      ),

      h2("Every business system was designed for a different job"),
      p(
        "It's worth being clear that none of this is a criticism of any system. Each operational tool is excellent — precisely because it was optimized for the department using it.",
      ),
      bullet(
        "**Sales** wants pipeline visibility, so the CRM is built around opportunities, stages, and forecasts.",
      ),
      bullet(
        "**Marketing** wants campaign attribution, so its platform is built around leads, sources, and touches.",
      ),
      bullet(
        "**Customer success** wants to manage renewals and health, so its tool is built around accounts and engagement signals.",
      ),
      bullet(
        "**Accounting** wants compliant, auditable records, so the ERP is built around journals and postings.",
      ),
      bullet(
        "**Product** wants to understand engagement, so its analytics are built around events and usage.",
      ),
      p(
        "Every one of these is well-designed for its purpose. That's exactly why they were adopted. But notice what none of them was built to answer — the questions that land on the CFO's desk:",
      ),
      bullet("Are we ahead of plan?"),
      bullet("Why did ARR change?"),
      bullet("What caused gross margin to decline?"),
      bullet("How much cash will we collect next quarter?"),
      bullet("Which customers are driving expansion?"),
      p(
        "Not one of these questions can be answered from inside a single operational system, because each requires combining several of them and translating their separate languages into a coherent financial answer. The CRM knows about the opportunity but not the recognition; the ERP knows the posting but not the pipeline; billing knows the invoice but not the churn signal.",
      ),
      p(
        "Finance sits at the intersection of all of them. It's the only function positioned to see across every system — and therefore the only one that can turn their separate records into one financial picture. That position is a responsibility, and it's the real work of the function.",
      ),

      h2("Why integration alone doesn't create better reporting"),
      p(
        "Here's the failure mode that trips up so many reporting initiatives. A company integrates its systems, expects the numbers to line up, and finds they still don't. The reason is that moving information between systems does not guarantee the information means the same thing in both places.",
      ),
      p(
        "Consider how much interpretation sits between an operational event and its financial meaning:",
      ),
      bullet(
        '**"Closed Won" in a CRM is not recognized revenue.** It\'s a sales milestone. Revenue recognition depends on delivery, terms, and accounting standards the CRM knows nothing about.',
      ),
      bullet(
        "**A subscription event is not automatically ARR.** Whether it counts, at what run-rate, and how a ramp or usage component is treated are all judgment calls the billing system doesn't make.",
      ),
      bullet(
        "**Customer activity is not automatically churn.** A drop in usage might signal churn, or a seasonal lull, or nothing. Turning activity into a churn number requires a definition.",
      ),
      bullet(
        "**A payment is not necessarily revenue.** Cash can arrive before revenue is earned (deferred) or after (receivables). Payment timing and revenue recognition are different clocks.",
      ),
      bullet(
        "**An invoice is not necessarily cash flow.** An issued invoice is a claim, not collected cash. The gap between them is billing terms and collections behavior.",
      ),
      p(
        'In every case, the raw event has to be *interpreted* before it becomes a financial figure. That interpretation is business context — the rules and definitions that turn "what happened operationally" into "what it means financially." An integration doesn\'t carry that context. It carries the event.',
      ),
      p(
        "Which leads to the insight that reframes the whole thing: every connection between systems is actually a translation, not simply a transfer of data. The moment you move a Salesforce opportunity toward a revenue number, you're translating — applying financial meaning the source never contained. Most reporting problems are really translation problems wearing an integration costume.",
      ),

      h2("Finance is the interpreter of the business"),
      p(
        "This is the heart of it, and it's worth stating carefully, because how you frame finance's role changes how you think about the whole problem.",
      ),
      p(
        "It would be easy to say finance's job is translation — moving between the languages the systems speak. But that undersells it. Translation is the mechanism. The role is larger: **finance is the interpreter of the business.** Operational systems record what happened. Finance turns those events into a consistent financial story that executives, boards, and investors can actually use to make decisions.",
      ),
      p(
        "That interpretation is happening constantly, whether or not anyone names it. Finance spends much of its time translating operational activity into financial understanding:",
      ),
      bullet(
        "**Sales activity into bookings** — turning opportunities into a committed number.",
      ),
      bullet(
        "**Contracts into revenue** — applying recognition rules to signed deals.",
      ),
      bullet(
        "**Billing into cash forecasts** — projecting collections from invoices and terms.",
      ),
      bullet(
        "**Customer events into ARR movements** — deciding what counts as new, expansion, contraction, or churn.",
      ),
      bullet(
        "**Operational metrics into executive KPIs** — converting activity into the measures leadership tracks.",
      ),
      bullet(
        "**Department activity into board reporting** — assembling the whole business into one coherent narrative.",
      ),
      p(
        'Every one of these is an act of interpretation, and every one requires consistent rules to be trustworthy. When the interpretation is consistent — when "ARR" means the same thing every time an opportunity becomes a revenue number — the reports tie out and the story holds together. When it\'s inconsistent, because it\'s done by hand differently each period or defined differently by different people, the numbers conflict and finance spends its month reconciling.',
      ),
      p(
        "So executive reporting doesn't actually depend on connected systems. It depends on consistent financial interpretation. Connection is necessary — you can't interpret data you can't reach — but it's the interpretation, applied consistently, that produces reporting a board can trust. (This is closely related to why [poor financial data holds back finance teams](/blog/poor-financial-data-limiting-finance): fragmented interpretation is what poor data quality really is.)",
      ),

      h2("Better translation creates better financial intelligence"),
      p(
        "When interpretation is consistent and governed rather than improvised each period, the effects compound across everything finance does:",
      ),
      bullet(
        "**Trusted executive reporting**, because every number was interpreted the same way and means what it says.",
      ),
      bullet(
        "**Faster month-end close**, because the translation isn't rebuilt from scratch each period.",
      ),
      bullet(
        "**Better forecasting**, because forecasts rest on consistently defined actuals.",
      ),
      bullet(
        "**More reliable board reporting**, because the figures tie to each other and to source.",
      ),
      bullet(
        "**More accurate scenario planning**, because every scenario branches from the same interpreted baseline.",
      ),
      bullet(
        "**Consistent KPI definitions**, because a metric means one thing across every report.",
      ),
      bullet(
        "**Cross-functional alignment**, because sales, finance, and the board are finally working from the same numbers.",
      ),
      bullet(
        "**Greater executive confidence**, because the story holds up when someone pushes on it.",
      ),
      p(
        "Notice that none of these come from a new dashboard. This is the trap many reporting initiatives fall into: the numbers conflict, so the company buys another reporting tool — a better visualization layer on top of the same inconsistent interpretation. The dashboard renders the inconsistency more attractively; it doesn't resolve it. The real opportunity isn't a better window onto the data. It's improving how financial information is interpreted as it moves between systems in the first place.",
      ),

      h2("Why AI depends on better translation"),
      p(
        "This is where the stakes rise sharply, because AI is entering finance fast, and AI is entirely dependent on consistent interpretation to be useful.",
      ),
      p(
        "AI cannot understand financial information if every system describes the business differently. Hand an AI system a stack where:",
      ),
      bullet("**ARR is defined differently** in the CRM and the billing platform,"),
      bullet('**"customer" means different things** across systems,'),
      bullet("**churn is calculated differently** by different teams,"),
      bullet("**booking assumptions vary**, and"),
      bullet("**revenue is classified inconsistently** —"),
      p(
        "and the AI has no way to reconcile the contradictions. It will produce fluent, confident commentary on whichever version it happened to receive, with no awareness that the underlying concepts don't agree. The output reads well and may be quietly wrong, which is harder to catch than an obvious error.",
      ),
      p(
        "The principle that keeps AI trustworthy is a boundary: AI should *consume* translated, validated, consistent financial information. It should not *determine* financial meaning on its own. Deciding what ARR means, which churn definition is correct, or how a contract converts to revenue — these are business judgments that belong to finance, encoded as consistent rules. AI's role is to explain and communicate the results of that interpretation, not to invent the interpretation itself. (We've drawn this line more fully in [what makes financial AI trustworthy](/blog/explainable-ai-in-finance) and in the governance principle behind [Financial Intelligence Segregation of Duties](/blog/financial-intelligence-segregation-of-duties).)",
      ),
      p(
        "In other words, better translation isn't just good hygiene for reporting — it's the precondition for AI producing anything worth trusting. Consistent interpretation first; AI on top.",
      ),

      h2("Integration vs. translation, side by side"),
      p(
        "The distinction between moving data and interpreting it shows up cleanly when you set the two next to each other:",
      ),
      bullet(
        "**Moves data / Preserves meaning** — Data Integration: Moves data between systems. Financial Data Translation: Preserves financial meaning.",
      ),
      bullet(
        "**Synchronizes / Standardizes** — Data Integration: Synchronizes records. Financial Data Translation: Standardizes business definitions.",
      ),
      bullet(
        "**Connects / Creates intelligence** — Data Integration: Connects applications. Financial Data Translation: Creates consistent financial intelligence.",
      ),
      bullet(
        "**Workflows / Executive reporting** — Data Integration: Enables workflows. Financial Data Translation: Enables executive reporting.",
      ),
      bullet(
        "**Shares information / Trusted decisions** — Data Integration: Shares information. Financial Data Translation: Creates trusted decisions.",
      ),
      p(
        "Integration is the left column, and it's necessary — you need it. But the value finance is actually chasing lives in the right column, and no amount of the left column produces it on its own.",
      ),

      h2("The future of finance is a common financial language"),
      p(
        "Step back, and the conclusion reframes what modern finance organizations are really struggling with.",
      ),
      p(
        "They are not struggling because they lack data. Data is abundant — every system generates it, and integration has made it accessible. They are struggling because every system speaks a different language, and turning those languages into one trusted financial story is done inconsistently, by hand, under deadline, every period.",
      ),
      p(
        "Which means the organizations that meaningfully improve their financial reporting won't necessarily be the ones that buy the most software. They'll be the ones that build a consistent financial language — a shared, governed way of interpreting operational events into financial meaning — so that every system can contribute to one trusted view of the business rather than its own conflicting version.",
      ),
      p("That's the shift worth internalizing:"),
      p(
        "**Great reporting doesn't begin with better dashboards. It begins with better translation.**",
      ),
      p(
        "**Because financial intelligence isn't created when systems connect. It's created when they all tell the same story.**",
      ),

      h2("FAQ"),
      p("**What is financial data translation?**"),
      p(
        "Financial data translation is the process of turning operational events — a closed deal, a subscription change, a payment — into consistent financial meaning, such as bookings, ARR, or recognized revenue. It's distinct from integration, which moves data between systems without interpreting what it means financially.",
      ),
      p("**Why isn't data integration enough for finance?**"),
      p(
        'Integration moves records between systems, but it doesn\'t make them mean the same thing. A "Closed Won" opportunity isn\'t recognized revenue; a payment isn\'t necessarily revenue. Turning those events into financial figures requires business context that an integration doesn\'t carry — which is why connected systems still produce conflicting reports.',
      ),
      p("**Why do connected systems still produce conflicting reports?**"),
      p(
        "Because each system defines business concepts differently, and connecting them doesn't reconcile those definitions. If ARR is counted at signature in the CRM and at activation in billing, integrating the two just delivers both conflicting versions. Consistency comes from standardized interpretation, not from the connection.",
      ),
      p("**How does finance translate operational data into financial reporting?**"),
      p(
        "By applying consistent definitions and rules: recognition rules that turn contracts into revenue, run-rate rules that turn subscriptions into ARR, and classification rules that turn customer events into churn or expansion. When these rules are governed and applied the same way every period, operational activity becomes trustworthy financial reporting.",
      ),
      p("**Why does AI require consistent financial translation?**"),
      p(
        "Because AI can't reconcile contradictory definitions on its own. If every system describes the business differently, AI will confidently explain whichever version it's given, unaware of the conflict. AI should consume already-translated, validated, consistent financial data — and explain it — rather than determine financial meaning itself.",
      ),

      h2("Where SMPL.ai fits"),
      p(
        "SMPL.ai is built to be that translation layer — a finance operating system that turns operational data into one consistent financial language.",
      ),
      p(
        "SMPL reads and reconciles data from your connected systems — billing, CRM, and the general ledger — and does not replace your systems of record or post transactions back into your ERP. It interprets operational events into standardized financial meaning: subscriptions into the ARR waterfall, contracts into recognized and deferred revenue, customer events into NRR and GRR movements, billing into cash. Financial calculations are deterministic and repeatable, so the same inputs always produce the same outputs, and validation and reconciliation occur before anything reaches executive reporting. Every reported number can be traced back to its originating source.",
      ),
      p(
        "Because the interpretation is consistent and governed, the AI-generated commentary is grounded in that validated financial data — it explains results rather than creating financial metrics or deciding what they mean. The translation happens in a governed engine; the AI describes the outcome. (Authentication today uses magic links.)",
      ),
      p(
        "If you'd like to see what consistent translation looks like on your own numbers, [book a demo](https://www.smpl-ai.com/book-demo) and we'll walk it on data that looks like yours.",
      ),
    ],
  },

  {
    _id: "post-financial-intelligence-segregation-of-duties",
    _type: "post",
    title: "AI: Never Both Accountant and Auditor",
    slug: {
      _type: "slug",
      current: "financial-intelligence-segregation-of-duties",
    },
    excerpt:
      "Financial Intelligence Segregation of Duties (FISoD): why AI should explain trusted financial results, not calculate and validate its own. A governance framework for finance AI.",
    publishedAt: "2026-07-30T17:30:00.000Z",
    author: { _type: "reference", _ref: "author-smpl-team" },
    categories: [{ _type: "reference", _ref: "category-ai-in-fpa" }],
    // Keep on-page H1 (title) as published; SEO/OG title leads with FISoD.
    seoTitle: "Financial Intelligence Segregation of Duties (FISoD) | SMPL.ai",
    seoDescription:
      "Financial Intelligence Segregation of Duties (FISoD) applies segregation of duties to finance AI: explain trusted results — don't calculate and validate your own.",
    body: [
      h2("Finance has always separated who does what"),
      p(
        "For as long as there have been finance functions, there has been segregation of duties. It's one of the oldest and most durable ideas in the discipline, and it exists for a simple reason: independent validation reduces risk.",
      ),
      p(
        "The examples are familiar to anyone who's worked in or around finance:",
      ),
      bullet(
        "The employee who sets up a new vendor cannot also approve the payment to that vendor.",
      ),
      bullet(
        "The person reconciling cash should not be the only individual recording the transactions.",
      ),
      bullet(
        "The analyst who prepares a figure is not the same person who signs off on it.",
      ),
      p(
        "None of this reflects distrust of any individual. It reflects a structural insight: when one person controls every step of a process, there's no independent check on that process, and errors — honest or otherwise — pass through unseen. Separating responsibilities creates natural friction, and that friction is where mistakes get caught. These principles have protected finance organizations for decades, through paper ledgers, mainframes, ERP systems, and the cloud.",
      ),
      p(
        "Now finance faces a genuinely new situation, and it's worth thinking through carefully rather than reflexively.",
      ),
      p(
        "AI is becoming capable of doing many steps of financial work at once. It can calculate metrics, forecast results, produce reports, and write the executive commentary that explains them. That's remarkable, and it's genuinely useful. But it raises a question the segregation-of-duties tradition prepares us to ask: **should AI be responsible for creating financial intelligence and validating it at the same time?**",
      ),
      p(
        "That question deserves a name and a framework. This article proposes one: **Financial Intelligence Segregation of Duties (FISoD)** — the principle that deterministic financial calculations and AI-generated interpretation should remain separate, ensuring AI explains trusted financial results rather than creating and validating its own conclusions.",
      ),
      p(
        "The rest of this piece makes the case for why FISoD belongs in every finance organization's approach to AI — not as a brake on adoption, but as the thing that makes confident adoption possible.",
      ),

      h2("Traditional segregation of duties protected financial transactions"),
      p(
        "To see why FISoD matters, it helps to be precise about what traditional segregation of duties actually does.",
      ),
      p(
        "In a well-controlled finance function, responsibilities are deliberately distributed across different people and functions:",
      ),
      bullet("**Transaction entry** — recording what happened."),
      bullet("**Payment approval** — authorizing money to move."),
      bullet(
        "**Account reconciliation** — confirming that records agree with reality.",
      ),
      bullet(
        "**Financial review** — a qualified person examining the results.",
      ),
      bullet(
        "**Internal audit** — independent verification that the controls themselves are working.",
      ),
      p(
        "Finance has never relied on one person to perform every one of these. It would be faster to — one person could enter, approve, reconcile, and review a transaction in a fraction of the time it takes to route it through several. But finance accepts that friction on purpose, because the speed of a single unchecked actor is not worth the risk of an unchecked process.",
      ),
      p(
        "The underlying logic is that independent validation is a feature, not overhead. Each handoff is an opportunity to catch what the previous step missed. Remove the handoffs and you remove the checks. This is so deeply embedded in financial practice that it's usually invisible — until something goes wrong in a process where it was absent.",
      ),
      p(
        "That logic doesn't change when the actor performing the steps is software instead of a person. If anything, it becomes more important, because software performs every step with the same confidence whether it's right or wrong.",
      ),

      h2("AI changes the control environment"),
      p(
        "Here's what's genuinely new. For most of finance's history, the tools finance used were narrow. A calculator computed. A spreadsheet held formulas. An ERP recorded transactions. None of them interpreted, explained, or recommended — those were human jobs, and the segregation of duties applied to the humans.",
      ),
      p(
        "AI collapses that separation, because a single AI system is becoming capable of:",
      ),
      bullet(
        "**Creating financial metrics** — deriving figures from raw data.",
      ),
      bullet(
        "**Calculating KPIs** — computing the numbers leadership watches.",
      ),
      bullet("**Forecasting revenue** — projecting forward."),
      bullet("**Producing board commentary** — writing the narrative."),
      bullet(
        "**Explaining financial performance** — interpreting what happened.",
      ),
      bullet(
        "**Recommending business decisions** — suggesting what to do next.",
      ),
      p(
        "Each of these is valuable. The concern isn't any one of them. It's the prospect of a single system doing all of them, end to end, with no independent step in between. Which surfaces the question at the heart of this framework: **if AI performs every step in this process, who validates the financial intelligence?**",
      ),
      p(
        'It\'s tempting to answer "the AI does — and its outputs are convincing." But that\'s precisely the trap segregation of duties was invented to avoid. A convincing output is not a validated one. AI produces fluent, confident, well-structured results whether or not those results are correct — and fluency, in finance, is not the same as accuracy. Confidence alone has never been an acceptable substitute for a financial control, and it shouldn\'t become one just because the confident party is a language model.',
      ),
      p(
        "None of this means AI is unsafe or shouldn't be adopted. It means AI should be adopted the way finance adopts anything powerful: with the controls that let you trust the result.",
      ),

      h2("AI should never be both the accountant and the auditor"),
      p(
        "This is the core of the framework, so it's worth stating as plainly as possible.",
      ),
      p(
        "Trustworthy financial intelligence separates responsibilities the same way trustworthy financial operations always have. Specifically, a single AI system should not simultaneously:",
      ),
      bullet("**Define** the business metrics,"),
      bullet("**Calculate** the financial results,"),
      bullet("**Validate** those calculations,"),
      bullet("**Generate** the executive commentary, and"),
      bullet("**Recommend** the business actions."),
      p(
        "When one system does all five, there is no independent verification anywhere in the chain. The entity that produced the number is also the entity vouching for it. That's not a workflow any controller would accept from a person, and it shouldn't be accepted from software either.",
      ),
      p(
        "There's an old principle in financial controls that captures this exactly: **you shouldn't write the check and sign the check.** The person who initiates a payment shouldn't also be the sole authority approving it, because the approval is meaningless if it's not independent. The separation is the whole point.",
      ),
      p(
        "Translate that directly into the AI context and the principle becomes clear:",
      ),
      p(
        "**AI shouldn't calculate the numbers, validate the numbers, and explain the numbers.**",
      ),
      p(
        'The moment AI does all three, the explanation loses its independence. If the AI computed a figure and then "validated" its own computation and then wrote the commentary explaining it, every layer is derived from the same source with no external check. A mistake introduced at the calculation step is confidently carried through validation and eloquently justified in the commentary. Nothing in the chain is positioned to catch it.',
      ),
      p(
        "FISoD draws the line where it belongs. The numbers should come from a deterministic, verifiable process — one that produces the same result every time and can be traced to source. AI's job is to *explain* those already-trusted numbers, not to be the source of them. The accountant role (producing the numbers) and the auditor role (independently confirming them) stay separate — and AI is neither. AI is the analyst who interprets numbers that have already been produced and verified by a process it doesn't control.",
      ),
      p(
        "That separation is what makes AI's contribution trustworthy. When AI explains a figure that was independently calculated and validated, its explanation carries weight, because the figure it's explaining wasn't its own invention.",
      ),

      h2("Deterministic calculations should come before AI"),
      p(
        "FISoD implies a specific order of operations, and the order matters as much as the separation.",
      ),
      p(
        "Trusted financial reporting begins with a chain that has nothing to do with AI:",
      ),
      bullet(
        "**Source systems** — the authoritative records of what happened.",
      ),
      bullet(
        "**Standardized financial definitions** — one agreed meaning per metric.",
      ),
      bullet(
        "**Validation** — confirming the data is complete and consistent.",
      ),
      bullet(
        "**Reconciliation** — proving the sources agree, or explaining why they don't.",
      ),
      bullet(
        "**Traceability** — every figure followable back to its origin.",
      ),
      bullet(
        "**Deterministic calculations** — the same inputs producing the same outputs, every time.",
      ),
      p(
        "Only after that foundation is in place should AI enter — and when it does, its role is well-defined:",
      ),
      bullet(
        "**Explain** the results the deterministic process produced.",
      ),
      bullet("**Summarize** trends across periods."),
      bullet("**Identify** anomalies worth a human's attention."),
      bullet("**Draft** executive commentary for finance to review."),
      bullet("**Answer** financial questions in plain language."),
      p(
        "Notice that every item on the AI list operates *on* the trusted output of the deterministic process. AI enhances financial intelligence; it does not originate it. The determinism comes first because determinism is what makes a number reproducible and defensible — and AI, which is probabilistic by nature, cannot provide that. A figure that might come out differently on a second run isn't a financial result; it's an estimate. Financial results have to be reproducible, which is exactly what deterministic calculation guarantees and generative AI does not.",
      ),
      p(
        "This is why the sequence is deterministic-first, AI-second, and never the reverse. (We've written more about that boundary in [what makes financial AI trustworthy](/blog/explainable-ai-in-finance), and about the foundation it depends on in [why poor financial data holds back finance teams](/blog/poor-financial-data-limiting-finance).)",
      ),

      h2("Traditional controls and their financial-intelligence equivalents"),
      p(
        "FISoD isn't a departure from finance's control tradition — it's an extension of it. Each classic control has a natural counterpart in the world of AI-assisted financial intelligence:",
      ),
      bullet(
        "**Transaction approval → Deterministic calculations** — Traditional: Transaction approval. Financial intelligence: Deterministic calculations.",
      ),
      bullet(
        "**Account reconciliation → Financial validation** — Traditional: Account reconciliation. Financial intelligence: Financial validation.",
      ),
      bullet(
        "**Internal audit → Traceable AI explanations** — Traditional: Internal audit. Financial intelligence: Traceable AI explanations.",
      ),
      bullet(
        "**Segregation of duties → FISoD** — Traditional: Segregation of duties. Financial intelligence: Financial Intelligence Segregation of Duties.",
      ),
      bullet(
        "**Financial review → Independent AI interpretation** — Traditional: Financial review. Financial intelligence: Independent AI interpretation.",
      ),
      p(
        "The right-hand column isn't a replacement for the left — it's the same philosophy applied one layer up, to the intelligence built on top of the transactions. Finance already knows how to think this way. FISoD just points that thinking at AI.",
      ),

      h2("Why this matters more as AI becomes more capable"),
      p(
        "A reasonable objection: isn't this a concern that fades as AI improves? If models get good enough, won't the need for these controls diminish?",
      ),
      p("The opposite is true, and it's worth being clear about why."),
      p(
        "Finance organizations are already asking AI to do more consequential work: build board decks, produce management reporting, forecast revenue, generate investor commentary, and explain business performance to the people who make the biggest decisions. As AI takes on more of this, the stakes of an unverified output rise, not fall. An AI-drafted footnote is low-risk. An AI-generated figure in an investor update is not.",
      ),
      p(
        "The pattern holds generally: the more capable and more trusted a system becomes, the more important it is that its outputs are independently verifiable. Capability increases reach, and reach increases the cost of an unchecked error. A more capable AI producing more influential outputs is precisely the situation that demands *more* control, applied more rigorously.",
      ),
      p(
        "This is why governance frameworks have to evolve alongside AI rather than lag behind it. The temptation is to relax controls as confidence in the technology grows. FISoD argues the reverse: as AI earns more responsibility, the discipline of keeping calculation and interpretation separate becomes more valuable, because there's more riding on the interpretation being grounded in something real.",
      ),

      h2("Financial intelligence requires independent validation"),
      p(
        "FISoD gives finance leaders a practical lens for evaluating any AI solution. The questions to ask a vendor aren't about how impressive the model is. They're about where the numbers come from and how they're verified:",
      ),
      bullet(
        "**Who defines the financial logic?** Is it configurable business rules you control, or logic the AI determines on its own?",
      ),
      bullet(
        "**How are calculations validated?** What confirms a figure before it reaches a report?",
      ),
      bullet(
        "**Can every metric be traced back to its source?** Is there a followable path from a headline number to the underlying transactions?",
      ),
      bullet(
        "**Are calculations deterministic or generated by AI?** Do the same inputs always produce the same outputs, or could the number vary between runs?",
      ),
      bullet(
        "**Can executive commentary be independently verified?** Does the narrative reference figures you can check, or is it self-contained?",
      ),
      bullet(
        "**How do we know the AI is explaining trusted numbers?** What guarantees the AI is interpreting validated results rather than producing its own?",
      ),
      p(
        "These questions matter far more than whether an AI system generates fluent, articulate responses. Fluency is easy and increasingly commoditized. Grounding — the guarantee that the fluent output is anchored to independently verified numbers — is the hard part, and it's the part that determines whether the intelligence can be trusted. A vendor who answers these concretely is offering financial intelligence. A vendor who answers with adjectives about their model is offering fluent output, which is not the same thing. (For a related evaluation lens, see [why every SaaS finance team needs a financial data governance strategy](/blog/financial-data-governance-saas-finance).)",
      ),

      h2("FISoD will become a core principle of modern finance"),
      p(
        "Finance has always evolved its internal controls as technology has changed. This is not the first time a new capability has required a new framework.",
      ),
      p(
        "Cloud computing moved financial data outside the corporate perimeter, and finance responded with new security and access controls. Digital payments made money move faster and more automatically, and finance responded with new approval workflows and fraud controls. In each case, the technology unlocked real value, and finance adopted it — but adopted it with controls suited to the new risk. The controls didn't slow the technology down. They made it safe to embrace fully.",
      ),
      p(
        "AI is the next step in that sequence. It brings genuine capability to financial intelligence, and finance should embrace it. But embracing it well means bringing a framework suited to its new risk — and that framework is Financial Intelligence Segregation of Duties. FISoD extends one of finance's oldest and most successful principles, independent validation, into the AI era. It's not a new idea so much as an old idea applied to a new actor.",
      ),
      p(
        "The finance organizations that adopt AI most successfully won't be the ones that hand it the most responsibility fastest. They'll be the ones that adopt it with the controls that let them trust what it produces — separating the deterministic calculation of the numbers from the AI interpretation of them, so that every AI-generated insight rests on a foundation that was independently verified.",
      ),
      p("Which leads to the principle worth remembering:"),
      p(
        "**AI should help finance make better decisions — but it should never become both the accountant and the auditor.**",
      ),

      h2("FAQ"),
      p("**What is Financial Intelligence Segregation of Duties?**"),
      p(
        "FISoD is the principle that deterministic financial calculations and AI-generated interpretation should remain separate. It ensures AI explains trusted financial results rather than creating and validating its own conclusions — extending finance's traditional segregation of duties into the age of AI.",
      ),
      p("**Why shouldn't AI calculate and validate financial metrics?**"),
      p(
        "Because that removes independent verification. If the same system produces a number, confirms it, and explains it, there's no external check to catch an error introduced along the way. Finance separates these responsibilities among people for exactly this reason, and the logic applies equally to AI.",
      ),
      p("**What are deterministic financial calculations?**"),
      p(
        "Deterministic calculations produce the same output from the same inputs, every time. This makes financial figures reproducible and defensible. Generative AI, by contrast, is probabilistic and may produce varying outputs — which is why calculation should be deterministic and AI should be reserved for interpretation.",
      ),
      p("**How can finance safely adopt AI?**"),
      p(
        "By keeping calculation and interpretation separate. Build a trusted foundation first — source systems, standardized definitions, validation, reconciliation, traceability, and deterministic calculations — then use AI to explain, summarize, and draft commentary on those already-trusted results, with a human reviewing and signing off.",
      ),
      p("**Why is explainability important in financial reporting?**"),
      p(
        "Because a number that can't be explained or traced can't be defended — to a board, an auditor, or an investor. Explainability ensures every reported figure has a clear derivation and a path back to source, which is what turns an AI-generated insight into something finance can stand behind.",
      ),

      h2("Where SMPL.ai fits"),
      p(
        "SMPL.ai is built around the FISoD principle — a finance operating system that keeps calculation and interpretation deliberately separate.",
      ),
      p(
        "SMPL reads and reconciles data from your connected systems — billing, CRM, and the general ledger — and does not replace your systems of record or post transactions back into your ERP. Financial calculations are deterministic and repeatable, so the same inputs always produce the same outputs, and validation and reconciliation occur before anything reaches executive reporting. Every reported number can be traced back to its originating source.",
      ),
      p(
        "Only after that trusted foundation is established does AI enter — and it stays in its lane. The AI explains validated financial results rather than creating financial metrics, and its commentary is grounded in that validated data. The numbers come from the deterministic engine; the AI interprets them. The accountant and the auditor stay separate, and AI is neither. (Authentication today uses magic links.)",
      ),
      p(
        "If you'd like to see how that separation works on your own numbers, [book a demo](https://www.smpl-ai.com/book-demo) and we'll walk it on data that looks like yours.",
      ),
    ],
  },
];
