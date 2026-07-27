# Business Continuity / Disaster Recovery Policy

> **STATUS: DRAFT — NOT APPROVED**  
> Template for SOC 2 Type I readiness. Not company policy until approved.  
> Not legal advice. Not evidence of SOC 2 compliance. SMPL is **not** SOC 2 certified.  
> RTO/RPO figures below are **working targets**, not customer SLAs unless separately contracted.

| Field | Value |
|-------|--------|
| Policy ID | P11 |
| Owner | Matt Justice (Security / Engineering owner) |
| Applies to | Production financial intelligence platform availability |
| Related criteria | Availability |
| Version | 0.2-draft |
| Effective date | _TBD on approval_ |
| Last expanded | 2026-07-26 |

---

## 1. Purpose

Describe how SMPL plans to continue or restore service after significant disruption of production infrastructure — honest for a solo-founder SaaS on managed providers (Vercel, Railway, Neon).

## 2. Scope

Production components in [../01_system_boundary.md](../01_system_boundary.md). Customer source ERPs and end-user devices are out of scope.

## 3. Critical dependencies

| Dependency | Role | Failure mode |
|------------|------|--------------|
| Vercel | Customer UI / Auth.js edge | Site unavailable |
| Railway | API / AI / exports | App features fail |
| Neon | Postgres warehouse + auth | Data unavailable |
| Resend | Magic-link email | Login disrupted |
| GitHub | Source + deploy triggers | Cannot ship fixes |
| Stripe | Billing | New subs / portal may fail |
| Anthropic | Commentary only | Core numbers still available if API/warehouse up |

## 4. Working recovery targets (DRAFT)

| Metric | Working target | Notes |
|--------|----------------|-------|
| RTO (restore service) | Best effort; aim under 24h for Sev1 infra | Depends on provider status |
| RPO (data loss) | Neon backup window / PITR as configured | **[!]** Confirm Neon plan features |

Do **not** publish these as customer SLAs unless the MSA says so.

## 5. Recovery strategies

1. **Provider status** — Check Vercel / Railway / Neon / Resend status; wait or failover per provider guidance.
2. **Redeploy** — Redeploy last known-good frontend/API from GitHub → Vercel/Railway ([../CHANGE_MANAGEMENT.md](../CHANGE_MANAGEMENT.md), [P05](./P05_change_management_policy.md)).
3. **Data restore** — Follow [P12](./P12_backup_and_restore.md); prefer point-in-time restore over destructive recreate.
4. **Secrets** — Restore env from documented secret stores (Vercel/Railway — not from git).
5. **Auth path** — If Resend is down, communicate outage; do not bypass Auth.js with insecure workarounds.
6. **Comms** — Security/exec owner notifies affected customers for material outages ([P04](./P04_incident_response_plan.md)).

## 6. Single points of failure (honest)

- Small team / single owner concentration (Matt Justice holds all roles today) — accepted residual risk ([P10](./P10_risk_assessment.md) R01).
- No secondary region / multi-cloud failover currently documented.
- Mitigations: MFA, backups, documented deploy path, vendor reliance on their SOC/ISO programs where reports are collected.

## 7. Testing

- Backup restore test at least annually (or before Type I) — see [P12](./P12_backup_and_restore.md).
- Optional tabletop for DR scenarios with IR plan ([P04](./P04_incident_response_plan.md)).

## 8. Evidence

| Artifact | Example |
|----------|---------|
| This policy | Approved version + date |
| Restore test | P12 sign-off row |
| Deploy path | [../CHANGE_MANAGEMENT.md](../CHANGE_MANAGEMENT.md) |
| Outage notes | IR timeline for Sev1 availability events |

## 9. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | _DRAFT — not signed — Matt Justice must approve_ | |

---

_End of DRAFT P11_
