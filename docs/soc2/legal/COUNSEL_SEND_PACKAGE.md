# Customer DPA / MSA — Counsel send package

> **INTERNAL — FOR COUNSEL ENGAGEMENT**  
> Readiness packaging only. **Not** legal advice. **Not** a signed DPA/MSA. **Not** evidence that counsel has been engaged or emailed. SMPL is **not** SOC 2 certified until an independent CPA Type I report is in hand. Do **not** claim GDPR / ISO / “SOC 2 compliant” from this pack.

| Field | Value |
|-------|--------|
| Workstream | Customer DPA / MSA — [P10](../policies/P10_risk_assessment.md) **R16** |
| Package status | **Sent to counsel 2026-07-29** — Matt attested send via chat; agent did **not** email. Counsel firm: **unspecified** |
| R16 status | **Open** — awaiting redline / customer-ready draft; send alone does **not** close R16 |
| Business owner | Matt Justice |
| Draft email | [DRAFT_EMAIL_TO_COUNSEL.md](./DRAFT_EMAIL_TO_COUNSEL.md) |
| Primary outline | [DPA_MSA_OUTLINE.md](./DPA_MSA_OUTLINE.md) |

---

## 1. What Matt should attach / link

Prefer attaching the markdown files from the repo (or a short PDF export of the same). Minimum set:

| # | Attach / link | Why |
|---|---------------|-----|
| 1 | **This file** — `docs/soc2/legal/COUNSEL_SEND_PACKAGE.md` | One-page brief + open questions |
| 2 | **`docs/soc2/legal/DPA_MSA_OUTLINE.md`** | Full clause outline (parties, processing, TOMs, AI, MSA pointers, exhibits) |
| 3 | **`docs/soc2/02_subprocessors.md`** | Living Customer Data subprocessor inventory |
| 4 | **`docs/soc2/01_system_boundary.md`** | Production Type I boundary + Matt Q1–Q10 locked answers |
| 5 | **`docs/soc2/SECURITY_ONE_PAGER.md`** | Customer diligence posture (honest “pursuing SOC 2”) |
| 6 | **`docs/soc2/policies/P15_ai_llm_data_handling.md`** | Approved AI/LLM policy (v1.1) — grounding / fail-closed |

**Optional if counsel wants depth (do not overwhelm first send):**

| Attach | Why |
|--------|-----|
| `docs/soc2/policies/P07_customer_data_confidentiality_procedures.md` | Confidentiality / no GL write-back / isolation |
| `docs/soc2/policies/P08_retention_and_deletion.md` | Retention vs immutability; offboarding windows |
| `docs/soc2/policies/P09_vendor_subprocessor_management.md` | Vendor process |
| `docs/soc2/policies/P04_incident_response_plan.md` | Breach / incident clock alignment |

**Do not attach as “certifications”:** SOC 2 report (none exists), vendor SOC reports (collection not started), fake region claims.

---

## 2. Ask of counsel (deliverables)

1. First **customer-ready DPA** (and MSA or combined Customer Agreement) suitable for US B2B SaaS Order Form attachment.
2. **Exhibit A** — subprocessors (from living list; publish path TBD).
3. **Exhibit B** — high-level TOMs (no invented SOC 2 / ISO / GDPR certs).
4. Optional **AI schedule** if counsel prefers standalone vs DPA section.
5. Redline / advice on open commercial defaults in §7 below (deletion window, breach notice, liability, governing law).

**Packaging preference (flexible):** Separate MSA + DPA **or** single Customer Agreement + DPA schedule — whichever counsel can maintain and sales can attach.

---

## 3. Product & data-flow summary (for counsel)

### 3.1 Product

**SMPL.ai** — B2B SaaS financial intelligence (FP&A / ARR / close / board export). Helps finance teams read and reconcile finance data.

**Hard product constraints (must survive into agreements):**

- **Read-only toward customer GL/ERP** — no journals / invoices / payroll write-back.
- **Multi-tenant** — data scoped by `organization_id` (Org A must not access Org B); isolation **evidence** still a readiness workstream — do not claim “audited proven.”
- **AI is not system of record for numbers** — deterministic engine / warehouse outputs are authoritative; LLM drafts narrative over those outputs.

### 3.2 Production hosts (Type I system = production)

| Surface | Identity |
|---------|----------|
| Web | `https://www.smpl-ai.com` (Vercel project `smpl-financial-intelligence`) |
| API | `https://sfi-api-production.up.railway.app` (`sfi-api-production`) |
| Datastore | Neon project `smpl-auth-prod` / branch `production` — **AWS us-east-1** |
| DNS | Squarespace for `smpl-ai.com` — **DNS-only** (not Customer Data processor) |

### 3.3 Typical data categories

| Category | Examples |
|----------|----------|
| Customer financial / operational data | GL-derived facts, ARR, pipeline, headcount, close packs, board/export artifacts |
| Account / user personal data | Email, name, org membership, invites, session/auth artifacts (magic-link Auth.js) |
| AI prompt context | Aggregated / governed report context to LLM API (minimize raw PII) |
| Billing | Billing contact / subscription metadata via **Stripe** (no full PAN at SMPL) |
| Support / white-glove | Occasional staging files for POC/load — minimize; delete after use |

**Roles (working):** Customer = Controller (or CPRA-style “business”); SMPL = Processor / Service Provider for Customer Data in the Service; SMPL = Controller for its own billing/admin/ops data. SOC Privacy Trust Services criteria are **deferred** for Type I — DPA still needed for user personal data in the product.

### 3.4 Out of product / not on product DPA exhibit

Locked by Matt Justice **2026-07-28** (boundary Q1–Q10):

