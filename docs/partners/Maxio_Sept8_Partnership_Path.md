# Maxio × SMPL — Partnership path from the learn.maxio catalog

> **For:** Matt · Nick follow-up, 2026-09-08  
> **Source:** `backend/tmp/learn_maxio_catalog_parsed.json` — 56 course/webinar titles, catalog page only (logged in as Partner)  
> **Evidence limit:** Titles only. Course *bodies* were not captured (`course_hrefs` empty). Treat everything below as "the curriculum tells us X" — verify before asserting as fact in the room.  
> **Companions:** [Maxio_Partner_Meeting_Prep_Trust_Budget_PPI.md](./Maxio_Partner_Meeting_Prep_Trust_Budget_PPI.md) · [Maxio_Technical_Readiness_QA.md](./Maxio_Technical_Readiness_QA.md)

---

## 1. The catalog's loudest signal: MCP is a shipped, C-suite-marketed product

Five of the 56 assets are about Maxio MCP:

- AI in the C-Suite: Faster Decisions with MCP — **CEO** episode
- …**CFO** episode
- …**CPO** episode
- …**Head of Sales** episode
- How-To Video Series: Maxio MCP — CPO's working with MCP

**Why this matters more than anything else in the catalog:** the prep doc treats Advanced Billing site + API key as the data path, and lists "Core API / MCP scope?" as a soft ask. The catalog says MCP is not a curiosity — it is productized and being sold upward to the C-suite.

That does two things:

1. **It reopens the data path that stalled.** Credentials never landed. MCP is a route Maxio is actively promoting rather than gatekeeping, so it is worth asking about partner scope early. **Do not assume MCP is the durable warehouse-ingestion path** — it may be built primarily for governed queries and approved AI tasks rather than bulk repeatable loads. MCP, REST API and standardized exports are three candidates, and which one fits which use case is a question for the technical session.
2. **It is a foundation to build on, not a risk to point at.** Maxio markets MCP as governed and auditable. Calling it an ungoverned-answer risk would put Nick on the defensive in the first five minutes for no gain.

**Say this instead:**

> "Maxio MCP provides governed access to trusted recurring-revenue information. SMPL extends that foundation across the broader finance stack, runs deterministic planning and predictive analysis on it, and turns the resulting evidence into decision-ready explanations."

**Line:** "MCP governs the answer inside recurring revenue. We extend that across the GL, CRM and workforce, build the plan on it, test whether the plan can be delivered, and hand the CFO something board-ready."

---

## 2. The absence in the catalog is your actual opening

Across all 56 assets, the curriculum covers: implementation, core objects, data migration, importer, admin, e-invoicing, e-payments, A/R + DSO, Avalara, Anrok, Salesforce, QuickBooks, rev rec (101 + audit-ready), month-end close (core + complex), cohort reporting, metrics, quote-to-cash, projects, surcharging, self-service billing, product roadmap.

**What is not there — not one course:**

- No budgeting
- No planning or forecasting
- No board reporting or investor packages
- No variance or scenario modeling
- **No co-branded Abacum asset**, even though Anrok and Rillet each have one

Their metrics content is explicitly historical — "Beyond ARR," cohort reporting, "Master Your Metrics with Maxio Reporting." It stops at reporting what happened.

**The dots connect like this:** Maxio's own customer-education library ends exactly where SMPL begins. Their customers finish the Maxio curriculum with trustworthy actuals and no guidance on turning those actuals into a plan, a variance story, or a board packet. That is an enablement gap in their asset library, and it maps 1:1 to SMPL's surface area.

This is a much better way to make the customer-lane argument than an Abacum teardown — which the prep doc forbids anyway. You are not attacking a competitor. You are pointing at a hole in their content shelf and offering to fill it.

> **Verify before saying out loud:** the scrape captured the catalog page only and may be incomplete. Phrase as a question — *"I went through the catalog and didn't see planning or board content; am I missing a section?"* — not as an assertion. If Nick confirms it, he has made your argument for you.

### 2a. You can now fill that gap on screen — Plan Assurance shipped last week

The Aug 31 briefing told you to keep predictive work off the table. **That guidance is out of date.** Plan Assurance and the Budget Engine shipped 09-04 → 09-07: a 15-check feasibility strip, named stress cases, and 1,000-draw Monte Carlo — all running through the same formula graph that builds the plan, with the LLM narrating findings rather than computing dollars.

