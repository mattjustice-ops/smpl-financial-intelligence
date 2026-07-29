# Change Management / Secure SDLC Policy

> **STATUS: APPROVED** — Effective 2026-07-27. Approved by Matt Justice (executive sponsor).  
> Not legal advice. Not evidence of SOC 2 certification. Approving policies ≠ SOC 2 certified; open evidence items remain. SMPL is **not** SOC 2 certified until a CPA Type I report is in hand.

| Field | Value |
|-------|--------|
| Policy ID | P05 |
| Owner | Matt Justice (Engineering owner) |
| Applies to | Production code and infrastructure changes for the SMPL financial intelligence platform |
| Related criteria | Security (CC8) |
| Version | 1.0 |
| Effective date | 2026-07-27 |
| Last expanded | 2026-07-26 |

---

## 1. Purpose

Ensure production changes are reviewed, authorized, and traceable — and that development does not bypass production controls.

## 2. Environments

| Environment | Purpose | Typical hosts |
|-------------|---------|---------------|
| Development | Local / feature work | Developer machines |
| Staging / sandbox | Pre-prod validation | Confirm exact projects with eng — **[!]** |
| Production | Customer-facing | **Vercel** (frontend), **Railway** (API), **Neon** (Postgres) |

Do not use production customer data in personal sandboxes without authorization and minimization.

## 3. Standard change path

1. Develop in a branch under **GitHub** version control.
2. Open a pull request; address review feedback.
3. **Required PR before merge** to `main` (GitHub branch ruleset — **confirmed 2026-07-26**; solo-friendly, approvals may be 0).
4. Deploy (see [../CHANGE_MANAGEMENT.md](../CHANGE_MANAGEMENT.md)):
   - Frontend → **Vercel** (typically from `main` / approved pipeline)
   - API → **Railway** (typically from `main` / approved pipeline)
5. Confirm health after deploy (`/health`, smoke login, critical routes); roll back via provider tooling if needed.

## 4. Who can promote to production

| Surface | Who can deploy / promote | Notes |
|---------|--------------------------|-------|
| Vercel (frontend) | Matt Justice | MFA verified 2026-07-26 |
| Railway (API) | Matt Justice | MFA verified 2026-07-26 |
| Neon schema / migrations | Matt Justice | Prefer reviewed migration PRs / Alembic via controlled process |
| Env / secrets changes | Matt Justice | Document material secret rotations |

## 5. Emergency changes

- Allowed to restore service or contain an incident ([P04](./P04_incident_response_plan.md)).
- Document after-the-fact (ticket + PR) within 2 business days.
- Still rotate any exposed secrets.

## 6. Secure SDLC hygiene

- No secrets in git; use Vercel/Railway env/secret stores.
- Prefer dependency alerting (e.g. Dependabot or equivalent) — **confirmed 2026-07-28** (PR #19 + GitHub Code security toggles; [../evidence/dependabot-enabled-2026-07-28.md](../evidence/dependabot-enabled-2026-07-28.md)).
- Anthropic / LLM keys only on Railway (API), never in browser or public board HTML.
- Customer financial methodology changes follow product process; **Processing Integrity is out of Type I scope** — do not imply audit attestation of ARR/FP&A math.

## 7. Evidence

- PR history with approvals
- Deploy history from Vercel / Railway for sample periods
- Branch protection screenshots or settings export — **[! Matt]**
- This policy + [../CHANGE_MANAGEMENT.md](../CHANGE_MANAGEMENT.md)

## 8. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | Matt Justice | 2026-07-27 |
| Engineering owner | _DRAFT — not signed — Matt Justice must approve_ | |

---

_End of APPROVED P05_
