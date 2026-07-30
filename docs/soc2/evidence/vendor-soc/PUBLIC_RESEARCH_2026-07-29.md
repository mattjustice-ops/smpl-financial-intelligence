# Vendor SOC — public Trust Center research — 2026-07-29

> Readiness packaging only. **Not** SOC 2 certified.  
> Agent had **no** Matt console login / no Cursor Allow for vendor dashboards.  
> Marketing pages and public SOC 3 summaries are **not** Type II reports.

## Method

Visited public compliance docs and Trust Center landing pages for P0 vendors (+ GitHub). Recorded what is publicly claimable vs what requires login / NDA / paid-customer access. Did **not** invent downloads or mark Type II `received`.

## Results summary

| Vendor | Public without Matt login | Requires Matt login / NDA / paid | Agent outcome |
|--------|---------------------------|----------------------------------|---------------|
| **Vercel** | Compliance docs (SOC 2 Type II claimed; ISO 27001:2022 + Schellman directory link); Trust Center overview | SafeBase **Get access** for SOC 2 / pentest / PCI packs | `researched` — no Type II PDF |
| **Railway** | Docs claim SOC 2 Type II + SOC 3; blog: SOC 3 public download | Type II, pentest, HIPAA via Trust Center (account email) | `researched` — SOC 3 not pulled (UI); no Type II |
| **Neon** | Docs claim SOC 2 / SOC 3 / ISO; Trust Center overview; **SOC 2 = paid customers only** | Trust Center request (~2 business days) | `researched` — no Type II PDF |
| **Stripe** | **Public SOC 3 PDF** (period 2024-10-01 → 2025-09-30; Sec/Avail/Conf) | SOC 1 / SOC 2 Type II via Dashboard Compliance/Documents | `public summary available` — SOC 3 in gitignored `private/`; **not** Type II |
| **Anthropic** | Certifications FAQ (SOC 2 I/II, ISO 27001, ISO 42001 claimed) | Trust Portal document requests | `researched` — portal interactive; no PDF |
| **Resend** | SOC 2 marketing page (Type II; period 2025-02-01 → 2026-02-01; Advantage Partners) | Settings → Documents (logged in) | `researched` — no PDF |
| **GitHub** | Trust Center hub FAQs; docs list org Compliance downloads (SOC 3, CSA CAIQ, ISO 27001) | Org Settings → Security → Compliance; Type II often Enterprise | `researched` — no PDF |

## Public links kept (safe to cite in git)

| Artifact | URL | Notes |
|----------|-----|-------|
| Vercel compliance docs | https://vercel.com/docs/security/compliance | Claims SOC 2 Type II + ISO |
| Vercel Trust Center | https://security.vercel.com/ | Access-gated reports |
| Vercel ISO listing | https://www.schellman.com/certificate-directory?certificateNumber=1868222-1 | Public certificate directory entry |
| Railway compliance docs | https://docs.railway.com/enterprise/compliance | Points to Trust Center |
| Railway Trust Center | https://trust.railway.com/ | SOC 3 public / Type II gated (per Railway blog) |
| Neon compliance docs | https://neon.com/docs/security/compliance | Points to Trust Center |
| Neon Trust Center | https://trust.neon.com/ | SOC 2 paid-only banner |
| Neon security | https://neon.com/security | Mentions SOC 3 without NDA via Trust Center |
| Stripe security | https://docs.stripe.com/security | Links public SOC 3 |
| Stripe SOC 3 (public) | https://docs.stripecdn.com/ebe9bebbdc5210a59ca18de4917ff3b152961a83fa3a98fbb81c758792472389.pdf | Summary report — not Type II |
| Anthropic certifications FAQ | https://privacy.claude.com/en/articles/10015870-what-certifications-has-anthropic-obtained | Claims list; docs via Trust Portal |
| Anthropic Trust Portal | https://trust.anthropic.com/ | Login for copies |
| Resend SOC 2 page | https://resend.com/security/soc-2 | Marketing + period; download via Documents |
| Resend Documents how-to | https://resend.com/docs/knowledge-base/downloading-documents | Login required |
| GitHub Trust Center | https://github.com/trust-center/ | Hub / FAQs |
| GitHub org compliance docs | https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/accessing-compliance-reports-for-your-organization | Org Settings path |

## Local private store (gitignored — not in git)

| File | Source | Claim |
|------|--------|-------|
| `private/2026-07-29_stripe_soc3_2024-10-2025-09.pdf` | Public Stripe CDN link above | **SOC 3** summary only — **not** SOC 2 Type II |

No other vendor PDFs downloaded. Do **not** commit NDA-bound Type II reports if Matt later obtains them — keep in `private/` or outside the repo.

## What this does **not** close

- Vendor SOC collection scoreboard item remains **[~] / in_progress**
- No P0 Type II marked `received` or `reviewed`
- Customer DPA / R16 unchanged (separate legal workstream)
