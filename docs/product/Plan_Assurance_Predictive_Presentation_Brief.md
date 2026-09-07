# Plan Assurance & Predictive Analytics — Presentation Brief

> **Purpose:** Shareable inventory of what Budget Engine Plan Assurance does today, how it is presented, and open design space for **outrageous, high-trust guardrail outputs**.  
> **Audience:** Product, design, FP&A advisors, anyone brainstorming “what should this feel like when the model warns you.”  
> **Status:** Live in Budget Engine Overview (`/budget-engine` → Overview). Framework ambitions beyond this surface: [SMPL_Predictive_Planning_Intelligence_Framework.md](./SMPL_Predictive_Planning_Intelligence_Framework.md).  
> **Last updated:** 2026-09-04

---

## 0. The product bet (say this first)

**Most planning software helps Finance build the plan. Plan Assurance / Predictive Planning Intelligence should help Finance determine whether the business can actually deliver it.**

Operating loop:

**Plan → Test → Observe → Reassess → Act**

Layer separation (non-negotiable):

| Layer | Owns | Must not own |
|-------|------|--------------|
| **Deterministic Finance Engine** | ARR / GTM / Sales / HC / IS / BS / CF waterfalls, identities, locks | Probabilistic attainment, narrative inventing dollars |
| **Plan Assurance / PPI** | Outliers vs history, hard risk checks, stress cases, Monte Carlo on levers, “what breaks” | Rewriting SoT schedules as alternate facts |
| **Generative AI / LLM** | Plain-language explanation of structured findings | Computing financial numbers or silent lever edits |
| **Finance judgment** | Accepts changes, promotes versions, ships board packs | Replaced by model confidence |

**Guardrail output design challenge:** Make the Test step so visceral and clear that a CFO *feels* the constraint — without ever looking like a black-box score.

---

## 1. Where it lives in the product

| Surface | Location | Role |
|---------|----------|------|
| **Plan Assurance panel** | Budget Engine → **Overview** (top of tab) | Primary predictive / feasibility UX today |
| **Operating visuals** | Same Overview, below Assurance | KPI strip + YoY charts (context, not the guardrail itself) |
| **Levers** | Left sidebar across tabs | The knobs stress tests mutate (growth, CPL, attrition, pipeline, cash floor, …) |
| **Commentary API** | `POST /api/v1/commentary/generate` | Optional LLM narration over structured packets (Anthropic if keyed; else deterministic fallback) |
| **Forecast Engine / Board** | Separate | Deterministic close / forecast / MD&A — **not** the Plan Assurance lanes yet |

Composition rule on Overview:

```
┌─────────────────────────────────────────────────────────────┐
│ Plan Assurance                                              │
│  ┌──────────────┬──────────────┬──────────────┐             │
│  │ 1 Outlier    │ 2 Status     │ 3 Scenario   │  ← 3 lanes  │
│  │    review    │    (plan)    │  (predictive)│             │
│  └──────────────┴──────────────┴──────────────┘             │
│  ┌─────────────────────────────────────────────┐             │
│  │ Risk checks · formula-graph validations     │  ← full-width│
│  └─────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────┘
│ Operating plan visuals (KPIs + YoY charts)                   │
```

Each lane has **↺ Refresh** (deterministic recompute) and **Generate** (LLM narrative over the same structured payload).

---

## 2. Lane 1 — Outlier review (vs history)

### Question it answers

“What about this FY27 plan is *weird* relative to FY25→FY26 and to its own intra-year shape?”

Not a fixed pet checklist — a **systematic scan** that emits findings when thresholds fire.

### What we compute

| Family | Lens | Examples |
|--------|------|----------|
| **YoY step-up / step-down** | vs_history | Ending ARR, net new, revenue, EBITDA, marketing, MQLs, Dec cash, Dec HC — plan YoY pp vs prior-year YoY pp |
| **Intra-year shape** | intra_year | H1/H2 share shift; H1→H2 tilt flip vs FY26; peak-quarter concentration move |
| **H2 path** | intra_year | Jun→Dec stock path for Ending ARR, cash, HC vs FY26 |
| **Cross-metric inversions** | cross_metric | Marketing↑ while MQLs↓; OpEx↑ while revenue↓; HC path vs net new — especially when history moved *together* |
| **Efficiency ratios** | vs_history / intra_year | Blended CPL YoY and H1→H2; EBITDA margin pp change; spend intensity, etc. |

Severities: `high` · `medium` · `info` · (`ok` / in-line tallied quietly).

### How it’s presented today

