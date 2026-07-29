# IR tabletop evidence — 2026-07-28 (WIP)

> **Tabletop ≠ real incident.**  
> **STATUS: WIP — NOT COMPLETE.** Do not mark PROGRESS IR tabletop `[x]` from this file.  
> Scenario B rewritten for Matt Allow (machine-primary gates + integrity framework / tie-out design targets).  
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
| Design targets | [../controls/README.md](../controls/README.md) |
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

### Inject (summary for Allow)

Customer-visible AI commentary: **+18% QoQ** MRR + **EMEA enterprise expansion** driver; freeze supports **~4%** and **no EMEA driver**. Package already delivered.

### Expected prevention (system design — cite controls)

| Control | Expected role in prevention |
|---------|----------------------------|
| Freeze-ID binding | Package/narrative bound to correct freeze; wrong-freeze packaging blocked |
| `_sources` / provenance | LLM may only state values present in evidence |
| Structural claim verify | Numbers **and** driver attributions checked vs freeze |
| Tie-out / second-pass gates | FAIL blocks emit/deploy (design target; partial paths may exist) |
| Fail-closed / don't-know | Unresolved → omit / don't-know |
| Human role | IR / exceptions / periodic testing — **not** day-to-day gate |

**Residual scenario:** gates **failed open** (bug/misconfig) — not “skipped human review.” Large commentary-vs-engine variance = unacceptable control failure (P15).

| Phase | Working expected answers (pre-Allow draft — not signed evidence) |
|-------|--------|
| Detect / report | Customer reports commentary **+18% QoQ** + EMEA expansion driver vs freeze **~4%** / no EMEA |
| Classify (severity) | **Sev2** (P04 §4 / P15 §4.7–§4.8) |
| Contain (planned; not executed) | Technical stop: feature flag if exists / disable narrative path / hotfix; correct customer output; bind to freeze ID; honesty on which product controls exist |
| Eradicate / prevent | Identify which gate failed open; restore `_sources` + structural verify + freeze-ID + tie-out/second-pass fail-closed — **not** “add human review before send as primary” |
| Recover | Corrected output matching freeze/`_sources`; re-enable only after fail-closed gate verified |
| Notify (draft only — do not send) | Customer correction narrative; exec approval noted; no live send |
| Lessons learned | Prevention expected via [../controls/](../controls/README.md) + P15; residual = fail-open; safety rises as gates ship; humans = IR / exceptions / periodic testing |

---

## Cross-cut findings

- WIP: align IR root-cause language with P15 v1.1 + controls README (pending Allow).
- Honesty: full framework layers are **required design / roadmap** where not yet shipping; partial freeze/tie-out paths exist — do not overclaim.

## Follow-ups

| # | Action | Owner | Due | Done? |
|---|--------|-------|-----|-------|
| 1 | Matt Allow rewritten Scenario B | Matt Justice | | ☐ |
| 2 | Matt Allow / skim P15 v1.1 PR redline (+ controls docs) | Matt Justice | | ☐ |
| 3 | Complete evidence for A + B after Allow; then mark PROGRESS `[x]` | Matt Justice | | ☐ |

---

## Sign-off

| Role | Name | Date | Signature / note |
|------|------|------|------------------|
| Facilitator | Matt Justice | | **WIP — not complete; no Allow forged** |
| Security owner | Matt Justice | | Tabletop **not** complete |

Related: [P04](../policies/P04_incident_response_plan.md) · [P15](../policies/P15_ai_llm_data_handling.md) · [controls](../controls/README.md) · [runbook](../runbooks/ir-tabletop.md) · [PROGRESS](../PROGRESS.md)
