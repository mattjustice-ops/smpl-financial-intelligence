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

1. Create products **Starter** and **Growth** with recurring prices (monthly + annual).
2. Create one-time prices for implementation fees (optional line items).
3. Enable **Customer Portal** in Stripe Billing settings (cancel, payment methods, invoices).
4. Copy price IDs into env vars above.

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

## Vercel production

Set all Stripe env vars on the **frontend** Vercel project. Set `APP_BASE_URL` to `https://smpl-financial-intelligence.vercel.app`. Register webhook endpoint:

`https://smpl-financial-intelligence.vercel.app/api/stripe/webhook`

Ensure Railway/backend URL is in `SFI_BACKEND_URL` so webhooks persist to Postgres.

## Security checklist

- [x] No custom card UI — Stripe Checkout only
- [x] Price IDs from server env only
- [x] Webhook signature verification
- [x] Checkout rate limit (10 sessions / email / hour)
- [x] Optional internal API key between Next and FastAPI