- Lane header + **history flag count** in the panel chrome  
- Short **deterministic narrative** (or LLM “Generate history”)  
- Stack of **finding rows**: severity chip · title · detail · citation (lens + metric)  
- “In line” metrics collapsed into a count, not noise

### Design opportunity (guardrail outputs)

Today this is a **list of amber/red chips**. Outrageous versions might look like:

- A **radar / fingerprint** of “how far from last year’s operating shape”  
- **Sparklines of FY26 vs FY27B** with the offending H2 tilt highlighted  
- A single **“inherited vs invented”** stamp when an inverse pattern already existed in FY26  
- **Side-by-side month ribbons** that pulse only on outlier months  

---

## 3. Lane 2 — Status (Plan Assurance narrative)

### Question it answers

“In one executive breath: what is this plan committing to, and are the hard checks clear?”

### What we compute

Structured **assurance packet** from the live formula graph (ARR path, GTM, Sales capacity, HC, cash, P&L), then:

1. Run **Risk checks** (Lane / strip below — same packet)  
2. Build **status narrative** from packet + high/med risks  

Deterministic narrative always includes:

- YoY ending ARR commitment and Dec path  
- FY net new, revenue, EBITDA  
- GTM MQLs / spend / pipeline cover  
- Sales ending NB/CS and bench vs hire split  
- HC Jan→Dec and Dec cash vs floor  
- Priority risks or “hard checks clear”

### How it’s presented today

- Prose block in the middle lane (escaped HTML, line breaks)  
- Header rollup: `N high risk · M med risk · K risk clear`  
- Generate status → optional LLM rewrite of the same facts  

### Design opportunity

Status is currently **paragraphs**. Guardrail-grade status might be:

- A **commitment card**: “We are promising X with Y capacity and Z cash cushion”  
- A **traffic stack** (ARR / Cash / Capacity / Funnel) with one verb each: *Hits · Breaches · Covers · Thin*  
- **Delta from last Generate** so refresh feels like a control loop, not a regen lottery  

---

## 4. Risk strip — formula-graph validations (full width)

### Question it answers

“Does the *math* of this plan contradict itself or our stated floors?”

These are **hard / soft validations**, not historical taste.

### Check catalog (current)

| ID | Domain | Pass condition (summary) |
|----|--------|---------------------------|
| `arr_path` | ARR | Dec ARR within ~0.2% of YoY target |
| `arr_bridge` | ARR | BOP + FY net new ≈ Dec EOP |
| `grr_floor` | Retention | Avg GRR ≥ ~92%, min month ≥ ~90% |
| `cash_floor` | Liquidity | Dec cash ≥ configured floor |
| `cash_path` | Liquidity | All months ≥ floor (else mid-year dip warn) |
| `nb_cover` | Sales | Ending NB AEs ≥ AE need from quota math |
| `cs_cover` | Sales | Ending CS ≥ need (expansion / churn cover) |
| `bench` | Sales | Existing bench cover % vs target |
| `pipeline` | GTM | Pipeline coverage ≥ min × |
| `gtm_mql` | GTM | Channel MQLs ≈ funnel required |
| `gtm_spend` | GTM | Program spend ≈ MQL × blended CPL |
| `gtm_mix` | GTM | Channel mix ≈ 100% |
| `jan_hc` | HC | Jan HC = Dec’26 lock |
| `ebitda` | P&L | FY EBITDA ≥ 0 (else watch) |
| `sm_tie` | P&L | Implied GTM S&M ≤ IS S&M |

Severity chips: `high` · `med` · `low` · `ok` · `info` (color tokens: red / amber / teal / blue).

### How it’s presented today

- Full-width grid under the three lanes  
- Each row: **severity pill + title + one-line detail**  
- Always live with the plan (no separate Generate)  

### Design opportunity

This is the closest thing we have to a **pre-flight checklist**. Outrageous guardrails:

- **Fail-closed gate** visual (“Promote blocked until…”) even before warehouse promote exists in UX  
- **Identity diagrams** (BOP + NN → Dec) that crack when bridge breaks  
- **Cash path ribbon** with floor line and trough callout  
- **Capacity meters**: AE need vs ending; CS need vs ending; bench %  

---

## 5. Lane 3 — Predictive / scenario stress

### Question it answers

“If the world is worse than our levers assume, what breaks first — and how often?”

Two layers run together on **Generate / Refresh scenarios**:

1. **Named discrete stress cases** (deterministic lever shocks)  
2. **Monte Carlo** — 1,000 annual lever draws through the **same formula graph**  
3. **Sensitivity curves** (YoY growth pp, CPL multiplier)

### 5.1 Named stress cases (families)

Cases are weighted toward themes already flagged in history/status text (ARR, CPL, cash, HC…).

