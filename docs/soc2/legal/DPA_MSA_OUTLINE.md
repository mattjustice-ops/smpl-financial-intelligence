# Customer DPA + MSA — Counsel-Ready Outline

> **DRAFT FOR COUNSEL REVIEW — NOT LEGAL ADVICE**  
> This outline is an internal work product for SMPL counsel and leadership. It is **not** a signed agreement, **not** legal advice, and **not** evidence of SOC 2 certification. SMPL is **pursuing** SOC 2 Type I readiness and is **not** SOC 2 certified until an independent CPA firm issues a report. Do **not** claim GDPR certification, ISO certification, or “SOC 2 compliant” based on this document.

| Field | Value |
|-------|--------|
| Workstream | Customer DPA / MSA (single legal path) — [P10](../policies/P10_risk_assessment.md) **R16** |
| Status | **Outline drafted** — awaiting counsel redline / first customer-ready draft |
| Owner (business) | Matt Justice |
| Sources (internal) | P07, P08, P09, P15; [02_subprocessors.md](../02_subprocessors.md); [SECURITY_ONE_PAGER.md](../SECURITY_ONE_PAGER.md); Trust & Security sales KB themes |
| Created | 2026-07-28 |
| Related scoreboard | [PROGRESS.md](../PROGRESS.md) |

---

## How to use this document

1. Counsel turns this outline into a DPA (and MSA pointers / schedules) suitable for US B2B SaaS.
2. Matt confirms commercial defaults (notice periods, deletion windows, liability caps) before customer negotiation.
3. Exhibits A/B stay synced with the living subprocessors list and security posture — **do not invent certifications**.
4. R16 stays **open** until counsel-ready agreement exists and can be offered / signed — this outline alone does **not** close R16.

---

## A. Document set (recommended packaging)

| Instrument | Role | Notes for counsel |
|------------|------|-------------------|
| **Master Service Agreement (MSA)** | Commercial terms: services, fees, term, warranties, liability, IP, confidentiality (business secrets), governing law | Keep product description honest: FP&A / financial intelligence SaaS; **read-only** vs customer GL/ERP |
| **Data Processing Addendum (DPA)** | Processing of Customer Data / personal data in connection with the Service | Primary vehicle for privacy, subprocessors, security, breach, retention/deletion |
| **Order Form / SOW** | Customer-specific commercial terms | May incorporate MSA + DPA by reference |
| **Exhibit A — Subprocessors** | Named list (or URL to current list) | Mirror [02_subprocessors.md](../02_subprocessors.md); publish path TBD with counsel |
| **Exhibit B — Technical & Organizational Measures (TOMs)** | High-level security measures | Align to approved policies + one-pager; no fake ISO/SOC claims |

**Counsel decision:** Single combined “Customer Agreement + DPA schedule” vs separate MSA + DPA. Either is fine for a small US SaaS; prefer whatever counsel can maintain and sales can attach to Order Forms.

---

## B. Parties, roles, and scope of processing

### B.1 Parties (placeholders)

- **Provider / Company:** SMPL (legal entity name as counsel confirms — “SMPL.ai” is product brand).
- **Customer:** The subscribing B2B entity.

### B.2 Roles (accurate for this product)

| Role | Typical allocation | Accuracy note |
|------|--------------------|---------------|
| **Customer as Controller** (or equivalent under applicable US state privacy law) | Determines purposes of using the Service with their finance/ops data and their users | Customer controls source systems (NetSuite, Salesforce, QuickBooks, etc.) |
| **SMPL as Processor** (or “Service Provider” under CPRA-style framing) | Processes Customer Data **only** to provide the Service per Customer instructions and the Agreement | Primary posture for warehouse facts, auth, exports, AI commentary prompts |
| **SMPL as Controller** (limited) | Own business data: billing contacts, account administration, security/ops logs as needed to run the company, website/marketing where applicable | Do **not** overstate SMPL as controller of Customer’s GL contents |

**Privacy Trust Services criteria** are **deferred** for SMPL’s SOC 2 Type I scope. That does **not** mean a DPA is unnecessary — contracts often still address personal data of Customer employees/users of the product even when SOC Privacy is out of scope.

### B.3 Nature and purpose of processing

