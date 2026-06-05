# Stripe + Vercel setup (beginner guide)

This guide assumes you are **not** charging real money yet. You can still copy settings into Vercel so production is ready when you need it.

---

## The idea in one minute

| Word | Plain English |
|------|----------------|
| **Stripe** | The company that processes card payments for you. |
| **Product** | What you sell (e.g. “SMPL Starter”). You see these on the Product catalog screen. |
| **Price** | How much and how often (e.g. $X per month). Each price has its own **Price ID**. |
| **Price ID** | A code Stripe uses behind the scenes, always starts with `price_`. Your website stores these codes in Vercel — **not** dollar amounts. |
| **Secret key** | Password for your server to talk to Stripe. Starts with `sk_test_` (sandbox) or `sk_live_` (real money). **Never** put this on a public webpage. |
| **Publishable key** | Safe-ish key for browser Stripe widgets. Starts with `pk_test_` or `pk_live_`. |
| **Webhook secret** | Password proving a message really came from Stripe. Starts with `whsec_`. |
| **Vercel env var** | A row in Vercel: **Name** = setting name, **Value** = the actual code or URL. |

Think of a **Price ID** like a SKU barcode: customers never type it; your app sends it to Stripe at checkout.

---

## Where your products live (sandbox)

You found them under **Switch to sandbox → SMPL.ai sandbox**.

Use that same sandbox when copying Price IDs below.

---

## Part A — Find a Price ID in Stripe (step by step)

1. Open https://dashboard.stripe.com  
2. Top-left account picker → **Switch to sandbox** → **SMPL.ai sandbox**  
3. Left menu → **Product catalog**  
4. Click **SMPL Starter** (or Professional)  
5. Scroll to the **Pricing** section  
6. Click one price row (e.g. “Starter Monthly”)  
7. Find **API ID** or **Price ID** — it looks like `price_1SomethingSomething`  
8. Click **Copy** (or select and Ctrl+C)

That copied text is what you paste into Vercel as the **Value**.

Repeat for each price you use (monthly, annual, implementation if any).

---

## Part B — Find API keys in Stripe

1. Still in **SMPL.ai sandbox** (for testing)  
2. Left menu → **Developers** → **API keys**  
3. You will see:
   - **Publishable key** → `pk_test_...`  
   - **Secret key** → click **Reveal** → `sk_test_...`  

For **real money later** (Live mode): turn **Test mode** off (or exit sandbox to Live), then copy `pk_live_...` and `sk_live_...` instead.

You can also copy `sk_test_` and `pk_test_` from `Stripe Token.txt` on your PC if you already saved them there.

---

## Part C — Add everything in Vercel

1. Go to https://vercel.com and log in  
2. Open project **smpl-financial-intelligence** (or your connected repo name)  
3. **Settings** → **Environment Variables**  
4. For each row below, click **Add** (or edit if it exists):
   - **Key** = exact name in the “Name” column (copy-paste, case-sensitive)  
   - **Value** = what the “Where to get value” column says  
   - **Environment**: check **Production** (and **Preview** if you want staging to work the same)  
5. Click **Save**  
6. Go to **Deployments** → latest deployment → **⋯** → **Redeploy** (required after changing variables)

### Important

- Vercel does **not** read `Stripe Token.txt` or `frontend/.env.local` on your laptop. You must type (or paste) each value in the Vercel website.  
- On your PC, `STRIPE_TOKEN_FILE=...` only works locally. On Vercel, use `STRIPE_SECRET_KEY` instead.

---

## Complete list — what to type in Vercel

### Stripe keys (sandbox / test — use while learning)

| Name (Key) — type exactly | Value — what to paste |
|---------------------------|------------------------|
| `STRIPE_SECRET_KEY` | Your secret key from Developers → API keys, e.g. `sk_test_51Te...` (full string) |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Your publishable key, e.g. `pk_test_51Te...` (full string) |
| `STRIPE_WEBHOOK_SECRET` | From Stripe → Developers → Webhooks → your endpoint → **Signing secret** `whsec_...` (see Part D). Leave empty until you create the webhook. |

### Price IDs — one row per price (from Product catalog → click price → copy ID)

| Name (Key) | Which price in Stripe |
|------------|------------------------|
| `STRIPE_STARTER_MONTHLY_PRICE_ID` | SMPL Starter → monthly recurring price |
| `STRIPE_STARTER_ANNUAL_PRICE_ID` | SMPL Starter → annual recurring price |
| `STRIPE_PROFESSIONAL_MONTHLY_PRICE_ID` | SMPL Professional → monthly recurring price |
| `STRIPE_PROFESSIONAL_ANNUAL_PRICE_ID` | SMPL Professional → annual recurring price |
| `STRIPE_STARTER_IMPLEMENTATION_PRICE_ID` | SMPL Starter → one-time “Implementation” price (if you created one) |
| `STRIPE_PROFESSIONAL_IMPLEMENTATION_PRICE_ID` | SMPL Professional → one-time implementation price (if you created one) |

