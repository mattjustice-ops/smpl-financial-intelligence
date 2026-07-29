# AI / LLM Data Handling Policy

> **STATUS: APPROVED** — Effective 2026-07-28 (v1.0). Approved by Matt Justice (executive sponsor).  
> **Amendment DRAFT v1.1 (2026-07-28)** — pending Matt Justice Allow on this redline (and IR Scenario B alignment). Not yet effective until Allow.  
> Not legal advice. Not evidence of SOC 2 certification. Approving policies ≠ SOC 2 certified; open evidence items remain. SMPL is **not** SOC 2 certified until a CPA Type I report is in hand.  
> **Normative design targets:** [../controls/data_integrity_framework.md](../controls/data_integrity_framework.md), [../controls/data_sources_tieout_prompt.md](../controls/data_sources_tieout_prompt.md) — see [../controls/README.md](../controls/README.md) for implemented vs roadmap labels. Do not claim all framework layers are shipping in prod unless evidence shows they are.

| Field | Value |
|-------|--------|
| Policy ID | P15 |
| Owner | Matt Justice (Security owner / Engineering owner) |
| Applies to | Product AI/LLM features, personnel using sanctioned or unsanctioned AI tools with SMPL or customer data, and LLM subprocessors |
| Related criteria | Security; Confidentiality |
| Version | 1.0 (approved); **1.1 draft amendment pending Allow** |
| Effective date | 2026-07-28 (v1.0) |
| Last expanded | 2026-07-28 (v1.1 draft: machine-primary + integrity framework alignment) |

---

## 1. Purpose

Define how SMPL uses generative AI / large language models (LLMs) so that:

1. Financial **numbers** come from the deterministic calculation engine and warehouse — not from model invention.
2. Customer Confidential data is handled with minimum necessary context, tenant isolation, and honest external language.
3. LLM vendors (today: **Anthropic**; optional fallbacks if live) are treated as subprocessors under [P09](./P09_vendor_subprocessor_management.md).

This policy aligns with approved P01–P12 and with sales-talk Trust & Security Q&As (`ai-data-handling`, `ai-security`, `ai-training`, `ai-hallucinations`, `ai-keys-server-side`, `ai-commentary-capabilities`, `ai-accuracy`, `no-gl-writeback`, `soc2-status`). It does **not** claim SOC 2 certification.

## 2. Scope

In scope:

- In-product AI narrative / commentary / executive Q&A that calls an LLM API from the SMPL backend.
- Internal tools that may call the same LLM APIs with customer or production context (ops, sales-assist, etc.).
- Personnel handling of customer Confidential data with third-party AI products (consumer ChatGPT, etc.).
- Prompt/response data sent to Anthropic (and any other live LLM vendor listed in [../02_subprocessors.md](../02_subprocessors.md)).

Out of scope (covered elsewhere):

- Deterministic ARR / FP&A / close engine math ([product architecture]; Processing Integrity is **deferred** for Type I — see [../00_decision_log.md](../00_decision_log.md)).
- Customer DPA contractual exhibits ([P10](./P10_risk_assessment.md) R16).
- White-glove privileged access procedures ([P16](./P16_white_glove_privileged_support_access.md) when drafted).

## 3. Roles

| Role | Responsibility |
|------|----------------|
| Executive sponsor (Matt Justice) | Approves this policy; accepts residual AI/LLM risk |
| Security owner (Matt Justice) | Maintains policy; vendor/subprocessor posture; sales language honesty; IR for AI incidents |
| Engineering owner (Matt Justice) | Implements grounding, evidence binding, freeze-ID binding, permission checks, key placement, **fail-closed** behavior |
| All personnel | No unsanctioned paste of production Confidential data into consumer AI tools ([P02](./P02_acceptable_use_policy.md)) |

## 4. Core posture (non-negotiables)

