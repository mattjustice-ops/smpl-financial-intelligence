# Backup & Restore Policy

> **STATUS: DRAFT — NOT APPROVED**  
> High-priority stub for Type I readiness. Not company policy until approved.  
> Not legal advice. Not evidence of SOC 2 compliance.  
> **A restore test has not been claimed complete** — calendar and execute before Type I fieldwork.

| Field | Value |
|-------|--------|
| Policy ID | P12 |
| Owner | Matt Justice (Engineering / Security owner) |
| Applies to | Production Postgres (Neon) and critical config restore capability |
| Related criteria | Availability |
| Version | 0.1-draft |
| Effective date | _TBD on approval_ |
| Created | 2026-07-22 |

---

## 1. Purpose

Ensure customer and auth data can be restored from backup after loss, corruption, or destructive error.

## 2. What is backed up

| Asset | Mechanism (expected) | Owner |
|-------|----------------------|-------|
| Neon Postgres (warehouse + auth) | Neon automated backups / PITR per plan | Matt Justice |
| App code | GitHub | Matt Justice |
| Env / secrets | Vercel + Railway secret stores (not git) | Matt Justice |
| CMS content | Sanity (if in boundary) | Matt Justice |

**[!]** Matt: confirm Neon backup retention and PITR settings for production project; screenshot for evidence.

## 3. Restore process (high level)

1. Identify target point-in-time / backup snapshot.
2. Prefer restore to a **non-prod branch/project** first for validation.
3. Validate row counts / smoke queries for a sample org.
4. Promote or cut over only with exec/eng approval (Matt).
5. Record: date, who, backup ID, result, time to restore.

## 4. Restore test requirement

Before Type I fieldwork:

- [ ] Calendar a Neon restore test
- [ ] Execute restore to non-prod (or documented safe procedure)
- [ ] Capture evidence (screenshots, notes, timing)
- [ ] Sign off in review log below

| Test date | Tester | Result | Evidence location | Sign-off |
|-----------|--------|--------|-------------------|----------|
| | Matt Justice | _Not yet run_ | | |

## 5. Related

- Continuity context: [P11](./P11_business_continuity_disaster_recovery.md)
- Incidents needing restore: [P04](./P04_incident_response_plan.md)

## 6. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | _DRAFT — not signed — Matt Justice must approve_ | |

---

_End of DRAFT P12_
