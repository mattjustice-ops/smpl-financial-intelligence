# What Resend DNS records look like (smpl-ai.com)

Resend gives you **3 records for sending** (exact values are on your account only). They always follow this shape:

---

## Record 1 — SPF (TXT)

| Field | What to enter |
|-------|----------------|
| **Type** | TXT |
| **Host / Name** | `send` (not `send.smpl-ai.com` on Cloudflare) |
| **Value** | Copy from Resend — looks like: `v=spf1 include:amazonses.com ~all` |
| **TTL** | Auto / 3600 |

---

## Record 2 — Return-path (MX)

| Field | What to enter |
|-------|----------------|
| **Type** | MX |
| **Host / Name** | `send` |
| **Mail server / Value** | Copy from Resend — looks like: `feedback-smtp.us-east-1.amazonses.com` |
| **Priority** | `10` |
| **TTL** | Auto |

---

## Record 3 — DKIM (TXT)

| Field | What to enter |
|-------|----------------|
| **Type** | TXT |
| **Host / Name** | `resend._domainkey` |
| **Value** | Copy from Resend — long string starting with `p=` |
| **TTL** | Auto |

On **Cloudflare**: set Proxy status to **DNS only** (grey cloud).

---

## Optional — DMARC (TXT)

| Field | What to enter |
|-------|----------------|
| **Type** | TXT |
| **Host / Name** | `_dmarc` |
| **Value** | `v=DMARC1; p=none;` |

---

## Easiest paths (pick one)

### A. Cloudflare + one click (recommended)

If `smpl-ai.com` DNS is on Cloudflare:

1. [resend.com/domains](https://resend.com/domains) → add `smpl-ai.com`
2. Click **Sign in to Cloudflare**
3. Authorize → records added automatically
4. Wait for **Verified**

### B. Copy exact values from Resend dashboard

1. Resend → **Domains** → `smpl-ai.com` → **Records** tab
2. Add each record in your DNS host (GoDaddy, Namecheap, Google, etc.)
3. Click **Verify DNS Records**

### C. Print values via script (needs Full Access API key)

```powershell
.\scripts\print-resend-dns-records.ps1 -CreateIfMissing
```

Your current login key may be **Sending only** — create a **Full access** key at [resend.com/api-keys](https://resend.com/api-keys) if the script says it cannot list domains.

---

## What you do NOT need (magic links only)

Skip **Receiving** / **inbound** MX records unless you want Resend to receive email at `@smpl-ai.com`. Login emails are **outbound only**.

---

## After Verified

```powershell
.\scripts\set-vercel-resend-from.ps1 -EmailFrom "SMPL.ai <noreply@smpl-ai.com>"
```

Redeploy Vercel, then smoke-test `/login`.
