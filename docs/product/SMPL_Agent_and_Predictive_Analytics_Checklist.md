# SMPL — Support Agent Path + Predictive Analytics Checklist

Internal working checklist. Captures the phased Slack/ops agent path (as pasted) and predictive analytics (lever-aware scenario intelligence) milestones from product discussion. **Docs/checklist only — not an implementation plan commitment.**

**Last updated:** 2026-08-11

---

## Principles (non-negotiable)

- [ ] **No GL write-back** — agent does not post to customer GL/ERP
- [ ] **No silent ARR / metric definition changes** — definition edits require approval workflow; never prod changes via chat alone
- [ ] **Steal the dispute pattern, not the CX vertical** — auth → pull SoR/evidence → apply *our* policy → resolve where work happens (SMPL); do not build a Salesforce dispute bot
- [ ] **Tenant isolation on every tool call** — per-company = one Slack workspace ↔ one SMPL tenant; tools never cross tenants
- [ ] **Individual = identity + RBAC** — not one shared “company bot” that can do anything
- [ ] **Fail closed** when evidence/sources are missing (esp. Phase 0 answers)
- [ ] **Audit everything** — who asked, what tool, what changed (or was proposed)

---

## Architecture

```
Slack (or Teams)
    → SMPL Agent Gateway (auth: Slack user ↔ tenant user/role)
        → Tool layer (strict allowlist)
            • read_freeze / query_metrics
            • get_job_status / retry_job
            • draft_definition_change
            • enqueue_deck_regen
            • list_recon_exceptions
        → Policy layer (tenant definitions + who can approve)
        → Audit log (who asked, what tool, what changed)
```

### Architecture checklist

- [ ] Slack (or Teams) app entry point
- [ ] **SMPL Agent Gateway** — map Slack user ↔ tenant user/role
- [ ] **Tool layer** — strict allowlist only
- [ ] **Policy layer** — tenant definitions + approvers
- [ ] **Audit log** — who / what tool / what changed
- [ ] Tenant isolation enforced on every tool call
- [ ] RBAC checked before any write or propose-apply path

### Initial tool allowlist (target)

- [ ] `read_freeze` / `query_metrics`
- [ ] `get_job_status` / `retry_job`
- [ ] `draft_definition_change`
- [ ] `enqueue_deck_regen`
- [ ] `list_recon_exceptions`

---

# Part 1 — Support agent path

Tenant-scoped **ops + trusted Q&A** agent (not a generic chatbot). Pattern: read → propose → allowlisted apply. Same dispute-agent pattern applied to **reporting ops**, not CX.

## Phase 0 — Read-only “support in Slack” (safest, still impressive)

*This is Copilot + status tools, in Slack.*

- [ ] Slack app installed per workspace, mapped to **one** SMPL tenant
- [ ] Commands / mentions supported, e.g.:
  - [ ] “Why did ARR move?”
  - [ ] “Status of last ingest?”
  - [ ] “What’s our ARR definition?”
- [ ] Answers **only** from freeze + docs + job logs
- [ ] Cite sources on every answer
- [ ] Fail closed if evidence missing
- [ ] No write actions in this phase

## Phase 1 — Propose, don’t apply

- [ ] “Regenerate MD&A deck for July freeze” → creates a **draft** job, posts link to review in SMPL
- [ ] “This customer mapped wrong” → opens a **suggested mapping change** for approval
- [ ] “Add expansion = seats × price” → drafts **definition diff** for admin approve
- [ ] Nothing applies without human approval in SMPL

## Phase 2 — Constrained write actions

Allowlisted tools only, with role checks:

- [ ] Retry failed ingest
- [ ] Re-run deck generation from freeze `X`
- [ ] Toggle a feature flag / clear a stuck job
- [ ] Still **no** GL write-back
- [ ] Still **no** silent ARR definition prod changes without approval workflow

## Phase 3 — “Resolution where it happens” (dispute analogy)

Only where **SMPL is the system of action**:

- [ ] Dispute-like: “Board pack wrong” → auth → pull freeze → apply **deck regeneration policy** → new PPTX in Drive/SMPL
- [ ] Data dispute: auth → pull recon exceptions → apply **mapping policy** → staged fix → customer confirms
- [ ] Explicitly **out of scope**: full Salesforce / CX dispute bot — steal the **pattern**, not the vertical

### Explicitly do *not* do first

- [ ] Full bi-directional Excel
- [ ] Agent edits prod metric definitions live in chat
- [ ] Agent “fixes” Salesforce/CRM as ARR system of record
- [ ] Unscoped “resolve anything” autonomy

---

# Part 2 — Predictive analytics (lever-aware scenario intelligence)

Internal name: “predictive analytics.” Buyer-facing: **scenario intelligence / lever analytics** — not crystal-ball marketing.

## Vision

