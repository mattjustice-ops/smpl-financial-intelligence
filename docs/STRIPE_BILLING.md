# Stripe billing (SMPL product subscriptions)

Week 2 billing flow: **Pricing (sales-led) → Demo / Request Quote → Contract → Stripe (optional) → Webhooks → Customer Portal**.

Public `/pricing` does **not** show dollar amounts or monthly/annual toggles. Starter and Professional CTAs go to **Book a demo** and **Request pricing**. Enterprise goes to **Request quote**. Stripe Checkout APIs remain for post-contract invoicing if needed.

This is SMPL’s own subscription billing (not a customer-facing AR feature inside the product).

## Architecture

| Layer | Responsibility |
|-------|----------------|
| Next.js `/pricing` | Plan selection, checkout form |
| `POST /api/billing/create-checkout-session` | Stripe Checkout (server-only secret key) |
| `POST /api/stripe/webhook` | Signature verification, forward to backend |
| FastAPI `/api/v1/billing/*` | Postgres: customers, orgs, subscriptions, events |
| `POST /api/billing/create-portal-session` | Stripe Customer Portal |

## Environment variables

### Frontend (`frontend/.env.local`)

**Option A — token file (recommended locally)**

If `C:\Users\mattj\OneDrive\Documents\Stripe Token.txt` exists (or `STRIPE_TOKEN_FILE` points to it), the app reads:

- `sk_test_...` / `sk_live_...` → secret key (server)
- `pk_test_...` / `pk_live_...` → publishable key (if `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` is unset)
- `whsec_...` → webhook secret (paste from `stripe listen` into the same file)

```env
STRIPE_TOKEN_FILE=C:\Users\mattj\OneDrive\Documents\Stripe Token.txt
APP_BASE_URL=http://localhost:3002
SFI_BACKEND_URL=http://127.0.0.1:8001
# Price IDs still required in env (see below)
```

**Option B — env vars only**

```env
APP_BASE_URL=http://localhost:3002
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...

STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

STRIPE_STARTER_MONTHLY_PRICE_ID=price_...
STRIPE_STARTER_ANNUAL_PRICE_ID=price_...
STRIPE_GROWTH_MONTHLY_PRICE_ID=price_...
STRIPE_GROWTH_ANNUAL_PRICE_ID=price_...
STRIPE_STARTER_IMPLEMENTATION_PRICE_ID=price_...
STRIPE_GROWTH_IMPLEMENTATION_PRICE_ID=price_...

SFI_BACKEND_URL=http://127.0.0.1:8001
# Optional — if set, webhook + checkout recording require this header from Next.js
# BILLING_INTERNAL_API_KEY=your-random-secret
```

Never expose `STRIPE_SECRET_KEY` or `STRIPE_WEBHOOK_SECRET` as `NEXT_PUBLIC_*`.

### Backend (`backend/.env`)

```env
DATABASE_URL=postgresql+psycopg://sfi:sfi_dev_password@127.0.0.1:5432/sfi
# BILLING_INTERNAL_API_KEY=your-random-secret
```

## Database migration

```powershell
cd backend
.\.venv312\Scripts\Activate.ps1
alembic upgrade head
```

Creates:

- `billing_customers` (spec: customers)
- `billing_subscriptions` (spec: subscriptions)
- `billing_events` (spec: billing_events)
- `billing_checkout_sessions` (spec: checkout_sessions)
- `pending_user_invites`
- Extends `organizations` with `slug`, `status`, `plan`, Stripe IDs

## Stripe Dashboard setup

Products are **not** created when you deploy to Vercel. You must either run the PowerShell script or click **+ Create product** in Stripe.

### Create products (PowerShell)

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\create-stripe-test-products.ps1
```

The script prints the **Stripe account email and ID** for the key in `Stripe Token.txt`. You must be logged into **that same account** in the browser to see products.

### Verify (if Dashboard looks empty)

```powershell
.\scripts\verify-stripe-catalog.ps1
```

If the script lists products but Dashboard shows 0, you are logged into a **different Stripe account** in the browser (use the account switcher, top-left).

### Test vs Live (sandbox)

| Key in Token.txt | Dashboard toggle | Product catalog URL |
|------------------|------------------|---------------------|
| `sk_test_...` | **Test mode** ON | https://dashboard.stripe.com/test/products |
| `sk_live_...` | **Test mode** OFF | https://dashboard.stripe.com/products |

Test and Live are separate catalogs. Creating in test does not appear in live.

### Manual setup

1. Create products **SMPL Starter** and **SMPL Professional** with recurring prices (monthly + annual).
2. Optional one-time implementation prices.
3. Enable **Customer Portal** in Stripe Billing settings.
4. Copy `price_...` IDs into `frontend/.env.local` and Vercel env vars.

## Local testing with Stripe CLI

### Install Stripe CLI on Windows (if `stripe` is not recognized)

**Option 1 — winget (recommended)**

```powershell
winget install -e --id Stripe.StripeCli --accept-source-agreements --accept-package-agreements
```

Close PowerShell, open a **new** window, then:

```powershell
stripe --version
```

**Option 2 — repo script**

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\install-stripe-cli.ps1
```

