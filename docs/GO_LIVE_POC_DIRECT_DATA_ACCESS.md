# POC path A — Direct data access (white-glove)

**Goal:** Enterprise prospects give SMPL read access to their data; ops loads the warehouse; customer logs into `/app` with their metrics — no self-serve upload required.

**Tracked on:** `/progress` → **poc-0**  
**Best for:** Mid-market / enterprise POCs where IT prefers not to upload files into a vendor UI.

**Companion doc:** `GO_LIVE_POC_ONBOARDING.md` (path B — self-serve CSV + AI mapping).

---

## When to use which path

| Path | Typical buyer | SMPL effort per deal | Product build |
|------|---------------|----------------------|---------------|
| **A. Direct access** (this doc) | Enterprise, security-conscious | Higher ops; lower customer friction | **Playbook + scripts today** |
| **B. Self-serve CSV** | Smaller teams, fast trials | Lower ops at scale | **poc-1 … poc-3** (in progress) |

**gl-7 (first paying customer)** can close on **path A** while path B is still being built.

---

## End-to-end flow

```
1. Sales / CS agrees POC scope + data sources
2. Legal / security: DPA + access method (read-only)
3. provision-prod-customer.ps1  → new org + invite
4. Customer grants access (Snowflake share, S3 bucket, SFTP, ERP export)
5. SMPL ops: extract → normalize → load warehouse (setup-prod-warehouse.ps1 or custom)
6. Customer: magic link → /app (enterprise plan recommended for full tabs)
7. Validation call: key metrics tie-out
```

---

## Supported access methods (choose per customer)

### 1. Snowflake secure share (preferred when customer is on Snowflake)

**Customer provides:**

- Secure data share to SMPL Snowflake account **or** read-only service user + warehouse
- Tables/views: GL, subscriptions/ARR, pipeline, headcount (scope per POC SOW)

**SMPL ops:**

- Export to CSV in SMPL canonical shape **or** direct ETL into Neon (future)
- Load with `setup-prod-warehouse.ps1 -OrganizationId <uuid> -CsvFolder <staging>`

**Security:** Read-only role; no write-back; document share name and revocation after POC.

---

### 2. Cloud object storage (S3, GCS, Azure Blob, Cloudflare R2)

**Customer provides:**

- Bucket path with periodic exports (CSV/Parquet)
- IAM: read-only for SMPL IP or access keys in secrets manager

**SMPL ops:**

- Download to secure staging folder (not committed to git)
- Validate headers; manual column map if needed (feeds future poc-2 mapper)
- `setup-prod-warehouse.ps1` or `demo-csv` upload against prod API for exact-format files

---

### 3. ERP / finance system export (NetSuite, QuickBooks, Sage, etc.)

**Customer provides:**

- Scheduled CSV/Excel exports to SFTP or shared drive
- Chart of accounts + transaction detail for POC period

**SMPL ops:**

- Map to SMPL schema (spreadsheet or script); document mapping in customer folder
- Load via warehouse scripts

---

### 4. Secure file drop (SFTP / OneDrive / Google Drive)

**Customer provides:**

- Time-limited share or SFTP credentials

**SMPL ops:**

- Same as object storage — stage locally, load to Neon with org ID

---

## Ops commands (production)

### Step 1 — Provision org + invite

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence

$env:DATABASE_URL = "postgresql://..."   # Neon prod

.\scripts\provision-prod-customer.ps1 `
  -Email admin@customer.com `
  -OrganizationName "Acme Corp" `
  -Plan enterprise
```

Save the printed **Organization ID**.

### Step 2 — Load warehouse

```powershell
.\scripts\setup-prod-warehouse.ps1 `
  -DatabaseUrl $env:DATABASE_URL `
  -OrganizationId "<customer-org-uuid>" `
  -CsvFolder "D:\smpl-staging\acme-poc"
```

Use `-ListOnly` first to preview files. Use `-SkipBundledDemo` when loading only customer files.

### Step 3 — Verify

```powershell
.\scripts\check-login-access.ps1 -Email admin@customer.com
.\scripts\list-prod-organizations.ps1
```

Customer signs in at https://smpl-financial-intelligence.vercel.app/login → `/app`.

---

## Security checklist (every direct-access POC)

- [ ] Written scope: which systems, which date range, which entities
- [ ] Read-only access; no production write credentials
- [ ] Credentials stored in team password manager / Railway secrets — **never** in git
- [ ] Staging copy deleted or encrypted at rest after load (define retention)
- [ ] Customer notified when POC ends and access can be revoked
- [ ] Neon row scoped to `organization_id` — confirm org ID before load
- [ ] Rotate any credentials shared in email/Slack

---

## Data quality / validation (before customer demo)

| Check | How |
|-------|-----|
| ARR tie-out | Compare ending ARR to customer source for close month |
| Revenue | IS revenue vs ARR movement sanity |
| Headcount | Workforce tab vs HR export |
| Period coverage | POC SOW months present in warehouse |
| Org isolation | Login as customer — no other org data visible |

Document results in customer onboarding notes (internal).

---

## poc-0 definition of done

Mark **poc-0** done on `/progress` when **all** of the following are true:

- [x] This playbook published (`GO_LIVE_POC_DIRECT_DATA_ACCESS.md`)
- [ ] One real prospect POC completed on prod using direct access (not SMPL Demo Co seed only)
- [ ] Security checklist signed off for that POC
- [ ] Customer validation call completed (metrics agreed)

---

## Future: productized connectors

After 2–3 white-glove loads, prioritize one connector (e.g. Snowflake read or NetSuite export) based on repeat demand. Billing tiers already reference integration counts (`frontend/lib/billing/plans.ts`) — implementation is post–path B MVP.

---

## Related docs

| Doc | Purpose |
|-----|---------|
| `GO_LIVE_GL1_CUSTOMER_PROVISIONING.md` | Invite + org provisioning |
| `GO_LIVE_POC_ONBOARDING.md` | Path B — self-serve CSV |
| `GO_LIVE_GL3_PLAN_ENTITLEMENTS.md` | Plan tiers after data is loaded |
| `REPORTING_ARCHITECTURE.md` | Warehouse + reporting |