| Family | Example cases | Plain-English intent |
|--------|---------------|----------------------|
| **growth** | YoY ending ARR −3pp / −5pp | Miss the growth rate commitment (pp, not “−3% revenue”) |
| **gtm** | CPL +15% / +30%; pipeline +1× | Demand gets more expensive or we over-cover |
| **sales** | Attrition +2pp / +5pp | More backfills, payroll, ramp drag |
| **retention** | Churn mix ×1.4 | More churn while still chasing Dec ARR → extra NB load |
| **combo** | −3pp growth + CPL +15% | Soft book + inefficient spend |
| **liquidity** | CPL ×2.5 + pipeline +2× + attrition +8pp; growth stall + spend spike | Intentional severe cash/ops stress |

Each case records **Δ Dec ARR · Δ Dec cash · Δ FY EBITDA**, plus break/watch reasons:

- Dec ARR vs target  
- Dec cash vs floor  
- AE / CS coverage  
- **Operating liquidity risk** (deep drawdown vs floor / large cash wipe even if still above floor)

Status chips: **break** · **watch** · **hold (ok)**.

### 5.2 Monte Carlo (what it is / isn’t)

| Is | Is not |
|----|--------|
| 1,000 draws of **annual levers** (YoY growth pp, log-CPL, attrition pp, pipeline ×) | Month-path combinatorial explosion |
| Each draw re-runs the **full Budget formula graph** | A separate statistical model of ARR |
| Outputs empirical μ/σ, P(ARR miss), P(cash &lt; floor), P(ops liquidity), P(AE short) | Calibrated Probability of Attainment (PPI Phase 2+) |
| Nerd view: histograms + Normal(μ̂,σ̂) overlay + sensitivity sparklines | Board-ready PoA product claim |

Priors (current defaults): growth σ ≈ 2pp; CPL log-σ ≈ 0.12; attrition σ ≈ 1.5pp; pipeline σ ≈ 0.35×.

### How it’s presented today

- Narrative (deterministic or LLM) summarizing breaks / watches / MC probabilities  
- Chip counts: `N break · M watch · K hold` + `MC n=1,000`  
- Scrollable **case table**: label + plain-English explain · Δ ARR · Δ Cash · Δ EBITDA · result chip  
- **Nerd view** (toggle):  
  - Dec ARR distribution histogram + fitted normal  
  - Dec cash distribution + P(floor) + P(ops liquidity)  
  - Sensitivity: YoY growth → Δ ARR; CPL mult → Δ cash  

### Design opportunity (highest leverage for “outrageous”)

Scenarios are still a **table + tiny SVGs**. This is where guardrail design can go nuclear:

| Idea | Why it fits |
|------|-------------|
| **Shatter glass** when a liquidity case breaks the floor | Emotional + unambiguous |
| **Tornado of “what kills us first”** from sensitivity | Classic FP&A, underused in SaaS UI |
| **Fan chart** of Dec ARR / cash from MC draws | Instant distribution literacy |
| **Survival strip**: % of trials that keep ARR + cash + AE cover all green | Single “can we operate?” number without calling it PoA |
| **Case cards as comic panels** (“The year paid channels died”) | Plain-English already exists — elevate the craft |
| **Compare-to-commitment**: shock overlay on the locked YoY / cash floor lines | Ties Test → Plan visually |

**Naming discipline:** Do not label MC P(miss) as **Probability of Attainment** in customer-facing copy until calibration / Phase 2 exists. Call it **stress frequency under stated priors** or **P(breach | lever noise)**.

---

## 6. Commentary / LLM presentation contract

| Control | Behavior |
|---------|----------|
| Input | Structured packet (history findings, risks, scenario suite, MC summary) |
| Endpoint | `/api/v1/commentary/generate` with credentials |
| Model | Anthropic when `ANTHROPIC_API_KEY` set; else deterministic template |
| Output | Prose only — **must not invent dollars**; should translate pp / CPL into $ and liquidity language |
| UX | Per-lane Generate; Refresh recomputes math without requiring LLM |

Guardrail for future “outrageous” LLM UX: **show the structured finding beside the sentence** (citation chip already exists on outliers — extend that pattern to scenarios).

---

## 7. Mapping to the PPI framework

