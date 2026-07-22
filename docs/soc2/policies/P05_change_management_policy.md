# Change Management / Secure SDLC Policy

> **STATUS: DRAFT — NOT APPROVED**  
> Template for SOC 2 Type I readiness. Not company policy until approved.  
> Not legal advice. Not evidence of SOC 2 compliance.

| Field | Value |
|-------|--------|
| Policy ID | P05 |
| Owner | Engineering owner |
| Applies to | Production code and infrastructure changes for the SMPL financial intelligence platform |
| Related criteria | Security (CC8) |
| Version | 0.1-draft |
| Effective date | _TBD on approval_ |

---

## 1. Purpose

Ensure production changes are reviewed, authorized, and traceable — and that development does not bypass production controls.

## 2. Environments

| Environment | Purpose |
|-------------|---------|
| Development | Local / feature work |
| Staging / sandbox | Pre-prod validation (confirm exact projects with eng) |
| Production | Customer-facing: Vercel (frontend), Railway (API), Neon (Postgres) |

Do not use production customer data in personal sandboxes without authorization and minimization.

## 3. Standard change path

1. Develop in a branch under **GitHub** version control.
2. Open a pull request; address review feedback.
3. **Required peer review** before merge to `main` (branch protection — _[! confirm in GitHub]_).
4. Deploy:
   - Frontend → **Vercel** (from protected branch / approved pipeline)
   - API → **Railway** (from protected branch / approved pipeline)
5. Confirm health after deploy; roll back via provider tooling if needed.

## 4. Who can promote to production

| Surface | Who can deploy / promote | Notes |
|---------|--------------------------|-------|
| Vercel (frontend) | _[! Matt / eng — name]_ | |
| Railway (API) | _[! Matt / eng — name]_ | |
| Neon schema / migrations | _[! Matt / eng — name]_ | Prefer reviewed migration PRs |

## 5. Emergency changes

- Allowed to restore service or contain an incident.
- Document after-the-fact (ticket + PR) within 2 business days.
- Still rotate any exposed secrets.

## 6. Secure SDLC hygiene

- No secrets in git; use Vercel/Railway env/secret stores.
- Prefer dependency alerting (e.g. Dependabot or equivalent) — enable/confirm.
- Customer financial methodology changes follow product process; **Processing Integrity is out of Type I scope** — do not imply audit attestation of ARR/FP&A math.

## 7. Evidence

- PR history with approvals
- Deploy history from Vercel / Railway for sample periods
- Branch protection screenshots or settings export

## 8. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | _DRAFT — not signed_ | |
| Engineering owner | _DRAFT — not signed_ | |

---

_End of DRAFT P05_