1. **AI explains validated engine outputs; it does not invent financial numbers.** Ledger figures, ARR movements, and other reported metrics are produced by the deterministic calculation engine / warehouse. The LLM drafts narrative over those outputs.
2. **Deterministic calc vs generative narrative.** Same inputs and methodology → same numeric outputs. Generative text may vary in wording; it must not become the system of record for numbers.
3. **No training on customer data for foundation models.** SMPL does not use customer content to train foundation models. Customer content used for narrative assistance is processed under vendor terms and the customer DPA workstream; the LLM provider is a **subprocessor**, not a training corpus for SMPL.
4. **Minimum necessary context.** Prompts prefer aggregated metrics and governed report / freeze context. Raw PII and unnecessary line-level personal data are excluded from prompts by default; any exception requires a documented product reason ([P06](./P06_data_classification_and_handling.md)).
5. **Permission-aware / same security model.** LLM features run in the authenticated user's org and role context. Tenant isolation (`organization_id`) still applies — Org A context must not leak to Org B. AI must not grant access the user does not already have via the product.
6. **Read-focused; no ERP write-back; no autonomous financial updates.** AI must not post journals, mutate customer GL/ERP, or autonomously change warehouse financial facts / finalized period numbers. Connectors remain read-only ([P07](./P07_customer_data_confidentiality_procedures.md)).
7. **Hallucination / "don't know" behavior — machine-primary controls.**
   - **Named failure modes.** Generative models can invent fluent narrative if unconstrained. For this product, the specific risks are: (a) inventing a figure the engine/warehouse never produced; (b) correctly citing a real number but attributing it to the wrong driver or cause (wrong-context packaging / embellishment); (c) fabricating a supporting reference or citation that does not resolve to real evidence; (d) stating a claim with unwarranted confidence when the underlying data is actually low-confidence or incomplete; (e) emitting commentary bound to the wrong freeze / period.
   - **Primary control (backend / engineering — fail closed).** Customer-visible analysis, commentary, and numbers must not rely on human re-validation before every send as the primary control. Users will misuse UI; the system must force the right path. Before commentary is emitted or packaged for customer delivery, the generation path **must**:
     1. Bind the package / narrative to a specific **freeze ID** (or equivalent immutable engine/warehouse snapshot identifier);
     2. Structurally verify every material numeric claim and driver attribution against that freeze / engine evidence (and against `_sources` / provenance when present — see §4.8);
     3. **Fail closed**: if a claim cannot be resolved to freeze evidence, omit it or replace it with an explicit "don't know" — never emit unsupported claims. Validation gates must not fail open (bug/misconfig that allows unsupported claims through is a defect and an incident path under [P04](./P04_incident_response_plan.md)).
   - **Verification mechanism.** Commentary is not considered complete, and must not be surfaced to a customer, until every material claim has been checked against engine/warehouse evidence it can be traced back to (automated evidence binding / second-pass verification). A claim that cannot be resolved to real evidence is removed or replaced with an explicit "don't know" statement before delivery. This check is a required step in the generation path, not an aspiration and not a human checklist substitute.
   - **"Don't know" trigger.** The system defaults to declining to answer, rather than answering, whenever: (i) required supporting evidence is missing or does not resolve; (ii) a requested metric is not present in the evidence / `_sources` package; (iii) the underlying data's confidence is below the product's configured threshold; or (iv) two available pieces of evidence conflict without a documented resolution.
   - **Large commentary-vs-engine variance is an unacceptable control failure.** A material gap between AI-stated figures/drivers and freeze/engine evidence (illustrative: commentary claiming ~+18% QoQ / wrong-region driver when the freeze supports ~4% / no such driver) is not a "user education" issue — it is a grounding/validation **fail-open** defect. Trust impact is severe; the residual acceptable scenario for IR is that automated gates failed open (bug/misconfig), not that humans skipped a review.
   - **Human role (not primary day-to-day control).** Humans are for **incident response**, **exception handling**, and **periodic control testing** — not for re-validating every board package or customer-visible narrative as the day-to-day gate. Board-package "human review before send" is **not** the primary control and must not be described as such in policy, sales language, or IR root-cause framing. (Framework Part 6 human sign-off is adapted to periodic testing — see [../controls/README.md](../controls/README.md).)
   - **Incident path.** A hallucinated, embellished, or unverified claim that reaches a customer is a reportable incident under [P04](./P04_incident_response_plan.md) — see P04 §3 / Sev2 / containment playbook. Root-cause analysis for such incidents focuses on grounding/validation fail-open, freeze-ID binding gaps, missing `_sources` enforcement, or structural/tie-out verification defects — not "skipped human review."
