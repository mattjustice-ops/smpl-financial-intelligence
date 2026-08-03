# Vendor SOC working pack — week of 2026-08-03+

> **INTERNAL — FOR MATT THIS WEEK**  
> Readiness only. **Not** SOC 2 certified.  
> Public research is done; Railway + Neon + Stripe + Anthropic Type II **received** (review pending); Vercel waiting; Resend still open. Do not invent PDFs or flip statuses without a private-store file.  
> Agents do **not** log into vendor portals or email vendors.

| Field | Value |
|-------|--------|
| Workstream | Vendor SOC / ISO reports (P09) — scoreboard `[~]` |
| As of | 2026-08-03 |
| Session checklist (ordered clicks) | [SESSION_CHECKLIST_2026-07-31.md](./SESSION_CHECKLIST_2026-07-31.md) |
| Status board (source of truth) | [TRACKER.md](./TRACKER.md) |
| Request copy | [REQUEST_TEMPLATES.md](./REQUEST_TEMPLATES.md) |
| Public research baseline | [PUBLIC_RESEARCH_2026-07-29.md](./PUBLIC_RESEARCH_2026-07-29.md) |
| Post-download review | [REVIEW_CHECKLIST.md](./REVIEW_CHECKLIST.md) |

---

## 1. Honest status board (do not inflate)

| Vendor | Tier | Target report | Status (as of pack) | File in private store? |
|--------|------|---------------|---------------------|------------------------|
| Vercel | P0 | SOC 2 Type II | `requested` (waiting approval) | **No** |
| Railway | P0 | SOC 2 Type II | `received` (review pending) | **Yes** (Type II + bridge; outside git) |
| Neon | P0 | SOC 2 Type II (+ ISO if listed) | `received` (review pending) | **Yes** (Type 2 + HIPAA 2026; outside git) |
| Stripe | P0 | SOC 2 Type II (+ SOC 1 optional) | `received` (review pending) | **Yes** (current Type II + bridge + previous archive; outside git) |
| Anthropic | P0 | SOC 2 Type II (+ ISO packs) | `received` (review pending) | **Yes** (SOC 2 Type II + CSA STAR L2; SOC 3 bonus; outside git) |
| Resend | P0 | SOC 2 Type II | `researched` | **No** |
| GitHub | P1 | SOC 2 / SOC 3 / ISO (plan-dependent) | `researched` | **No** |

**Legit path:** `researched` → `requested` / `nda signed` → `received` → `reviewed`.  
**Never:** treat marketing pages or public SOC 3 as Type II `received`.

Scoreboard stays `[~]` until P0 are at least honestly `reviewed` (or documented `blocked`).

---

## 2. Where to store files (never commit NDA PDFs)

| Priority | Path | Commit? |
|----------|------|---------|
| **Preferred** | `~/Documents/SMPL/soc2/vendor-reports/` (or OneDrive/Google Drive **outside** the git tree) | **No** |
| Optional | `docs/soc2/evidence/vendor-soc/private/` (gitignored) | **No** — still NDA risk if mis-committed |
| **Never** | Git commit, public PR, pasted report excerpts / exception tables | **No** |

**Naming:** `YYYY-MM-DD_<vendor>_<report-type>_period-YYYY-YYYY.pdf`  
Example: `2026-08-05_vercel_soc2-type2_2025-01-2025-12.pdf`

Also store **bridge letters** (if offered when Type II period is stale) with the same convention, e.g. `..._bridge-letter_asof-YYYY-MM-DD.pdf`.

After each real download: update [TRACKER.md](./TRACKER.md) only — never paste confidential findings into git.

---

## 3. P0 download targets (exact)

Do in this order (~45–90 min if portals cooperate; Neon may wait ~2 business days).

