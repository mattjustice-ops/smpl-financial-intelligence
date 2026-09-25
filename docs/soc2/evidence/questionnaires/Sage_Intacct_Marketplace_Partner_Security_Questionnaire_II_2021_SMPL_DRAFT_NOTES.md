# Sage Intacct Marketplace Partner Security Questionnaire — SMPL DRAFT NOTES

**Status:** DRAFT for Matt review. Prefer under-claim. **Not SOC 2 certified.**

- **Filled workbook (Downloads):** `c:\Users\mattj\Downloads\Sage_Intacct_Marketplace_Partner_Security_Questionnaire_II_2021_SMPL_DRAFT.xlsx`
- **Filled workbook (repo):** `C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence\docs\soc2\evidence\questionnaires\Sage_Intacct_Marketplace_Partner_Security_Questionnaire_II_2021_SMPL_DRAFT.xlsx`
- **Source questionnaire:** `Sage Intacct - Marketplace Partner Security Questionnaire II 2021.xlsx`
- **Draft date:** 2026-08-04
- **Company:** SMPL / SMPL.ai (smpl-ai.com)
- **Completer:** Matt Justice (Founder; Executive Sponsor & Security Owner)
- **Product framing:** SaaS FP&A / financial intelligence — reads/reconciles; **no GL write-back**
- **Compliance framing:** Pursuing SOC 2 Type I readiness (Security + Availability + Confidentiality). **Not certified.**

## Counts

| Status | Count |
|--------|------:|
| Answered from docs | 41 |
| Assumed (verify) | 3 |
| Needs Matt confirmation | 6 |
| **Total items filled** | **50** |

## Needs Matt confirmation

- **Row 7 (Telephone):** Response=`To be confirmed` — Telephone not in soc2 docs
- **Row 21 (Major breach?):** Response=`No` — Confirm no historical breach to disclose
- **Row 22 (Cyber insurance):** Response=`No` — Confirm whether cyber insurance exists
- **Row 34 (Background screening):** Response=`N/A` — Confirm if any background screening exists
- **Row 56 (GDPR DPA):** Response=`No` — Confirm DPA status before send; still No unless customer-ready DPA exists
- **Row 57 (CCPA DPA):** Response=`No` — Same as GDPR DPA status

## Assumed (still verify)

- **Row 53 (Privacy owner):** Response=`Yes` — Confirm Matt wants to claim dedicated privacy owner vs N/A given Privacy deferred
- **Row 59 (SolarWinds impact):** Response=`No` — Confirm Matt has no SolarWinds exposure
- **Row 61 (MS on-prem zero-day impact):** Response=`No` — Confirm no on-prem Exchange exposure

## Top items before sending to Sage

1) Confirm NOT claiming SOC 2 certified anywhere in the package (draft already says No / readiness only).
2) Telephone number (row 7) — currently 'To be confirmed'.
3) Cyber insurance (row 22) — answered No; change only if a policy exists (do not invent limits).
4) Major breach history (row 21) — answered No; disclose if anything material exists.
5) GDPR/CCPA DPA (rows 56-57) — answered No; flip only if customer-ready DPA exists.
6) Background screening (row 34) — N/A for solo founder; confirm.
7) Legal entity / company name for Sage contracts if different from 'SMPL / SMPL.ai'.
8) Optional: whether row 12 should be Yes because GL account codes are stored (draft = No + explanation).
9) Privacy owner claim (row 53) — Yes as Matt; switch to N/A if preferred given Privacy deferred.
10) SolarWinds / MS on-prem (rows 59/61) — answered No based on stack; confirm.

## Intentionally under-claimed (No / N/A)

- No SMPL SOC 2 / ISO / PCI / SSAE18 report
- No Privacy Shield
- No formal security awareness / OWASP training program yet (P17 not started)
- No formal logging/monitoring policy yet (P14 not started)
- No annual pen test / vulnerability test program
- No customer-ready GDPR/CCPA DPA yet
- No published privacy policy URL
- No cyber insurance claimed

## Primary sources used

- `docs/soc2/PROGRESS.md`
- `docs/soc2/SECURITY_ONE_PAGER.md`
- `docs/soc2/01_system_boundary.md`
- `docs/soc2/02_subprocessors.md`
- `docs/soc2/04_policy_index.md` + policies P01-P12, P15
- Evidence: IR tabletop, neon restore, tenant isolation, access review, Dependabot
