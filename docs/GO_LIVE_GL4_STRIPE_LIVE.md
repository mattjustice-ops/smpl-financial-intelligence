# Go-live gl-4 — Stripe live keys + webhooks

**Goal:** Production checkout and webhooks use **Live** mode (`sk_live_`, `pk_live_`, live `price_` IDs).

**Prod webhook URL:** `https://www.smpl-ai.com/api/stripe/webhook`  
(alternate: `https://smpl-financial-intelligence.vercel.app/api/stripe/webhook`)

---

## One-command setup (recommended)

From repo root, with **Live** keys in `Stripe Token.txt` (`sk_live_...`, `pk_live_...`):

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence
.\scripts\setup-stripe-live-gl4.ps1
```

Options:

```powershell
# Create live catalog + webhook + print Vercel checklist only
.\scripts\setup-stripe-live-gl4.ps1

# Also push Stripe env vars to Vercel Production (needs vercel login or VERCEL_TOKEN)
.\scripts\setup-stripe-live-gl4.ps1 -ApplyVercel

# Skip product creation if live catalog already exists
.\scripts\setup-stripe-live-gl4.ps1 -SkipProductCreate -ApplyVercel
```

After `-ApplyVercel`: redeploy Production:

```powershell
.\scripts\redeploy-vercel-production.ps1
# or skip local build if you only changed env vars:
.\scripts\redeploy-vercel-production.ps1 -SkipBuild -SmokeTest
```

---

## Manual checklist (if you prefer Dashboard)

### 1. Live product catalog

Stripe Dashboard → turn **Test mode OFF** → Product catalog:

- **SMPL Starter** — monthly, annual, optional one-time Implementation
- **SMPL Professional** — monthly, annual, optional one-time Implementation

Or run: `.\scripts\create-stripe-test-products.ps1` with `sk_live_` in Token.txt.

### 2. Vercel Production env vars

| Key | Value |
|-----|--------|
| `STRIPE_SECRET_KEY` | `sk_live_...` |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | `pk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` from live webhook endpoint |
| `STRIPE_STARTER_MONTHLY_PRICE_ID` | live `price_...` |
| `STRIPE_STARTER_ANNUAL_PRICE_ID` | live `price_...` |
| `STRIPE_PROFESSIONAL_MONTHLY_PRICE_ID` | live `price_...` |
| `STRIPE_PROFESSIONAL_ANNUAL_PRICE_ID` | live `price_...` |
| `STRIPE_*_IMPLEMENTATION_PRICE_ID` | if used |
| `APP_BASE_URL` | `https://www.smpl-ai.com` |
| `SFI_BACKEND_URL` | `https://sfi-api-production.up.railway.app` |
| `BILLING_INTERNAL_API_KEY` | same on Vercel + Railway |

Print local price IDs: `.\scripts\print-vercel-stripe-env.ps1`

### 3. Live webhook (Stripe Dashboard)

Developers → Webhooks → Add endpoint:

- **URL:** `https://www.smpl-ai.com/api/stripe/webhook`
- **Events:** `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`, `customer.updated`

Copy signing secret → Vercel `STRIPE_WEBHOOK_SECRET` → redeploy.

### 4. Railway

Confirm `BILLING_INTERNAL_API_KEY` matches Vercel. Redeploy if changed.

### 5. Customer Portal

Stripe → Settings → Billing → Customer portal → Enable.

---

## Smoke test

```powershell
.\scripts\smoke-test-stripe-prod.ps1
```

Then (sales-led): create a **contract** checkout from `/pricing` or Stripe Dashboard → send to a test email you control. Confirm:

1. Webhook delivery **200** in Stripe Dashboard
2. Row in Neon `billing_subscriptions` / org updated
3. Customer can open `/account` or portal

---

## gl-4 done when

- [x] Live keys + live price IDs on Vercel Production
- [x] Live webhook endpoint registered and returning 200
- [x] `BILLING_INTERNAL_API_KEY` aligned (Vercel + Railway)
- [x] Smoke test passes (`.\scripts\smoke-test-stripe-prod.ps1`)
- [ ] One live contract checkout → `billing_subscriptions` row in Neon (`.\scripts\verify-stripe-billing-neon.ps1`)
- [x] Mark `gl-4` done on `/progress`

---

## Related

- `docs/STRIPE_BILLING.md` — architecture
- `docs/VERCEL_STRIPE_SETUP_BEGINNER.md` — sandbox walkthrough
- `docs/GO_LIVE_GL1_CUSTOMER_PROVISIONING.md` — manual provision until auto-provision from checkout
