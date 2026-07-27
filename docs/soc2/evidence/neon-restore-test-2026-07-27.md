# Neon restore test evidence — 2026-07-27

> Sanitized evidence only. No connection strings, API keys, passwords, or PII dumps.

## Clarification

This exercise validates restore from **Neon’s existing** PITR/backups onto a **throwaway** branch. It does **not** add product backup features and must **not** change production Railway `DATABASE_URL`.

## Status: BLOCKED — credentials

| Field | Value |
|-------|--------|
| Date | 2026-07-27 |
| Tester | Cursor agent / Matt Justice |
| Restore kind | **Not performed** (neither PITR child branch nor head fork) |
| Pass / fail | **Blocked** (cannot create throwaway branch without Neon API or Console action) |
| Restore point timestamp | _Pending Matt_ |
| Throwaway branch name | Planned: `restore-test-2026-07-27` |
| Production touched? | **No** — Railway / Vercel URLs not modified; prod DB not used for validation |

### Blocker

- `NEON_API_KEY` absent from local env files and shell.
- Cannot call Neon `POST /projects/{id}/branches` with `parent_timestamp`.
- Awaiting Matt to create **Past data** branch in Neon Console (see [runbook](../runbooks/neon-restore-test.md)) and provide the **restore-test** connection string only.

## Validation results (to fill after branch exists)

| Check | Result |
|-------|--------|
| Connection to throwaway host | _Pending_ |
| Tables: organizations / users / organization_members | _Pending_ |
| Warehouse tables present (customers, subscriptions, invoices, gl_actuals, …) | _Pending_ |
| Row counts (sanitized) | _Pending_ |
| Demo Co org `8571e520-0687-4516-bdee-379f37c58c1f` | _Pending_ |
| Timing (create → validate) | _Pending_ |

### Row counts (template)

| Table | Count |
|-------|------:|
| organizations | |
| users | |
| organization_members | |
| customers | |
| subscriptions | |
| invoices | |
| gl_actuals | |
| warehouse_csv_rows | |
| mrr_waterfall | |

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Tester | | | _Pending successful run_ |
| Security owner | Matt Justice | | _Pending successful run_ |

Related: [P12](../policies/P12_backup_and_restore.md) · [runbook](../runbooks/neon-restore-test.md)