| Item | Posture |
|------|---------|
| **Sanity** | Marketing CMS only — **outside** Type I product boundary; **not** Customer Data subprocessor for product DPA |
| **HubSpot** | SMPL sales CRM / prospect data — **not** on customer product DPA exhibit |
| **OpenAI** | **Not live** on production Railway — omit until live |
| **APM / product analytics** | None live in prod with request/user context |
| **Staging / preview** | Exists; holds **no Customer Data** — out of Type I production system |
| Customer NetSuite / Salesforce / ERP | Customer systems; SMPL processes data they provide |

---

## 4. Subprocessors (product DPA exhibit)

Source of truth: [02_subprocessors.md](../02_subprocessors.md).

| Vendor | Purpose | Region |
|--------|---------|--------|
| **Vercel** | Customer-facing web app | **TBD** |
| **Railway** | API / application services | **TBD** |
| **Neon** | Managed Postgres (warehouse + auth/org) | **AWS us-east-1** (confirmed) |
| **Resend** | Transactional email (magic links, etc.) | **TBD** |
| **Anthropic** | LLM API for narrative / commentary | Processing region **TBD**; keys on Railway only |
| **Stripe** | Billing / subscriptions | **TBD** |
| **GitHub** | Source control & CI (not warehouse dumps) | **TBD** / multi-region |

**Do not invent regions** for non-Neon vendors. Do not promise “US-only” until confirmed. Auth.js is library code on Vercel — not a separate subprocessor vendor.

---

## 5. AI / LLM posture (P15 Approved v1.1 — fail-closed)

Policy: [P15](../policies/P15_ai_llm_data_handling.md) — Approved **2026-07-28** by Matt Justice (v1.1). Approval ≠ SOC 2 certified.

| Theme | Honest commitment for contracts |
|-------|----------------------------------|
| Provider | **Anthropic** only today (OpenAI not live) |
| Training | SMPL does **not** use Customer Data to train foundation models |
| System of record | Engine / warehouse numbers win; narrative may vary in wording |
| Grounding | Machine-primary: evidence binding, **fail-closed** (omit / “don’t know” if claim unresolved), freeze-ID binding; large commentary-vs-engine variance = control failure / incident path |
| Keys | Server-side (Railway) only — not in browser |
| No GL write-back via AI | Required |
| Tenant isolation | Org-scoped prompts; no cross-tenant context |
| Customer “AI kill switch” | **Do not** contract until product control exists |
| Vendor terms | Counsel: check Anthropic DPA / training terms vs customer promises |

---

## 6. Security / TOMs themes (Exhibit B — high level)

Align to approved policies + one-pager; **no fake certificates:**

- Access control (Auth.js magic-link; org membership; MFA on admin consoles; least privilege)
- Tenant isolation by design (`organization_id`)
- TLS in transit; Neon encryption-at-rest defaults
- Secrets in host env stores (not in source)
- Change management via GitHub PRs → Vercel / Railway
- Neon backups / PITR; restore test Pass 2026-07-27 (readiness evidence)
- Approved IR plan (P04); tabletop completed 2026-07-28 (readiness only)
- AI controls per P15; card data via Stripe

**SOC 2 status language:** “pursuing / readiness in progress” until CPA Type I report in hand.

---

## 7. Open questions for Matt + counsel

| # | Item | Owner | Notes |
|---|------|-------|-------|
| 1 | Legal entity name / signatory block | Matt + counsel | Brand is “SMPL.ai”; entity TBD with counsel |
| 2 | Hosting regions for Vercel / Railway / Resend / Stripe / Anthropic / GitHub | Matt | Neon **us-east-1** locked; others **TBD** — confirm before external publish / US-only claims |
| 3 | Offboarding deletion window (30 vs 90 vs other) | Counsel + Matt | Working internal target 30–90 days |
| 4 | Subprocessor notice period + objection mechanics | Counsel | Sized for small SaaS |
| 5 | Breach notification timing language | Counsel | Align P04; do not invent statutory claims |
| 6 | Governing law / venue / liability caps | Counsel | Confirm whether breach liability is same cap or carved out |
| 7 | Publish path for customer-facing subprocessors list | Matt + counsel | Exhibit vs hosted URL |
| 8 | Anthropic terms vs “no training” customer promises | Counsel | Consistency check |
| 9 | Combined agreement vs separate MSA + DPA | Counsel | Either OK |
| 10 | First customer-ready PDF/Doc for Order Form | Counsel | Closes “outline-only” stage; R16 still open until offerable/signed path |

---

## 8. Honest status (do not overclaim)

| Claim | Truth |
|-------|-------|
| Counsel engaged / emailed | **No** — Matt must send ([DRAFT_EMAIL_TO_COUNSEL.md](./DRAFT_EMAIL_TO_COUNSEL.md)) |
| Customer-ready DPA exists | **No** — outline + this pack only |
| R16 closed | **No** |
| SOC 2 certified | **No** |
| Vendor SOC reports collected | **No** (inventory locked; collection open) |
| All vendor regions known | **No** — only Neon us-east-1 locked |

---

## 9. Source map (internal)

| Theme | Source |
|-------|--------|
| Full outline | [DPA_MSA_OUTLINE.md](./DPA_MSA_OUTLINE.md) |
| Boundary + Q1–Q10 | [01_system_boundary.md](../01_system_boundary.md) |
| Subprocessors | [02_subprocessors.md](../02_subprocessors.md) |
| Decisions | [00_decision_log.md](../00_decision_log.md) |
| AI / fail-closed | [P15](../policies/P15_ai_llm_data_handling.md) |
| Risk R16 | [P10](../policies/P10_risk_assessment.md) |
| Scoreboard | [PROGRESS.md](../PROGRESS.md) |

---

_End of counsel send package. Not legal advice. Not SOC 2 certified. Email not sent._
