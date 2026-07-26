# Change Management / Secure SDLC Policy

> **STATUS: DRAFT — NOT APPROVED**  
> Template for SOC 2 Type I readiness. Not company policy until approved.  
> Not legal advice. Not evidence of SOC 2 compliance.  
> Operational detail of the deploy path: [../CHANGE_MANAGEMENT.md](../CHANGE_MANAGEMENT.md).

| Field | Value |
|-------|--------|
| Policy ID | P05 |
| Owner | Matt Justice (Engineering owner) |
| Applies to | Production code and infrastructure changes for the SMPL financial intelligence platform |
| Related criteria | Security (CC8) |
| Version | 0.2-draft |
| Effective date | _TBD on approval_ |
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
3. **Required peer review** before merge to `main` (branch protection — _[! Matt: confirm in GitHub settings]_).
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
- Prefer dependency alerting (e.g. Dependabot or equivalent) — enable/confirm (**[!]**).
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
| Executive sponsor | _DRAFT — not signed — Matt Justice must approve_ | |
| Engineering owner | _DRAFT — not signed — Matt Justice must approve_ | |

---

_End of DRAFT P05_
