# Incident Response tabletop exercise (SOC 2 / P04)

> **This is a tabletop exercise — not a real incident.**  
> Walk the P04 process with fictional injects. Do **not** rotate production secrets, revoke live access, or notify customers unless you separately decide a real issue exists.  
> Completing the notes / evidence file = readiness evidence that the IR plan is **operable**. It is **not** SOC 2 certification.

| Field | Value |
|-------|--------|
| Related policy | [P04 Incident Response Plan](../policies/P04_incident_response_plan.md) |
| Related | [P15 AI / LLM Data Handling](../policies/P15_ai_llm_data_handling.md) (Scenario B); [P12](../policies/P12_backup_and_restore.md) if restore discussed |
| Owner / facilitator | Matt Justice (solo founder — all IR roles) |
| Duration | ~45–60 minutes |
| Cadence | At least annually, or before Type I fieldwork ([P04](../policies/P04_incident_response_plan.md) §7) |
| Evidence | Copy [../evidence/ir-tabletop-TEMPLATE.md](../evidence/ir-tabletop-TEMPLATE.md) → `ir-tabletop-YYYY-MM-DD.md` and fill during/after the run |

---

## Purpose

Exercise the approved Incident Response Plan ([P04](../policies/P04_incident_response_plan.md)) so Matt can demonstrate:

1. Severity classification (especially **Sev2** for secret exposure and AI hallucination reaching a customer).
2. Solo-founder role switching (Security / Eng / Exec / Ops are all Matt — still name the hat at each step).
3. Containment playbook actions from P04 §5 without executing them on production during the exercise.
4. Customer notification decision criteria and post-incident lessons learned.

**Out of scope for this session:** live forensics, actual secret rotation, customer emails, counsel engagement, or changing production config.

---

## Agenda (~45–60 min) — solo Matt Justice

| Min | Block | What you do |
|-----|-------|-------------|
| 0–5 | Setup | Open P04 + this runbook. Copy evidence template to `docs/soc2/evidence/ir-tabletop-YYYY-MM-DD.md`. Note start time (UTC). Remind yourself: **tabletop ≠ real incident**. |
| 5–25 | Scenario A | Leaked API / credential exposure — full IR step-through (below). Capture decisions in the evidence file as you go. |
| 25–45 | Scenario B | AI hallucination / unsupported claim reached a customer (P15 §4.7 → P04 Sev2) — same step-through. |
| 45–55 | Cross-cut | Compare findings across A and B. List follow-ups (runbook gaps, tooling, fail-closed grounding / freeze-ID binding). |
| 55–60 | Sign-off | Fill sign-off table. Mark PROGRESS / `/compliance` **only after** notes are filed (this pack alone does not close the item). |

If short on time: run **one** scenario fully (≥30 min) and note the other as deferred — still file evidence with that honesty.

---

## Roles (solo founder)

During the exercise, say out loud (or write in notes) which hat you are wearing:

| Hat | Responsibility | Holder |
|-----|----------------|--------|
| Security owner / IC | Severity, timeline, customer-notice decision | Matt Justice |
| Engineering | Contain / eradicate / recover actions | Matt Justice |
| Executive sponsor | Approve external comms for material incidents | Matt Justice |
| Ops / CS | Customer channel if notified | Matt Justice |

Intake channel (working): corporate email / phone — confirm preferred channel in notes if still open in P04.

---

## Shared IR step-through (use for both scenarios)

Work each inject through P04 §5. For every phase, write **what you would do**, **who you’d tell**, and **what evidence you’d keep** — do not execute live actions in this exercise.

### 1. Detect / report

- How did you learn about it? (self-report, customer ticket, GitHub alert, vendor notice, board-package review, etc.)
- Record: reporter, time discovered, time reported to IC (same person is fine).

### 2. Classify (triage)

- Confirm scope: systems, tenants, data categories ([P06](../policies/P06_data_classification_and_handling.md)).
- Assign severity per P04 §4:

| Severity | When (reminder) |
|----------|-----------------|
| Sev1 | Confirmed customer-data breach; total prod outage |
| Sev2 | Likely compromise; major degradation; **or** hallucinated/incorrect AI claim delivered to a customer; **secret in git** → treat as Sev2+ |
| Sev3 | Limited impact; contained quickly |
| Sev4 | Suspicious; no confirmed impact |

- Start a timeline (who / what / when).

### 3. Contain

- First actions only from P04 containment playbook (see scenario sections).
- **Tabletop rule:** list the clicks / rotations you would perform; do not perform them unless you escalate to a real incident.

### 4. Eradicate

- Root cause: misconfig, leaked key, grounding/validation **fail-open**, freeze-ID binding gap, etc. (For Scenario B: do **not** frame root cause as “skipped human review.”)
- Fix path: ticket / PR / policy update — name it even if fictional for the exercise.

### 5. Recover

- Return to known-good: redeploy, restore per [P12](../policies/P12_backup_and_restore.md) if needed, re-enable feature after fix.
- Validation: how would you know it’s safe?

### 6. Notify

