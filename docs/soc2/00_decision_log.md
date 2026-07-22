# SOC 2 Type I — Decision log

Fill as decisions are made. Do not claim certification until a CPA firm issues a report.

Parent plan: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md) · Scoreboard: [PROGRESS.md](./PROGRESS.md) · Scope detail: [../SMPL_SOC2_Readiness_Reference_v2.md](../SMPL_SOC2_Readiness_Reference_v2.md)

**How to read this log:** Scope and named owners below were set **2026-07-22** (Matt Justice owns all roles for now). Platform choice and audit engagement remain **open for Matt**. Formal confirmation block still needs Matt’s signature when ready.

---

## Scope & platform

| Decision | Choice | Date | Owner | Notes |
|----------|--------|------|-------|-------|
| Engagement type | Type I first, then Type II | 2026-07-22 | Matt Justice | Confirmed for readiness planning |
| Type I Trust Services Criteria | **Security + Availability + Confidentiality** | 2026-07-22 | Matt Justice | Confirmed per readiness v2 / kickoff |
| Processing Integrity | **Deferred** | 2026-07-22 | Matt Justice | Revisit only with auditor + counsel; not “certified ARR math” |
| Privacy | Skip for now | 2026-07-22 | Matt Justice | Revisit if consumer/employee PII at scale or contract requires |
| Compliance automation platform | **TBD** | | **[!]** Matt Justice | **Matt to decide** (Vanta / Drata / Secureframe / other) **or** write an explicit “wait until YYYY-MM-DD.” Do **not** sign up until MFA + access inventory are underway. No auto-signup in this kickoff. |
| Audit firm (CPA) | TBD | | **[!]** Matt Justice | Independent CPA; platform partner network OK later |
| Target Type I fieldwork / report month | YYYY-MM | | **[!]** Matt Justice | Book only when controls are live |

---

## Named owners

| Role | Name | Date named | Notes |
|------|------|------------|-------|
| Executive sponsor | **Matt Justice** | 2026-07-22 | Approves policies; accepts residual risk. Owns all roles for now. |
| Security owner | **Matt Justice** | 2026-07-22 | Policies, access reviews, IR, vendor risk |
| Engineering owner | **Matt Justice** | 2026-07-22 | Change management, SDLC, logging, env separation |
| Ops / CS privileged access owner | **Matt Justice** | 2026-07-22 | White-glove loads, tenant support access |

One person may hold multiple roles; still write the names so accountability is clear. Roles may be split later without changing Type I scope.

---

## Confirmation block (Matt)

When you are ready to formally lock this log (optional if already acting under the decisions above), complete:

| Field | Value |
|-------|--------|
| Confirmed by | Matt Justice — _signature / typed name when ready_ |
| Date | |
| Exceptions / changes from proposed | Scope and owners set 2026-07-22; platform still TBD |

---

## Change history

| Date | What changed | Who |
|------|--------------|-----|
| 2026-07-22 | Initial log created | Kickoff |
| 2026-07-22 | Proposed defaults: Sec+Avail+Conf; PI deferred; Privacy skip; platform TBD/wait; security/sponsor Matt Justice TBD confirm | Agent (readiness kickoff) |
| 2026-07-22 | Confirmed scope Sec+Avail+Conf; PI deferred; Privacy skip; all named owners → Matt Justice; platform left TBD (Matt to decide) | Agent (compliance checklist wave) |