**Purpose:** Provide B2B SaaS financial intelligence (FP&A / ARR / close / board export and related features), including ingest, storage, calculation, export, support, and optional AI narrative/commentary.

**Product constraints to reflect in instructions / description (not optional marketing):**

- **Read-only toward customer GL/ERP** — SMPL does not write back journals, invoices, or payroll to customer source systems ([P07](../policies/P07_customer_data_confidentiality_procedures.md)).
- **Multi-tenant isolation** — data scoped by organization (`organization_id`); Org A must not access Org B ([SECURITY_ONE_PAGER.md](../SECURITY_ONE_PAGER.md)).
- **AI is not system of record for numbers** — deterministic engine / warehouse outputs are authoritative; LLM drafts narrative over those outputs ([P15](../policies/P15_ai_llm_data_handling.md)).

### B.4 Categories of data (outline — counsel to refine)

| Category | Examples | Notes |
|----------|----------|-------|
| **Customer financial / operational data** | GL-derived facts, ARR, pipeline, headcount, close packs, board/export artifacts | Core Confidential content; typically business data |
| **Account / user data (personal data)** | User email, name, org membership, invites, session/auth artifacts | Needed for magic-link login and tenancy; **include in DPA even though SOC Privacy is deferred** |
| **Support / white-glove operational copies** | Staging files used for POC or assisted loads | Minimize; delete after load/POC per [P08](../policies/P08_retention_and_deletion.md) |
| **AI prompt context** | Aggregated metrics / governed report context sent to LLM API | Subprocessor processing; minimize raw PII ([P15](../policies/P15_ai_llm_data_handling.md)) |
| **Billing data** | Billing contact, subscription metadata | **Stripe** is payment processor; SMPL does not store full PAN |
| **Logs** | Application / deploy logs at providers | Avoid Confidential dumps; provider retention defaults |

**Out of scope / not SMPL-held as system of record:** Customer’s NetSuite / Salesforce / ERP systems themselves; board recipients of Customer-exported files (Customer-controlled distribution).

### B.5 Data subjects (typical)

- Customer employees and contractors who use the Service (login / invites).
- Optionally, individuals whose identifiers appear in financial datasets Customer uploads (e.g. employee names in headcount files) — Customer is responsible for lawful collection and instructions; SMPL processes as instructed.

---

## C. Customer instructions & SMPL obligations (DPA core)

### C.1 Customer instructions (outline)

Customer instructs SMPL to process Customer Data solely to:

1. Provide, maintain, secure, and support the Service;
2. Prevent or address security / availability issues;
3. Comply with law / valid legal process;
4. Process as further documented in the Agreement, Order Form, and product documentation.

Customer remains responsible for: accuracy of data provided; lawful basis / notices to its users; access provisioning within its org; downstream use of exports.

### C.2 SMPL processor obligations (outline checklist for counsel)

- Process only per documented instructions (Agreement + DPA + product config).
- Confidentiality of personnel with access; need-to-know / least privilege ([P03](../policies/P03_access_control_policy.md), [P07](../policies/P07_customer_data_confidentiality_procedures.md)).
- Implement TOMs (Exhibit B) — **reasonable for a small SaaS**, not enterprise-bank language.
- Assist with Customer requests (access, deletion, etc.) **to the extent** data is in the Service and request is verified — sized for solo/small ops capacity.
- Notify of inability to comply with instructions where legally required framing applies.
- Flow-down equivalent obligations to subprocessors ([P09](../policies/P09_vendor_subprocessor_management.md)).
- Upon termination / offboarding: delete or return per §G (align [P08](../policies/P08_retention_and_deletion.md)).
- No sale of personal information; no use of Customer Data for SMPL’s unrelated advertising (counsel: CPRA “Service Provider” / “business purpose” language as appropriate for US customers).
- If SMPL receives a request directly from an individual data subject (rather than through Customer) regarding their personal data, SMPL redirects the individual to Customer and/or promptly forwards the request to Customer, and does not respond substantively except as required by law.

---

## D. Subprocessors

### D.1 Current named subprocessors (from living inventory)

Source of truth for diligence: [02_subprocessors.md](../02_subprocessors.md). **Regions marked TBD — confirm before external publish.**

