# Incident Response Plan

> **STATUS: APPROVED** — Effective 2026-07-27. Approved by Matt Justice (executive sponsor).  
> Not legal advice. Not evidence of SOC 2 certification. Approving policies ≠ SOC 2 certified; open evidence items remain. SMPL is **not** SOC 2 certified until a CPA Type I report is in hand.

| Field | Value |
|-------|--------|
| Policy ID | P04 |
| Owner | Matt Justice (Security owner) |
| Applies to | Suspected or confirmed security / availability incidents affecting SMPL or customer data |
| Related criteria | Security; Availability |
| Version | 1.0 (companion note 2026-07-28) |
| Effective date | 2026-07-27 |
| Last expanded | 2026-07-28 (AI containment: machine-primary; P15 v1.1 Approved) |

---

## 1. Purpose

Define how SMPL detects, contains, eradicates, recovers from, and communicates about security and availability incidents.

## 2. Roles

| Role | During an incident | Current holder |
|------|---------------------|----------------|
| Security owner | Incident commander (or designates); decides severity & customer notice | Matt Justice |
| Engineering owner | Technical containment, forensics lite, restore | Matt Justice |
| Executive sponsor | Escalation; external comms approval for material incidents | Matt Justice |
| Ops / CS | Customer channel if notified | Matt Justice |

**Primary contact:** Matt Justice (executive / security / eng / ops for now).  
**Channel (working):** corporate email / phone — _[! Matt: confirm preferred IR intake channel]_.

## 3. What counts as an incident

Examples (not exhaustive):

- Unauthorized access to production systems or tenant data
- Suspected credential compromise / missing MFA on admin account
- Ransomware, malware, or destructive change in prod
- Prolonged unplanned outage affecting committed availability
- Accidental cross-tenant data exposure
- Subprocessor breach that may affect SMPL customers
- Exposure of secrets in git, logs, or public channels
- AI-generated commentary or narrative reaching a customer with a claim that does not resolve to verified engine/warehouse evidence (see P15 §4.7)

## 4. Severity (working model)

| Severity | Example | Response target (draft) |
|----------|---------|-------------------------|
| Sev1 | Confirmed breach of customer data; total prod outage | Immediate; eng + exec engaged |
| Sev2 | Likely compromise; major degradation; or a hallucinated/incorrect AI-generated financial claim delivered to a customer | Same business day |
| Sev3 | Limited impact; contained quickly | Next business day triage |
| Sev4 | Suspicious event; no confirmed impact | Track and investigate |

## 5. Process

1. **Detect / report** — Anyone reports to Matt Justice via the IR intake channel.
2. **Triage** — Confirm scope; assign severity; start timeline notes (who/what/when).
3. **Contain** — Revoke access, rotate secrets (Vercel/Railway/Neon/API keys), isolate systems as needed.
4. **Eradicate & recover** — Fix root cause; restore from known-good backup if needed ([P12](./P12_backup_and_restore.md)).
5. **Communicate** — Internal first; customer notification when legally/contractually required or material risk to their data (exec approval — Matt).
6. **Post-incident** — Blameless write-up within 10 business days for Sev1–2; update controls/policies if needed.

### Containment playbook (quick reference)

| Scenario | First actions |
|----------|---------------|
| Compromised admin account | Disable/reset account; rotate API keys & DB credentials; review audit logs |
| Suspected cross-tenant leak | Disable affected feature/path; snapshot evidence; notify exec; assess customer impact |
| Provider outage (Vercel/Railway/Neon) | Check status pages; communicate; failover only if pre-documented |
| Secret in git | Rotate immediately; purge history if needed; treat as Sev2+ |
| AI hallucination reaching customer | Identify affected output(s), freeze ID(s), and customer(s); **stop shipping** further bad commentary via technical controls (feature flag if present / disable narrative path / hotfix — fail closed); issue corrected output bound to freeze evidence; document root cause as grounding/validation / provenance / claim-verify / tie-out gate **fail-open** or freeze-binding defect — **not** “skipped human review”; humans handle IR / exceptions / periodic testing (see P15 §4.7–§4.8; [../controls/README.md](../controls/README.md)) |

## 6. Evidence to keep

- Timeline notes, decisions, who was notified
- Tickets / PR links for fixes
- Access revoke / secret rotation records
- Customer notification drafts (if any)

## 7. Tabletop

Run a lightweight tabletop at least annually (or before Type I fieldwork). Record date and attendees.

**Solo-founder pack:** [../runbooks/ir-tabletop.md](../runbooks/ir-tabletop.md) (~45–60 min; credential leak + AI hallucination scenarios). File notes from [../evidence/ir-tabletop-TEMPLATE.md](../evidence/ir-tabletop-TEMPLATE.md). Tabletop ≠ real incident; completing dated notes = operable-IR evidence. **[!]** Run before auditor fieldwork — pack ready; exercise not yet completed.

## 8. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | Matt Justice | 2026-07-27 |

---

_End of APPROVED P04_
