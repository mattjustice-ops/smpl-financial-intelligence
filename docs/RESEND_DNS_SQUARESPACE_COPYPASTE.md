# Squarespace DNS — copy/paste for smpl-ai.com (Resend)

Squarespace shows **Type, Name, Priority, TTL, Mail server** when **Type = MX**.

For **Type = TXT**, change Type first — **Priority** and **Mail server** are not used. Squarespace should show a **Text** box (sometimes below those fields, or labeled **Data**). Paste the TXT string there.

If you only ever see Mail server, you are still on **MX** — switch Type to **TXT** and save/add a new record.

---

## Record 1 — MX

| Squarespace field | Enter exactly |
|-------------------|---------------|
| Type | `MX` |
| Name | `send` |
| Priority | `10` |
| TTL | leave default (4 hours) |
| Mail server | `feedback-smtp.us-east-1.amazonses.com` |

Save.

---

## Record 2 — SPF (TXT)

Click **Add record** again.

| Squarespace field | Enter exactly |
|-------------------|---------------|
| Type | `TXT` |
| Name | `send` |
| TTL | leave default (4 hours) |
| **Text** (or **Data**) | `v=spf1 include:amazonses.com ~all` |

Do not fill Priority or Mail server for TXT records.

Save.

---

## Record 3 — DKIM (TXT) — one value from Resend only

This string is **unique to your Resend account**. It is not the same as Records 1–2.

1. Open [resend.com/domains](https://resend.com/domains) → click **smpl-ai.com**
2. **Records** tab → find the row **DKIM** (Type TXT, Name `resend._domainkey`)
3. Click **copy** on the **Value** column (long text starting with `p=`)

Then in Squarespace:

| Squarespace field | Enter exactly |
|-------------------|---------------|
| Type | `TXT` |
| Name | `resend._domainkey` |
| TTL | leave default |
| **Text** (or **Data**) | paste the copied `p=...` string only (no quotes) |

Save.

---

## Verify

Resend → **Verify DNS Records**. Wait 5–30 minutes.

If verification fails, open smpl-ai.com in Resend and confirm the MX/SPF values match **exactly** what Resend shows (region can differ from the examples above).