| Vendor | Purpose (customer-facing summary) |
|--------|-----------------------------------|
| **Vercel** | Host customer-facing web application |
| **Railway** | Host API / application services |
| **Neon** | Managed Postgres (warehouse + auth/org data) |
| **Resend** | Transactional email (e.g. magic links, notifications) |
| **Anthropic** | LLM API for AI narrative / commentary |
| **Stripe** | Billing / subscriptions |
| **GitHub** | Source control and CI (code/CI; not customer warehouse dumps) |
| **Sanity** | Marketing CMS (blog/glossary); confirm before treating as Customer Data processor |

**Conditional (add only if live in production):** OpenAI or other LLM fallback; error/APM tooling with request context; product analytics capturing user PII.

**Explicitly not subprocessors (typical):** Customer’s ERP/CRM; recipients of Customer-controlled exports.

### D.2 Change notification (counsel to set periods)

Outline options for counsel (do not invent a signed SLA here):

- Maintain a current subprocessor list (Exhibit A and/or URL).
- Notify Customer of **material new** subprocessors before or promptly after engagement (P09: update list before or promptly after go-live).
- Reasonable objection right for material changes that adversely affect Customer’s compliance posture — **sized for small SaaS** (avoid 90-day enterprise grids unless counsel/customer requires).
- Annual review of material processors; collect vendor SOC/ISO reports **under NDA when available** — SMPL does **not** inherit or restate vendor certifications as its own.

---

## E. Security measures (high level → Exhibit B)

Align TOMs to approved internal posture; cite themes, not fake certificates:

| Theme | Current practice (honest) |
|-------|---------------------------|
| Access control | Auth.js magic-link; org membership; MFA on admin/cloud consoles; least privilege / named white-glove operators |
| Tenant isolation | `organization_id` scoping; isolation evidence is a readiness workstream (not claimed “proven audited” yet) |
| Encryption | TLS in transit; managed Postgres encryption-at-rest via provider defaults (Neon) |
| Secrets | Host env / secret stores (Vercel, Railway); not in application source |
| Change management | GitHub PRs; Vercel FE / Railway API deploys; authorized promoters only |
| Backups / restore | Neon backups / PITR; restore testing as part of readiness ([P12](../policies/P12_backup_and_restore.md)) |
| Incident response | Approved IR plan ([P04](../policies/P04_incident_response_plan.md)) |
| AI controls | Keys server-side only; minimum necessary prompt context; no GL write-back via AI ([P15](../policies/P15_ai_llm_data_handling.md)) |
| Card data | Stripe; SMPL does not store full PAN |

**Do not claim in TOMs or MSA:** SOC 2 certified; ISO 27001 certified; GDPR certified; Processing Integrity attestation; Privacy Trust Services attestation.

---

## F. Security incident / breach notification

Align to [P04](../policies/P04_incident_response_plan.md); counsel sets contractual clock and definition of “Security Incident.”

**Outline:**

1. SMPL investigates suspected incidents affecting Customer Data.
2. Notify Customer **without undue delay** after confirming a Security Incident involving Customer Data (counsel: pick a working target such as “within X hours of confirmation” — **finalize with counsel**; do not invent statutory claims).
3. Include known facts: nature, categories of data (to the extent known), likely consequences, measures taken/proposed.
4. Cooperate reasonably on Customer’s notification obligations.
5. Subprocessor incidents that may affect Customer Data are in scope of notice assessment.
6. Primary security contact today: **Matt Justice** (update if roles split).

---

## G. Retention, deletion, and return of data

### G.1 Critical distinction (carry into customer language)

From [P08](../policies/P08_retention_and_deletion.md):

- **Immutability / integrity (active relationship):** Warehouse / financial facts are not silently rewritten; corrections are new loads or documented adjustments — **not** a promise to keep data forever after offboarding.
- **Retention / deletion (offboarding):** Separate axis — after Customer leaves or requests removal, SMPL deletes/anonymizes per agreed window; backups may lag until provider expiry.

### G.2 Working defaults (for counsel — not yet contractual)