Optional legacy names (only if your app still references them — same value as Professional is OK):

| Name (Key) | Usually same as |
|------------|-----------------|
| `STRIPE_GROWTH_MONTHLY_PRICE_ID` | Professional monthly `price_...` |
| `STRIPE_GROWTH_ANNUAL_PRICE_ID` | Professional annual `price_...` |
| `STRIPE_GROWTH_IMPLEMENTATION_PRICE_ID` | Professional implementation `price_...` |

**Example** (your sandbox IDs will look similar but may differ):

```
STRIPE_STARTER_MONTHLY_PRICE_ID = price_1TejPwHh0tGouORymsGCt8kD
```

The part after `price_` is random letters/numbers Stripe assigned — you must use **your** copied IDs, not someone else’s.

### Site URLs (not Stripe — still required for billing pages)

| Name (Key) | Value |
|------------|--------|
| `APP_BASE_URL` | `https://smpl-financial-intelligence.vercel.app` |
| `SFI_BACKEND_URL` | Your production API URL (e.g. Railway backend), **no** trailing slash |
| `HUBSPOT_PRIVATE_APP_TOKEN` | Your HubSpot `pat-...` token (if you use HubSpot on production) |
| `HUBSPOT_PIPELINE_NAME` | `Sales Pipeline` or `SMPL Inbound Sales` (must match a pipeline in HubSpot) |

---

## Part D — Webhook (optional until you test payments on production)

The URL is **not** a page you browse for fun. Stripe **sends** payment notifications there.

1. Stripe → **Developers** → **Webhooks** → **Add endpoint**  
2. **Endpoint URL**: `https://smpl-financial-intelligence.vercel.app/api/stripe/webhook`  
3. Select events (at minimum): `checkout.session.completed`  
4. Create endpoint → open it → copy **Signing secret** (`whsec_...`)  
5. Vercel → add `STRIPE_WEBHOOK_SECRET` = that `whsec_...`  
6. Redeploy  

To sanity-check after deploy: open the URL in a browser. You should see JSON text like “webhook endpoint is active”, not a marketing page.

---

## Copy from your PC file (shortcut)

Your laptop already has price IDs in:

`frontend\.env.local`

Open it in Notepad. Each line is `NAME=value`. For Vercel:

- **Key** = text before `=`  
- **Value** = text after `=`  

Do **not** add `STRIPE_TOKEN_FILE` to Vercel — it only works on your machine. Use `STRIPE_SECRET_KEY` instead.

Run this in PowerShell to print a checklist from that file:

```powershell
.\scripts\print-vercel-stripe-env.ps1
```

---

## Sandbox vs Live (when you start real billing)

| | Sandbox (now) | Live (real customers) |
|---|---------------|------------------------|
| Keys | `sk_test_`, `pk_test_` | `sk_live_`, `pk_live_` |
| Products | SMPL.ai sandbox catalog | Create again in Live mode |
| Price IDs | `price_...` from sandbox | New `price_...` from Live — paste into Vercel again |
| Vercel | Can use test keys on Production only if you accept no real charges | Must use live keys + live price IDs |

---

## Do you need Vercel Stripe vars today?

| Your situation | Action |
|----------------|--------|
| Only testing on `localhost:3002` | Optional. `.env.local` is enough. |
| Want production site to run checkout later | Add the table above in Vercel + redeploy |
| Not charging anyone yet | Skip Live keys; sandbox on laptop is fine |

---

## Quick troubleshooting

| Problem | Fix |
|---------|-----|
| “Price ID not configured” on checkout | That `STRIPE_..._PRICE_ID` name is missing or wrong in Vercel — redeploy after fix |
| Products in Stripe but checkout fails | Price ID in Vercel must be from the **same** sandbox/live mode as `STRIPE_SECRET_KEY` |
| Webhook URL “doesn’t work” in browser | After deploy, should show JSON; real tests come from Stripe webhook deliveries, not Chrome |

---

## Related docs

- `docs/STRIPE_BILLING.md` — technical billing architecture  
- `scripts/create-stripe-test-products.ps1` — create sandbox products + fill `.env.local`  
- `scripts/verify-stripe-catalog.ps1` — confirm API sees your products  
