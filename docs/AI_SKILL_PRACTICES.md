# AI skill practices (internal)

> Practical takeaways from external “Claude Skills” workflows, mapped onto **SMPL** — not a Skills product UI and not marketing claims.  
> **Honesty:** SOC 2 Type I readiness ≠ certified. AI **explains after validation**; do not invent methodologies.

Related: [Reporting_Logic.md](./Reporting_Logic.md) · [EXECUTIVE_REPORTING_GOVERNANCE.md](./EXECUTIVE_REPORTING_GOVERNANCE.md) · [product/SMPL_Agent_and_Predictive_Analytics_Checklist.md](./product/SMPL_Agent_and_Predictive_Analytics_Checklist.md) · [soc2/controls/ai_claim_verify.md](./soc2/controls/ai_claim_verify.md) · [soc2/policies/P15_ai_llm_data_handling.md](./soc2/policies/P15_ai_llm_data_handling.md) · [ANTHROPIC_SETUP.md](./ANTHROPIC_SETUP.md)

---

## 1. Skill lifecycle (personal → cool-down → team → prune)

| Stage | What to do | SMPL home |
|-------|------------|-----------|
| **Personal** | Solve a real close / board / Copilot task with a prompt. Correct the model until the recipe is clear. | Chat / one-off script — do **not** ship yet |
| **Cool-down / use** | Re-run on the next close (or next deck) without rewriting from scratch. Note what still breaks. | Same prompt file or private note |
| **Promote to team** | After a human accepts the output **and** existing gates pass (tie-outs / claim-verify), promote into shared prompts, docs, or product code | `prompt2_system.py`, `prompt5_narrative.py`, Copilot system string, this doc, `Reporting_Logic.md` |
| **Prune** | Delete or archive skills nobody used for 2–3 closes | Prefer fewer durable recipes over a graveyard of commentary macros |

**Rule of thumb:** build it, then skill it — do not start by inventing a skill registry.

---

## 2. Definition skills over commentary skills

Prefer durable **definitions** bound to governed metrics over “write nicer prose” macros.

| Prefer (definition) | Avoid (commentary theater) |
|---------------------|----------------------------|
| ARR / bookings / N$R / G$R meaning + SoT table | Tone-only “board voice” packs with no metric binding |
| Close-date vs start-date (or service-start) for new ARR / bookings — **one** tenant policy | Switching definitions mid-narrative |
| Waterfall hierarchy (never derive ARR from GAAP revenue) | Ad-hoc Excel commentary that invents drivers |

**Canonical definition homes (already exist):**

- Metric SoT + tie-outs → [Reporting_Logic.md](./Reporting_Logic.md)
- Export / board forbidden derivations → [EXECUTIVE_REPORTING_GOVERNANCE.md](./EXECUTIVE_REPORTING_GOVERNANCE.md) + `executive_reporting_governance.py`
- Tenant ARR policy fields → onboarding discovery sheet (capture) + tenant settings (document; do not invent)

When promoting a definition skill, update those docs/code constants — not a parallel “skills wiki.”

---

## 3. Clarify / plan before build

Before writing MD&A or board narrative:

1. Resolve period, scenario (Actual / Budget / Forecast), and metric definitions from freeze + payload.
2. If the ask is underspecified (which month? bookings close-date vs start-date?), **ask** (interactive) or **flag insufficient evidence** (export) — do not paper over gaps.
3. Only then draft commentary.

**Fluvo CFO webinar (2026-08-26) — same posture, plainer words:**

- **Foundation first:** reconciled data + governed definitions before prompt tricks (see [product/SMPL_Agent_and_Predictive_Analytics_Checklist.md](./product/SMPL_Agent_and_Predictive_Analytics_Checklist.md) §1).
- **Pre-flight in one message:** list missing/ambiguous inputs before running analysis — do not start with “What is my cash runway?” on a half-loaded model.
- **Plan before execute:** for Excel/forecast edits, *“Give me a plan before you change anything”* — model must not rewrite cells without approval.
- **Checks step (PGCI + C):** self-validate; flag gaps; **never invent numbers** — in finance you only catch hallucinations by auditing figures, not by reading prose.

**Product hooks:**

| Surface | Behavior |
|---------|----------|
| Copilot | Clarifying questions first when the question lacks period / metric / definition context |
| MD&A Prompt 2 / Prompt 5 | Preflight checklist in system/craft prompts; unresolved → don't-know / insufficient evidence, never invent |

Code: `backend/app/services/commentary/clarify_before_write.py`

---

## 4. Validation checks embedded (already the platform)

Do not treat “second pass” as a human ritual before every send. SMPL posture: **machine-primary**, fail-closed where wired.

| Check family | Where |
|--------------|--------|
| Numeric claim-verify | `claim_verify.py` — Prompt 2 strict; Prompt 5 soft-strip; Copilot interactive |
| Attribution / drivers | `attribution_verify.py` |
| Citations (`_sources`) | `citation_verify.py` |
| Close / export validation catalog | `ValidationCheck` + export validation gate |
| Client advisory A–F tie-out | FE `runTieOut` — advisory on export; hard ID at import/close |

Founder checklist: [ai_claim_verify.md](./soc2/controls/ai_claim_verify.md). When a skill fails these, **fix the skill or the data** — do not weaken tolerances.

---

## 5. Skill = validated SOP after human acceptance

Aligns with governed AI after validation (P15):

1. Engine / warehouse produces numbers.  
2. Tie-outs / evidence packages validate.  
3. AI explains **only** what is in the evidence.  
4. A human accepting a **recipe** (prompt/skill) for reuse is separate from day-to-day “human re-checks every number.”

Promote to team only when: (a) a human would ship the output, and (b) verify gates did not have to strip the story to nonsense.

---

## 6. Model routing with thick context

Prefer **strong evidence packages + freeze context + appropriate model** over thrashing larger models with thin prompts.

| Practice | SMPL default |
|----------|----------------|
| Thick context | Full freeze block on Prompt 2/5; Copilot evidence + attribution packages |
| Model choice | `llm_factory` — interactive vs export; `SMPL_FAST_AI` Haiku path for latency; Sonnet when quality flag off |
| Anti-pattern | Chasing Opus / max model for board-ready from a one-line prompt |

Ops: [ANTHROPIC_SETUP.md](./ANTHROPIC_SETUP.md). Quality comes from **payload + freeze + verify**, not model theater.

---

## Explicitly out of scope (do not incorporate)

- Laptop-scheduled Claude Desktop automations / “Mac Mini farms”
- “Must have MCP” as a purchase criterion
- Browser scraping as a data strategy
- Marketing claim: short prompt → board-ready
- SOC 2 **certification** claims (readiness only until a CPA report)

---

## How Matt uses this

1. **Weekly:** capture personal recipes that survived a real close; cool-down once; promote winners into prompts/docs above; prune the rest.  
2. **Definitions:** put ARR/bookings date rules in tenant policy + `Reporting_Logic` — not in ad-hoc commentary skills.  
3. **Ship narrative:** rely on clarify-before-write + existing P15 verify; do not add a Skills marketplace.  
4. **Sales/language:** AI explains validated evidence; SOC 2 Type I readiness is not certification.