So the gap argument is no longer "here is a hole in your curriculum, trust me that we fill it." It is: their library ends at trustworthy actuals, and you can show, live, the layer that asks whether the plan built on those actuals can be delivered.

**Demo loop to use instead of the old Pipeline-only script:** Board (what happened) → Forecast (what's in motion) → Budget Analytics / Plan Assurance (can the FY plan deliver). The exec summary already carries a Plan Assurance hand-off band.

**Naming discipline still applies:** Monte Carlo output is stress frequency under stated priors, not calibrated Probability of Attainment. Show the simulation; do not rename it.

**Strongest single beat in the demo (shipped 09-08):** the monthly cash band. Each of the 1,000 draws retains its full twelve-month cash path, so you can show P10–P90 by month against the floor, name the tightest month, and contrast **P(any month below floor)** with **P(December below floor)**. A plan can end the year comfortably and still need financing mid-year — that is a question Maxio's reporting surface cannot ask, and it lands with a CFO immediately.

---

## 2b. Your strongest argument is the one the docs almost omit: SMPL does the implementation

This belongs in the top three partnership arguments, not in a footnote called "Path A white-glove load."

Every FP&A conversation in Maxio's base runs into the same wall: the finance team is two or three people, the need is real, and nobody has the capacity to implement and then administer a planning platform. That is not a feature objection — it is a labour objection, and it is the reason the lane exists.

**What to say:**

- **SMPL performs the implementation.** We stand up the environment.
- **The customer does not redesign its systems.** We take the existing stack and data largely as-is.
- **Maxio remains intact and central.** Nothing about their billing configuration changes.
- **Customer participation is validation and decision-making** — confirm mappings and definitions, approve the plan.
- **Standard Maxio configurations are a known shape**, so implementations on them could plausibly be packaged predictably.
- **Total cost includes far less internal finance labour and change management** than a self-administered platform.

**Why Nick should care:** it makes SMPL deployable to customers his current FP&A partner realistically cannot serve, without asking him to move anyone off anything.

**Honest limits:** native connectors are not GA — today is white-glove load. Packaged pricing is a direction, not a published SKU. No joint Maxio implementation yet.

**Line:** "Their team doesn't implement anything. We take the stack as it is — Maxio included — and build the environment. They validate and decide."

---

## 2c. The central story — use this framing in every conversation

> Maxio gives SaaS finance teams governed recurring-revenue actuals. SMPL takes those actuals together with the customer's GL, CRM and workforce information, **implements the financial environment**, builds the operating budget, evaluates the plan against historical performance, models the distribution of future cash outcomes, and turns the results into board-ready decision support. **Maxio remains the recurring-revenue foundation, and the customer does not have to undertake a major FP&A implementation.**

Four points, all load-bearing: Maxio stays central · SMPL expands Maxio across the business · Plan Assurance is demonstrable today · SMPL performs the implementation.

---

## 3. Maxio's partner playbook is visible — propose *their* stages, not an abstract partnership

Nick framed today as "is there a meaningful path." The catalog shows what a real Maxio partnership physically looks like, because completed ones leave artifacts:

| Stage | Artifact in the catalog | Examples |
|-------|------------------------|----------|
| Integration exists | `Maxio Core Implementation: <Partner>` module | Salesforce, QuickBooks, Avalara |
| Co-marketing | `Webinar: Maxio + <Partner>` | Anrok (12.4.25), Rillet ("Unified AI-Powered Finance Stack") |
| Partner enablement | `Maxio Core Essentials Certifications for Partners` | — |
| Advocacy / amplification | `Maxio Advocacy Program` | — |

**Rillet is the template to name.** "Maxio + Rillet: The Unified AI-Powered Finance Stack" is an AI-native ERP partner with a co-branded webinar. That is the shape of the outcome you want, and it gives Nick a precedent he already understands instead of a bespoke ask.

**Proposed path to put on the table (concrete, staged, low-risk for him):**

1. **Now** — you complete `Maxio Core Essentials Certifications for Partners` (you already have a Partner account). Costs him nothing, proves you're serious, and gives you real fluency in their objects before any technical session.
2. **Next** — SC / architecture session on Path A: Maxio-shaped billing exports → SMPL ARR waterfall with tie-out. Scoped so it does not depend on credentials.
3. **Then** — establish the right data path per use case: MCP for governed queries, API or standardized exports for repeatable loads. Decide it with their integrations people rather than assuming it.
4. **Proof** — one joint design-partner customer, **implemented by SMPL**, producing a board packet and a tested plan on Maxio actuals.
5. **Payoff** — co-branded webinar in the Rillet mold: *"From Maxio actuals to a board-ready plan."* Fills their curriculum gap and is a Maxio marketing asset, not just a SMPL one.

### 6a. The progression that earns preferred positioning

Do not skip steps. Each one buys the right to the next.

1. Validate the distinct customer lane.
2. Complete technical validation.
3. Run one joint design-partner implementation.
4. Produce measurable results.
5. *Then* earn preferred positioning.

---

## 4. Their AI-trust content is your thesis in their own words

Three assets, all recent:

- AI in Finance: **Connect AI Tools with Confidence**
- AI in Finance: **Spot Anomalies Before They Affect the Business**
- AI in Finance: **Use Cases That Actually Work**

Maxio has already taught its customers to be skeptical of ungoverned AI and to want anomaly detection and confidence. You do not have to sell the category — quote their curriculum back and position SMPL as the delivery of a promise they are already making. "Spot anomalies" in particular is your validation catalog described in marketing language.

---

## 5. Two smaller threads worth pulling

- **SaaS Capital webinar + B2B Growth Report + SaaSPedia.** Maxio partners with a SaaS lender and publishes benchmark content. You already pitch **debt covenant and investor reporting** — that is a direct, named tie to a partner motion they already run, and a second co-content angle.
- **Product Roadmap webinars (Spring + Summer 2026).** Asking "where does planning/FP&A sit on the roadmap you presented this summer?" is a cheap question that signals you did the work and surfaces whether they intend to build into your space.

---

## 6. Re-ranked asks for today

The prep doc's asks still hold; the catalog changes the order, and the Abacum ask is now retired for today.

1. **Validate the customer lane** — *"Does your base include growth companies with lean finance teams that want this capability but won't implement and administer an FP&A platform?"* This is the one ask that matters; everything else follows from a yes.
2. **Technical session date** — 45 minutes with partnerships, solutions consulting, and product/integrations. Agenda: which of MCP / API / exports fits which use case, data objects and reconciliation, joint customer profile, scope one design-partner implementation.
3. **Confirm the curriculum gap** — is there planning/board content I missed? If not, would co-built enablement content interest you?
4. **Partner certification** — confirm the right track for you to complete.
5. **MCP partner scope** — is there a partner path? *(Framed as a question about fit, not as the assumed pipe.)*
6. AB sandbox site + key — **soft, last**, explicitly not the unlock.

**Retired for today:** preferred / long-term / successor FI partner framing. That is the eventual ambition, and asking for it before a joint customer result puts Nick in the position of defending an existing relationship. Earn it in the order set out in §6a.

---

## 7. Discipline carried over — do not say

Unchanged from the prep doc: no live Maxio API pull, no SOC 2 report, no multi-user warehouse load locking, no customer logos, no Abacum feature matrix or win rates, no "we already replaced Abacum in production."

**Corrected 2026-09-08 — the old "no PPI / Monte Carlo / PoA" line is wrong now.** Plan Assurance and Monte Carlo stress analysis **can be demonstrated**, including the monthly P10–P90 cash band and the intra-year trough. What remains off-limits is the *label*: do not describe simulation breach frequency as calibrated Probability of Attainment. Two precisions that matter if an SC probes — annual levers are drawn **once per trial** and propagated through the months rather than resampled monthly, and the deep prior-year series is partly **backcast** rather than loaded actuals.

**Also do not:**

- Ask for preferred / successor partner status or suggest displacing Abacum (see §6).
- Assert MCP is the ingestion path before the technical session establishes it.
- Assert the curriculum gap as established fact — the scrape is catalog-level only. Ask it; let Nick confirm it.
- Quote a fixed implementation price or timeline — packaging is a direction, not a published SKU.