| PPI capability (framework) | Budget Plan Assurance today | Gap |
|----------------------------|-----------------------------|-----|
| Plan Feasibility | Risk strip + stress breaks | No formal constraints registry / API DTO |
| What Has to Be True | Implicit in break reasons | Not a first-class structured list |
| Assumption Risk | Sensitivity minis + weighted cases | No ranked tornado object |
| Probability of Attainment | MC P(miss) under priors | Not calibrated; naming reserved |
| Trajectory | Outlier H2 paths / YoY charts | Not a live Act vs Plan track |
| Simulation | Discrete + MC lever shocks | Annual draws only; no path sim |
| Forecast Accuracy | — | Not started (Phase 4) |
| LLM narration | Lane Generate | Evidence package can get thicker |

See also: [SMPL_Agent_and_Predictive_Analytics_Checklist.md](./SMPL_Agent_and_Predictive_Analytics_Checklist.md) §5–§7.

---

## 8. Visual language (current tokens)

| Element | Treatment |
|---------|-----------|
| Panel | Dark surface, hairline border, three equal lanes + wide risk strip |
| Severity | Uppercase micro-pills: high (red), med (amber), ok/low (teal), info (blue) |
| Scenario result | break / watch / ok chips; row wash on break/watch |
| Nerd charts | 72px SVG histograms (blue bars + stroke curve); amber sensitivity path |
| Motion | Progress strings during MC (“Monte Carlo 400/1,000 full-plan draws…”) — functional, not cinematic |
| Typography | UI sans + mono for numbers; no “hero brand” treatment on Overview |

**Design note:** Overview is a **control surface**, not a marketing landing page — but guardrail *outputs* can still be cinematic as long as numbers stay formula-graph-true.

---

## 9. Brainstorm prompt (use this with design / advisors)

> We already compute: history outliers, hard identity/floor/capacity checks, named stress cases, and 1,000 formula-graph Monte Carlo draws with distributions.  
> Presentation today is chips, prose, a stress table, and tiny nerd SVGs.  
>  
> **Design challenge:** Propose 3–5 *outrageous* guardrail output concepts for the Test step — things a CFO would screenshot — that:  
> 1. Never invent dollars (always bind to the deterministic engine / stress packet)  
> 2. Make “break vs watch vs hold” unmistakable in &lt;3 seconds  
> 3. Teach pp vs % and cash-floor risk without a footnote essay  
> 4. Could ship as progressive enhancement on the existing three-lane + risk layout  
>  
> Prefer sketches over copy decks. Call out anything that would accidentally claim calibrated Probability of Attainment.

---

## 10. Implementation anchors (for eng)

| Concern | Location |
|---------|----------|
| Overview (risk + YoY visuals) | `frontend/public/budget-engine/index.html` → `renderOverview` |
| Analytics tab | `renderAnalytics` · nav `data-tab="analytics"` |
| Predictive craft (Claude HTML) | `frontend/public/budget-engine/plan-assurance-levers.html` (iframe + `smpl:pa-levers` live packet) |
| Live packet bridge | `buildPaLeversLivePacket` / `pushPaLeversToFrame` |
| Outlier engine | `runHistoryOutlierReview` |
| Risk checks | `runBudgetRiskChecks` (Overview) |
| Stress + MC | `runScenarioStressSuite`, `runScenarioMonteCarlo*` |
| Framework (aspirational) | `docs/product/SMPL_Predictive_Planning_Intelligence_Framework.md` |

---

## 11. Surface reuse — Budget · Board · Forecast

The Analytics methodology is **one packet shape, three hosts**:

| Host | Question | History LLM | Forward likelihood |
|------|----------|--------------|--------------------|
| **Budget Analytics** | Can we deliver the FY operating plan? | Outlier lane vs prior FY shape | Stress + MC on formula graph (remainder of year / full FY) |
| **Board / month-end** | What changed this close, and does outlook still hold? | Commentary over freeze / YoY / bridges | Re-run remaining-year stress from close month (same levers, shorter path) |
| **Forecast Engine** | Does *this* forecast version still clear the rails? | Version-over-version + vs Actual | Same Test harness keyed to active forecast version |

**Shared contract (do not fork):**
1. Deterministic engine owns dollars  
2. Structured findings (outliers, risks, cases, MC frequencies)  
3. LLM narrates only — never invents cash/ARR  
4. Frequencies under stated priors ≠ calibrated Probability of Attainment until Phase 2  

**Remainder-of-year likelihood** is the Board/Forecast killer feature: same corridor + trip-wires, but the cash/ARR path starts at the close (or forecast as-of) instead of Jan BOP. Budget already has the full-year form; Board/FE should call the same stress runner with `startPeriod = as_of`.

---

## 12. One-line summary for Slack

**Plan Assurance is a three-lane Test harness — history outliers, status narrative, and stress+MC — sitting on the same formula graph as the plan, with Analytics as the full-width predictive craft surface; Board and Forecast reuse the same packet for close and version likelihood.**