| Topic | Working default (internal) | Counsel action |
|-------|----------------------------|----------------|
| Active warehouse | Duration of subscription / service | Confirm |
| Auth / org membership | Account life + short grace (target ≤ 90 days) | Confirm |
| Offboarding deletion | Working target **30–90 days** after confirmed offboarding | **Finalize window** |
| White-glove staging | Delete after load / POC (target ≤ 30 days) | Confirm |
| AI prompt / debug logs | ≤ 30 days then delete/truncate Confidential content | Confirm |
| Backups | Provider window; honest disclosure of lag after deletion | Disclose in DPA |
| Billing | Stripe + legal/tax needs | Confirm |
| Return of data | Customer may export via product before offboarding; “return” = export assistance reasonable for small SaaS | Define format/assistance level |

**Legal hold:** Deletion may be suspended for litigation/regulatory hold per executive decision ([P08](../policies/P08_retention_and_deletion.md) §5).

### G.3 Written confirmation of deletion

Upon Customer’s written request after offboarding deletion is complete, SMPL provides written confirmation that Customer Data has been deleted or anonymized per the windows in §G.2 (including honest disclosure that provider backups may lag until expiry).

---

## H. International transfers

**Known posture:** US-oriented B2B SaaS; production stack includes Vercel, Railway, Neon, Stripe, Resend, Anthropic, Sanity, GitHub. **Exact hosting regions are TBD** in the subprocessors inventory — confirm before promising “US-only.”

**Counsel guidance requested:**

- If Customer is US-only and processing is US-based: simple US-law DPA may suffice.
- If Customer requires EU/UK transfer mechanisms (SCCs, UK addendum, etc.): only add when there is a real cross-border need and confirmed vendor regions — **do not paste SCCs “just in case” without facts**.
- Do not claim adequacy decisions or transfer certifications SMPL does not hold.

---

## I. Audit and assistance rights (reasonable for small SaaS)

Outline preferences for counsel (avoid enterprise audit tourism):

- Customer may request **reasonable** information to demonstrate DPA compliance (security one-pager, policies under NDA, questionnaire responses, subprocessors list).
- Once a SOC 2 Type I/II report exists, share **under NDA** in lieu of on-site audit where practicable.
- **Until a CPA report exists:** do not promise “SOC 2 report available”; offer current diligence pack instead.
- On-site / penetration-test rights: either omit or tightly condition (notice, scope, cost, no disruption, annual frequency) — sized for solo-founder ops.
- Assistance with DPIA / customer assessments: commercially reasonable, reimbursable if extraordinary.
- **Post-incident distinction:** the “reasonable, limited” posture above applies to routine annual diligence. Following a confirmed Security Incident affecting Customer Data, Customer may request additional relevant information reasonably necessary to assess impact and its own notification obligations, per §F.

---

## J. AI-specific terms (optional schedule or DPA section)

Align to [P15](../policies/P15_ai_llm_data_handling.md) and Trust & Security positioning (`ai-training`, `ai-data-handling`, `ai-security`):

| Commitment (draft theme) | Honest boundary |
|--------------------------|-----------------|
| **No foundation-model training on Customer Data by SMPL** | SMPL does not use Customer content to train foundation models |
| LLM provider is a **subprocessor** | Today: **Anthropic**; OpenAI only if live |
| **Governed / minimum necessary context** | Prefer aggregated metrics and governed report context; exclude unnecessary raw PII by default |
| **Not system of record** | Numbers from engine/warehouse; narrative may vary in wording |
| **No ERP/GL write-back via AI** | AI must not post journals or mutate customer source systems |
| **Tenant isolation** | Org-scoped prompts; no cross-tenant context |
| **Optional disable** | Do **not** contract a customer-facing “AI kill switch” until the product control exists; directional roadmap OK |
| **AI-generated content errors** | If AI-generated commentary contains a claim not supported by engine/warehouse evidence, SMPL corrects the output and follows internal incident handling per P04. MSA §K.8 sets any contractual remedy/disclaimer language — this outline does not itself create a warranty. |

Counsel: ensure Anthropic (and any LLM) vendor terms are consistent with “no training” claims SMPL makes to customers.

---

## K. MSA pointers (non-DPA commercial topics counsel should cover)

These are **not** fully outlined here; flag for MSA counsel draft:

