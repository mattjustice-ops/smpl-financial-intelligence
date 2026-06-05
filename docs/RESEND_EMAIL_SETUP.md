# Magic-link email (Resend)

Customer login sends a **sign-in link by email**. Resend is the recommended provider (same idea as Stripe/HubSpot token files).

## Quick setup (local)

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence
.\scripts\setup-resend-email.ps1
```

1. Sign up at [resend.com](https://resend.com) with your work email (`mattjustice@smpl-ai.com`).
2. **API Keys** → **Create API Key** → **Sending access**.
3. Paste the key (`re_...`) into `C:\Users\mattj\OneDrive\Documents\Resend Token.txt`.
4. Run the script again (or restart `npm run dev`).

Try login at http://localhost:3002/login — the link should arrive in your inbox.

## Important: “From” address rules

| Stage | `EMAIL_FROM` | Who can receive |
|--------|----------------|-----------------|
| **Getting started** | `SMPL.ai <onboarding@resend.dev>` | Only the email you used to sign up for Resend |
| **Production** | `SMPL.ai <noreply@smpl-ai.com>` | Any customer (after domain verified) |

To send to **any** customer email, verify **smpl-ai.com** in Resend (**Domains** → add DNS records), then set:

```env
EMAIL_FROM=SMPL.ai <noreply@smpl-ai.com>
```

## Environment variables

**Local** (`frontend/.env.local`):

```env
RESEND_TOKEN_FILE=C:\Users\mattj\OneDrive\Documents\Resend Token.txt
EMAIL_FROM=SMPL.ai <onboarding@resend.dev>
```

Or set `AUTH_RESEND_KEY=re_...` directly (Vercel production).

Optional SMTP fallback instead of Resend API:

```env
EMAIL_SERVER=smtp://resend:re_YOUR_KEY@smtp.resend.com:587
EMAIL_FROM=SMPL.ai <onboarding@resend.dev>
```

## Vercel production

| Key | Value |
|-----|--------|
| `AUTH_RESEND_KEY` | `re_...` from Resend dashboard |
| `EMAIL_FROM` | Verified address on smpl-ai.com |
| `AUTH_SECRET` | Random secret |
| `AUTH_URL` | `https://smpl-financial-intelligence.vercel.app` |
| `AUTH_DATABASE_URL` | Production Postgres connection string |

Redeploy after adding variables.

## Troubleshooting

- **No email** — Confirm `re_...` is in the token file; restart `npm run dev`.
- **Resend error “domain not verified”** — Use `onboarding@resend.dev` for testing, or verify smpl-ai.com.
- **Link works but sign-in denied** — Email must have a pending invite (`.\scripts\seed-dev-invite.ps1`).
- **Still prints to terminal** — Email is not configured; `EMAIL_SERVER` and Resend key are both missing.
