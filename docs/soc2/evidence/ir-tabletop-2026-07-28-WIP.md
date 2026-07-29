# IR tabletop evidence — 2026-07-28 (WIP)

> **Tabletop ≠ real incident.**  
> **STATUS: WIP — NOT COMPLETE.** Do not mark PROGRESS IR tabletop `[x]` from this file.  
> Scenario B rewrite **Allowed 2026-07-28** by Matt Justice (chat); P15 v1.1 **Approved 2026-07-28**.  
> Allow unblocks finalizing notes — the **45–60 min tabletop exercise still needs to be run** and both scenarios filled with dated evidence.  
> Sanitized only — no secrets, no customer emails. **Not** SOC 2 certification.

## Status: WIP — SCENARIO B ALLOWED; FULL RUN PENDING

| Field | Value |
|-------|--------|
| Date of exercise | 2026-07-28 (pack / redline day — **full run not closed**) |
| Start–end (UTC) | _pending full 45–60 min run_ |
| Facilitator | Matt Justice |
| Attendees | Matt Justice (solo) |
| Related policy | [P04](../policies/P04_incident_response_plan.md); [P15](../policies/P15_ai_llm_data_handling.md) v1.1 Approved |
| Design targets | [../controls/README.md](../controls/README.md) |
| Runbook | [../runbooks/ir-tabletop.md](../runbooks/ir-tabletop.md) |
| Scenario B rewrite | **Allowed 2026-07-28** by Matt Justice (chat) — controls-aligned prevent path |
| Scenarios run | ☐ A (credential leak) ☐ B (AI hallucination → customer) — **exercise not yet run** |
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

> **Allowed 2026-07-28** by Matt Justice on the rewritten Scenario B (runbook + this evidence). Exercise notes below are **working expected answers** — not signed evidence until the full tabletop run is completed.

### Inject (summary)

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

| Phase | Working expected answers (finalize after full run) |
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

- IR root-cause language aligned with P15 v1.1 + controls README (Allowed 2026-07-28).
- Honesty: full framework layers are **required design / roadmap** where not yet shipping; partial freeze/tie-out paths exist — do not overclaim.

## Follow-ups

| # | Action | Owner | Due | Done? |
|---|--------|-------|-----|-------|
| 1 | Matt Allow rewritten Scenario B | Matt Justice | 2026-07-28 | ☑ Allowed (chat) |
| 2 | Matt Allow / skim P15 v1.1 redline (+ controls docs) | Matt Justice | 2026-07-28 | ☑ Approved v1.1 |
| 3 | Complete evidence for A + B after full run; then mark PROGRESS `[x]` | Matt Justice | | ☐ |

---

## Sign-off

| Role | Name | Date | Signature / note |
|------|------|------|------------------|
| Facilitator | Matt Justice | | **WIP — full tabletop not complete** |
| Security owner | Matt Justice | | Scenario B rewrite Allowed 2026-07-28; exercise run pending |

Related: [P04](../policies/P04_incident_response_plan.md) · [P15](../policies/P15_ai_llm_data_handling.md) · [controls](../controls/README.md) · [runbook](../runbooks/ir-tabletop.md) · [PROGRESS](../PROGRESS.md)
