# Neon restore test evidence — 2026-07-27

> Sanitized evidence only. No connection strings, API keys, passwords, or PII dumps.

## Clarification

This exercise validates restore from **Neon’s existing** PITR/backups onto a **throwaway** branch. It does **not** add product backup features and must **not** change production Railway `DATABASE_URL`.

## Status: PASS

| Field | Value |
|-------|--------|
| Date | 2026-07-27 |
| Tester | Cursor agent / Matt Justice |
| Restore kind | **PITR child branch** (`parent_timestamp` / `init_source=parent-data`) |
| Pass / fail | **Pass** |
| Project | `smpl-auth-prod` (`hidden-scene-76708131`) |
| Parent branch | `production` (`br-wild-bread-aqd4clug`) |
| Requested restore point | `2026-07-27T22:00:00Z` (via `neonctl branches create --parent <timestamp>`) |
| Neon-resolved `parent_timestamp` | `2026-07-27T19:38:21Z` |
| Parent LSN | `0/FEAEC88` |
| Throwaway branch name | `restore-test-2026-07-27` (`br-damp-poetry-aq87hjrl`) |
| Throwaway endpoint host (no secrets) | `ep-quiet-bird-aqicczkz.c-8.us-east-1.aws.neon.tech` |
| Branch created (UTC) | `2026-07-27T23:30:42Z` |
| Validation (UTC) | `2026-07-27T23:43:37Z` (~13 min create → validate incl. waits) |
| Auth method | `npx neonctl auth` (browser OAuth; Matt approved) |
| Production touched? | **No** — Railway / Vercel URLs not modified; validation only on throwaway host |

### Method

1. `npx neonctl auth` — browser OAuth completed.
2. Listed org `SMPL.ai` projects → production project `smpl-auth-prod`.
3. Created throwaway branch `restore-test-2026-07-27` from production with `--parent 2026-07-27T22:00:00Z` (PITR; not head fork).
4. Confirmed branch ready; host ≠ production endpoint.
5. Ran runbook validation SQL against throwaway connection only.
6. Branch left named `restore-test-2026-07-27` for Matt to delete when convenient.

## Validation results

| Check | Result |
|-------|--------|
| Connection to throwaway host | **Pass** — `neondb` / `neondb_owner` |
| Tables: organizations / users / organization_members | **Pass** — all present |
| Warehouse tables present (customers, subscriptions, invoices, gl_actuals, …) | **Pass** — all nine expected tables present |
| Row counts (sanitized) | **Pass** — see below |
| Demo Co org `8571e520-0687-4516-bdee-379f37c58c1f` | **Pass** — present (`SMPL Demo Co`, plan `enterprise`, status `pending`); 3 member rows |
| Timing (create → validate) | ~13 minutes (incl. compute ready wait) |

### Row counts (sanitized)

| Table | Count |
|-------|------:|
| organizations | 9 |
| users | 3 |
| organization_members | 4 |
| customers | 14 |
| subscriptions | 20 |
| invoices | 2 |
| gl_actuals | 5530 |
| warehouse_csv_rows | 0 |
| mrr_waterfall | 2 |

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Tester | Cursor agent (on behalf of Matt Justice) | 2026-07-27 | Pass — PITR throwaway validated |
| Security owner | Matt Justice | 2026-07-27 | OAuth approved; evidence filed |

Related: [P12](../policies/P12_backup_and_restore.md) · [runbook](../runbooks/neon-restore-test.md)
