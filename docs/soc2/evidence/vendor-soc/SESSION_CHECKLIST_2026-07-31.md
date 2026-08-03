# Vendor SOC session checklist — 2026-07-31

**Owner:** Matt Justice  
**Goal:** Knock out P0 Trust Center downloads (login → NDA → Type II) in one sitting.  
**Honesty:** Readiness only — **not** SOC 2 certified. Public SOC 3 / marketing claims are **not** Type II `received`. Do not mark `received` without a private-store file (or documented portal-only review date).

**Companion docs:** [WORKING_PACK_2026-08.md](./WORKING_PACK_2026-08.md) (this-week hub) · [TRACKER.md](./TRACKER.md) · [REVIEW_CHECKLIST.md](./REVIEW_CHECKLIST.md) · [REQUEST_TEMPLATES.md](./REQUEST_TEMPLATES.md) · [PUBLIC_RESEARCH_2026-07-29.md](./PUBLIC_RESEARCH_2026-07-29.md) · [README.md](./README.md)

---

## Before you start (2 min)

- [ ] Use corporate email **mattjustice@smpl-ai.com** (or the account that owns each vendor console).
- [ ] Have browser ready for Google IdP / vendor MFA.
- [ ] Open [REQUEST_TEMPLATES.md](./REQUEST_TEMPLATES.md) in a second tab for paste-ready justification text.
- [ ] Confirm private store folder exists (see below). Prefer **outside git**.

### Where to store PDFs

| Priority | Path | Notes |
|----------|------|-------|
| **Preferred** | `~/Documents/SMPL/soc2/vendor-reports/` (or OneDrive/Google Drive **outside** the git tree) | Naming: `YYYY-MM-DD_<vendor>_<report-type>_period-YYYY-YYYY.pdf` |
| Optional | `docs/soc2/evidence/vendor-soc/private/` | Gitignored — still NDA material; clones risk if mis-committed |
| **Never** | Git commit / public PR / pasted report excerpts | Do not commit NDA PDFs |

Example: `2026-07-31_vercel_soc2-type2_2025-01-2025-12.pdf`

---

## Ordered P0 vendors (do in this order)

Estimate ~45–90 min if portals cooperate; Neon may need a 2-business-day wait after request.

### 1. Vercel — SOC 2 Type II

**Trust Center:** https://security.vercel.com/  
**Backup docs:** https://vercel.com/docs/security/compliance · help: privacy@vercel.com