8. **Provenance, `_sources`, freeze binding, and automated gates (required control design).** Normative detail lives in [../controls/](../controls/README.md). Engineering **must** treat the following as required design (roadmap-to-implement where not yet shipping — label honestly; see controls README):
   - **`_sources` / provenance.** Every data payload supplied to Claude (commentary, Copilot, close-context packages) must carry provenance that maps each material metric to warehouse/engine origin (table/column/period/org, computed formula, or lever/budget). Unacceptable classes: phantom, stale-without-flag, estimated-without-disclosure, hardcoded display values presented as facts.
   - **Claude may only state values present in evidence.** The model must not invent, interpolate, or recall numbers outside the supplied evidence / `_sources`. Missing metric → explicit don't-know / decline — not a guess.
   - **Fail-closed / don't-know.** Unresolved or unverifiable claims are omitted or don't-know; gates must not fail open.
   - **Freeze-ID binding.** Board and customer-facing packages / narratives bind to a specific freeze ID (or equivalent immutable snapshot). Wrong-freeze packaging is a defect.
   - **Automated tie-out / second-pass verification as deploy or release gates (design target).** Tie-out checks (warehouse vs displayed; Rule Sets A–F where applicable) and commentary second-pass verification **block** publish/deploy/customer-visible emit on FAIL. Warnings may be reviewed; FAILs do not ship. Partial product paths (e.g. freeze-pack required for some exports; financial close tie-outs) must expand toward this full gate — not be overstated as complete framework coverage.
   - **Embellishment / wrong-context packaging** (correct number, wrong driver/region/cause) is prevented by structural claim verification against freeze evidence — same fail-closed path as invented numbers.
9. **Honest SOC 2 language.** Never claim SMPL is "SOC 2 certified" or "SOC 2 compliant" because AI features exist or this policy is approved. Say "pursuing SOC 2" / "readiness in progress" until a CPA report is in hand ([P01](./P01_information_security_policy.md), [P02](./P02_acceptable_use_policy.md)). Never claim all integrity-framework layers are live in production unless code and evidence show they are ([../controls/README.md](../controls/README.md)).

## 5. Architecture controls

