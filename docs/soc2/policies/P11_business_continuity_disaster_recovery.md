# Business Continuity / Disaster Recovery Policy

> **STATUS: DRAFT — NOT APPROVED**  
> High-priority stub for Type I readiness. Not company policy until approved.  
> Not legal advice. Not evidence of SOC 2 compliance. RTO/RPO figures below are **working targets**, not SLAs sold to customers unless separately contracted.

| Field | Value |
|-------|--------|
| Policy ID | P11 |
| Owner | Matt Justice (Security / Engineering owner) |
| Applies to | Production financial intelligence platform availability |
| Related criteria | Availability |
| Version | 0.1-draft |
| Effective date | _TBD on approval_ |
| Created | 2026-07-22 |

---

## 1. Purpose

Describe how SMPL plans to continue or restore service after significant disruption of production infrastructure.

## 2. Critical dependencies

| Dependency | Role | Failure mode |
|------------|------|--------------|
| Vercel | Customer UI / Auth.js edge | Site unavailable |
| Railway | API / AI / exports | App features fail |
| Neon | Postgres warehouse + auth | Data unavailable |
| Resend | Magic-link email | Login disrupted |
| GitHub | Source + deploy triggers | Cannot ship fixes |
| Stripe | Billing | New subs / portal may fail |
| Anthropic | Commentary only | Core numbers still available if API up |

## 3. Working recovery targets (DRAFT)

| Metric | Working target | Notes |
|--------|----------------|-------|
| RTO (restore service) | Best effort; aim under 24h for Sev1 infra | Depends on provider status |
| RPO (data loss) | Neon backup window / PITR as configured | **[!]** Confirm Neon plan features |

Do **not** publish these as customer SLAs unless MSA says so.

## 4. Recovery strategies

1. **Provider status** — Check Vercel / Railway / Neon status; wait or failover per provider guidance.
2. **Redeploy** — Redeploy last known-good frontend/API from GitHub → Vercel/Railway ([../CHANGE_MANAGEMENT.md](../CHANGE_MANAGEMENT.md)).
3. **Data restore** — Follow [P12](./P12_backup_and_restore.md); prefer point-in-time restore over destructive recreate.
4. **Secrets** — Restore env from documented secret stores (not from git).
5. **Comms** — Security/exec owner notifies affected customers for material outages.

## 5. Single points of failure (honest)

- Small team / single owner concentration (Matt Justice holds all roles today).
- No secondary region / multi-cloud failover currently documented.
- Mitigations: MFA, backups, documented deploy path, vendor reliance on their SOC/ISO programs.

## 6. Testing

- Backup restore test at least annually (or before Type I) — see P12.
- Optional tabletop for DR scenarios with IR plan (P04).

## 7. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | _DRAFT — not signed — Matt Justice must approve_ | |

---

_End of DRAFT P11_
