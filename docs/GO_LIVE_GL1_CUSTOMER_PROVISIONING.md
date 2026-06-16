# Go-live gl-1 — Customer provisioning playbook

**Goal:** Onboard a customer (or teammate) onto production: org row + invite → magic link → `/app`.

**Production login:** https://smpl-financial-intelligence.vercel.app/login

---

## Two paths

| Path | When to use |
|------|-------------|
| **A. Add user to existing org** | Pilot on SMPL Demo Co, extra seat on same data |
| **B. New customer org** | Separate tenant, own company name and (eventually) own CSVs |
| **C. Direct data access (enterprise POC)** | Customer grants read access; SMPL ops loads warehouse — see `GO_LIVE_POC_DIRECT_DATA_ACCESS.md` |

Stripe checkout auto-provisioning is **gl-4** — until then, use **manual ops** below.

---

## Path A — Invite to SMPL Demo Co (fastest)

Same org as Matt (`8571e520-0687-4516-bdee-379f37c58c1f`), warehouse data already loaded.

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence

.\scripts\provision-prod-customer.ps1 `
  -Email colleague@theircompany.com `
  -UseDemoOrg
```

Script reads Neon URL from `frontend/.env.neon-production.local` (save once with `save-prod-database-url.ps1`), or pass `-DatabaseUrl`, or use `-TryVercelPull` if logged into Vercel CLI.

**Customer steps:**

1. Open prod `/login`
2. Enter invited email → magic link from `noreply@smpl-ai.com`
3. Land on `/app` — banner shows their email + **SMPL Demo Co**

**Ops verification:**

```powershell
.\scripts\check-login-access.ps1 -Email colleague@theircompany.com
```

---

## Path B — New customer organization

```powershell
.\scripts\provision-prod-customer.ps1 `
  -Email admin@acme.com `
  -OrganizationName "Acme Corp" `
  -Plan professional
```

Note the **Organization ID** printed at the end.

### Load financial data (optional)

Empty org until CSVs are loaded:

```powershell
.\scripts\setup-prod-warehouse.ps1 `
  -DatabaseUrl "postgresql://...@ep-....neon.tech/neondb?sslmode=require" `
  -OrganizationId "<new-org-uuid>"
```

Use customer CSVs in `-CsvFolder` when ready; demo bundled data works for pilots.

---

## Seat limits

| Plan | Max active members |
|------|-------------------|
| starter | 2 |
| professional | 5 |
| enterprise | 10 |

Login returns `seats_full` if the org is at capacity. Upgrade plan on the `organizations.plan` row or remove inactive members before inviting.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Magic link never arrives | Resend domain verified? `EMAIL_FROM` = `@smpl-ai.com` on Vercel? |
| Link works, **Access denied** | Re-run `provision-prod-customer.ps1` for that email |
| `/app` empty charts | Org has no warehouse data — run `setup-prod-warehouse.ps1` for that org ID |
| Wrong workspace | User has multiple orgs — check `activeOrganizationId` after login |

---

## gl-1 done when

- [x] Playbook documented (this file)
- [x] Second email invited on prod (Path A or B)
- [x] Prod `/login` → `/app` smoke test passed for that email
- [x] `gl-1` marked done on `/progress`

---

## Next (gl-7)

First **paying** external customer on the same stack:

- **Enterprise / white-glove:** Path B provision + **Path C** direct data load (`GO_LIVE_POC_DIRECT_DATA_ACCESS.md`) — does not require self-serve upload.
- **Self-serve at scale:** Path B + `/app/onboarding` when poc-1 … poc-3 ship.

Contract/Stripe: gl-4 when charging.