| Control | Requirement | Status posture |
|---------|-------------|----------------|
| Key placement | Anthropic (and any other LLM) API keys live on the **API / backend** (Railway env) only — never in browser, Vercel client env, static board HTML, or exported artifacts | Required (ops) |
| Call path | Production narrative LLM calls originate from the backend with org-scoped context | Required (ops) |
| Grounding | Prompts and tooling supply engine/warehouse outputs (or summaries thereof); models must not be asked to invent missing ledger totals | Required |
| `_sources` / provenance | LLM context includes provenance mapping for every material metric; Claude may only state values present in evidence / `_sources` | **Required design** — see controls README for shipping honesty |
| Evidence binding / structural claim verify | Material claims (numbers **and** driver attributions) in customer-visible commentary must resolve to freeze/engine evidence; unsupported claims omit / "don't know" | **Required design** (partial paths may exist; full gate is target) |
| Freeze-ID binding | Board / customer-facing packages and narratives are bound to a specific freeze ID (or equivalent snapshot id); wrong-freeze packaging is a defect | **Partial implemented** + required design for all customer-facing packages |
| Automated tie-out / second-pass gates | Tie-out + commentary verification run as deploy/release (or emit) gates; FAIL blocks ship | **Required design** (partial close/export validations exist) |
| Fail-closed validation | Grounding/validation gates must fail closed — never fail open on bug or misconfig | Required |
| Isolation | Requests are scoped to the caller's organization; no cross-tenant prompt assembly | Required |
| Logging | Full Confidential prompts are not written to long-lived cleartext logs. Where debug logging of prompt/response content is operationally necessary, it is treated as Confidential per [P06](./P06_data_classification_and_handling.md), access-restricted the same as production secrets, and retained no longer than **30 days**, after which it is deleted or truncated of Confidential content (see [P08](./P08_retention_and_deletion.md) retention row) | Required |
| Change control | Material changes to AI grounding, tool permissions, or vendor switch follow [P05](./P05_change_management_policy.md) | Required |
| Normative specs | [../controls/data_integrity_framework.md](../controls/data_integrity_framework.md); [../controls/data_sources_tieout_prompt.md](../controls/data_sources_tieout_prompt.md) | Design targets |

## 6. Anthropic and other LLM subprocessors

- **Primary:** Anthropic — LLM API for narrative / commentary (see [../02_subprocessors.md](../02_subprocessors.md)).
- **Conditional:** OpenAI or other LLM fallbacks — **not live** on production Railway as of 2026-07-28 (Matt Q2). Add to the subprocessors list only if a key is later enabled in production; same key-placement and minimum-context rules apply.
- Onboard and review under [P09](./P09_vendor_subprocessor_management.md); collect vendor SOC/ISO reports under NDA when available.
- Customer-facing subprocessor disclosure follows the consolidated **Customer DPA / MSA** legal workstream ([P10](./P10_risk_assessment.md) R16) — this policy does not invent signed DPA terms.

### 6.1 Optional disable / commentary governance (directional)

SMPL may, over time, offer customer- or plan-level controls to limit or disable generative commentary (for example: enterprise preference, entitlement packaging, or ops configuration).

**Honesty constraint:** Until a specific product control is shipped and documented, do **not** claim a customer-facing "AI kill switch," per-tenant hard disable, or contractual kill-switch that does not exist in the product. Directional roadmap language is fine; fake feature claims are not.

Until such customer-facing controls exist, governance relies on: **`_sources` / provenance**, **automated evidence binding**, **fail-closed grounding**, **freeze-ID binding**, **tie-out / second-pass verification gates** (as implemented + roadmap), permission model, and engineering ability to disable the narrative generation path via real technical controls (feature flag / env / hotfix) during incidents — not on human review of every package before send.

## 7. Personnel use of AI tools

- **Sanctioned product path:** In-product / backend Anthropic (or approved fallback) under this policy.
- **Unsanctioned:** Do not paste production Confidential customer data into consumer AI products (ChatGPT web, personal Copilot, etc.) unless the security owner explicitly approves that use case ([P02](./P02_acceptable_use_policy.md)).
- Prefer sanitized or demo data in tickets, screenshots, and external AI experiments.

## 8. External / sales language (approved themes)

Safe themes (align with sales-talk KB):

| Theme | Say |
|-------|-----|
| Role of AI | Narrative assistance over engine-calculated metrics; not the system of record for numbers |
| Training | We do not use customer data to train foundation models |
| Security | Keys server-side; minimum necessary prompts; tenant isolation; no GL/ERP write-back |
| Hallucinations | Every material claim is checked against engine/warehouse (freeze-bound) evidence / `_sources` before delivery; unsupported claims are omitted or marked "don't know," not guessed; primary controls are automated and fail closed — not human re-validation of every package; large commentary-vs-engine variance is a control failure |
| SOC 2 | Pursuing / readiness in progress — **not** certified |
| Integrity gates | Speak honestly: some freeze/tie-out paths exist; full `_sources` + second-pass + publish-block framework is required design / roadmap — see [../controls/README.md](../controls/README.md) |