1. **Services description** — FP&A / financial intelligence SaaS; features as ordered; beta/preview disclaimers as needed.
2. **Read-only / no GL write-back** — product warranty or limitation aligned with architecture.
3. **Fees, taxes, auto-renewal, suspension for non-payment.**
4. **Term & termination** — cross-link DPA deletion/return.
5. **Customer responsibilities** — credentials, lawful data, export review before board distribution.
6. **Confidentiality** (mutual business confidential info) — distinct from DPA personal-data processing.
7. **IP** — SMPL owns Service/IP; Customer owns Customer Data; feedback license.
8. **Warranties / disclaimer** — no guarantee of specific financial outcomes; AI narrative disclaimer; correction process for AI-generated errors aligned with internal incident handling (P04).
9. **Indemnities & liability caps** — counsel to set; small-SaaS-appropriate. Confirm whether liability arising from a confirmed data breach / Security Incident is subject to the same cap as general commercial liability, or carved out separately (a common customer negotiation point).
10. **Governing law / venue** — likely US state of SMPL entity (counsel confirms).
11. **Publicity** — logo use optional.
12. **Insurance** — only if actually carried; do not invent.
13. **SOC 2 / security representations** — “pursuing / readiness in progress” until report in hand; update when Type I issued.

---

## L. Exhibit placeholders

### Exhibit A — Subprocessors (placeholder)

> See current named list in [02_subprocessors.md](../02_subprocessors.md). Counsel to convert to customer-facing exhibit or hosted URL. Mark regions when confirmed. Remove unused vendors before publish.

### Exhibit B — Technical and Organizational Measures (placeholder)

> Summarize §E themes in counsel-approved TOMs format. Cross-reference internal policies P01–P12, P15 for operators — **customer exhibit should stay high-level**. No SOC 2 / ISO / GDPR certification claims.

### Exhibit C — (optional) AI Addendum

> Pull §J if Customer requires standalone AI schedule.

### Exhibit D — (optional) Regional / transfer addendum

> Only if international transfer facts require it (§H).

---

## M. Open items for Matt + counsel (before first customer send)

| # | Item | Owner |
|---|------|-------|
| 1 | Confirm legal entity name / signatory block | Matt + counsel |
| 2 | Confirm hosting regions for Vercel / Railway / Neon | Matt |
| 3 | Confirm whether OpenAI (or other LLM) is live | Matt |
| 4 | Finalize offboarding deletion window (30 vs 90 vs other) | Counsel + Matt |
| 5 | Subprocessor notice period + objection mechanics | Counsel |
| 6 | Breach notification timing language | Counsel (align P04) |
| 7 | Governing law / liability / MSA commercial pack | Counsel |
| 8 | Publish path for customer-facing subprocessors list | Matt + counsel |
| 9 | Consistency check: Anthropic DPA / training terms vs customer promises | Counsel |
| 10 | First redline → customer-ready PDF/Doc for Order Form attachment | Counsel |
| 11 | Decide whether data breach liability is capped separately from general commercial liability | Counsel + Matt |

---

## N. Source map (internal — not for customer attachment)

| Theme | Internal source |
|-------|-----------------|
| Confidentiality / ingest / isolation / no write-back | [P07](../policies/P07_customer_data_confidentiality_procedures.md) |
| Retention / offboarding / immutability distinction | [P08](../policies/P08_retention_and_deletion.md) |
| Vendor / subprocessor process | [P09](../policies/P09_vendor_subprocessor_management.md) |
| Named subprocessors | [02_subprocessors.md](../02_subprocessors.md) |
| AI / no training / governed context | [P15](../policies/P15_ai_llm_data_handling.md) |
| Customer diligence one-pager | [SECURITY_ONE_PAGER.md](../SECURITY_ONE_PAGER.md) |
| Incident / breach process | [P04](../policies/P04_incident_response_plan.md) |
| Risk tracking (R16) | [P10](../policies/P10_risk_assessment.md) |
| Trust & Security sales themes | sales KB: `ai-training`, `ai-data-handling`, `ai-security`, `no-gl-writeback`, `soc2-status`, tenant isolation |

---

_End of DRAFT outline — for counsel review only. Not legal advice. Not SOC 2 certified._
