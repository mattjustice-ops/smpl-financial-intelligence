# gl-3 — Plan module entitlements

**Goal:** Gate `/app` operating tabs and key API routes by plan tier.

Keep **backend** `app/services/entitlements.py` and **frontend** `lib/entitlements/plan-modules.ts` in sync.

---

## Module matrix

| Module / tab | Starter | Professional | Enterprise |
|--------------|---------|--------------|------------|
| Executive, ARR, Revenue, GTM, Pipeline, Decisions | yes | yes | yes |
| Management P&L | no | yes | yes |
| Workforce | no | yes | yes |
| Cash Forecast | no | yes | yes |
| Board export | yes | yes | yes |
| AI commentary | yes | yes | yes |

Enterprise currently matches Professional for modules (SSO/onboarding differ in sales, not code yet).

---

## Session

After deploy, users need a **fresh login** so `enabledModules` is populated in the JWT (falls back to plan-based defaults if missing).

---

## API enforcement

| Route prefix | Module |
|--------------|--------|
| `/management-pl/*` | `management-pl` |
| `/workforce/*` | `workforce` |
| `/forecast/cash-flow`, `/working-capital`, etc. | `cash` |
| `/forecast/deferred-revenue-waterfall` | `revenue` |

Aggregate `/dashboard/executive-flow` still returns all waterfalls (UI hides Cash tab on Starter). Tighten later if needed.

---

## Smoke test

1. Set org plan to `starter` on Neon: `UPDATE organizations SET plan = 'starter' WHERE id = '...'`
2. Re-login on prod → fewer nav tabs + upgrade banner
3. Direct API call to `/workforce/...` → 403 `module_not_entitled`
4. Set plan to `professional`, re-login → all tabs visible

```powershell
# Optional: provision starter pilot
.\scripts\provision-prod-customer.ps1 -Email pilot@company.com -OrganizationName "Starter Pilot" -Plan starter
```

---

## gl-3 done when

- [x] Shared plan → module catalog (BE + FE)
- [x] `enabledModules` in session sync
- [x] `/app` nav filtered by plan
- [x] API 403 on workforce / management-pl / cash forecast routes
- [ ] Smoke test on prod (starter vs professional)
- [ ] Mark gl-3 done on `/progress`
