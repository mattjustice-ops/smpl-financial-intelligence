# Neon restore test runbook (SOC 2 / P12)

> **Scope clarification:** This is **not** new backup/restore product functionality. Neon already provides managed backups / PITR. This runbook proves we can restore from those backups to a **throwaway** Neon branch, validate data, and file evidence — **without** changing production Railway `DATABASE_URL` or Vercel `AUTH_DATABASE_URL`.

| Field | Value |
|-------|--------|
| Related policy | [P12 Backup & Restore](../policies/P12_backup_and_restore.md) |
| Risk | [P10](../policies/P10_risk_assessment.md) R06 |
| Owner | Matt Justice |
| Production safety | **Never** point Railway/Vercel at the restore-test branch. Never run in-place restore on `main` / production. |

---

## Preferred restore kind: PITR child branch (true point-in-time)

Neon supports creating a **new child branch** from a parent’s history via `parent_timestamp` (API) or Console **Past data**. That is the preferred SOC 2 fire drill:

| Kind | What it proves | Safe for prod? |
|------|----------------|----------------|
| **PITR child branch** (`parent_timestamp` / Console “Past data”) | Can materialize DB state at a chosen timestamp onto a **throwaway** branch | Yes — prod untouched |
| **Branch fork at head** (no timestamp) | Can copy current head to a child branch (“branch copy” fire drill) | Yes — weaker than PITR; document honesty if used |
| **In-place restore** on production (`POST .../branches/{id}/restore`) | Rolls prod back | **Do not use for this test** |

API create-branch (preferred):

```http
POST https://console.neon.tech/api/v2/projects/{project_id}/branches
Authorization: Bearer $NEON_API_KEY
Content-Type: application/json
```

```json
{
  "branch": {
    "name": "restore-test-YYYY-MM-DD",
    "parent_id": "<production-or-main-branch-id>",
    "parent_timestamp": "<RFC3339 within history window>"
  },
  "endpoints": [{ "type": "read_write" }]
}
```

Omit `parent_timestamp` only if PITR is unavailable; then label the run a **branch-copy fire drill**, not true PITR.

---

## Matt — Console clicks (when `NEON_API_KEY` is missing)

