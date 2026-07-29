# SOC 2 evidence (sanitized)

Put **sanitized** markdown notes here (counts, dates, pass/fail, screenshots described in text).  

**Do not commit:** connection strings, API keys, customer emails, or raw query dumps.  
Use `*.local.md` for scratch notes containing secrets (gitignored).

| Template / example | Use |
|--------------------|-----|
| [ir-tabletop-TEMPLATE.md](./ir-tabletop-TEMPLATE.md) | Copy → `ir-tabletop-YYYY-MM-DD.md` after running [../runbooks/ir-tabletop.md](../runbooks/ir-tabletop.md) |
| [ir-tabletop-2026-07-28.md](./ir-tabletop-2026-07-28.md) | IR tabletop **complete** 2026-07-28 — Scenarios A + B; async/chat-facilitated; operable-IR readiness evidence (not certification) |
| [neon-restore-test-2026-07-27.md](./neon-restore-test-2026-07-27.md) | Neon PITR restore fire drill (Pass) |
| [dependabot-enabled-2026-07-28.md](./dependabot-enabled-2026-07-28.md) | Dependabot config (PR #19) + GitHub Code security toggles confirmed 2026-07-28 |
| [access-review-2026-Q3.md](./access-review-2026-Q3.md) | First quarterly-style access review — **COMPLETE / signed 2026-07-29** (Matt Justice; OK/Allow; readiness only — not certified) |
| [secrets-env-store-spotcheck-TEMPLATE.md](./secrets-env-store-spotcheck-TEMPLATE.md) | Template for secrets env-store spot-check |
| [secrets-env-store-spotcheck-2026-07-29.md](./secrets-env-store-spotcheck-2026-07-29.md) | **Pass 2026-07-29** — git + Vercel/Railway/Neon consoles (Matt chat attestation); readiness only — not certified |
| [tenant-isolation-TEMPLATE.md](./tenant-isolation-TEMPLATE.md) | Template for Org A ≠ Org B isolation test |
| [tenant-isolation-2026-07-29.md](./tenant-isolation-2026-07-29.md) | **Pass 2026-07-29** — unit/SQL/unauth + Matt confirmed Org-B-only T1/T2 via chat; readiness only — not certified |
| [security-one-pager-published-2026-07-29.md](./security-one-pager-published-2026-07-29.md) | Security one-pager **published for sales under NDA 2026-07-29** — markdown + PDF; no public `/security` page; readiness only — not certified |
| [vendor-soc/](./vendor-soc/) | Vendor SOC / ISO collection scaffold — tracker + request templates; **PDFs outside git / gitignored** — collection **in progress**, not complete |
