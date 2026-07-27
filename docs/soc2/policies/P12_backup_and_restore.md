# Backup & Restore Policy

> **STATUS: APPROVED** — Effective 2026-07-27. Approved by Matt Justice (executive sponsor).  
> Not legal advice. Not evidence of SOC 2 certification. Approving policies ≠ SOC 2 certified; open evidence items remain. SMPL is **not** SOC 2 certified until a CPA Type I report is in hand.

| Field | Value |
|-------|--------|
| Policy ID | P12 |
| Owner | Matt Justice (Engineering / Security owner) |
| Applies to | Production Postgres (Neon) and critical config restore capability |
| Related criteria | Availability |
| Version | 1.0 |
| Effective date | 2026-07-27 |
| Last expanded | 2026-07-26 |

---

## 1. Purpose

Ensure customer and auth data can be restored from backup after loss, corruption, or destructive error — implementable with Neon managed backups / PITR and GitHub + env secret stores.

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
3. Validate row counts / smoke queries for a sample org (and that Org A ≠ Org B still holds).
4. Promote or cut over only with exec/eng approval (Matt Justice).
5. Record: date, who, backup ID, result, time to restore.
6. If restore is part of an incident, link notes to [P04](./P04_incident_response_plan.md).

## 4. Restore test requirement

Before Type I fieldwork (target: Week 3–4 per [../PROGRESS.md](../PROGRESS.md)):

- [x] Calendar a Neon restore test — runbook [../runbooks/neon-restore-test.md](../runbooks/neon-restore-test.md) (2026-07-27)
- [ ] Execute restore to **throwaway** Neon branch (prefer PITR / “Past data”; never change Railway `DATABASE_URL`)
- [ ] Capture evidence (sanitized counts, notes, timing)
- [ ] Sign off in review log below

| Test date | Tester | Result | Evidence location | Sign-off |
|-----------|--------|--------|-------------------|----------|
| 2026-07-27 | Cursor agent / Matt Justice | **Blocked** — no `NEON_API_KEY`; Console PITR branch not yet created | [../evidence/neon-restore-test-2026-07-27.md](../evidence/neon-restore-test-2026-07-27.md) · [../runbooks/neon-restore-test.md](../runbooks/neon-restore-test.md) | _Pending pass_ |

Approving this **policy** is not the same as completing the restore test. Both are required before booking Type I.

**Clarification:** Neon already provides PITR/backups. The restore test proves we can restore to a throwaway branch and validate — it does not invent new backup product features.

## 5. Retention interaction

Customer deletion requests may lag in backups until the backup window expires — disclose honestly ([P08](./P08_retention_and_deletion.md)).

## 6. Related

- Continuity context: [P11](./P11_business_continuity_disaster_recovery.md)
- Incidents needing restore: [P04](./P04_incident_response_plan.md)
- Risk: [P10](./P10_risk_assessment.md) R06

## 7. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | Matt Justice | 2026-07-27 |

---

_End of APPROVED P12_
