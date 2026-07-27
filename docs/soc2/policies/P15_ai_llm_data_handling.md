# AI / LLM Data Handling Policy

> **STATUS: DRAFT — ready for approval** — Not yet approved. Do not treat as effective company policy until the Approval table is signed.  
> Not legal advice. Not evidence of SOC 2 certification. Drafting or approving this policy ≠ SOC 2 certified. SMPL is **not** SOC 2 certified until a CPA Type I report is in hand.

| Field | Value |
|-------|--------|
| Policy ID | P15 |
| Owner | Matt Justice (Security owner / Engineering owner) |
| Applies to | Product AI/LLM features, personnel using sanctioned or unsanctioned AI tools with SMPL or customer data, and LLM subprocessors |
| Related criteria | Security; Confidentiality |
| Version | 0.1 (draft) |
| Effective date | TBD on approval |
| Last expanded | 2026-07-27 |

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
| Security owner (Matt Justice) | Maintains policy; vendor/subprocessor posture; sales language honesty |
| Engineering owner (Matt Justice) | Implements grounding, permission checks, key placement, fail-closed behavior |
| All personnel | No unsanctioned paste of production Confidential data into consumer AI tools ([P02](./P02_acceptable_use_policy.md)) |

## 4. Core posture (non-negotiables)

1. **AI explains validated engine outputs; it does not invent financial numbers.** Ledger figures, ARR movements, and other reported metrics are produced by the deterministic calculation engine / warehouse. The LLM drafts narrative over those outputs.
2. **Deterministic calc vs generative narrative.** Same inputs and methodology → same numeric outputs. Generative text may vary in wording; it must not become the system of record for numbers.
3. **No training on customer data for foundation models.** SMPL does not use customer content to train foundation models. Customer content used for narrative assistance is processed under vendor terms and the customer DPA workstream; the LLM provider is a **subprocessor**, not a training corpus for SMPL.
4. **Minimum necessary context.** Prompts prefer aggregated metrics and governed report / freeze context. Avoid raw PII dumps and unnecessary line-level personal data where practical ([P06](./P06_data_classification_and_handling.md)).
5. **Permission-aware / same security model.** LLM features run in the authenticated user’s org and role context. Tenant isolation (`organization_id`) still applies — Org A context must not leak to Org B. AI must not grant access the user does not already have via the product.
6. **Read-focused; no ERP write-back; no autonomous financial updates.** AI must not post journals, mutate customer GL/ERP, or autonomously change warehouse financial facts / finalized period numbers. Connectors remain read-only ([P07](./P07_customer_data_confidentiality_procedures.md)).
7. **Hallucination / “don’t know” behavior.** Generative models can invent fluent narrative if unconstrained. Product design must ground commentary in engine-calculated evidence, keep humans in the loop for board-facing packages, and **fail closed** (say the data does not support a claim / “don’t know”) rather than fabricate explanations or ledger figures.
8. **Honest SOC 2 language.** Never claim SMPL is “SOC 2 certified” or “SOC 2 compliant” because AI features exist or this policy is approved. Say “pursuing SOC 2” / “readiness in progress” until a CPA report is in hand ([P01](./P01_information_security_policy.md), [P02](./P02_acceptable_use_policy.md)).

## 5. Architecture controls

| Control | Requirement |
|---------|-------------|
| Key placement | Anthropic (and any other LLM) API keys live on the **API / backend** (Railway env) only — never in browser, Vercel client env, static board HTML, or exported artifacts |
| Call path | Production narrative LLM calls originate from the backend with org-scoped context |
| Grounding | Prompts and tooling supply engine/warehouse outputs (or summaries thereof); models must not be asked to invent missing ledger totals |
| Isolation | Requests are scoped to the caller’s organization; no cross-tenant prompt assembly |
| Logging | Prefer not to log full Confidential prompts in long-lived cleartext stores; if debug logging is needed, treat as Confidential and minimize retention |
| Change control | Material changes to AI grounding, tool permissions, or vendor switch follow [P05](./P05_change_management_policy.md) |

## 6. Anthropic and other LLM subprocessors

- **Primary:** Anthropic — LLM API for narrative / commentary (see [../02_subprocessors.md](../02_subprocessors.md)).
- **Conditional:** OpenAI or other LLM fallbacks — add to the subprocessors list only if live in production; same key-placement and minimum-context rules apply.
- Onboard and review under [P09](./P09_vendor_subprocessor_management.md); collect vendor SOC/ISO reports under NDA when available.
- Customer-facing subprocessor disclosure follows the consolidated **Customer DPA / MSA** legal workstream ([P10](./P10_risk_assessment.md) R16) — this policy does not invent signed DPA terms.

### 6.1 Optional disable / commentary governance (directional)

SMPL may, over time, offer customer- or plan-level controls to limit or disable generative commentary (for example: enterprise preference, entitlement packaging, or ops configuration).

**Honesty constraint:** Until a specific product control is shipped and documented, do **not** claim a customer-facing “AI kill switch,” per-tenant hard disable, or contractual kill-switch that does not exist in the product. Directional roadmap language is fine; fake feature claims are not.

Until such controls exist, governance relies on: grounding + permission model + human review for board packages + ability to avoid using commentary features in a given workflow.

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
| Hallucinations | Grounded in engine outputs; fail closed / don’t invent unsupported explanations; humans review board packages |
| SOC 2 | Pursuing / readiness in progress — **not** certified |

Do not overstate vendor certifications or claim SMPL SOC 2 status from Anthropic’s (or any vendor’s) reports alone.

## 9. Linkage to other policies

| Theme | Policy |
|-------|--------|
| Umbrella security + honest language | [P01](./P01_information_security_policy.md) |
| Acceptable use / no consumer AI paste | [P02](./P02_acceptable_use_policy.md) |
| Access / MFA on Anthropic console | [P03](./P03_access_control_policy.md) |
| Incidents involving prompt/data leakage | [P04](./P04_incident_response_plan.md) |
| Changes to AI features / vendors | [P05](./P05_change_management_policy.md) |
| Classification + AI prompts | [P06](./P06_data_classification_and_handling.md) |
| No GL write-back / confidentiality procedures | [P07](./P07_customer_data_confidentiality_procedures.md) |
| Retention of prompts/logs (as applicable) | [P08](./P08_retention_and_deletion.md) |
| Anthropic as subprocessor | [P09](./P09_vendor_subprocessor_management.md), [../02_subprocessors.md](../02_subprocessors.md) |
| Risk R09 (prompt leakage) | [P10](./P10_risk_assessment.md) |

## 10. Evidence

| Control | Example evidence |
|---------|------------------|
| Policy draft / approval | This file + [../04_policy_index.md](../04_policy_index.md) |
| Key placement | Railway env config (no client keys); code review / spot-check |
| Subprocessor listing | [../02_subprocessors.md](../02_subprocessors.md); Anthropic vendor report folder (NDA) |
| Grounding / fail-closed | Product tests or design notes showing engine-first numbers; “don’t know” behavior |
| Sales alignment | sales-talk KB AI cards; [../SECURITY_ONE_PAGER.md](../SECURITY_ONE_PAGER.md) |

## 11. Review

Review at least annually, or when LLM vendor, prompt architecture, or product AI permissions change materially.

## 12. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | *Pending — Matt Justice* | *TBD* |

---

_End of DRAFT P15 (not approved)_
