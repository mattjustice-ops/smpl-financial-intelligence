# Go-live Step 2 — Resend verified domain (gl-2)

**Milestone:** Full go-live item **gl-2** on `/progress`  
**Goal:** Send magic-link emails from `@smpl-ai.com` to **any** customer email (not just your Resend signup address).

**Production login:** https://smpl-financial-intelligence.vercel.app/login

---

## Why this step matters

| Stage | `EMAIL_FROM` | Who receives magic links |
|-------|----------------|---------------------------|
| Dev / early prod | `onboarding@resend.dev` | Only the email on your Resend account |
| **After gl-2** | `noreply@smpl-ai.com` (verified) | Any invited customer email |

---

## Step 1 — Add domain in Resend

1. Open [resend.com/domains](https://resend.com/domains)
2. **Add Domain** → enter `smpl-ai.com`
3. Resend shows DNS records (SPF, DKIM, optional DMARC)

**Easiest if DNS is on Cloudflare:** click **Sign in to Cloudflare** on that domain page — Resend adds the records for you (no manual copy/paste).

**smpl-ai.com uses Squarespace DNS** (not Cloudflare), so use manual setup: [RESEND_DNS_SQUARESPACE.md](./RESEND_DNS_SQUARESPACE.md)

**Not sure what records look like?** See [RESEND_DNS_EXAMPLE.md](./RESEND_DNS_EXAMPLE.md) or run:

```powershell
.\scripts\print-resend-dns-records.ps1 -CreateIfMissing
```

(Requires a Full Access Resend API key; Sending-only keys must use the dashboard Records tab.)

---

## Step 2 — Add DNS records

Log in wherever **smpl-ai.com** DNS is managed (Cloudflare, GoDaddy, Namecheap, Google Domains, etc.).

Add **every** record Resend shows. Typical set:

| Type | Name / Host | Value |
|------|-------------|--------|
| TXT | `@` or `smpl-ai.com` | SPF (Resend provides exact string) |
| CNAME | `resend._domainkey` | DKIM target (Resend provides) |
| TXT | `_dmarc` | Optional but recommended |

**Tips:**

- In Cloudflare, set proxy status to **DNS only** (grey cloud) for CNAME/TXT used by email.
- DNS can take 5 minutes to 48 hours; Resend dashboard shows **Verified** when ready.

---

## Step 3 — Confirm domain verified

In Resend → **Domains** → `smpl-ai.com` status must be **Verified** (green).

If stuck: click **Verify** again after DNS propagates; use [dnschecker.org](https://dnschecker.org) to confirm TXT/CNAME records globally.

---

## Step 4 — Update Vercel `EMAIL_FROM`

From repo root (after domain is verified):

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence

.\scripts\set-vercel-resend-from.ps1 `
  -EmailFrom "SMPL.ai <noreply@smpl-ai.com>"
```

Or manually: **Vercel → Settings → Environment Variables → Production** → set:

```
EMAIL_FROM = SMPL.ai <noreply@smpl-ai.com>
```

`AUTH_RESEND_KEY` stays the same (no change needed if login already works for your account).

---

## Step 5 — Redeploy Vercel

**Vercel → Deployments → Redeploy latest**

---

## Step 6 — Smoke test (critical)

Send to an email **different** from your Resend signup address (proves gl-2 works):

```powershell
.\scripts\test-resend-email.ps1 `
  -To colleague@theircompany.com `
  -From "SMPL.ai <noreply@smpl-ai.com>"
```

Then prod login test:

1. Seed invite for that email on Neon:

```powershell
cd backend
$env:DATABASE_URL = "postgresql+psycopg://..."   # same Neon URL as prod
.\.venv312\Scripts\python.exe scripts\seed_dev_invite.py `
  --email colleague@theircompany.com `
  --organization-id 8571e520-0687-4516-bdee-379f37c58c1f
```

2. https://smpl-financial-intelligence.vercel.app/login → enter their email → confirm magic link arrives **From: noreply@smpl-ai.com**

---

## Step 7 — Mark gl-2 done

Update `frontend/lib/go-live-progress.ts` → `gl-2` → `done: true`, or tell your agent to mark it after smoke test passes.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Domain stuck on Pending | Wait for DNS; re-check record names (some hosts want `@` vs root) |
| Resend "domain not verified" on send | Do not use `@smpl-ai.com` From until Verified |
| Test works but prod login fails | Redeploy Vercel after `EMAIL_FROM` change |
| Email arrives but Access Denied | Seed `pending_user_invites` for that address on Neon |
| Still only delivers to your email | `EMAIL_FROM` still `onboarding@resend.dev` on Vercel |

---

## Next step (gl-1)

Document manual customer provisioning: create org + invite → customer logs in. See `docs/CUSTOMER_ACCESS.md`.