1. Open [Neon Console](https://console.neon.tech) → production project (the one behind Railway `DATABASE_URL` / Vercel `AUTH_DATABASE_URL`).
2. Note **Settings → History retention / PITR window** (screenshot optional for evidence).
3. **Branches** → **New branch**.
4. Name: `restore-test-2026-07-27` (or today’s date).
5. Parent: production / `main` (default branch).
6. Include: **Past data** (not “Current data”, not “Schema only”).
7. Pick a restore point timestamp **inside** the history window (e.g. ~1 hour ago, or a known quiet time). Write it down (UTC).
8. Create compute / endpoint so the branch is connectable.
9. Open the new branch → **Connection details** → copy the **branch** connection string (host will **not** be the production endpoint).
10. Paste that connection string to the agent/operator in chat (or a local env var). **Do not** paste production URL. **Do not** put it in git.
11. After validation evidence is captured, delete the branch in Console (or leave named `restore-test-*` for Matt to delete).

Optional API key path (faster next time): Neon Console → Account → API keys → create key → set `NEON_API_KEY` in a local secret file (gitignored) or shell env. Also note `NEON_PROJECT_ID` from Settings.

---

## Validation SQL (run only against throwaway branch)

Connect with `psql` or Python/`psycopg`. Confirm host ≠ production endpoint before running.

```sql
-- 1) Connectivity
SELECT current_database() AS db, current_user AS usr, now() AT TIME ZONE 'utc' AS utc_now;

-- 2) Key tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'organizations', 'users', 'organization_members',
    'customers', 'subscriptions', 'invoices', 'gl_actuals',
    'warehouse_csv_rows', 'mrr_waterfall'
  )
ORDER BY 1;

-- 3) Sanitized row counts (no PII)
SELECT 'organizations' AS tbl, COUNT(*)::bigint AS n FROM organizations
UNION ALL SELECT 'users', COUNT(*) FROM users
UNION ALL SELECT 'organization_members', COUNT(*) FROM organization_members
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'subscriptions', COUNT(*) FROM subscriptions
UNION ALL SELECT 'invoices', COUNT(*) FROM invoices
UNION ALL SELECT 'gl_actuals', COUNT(*) FROM gl_actuals
UNION ALL SELECT 'warehouse_csv_rows', COUNT(*) FROM warehouse_csv_rows
UNION ALL SELECT 'mrr_waterfall', COUNT(*) FROM mrr_waterfall
ORDER BY 1;

-- 4) Demo Co spot-check (id only; no email dumps)
SELECT id, name, plan, status
FROM organizations
WHERE id = '8571e520-0687-4516-bdee-379f37c58c1f';

SELECT COUNT(*) AS demo_member_rows
FROM organization_members
WHERE organization_id = '8571e520-0687-4516-bdee-379f37c58c1f';
```

Pass criteria:

- Connection succeeds on restore-test host.
- Core auth tables present (`organizations`, `users`, `organization_members`).
- Warehouse tables present as applicable (missing table = note; fail only if unexpected empty disaster).
- Demo Co org row present (or documented absent if that org was deleted before restore point).
- Counts recorded in sanitized evidence markdown (no connection strings, no emails, no dumps).

---

## Evidence to file

| Artifact | Path |
|----------|------|
| This runbook + run log | `docs/soc2/runbooks/neon-restore-test.md` (this file) |
| Sanitized counts / pass-fail | `docs/soc2/evidence/neon-restore-test-YYYY-MM-DD.md` |
| P12 sign-off row | [P12](../policies/P12_backup_and_restore.md) §4 |
| Progress | [PROGRESS.md](../PROGRESS.md), `frontend/lib/compliance/progress.ts` |
| Risk | Close/update R06 notes in [P10](../policies/P10_risk_assessment.md) when pass |

Do **not** commit connection strings, API keys, or `SELECT *` PII dumps. Sensitive scratch files: `docs/soc2/evidence/*.local.md` (gitignored).

---

## Cleanup

Prefer delete the throwaway branch via API/Console after evidence is written. If left for Matt: keep the `restore-test-YYYY-MM-DD` name only.

---

## Run log

### Attempt 2026-07-27 (earlier) — blocked (no Neon API key)

| Field | Value |
|-------|--------|
| Started (UTC) | 2026-07-27 ~22:41 UTC (agent session local 15:41 PDT) |
| Operator | Cursor agent (on behalf of Matt Justice) |
| Result | **Blocked** — no API key / Console branch yet |
| Evidence stub | [../evidence/neon-restore-test-2026-07-27.md](../evidence/neon-restore-test-2026-07-27.md) (superseded by pass below) |

### Attempt 2026-07-27 (retry) — Pass (neonctl OAuth + PITR branch)

| Field | Value |
|-------|--------|
| Started (UTC) | 2026-07-27 ~23:28 UTC (agent session local ~16:28 PDT) |
| Operator | Cursor agent (on behalf of Matt Justice) |
| Auth | `npx neonctl auth` — browser OAuth; Matt approved promptly |
| Project | `smpl-auth-prod` / `hidden-scene-76708131` |
| Branch created? | **Yes** — `restore-test-2026-07-27` (`br-damp-poetry-aq87hjrl`) |
| Restore kind | **PITR child branch** — requested `--parent 2026-07-27T22:00:00Z`; Neon resolved `parent_timestamp=2026-07-27T19:38:21Z`, `parent_lsn=0/FEAEC88`, `init_source=parent-data` |
| Throwaway host (no secrets) | `ep-quiet-bird-aqicczkz.c-8.us-east-1.aws.neon.tech` |
| Validation | **Pass** — core + warehouse tables present; Demo Co org present; sanitized counts filed |
| Result | **Pass** |
| Production `DATABASE_URL` / Railway | **Unchanged** |
| Cleanup | Branch left named for Matt to delete when convenient |
| Evidence | [../evidence/neon-restore-test-2026-07-27.md](../evidence/neon-restore-test-2026-07-27.md) |

---

_End of runbook_
