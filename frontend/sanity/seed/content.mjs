/**
 * Starter content for Sanity seed (blog posts + ~20 glossary terms).
 * Imported by scripts/seed-sanity.mjs — edit here, then re-run seed.
 *
 * Blog posts: ARR waterfall vs GAAP, board ARR/cash/P&L, AI variance commentary.
 * Old IP-heavy cornerstone posts intentionally removed from this seed.
 */

let keySeq = 0;
function key(prefix = "k") {
  keySeq += 1;
  return `${prefix}${keySeq}`;
}

/** Parse inline markdown: **strong**, *em*, [label](href) */
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

function quote(text) {
  return block("blockquote", text);
}

function bullet(text) {
  return block("normal", text, { listItem: "bullet", level: 1 });
}

function blocks(...paragraphs) {
  return paragraphs.map((text) => p(text));
}

export const author = {
  _id: "author-smpl-team",
  _type: "author",
  name: "SMPL.ai Team",
  role: "Product & FP&A",
};

export const categories = [
  {
    _id: "category-arr-revenue",
    _type: "category",
    title: "ARR & revenue",
    slug: { _type: "slug", current: "arr-revenue" },
  },
  {
    _id: "category-trust-reporting",
    _type: "category",
    title: "Trust & reporting",
    slug: { _type: "slug", current: "trust-reporting" },
  },
  {
    _id: "category-ai-in-fpa",
    _type: "category",
    title: "AI in FP&A",
    slug: { _type: "slug", current: "ai-in-fpa" },
  },
  // Kept so existing Studio refs / glossary context don't break; unused by new posts.
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

/** Posts removed from seed (delete on re-seed): board-numbers-need-evidence, saas-close-load-validate-lock-freeze, ai-commentary-finance-will-sign */
export const posts = [
  {
    _id: "post-arr-waterfall-vs-gaap-revenue",
    _type: "post",
    title: "ARR Waterfall vs GAAP Revenue",
    slug: { _type: "slug", current: "arr-waterfall-vs-gaap-revenue" },
    excerpt:
      "ARR waterfall and GAAP revenue answer different board questions. Why SaaS CFOs need both in one traceable operating model — and how to reconcile them for board reporting.",
    publishedAt: "2026-07-21T18:00:00.000Z",
    author: { _type: "reference", _ref: "author-smpl-team" },
    categories: [{ _type: "reference", _ref: "category-arr-revenue" }],
    seoTitle: "ARR Waterfall vs GAAP Revenue | SMPL.ai",
    seoDescription:
      "ARR waterfall and GAAP revenue answer different board questions. Why SaaS CFOs need both in one traceable operating model — and how to reconcile them for board reporting.",
    body: [
      h2("Two numbers, one board meeting"),
      p(
        "A SaaS board deck almost always carries two revenue stories.",
      ),
      p(
        "One is the **ARR waterfall**: new, expansion, contraction, churn, ending ARR. It tells the board where recurring momentum is heading.",
      ),
      p(
        "The other is GAAP revenue: what the income statement recognized last quarter, audited and tied to deferred revenue.",
      ),
      p(
        "Both are correct. They rarely tie out to the same number. And that gap is where board conversations go sideways.",
      ),
      p(
        'A director looks at 42% ARR growth on slide 9, then sees 31% revenue growth on slide 14, and asks the obvious question: which one is real? The honest answer is "both, they measure different things" — but if your FP&A team can\'t show *why* they differ, the follow-up emails start before the meeting ends.',
      ),
      p(
        "This piece breaks down what each number actually measures, why they diverge on purpose, and why a growth-stage SaaS CFO needs both living in one governed operating model instead of two disconnected spreadsheets.",
      ),
      h2("What the ARR waterfall actually measures"),
      p(
        "ARR is a run-rate. It's the annualized value of your recurring subscription contracts at a point in time. Multiply committed MRR by twelve and you're close.",
      ),
      p(
        "Note the word *contracted*. ARR is a forward-looking momentum metric, not a recognized-revenue metric. A customer who signs a $120,000 annual deal on the last day of the quarter adds $120,000 to ARR immediately — even though GAAP will recognize almost none of it in that period.",
      ),
      p(
        "The ARR waterfall is the bridge that explains how you got from beginning ARR to ending ARR over a period. It's built from four movements.",
      ),
      h3("The four movements"),
      bullet(
        "**New.** ARR from newly acquired customers — logos that weren't paying you at the start of the period. This is the top-of-funnel growth line the board watches most closely.",
      ),
      bullet(
        "**Expansion.** ARR growth *inside* your existing base: upsells, cross-sells, added seats, tier upgrades, price increases on renewal. The customer stays; their spend goes up.",
      ),
      bullet(
        "**Contraction.** The reverse. Existing customers who downgrade, drop seats, or move to a cheaper tier. They're still customers, but they're worth less than they were.",
      ),
      bullet(
        "**Churn.** Full loss. A customer cancels and their ARR leaves the base entirely. This is gross ARR churn — the number that feeds gross revenue retention.",
      ),
      p(
        "Beginning ARR, plus new, plus expansion, minus contraction, minus churn, equals ending ARR. That's the whole waterfall.",
      ),
      p(
        "These movements also feed the retention metrics boards ask about by name. **Net revenue retention** nets expansion against contraction and churn within the existing base. **Gross revenue retention** ignores expansion and shows how much you kept before any upsell. A waterfall that can't reproduce NRR and GRR from the same movements isn't finished.",
      ),
      p(
        'The ARR waterfall is a management metric. There\'s no accounting standard that defines it. Two companies can compute "expansion" differently and both be defensible. That flexibility is useful — and it\'s exactly why the number needs governance, which we\'ll come back to.',
      ),
      h2("What GAAP revenue actually measures"),
      p(
        "GAAP revenue is what you *earned*, recognized under ASC 606 as you satisfy performance obligations. For most SaaS, that means recognizing subscription revenue ratably over the service period.",
      ),
      p(
        "Take that same $120,000 annual contract signed on the last day of the quarter. GAAP recognizes roughly $10,000 per month as you deliver the service. In the quarter it was signed, recognized revenue is close to zero. The other ~$120,000 sits on the balance sheet as **deferred revenue** — a liability representing cash you've billed or collected but haven't yet earned.",
      ),
      p(
        "So GAAP revenue is backward-looking and delivery-based. It's audited. It ties to the income statement, to deferred revenue on the balance sheet, and to cash once you account for billing terms and collections.",
      ),
      p(
        "It also includes things ARR deliberately excludes. One-time implementation fees, professional services, and usage overages generally show up in GAAP revenue but not in ARR, because they aren't recurring. That's another reason the two numbers won't match.",
      ),
      p(
        "**ARR is not recognized revenue.** Treating them as interchangeable is the single most common error in SaaS board reporting, and a sharp director will catch it in seconds.",
      ),
      h2("Why the two never tie — and why that's fine"),
      p(
        "The divergence isn't a mistake to fix. It's structural. Three drivers explain most of it.",
      ),
      p(
        "**Timing.** ARR books the full run-rate the moment a contract goes live. GAAP spreads that same contract across the delivery period. A strong bookings quarter inflates ending ARR long before it shows up in recognized revenue.",
      ),
      p(
        "**Scope.** ARR is recurring subscription only. GAAP revenue includes services, one-time fees, and usage. The two are measuring overlapping-but-different populations of dollars.",
      ),
      p(
        "**Definition.** GAAP is standardized and enforceable. ARR is a management convention. Ramp deals, mid-period starts, multi-year contracts with escalators, and usage-based components all get handled differently depending on your ARR policy — and none of those judgment calls apply to how ASC 606 recognizes the revenue.",
      ),
      p(
        "None of this is a problem. The problem is when a board deck presents both numbers as if they should agree, and then can't explain the bridge when asked.",
      ),
      h2("The board conversation that goes wrong"),
      p(
        "Here's the failure mode. FP&A pulls ARR from the CRM, revenue from the GL, and retention from a separate model. Each lives in its own tab, built by a different person, refreshed on a different date.",
      ),
      p(
        'The deck looks clean. Then a director asks a simple question: "Your expansion ARR is up 60%, but recognized revenue is only up 20% — walk me through that."',
      ),
      p(
        "If the answer requires someone to reopen three spreadsheets, hunt for the source of a hardcoded cell, and rebuild a bridge live, you've lost the room. Not because the numbers are wrong, but because they aren't *traceable*. The board can't see the lineage from the headline figure back to the contract that produced it.",
      ),
      p(
        "The follow-up questions after the meeting are a symptom of the same disease. Executives keep asking because the first answer wasn't grounded in something they could verify. Trust in the numbers erodes one unresolved question at a time.",
      ),
      h2("Putting both in one operating model"),
      p(
        "The fix isn't picking ARR or GAAP. Boards need both — one for momentum, one for earned performance. The fix is putting them in a single operating model built on the same governed data, with an explicit reconciliation between them.",
      ),
      p(
        "That means the ARR waterfall and recognized revenue draw from one reconciled source of truth, not two exports that happen to sit in the same file. When new-logo ARR moves, you can trace which contracts drove it, and show how that same population flows into recognized revenue over the coming quarters. The bridge between the two becomes a standing artifact, not a fire drill.",
      ),
      p("Three things make that bridge trustworthy."),
      h3("Traceability is the price of trust"),
      p(
        "Every number in the board pack should drill down to its source. If ending ARR is $8.4M, a director should be able to see the movements that built it, and each movement should tie back to the underlying customer records — not to a cell someone typed in.",
      ),
      h3("Deterministic calculation"),
      p(
        "The same inputs should always produce the same ARR. If two runs of the same period return different numbers, no amount of narrative will rebuild trust. Deterministic calcs mean expansion is computed the same way every close, so quarter-over-quarter comparisons actually mean something.",
      ),
      h3("Governed close, not a moving target"),
      p(
        "A board number should be locked before it's presented. When your ARR waterfall and revenue figures can still shift after the deck ships, the board is reviewing a draft. A governed close — where data is loaded, validated, locked, and frozen in sequence — means the figures on slide 9 are the figures, full stop.",
      ),
      h2("How SMPL.ai handles it"),
      p(
        "SMPL.ai is built for exactly this reconciliation problem, and it's worth being precise about what it does and doesn't do.",
      ),
      p(
        "SMPL **reads and reconciles** your source systems — billing, CRM, and the general ledger — into one governed model. It computes the ARR waterfall, MRR movements, NRR, GRR, deferred revenue, and recognized revenue from the same reconciled base, so ARR and GAAP live side by side instead of in separate files.",
      ),
      p(
        "SMPL does **not** write back to your ERP or general ledger. It reads from your systems of record; it never posts to them. Your GL stays your GL. That's a deliberate boundary — the platform is a reporting and reconciliation layer, not a bookkeeping system.",
      ),
      p(
        "The calculations are deterministic. Run the same period twice, get the same waterfall. Every figure carries its lineage, so when a director asks how expansion ARR reconciles to recognized revenue, you can walk the bridge on screen and drill to the contracts underneath.",
      ),
      p(
        "The close is governed through a Load → Validate → Lock → Freeze sequence, so board numbers are locked before they're presented, not still moving in the background.",
      ),
      p(
        "And the AI narrative is grounded in those validated engine outputs. It explains the movements the model actually computed — it doesn't invent a number or a trend that isn't in the data. If the narrative says expansion drove the quarter, the figure behind that sentence traces to the same reconciled source as everything else in the pack.",
      ),
      p(
        "The result is a board conversation where ARR and GAAP revenue can both be on the table, clearly distinct, and fully reconcilable — with far fewer follow-up emails after the meeting.",
      ),
      h2("See it on your own numbers"),
      p(
        "The fastest way to judge whether one governed model beats two spreadsheets is to watch your own ARR waterfall reconcile to your own recognized revenue.",
      ),
      p(
        "[Book a demo](https://www.smpl-ai.com/book-demo) and we'll walk the bridge on data that looks like yours.",
      ),
    ],
  },
  {
    _id: "post-saas-board-reporting-arr-cash-pl",
    _type: "post",
    title: "Why SaaS Board Reporting Breaks Down",
    slug: { _type: "slug", current: "saas-board-reporting-arr-cash-pl" },
    excerpt:
      "When ARR, cash, and the P&L tell different stories, board confidence erodes. How finance leaders rebuild trust in SaaS board reporting through reconciliation, not another dashboard.",
    publishedAt: "2026-07-21T19:00:00.000Z",
    author: { _type: "reference", _ref: "author-smpl-team" },
    categories: [{ _type: "reference", _ref: "category-trust-reporting" }],
    seoTitle: "Why SaaS Board Reporting Breaks Down | SMPL.ai",
    seoDescription:
      "When ARR, cash, and the P&L tell different stories, board confidence erodes. How finance leaders rebuild trust in SaaS board reporting through reconciliation, not another dashboard.",
    body: [
      h2("Three true numbers, three different stories"),
      p(
        "Every SaaS board meeting runs on three numbers that refuse to agree.",
      ),
      p(
        "ARR says the business grew 40% this year. Cash says the balance dropped and burn accelerated. The P&L says revenue grew 26% and the operating loss widened.",
      ),
      p(
        "None of these is wrong. They're measuring different things, on different clocks, under different rules. But a board director doesn't experience them as three valid perspectives. They experience them as a contradiction — and contradictions are where confidence goes to die.",
      ),
      p(
        "The finance leader's instinct, faced with this, is to build another view. A cash dashboard. An ARR dashboard. A board-specific summary that pulls from both. Six months later there are five dashboards, they still don't reconcile, and the board is asking sharper questions than before.",
      ),
      p(
        "The problem was never a missing dashboard. It's that the three numbers were never reconciled to a common source in the first place. This piece is about why ARR, cash, and the P&L diverge, why more dashboards make it worse, and how finance leaders rebuild board confidence through reconciliation and a single operating view instead.",
      ),
      h2("Why the three numbers diverge — on purpose"),
      p(
        "Start by accepting that the divergence is real and structural. It isn't a data-quality bug you can scrub away. Each number answers a different question.",
      ),
      h3("ARR answers: how fast is recurring momentum growing?"),
      p(
        "ARR is a run-rate — the annualized value of your recurring contracts at a point in time. It books the full annual value the moment a contract goes live. Sign a $240,000 annual deal on the last day of the quarter and ARR jumps $240,000 that day.",
      ),
      p(
        "That makes ARR the cleanest read on momentum. It's also the least connected to what actually happened to the income statement or the bank account this period. ARR is forward-looking by design. It tells the board where the recurring base is heading, not what the business earned or collected.",
      ),
      h3("Cash answers: what actually hit the bank?"),
      p(
        "Cash is the one number that can't be argued with. It reflects real money in and out — collections, payroll, vendors, infrastructure.",
      ),
      p(
        "Cash runs on billing terms and collection timing, which have nothing to do with ARR. A customer on annual upfront billing pays you twelve months of cash on day one. A customer on monthly billing pays one-twelfth, even if their ARR is identical. Two customers, same ARR, wildly different cash profiles. Add a slow-paying enterprise logo and cash lags bookings by a quarter or more.",
      ),
      p(
        "So a strong ARR quarter can coincide with a weak cash quarter, and both statements are true at once.",
      ),
      h3("The P&L answers: what did you earn under the rules?"),
      p(
        "The P&L recognizes revenue as you deliver the service, under the accounting standards. That $240,000 annual deal signed on the last day of the quarter recognizes almost nothing in the quarter it was signed — roughly a month's worth, spread going forward. The rest sits on the balance sheet as **deferred revenue**, a liability for service you've been paid for but haven't yet delivered.",
      ),
      p(
        "The P&L is backward-looking and audited. It's the number your auditors sign, the number that ties to the financial statements. It deliberately ignores momentum and ignores cash timing. It only counts what you earned.",
      ),
      p(
        "So: ARR leads, cash lags or leads depending on billing, and the P&L sits in the middle recognizing earned value ratably. Three clocks, three answers. All correct.",
      ),
      h2("The board meeting where it falls apart"),
      p(
        "Here's the failure mode, and most finance leaders have lived it.",
      ),
      p(
        "The deck looks clean. ARR growth on one slide, a cash bridge a few slides later, the P&L summary near the back. Each was built by a different person, pulled from a different system, refreshed on a different day.",
      ),
      p(
        'Then a director connects two slides the deck kept apart. "Your ARR is up 40%, but the P&L shows revenue up 26% and cash going the wrong way. Which of these is the real business?"',
      ),
      p(
        'That question is fair. It\'s also unanswerable in the moment if the three numbers don\'t share a source. Someone has to say "let me get back to you," reopen three spreadsheets after the meeting, and reconstruct a bridge by hand. By the time the follow-up email goes out, the board has already formed an impression: finance doesn\'t fully understand its own numbers.',
      ),
      p(
        "That impression is the real cost. Not the reconciliation work itself — the erosion of trust. Once a board suspects the numbers can't be tied together on demand, every subsequent figure gets a second look. The follow-up questions multiply. The meeting stops being a decision-making forum and becomes an audit.",
      ),
      p(
        "And the frustrating part is that nothing was wrong. ARR, cash, and the P&L were all accurate. They just weren't reconciled, so the finance team couldn't show the board how they fit together.",
      ),
      h2("Why another dashboard won't fix it"),
      p(
        "The reflexive fix is a new view. If the board is confused by three numbers, build a fourth that reconciles them.",
      ),
      p(
        "It doesn't work, for a specific reason. A dashboard is a presentation layer. It shows numbers; it doesn't reconcile them. If ARR comes from the CRM, cash comes from the bank feed, and recognized revenue comes from the general ledger, a dashboard that displays all three side by side has done nothing to prove they tie out. It's just moved the contradiction into a nicer chart.",
      ),
      p(
        "Worse, every new dashboard is a new place for the numbers to drift. Dashboard A pulls ARR as of Tuesday. Dashboard B pulls it as of Thursday, after two deals closed. Now the same metric reads differently in two board-adjacent tools, and you've manufactured a new discrepancy to explain.",
      ),
      p(
        "More views multiply the surface area for disagreement. What finance needs is fewer numbers, more tightly connected — not more numbers, more loosely arranged.",
      ),
      p(
        "The distinction that matters: **a dashboard shows you the number; reconciliation proves the number.** Board confidence is built on the second thing, and no amount of visualization substitutes for it.",
      ),
      h2(
        "What actually rebuilds confidence: reconciliation and one operating view",
      ),
      p(
        "Confidence comes back when the finance leader can do one thing in the room: take any headline number and walk it back to its source, live, without leaving the meeting. That capability rests on a few foundations.",
      ),
      h3("One reconciled source, not three exports"),
      p(
        "ARR, cash, and recognized revenue should draw from the same reconciled base of contracts, billings, and ledger entries — not three independent exports that happen to land in the same deck. When they share a source, the bridges between them exist by construction. You can show that the ARR added this quarter flows into deferred revenue, gets recognized on the P&L over the coming periods, and converts to cash on the customer's billing schedule. The three numbers stop looking like a contradiction and start looking like one story told from three angles.",
      ),
      p(
        "That's what a single operating view means. Not a prettier dashboard — a common foundation underneath every number the board sees.",
      ),
      h3("Traceability from headline to source"),
      p(
        "Every number in the board pack should drill down. If ending ARR is $12.4M, a director should be able to see the movements that built it — new, expansion, contraction, churn — and each movement should tie back to the specific customer records behind it. Not to a typed-in cell. To the source.",
      ),
      p(
        'Traceability is what turns "let me get back to you" into "here\'s exactly where that comes from." It\'s the difference between a finance team that reports numbers and one that can defend them.',
      ),
      h3("Numbers that don't move after you present them"),
      p(
        "A board number should be settled before it goes in the deck, and it should stay settled. If ARR or recognized revenue can still shift after the pack ships — because someone refreshed a source or a late deal posted — then the board reviewed a draft. Confidence requires that the figure on the slide is the figure, and that the same period produces the same number every time it's calculated. Consistency isn't a nicety here; it's the precondition for the board trusting anything you show them.",
      ),
      h3("A narrative that matches the numbers"),
      p(
        'Boards read the commentary as closely as the charts. When the written explanation of the quarter is built on the same reconciled figures as the tables — rather than a separate, hand-written story that might not match — the whole pack holds together. The sentence "expansion drove the quarter" should trace to the same expansion number in the waterfall, not to a claim someone typed from memory.',
      ),
      h2("Where SMPL.ai fits"),
      p(
        "SMPL.ai is built for exactly this reconciliation problem, and it's worth being precise about what it does and doesn't do.",
      ),
      p(
        "SMPL **reads and reconciles** your source systems — billing, CRM, and the general ledger — into one governed operating model. From that single reconciled base it computes the SaaS metrics a board expects: the ARR waterfall, MRR movements, NRR and GRR, deferred revenue, recognized revenue, cash, and headcount as a driver. Because they all come from the same source, ARR, cash, and the P&L can sit in one view and actually tie together.",
      ),
      p(
        "SMPL does **not** write back to your ERP or general ledger. It reads from your systems of record; it never posts to them. Your GL stays your GL, owned by your team and your auditors. SMPL is a reconciliation and reporting layer on top, not a bookkeeping system that touches your books.",
      ),
      p(
        "The calculations are deterministic. Run the same period twice and you get the same numbers, so the figure in the board pack is stable and defensible. Every number carries its lineage, so when a director asks how ARR growth squares with recognized revenue and cash, you can walk the bridge on screen and drill down to the underlying contracts — in the meeting, not in a follow-up email a week later.",
      ),
      p(
        "And the AI-generated narrative is grounded in those reconciled engine outputs. It explains the movements the model actually computed. It doesn't invent a number or a trend that isn't in the data. The commentary and the tables come from the same place, so they can't quietly disagree.",
      ),
      p(
        "The result is a board conversation where ARR, cash, and the P&L stop contradicting each other and start reinforcing each other — three views of one reconciled business, not three disconnected dashboards the finance team has to defend one slide at a time.",
      ),
      h2("See it on your own numbers"),
      p(
        "The honest test of any of this is whether your own ARR, cash, and P&L can be reconciled to a single source and walked back to the contracts underneath.",
      ),
      p(
        "[Book a demo](https://www.smpl-ai.com/book-demo) and we'll do exactly that on data that looks like yours — and show you what a board pack feels like when the three numbers finally agree.",
      ),
    ],
  },
  {
    _id: "post-ai-variance-commentary-cfo-standard",
    _type: "post",
    title: "What CFOs Should Demand From AI Variance Commentary",
    slug: { _type: "slug", current: "ai-variance-commentary-cfo-standard" },
    excerpt:
      'AI for FP&A shouldn\'t produce "revenue was strong" fluff. The specificity, evidence, and sign-off readiness CFOs should demand from AI-written variance analysis and board reporting.',
    publishedAt: "2026-07-21T20:00:00.000Z",
    author: { _type: "reference", _ref: "author-smpl-team" },
    categories: [{ _type: "reference", _ref: "category-ai-in-fpa" }],
    seoTitle: "What CFOs Should Demand From AI Variance Commentary | SMPL.ai",
    seoDescription:
      'AI for FP&A shouldn\'t produce "revenue was strong" fluff. The specificity, evidence, and sign-off readiness CFOs should demand from AI-written variance analysis and board reporting.',
    body: [
      h2('"Revenue was strong" is not commentary'),
      p(
        'Here is a sentence that has appeared in a thousand board decks: "Revenue was strong this quarter, driven by continued growth across the business."',
      ),
      p(
        "It says nothing. It names no driver, cites no number, and commits to no cause. A director reading it learns exactly what they knew before: revenue went up. If that sentence was written by a person, it's weak. If it was written by AI, it's worse — because now the tool you bought to save time has produced something a human still has to rewrite.",
      ),
      p(
        'AI for FP&A is being sold hard into finance teams right now, and variance commentary is the flagship use case. Feed the model your actuals versus plan, get back written explanations of what moved and why. The pitch is real time savings. The risk is that you automate the production of fluff — generating plausible, grammatical, evidence-free prose at scale, faster than anyone can fact-check it.',
      ),
      p(
        'The question a CFO should ask isn\'t "can AI write our commentary?" It\'s "what standard does the commentary have to meet before I put my name on it?" Because you are still the one signing the board pack. This piece lays out that standard: specificity, evidence, and sign-off readiness.',
      ),
      h2("The standard: specificity, evidence, sign-off"),
      p(
        "Good variance commentary does three things generic commentary can't.",
      ),
      p(
        '**It\'s specific.** It names the actual driver, not a category. Not "strong sales performance" but "two enterprise renewals that slipped from Q2 into Q3." A CFO reading it knows something they\'d otherwise have to dig for.',
      ),
      p(
        '**It\'s evidenced.** Every claim ties to a number, and the number ties to a source. "Expansion ARR of $1.2M, up from $700K last quarter" beats "expansion was healthy." If a director asks where $1.2M comes from, the answer exists and is traceable.',
      ),
      p(
        "**It's sign-off ready.** The commentary is something the CFO can put in front of the board without a rewrite, because it's accurate, sourced, and free of claims nobody can defend. Sign-off ready doesn't mean unedited — it means the draft raises your confidence instead of your workload.",
      ),
      p(
        "Miss any one of these and the AI hasn't saved you time. It's produced a first draft you now have to audit, which for most variance work is the slow part anyway.",
      ),
      h2("Good vs bad, side by side"),
      p(
        "The gap is easiest to see in examples. Same underlying quarter, two commentaries.",
      ),
      p("**Bad:**"),
      quote(
        "Revenue exceeded expectations this quarter due to strong performance across our customer base. Churn remained manageable and expansion trends were positive. Overall, the business is well-positioned heading into next quarter.",
      ),
      p(
        'Every clause is unfalsifiable. "Strong," "manageable," "positive," "well-positioned" — none of it can be checked, and none of it tells the board anything actionable. This is the house style of AI left unsupervised.',
      ),
      p("**Good:**"),
      quote(
        "Revenue came in at $6.4M, $400K above plan. The beat was concentrated in expansion: NRR rose to 118% from 112%, driven mainly by three accounts that upgraded tiers ahead of renewal. New-logo ARR was $200K below plan, reflecting two deals that pushed to Q4. Gross churn held at 4%, in line with the prior three quarters.",
      ),
      p(
        "Notice what changed. Real numbers. Named movements. A driver you can trace to specific accounts. A miss disclosed plainly rather than buried under \"positive trends.\" A director reads this and can ask a sharper question — which is the point of commentary.",
      ),
      p(
        "The difference isn't writing quality. Both are grammatical. The difference is that the second one is *accountable to the numbers* and the first one floats free of them.",
      ),
      h2("Why generic commentary is a trust problem, not a style problem"),
      p(
        "It's tempting to treat fluffy commentary as a cosmetic issue — tighten the prose and move on. It's deeper than that.",
      ),
      p(
        'Vague commentary is often vague because the writer, human or AI, didn\'t actually reconcile the drivers. "Revenue was strong" can mean "I looked at the total and it was up" without anyone confirming *why*. When the explanation is generic, you usually can\'t tell whether the analysis underneath was rigorous or skipped entirely.',
      ),
      p(
        "That's the real danger with AI variance commentary. A language model will happily generate a confident explanation whether or not it's grounded in your actual figures. If the commentary isn't tied to reconciled numbers, it can assert a driver that the data doesn't support — and it'll do it in fluent, board-ready prose that's hard to spot as wrong. Fluency is not accuracy. The more polished the sentence, the more scrutiny the number behind it deserves.",
      ),
      p(
        "So the standard isn't a matter of taste. Specific, evidenced commentary is the observable signal that someone did the reconciliation. Generic commentary is the signal that maybe nobody did.",
      ),
      h2("AI drafts. A person signs."),
      p(
        "Here's the line that matters, and it doesn't move.",
      ),
      p(
        "AI can accelerate the writing. It can turn reconciled figures into a clean first draft, flag the biggest variances, and save your team the blank-page problem. That's genuine value, and finance teams should use it.",
      ),
      p(
        "What AI does not do is own the numbers. It doesn't replace your books, your ledger, or your accountability for what the board sees. The general ledger stays your system of record, owned by your team and your auditors. A model does not close the books and does not sign the pack — you do.",
      ),
      p(
        "That's why the useful role for AI in variance commentary is narrow and honest: draft from numbers that already exist and have already been reconciled, so the explanation reflects the actuals rather than inventing a story around them. The human reviews, corrects, and signs. The accountability never transfers to the tool. Any vendor implying otherwise is selling you a liability, not a feature.",
      ),
      h2("What this looks like with SMPL.ai"),
      p(
        "SMPL.ai reads and reconciles your source systems — billing, CRM, and the general ledger — into one governed operating model, and the AI narrative it generates is grounded in those reconciled outputs. The commentary explains the movements the model actually computed. It doesn't invent a number or assert a driver that isn't in the data.",
      ),
      p(
        "That grounding is what makes the output meet the standard above. Because every figure in the narrative carries its lineage back to source, the commentary is specific by default, evidenced by construction, and traceable when a director pushes on it. When the draft says expansion drove the quarter, that number ties to the same reconciled source as the rest of the pack — so you can defend it in the room.",
      ),
      p(
        "And SMPL doesn't write back to your ERP or general ledger. It reads from your systems of record; it never posts to them. Your books stay yours. The AI drafts the explanation; your team reviews and signs. That division of labor is the point — faster commentary, with accountability firmly where it belongs.",
      ),
      h2("See it on your own variances"),
      p(
        "The test worth running is simple: does the AI commentary name your actual drivers, cite your actual numbers, and hold up when someone asks where a figure came from?",
      ),
      p(
        "[Book a demo](https://www.smpl-ai.com/book-demo) and we'll generate variance commentary on data that looks like yours — so you can judge it against your own sign-off bar.",
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
    _id: "glossary-fpa",
    term: "FP&A",
    slug: "fpa",
    shortDefinition:
      "Financial Planning & Analysis — the finance function that plans, forecasts, and explains performance so leaders can decide with confidence.",
    body: blocks(
      "FP&A connects operating metrics (ARR, pipeline, headcount) with financial statements and cash so the company can plan, close, and report from one coherent model.",
      "SMPL is SaaS FP&A and financial intelligence for finance teams: unify ARR, board reporting, and the operating model so every board number is traceable to its source.",
    ),
  },
  {
    _id: "glossary-mda",
    term: "MD&A",
    slug: "mda",
    shortDefinition:
      "Management’s Discussion & Analysis — narrative explaining results, drivers, and outlook.",
    body: blocks(
      "MD&A should cite finalized period metrics and known variances. AI can draft structure; finance owns the signed narrative.",
    ),
  },
  {
    _id: "glossary-rolling-forecast",
    term: "Rolling forecast",
    slug: "rolling-forecast",
    shortDefinition:
      "A continuously updated outlook that blends year-to-date actuals with forward plan assumptions.",
    body: blocks(
      "Rolling forecasts help boards see actuals to date plus the remaining year without switching workbooks. Document which drivers change the forward slice each cycle.",
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
      "Pipeline informs outlook but should not silently rewrite closed ARR. Keep pipeline attribution separate from certified period metrics.",
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
      "Runway should use a clear burn definition (operating vs total cash). Present scenario runway next to the rolling forecast so boards see cash and growth outlook together.",
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