- Internal first (for solo: note to self / decision log is enough for the exercise).
- Customer notification: only if legally/contractually required or material risk to their data — **exec approval = Matt**.
- Draft one sentence of what you’d say (do not send).

### 7. Lessons learned

- Blameless write-up within **10 business days** for Sev1–2 (P04 §5).
- Control / policy updates? Add follow-ups to the evidence sign-off table.

---

## Scenario A — Leaked API / credential exposure

### Inject (fictional)

> You discover a Railway / Anthropic / Neon API key (or similar production secret) was pasted into a public GitHub issue comment on the SMPL repo ~6 hours ago. A bot may have scraped it. No confirmed customer-data access yet.

### Align to P04

| Field | Expected working answer (challenge yourself) |
|-------|-----------------------------------------------|
| Incident type | Exposure of secrets in git / public channels (P04 §3) |
| Default severity | **Sev2+** (P04 playbook: secret in git → Sev2+) |
| Containment row | Secret in git — rotate immediately; purge history if needed |

### Step prompts

1. **Detect** — Who found it? Screenshot / URL noted (fictional OK)?
2. **Classify** — Sev2 vs Sev1: when would you escalate to Sev1? (e.g. confirmed tenant data exfil).
3. **Contain** — Rotate which secrets, in which order (Vercel / Railway / Neon / Anthropic / GitHub)? Disable which tokens? Revoke sessions?
4. **Eradicate** — Remove secret from git history / issue; add pre-commit or secret scanning follow-up?
5. **Recover** — Redeploy with new env vars; smoke-check auth + API; confirm old key returns 401.
6. **Notify** — Customer notice if key scoped to customer data path? Counsel? Vendor?
7. **Lessons** — How does this not happen again (secret scanning, Dependabot/secret alerts, env-only policy spot-check)?

### Evidence to “imagine” keeping (do not fabricate live tickets unless real)

- Timeline notes
- Rotation checklist (systems touched)
- PR / issue links for purge + scanning
- Customer notification draft (if any)

---

## Scenario B — AI hallucination / unsupported claim reached a customer

> **Product posture (must follow in this exercise):** Primary controls are backend / automated **fail-closed** — provenance / `_sources`, structural claim verify, freeze-ID binding, tie-out / second-pass gates (P15 §4.7–§4.8; [../controls/README.md](../controls/README.md)). Do **not** treat “human review before send” or “customer should have re-validated” as root cause or primary control. Hypothetical only — no live actions.
>
> **How prevention is expected to work** (cite these; residual scenario = gates failed open):
> 1. Package bound to **freeze ID**; numbers/drivers only from freeze / engine evidence
> 2. LLM context carries **`_sources` / provenance**; Claude may only state values present in evidence
> 3. **Structural claim verify** (numbers + driver attributions) + **second-pass / tie-out** as emit or release gates — FAIL blocks ship
> 4. Unresolved → omit / **"don't know"** (fail closed)
> 5. Humans = IR / exceptions / **periodic control testing** — not the day-to-day gate
>
> Honesty: not all layers above are fully shipping yet — label **required design / roadmap** vs **partial implemented** per controls README. Do not claim full framework coverage in prod.

### Inject (fictional / hypothetical)

> A customer emails: their board package (or in-product customer-visible analysis) includes AI-generated commentary claiming MRR grew **+18% QoQ**, driven by **“expansion in EMEA enterprise.”** The warehouse / engine **freeze** for that period supports only **~4% QoQ** and has **no EMEA expansion driver**. The package was already delivered externally.
>
> **Root-cause framing for this exercise (required):** One or more machine-primary gates **failed open** (bug or misconfiguration) — e.g. missing/unenforced `_sources`, structural claim verify skipped, freeze-ID not bound, or tie-out/second-pass gate not blocking FAIL — so an unsupported numeric claim **and** wrong-context driver packaging were emitted despite the freeze. This is **not** “we skipped human review before send.” A large commentary-vs-engine variance (e.g. ~18% vs ~4%) is an **unacceptable control failure** and devastating to trust; users will misuse UI — the system must force the right path. **Residual risk scenario** for the tabletop = gates failed open, not “controls don’t exist as a product idea.”

### Align to P04 + P15

| Field | Expected working answer (challenge yourself) |
|-------|-----------------------------------------------|
| Incident type | AI-generated commentary reaching a customer with a claim that does not resolve to verified engine/warehouse evidence (P04 §3; P15 §4.7–§4.8) |
| Default severity | **Sev2** (P04 §4) |
| Containment row | Stop shipping bad commentary via **technical controls**; identify freeze ID / package / org / period; issue corrected output; document root cause as grounding/validation / gate **fail-open** (not human-review miss) |
| Root cause (exercise) | Automated gates **failed open** — bug/misconfig (provenance / claim verify / freeze bind / tie-out) |
| Prevention design | [../controls/data_integrity_framework.md](../controls/data_integrity_framework.md) + [../controls/data_sources_tieout_prompt.md](../controls/data_sources_tieout_prompt.md); P15 §4.8 |

### Step prompts

