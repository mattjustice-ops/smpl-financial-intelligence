/**
 * Blog posts: no standard ARR calculation + GRR vs NRR (light merge).
 * Published via scripts/publish-aug4-posts.mjs
 *
 * Publish order: no-standard-arr-calculation first, then grr-vs-nrr
 * (so cross-links resolve). Schema adaptations match prior batches:
 * - Markdown text-tables → bullet comparisons
 * - Dropped HTML draft comments / internal-only footers
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

function numbered(text) {
  return block("normal", text, { listItem: "number", level: 1 });
}

export const aug4Posts = [
  {
    _id: "post-no-standard-arr-calculation",
    _type: "post",
    title: "There's No Standard ARR Calculation",
    slug: { _type: "slug", current: "no-standard-arr-calculation" },
    excerpt:
      "There's no universal ARR calculation — and that's fine. Why consistency beats standardization, and how to build an ARR methodology boards and investors actually trust.",
    publishedAt: "2026-08-04T16:00:00.000Z",
    author: { _type: "reference", _ref: "author-smpl-team" },
    categories: [{ _type: "reference", _ref: "category-arr-revenue" }],
    seoTitle: "There's No Standard ARR Calculation | SMPL.ai",
    seoDescription:
      "There's no universal ARR calculation — and that's fine. Why consistency beats standardization, and how to build an ARR methodology boards and investors actually trust.",
    body: [
      h2("The most important SaaS number nobody defines the same way"),
      p(
        "Annual Recurring Revenue is arguably the single most scrutinized number in SaaS. It's the headline on the board slide, the metric in the investor update, the figure a lender underwrites against, the number private equity and venture capital anchor their valuations to. Executives run the business on it. Everyone treats it as bedrock.",
      ),
      p(
        "Which makes one fact surprisingly under-discussed: there is no universally accepted way to calculate ARR.",
      ),
      p(
        "This trips people up, because ARR *feels* standardized. It's quoted so confidently, in so many rooms, that it seems like there must be a formula everyone agrees on. There isn't. Unlike GAAP revenue — which is governed by accounting standards, audited, and defined by rules you don't get to choose — ARR is an operational metric. Finance organizations developed it themselves to describe recurring business performance, and no standards body governs how it's computed.",
      ),
      p(
        "That's not a gap to be embarrassed about. It's a feature of what ARR is. But it has a practical consequence most finance leaders eventually run into: two companies can report ARR honestly and correctly and still be computing it in materially different ways — and so can two *people* inside the same company, if the methodology was never pinned down.",
      ),
      p(
        'This article is about what to do with that reality. Not how to find the "right" ARR formula — there isn\'t one — but how to build an ARR methodology that\'s consistent, documented, and trusted, which turns out to matter far more than matching anyone else\'s.',
      ),

      h2("Why ARR is different at every company"),
      p(
        "Start with why the variation exists, because once you see it, the absence of a standard formula stops being surprising and starts being obvious.",
      ),
      p(
        'Every SaaS company has its own products, pricing models, contract structures, billing mechanics, and reporting objectives. Consider the range of business models that all call their recurring revenue "ARR":',
      ),
      bullet(
        "**Pure subscription businesses**, with clean annual or monthly plans.",
      ),
      bullet(
        "**Usage-based pricing**, where revenue scales with consumption and varies month to month.",
      ),
      bullet(
        "**Hybrid pricing**, combining a subscription floor with usage on top.",
      ),
      bullet("**Multi-year agreements**, sometimes with escalators built in."),
      bullet(
        "**Minimum commitments**, where a customer commits to a floor but may spend more.",
      ),
      bullet("**Consumption pricing**, billed purely on what's used."),
      bullet(
        "**Enterprise contracts**, custom-negotiated and often complex.",
      ),
      bullet(
        "**Freemium conversions**, where free users become paying ones over time.",
      ),
      p(
        'A metric that has to describe "recurring revenue" across all of these cannot have one formula. Is variable usage revenue "recurring" if it recurs but fluctuates? Does a minimum commitment count at the floor or at expected spend? How do you annualize a consumption contract with no fixed subscription? Each business model raises different questions, and the honest answer depends on the economics of that specific business.',
      ),
      p(
        "So finance teams define ARR differently. That's expected. It is not a mistake, and it's not sloppiness. It's the natural result of a single metric being asked to describe genuinely different businesses. The mistake isn't defining ARR to fit your business — it's failing to define it deliberately at all.",
      ),

      h2("The questions every finance team must answer"),
      p(
        "The variation isn't abstract. It comes down to a specific set of decisions every SaaS finance team has to make, explicitly or by default. Each of these is a real fork in the road:",
      ),
      bullet(
        "**Should usage revenue be included in ARR?** If it recurs but varies, is it recurring?",
      ),
      bullet(
        "**Should implementation or onboarding services count?** They're often one-time, but sometimes bundled.",
      ),
      bullet(
        "**Should professional services count?** Usually excluded as non-recurring — but not always, in some models.",
      ),
      bullet(
        "**Should discounts reduce ARR?** Do you report gross or net of negotiated discounts?",
      ),
      bullet(
        "**How should multi-year contracts be annualized?** Even split, or reflecting escalators and ramps?",
      ),
      bullet(
        "**What happens when a customer pauses a subscription?** Out of ARR entirely, or held?",
      ),
      bullet(
        "**How are upgrades recognized?** Immediately, or at the next billing boundary?",
      ),
      bullet(
        "**When does booked ARR become active ARR?** At signature, at activation, at first invoice?",
      ),
      bullet(
        "**How are contract amendments handled?** Mid-term changes can move the number several ways.",
      ),
      bullet(
        "**How should early renewals be treated?** Do they reset timing, or not?",
      ),
      bullet(
        "**Should month-to-month customers be annualized?** They generate recurring revenue but carry no annual commitment.",
      ),
      p(
        "None of these has a universally correct answer. Each is a business decision — a judgment about how best to represent *your* recurring economics. A usage-heavy business will answer the usage question differently than a pure-subscription one, and both can be right. What matters is that the question gets answered deliberately, written down, and applied the same way every time.",
      ),

      h2("Consistency is more important than standardization"),
      p(
        "Here's the reframe at the heart of this, and it's worth sitting with because it runs against a common instinct.",
      ),
      p(
        'Finance leaders often go looking for the "industry-standard" ARR calculation, hoping to adopt the correct one and be done. That search is misguided, because the standard they\'re looking for doesn\'t exist — and even if it did, adopting it might misrepresent their own business. Forcing a pure-subscription ARR definition onto a usage-heavy company doesn\'t make the number more correct; it makes it less honest.',
      ),
      p(
        "The goal isn't to compute ARR the way everyone else does. The goal is to establish an ARR methodology that:",
      ),
      bullet(
        "**Reflects the economics of your business** — represents how your recurring revenue actually behaves.",
      ),
      bullet(
        "**Is documented** — written down, not living in one analyst's head.",
      ),
      bullet(
        "**Is repeatable** — produces the same result from the same inputs every time.",
      ),
      bullet(
        "**Is explainable** — can be articulated clearly to anyone who asks.",
      ),
      bullet(
        "**Produces consistent results over time** — so this quarter compares honestly to last quarter.",
      ),
      p(
        "A methodology with those five properties is trustworthy regardless of whether it matches any other company's. And trustworthiness is what you're actually after, because it's what makes the number *usable*.",
      ),
      p(
        "Consistency is what enables everything ARR is supposed to support. **Better executive reporting**, because leadership is looking at a stable, well-understood number. **Better board reporting**, because directors can trust that this quarter's ARR was computed like last quarter's. **Better investor communication**, because you can explain precisely what your ARR represents. **More reliable forecasting**, because you're projecting from a consistent base. **Better strategic decisions**, because decisions built on a shifting definition are built on sand.",
      ),
      p(
        'An inconsistent ARR — one computed differently by different people, or redefined quietly between periods — poisons all of that, no matter how "standard" the underlying formula. A consistent ARR that\'s unique to your business supports all of it. Consistency beats standardization, decisively.',
      ),

      h2("Why software shouldn't define your ARR"),
      p("This has a direct implication for the tools finance uses."),
      p(
        "Finance organizations spend years refining how they define recurring revenue. The current ARR methodology at a mature SaaS company usually reflects dozens of deliberate decisions — how to handle that unusual enterprise contract, what to do with the usage tier introduced two years ago, how amendments flow through. That accumulated set of choices is institutional knowledge. It encodes a real understanding of the business's economics.",
      ),
      p(
        'So it\'s a problem when software forces finance into a predefined ARR calculation. A tool that says "here\'s how we compute ARR, adapt your business to it" is asking finance to discard hard-won methodology in favor of the vendor\'s assumptions. That\'s backwards. The methodology represents years of refinement specific to the business; the software is a newcomer. The software should adapt to the methodology, not the other way around.',
      ),
      p(
        "The right relationship is that technology preserves and enforces your methodology — applying your documented rules consistently and at scale — rather than replacing them with someone else's defaults. Your ARR definition is yours for good reasons. Software's job is to compute it faithfully, not to overrule it. (This is closely related to why [financial data needs translation, not just integration](/blog/financial-data-translation): your methodology *is* the translation layer, and it shouldn't be flattened into a vendor's generic definitions.)",
      ),

      h2("Why AI cannot invent your ARR definition"),
      p(
        "The same principle applies, even more sharply, to AI — because AI's fluency can create the illusion that it *could* define ARR for you.",
      ),
      p("It can't, and it shouldn't try. AI cannot determine:"),
      bullet(
        "**What counts as recurring revenue** in your specific model.",
      ),
      bullet(
        "**Which customers belong in ARR** given your contract structures.",
      ),
      bullet(
        "**Which pricing models qualify** as recurring for your purposes.",
      ),
      bullet(
        "**How you define expansion** versus a routine true-up.",
      ),
      bullet(
        "**How you define contraction** versus a temporary dip.",
      ),
      p(
        "These aren't pattern-recognition problems that a capable model can solve. They're business judgments that belong to finance leadership — decisions about how to represent the economics of a business the AI doesn't run. An AI can guess at a plausible ARR definition, but a plausible guess is exactly the wrong thing here, because it might not match how your business actually works, and it would be delivered with total confidence.",
      ),
      p(
        "The correct role for AI is the same one it should hold everywhere in finance: apply the documented methodology, don't invent it. Once finance has defined ARR, AI can compute against that definition, explain the movements, and surface trends — all valuable. But the definition itself comes from finance, is encoded as explicit rules, and stays under finance's control. AI executes the methodology; it doesn't author it. (This is the ARR-specific case of a broader principle we've written about in [what makes financial AI trustworthy](/blog/explainable-ai-in-finance).)",
      ),

      h2("Your ARR methodology is part of your competitive advantage"),
      p(
        "It's worth reframing ARR methodology from a chore into an asset, because that's what a well-governed one actually is.",
      ),
      p("A consistent, documented ARR methodology produces:"),
      bullet(
        "**Better executive alignment**, because leadership shares one understanding of the number.",
      ),
      bullet(
        "**More trustworthy board reporting**, because the methodology holds steady across quarters.",
      ),
      bullet(
        "**Stronger investor confidence**, because you can explain your ARR precisely and defend it under diligence.",
      ),
      bullet(
        "**Better internal decision making**, because the number decisions rest on is stable.",
      ),
      bullet(
        "**Consistent historical reporting**, because you can compare across periods without apples-to-oranges problems.",
      ),
      bullet(
        "**Reliable financial intelligence**, because everything built on ARR inherits its consistency.",
      ),
      p(
        'That last point about diligence deserves emphasis. When an investor or acquirer examines your ARR, the question isn\'t "did you use the industry-standard formula?" It\'s "can you explain your methodology, show that you\'ve applied it consistently, and trace the number to source?" A company that can do that inspires confidence. A company whose ARR was computed differently each period, with no documentation, raises red flags — even if the underlying number is defensible.',
      ),
      p(
        "Which is why ARR methodology deserves the same discipline you apply to any financial policy: documented, owned, reviewed when it changes, and enforced consistently. It's not a spreadsheet convention. It's a governing policy, and treating it as one is part of what separates a finance function that inspires confidence from one that merely produces numbers. (For the broader discipline this fits into, see [why every SaaS finance team needs a financial data governance strategy](/blog/financial-data-governance-saas-finance).)",
      ),

      h2("Different methodologies, all potentially valid"),
      p(
        "To make the point concrete: here are common ARR questions with two reasonable answers each. The purpose isn't to pick a winner — it's to show that different intentional, consistently applied choices can all be valid.",
      ),
      bullet(
        "**Usage revenue** — One possible methodology: included as recurring. Another: excluded as variable.",
      ),
      bullet(
        "**Professional services** — One possible methodology: excluded as non-recurring. Another: included in limited, recurring cases.",
      ),
      bullet(
        "**Multi-year contracts** — One possible methodology: annualized evenly. Another: recognized per escalator/ramp policy.",
      ),
      bullet(
        "**Month-to-month subscriptions** — One possible methodology: annualized into ARR. Another: excluded (no annual commitment).",
      ),
      bullet(
        "**Discounts** — One possible methodology: reflected in reported ARR. Another: treated separately per reporting policy.",
      ),
      p(
        "Every row above is a defensible choice. What makes any row *correct* isn't which column you pick — it's that you picked deliberately, documented the choice, and apply it the same way every period. Two companies could choose opposite answers down the entire list and both have trustworthy ARR, as long as each is internally consistent and explainable.",
      ),

      h2("The goal isn't standard ARR. It's trusted ARR."),
      p("Pull it all together and the conclusion is clear."),
      p(
        "The objective was never to calculate ARR exactly like every other SaaS company. That would be impossible — your business isn't like every other SaaS company — and chasing it would produce a number that misrepresents your own economics.",
      ),
      p(
        'The objective is to calculate ARR consistently, explainably, and transparently, so that every executive, board member, and investor understands exactly what the number represents. A trusted ARR is one where the methodology is documented, the calculation is repeatable, every figure traces to source, and anyone who asks "how did you get this?" gets a clear, confident answer. That number is useful. It supports decisions, survives diligence, and holds up over time — precisely because it\'s consistent and explainable, not because it matches an imaginary standard.',
      ),
      p("So the principle to leave with:"),
      p(
        "**The best ARR methodology isn't the industry's. It's yours — as long as it's consistent, explainable, repeatable, and trusted.**",
      ),

      h2("FAQ"),
      p("**What is ARR?**"),
      p(
        "ARR stands for Annual Recurring Revenue — the annualized value of a SaaS company's recurring revenue at a point in time. It's an operational metric finance teams use to understand recurring business performance. Unlike GAAP revenue, it isn't governed by accounting standards.",
      ),
      p("**How is ARR calculated?**"),
      p(
        "At its simplest, ARR annualizes recurring subscription revenue (roughly, committed monthly recurring revenue times twelve). But the details — how to treat usage, services, discounts, multi-year deals, and month-to-month customers — vary by company, so there's no single formula that applies universally.",
      ),
      p("**Is there a standard ARR formula?**"),
      p(
        "No. Unlike GAAP revenue, ARR has no governing standard or authoritative definition. It's an operational metric each finance team defines to fit its own business model, which is why two companies can report ARR correctly yet compute it differently.",
      ),
      p("**What should be included in ARR?**"),
      p(
        "That depends on your business and your documented methodology. Recurring subscription revenue is almost always included; one-time professional services are usually excluded; usage revenue, discounts, and month-to-month contracts are judgment calls. The right answer is the one that reflects your economics and is applied consistently.",
      ),
      p("**Why do SaaS companies report different ARR values?**"),
      p(
        "Because ARR isn't standardized, and because companies have genuinely different pricing models, contracts, and reporting objectives. Different, intentional methodologies can all be valid — what matters is that each company defines, documents, and applies its methodology consistently.",
      ),

      h2("Where SMPL.ai fits"),
      p(
        "SMPL.ai is built on the premise that your ARR methodology is yours — a finance operating system that adapts to how your company defines recurring revenue rather than imposing a definition on you.",
      ),
      p(
        "SMPL reads and reconciles data from your connected systems — billing, CRM, and the general ledger — and does not replace your systems of record. It applies your documented ARR methodology, computing the ARR waterfall and its movements deterministically and repeatably, so the same inputs always produce the same outputs. Every reported number can be traced back to its originating source, and validation and reconciliation occur before anything reaches executive reporting.",
      ),
      p(
        "The AI explains financial performance — what drove ARR, how movements compare across periods — but it does not invent your financial methodologies. Your definitions govern the calculation; the AI describes the result. (Authentication today uses magic links.)",
      ),
      p(
        "If you'd like to see your own ARR methodology computed consistently and traced to source, [book a demo](https://www.smpl-ai.com/book-demo) and we'll walk it on data that looks like yours.",
      ),
    ],
  },

  {
    _id: "post-grr-vs-nrr",
    _type: "post",
    title: "GRR vs NRR: Why SaaS Companies Need Both",
    slug: { _type: "slug", current: "grr-vs-nrr" },
    excerpt:
      "GRR vs NRR: what each retention metric actually measures, why they can tell opposite stories, and why great SaaS finance teams report both. A practical guide, not a glossary.",
    publishedAt: "2026-08-04T16:30:00.000Z",
    author: { _type: "reference", _ref: "author-smpl-team" },
    categories: [{ _type: "reference", _ref: "category-arr-revenue" }],
    seoTitle: "GRR vs NRR: Why SaaS Companies Need Both | SMPL.ai",
    seoDescription:
      "GRR vs NRR: what each retention metric actually measures, why they can tell opposite stories, and why great SaaS finance teams report both. A practical guide, not a glossary.",
    body: [
      h2("Two retention metrics, one common mistake"),
      p(
        "Gross Revenue Retention and Net Revenue Retention have become two of the most closely watched numbers in SaaS. They show up in every board deck, every investor update, every diligence process. And they generate a predictable set of questions in every finance team:",
      ),
      p(
        "What's our NRR? What's our GRR? Why are they different? And the one that comes up most: which metric matters more?",
      ),
      p(
        "That last question is the wrong one — and it's worth understanding why, because the framing itself causes confusion. GRR and NRR aren't competing measures of the same thing, where one is the better version. They answer *different business questions*. Asking which matters more is like asking whether a car's speedometer or its fuel gauge is more important. They tell you different things, and you need both to drive.",
      ),
      p(
        "Understanding both — and, crucially, understanding what it means when they diverge — gives finance a far more complete picture of customer health than either number alone. This article is about what each metric actually measures, why they can tell opposite stories about the same business, and why mature finance organizations always report both together.",
      ),
      p(
        "If you need short definitions first: see [NRR](/glossary/nrr) and [GRR](/glossary/grr) in the glossary. The rest of this piece is about reading both numbers together — in the board pack and in diligence.",
      ),

      h2("What is Gross Revenue Retention (GRR)?"),
      p(
        "Gross Revenue Retention measures how much recurring revenue you keep from your existing customer base — *before* counting any expansion.",
      ),
      p(
        'That "before expansion" part is the whole point of GRR. It deliberately ignores upsells, cross-sells, and any growth within the base, and looks only at what you retained or lost. It reflects:',
      ),
      bullet("**Customer retention** — did customers stay?"),
      bullet("**Downgrades** — did they move to cheaper tiers?"),
      bullet("**Contractions** — did they reduce their spend?"),
      bullet("**Churn** — did they leave entirely?"),
      p(
        'Because it excludes expansion, GRR can never exceed 100%. The best you can do is keep every dollar you started with — you can\'t "gain" in a metric that ignores growth. A GRR of 90% means you retained 90% of your starting recurring revenue and lost 10% to some combination of churn and contraction, regardless of how much you expanded elsewhere.',
      ),
      p(
        "GRR answers one focused question: how well are we *protecting* the revenue we already have? It's a measure of the durability of your customer base — the leakage before any of the growth story is layered on top.",
      ),

      h2("What is Net Revenue Retention (NRR)?"),
      p(
        "Net Revenue Retention measures how the revenue from your existing customers changes over time — *after* accounting for everything, growth included.",
      ),
      p(
        "Where GRR stops at retention, NRR adds the expansion back in. It reflects:",
      ),
      bullet("**Expansion revenue** — customers spending more."),
      bullet("**Upsells** — moving to higher tiers."),
      bullet("**Cross-sells** — buying additional products."),
      bullet("**Contractions** — customers reducing spend."),
      bullet("**Churn** — customers leaving."),
      p(
        "Because it includes expansion, NRR *can* exceed 100% — and for healthy SaaS businesses, it often does. An NRR above 100% means your existing customers, as a group, are worth more today than they were a year ago, even after accounting for the ones who left or shrank. That's the hallmark of a business where growth compounds within the base, not just from new logos.",
      ),
      p(
        "NRR answers a different question than GRR: how much *additional value* are our existing customers creating over time? It measures the overall economic trajectory of the customer base — not just whether you kept it, but whether it grew.",
      ),

      h2("GRR measures stability. NRR measures growth."),
      p(
        "Here's the distinction that makes both metrics necessary, stated as simply as possible:",
      ),
      p(
        "**GRR answers: how well are we protecting the revenue we already have?**",
      ),
      p(
        "**NRR answers: how much additional value are our existing customers creating?**",
      ),
      p(
        "GRR is a stability metric. It tells you how leaky the bucket is — how much revenue drains away before you pour anything new in. NRR is a growth metric. It tells you whether the water you already have is somehow multiplying — whether expansion is outrunning churn inside the existing base.",
      ),
      p(
        "Both perspectives matter, and neither substitutes for the other, because each can hide what the other reveals:",
      ),
      bullet(
        "**High NRR can hide weak retention.** A company can post an impressive NRR while quietly losing a meaningful share of customers — because strong expansion from the customers who stay masks the churn of the ones who leave. The growth story looks great; the retention problem is invisible in the NRR alone.",
      ),
      bullet(
        "**Strong GRR with weak NRR can signal limited growth.** A company can retain almost every dollar (high GRR) but generate little expansion (NRR barely above 100%). The customer base is loyal and stable, but it isn't growing — which may point to limited upsell opportunity or an under-monetized product.",
      ),
      bullet(
        "**Strong performance requires understanding both.** A genuinely healthy business retains well *and* expands well — high GRR *and* high NRR. You can only confirm that by looking at both. Either number alone can tell a flattering story that the other would complicate.",
      ),
      p(
        'This is why the "which matters more?" question misleads. The valuable question is: what do GRR and NRR say *together*, and what does the gap between them reveal?',
      ),

      h2("When GRR and NRR tell different stories"),
      p(
        "This is where interpretation gets genuinely useful — and where a finance leader adds value that a metric definition can't. Consider two companies:",
      ),
      bullet("**Company A: GRR = 85%, NRR = 115%**"),
      bullet("**Company B: GRR = 95%, NRR = 102%**"),
      p(
        "Glance at NRR alone and Company A looks like the stronger business — 115% versus 102%. But that reading misses almost everything important, and the two numbers together tell a much richer story.",
      ),
      p(
        "**Company A** is losing 15% of its recurring revenue to churn and contraction each year (GRR of 85%). That's significant leakage. What rescues the NRR is powerful expansion — the customers who stay are spending so much more that they more than offset the substantial losses, pushing NRR to 115%. This is a business with an excellent expansion motion papering over a real retention problem. The 115% NRR is impressive, but it's masking a leaky bucket. If expansion ever slows — a saturated base, a tougher economy, a pricing ceiling — that retention weakness will surface fast, because there'll be nothing offsetting the 15% leak. Company A should be worried about *why* customers are leaving, even while celebrating expansion.",
      ),
      p(
        "**Company B** looks less exciting on NRR (102%) but is retaining almost everything (GRR of 95%). Only 5% of recurring revenue leaks away. The modest NRR tells you expansion is limited — existing customers aren't growing their spend much. This is an exceptionally loyal, stable customer base with less expansion opportunity. The question for Company B isn't retention — that's excellent — it's whether there's untapped upsell potential, a product-expansion path, or pricing power being left on the table. Company B should be asking *how to grow* its very sticky base, not *how to keep* it.",
      ),
      p(
        'Same category of metrics, opposite underlying stories. Company A has a growth engine hiding a retention hole; Company B has a retention fortress with an underused growth lever. Neither is simply "better" — they have different strengths and different risks, and you can only see any of that by reading GRR and NRR *together*. That\'s the interpretation finance owes its executive team: not "NRR is 115%," but "NRR is 115% *because* expansion is masking 15% churn, and here\'s why that matters."',
      ),

      h2("How the math actually works"),
      p(
        "Both metrics start from a cohort: the customers (and their ARR) you had at the beginning of the period. New logos acquired during the period do **not** belong in classic NRR/GRR. They belong in new ARR on the [ARR waterfall](/blog/arr-waterfall-vs-gaap-revenue).",
      ),
      p("From that starting ARR:"),
      bullet(
        "**Subtract contraction** (downgrades, seat loss, tier moves down).",
      ),
      bullet("**Subtract churn** (full logo or ARR exits)."),
      bullet(
        "**For NRR only, add expansion** (upsells, cross-sells, seat growth, price increases on renewals).",
      ),
      p("A clean way to say it:"),
      bullet(
        "**GRR** = (starting ARR − contraction − churn) ÷ starting ARR",
      ),
      bullet(
        "**NRR** = (starting ARR − contraction − churn + expansion) ÷ starting ARR",
      ),
      p(
        "If your waterfall cannot reproduce both from the same movements, the retention slide is not finished. GRR and NRR are not separate models. They are two readings of one bridge — see also [waterfall](/glossary/waterfall) and [ARR](/glossary/arr).",
      ),

      h3("A simple example"),
      p("Start the quarter with $10.0M ARR in the existing base."),
      bullet("Expansion: +$1.8M"),
      bullet("Contraction: −$0.7M"),
      bullet("Churn: −$0.9M"),
      p(
        "Ending ARR from that cohort = $10.0M + $1.8M − $0.7M − $0.9M = **$10.2M**.",
      ),
      bullet("**NRR** = $10.2M ÷ $10.0M = **102%**"),
      bullet(
        "**GRR** = ($10.0M − $0.7M − $0.9M) ÷ $10.0M = **84%**",
      ),
      p(
        "NRR says the installed base grew slightly. GRR says you kept 84 cents of every starting dollar before upsell. Both are true. Presenting only 102% invites the wrong celebration.",
      ),

      h2("Why investors watch both metrics"),
      p(
        "Sophisticated investors never look at one of these in isolation, because each tells them something the other can't.",
      ),
      p("**High GRR** signals to investors:"),
      bullet(
        "**Strong customer satisfaction** — customers stay because the product delivers.",
      ),
      bullet(
        "**Stable recurring revenue** — the base is durable and predictable.",
      ),
      bullet(
        "**A predictable business** — low leakage means the revenue floor is solid.",
      ),
      p("**High NRR** signals something different:"),
      bullet(
        "**Product expansion** — the product has room to grow within accounts.",
      ),
      bullet(
        "**Pricing power** — customers accept paying more over time.",
      ),
      bullet(
        "**Customer adoption** — usage and reliance are deepening.",
      ),
      bullet(
        "**Long-term growth potential** — the base compounds, so growth doesn't depend solely on new logos.",
      ),
      p(
        "Notice these are different signals about different qualities. GRR speaks to the *safety* of the revenue; NRR speaks to its *growth potential*. An investor evaluating a SaaS business wants both — a durable base (GRR) that also compounds (NRR). A company strong on one and weak on the other raises exactly the questions the two-company example illustrates. This is why neither metric should be evaluated independently in diligence, and why a finance team that reports only its most flattering number invites skepticism rather than confidence.",
      ),

      h2("Why finance needs consistent methodologies"),
      p(
        "Everything above assumes GRR and NRR are calculated consistently — and that's a bigger assumption than it sounds. Like ARR, neither metric has a single universal formula, so calculating them reliably requires documented methodology decisions:",
      ),
      bullet(
        "**Customer cohorts** — how you define the starting base and the period being measured.",
      ),
      bullet(
        "**Expansion timing** — when an upsell counts toward the period.",
      ),
      bullet(
        "**Contract amendments** — how mid-term changes flow through.",
      ),
      bullet(
        "**Usage revenue** — whether and how variable revenue counts toward retention.",
      ),
      bullet("**Downgrades** — how contractions are measured."),
      bullet(
        "**Reactivations** — how a returning customer is treated.",
      ),
      bullet(
        "**Foreign exchange** — how currency movement is handled, if applicable.",
      ),
      bullet(
        "**Partial-period customers** — how customers who start or leave mid-period count.",
      ),
      p("A few definition traps that show up in the same meetings:"),
      bullet(
        "**CRM ARR vs billing ARR.** If Sales' expansion sits in the CRM and Finance's retention sits in billing, NRR and GRR will disagree with bookings commentary. The metrics are only as trustworthy as the source definitions behind ARR — and as a [documented ARR methodology](/blog/arr-governance) the whole company can reuse. Pick one governed definition for board retention and stick to it.",
      ),
      bullet(
        "**Including new logos in NRR.** That inflates the rate and breaks comparability. New business is a growth line, not a retention credit.",
      ),
      bullet(
        "**Price increases counted as expansion without disclosure.** Legitimate in many ARR policies — but boards should know when NRR is partly a pricing story.",
      ),
      bullet(
        "**Multi-year ramps and delayed starts.** Ramp deals can look like expansion when they are really contracted schedule. Your ARR policy has to say which is which, consistently, every close.",
      ),
      p(
        "Each of these is a judgment call, and the same underlying business can produce different GRR and NRR figures depending on how they're answered. Which leads to the same principle that governs ARR: methodology *consistency* matters more than matching another company's reported numbers. Comparing your NRR to a competitor's headline NRR is nearly meaningless if you've defined the metric differently — and you probably have. What matters is that you calculate GRR and NRR the same way every period, document how you do it, and can explain it. (This is the retention-metric case of the discipline we've written about in [ARR governance](/blog/arr-governance) and [why there's no standard ARR calculation](/blog/no-standard-arr-calculation).)",
      ),
      p(
        "Consistency is also what makes the *trend* trustworthy. A rising NRR only means something if this quarter's NRR was computed like last quarter's. Inconsistent methodology turns your retention trend into noise — which is why consistent calculation, traceable to source, underpins any useful retention reporting. (Inconsistent underlying data is a fast way to undermine this; see [why poor financial data holds back finance teams](/blog/poor-financial-data-limiting-finance).)",
      ),

      h2("Executive reporting should include both"),
      p(
        "Given all this, board and executive reporting should never present one retention number in isolation. A complete retention picture includes:",
      ),
      bullet("**GRR** — the stability of the base."),
      bullet("**NRR** — the growth of the base."),
      bullet("**Churn** — the revenue lost to departures."),
      bullet("**Expansion** — the revenue gained within the base."),
      bullet("**Contraction** — the revenue lost to downgrades."),
      p(
        "Presented together, these let executives see the full story rather than a curated slice. GRR and NRR frame it; churn, expansion, and contraction explain it. You can see not just *that* NRR is 112%, but that it's 112% because expansion of 22% offset churn and contraction of 10% — which is a completely different situation than 112% built on 4% churn and 8% expansion.",
      ),
      p(
        "That's the real standard for retention reporting: executives should understand *why* NRR changed, not simply *whether* it went up or down. A number that moves without an explanation invites the follow-up questions that erode confidence. A number presented with its drivers — here's the expansion, here's the churn, here's what changed — is one the board can actually use to make decisions.",
      ),

      h2("Board questions you should be ready for"),
      p("These come up whether or not they appear on the slide."),
      numbered(
        '**"Is NRR above 100% because we retained customers — or because a few whales expanded?"** Be ready to show concentration: top-10 expansion vs the rest of the base. Cohort NRR without a concentration note is easy to misread.',
      ),
      numbered(
        '**"What would GRR be if we excluded involuntary churn / bankruptcies / one large logo?"** Have a policy before the meeting. Adjustments are fine when disclosed. Silent exclusions destroy trust.',
      ),
      numbered(
        '**"Why did GRR fall while NRR held?"** Classic pattern: churn or contraction worsened, and expansion plugged the hole. That is an early warning, not a win.',
      ),
      numbered(
        '**"Are these logo-weighted or ARR-weighted?"** Almost all board NRR/GRR should be **ARR-weighted** (dollar retention). Logo retention is a different chart. Mixing the two mid-answer is how meetings derail.',
      ),
      numbered(
        '**"Does this match the waterfall on the prior slide?"** If ending ARR, expansion, contraction, and churn on the waterfall cannot regenerate the retention percentages, stop. Fix the pack before you defend a narrative. Related failure mode: when [ARR, cash, and the P&L tell different stories](/blog/saas-board-reporting-arr-cash-pl) because each came from a different export.',
      ),
      numbered(
        '**"Is starting ARR the same population RevOps uses for renewal forecasts?"** Definition drift between finance and RevOps is one of the fastest ways to lose a room. Align the cohort rules in writing.',
      ),

      h2("How to present GRR and NRR in the pack"),
      p("A practical pattern that keeps the board oriented:"),
      numbered(
        "**Waterfall first** — beginning ARR → new / expansion / contraction / churn → ending ARR.",
      ),
      numbered(
        "**Retention second** — GRR and NRR for the same period, same cohort, same movements.",
      ),
      numbered(
        '**One sentence on the gap** — "NRR is 108%; GRR is 91%; the 17-point spread is expansion in the existing base, concentrated in enterprise."',
      ),
      numbered(
        "**Optional: segment** — enterprise vs mid-market GRR/NRR often matters more than the blended number.",
      ),
      p(
        "Keep commentary tied to the same figures as the table. If the narrative says expansion saved the quarter, the expansion dollar amount on the waterfall should be the one in the sentence. That is the same trust standard as the rest of [SaaS board reporting](/blog/saas-board-reporting-arr-cash-pl): traceable numbers beat a polished story that cannot be checked.",
      ),
      p(
        'When CFOs start hearing "which number is correct?" about retention, the root cause is usually conflicting definitions — not a missing chart. The fix is one cohort, one set of movements, two clearly labeled rates. See also [why CFOs stop trusting their own numbers](/blog/why-cfos-stop-trusting-their-numbers).',
      ),

      h2("The goal isn't choosing one metric"),
      p("Pull it all together and the conclusion is clear."),
      p(
        "GRR and NRR are complementary, not competing. One measures the strength of your customer retention — how well you protect what you have. The other measures the growth potential of your existing customers — how much more they become worth over time. Together, they tell you both the *stability* and the *scalability* of your recurring revenue, which is exactly what finance, executives, and investors need to understand the health of a SaaS business.",
      ),
      p(
        "Choosing between them means throwing away half the picture. The gap between them — as the two-company example showed — often contains the most important insight of all: whether expansion is masking churn, or whether loyalty is masking a growth ceiling.",
      ),
      p("So the principle worth leaving with:"),
      p(
        "**Great SaaS finance organizations don't ask whether GRR or NRR is more important. They understand that each metric tells a different part of the company's growth story.**",
      ),

      h2("GRR vs NRR at a glance"),
      p(
        "The two metrics side by side, to keep the distinction clear:",
      ),
      bullet(
        "**Gross Revenue Retention (GRR)** — Measures retained recurring revenue; excludes expansion; focuses on retention quality; highlights churn and contractions; capped at 100%; indicates revenue stability.",
      ),
      bullet(
        "**Net Revenue Retention (NRR)** — Measures retained and expanded recurring revenue; includes expansion; focuses on customer growth; highlights total customer value; can exceed 100%; indicates long-term growth potential.",
      ),

      h2("FAQ"),
      p("**What is Gross Revenue Retention?**"),
      p(
        "GRR measures how much recurring revenue a company retains from its existing customers before any expansion — accounting only for churn, downgrades, and contractions. It's capped at 100% and reflects the stability and durability of the customer base.",
      ),
      p("**What is Net Revenue Retention?**"),
      p(
        "NRR measures how the recurring revenue from existing customers changes over time after including expansion, upsells, and cross-sells alongside contraction and churn. It can exceed 100%, and a figure above 100% means existing customers are worth more over time even after accounting for losses.",
      ),
      p("**What is a good GRR?**"),
      p(
        "It varies by segment, but higher is better and the ceiling is 100%. Enterprise-focused SaaS businesses often target GRR in the low-to-mid 90s, while lower figures can be normal for SMB-focused businesses with naturally higher churn. What matters most is measuring it consistently and understanding the trend.",
      ),
      p("**What is a good NRR?**"),
      p(
        "NRR above 100% is generally considered healthy, since it means expansion is outpacing churn and contraction. Best-in-class businesses often report meaningfully higher. But NRR should always be read alongside GRR, because a strong NRR can mask weak retention.",
      ),
      p("**Why do investors care about NRR?**"),
      p(
        "Because NRR indicates whether growth compounds within the existing customer base rather than depending entirely on new-logo acquisition. High NRR signals product expansion, pricing power, and deepening adoption — all markers of long-term growth potential. Investors read it alongside GRR to confirm the base is both durable and growing.",
      ),
      p("**Should SaaS companies report both GRR and NRR?**"),
      p(
        "Yes. They answer different questions — GRR measures retention stability, NRR measures growth within the base — and each can hide what the other reveals. Reporting both, alongside churn, expansion, and contraction, gives a complete and honest picture of customer health.",
      ),
      p("**Should new customers be included in NRR?**"),
      p(
        "No. Classic NRR and GRR measure the existing starting cohort. New logos belong in new ARR on the waterfall, not as a retention credit.",
      ),
      p("**How do GRR and NRR tie to the ARR waterfall?**"),
      p(
        "They should regenerate from the same movements: starting ARR, contraction, churn, and (for NRR) expansion. If the retention slide and the waterfall disagree, fix the pack before you defend a narrative.",
      ),

      h2("Where SMPL.ai fits"),
      p(
        "SMPL.ai is built to compute retention metrics the way your business defines them — a finance operating system that applies your methodologies rather than imposing its own.",
      ),
      p(
        "SMPL reads and reconciles data from your connected systems — billing, CRM, and the general ledger — and does not replace your systems of record. It computes GRR, NRR, and the churn, expansion, and contraction movements beneath them from one reconciled base, deterministically and repeatably, so the same inputs always produce the same outputs and this quarter's retention is computed like last quarter's. Every reported number can be traced back to its originating source, and validation and reconciliation occur before anything reaches executive reporting.",
      ),
      p(
        "The AI explains financial performance — why NRR moved, what drove the gap between GRR and NRR — but it does not invent your financial methodologies. Your definitions govern the calculation; the AI describes the result. (Authentication today uses magic links.)",
      ),
      p(
        "We do not claim a certification status here. Trust in board metrics comes from definitions, reconciliation, and the ability to drill from the percentage to the customers underneath.",
      ),
      p(
        "If you'd like to see your own GRR and NRR computed consistently and traced to source, [book a demo](https://www.smpl-ai.com/book-demo) and we'll walk it on data that looks like yours.",
      ),
    ],
  },
];
