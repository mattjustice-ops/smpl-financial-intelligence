# IR tabletop evidence — 2026-07-28 (WIP)

> **Tabletop ≠ real incident.**  
> **STATUS: WIP — NOT COMPLETE.** Do not mark PROGRESS IR tabletop `[x]` from this file.  
> Scenario B text rewritten for Matt Allow (machine-primary / fail-open root cause).  
> Complete dated notes for **both** scenarios only after Matt Allows Scenario B (and preferably P15 v1.1 redline).  
> Sanitized only — no secrets, no customer emails. **Not** SOC 2 certification. **No forged approvals.**

## Status: WIP / AWAITING MATT ALLOW ON SCENARIO B

| Field | Value |
|-------|--------|
| Date of exercise | 2026-07-28 (pack / redline day — full run not closed) |
| Start–end (UTC) | _pending full run after Allow_ |
| Facilitator | Matt Justice |
| Attendees | Matt Justice (solo) |
| Related policy | [P04](../policies/P04_incident_response_plan.md); [P15](../policies/P15_ai_llm_data_handling.md) v1.1 draft |
| Runbook | [../runbooks/ir-tabletop.md](../runbooks/ir-tabletop.md) |
| Scenarios run | ☐ A (credential leak) ☐ B (AI hallucination → customer) — B awaiting **Allow** on rewrite |
| Real production actions taken? | **No** — tabletop / docs only |
| Pass / complete? | ☐ Notes complete — **not yet** |

---

## Scenario A — Leaked API / credential exposure

| Phase | Notes |
|-------|--------|
| Detect / report | _Fill after run_ |
| Classify (severity) | Expected working default: **Sev2+** |
| Contain (planned; not executed) | |
| Eradicate | |
| Recover | |
| Notify (draft only — do not send) | |
| Lessons learned | |

---

## Scenario B — AI hallucination / unsupported claim reached a customer

> **Awaiting Matt Allow** on the rewritten Scenario B in chat / runbook before treating exercise notes as final.

| Phase | Working expected answers (pre-Allow draft — not signed evidence) |
|-------|--------|
| Detect / report | Customer reports commentary **+18% QoQ** + EMEA expansion driver vs freeze **~4%** / no EMEA |
| Classify (severity) | **Sev2** (P04 §4 / P15 §4.7) |
| Contain (planned; not executed) | Technical stop: feature flag if exists / disable narrative path / hotfix; correct customer output; bind to freeze ID |
| Eradicate | Grounding/validation **fail-open** (bug/misconfig) — **not** “skipped human review”; fix gate → fail closed; freeze-ID binding; structural claim verification |
| Recover | Corrected output; re-enable only after fail-closed gate verified |
| Notify (draft only — do not send) | Customer correction narrative; exec approval noted; no live send |
| Lessons learned | Machine-primary controls; humans = IR / exceptions / periodic testing |

---

## Cross-cut findings

- WIP: align IR root-cause language with P15 v1.1 draft (pending Allow).

## Follow-ups

| # | Action | Owner | Due | Done? |
|---|--------|-------|-----|-------|
| 1 | Matt Allow rewritten Scenario B | Matt Justice | | ☐ |
| 2 | Matt Allow / skim P15 v1.1 PR redline | Matt Justice | | ☐ |
| 3 | Complete evidence for A + B after Allow; then mark PROGRESS `[x]` | Matt Justice | | ☐ |

---

## Sign-off

| Role | Name | Date | Signature / note |
|------|------|------|------------------|
| Facilitator | Matt Justice | | **WIP — not complete; no Allow forged** |
| Security owner | Matt Justice | | Tabletop **not** complete |

Related: [P04](../policies/P04_incident_response_plan.md) · [P15](../policies/P15_ai_llm_data_handling.md) · [runbook](../runbooks/ir-tabletop.md) · [PROGRESS](../PROGRESS.md)
