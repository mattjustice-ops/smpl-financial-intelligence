# Resend DNS on Squarespace (smpl-ai.com)

`smpl-ai.com` uses **Squarespace DNS** (`squarespacedns.com` nameservers), not Cloudflare. Resend will **not** show "Sign in to Cloudflare" — use **Manual setup** instead.

Official Resend guide: https://resend.com/docs/knowledge-base/squarespace

---

## 1. Get values from Resend

1. [resend.com/domains](https://resend.com/domains) → add or open `smpl-ai.com`
2. Choose **Manual setup** if prompted
3. Open the **Records** tab — copy the three **sending** records (ignore Receiving/inbound)

---

## 2. Open Squarespace DNS

1. [account.squarespace.com/domains](https://account.squarespace.com/domains)
2. Click **smpl-ai.com**
3. **DNS** → scroll to **Custom records**

Squarespace appends `.smpl-ai.com` automatically. In **Host**, enter only the short name (e.g. `send`, not `send.smpl-ai.com`).

---

## 3. Add three custom records

### Record A — MX (return path)

| Field | Value |
|-------|--------|
| Host | `send` |
| Type | MX |
| Priority | `10` |
| Mail server | Copy from Resend (e.g. `feedback-smtp.us-east-1.amazonses.com`) |
| TTL | Default (4 hours) |

### Record B — TXT (SPF)

| Field | Value |
|-------|--------|
| Host | `send` |
| Type | TXT |
| Text | Copy from Resend (e.g. `v=spf1 include:amazonses.com ~all`) |
| TTL | Default |

### Record C — TXT (DKIM)

| Field | Value |
|-------|--------|
| Host | `resend._domainkey` |
| Type | TXT |
| Text | Copy full value from Resend (starts with `p=`) |
| TTL | Default |

### Optional — DMARC

| Field | Value |
|-------|--------|
| Host | `_dmarc` |
| Type | TXT |
| Text | `v=DMARC1; p=none;` |

**Do not add** Receiving/inbound MX records unless you want Resend to receive mail at `@smpl-ai.com`.

---

## 4. Verify in Resend

Back in Resend → **Verify DNS Records**. Propagation often takes 5–30 minutes (up to 72h).

---

## 5. Update production

```powershell
.\scripts\set-vercel-resend-from.ps1 -EmailFrom "SMPL.ai <noreply@smpl-ai.com>"
```

Redeploy Vercel.
