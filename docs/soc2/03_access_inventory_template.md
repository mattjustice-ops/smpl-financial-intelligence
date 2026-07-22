# Access inventory template

Who can touch production systems or customer data, and why. Complete Week 1; review quarterly thereafter (dated sign-off = audit evidence).

Parent: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md)

**Rules of thumb:** unique accounts (no shared logins); MFA on admin; least privilege; revoke same day on offboarding.

---

## Instructions

1. Export members/admins from each console (or screenshot role lists).
2. Fill one row per person × system (or attach export and summarize admins here).
3. Security owner reviews; executive sponsor signs quarterly review block at bottom.

---

## Inventory

| Person | Email | System | Role / permission | Prod access? | MFA on? | Business justification | Last reviewed |
|--------|-------|--------|-------------------|--------------|---------|------------------------|---------------|
| | | GitHub (org / repo) | | Y/N | Y/N | | |
| | | Vercel (team / project) | | Y/N | Y/N | | |
| | | Railway (project / service) | | Y/N | Y/N | | |
| | | Neon (org / project / DB) | | Y/N | Y/N | | |
| | | Sanity (project) | | Y/N | Y/N | | |
| | | Stripe (account) | | Y/N | Y/N | | |
| | | Resend (account) | | Y/N | Y/N | | |
| | | Anthropic (console / API keys) | | Y/N | Y/N | | |
| | | Corporate email / IdP (Google / Microsoft / other) | | Y/N | Y/N | | |
| | | Compliance platform (when chosen) | | Y/N | Y/N | | |
| | | Ops console / white-glove tooling | | Y/N | Y/N | | |
| | | Direct DB / break-glass | | Y/N | Y/N | | |
| | | Domain DNS / Squarespace / registrar | | Y/N | Y/N | | |

Add rows as needed. Duplicate systems for staging if separate from prod.

---

## Systems checklist (have we inventoried?)

- [ ] GitHub
- [ ] Vercel
- [ ] Railway
- [ ] Neon
- [ ] Sanity
- [ ] Stripe
- [ ] Resend
- [ ] Anthropic
- [ ] Email / IdP
- [ ] DNS / domain admin
- [ ] Ops / privileged tenant access
- [ ] Compliance platform (when live)

---

## Privileged / white-glove operators

| Person | What they can access | Approval path | Revocation trigger |
|--------|----------------------|---------------|--------------------|
| | Tenant data via ops / DB / load tooling | | End of POC / ticket close / offboarding |

---

## Quarterly access review sign-off

| Review period | Reviewer | Date | Result (OK / changes made) | Notes |
|---------------|----------|------|----------------------------|-------|
| YYYY-QX | | | | |

Attach exports or links to evidence folder (do not commit secrets or customer dumps to git).
