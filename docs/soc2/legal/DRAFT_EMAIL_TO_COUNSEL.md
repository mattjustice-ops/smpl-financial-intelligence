# Draft email to counsel — Customer DPA / MSA

> **Paste-ready draft for Matt Justice.**  
> Agent did **not** send this email. Update counsel name, firm, and attachment method before sending.  
> Not legal advice. Not SOC 2 certified. R16 remains open until a customer-offerable agreement exists.

---

**To:** [Counsel name / firm]  
**From:** Matt Justice \<mattjustice@smpl-ai.com\>  
**Subject:** SMPL.ai — Customer DPA / MSA draft request (US B2B SaaS)

---

Hi [Counsel name],

I’m preparing customer-ready **MSA + DPA** materials for SMPL.ai (US B2B SaaS financial intelligence / FP&A). We need a first draft we can attach to Order Forms for US customers.

**Ask:** Please turn the attached outline into a customer-ready DPA (and MSA or combined Customer Agreement + DPA schedule — whichever you recommend for a small SaaS), including a subprocessors exhibit and high-level TOMs. We are **pursuing SOC 2 Type I** readiness and are **not** certified — please avoid inventing SOC 2 / ISO / GDPR certification claims.

**Product facts (high level):**
- Multi-tenant SaaS; SMPL is generally a **processor / service provider** of Customer Data used in the product.
- **Read-only** toward customer GL/ERP (no write-back).
- Production stack: Vercel (web), Railway (API), Neon Postgres (**AWS us-east-1**), Resend, Anthropic (LLM), Stripe, GitHub. Other vendor **regions still TBD** — please do not promise “US-only” yet.
- **Sanity** (marketing CMS) and **HubSpot** (our sales CRM) are **outside** the product Customer Data DPA exhibit per our boundary decisions.
- AI: Anthropic only today; no foundation-model training on Customer Data by SMPL; numbers come from our engine/warehouse; narrative is fail-closed / evidence-bound per our approved P15 policy.

**Attached / linked from our repo:**
1. Counsel send package (summary + open questions)
2. DPA/MSA outline
3. Subprocessors list
4. System boundary (incl. locked Q&A)
5. Security one-pager
6. P15 AI/LLM policy (optional depth)

Open items I’d especially like your guidance on: legal entity/signatory block, offboarding deletion window (we’re thinking 30–90 days), subprocessor notice/objection, breach notice timing, liability caps (including whether breach is carved out), and governing law.

Happy to jump on a short call if useful. Thanks,

Matt Justice  
SMPL.ai  
mattjustice@smpl-ai.com

---

## Attachment checklist (repo paths)

Copy or export these before sending:

1. `docs/soc2/legal/COUNSEL_SEND_PACKAGE.md`
2. `docs/soc2/legal/DPA_MSA_OUTLINE.md`
3. `docs/soc2/02_subprocessors.md`
4. `docs/soc2/01_system_boundary.md`
5. `docs/soc2/SECURITY_ONE_PAGER.md`
6. `docs/soc2/policies/P15_ai_llm_data_handling.md` (recommended)

Optional: P04, P07, P08, P09 if counsel asks for more depth.

---

## After you send (Matt)

1. Note date/time sent and counsel firm in [../00_decision_log.md](../00_decision_log.md) (or reply in chat so scoreboard can update).
2. Keep R16 **open** until a customer-offerable draft exists (and until signed for the risk to fully close).
3. Do not mark “DPA done” on the scoreboard from send alone.