| # | Vendor | Trust Center / portal | Login notes | Download target(s) | Bridge letter? |
|---|--------|----------------------|-------------|--------------------|----------------|
| 1 | **Vercel** | https://security.vercel.com/ · docs: https://vercel.com/docs/security/compliance · help: privacy@vercel.com | Corporate email; SafeBase **Get access** + click-through NDA | **SOC 2 Type II** (not ISO directory listing alone) | If Type II period ended >3 months ago and portal offers one |
| 2 | **Railway** | https://trust.railway.com/ · docs: https://docs.railway.com/enterprise/compliance | Sign in with **Railway account** email | **SOC 2 Type II**; optional public **SOC 3** (useful, **not** Type II substitute) | Same rule |
| 3 | **Neon** | https://trust.neon.com/ · docs: https://neon.com/docs/security/compliance · sales@neon.tech | **Paid** customer login; requests often reviewed ~**2 BD** | **SOC 2 Type II**; ISO 27001/27701 if listed | Same rule |
| 4 | **Stripe** | Dashboard → [Compliance](https://dashboard.stripe.com/settings/compliance) / [Documents](https://dashboard.stripe.com/settings/documents) · public SOC 3 already noted | Stripe Dashboard + MFA | **SOC 2 Type II** (SOC 1 optional). Public SOC 3 ≠ Type II | Same rule |
| 5 | **Anthropic** | https://trust.anthropic.com/ · FAQ (claims only): https://privacy.claude.com/en/articles/10015870-what-certifications-has-anthropic-obtained | Google IdP / corporate email | **SOC 2 Type II**; ISO 27001 / 42001 if offered | Same rule |
| 6 | **Resend** | https://resend.com/settings/documents · how-to: https://resend.com/docs/knowledge-base/downloading-documents · marketing period claim: https://resend.com/security/soc-2 | Resend login | **SOC 2 Type II**; confirm period in PDF | Same rule |

**Bonus P1 — GitHub:** Org → **Settings → Security → Compliance** · hub: https://github.com/trust-center/ · docs: https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/accessing-compliance-reports-for-your-organization  
Download what the plan exposes; note honestly if Type II needs Enterprise Cloud.

Paste-ready justification text: [REQUEST_TEMPLATES.md](./REQUEST_TEMPLATES.md).

---

## 4. After each download — review (before flipping tracker)

Use the full checklist: [REVIEW_CHECKLIST.md](./REVIEW_CHECKLIST.md).

Minimum skim:

1. **Report type** = SOC 2 **Type II** (or target type you requested) — not Type I only if you needed Type II; not SOC 3 alone for P0 Type II rows.
2. **Period / report date** current enough for diligence (note end date; pull bridge letter if stale and available).
3. **Scope** covers how SMPL uses the service (hosting / DB / payments / LLM / email as applicable).
4. **Exceptions / qualified opinions** — note existence in tracker (sanitized one-liner); do **not** paste confidential tables into git.
5. Then set status `received` → after skim `reviewed`. Flip “Vendor report collected?” in [02_subprocessors.md](../../02_subprocessors.md) only after real review.

---

## 5. Session outcome block (paste back after portal work)

```text
Vendor SOC session — YYYY-MM-DD

Vercel:     [researched|requested|nda signed|received|reviewed|blocked] — period: ____ — file: ____
Railway:    [researched|requested|nda signed|received|reviewed|blocked] — period: ____ — file: ____
Neon:       [researched|requested|nda signed|received|reviewed|blocked] — period: ____ — file: ____ / waiting until ____
Stripe:     [public summary available|requested|nda signed|received|reviewed|blocked] — Type II period: ____ — file: ____
Anthropic:  [researched|requested|nda signed|received|reviewed|blocked] — period: ____ — file: ____
Resend:     [researched|requested|nda signed|received|reviewed|blocked] — period: ____ — file: ____
GitHub(P1): [researched|requested|received|reviewed|blocked|skipped] — what downloaded: ____ — plan note: ____

Private store root: ~/Documents/SMPL/soc2/vendor-reports/  (or: ____)
Bridge letters pulled: ____

Blockers / notes:
- ____

Do NOT mark PROGRESS vendor collection complete until P0 are at least `reviewed` (or honestly `blocked`).
Not SOC 2 certified.
```

---

## 6. Stakeholder-safe language

| Say | Do not say |
|-----|------------|
| Vendor SOC collection **in progress** — Trust Centers researched; downloading Type II under NDA | “We have all vendor SOC 2 reports” |
| Pursuing **SOC 2 Type I** readiness | “SOC 2 certified” / “SOC 2 compliant” |
| Stripe Type II + bridge **received** (review pending); public SOC 3 also on file | Treating SOC 3 alone as Type II complete |
| Reports stored **privately under NDA** (not in public git) | Pasting report findings into public materials |

Optional spoken line:  
“We’ve mapped every product subprocessor Trust Center and are pulling Type II reports into a private folder this week. We’re pursuing Type I readiness — we’re not certified, and we don’t claim vendor reports we haven’t reviewed.”

---

## 7. Explicit non-goals

- Do **not** invent Type II PDFs, periods, auditor names, or exception text.
- Do **not** mark `received` / `reviewed` / scoreboard `[x]` without a private-store file (or documented portal-only review date).
- Do **not** clear completed Pass evidence elsewhere to create urgency.
- Do **not** email vendors unless Matt asks.
- CPA outreach stays a separate `[!]` track — leave alone.

---

## 8. Ordered next actions (Matt)

1. Create private folder `~/Documents/SMPL/soc2/vendor-reports/` (or confirm OneDrive equivalent).
2. Run [SESSION_CHECKLIST_2026-07-31.md](./SESSION_CHECKLIST_2026-07-31.md) for P0 #1–#6 (Vercel → … → Resend).
3. For each download: run [REVIEW_CHECKLIST.md](./REVIEW_CHECKLIST.md); update [TRACKER.md](./TRACKER.md).
4. If Neon (or others) pending: leave `requested` + date; do not fake `received`.
5. Bonus: GitHub org Compliance if time.
6. Reply with the session outcome block (or edit TRACKER yourself).

Companion legal track (separate): [DPA_COUNSEL_CHASE_PACK.md](../../DPA_COUNSEL_CHASE_PACK.md) — R16 still open.

---

_End of Vendor SOC working pack. Not SOC 2 certified._
