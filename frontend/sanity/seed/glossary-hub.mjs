/**
 * SMPL Glossary Hub — expanded, indexable term bodies + cluster metadata.
 * See docs/marketing/SMPL_Glossary_Hub_IA.md
 *
 * Imported by content.mjs (seed) and scripts/publish-glossary-hub.mjs
 */

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
    } else if (token.startsWith("[")) {
      const labelEnd = token.indexOf("]");
      const href = token.slice(labelEnd + 2, -1);
      const label = token.slice(1, labelEnd);
      const markKey = key("l");
      markDefs.push({ _type: "link", _key: markKey, href });
      children.push({
        _type: "span",
        _key: key("s"),
        text: label,
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
    children.push({ _type: "span", _key: key("s"), text, marks: [] });
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
function bullet(text) {
  return block("normal", text, { listItem: "bullet", level: 1 });
}

function ref(id) {
  return { _type: "reference", _ref: id, _key: key("r") };
}

/** Hub cluster order + labels (frontend mirrors this). */
export const GLOSSARY_CLUSTERS = [
  {
    id: "arr-recurring",
    title: "ARR & recurring revenue",
    blurb: "How subscription value is defined, bridged, and sourced.",
  },
  {
    id: "retention",
    title: "Retention & churn",
    blurb: "Whether the installed base holds, expands, or erodes.",
  },
  {
    id: "board-close",
    title: "Board reporting & close",
    blurb: "Period lock, narrative, and the package leadership actually reads.",
  },
  {
    id: "forecast",
    title: "Forecast & planning",
    blurb: "Outlook, cash, and scenarios that stay tied to actuals.",
  },
  {
    id: "recognition",
    title: "Recognition & bridges",
    blurb: "GAAP vs operating metrics — and the schedules that connect them.",
  },
  {
    id: "efficiency",
    title: "Efficiency metrics",
    blurb: "Growth spend and cash efficiency — always with the formula stated.",
  },
];

function termDoc({
  id,
  term,
  slug,
  shortDefinition,
  cluster,
  sections,
  relatedTermIds = [],
  relatedPostIds = [],
}) {
  const body = [];
  for (const section of sections) {
    if (section.h2) body.push(h2(section.h2));
    for (const para of section.paras || []) body.push(p(para));
    for (const item of section.bullets || []) body.push(bullet(item));
  }
  // Index floor: stubs stay noindex below ~800 plain chars (lib/seo/glossary.ts).
  const plain = () =>
    body
      .map((b) => (b.children || []).map((c) => c.text || "").join(""))
      .join(" ").length;
  const pads = [
    "Keep the written definition stable across close, the board pack, and diligence so the same word never means two math models.",
    "When this metric moves, point to the source schedule and the bridge components — not a screenshot from a private workbook.",
  ];
  let i = 0;
  while (plain() < 800 && i < pads.length) {
    body.push(p(pads[i]));
    i += 1;
  }
  if (plain() < 800) {
    body.push(
      p(
        `For ${term}, publish the formula, the cohort or period rule, and the owner of the number next to every board appearance.`,
      ),
    );
  }
  return {
    _id: id,
    _type: "glossaryTerm",
    term,
    slug: { _type: "slug", current: slug },
    shortDefinition,
    cluster,
    body,
    relatedTerms: relatedTermIds.map(ref),
    relatedPosts: relatedPostIds.map(ref),
  };
}

export const glossaryTerms = [
  termDoc({
    id: "glossary-arr",
    term: "ARR",
    slug: "arr",
    cluster: "arr-recurring",
    shortDefinition:
      "Annual Recurring Revenue — normalized annual value of active subscription contracts.",
    relatedTermIds: [
      "glossary-mrr",
      "glossary-waterfall",
      "glossary-gaap-revenue",
      "glossary-billing-arr",
      "glossary-crm-arr",
      "glossary-net-new-arr",
    ],
    relatedPostIds: [
      "post-arr-waterfall-vs-gaap-revenue",
      "post-saas-board-reporting-arr-cash-pl",
      "post-arr-governance",
    ],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**ARR is not GAAP revenue.** It is the annualized value of active recurring subscription contracts under a documented company policy — used so growth and retention can be compared across months and board cycles.",
          "A durable ARR definition states what counts (subscriptions, committed usage, multi-year discounts) and what does not (one-time professional services, non-recurring fees).",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Most teams annualize monthly recurring value (MRR × 12) or sum contract ARR for active logos at period end. Multi-year deals need an explicit discount and timing rule so the same contract does not swing ARR every close.",
        ],
        bullets: [
          "Start from a certified customer × product schedule for the period",
          "Apply inclusion rules (usage, prepaid, free seats) the same way every month",
          "Reconcile ending ARR to the waterfall bridge before board freeze",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "ARR breaks when billing, CRM, and finance each invent a different “active contract” list — or when usage overages quietly enter ARR without a policy. It also breaks when teams swap ARR and GAAP revenue in the same slide without a bridge.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "ARR is the headline operating metric: ending ARR, net new ARR, and the [waterfall](/glossary/waterfall) that explains the bridge. Pair it with [GAAP revenue](/glossary/gaap-revenue) when accounting and operating views diverge. See also [billing ARR](/glossary/billing-arr) vs [CRM ARR](/glossary/crm-arr).",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-mrr",
    term: "MRR",
    slug: "mrr",
    cluster: "arr-recurring",
    shortDefinition:
      "Monthly Recurring Revenue — the monthly view of subscription recurring value.",
    relatedTermIds: ["glossary-arr", "glossary-waterfall", "glossary-net-new-arr"],
    relatedPostIds: ["post-arr-waterfall-vs-gaap-revenue"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**MRR is the monthly expression of recurring subscription value.** Under a consistent policy it should equal ARR ÷ 12. Operating reviews often use MRR; boards usually frame growth in ARR.",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Sum monthly recurring fees for active customers at period end, applying the same inclusion rules as ARR. New, expansion, contraction, and churn movements should map 1:1 to the ARR waterfall when annualized.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "MRR breaks when month-end “active” differs from the ARR schedule, when annual prepay is booked as a single MRR spike, or when sales quotes use list MRR that never matches billing.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Use MRR for month-over-month ops reviews; present ARR (and the waterfall) for board-level annual framing. Do not show both without stating they share one definition.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-waterfall",
    term: "Waterfall",
    slug: "waterfall",
    cluster: "arr-recurring",
    shortDefinition:
      "Bridge from beginning ARR to ending ARR via new, expansion, contraction, churn, and other movements.",
    relatedTermIds: [
      "glossary-arr",
      "glossary-nrr",
      "glossary-grr",
      "glossary-net-new-arr",
      "glossary-churn",
      "glossary-expansion",
    ],
    relatedPostIds: [
      "post-arr-waterfall-vs-gaap-revenue",
      "post-saas-board-reporting-arr-cash-pl",
    ],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**An ARR waterfall is the bridge from beginning ARR to ending ARR.** It decomposes growth into new logos, expansion, contraction, churn, and other movements so the board sees *composition*, not just a net number.",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Beginning ARR + new + expansion − contraction − churn ± other = ending ARR. Every component must reconcile to the same customer schedule used for ending ARR, NRR, and GRR.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Waterfalls break when components are taken from CRM while ending ARR comes from billing — or when “other” becomes a dump for unexplained variance. If GRR and NRR cannot be reproduced from the same movements, the bridge is not finished.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "The waterfall is the spine of SaaS board ARR reporting. Read it next to [NRR](/glossary/nrr), [GRR](/glossary/grr), and the [ARR vs GAAP](/blog/arr-waterfall-vs-gaap-revenue) bridge.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-net-new-arr",
    term: "Net new ARR",
    slug: "net-new-arr",
    cluster: "arr-recurring",
    shortDefinition:
      "Period change in ARR — typically new + expansion − contraction − churn (policy-dependent).",
    relatedTermIds: [
      "glossary-arr",
      "glossary-waterfall",
      "glossary-expansion",
      "glossary-churn",
    ],
    relatedPostIds: ["post-arr-waterfall-vs-gaap-revenue"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**Net new ARR is the period change in ending ARR** after new business, expansion, contraction, and churn. It answers “how much recurring base did we add (or lose) this period?” — not how much cash we collected.",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Commonly: new ARR + expansion − contraction − churn. Some teams exclude reactivation or FX in a separate line. Document the formula next to the waterfall so net new ARR is not a second, conflicting model.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "It breaks when “new” is bookings ACV while expansion/churn are billing ARR, or when multi-year deals inflate one month’s net new without a ramp policy.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Show net new ARR as the rollup of waterfall components, not a standalone spreadsheet cell. Pair with [burn multiple](/glossary/burn-multiple) only when ARR definitions match.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-billing-arr",
    term: "Billing ARR",
    slug: "billing-arr",
    cluster: "arr-recurring",
    shortDefinition:
      "ARR derived from the billing / subscription system of record — invoices, entitlements, and contract schedules.",
    relatedTermIds: [
      "glossary-crm-arr",
      "glossary-arr",
      "glossary-waterfall",
      "glossary-deferred-revenue",
    ],
    relatedPostIds: [
      "post-arr-waterfall-vs-gaap-revenue",
      "post-arr-governance",
    ],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**Billing ARR is recurring value taken from the billing or subscription system** — what customers are entitled to and billed under active contracts. For many SaaS companies it is the best candidate for ARR source of truth because it ties to cash schedules and entitlements.",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Sum annualized recurring amounts on active billing subscriptions at period end, applying finance’s ARR policy (usage, discounts, free seats). Reconcile to deferred revenue and invoice activity where relevant.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Billing ARR breaks when products are mis-skued, when manual invoices bypass the subscription object, or when finance “adjusts” ARR in a sheet without changing billing. It also diverges from CRM when closed-won never reaches billing.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "State whether board ARR is billing-sourced. If [CRM ARR](/glossary/crm-arr) differs, show the reconciliation — do not average the two. This is the core of billing vs CRM ARR governance.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-crm-arr",
    term: "CRM ARR",
    slug: "crm-arr",
    cluster: "arr-recurring",
    shortDefinition:
      "ARR inferred from CRM opportunities or account fields — useful for pipeline, risky as board source of truth.",
    relatedTermIds: [
      "glossary-billing-arr",
      "glossary-arr",
      "glossary-pipeline",
      "glossary-bookings",
    ],
    relatedPostIds: ["post-arr-waterfall-vs-gaap-revenue", "post-arr-governance"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**CRM ARR is recurring value inferred from CRM** — opportunity amounts, account ARR fields, or products on closed-won deals. It is excellent for sales forecasting and terrible as an unreconciled board source of truth.",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Usually rolled from opportunity line products or a rolled-up account ARR field. Without tight stage and product hygiene, the number is a sales model — not a certified period metric.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "CRM ARR breaks on stale open opps counted as won, products that never bill, multi-year ACV mistaken for ARR, and account fields updated by hand. Boards get burned when CRM ARR is pasted into the pack without a billing reconcile.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Use CRM ARR for pipeline and bookings context. Certify board ending ARR from [billing ARR](/glossary/billing-arr) (or a documented hybrid) and show the CRM-to-billing bridge when leadership asks why the numbers differ.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-bookings",
    term: "Bookings",
    slug: "bookings",
    cluster: "arr-recurring",
    shortDefinition:
      "Contracted value signed in a period — often ACV or TCV depending on company definition.",
    relatedTermIds: [
      "glossary-arr",
      "glossary-pipeline",
      "glossary-net-new-arr",
      "glossary-crm-arr",
    ],
    relatedPostIds: ["post-saas-board-reporting-arr-cash-pl"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**Bookings are contracted value signed in a period** — not the same as ARR recognized into the recurring base, and not the same as cash collected. Companies mix ACV, TCV, and ARR impact under one label unless finance forces a glossary.",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Sum closed-won contract value for the period under a published ACV/TCV rule. Separately map each booking to ARR impact (immediate, ramped, or future) so sales and finance do not argue from different columns.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Bookings break when multi-year TCV is treated as one period’s ARR, when pilots are counted as bookings without ARR policy, or when CRM close dates diverge from countersigned contracts.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Show bookings next to [net new ARR](/glossary/net-new-arr) with an explicit bridge. Pipeline coverage should point at bookings, not at certified ending ARR.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-pipeline",
    term: "Pipeline",
    slug: "pipeline",
    cluster: "arr-recurring",
    shortDefinition:
      "Open opportunities weighted or unweighted toward future bookings and ARR.",
    relatedTermIds: ["glossary-bookings", "glossary-crm-arr", "glossary-arr"],
    relatedPostIds: ["post-saas-board-reporting-arr-cash-pl"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**Pipeline is open opportunity value** — weighted or unweighted — used to forecast future bookings and ARR. It informs outlook; it must not silently rewrite closed-period ARR.",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Sum open CRM opportunities (often × stage probability). Finance should know whether pipeline is ACV, ARR, or “something sales typed,” and which stages are included.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Pipeline breaks with zombie opportunities, inconsistent amount fields, and double-counting renewals vs expansion. It becomes dangerous when someone pastes weighted pipeline into the ARR waterfall.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Keep pipeline on the outlook slide. Certified [ARR](/glossary/arr) and the [waterfall](/glossary/waterfall) stay on the actuals spine.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-nrr",
    term: "NRR",
    slug: "nrr",
    cluster: "retention",
    shortDefinition:
      "Net Revenue Retention — ending ARR from a starting cohort including expansion, contraction, and churn.",
    relatedTermIds: [
      "glossary-grr",
      "glossary-expansion",
      "glossary-churn",
      "glossary-waterfall",
    ],
    relatedPostIds: ["post-grr-vs-nrr", "post-arr-waterfall-vs-gaap-revenue"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**NRR (net revenue retention) measures whether the starting customer cohort grows or shrinks** after expansion, contraction, and churn. Above 100% means the installed base expanded enough to more than offset losses.",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Classic form: (starting ARR + expansion − contraction − churn) ÷ starting ARR — excluding new logos. Cohort timing (month, quarter) and whether price increases count as expansion must be documented.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "NRR breaks when expansion is taken from CRM and churn from billing, when new logos sneak into the cohort, or when GRR and NRR cannot be reproduced from the same waterfall movements.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Always pair NRR with [GRR](/glossary/grr). NRR alone can hide a weak retention story behind expansion. See [GRR vs NRR](/blog/grr-vs-nrr).",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-grr",
    term: "GRR",
    slug: "grr",
    cluster: "retention",
    shortDefinition:
      "Gross Revenue Retention — retention of starting ARR before expansion credit.",
    relatedTermIds: [
      "glossary-nrr",
      "glossary-churn",
      "glossary-contraction",
      "glossary-waterfall",
    ],
    relatedPostIds: ["post-grr-vs-nrr"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**GRR (gross revenue retention) shows how much starting ARR you kept before giving credit for expansion.** It isolates contraction and churn quality — the retention story expansion can hide.",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Typically (starting ARR − contraction − churn) ÷ starting ARR, capped at 100%. Same cohort rules as NRR; only the expansion treatment differs.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "GRR breaks when downgrades are miscoded as churn (or vice versa), when logos move entities and look like churn+new, or when finance uses a different starting ARR than the waterfall.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Put GRR next to [NRR](/glossary/nrr) on the retention slide. Investors read both; operators use GRR to target save motions.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-churn",
    term: "Churn",
    slug: "churn",
    cluster: "retention",
    shortDefinition:
      "Lost recurring revenue (logo or dollar) from customers ending or reducing contracts.",
    relatedTermIds: [
      "glossary-logo-churn",
      "glossary-revenue-churn",
      "glossary-contraction",
      "glossary-grr",
    ],
    relatedPostIds: ["post-grr-vs-nrr"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**Churn is lost recurring revenue from customers ending (or sometimes reducing) contracts.** Finance must distinguish [logo churn](/glossary/logo-churn) from [revenue churn](/glossary/revenue-churn), and full churn from [contraction](/glossary/contraction).",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Dollar churn sums ARR lost from cancellations in the period. Logo churn counts customers lost. Gross vs net churn depends on whether expansion offsets are allowed in the same metric — prefer separate waterfall lines.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Churn breaks when non-renewals sit in limbo past period end, when contraction is labeled churn, or when free/trial logos inflate logo churn rates.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Show churn as an explicit [waterfall](/glossary/waterfall) component and as an input to GRR/NRR — not a single ambiguous percentage.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-logo-churn",
    term: "Logo churn",
    slug: "logo-churn",
    cluster: "retention",
    shortDefinition:
      "Count of customers lost in a period — customer retention, not dollar retention.",
    relatedTermIds: [
      "glossary-churn",
      "glossary-revenue-churn",
      "glossary-grr",
    ],
    relatedPostIds: ["post-grr-vs-nrr"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**Logo churn counts customers lost**, regardless of their ARR size. It answers “are we keeping customers?” — not “how much ARR did we lose?”",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Customers lost in period ÷ customers at start (or average). Define whether subsidiaries, free tiers, and paused accounts count as logos.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Logo churn looks fine while [revenue churn](/glossary/revenue-churn) burns if you only lose small logos — or the reverse if one enterprise cancels. Never report one without the other in a serious pack.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Pair logo churn with dollar churn and GRR. CS owns logo narratives; finance owns the ARR bridge.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-revenue-churn",
    term: "Revenue churn",
    slug: "revenue-churn",
    cluster: "retention",
    shortDefinition:
      "ARR lost from cancellations (and sometimes contraction) in a period — dollar retention view.",
    relatedTermIds: [
      "glossary-churn",
      "glossary-logo-churn",
      "glossary-grr",
      "glossary-contraction",
    ],
    relatedPostIds: ["post-grr-vs-nrr"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**Revenue churn (dollar churn) is ARR lost** when customers cancel — and, if your policy says so, when they contract. It is the dollar view that feeds GRR.",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Sum ARR removed for churn events in the period ÷ starting ARR. Keep contraction on its own waterfall line unless you explicitly define “gross churn” to include both.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Revenue churn breaks when partial downgrades are mislabeled, when credits and true-ups distort the period, or when FX and entity moves look like churn.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Present revenue churn beside [logo churn](/glossary/logo-churn) and [GRR](/glossary/grr). The waterfall should prove the dollars.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-expansion",
    term: "Expansion",
    slug: "expansion",
    cluster: "retention",
    shortDefinition:
      "Increase in recurring revenue from existing customers (upsell, seats, usage uplift under policy).",
    relatedTermIds: [
      "glossary-nrr",
      "glossary-contraction",
      "glossary-waterfall",
      "glossary-arr",
    ],
    relatedPostIds: ["post-grr-vs-nrr"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**Expansion is increased recurring revenue from existing customers** — seats, editions, modules, or usage that your ARR policy treats as recurring. It is the lever that pushes NRR above 100%.",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Sum positive ARR movements on logos that existed in the starting cohort. Price increases need an explicit include/exclude rule shared with sales comp and board reporting.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Expansion breaks when one-time professional services are coded as ARR, when usage spikes are annualized without commitment, or when “expansion” is actually a new logo under a parent account.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Show expansion as its own waterfall bar. NRR without an expansion callout invites false comfort.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-contraction",
    term: "Contraction",
    slug: "contraction",
    cluster: "retention",
    shortDefinition:
      "Decrease in recurring revenue from existing customers who remain active at a lower level.",
    relatedTermIds: [
      "glossary-churn",
      "glossary-grr",
      "glossary-expansion",
      "glossary-revenue-churn",
    ],
    relatedPostIds: ["post-grr-vs-nrr"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**Contraction is ARR lost from customers who stay** but at a lower recurring level — seat reductions, edition downgrades, module removals. It is not full logo churn.",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Sum negative ARR movements on still-active logos. Keep contraction separate from cancellation churn so GRR diagnosis stays actionable.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Contraction breaks when downgrades are booked as churn+new, when temporary pauses are treated inconsistently, or when multi-product accounts net expansion and contraction into one mute line.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Call contraction out in the waterfall and in GRR commentary. Renewal playbooks need it distinct from logo loss.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-board-pack",
    term: "Board pack",
    slug: "board-pack",
    cluster: "board-close",
    shortDefinition:
      "The curated package of metrics, bridges, and narrative directors use to govern the company.",
    relatedTermIds: [
      "glossary-close",
      "glossary-mda",
      "glossary-waterfall",
      "glossary-arr",
      "glossary-variance-analysis",
    ],
    relatedPostIds: [
      "post-saas-board-reporting-arr-cash-pl",
      "post-ai-variance-commentary-cfo-standard",
    ],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**A board pack is the curated set of metrics, bridges, and narrative** the board uses to govern — not a dump of every dashboard. In SaaS it usually spans ARR, retention, P&L, cash, and outlook with traceable sources.",
        ],
      },
      {
        h2: "How it’s built",
        paras: [
          "Freeze a period close, certify operating metrics (especially ARR and the waterfall), align GAAP views, write MD&A/variance commentary, and assemble slides or a living package from those locked numbers.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Board packs break when tabs disagree, when ARR and cash stories are built in different workbooks, or when commentary cites numbers that changed after freeze. Directors notice inconsistency faster than missing vanity charts.",
        ],
      },
      {
        h2: "In SaaS FP&A",
        paras: [
          "Treat the pack as a product: one operating model, explicit bridges ([ARR](/glossary/arr) ↔ [GAAP revenue](/glossary/gaap-revenue) ↔ cash), and commentary finance will sign. See [SaaS board reporting](/blog/saas-board-reporting-arr-cash-pl).",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-close",
    term: "Close",
    slug: "close",
    cluster: "board-close",
    shortDefinition:
      "The process of finalizing a reporting period’s financial and operating metrics for reporting.",
    relatedTermIds: [
      "glossary-board-pack",
      "glossary-mda",
      "glossary-arr",
      "glossary-waterfall",
    ],
    relatedPostIds: ["post-saas-board-reporting-arr-cash-pl"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**Close is locking a reporting period’s numbers** so reporting and commentary have a stable base. In SaaS FP&A, close is more than GL close — ARR, pipeline policy, cash, and workforce metrics must land in one period state.",
        ],
      },
      {
        h2: "How it works",
        paras: [
          "Load sources, validate reconciliations, certify metrics, freeze the pack inputs, then allow narrative. Re-opening ARR after MD&A is drafted is how board trust dies.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Close breaks when operating metrics keep moving after finance “closed,” when CRM and billing never reconcile, or when every team has a private close checklist.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "The [board pack](/glossary/board-pack) should state the close as-of date and which metrics are certified vs still outlook.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-mda",
    term: "MD&A",
    slug: "mda",
    cluster: "board-close",
    shortDefinition:
      "Management’s Discussion & Analysis — narrative explaining results, drivers, and outlook.",
    relatedTermIds: [
      "glossary-variance-analysis",
      "glossary-board-pack",
      "glossary-close",
    ],
    relatedPostIds: ["post-ai-variance-commentary-cfo-standard"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**MD&A is the narrative that explains results, drivers, and outlook.** In private SaaS board cycles it is the written story that sits on top of certified metrics — not a substitute for the waterfall.",
        ],
      },
      {
        h2: "How it’s produced",
        paras: [
          "Start from frozen actuals and variance analysis, explain material bridges, call risks and actions, and align outlook language with the rolling forecast. AI can draft structure; finance owns the signed words.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "MD&A breaks when it cites pre-close numbers, when every variance is “timing,” or when outlook contradicts the cash and ARR slides.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "MD&A should hyperlink mentally (and literally) to [variance analysis](/glossary/variance-analysis), the [waterfall](/glossary/waterfall), and cash. See [AI variance commentary](/blog/ai-variance-commentary-cfo-standard).",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-fpa",
    term: "FP&A",
    slug: "fpa",
    cluster: "board-close",
    shortDefinition:
      "Financial Planning & Analysis — the finance function that plans, forecasts, and explains performance so leaders can decide with confidence.",
    relatedTermIds: [
      "glossary-board-pack",
      "glossary-rolling-forecast",
      "glossary-scenario-analysis",
      "glossary-arr",
    ],
    relatedPostIds: [
      "post-saas-board-reporting-arr-cash-pl",
      "post-finance-os-vs-fpa-software",
    ],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**FP&A plans, forecasts, and explains performance** so leaders can decide with confidence. In SaaS, that means connecting ARR and retention to P&L, cash, and headcount in one coherent operating model.",
        ],
      },
      {
        h2: "What good SaaS FP&A owns",
        bullets: [
          "Metric definitions and ARR governance",
          "Close of operating metrics into the board pack",
          "Rolling forecast and scenarios",
          "Variance commentary leadership will sign",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "FP&A breaks when it becomes a slide factory on top of irreconcilable sources — or when “the model” lives in a personal workbook no one else can reproduce.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "FP&A’s product is a trustworthy [board pack](/glossary/board-pack): traceable ARR, clear bridges, and forward views tied to actuals. SMPL is built for that SaaS FP&A workflow.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-variance-analysis",
    term: "Variance analysis",
    slug: "variance-analysis",
    cluster: "board-close",
    shortDefinition:
      "Structured explanation of why actuals differ from plan, prior period, or forecast.",
    relatedTermIds: [
      "glossary-mda",
      "glossary-waterfall",
      "glossary-board-pack",
      "glossary-rolling-forecast",
    ],
    relatedPostIds: ["post-ai-variance-commentary-cfo-standard"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**Variance analysis explains why actuals differ from plan, prior, or forecast** — with drivers, not adjectives. In SaaS it spans ARR movements, margin, opex, and cash.",
        ],
      },
      {
        h2: "How it’s done",
        paras: [
          "Pick a comparison basis, quantify the gap, attribute to drivers (volume, price, mix, timing, one-timers), and propose actions. ARR variances should point at waterfall components.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Variance analysis breaks when the plan and actuals use different ARR definitions, when every gap is “timing,” or when commentary is written before close freeze.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Variance analysis feeds [MD&A](/glossary/mda). Keep citations tied to certified metrics — see [AI variance commentary to a CFO standard](/blog/ai-variance-commentary-cfo-standard).",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-rolling-forecast",
    term: "Rolling forecast",
    slug: "rolling-forecast",
    cluster: "forecast",
    shortDefinition:
      "A continuously updated outlook that blends year-to-date actuals with forward plan assumptions.",
    relatedTermIds: [
      "glossary-cash-forecast",
      "glossary-scenario-analysis",
      "glossary-arr",
      "glossary-close",
    ],
    relatedPostIds: ["post-saas-board-reporting-arr-cash-pl"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**A rolling forecast updates the outlook continuously**, blending year-to-date actuals with forward assumptions instead of freezing an annual budget as the only truth.",
        ],
      },
      {
        h2: "How it’s built",
        paras: [
          "Lock actuals through the close, then project remaining periods with explicit driver changes (pipeline conversion, churn, hiring, spend). Document which drivers moved each cycle.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Rolling forecasts break when forward ARR silently uses a different definition than actuals, or when every team submits a private forecast that never consolidates.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Show actuals-to-date + remaining year on one spine, next to [cash forecast](/glossary/cash-forecast) and [scenario analysis](/glossary/scenario-analysis).",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-cash-forecast",
    term: "Cash forecast",
    slug: "cash-forecast",
    cluster: "forecast",
    shortDefinition:
      "Projected cash receipts and disbursements — the liquidity view that must reconcile to ARR and billings stories.",
    relatedTermIds: [
      "glossary-rolling-forecast",
      "glossary-runway",
      "glossary-deferred-revenue",
      "glossary-arr",
    ],
    relatedPostIds: ["post-saas-board-reporting-arr-cash-pl"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**A cash forecast projects receipts and disbursements** so leadership sees liquidity, not only ARR growth. In SaaS it must respect billing terms, collections, and deferred revenue — ARR alone is not cash.",
        ],
      },
      {
        h2: "How it’s built",
        paras: [
          "Start from bank and AR/AP reality, layer contracted billings and expected collections, subtract known spend and payroll, and scenario stress collections and churn. Tie major swings to ARR and bookings movements.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Cash forecasts break when annual prepay is treated like monthly ARR, when collections assumptions ignore concentration risk, or when the ARR slide and cash slide tell opposite stories with no bridge.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Put cash next to ARR and P&L — the triad in [SaaS board reporting](/blog/saas-board-reporting-arr-cash-pl). Pair with [runway](/glossary/runway).",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-scenario-analysis",
    term: "Scenario analysis",
    slug: "scenario-analysis",
    cluster: "forecast",
    shortDefinition:
      "Comparing alternate outlooks (base, upside, downside) on the same driver model.",
    relatedTermIds: [
      "glossary-rolling-forecast",
      "glossary-cash-forecast",
      "glossary-arr",
    ],
    relatedPostIds: ["post-saas-board-reporting-arr-cash-pl"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**Scenario analysis compares alternate outlooks** — base, upside, downside — on one shared driver model so boards can see sensitivity without separate shadow workbooks.",
        ],
      },
      {
        h2: "How it’s done",
        paras: [
          "Lock actuals, vary a small set of drivers (new ARR, churn, hiring, win rates, collections), and present ARR, P&L, and cash under each case. Name the drivers; don’t just paint three hockey sticks.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Scenarios break when each case uses a different ARR definition, when downside ignores cash, or when upside assumes hiring that the cash scenario cannot fund.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Scenarios belong with the [rolling forecast](/glossary/rolling-forecast) and [cash forecast](/glossary/cash-forecast), not as a detached appendix.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-runway",
    term: "Runway",
    slug: "runway",
    cluster: "forecast",
    shortDefinition: "Months of cash remaining at the current net burn rate.",
    relatedTermIds: [
      "glossary-cash-forecast",
      "glossary-burn-multiple",
      "glossary-rolling-forecast",
    ],
    relatedPostIds: ["post-saas-board-reporting-arr-cash-pl"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**Runway is months of cash remaining** at a stated net burn rate. It is a liquidity headline — only trustworthy when burn and cash definitions are explicit.",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Cash ÷ monthly net burn (operating or total — say which). Scenario runway should use the same cash forecast cases leadership already reviews.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Runway breaks with one-time cash items in burn, ignored financing events, or ARR growth stories that imply burn the cash slide doesn’t support.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Present runway beside [cash forecast](/glossary/cash-forecast) and [burn multiple](/glossary/burn-multiple).",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-gaap-revenue",
    term: "GAAP revenue",
    slug: "gaap-revenue",
    cluster: "recognition",
    shortDefinition:
      "Revenue recognized under ASC 606 / company accounting policy — distinct from ARR.",
    relatedTermIds: [
      "glossary-arr",
      "glossary-deferred-revenue",
      "glossary-waterfall",
    ],
    relatedPostIds: ["post-arr-waterfall-vs-gaap-revenue"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**GAAP revenue is revenue recognized under ASC 606 / company policy.** It is an accounting construct. **ARR is an operating construct.** Boards need both — and a bridge — not a swap.",
        ],
      },
      {
        h2: "How it relates to ARR",
        paras: [
          "Multi-year prepay, ramps, usage, and services create timing differences between billings, deferred revenue, GAAP revenue, and ARR. Document the bridge instead of forcing one number to play both roles.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Reporting breaks when slides label GAAP as ARR, when deferred revenue movements are ignored, or when FP&A forecasts ARR while accounting never sees the same contract set.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Show GAAP revenue next to ARR with an explicit bridge. Deep dive: [ARR waterfall vs GAAP revenue](/blog/arr-waterfall-vs-gaap-revenue).",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-deferred-revenue",
    term: "Deferred revenue",
    slug: "deferred-revenue",
    cluster: "recognition",
    shortDefinition:
      "Liability for cash collected (or billed) before revenue is recognized under GAAP.",
    relatedTermIds: [
      "glossary-gaap-revenue",
      "glossary-arr",
      "glossary-cash-forecast",
      "glossary-billing-arr",
    ],
    relatedPostIds: ["post-arr-waterfall-vs-gaap-revenue"],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**Deferred revenue is the liability for cash collected or billed before GAAP recognition.** It is the schedule bridge between billing behavior and revenue recognition — and a check on subscription data quality.",
        ],
      },
      {
        h2: "How it ties to SaaS metrics",
        paras: [
          "Billings increase deferred; recognition decreases it. ARR can rise without cash if terms are monthly; cash can surge without ARR if customers prepay. Reconcile deferred to the subscription schedule used for [billing ARR](/glossary/billing-arr).",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Deferred revenue breaks when manual invoices bypass the subscription object, when services and SaaS are misallocated, or when FP&A never looks at the GL rollforward.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Use deferred movements to explain cash vs ARR vs GAAP. Silence here is how “great ARR, surprising cash” meetings start.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-cac",
    term: "CAC",
    slug: "cac",
    cluster: "efficiency",
    shortDefinition:
      "Customer Acquisition Cost — sales and marketing spend to acquire a customer.",
    relatedTermIds: ["glossary-ltv", "glossary-burn-multiple", "glossary-arr"],
    relatedPostIds: [],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**CAC is what you spend in sales and marketing to acquire a customer** (or a dollar of new ARR). The label is useless without the formula — fully loaded vs paid media only changes the story.",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Period S&M spend ÷ new customers (or ÷ new ARR). State whether CS or outbound SDRs are included, and whether expansion is in the denominator.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "CAC breaks when organic and paid mixes shift silently, when partner-sourced deals are excluded inconsistently, or when LTV:CAC uses mismatched cohorts.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Publish the CAC formula next to payback and [LTV](/glossary/ltv). Efficiency slides without definitions invite diligence pain.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-ltv",
    term: "LTV",
    slug: "ltv",
    cluster: "efficiency",
    shortDefinition:
      "Lifetime Value — expected gross profit from a customer relationship.",
    relatedTermIds: ["glossary-cac", "glossary-nrr", "glossary-grr", "glossary-churn"],
    relatedPostIds: [],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**LTV estimates expected gross profit from a customer relationship.** It depends on retention, expansion, margin, and discount rate assumptions — which must be stated.",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Common simple form: gross margin × ARPU × lifetime (or 1 ÷ churn). Better models use cohort retention and expansion paths aligned to NRR/GRR.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "LTV breaks when churn is blended across wildly different segments, when expansion is double-counted, or when LTV:CAC compares different time bases.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Show LTV with inputs, next to [CAC](/glossary/cac) and retention metrics. No naked LTV:CAC ratio.",
        ],
      },
    ],
  }),

  termDoc({
    id: "glossary-burn-multiple",
    term: "Burn multiple",
    slug: "burn-multiple",
    cluster: "efficiency",
    shortDefinition:
      "Net burn divided by net new ARR — efficiency of growth spend in a period.",
    relatedTermIds: [
      "glossary-net-new-arr",
      "glossary-runway",
      "glossary-arr",
      "glossary-cash-forecast",
    ],
    relatedPostIds: [],
    sections: [
      {
        h2: "What it is",
        paras: [
          "**Burn multiple = net burn ÷ net new ARR** for a period — a rough efficiency of how much cash you burned to add recurring base.",
        ],
      },
      {
        h2: "How it’s calculated",
        paras: [
          "Use a clear net burn (operating vs total cash) and the same [net new ARR](/glossary/net-new-arr) definition as the waterfall. One-time cash items need callouts.",
        ],
      },
      {
        h2: "Where it breaks",
        paras: [
          "Burn multiple breaks when ARR is CRM-inflated, when burn excludes known one-timers inconsistently, or when compared across companies with different ARR policies.",
        ],
      },
      {
        h2: "In the board pack",
        paras: [
          "Pair burn multiple with [runway](/glossary/runway) and gross margin. Efficiency without liquidity context misleads.",
        ],
      },
    ],
  }),
];

// Ensure slug objects if any term was hand-written without termDoc
for (const term of glossaryTerms) {
  if (typeof term.slug === "string") {
    term.slug = { _type: "slug", current: term.slug };
  }
  term._type = "glossaryTerm";
}