- [ ] Lever-aware simulation on top of the trusted financial model (not static best/base/worst only)
- [ ] Multi-iteration runs (Monte Carlo-style); move **multiple drivers** at once
- [ ] Surface **what matters**: biggest levers, downside risks, upside paths
- [ ] Goal tiers + covenant rails as first-class scenario tiers (over time)
- [ ] Optional outside reality later: market / buying trends; historical pipeline conversion
- [ ] AI **explains after** deterministic math — does not invent formulas
- [ ] Not sold as “we predict revenue”

### Core questions the product answers

- [ ] What are our biggest levers? (sensitivity / importance)
- [ ] What are the biggest downside risks? (paths that breach cash, growth, or covenants)
- [ ] What upside paths actually move the needle?
- [ ] How do we stay inside operating goals and covenant rails?

## MVP — shippable story

**Job to be done:** “Given our model and a few uncertain drivers, show the range of outcomes and the 5 things that matter most.”

### In scope

- [ ] **Driver set** — 5–15 levers from scenario analysis (churn, expansion, new logo conversion, hiring/burn, collection lag, price, etc.) — not every GL line
- [ ] **Distributions, not point guesses** — simple ranges (low/base/high or mean + uncertainty)
- [ ] **Multi-driver Monte Carlo** — thousands of runs; several levers per run (independent OK for v1)
- [ ] **Outcome pack (small)** — e.g. ending cash / runway, ARR or bookings (their methodology), burn; maybe GAAP revenue if already modeled
- [ ] **Outputs**
  - [ ] P10 / P50 / P90 (and % below a threshold)
  - [ ] Tornado / lever importance
  - [ ] Top risk scenarios (short narrative list)
  - [ ] Top upside scenarios
- [ ] **Historical conversion (light)** — past win rates / stage conversion as defaults where data exists; manual override always
- [ ] **Goal tiers (simple)** — e.g. stay above $X cash, hit $Y ARR — P(hit/miss); not full covenant legalese yet

### Trust rules (non-negotiable)

- [ ] Same inputs → same distribution (**seeded RNG**)
- [ ] Every run uses **their** methodologies / canonical defs
- [ ] **Trace**: which drivers, ranges, outcome defs
- [ ] AI explains **after** the runs; doesn’t invent formulas

### Out of MVP

- [ ] Live market data feeds / macro overlays
- [ ] Full debt/equity covenant parsers
- [ ] Auto “recommended operating plan” that replaces FP&A judgment
- [ ] Claiming the model *knows* the future

### Sequencing recommendation (not locked)

- [ ] Prefer **cash-first + one growth metric** for MVP (cash/runway home for later covenants; one ARR/bookings-style metric for growth story)
- [ ] Decide later if needed: pure cash-first vs ARR-first outcome pack

## V1.5 — soon after MVP

- [ ] **Correlation** between drivers (e.g. churn up ↔ expansion down)
- [ ] **Quarter-by-quarter path** charts (not just end-state)
- [ ] **Saved operating cases** — Base / Stretch / Survival as labels on the distribution (not separate fake models)
- [ ] **Pipeline as a structured lever** — stages × historical conversion × capacity

## Later — differentiating

- [ ] **Covenant packs** — debt/equity tests as constraints; P(breach), when, which lever cluster; templates + customer-entered terms (not overnight credit-agreement interpretation)
- [ ] **Market / buying-trend overlays** — optional shocks, clearly labeled vs company history
- [ ] **Guided next-quarter playbooks** — efficient lever moves to raise P(goal OK) under constraints
- [ ] **Board / MD&A export** — distribution + levers + risks in monthly exec language (MD&A first)

## External language

| Say | Don’t say |
|-----|-----------|
| Scenario intelligence / lever analytics | “We predict your revenue” |
| Probability of hitting goals | Guaranteed forecast |
| Biggest risks and upsides | Black-box AI CFO |
| Works with your methodologies | One true ARR for everyone |

- [ ] Keep “predictive analytics” as **internal** name if useful
- [ ] Prefer buyer-facing: **Predictive scenarios** or **Lever & risk analysis**

---

# Part 3 — Competitive posture (short)

Radar check, not a feature checklist. Skip competitor features that fight the story.

- [ ] **Don’t copy Aleph Excel bi-di** — bi-directional Excel muddies source of truth; SMPL sits above SoRs
- [ ] **Slack agent = ops + trusted Q&A** — where the platform is operated/supported, not “live in the spreadsheet”
- [ ] **Predictive / lever-aware scenario intelligence as differentiator** — multi-iteration levers, risks, upsides, rails — neither Aleph nor Sapien leads with this layout
- [ ] **AI after validation** — differentiator vs free-running agents
- [ ] For each shiny competitor feature: tag **ours / theirs / skip** + one-line “why better”

---

## Open decisions (parked)

- [ ] Cash-first vs ARR-first for v1 outcomes (recommendation: cash + one growth metric)
- [ ] Which 8–10 levers in today’s scenario tool plug into MC first
- [ ] Covenant tiers as packaging story now vs literal constraint engine in v2
- [ ] First 5 agent tools + which roles can use them
- [ ] Separate “support agent” vs “analyst agent” for segregation of duties (optional later)