Do not overstate vendor certifications or claim SMPL SOC 2 status from Anthropic's (or any vendor's) reports alone.

## 9. Linkage to other policies

| Theme | Policy |
|-------|--------|
| Umbrella security + honest language | [P01](./P01_information_security_policy.md) |
| Acceptable use / no consumer AI paste | [P02](./P02_acceptable_use_policy.md) |
| Access / MFA on Anthropic console | [P03](./P03_access_control_policy.md) |
| Incidents involving prompt/data leakage, or hallucinated content reaching a customer | [P04](./P04_incident_response_plan.md) |
| Changes to AI features / vendors | [P05](./P05_change_management_policy.md) |
| Classification + AI prompts | [P06](./P06_data_classification_and_handling.md) |
| No GL write-back / confidentiality procedures | [P07](./P07_customer_data_confidentiality_procedures.md) |
| Retention of AI prompt/debug logs | [P08](./P08_retention_and_deletion.md) |
| Anthropic as subprocessor | [P09](./P09_vendor_subprocessor_management.md), [../02_subprocessors.md](../02_subprocessors.md) |
| Risk R09 (prompt leakage) | [P10](./P10_risk_assessment.md) |
| Provenance / tie-out design targets | [../controls/README.md](../controls/README.md) |

## 10. Evidence

| Control | Example evidence |
|---------|------------------|
| Policy draft / approval | This file + [../04_policy_index.md](../04_policy_index.md) |
| Key placement | Railway env config (no client keys); code review / spot-check |
| Subprocessor listing | [../02_subprocessors.md](../02_subprocessors.md); Anthropic vendor report folder (NDA) |
| Normative design targets | [../controls/](../controls/README.md) (framework + tie-out prompt); honest implemented-vs-roadmap labels |
| Grounding / fail-closed | Product tests or design notes showing engine-first numbers; freeze-ID binding; `_sources`; structural claim verification; "don't know"/omit on unresolved claims; fail-closed validation (not fail-open) |
| Tie-out / second-pass gates | Tests or release evidence that FAIL blocks emit/deploy (as gates are built); do not claim full coverage prematurely |
| Periodic control testing | Dated notes from periodic tests of grounding/validation/tie-out gates (not per-package human sign-off as primary evidence) |
| Incident / exception handling | P04 IR notes when unsupported claims reach a customer |
| Sales alignment | sales-talk KB AI cards; [../SECURITY_ONE_PAGER.md](../SECURITY_ONE_PAGER.md) |

## 11. Review

Review at least annually, or when LLM vendor, prompt architecture, or product AI permissions change materially.

## 12. Approval

| Approver | Signature / name | Date | Notes |
|----------|------------------|------|-------|
| Executive sponsor | Matt Justice | 2026-07-28 | Approved v1.0 |
| Executive sponsor | _pending Allow_ | — | v1.1 draft amendment (machine-primary + integrity framework alignment) — **do not treat as Allowed until Matt confirms** |

### Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-07-28 | Initial Approved policy (hallucination §4.7, logging/retention 30 days) |
| 1.1 draft | 2026-07-28 | Redline: primary controls = automated evidence binding, fail-closed grounding, freeze-ID binding, structural claim verification; human review before send is **not** primary; humans = IR / exceptions / periodic testing. Pending Matt Allow. |
| 1.1 draft (rev) | 2026-07-28 | Align to [../controls/](../controls/README.md): `_sources`/provenance; Claude only states evidence values; fail-closed don't-know; freeze-ID binding; automated tie-out/second-pass as deploy/release gates (design target); large commentary-vs-engine variance = unacceptable control failure; honest partial-vs-roadmap labels. Pending Matt Allow. |

---

_End of P15 (v1.0 Approved; v1.1 draft amendment pending Allow)_