| Step | Action |
|------|--------|
| 1 | Open Trust Center → **Get access** / sign in |
| 2 | Complete click-through **NDA** / access request (use [Vercel template](./REQUEST_TEMPLATES.md#vercel) if asked for justification) |
| 3 | Download **SOC 2 Type II** (not just marketing / ISO directory listing) |
| 4 | Save to private store with naming convention above |

- [ ] **Vercel Type II downloaded** → private store path: _______________________
- [ ] Period / report date noted: _______________________
- [ ] Tracker status ready to set: `nda signed` / `requested` / `received` (pick honest one)

---

### 2. Railway — SOC 2 Type II (+ optional public SOC 3)

**Trust Center:** https://trust.railway.com/  
**Backup docs:** https://docs.railway.com/enterprise/compliance

| Step | Action |
|------|--------|
| 1 | Open Trust Center → **sign in** with Railway account email |
| 2 | (Optional) Download public **SOC 3** — useful, **not** a Type II substitute |
| 3 | Request / complete NDA for **SOC 2 Type II** ([template](./REQUEST_TEMPLATES.md#railway)) |
| 4 | Download Type II → private store |

- [ ] **Railway Type II downloaded** (or `requested` / blocked with reason)
- [ ] Optional SOC 3 saved: yes / no
- [ ] Private store path: _______________________
- [ ] Period noted: _______________________

---

### 3. Neon — SOC 2 Type II (+ ISO if listed)

**Trust Center:** https://trust.neon.com/  
**Backup docs:** https://neon.com/docs/security/compliance · sales@neon.tech  
**Gate:** SOC 2 often **paid customers only**; access requests reviewed ~**2 business days**.

| Step | Action |
|------|--------|
| 1 | Open Trust Center → sign in as **paid** Neon customer |
| 2 | Request **SOC 2** (and ISO 27001/27701 if listed) ([template](./REQUEST_TEMPLATES.md#neon)) |
| 3 | If approved immediately: download Type II → private store |
| 4 | If pending: note request date; status stays `requested` until PDF lands |

- [ ] **Neon** access requested / NDA done
- [ ] Type II downloaded **or** waiting (~2 BD) — circle one
- [ ] Private store path (if any): _______________________
- [ ] Period noted: _______________________

---

### 4. Stripe — SOC 2 Type II (SOC 1 optional)

**Dashboard:** https://dashboard.stripe.com/settings/compliance · https://dashboard.stripe.com/settings/documents  
**Public SOC 3 (already noted — not Type II):** https://docs.stripe.com/security  
**Template if Dashboard empty:** [REQUEST_TEMPLATES.md#stripe](./REQUEST_TEMPLATES.md#stripe)

| Step | Action |
|------|--------|
| 1 | Sign in to Stripe Dashboard (MFA) |
| 2 | **Settings → Compliance** and/or **Documents** |
| 3 | Complete NDA / request if prompted → download **SOC 2 Type II** (SOC 1 if needed) |
| 4 | Save Type II to private store — do **not** treat existing SOC 3 as Type II |

- [ ] **Stripe Type II downloaded** (or `requested` / support ticket opened)
- [ ] Confirmed: public SOC 3 alone is **not** marked `received` for Type II target
- [ ] Private store path: _______________________
- [ ] Period noted: _______________________

---

### 5. Anthropic — SOC 2 Type II (+ ISO packs as available)

**Trust Portal:** https://trust.anthropic.com/  
**Claims FAQ (not a report):** https://privacy.claude.com/en/articles/10015870-what-certifications-has-anthropic-obtained  
**Template:** [REQUEST_TEMPLATES.md#anthropic](./REQUEST_TEMPLATES.md#anthropic)

| Step | Action |
|------|--------|
| 1 | Open Trust Portal → sign in (Google IdP) |
| 2 | Request / NDA for **SOC 2 Type II** + ISO 27001 / 42001 if offered |
| 3 | Download → private store |
| 4 | Align mental model with [P15](../../policies/P15_ai_llm_data_handling.md) (usage context only — not a report substitute) |

- [ ] **Anthropic Type II downloaded** (or `requested`)
- [ ] ISO packs if available: _______________________
- [ ] Private store path: _______________________
- [ ] Period noted: _______________________

---

### 6. Resend — SOC 2 Type II

**Direct download path:** https://resend.com/settings/documents  
**Marketing period claim (verify in PDF):** https://resend.com/security/soc-2 (docs say ~2025-02-01 → 2026-02-01)  
**How-to:** https://resend.com/docs/knowledge-base/downloading-documents  
**Template if missing:** [REQUEST_TEMPLATES.md#resend](./REQUEST_TEMPLATES.md#resend)

| Step | Action |
|------|--------|
| 1 | Log in to Resend |
| 2 | **Settings → Documents** |
| 3 | Download **SOC 2 Type II** → private store |
| 4 | Confirm period in PDF is still current |

- [ ] **Resend Type II downloaded**
- [ ] Period confirmed current: yes / no — _______________________
- [ ] Private store path: _______________________

---

## Bonus P1 (if time) — GitHub

**Org path:** GitHub Org → **Settings → Security → Compliance**  
**Docs:** https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/accessing-compliance-reports-for-your-organization  
**Hub:** https://github.com/trust-center/  
**Note:** Fuller SOC 2 Type II often **Enterprise Cloud** — record plan honestly if missing.

- [ ] Downloaded available reports (SOC 3 / ISO / CAIQ as offered)
- [ ] Type II available on current plan? yes / no / unknown
- [ ] Private store path(s): _______________________

---

## After session — reply format to update TRACKER

Paste this block back in chat (or edit [TRACKER.md](./TRACKER.md) yourself). **Only claim `received` when a Type II (or target report) file is in the private store.**

```text
Vendor SOC session — 2026-07-31

Vercel:     [researched|requested|nda signed|received|blocked] — period: ____ — file: ____
Railway:    [researched|requested|nda signed|received|blocked] — period: ____ — file: ____
Neon:       [researched|requested|nda signed|received|blocked] — period: ____ — file: ____ / waiting until ____
Stripe:     [public summary available|requested|nda signed|received|blocked] — Type II period: ____ — file: ____
Anthropic:  [researched|requested|nda signed|received|blocked] — period: ____ — file: ____
Resend:     [researched|requested|nda signed|received|blocked] — period: ____ — file: ____
GitHub(P1): [researched|requested|received|blocked|skipped] — what downloaded: ____ — plan note: ____

Private store root used: ~/Documents/SMPL/soc2/vendor-reports/  (or: ____)

Blockers / notes:
- ____

Do NOT mark PROGRESS vendor collection complete until P0 are at least `reviewed` (or honestly `blocked`).
Not SOC 2 certified.
```

Also after each real download:

1. Run [REVIEW_CHECKLIST.md](./REVIEW_CHECKLIST.md) (scope, period, exceptions).
2. Update [TRACKER.md](./TRACKER.md) status + **Next action** + date in Progress log.
3. Flip “Vendor report collected?” in [02_subprocessors.md](../../02_subprocessors.md) only after a real **review** skim.
4. Optional: sanitized one-liner in tracker notes — no NDA-secret excerpts.

---

## Session outcome (Matt fills)

| Vendor | Checkbox | Outcome status | Private file exists? |
|--------|----------|----------------|----------------------|
| Vercel | [ ] | | Y / N |
| Railway | [ ] | | Y / N |
| Neon | [ ] | | Y / N |
| Stripe Type II | [ ] | | Y / N |
| Anthropic | [ ] | | Y / N |
| Resend | [ ] | | Y / N |
| GitHub (bonus) | [ ] | | Y / N |

_Session kit prepared 2026-07-31. Public research baseline: 2026-07-29. No Type II faked as received._
