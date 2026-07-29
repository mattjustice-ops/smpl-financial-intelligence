# Dependabot + GitHub Code security — 2026-07-28

> **Readiness evidence only.** Enabling Dependabot and secret scanning ≠ SOC 2 certification — Type I requires an independent CPA report.

## Status: CONFIRMED

| Field | Value |
|-------|--------|
| Date confirmed | 2026-07-28 |
| Confirmed by | Matt Justice |
| Repository | `mattjustice-ops/smpl-financial-intelligence` |
| Config merged | PR **#19** on `main` — `.github/dependabot.yml` (npm `/frontend`, pip `/backend`, weekly Monday) |

## GitHub Code security toggles (Matt confirmed enabled)

| Toggle | Status |
|--------|--------|
| Dependabot alerts | Enabled |
| Dependabot security updates | Enabled |
| Secret scanning (Secret Protection) | Enabled |
| Push protection | Enabled |

## Notes

- Dependabot version-update PRs were already opening on the repo at fetch time (e.g. `dependabot/npm_and_yarn/frontend/*`, `dependabot/pip/backend/*` branches), consistent with alerts + config live.
- Pre-commit secret scan on developer machines (e.g. gitleaks) remains an optional follow-up from IR tabletop Scenario A — **not** claimed done here.
- Related: [P05](../policies/P05_change_management_policy.md) §6, [CHANGE_MANAGEMENT.md](../CHANGE_MANAGEMENT.md), [ir-tabletop-2026-07-28.md](./ir-tabletop-2026-07-28.md) follow-up #1.