**Option 3 — manual zip**

1. https://github.com/stripe/stripe-cli/releases/latest  
2. Download `stripe_*_windows_x86_64.zip`, extract `stripe.exe`  
3. Add the folder to your system **Path** (Settings → Environment Variables)  
4. New PowerShell window → `stripe --version`

### Forward webhooks locally

1. Login: `stripe login`
3. Forward webhooks (use your Next dev port — default frontend is **3002**):

```powershell
stripe listen --forward-to localhost:3002/api/stripe/webhook
```

4. Copy the signing secret from CLI output into `STRIPE_WEBHOOK_SECRET` or add a line `whsec_...` to `Stripe Token.txt`.
5. Start stack:

```powershell
docker compose up -d
cd backend; .\start-api.ps1
cd frontend; npm install; npm run dev
```

6. Open `http://localhost:3002/pricing`, submit checkout with test card `4242 4242 4242 4242`.
7. Confirm webhook logs and DB rows in `billing_subscriptions` / `organizations`.

## API reference

### `POST /api/billing/create-checkout-session`

Body:

```json
{
  "plan": "starter",
  "billing_interval": "monthly",
  "include_implementation_fee": true,
  "customer_email": "cfo@acme.com",
  "company_name": "Acme Inc",
  "hubspot_deal_id": "optional"
}
```

Returns `{ "ok": true, "url": "https://checkout.stripe.com/..." }`.

### `POST /api/billing/create-portal-session`

Body: `{ "organization_id": "uuid" }` or `{ "email": "cfo@acme.com" }`.

### `POST /api/stripe/webhook`

Raw body + `Stripe-Signature` header. Handled events:

- `checkout.session.completed`
- `customer.subscription.created|updated|deleted`
- `invoice.payment_succeeded|failed`
- `customer.updated`

Idempotency: `billing_events.stripe_event_id` unique constraint.

## Pages

| URL | Purpose |
|-----|---------|
| `/pricing` | Starter / Growth checkout, Enterprise → `/request-quote` |
| `/billing/success?session_id=` | Post-checkout confirmation |
| `/account/billing?organization_id=` or `?email=` | Plan summary + portal (until auth exists) |

## HubSpot (optional)

If `HUBSPOT_PRIVATE_APP_TOKEN` is set and checkout metadata includes `hubspot_deal_id`, webhook handler updates the deal with checkout note and contract value.

## Vercel production (plain language)

You only need this when accepting **real** payments in **Live** mode. For now, **sandbox + local `.env.local` is enough** for development.

### What “copy price_... into Vercel” means

A **price ID** is a Stripe label like `price_1ABC123...`. Your app does not read the Product catalog UI — it reads these IDs from **environment variables** on Vercel.

1. In Stripe (Live mode or your sandbox), open a product → click a price → copy **Price ID**.
2. In [Vercel](https://vercel.com) → your project → **Settings** → **Environment Variables**.
3. Add or edit each name to match the value, for example:
   - `STRIPE_STARTER_MONTHLY_PRICE_ID` = `price_...`
   - `STRIPE_PROFESSIONAL_MONTHLY_PRICE_ID` = `price_...`
   - (same for annual + implementation IDs)
4. Add `STRIPE_SECRET_KEY` = your `sk_live_...` (live) or keep `sk_test_...` only on preview if you prefer.
5. **Redeploy** the site after saving variables (Deployments → … → Redeploy).

`frontend/.env.local` on your PC is **not** uploaded to Vercel automatically.

### Webhook URL (not a web page)

`https://smpl-financial-intelligence.vercel.app/api/stripe/webhook`

- Opening it in Chrome is only a quick **health check** (should return JSON saying the endpoint is active).
- **Stripe** sends **POST** requests to this URL when someone pays or a subscription changes. You configure it in Stripe, not by visiting the link.

**Stripe Dashboard → Developers → Webhooks → Add endpoint**

- Endpoint URL: `https://smpl-financial-intelligence.vercel.app/api/stripe/webhook`
- Events: `checkout.session.completed`, `customer.subscription.*`, `invoice.payment_*`, `customer.updated`
- After creating the endpoint, copy the **Signing secret** (`whsec_...`) into Vercel as `STRIPE_WEBHOOK_SECRET`.

Also set `SFI_BACKEND_URL` on Vercel to your production API URL so webhooks can save to Postgres.

### Sandbox vs Live on Vercel

| Goal | Keys on Vercel |
|------|----------------|
| Dev / no real charges | Optional: only needed for testing checkout on production URL |
| Real customer billing | `sk_live_...`, live `price_...` IDs, live `whsec_...` from a **Live mode** webhook endpoint |

## Security checklist

- [x] No custom card UI — Stripe Checkout only
- [x] Price IDs from server env only
- [x] Webhook signature verification
- [x] Checkout rate limit (10 sessions / email / hour)
- [x] Optional internal API key between Next and FastAPI
