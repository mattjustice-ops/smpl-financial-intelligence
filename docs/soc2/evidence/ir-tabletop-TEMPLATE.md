# IR tabletop evidence — YYYY-MM-DD

> **Tabletop ≠ real incident.** Fill this during/after the exercise in [../runbooks/ir-tabletop.md](../runbooks/ir-tabletop.md).  
> Sanitized only — no API keys, connection strings, customer emails, or raw dumps.  
> Completing this file after a real run = operable-IR evidence. **Not** SOC 2 certification.

## Status: AWAITING RUN

| Field | Value |
|-------|--------|
| Date of exercise | YYYY-MM-DD |
| Start–end (UTC) | |
| Facilitator | Matt Justice |
| Attendees | Matt Justice (solo) |
| Related policy | [P04](../policies/P04_incident_response_plan.md) |
| Runbook | [../runbooks/ir-tabletop.md](../runbooks/ir-tabletop.md) |
| Scenarios run | ☐ A (credential leak) ☐ B (AI hallucination → customer) |
| Real production actions taken? | **No** — tabletop only (change if escalated) |
| Pass / complete? | ☐ Notes complete (exercise done) |

---

## Scenario A — Leaked API / credential exposure

| Phase | Notes (what you would do / decided) |
|-------|-------------------------------------|
| Detect / report | |
| Classify (severity) | Expected working default: **Sev2+** |
| Contain (planned; not executed) | |
| Eradicate | |
| Recover | |
| Notify (draft only — do not send) | |
| Lessons learned | |

---

## Scenario B — AI hallucination / unsupported claim reached a customer

| Phase | Notes (what you would do / decided) |
|-------|-------------------------------------|
| Detect / report | |
| Classify (severity) | Expected working default: **Sev2** (P04 §4 / P15 §4.7) |
| Contain (planned; not executed) | |
| Eradicate | Grounding/validation **fail-open** ☐ / freeze-ID binding gap ☐ / other: _(do not use “skipped human review” as primary root cause)_ |
| Recover | |
| Notify (draft only — do not send) | |
| Lessons learned | |

---

## Cross-cut findings

-

## Follow-ups

| # | Action | Owner | Due | Done? |
|---|--------|-------|-----|-------|
| 1 | | Matt Justice | | ☐ |
| 2 | | Matt Justice | | ☐ |
| 3 | | Matt Justice | | ☐ |

---

## Sign-off

| Role | Name | Date | Signature / note |
|------|------|------|------------------|
| Facilitator | Matt Justice | | |
| Security owner | Matt Justice | | Tabletop complete; notes filed |

Related: [P04](../policies/P04_incident_response_plan.md) · [P15](../policies/P15_ai_llm_data_handling.md) · [runbook](../runbooks/ir-tabletop.md) · [PROGRESS](../PROGRESS.md)

_After filing: rename this copy to `ir-tabletop-YYYY-MM-DD.md`, set Status to **COMPLETE**, mark PROGRESS IR tabletop `[x]`, sync `/compliance` data._