1. **Detect** — Customer report of variance (+18% / EMEA vs freeze ~4% / no EMEA). Note intake channel. Do not treat “customer should have caught it” as the control failure. Large commentary-vs-engine variance is itself the detection signal of gate fail-open.
2. **Classify** — Why Sev2 (not Sev3)? Material incorrect financial claim and wrong-context packaging delivered externally. Per P15: large commentary-vs-engine variance is an unacceptable control failure / trust-critical.
3. **Contain** — Stop further bad commentary with **real technical controls**: feature flag if one exists, disable narrative generation path, and/or hotfix that fails closed. Identify freeze ID / package version / org / period. Issue corrected customer output bound to freeze evidence (values only from evidence). Honesty: only claim product controls that exist (P15 §6.1; controls README) — no fake customer kill-switch or “full `_sources` already everywhere” claims.
4. **Eradicate / prevent** — Restore the **expected** prevention path (system design), not a human checklist:
   - Enforce **`_sources` / provenance** on LLM payloads; Claude may only state values present in evidence
   - **Freeze-ID binding** for board/customer-facing packages
   - **Structural claim verify** (figures **and** drivers/regions/causes) against freeze evidence
   - **Automated tie-out / second-pass verification** as deploy or release (emit) gates — FAIL blocks ship
   - **Fail closed** → omit / don't-know on unresolved claims
   - Confirm which gate failed open (bug/misconfig) and fix so it cannot fail open again
   - Do **not** “eradicate” by adding human review before send as the primary control; humans remain IR / exceptions / periodic testing (framework Part 6 adapted — controls README)
5. **Recover** — Deliver corrected package/output; confirm commentary figures and drivers match the freeze / `_sources`; re-enable the narrative path only after the fail-closed gate(s) are verified (and note any still-roadmap layers honestly).
6. **Notify** — Customer correction (required for exercise narrative); any broader notice? Exec approval recorded. No live customer email in this tabletop.
7. **Lessons** — Prevention is expected via machine-primary controls in P15 §4.8 + controls docs. Residual scenario = gates failed open. Product safety rises as roadmap gates ship fail-closed. Humans = IR, exceptions, periodic control testing — not day-to-day re-validation of every output.

### Evidence to “imagine” keeping

- Affected output id / freeze ID / period (sanitized — no customer PII in git evidence)
- Which gate failed open (provenance / claim verify / freeze bind / tie-out/second-pass) — planned RCA only in tabletop
- Technical containment action (flag / path disable / hotfix) — planned only in tabletop
- Correction sent (describe; don’t paste customer email)
- Root-cause: gate **fail-open** (bug/misconfig) — not human-review miss
- Follow-up ticket / PR to harden fail-closed gates toward [../controls/](../controls/README.md) (honest partial vs roadmap)

---

## Notes template (inline quick capture)

Use during the live run if you prefer not to switch files mid-scenario; then copy into the dated evidence file.

```
Date (UTC):
Facilitator: Matt Justice
Scenarios run: A / B / both
Start–end:

--- Scenario A ---
Severity assigned:
Detect:
Classify:
Contain (planned only):
Eradicate:
Recover:
Notify (draft; not sent):
Lessons / follow-ups:

--- Scenario B ---
Severity assigned:
Detect:
Classify:
Contain (planned only):
Eradicate:
Recover:
Notify (draft; not sent):
Lessons / follow-ups:

Cross-cut findings:
```

---

## Sign-off table (copy into evidence file)

| Field | Value |
|-------|--------|
| Date of exercise | YYYY-MM-DD |
| Facilitator | Matt Justice |
| Attendees | Matt Justice (solo) |
| Scenarios run | A / B / both |
| Real production actions taken? | **No** (tabletop only) — or list if escalated |
| Findings (summary) | |
| Follow-ups (owner + due) | |
| Evidence filed | `docs/soc2/evidence/ir-tabletop-YYYY-MM-DD.md` |
| Facilitator sign-off | Name + date |

Completing and filing this table **is** the evidence artifact for “IR tabletop notes.” Until it exists with a real run date, PROGRESS stays open / awaiting run.

---

## After the run — close the loop

1. Save dated evidence under `docs/soc2/evidence/ir-tabletop-YYYY-MM-DD.md` (sanitized — no secrets, no customer emails).
2. Update [PROGRESS.md](../PROGRESS.md): mark IR tabletop notes `[x]` with date + evidence link.
3. Sync `frontend/lib/compliance/progress.ts` (`rem-ir-tabletop` → `done`; `bar-5` operable notes).
4. Optionally note the annual due date for the next tabletop in P04 or calendar.

---

## Honesty

| This pack proves | This pack does **not** prove |
|------------------|------------------------------|
| IR plan can be walked by the solo founder | SMPL is SOC 2 certified |
| Scenarios cover secret leak + AI Sev2 path | A real incident was handled |
| Notes template ready for auditor evidence | The exercise was completed (until Matt runs it) |

**Not SOC 2 certified.** Pursuing / readiness only until a CPA Type I report is in hand.

---

_End of IR tabletop runbook_
