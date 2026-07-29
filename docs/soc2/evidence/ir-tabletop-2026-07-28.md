# IR tabletop evidence — 2026-07-28

> **Tabletop ≠ real incident.** No production secrets were rotated, no customer emails were sent, and no live containment actions were executed during this exercise.  
> Completing this file = **operable-IR readiness evidence** only. **Not** SOC 2 certification — Type I requires an independent CPA report.

## Status: COMPLETE

| Field | Value |
|-------|--------|
| Date of exercise | 2026-07-28 |
| Start–end (UTC) | 2026-07-28 17:05 → 18:00 UTC (~55 min) |
| Facilitation | **Async / chat-facilitated** — Cursor agent walked P04 §5 phases against runbook injects; Matt Justice (solo founder) wore all IR hats and provided **Allow** on Scenario B rewrite + tabletop closeout via chat 2026-07-28 |
| Attendees | Matt Justice (solo — Security / Eng / Exec / Ops roles); **not** a live multi-person meeting |
| Related policy | [P04](../policies/P04_incident_response_plan.md); [P15](../policies/P15_ai_llm_data_handling.md) v1.1 Approved 2026-07-28 |
| Design targets | [../controls/README.md](../controls/README.md) |
| Runbook | [../runbooks/ir-tabletop.md](../runbooks/ir-tabletop.md) |
| Scenario B rewrite | **Allowed 2026-07-28** by Matt Justice (chat) — controls-aligned prevent path |
| Scenarios run | ☑ A (credential leak) ☑ B (AI hallucination → customer) |
| Real production actions taken? | **No** — tabletop / planned actions only |
| Pass / complete? | ☑ Notes complete — exercise closed 2026-07-28 |

---

## Scenario A — Leaked API / credential exposure

**Inject (fictional):** Railway / Anthropic / Neon API key pasted into a public GitHub issue comment on the SMPL repo ~6 hours ago; bot may have scraped it; no confirmed customer-data access.

| Phase | Notes |
|-------|--------|
| **Detect / report** | **Hat: Security owner.** Self-discovery via GitHub notification (Dependabot secret scanning alert or manual review while triaging issues). Record fictional issue URL + screenshot description (sanitized — no secret value in evidence). Time discovered: T+0 (~6 h after paste). Time reported to IC: immediate (same person). Intake channel: corporate email / GitHub — working per P04. |
| **Classify (severity)** | **Sev2+** per P04 §4 playbook row “secret in git.” Scope: production API keys (Railway backend, Neon DB, Anthropic LLM) — Confidential per P06; not yet confirmed tenant-data exfil. Escalate to **Sev1** only if logs show authenticated access to Customer Data with the leaked credential or confirmed cross-tenant query. Start timeline: T+0 discovery → T+15 min classification complete. |
| **Contain (planned; not executed)** | **Hat: Engineering.** Order of operations (planned): (1) Revoke/disable the exposed GitHub PAT or token class if applicable; (2) Rotate **Neon** DB credentials first (data plane); (3) Rotate **Railway** service env vars + redeploy API; (4) Rotate **Anthropic** API key; (5) Rotate **Vercel** preview/prod env if any shared key class; (6) Review **Stripe** / **Resend** only if same key material was exposed (inject: backend stack keys only). Disable old keys before new deploy completes. No customer-facing kill switch needed for this inject. Evidence to keep: rotation checklist with timestamps (real incident only). |
| **Eradicate** | Remove secret from issue (delete comment); open PR to purge from git history if the key ever touched a commit (`git filter-repo` or GitHub secret-removal workflow). Root cause: human error — pasted key into public channel. Follow-ups: confirm GitHub **secret scanning** + push protection enabled; pre-commit secret scan (e.g. gitleaks) on developer machines; reiterate env-only policy (P05) in onboarding checklist. |
| **Recover** | Redeploy Railway with new env vars; smoke-test auth, API health, one read-only tenant query; confirm old Neon connection string returns auth failure; confirm Anthropic calls succeed with new key. Validation: 401/403 on old credentials; app green on new credentials; no error spike in logs (real incident). |
| **Notify (draft only — do not send)** | **Hat: Exec.** Internal: decision log entry (solo — note to self sufficient). Customer notice: **not required** for this inject unless rotation logs show the key was used to access Customer Data — none assumed. Vendor notice: optional heads-up to Anthropic/Neon abuse teams if scraping confirmed. Draft (if needed): *“We rotated an API credential after potential exposure in a public channel; we have no evidence of unauthorized access to your data.”* Counsel: not engaged for Sev2+ without confirmed data access. |
| **Lessons learned** | P04 secret-in-git playbook is operable solo. Dependabot/secret scanning **confirmed 2026-07-28** (follow-up #1 closed — [dependabot-enabled-2026-07-28.md](./dependabot-enabled-2026-07-28.md)). Remaining gap: no documented rotation runbook order beyond P04 table — acceptable for solo founder but worth a one-page checklist. Annual tabletop cadence satisfied for 2026. |

---

## Scenario B — AI hallucination / unsupported claim reached a customer

> **Allowed 2026-07-28** by Matt Justice on the rewritten Scenario B (runbook + evidence). Root-cause framing = automated gate **fail-open**, not “skipped human review.”

### Inject (summary)

Customer-visible AI commentary: **+18% QoQ** MRR + **EMEA enterprise expansion** driver; freeze supports **~4% QoQ** and **no EMEA driver**. Package already delivered externally.

### Expected prevention (system design — cite controls)

| Control | Expected role in prevention | Honest status ([controls README](../controls/README.md)) |
|---------|----------------------------|----------------------------------------------------------|
| Freeze-ID binding | Package/narrative bound to correct freeze; wrong-freeze packaging blocked | **Partial implemented** + required design |
| `_sources` / provenance | LLM may only state values present in evidence | **Required design / roadmap** |
| Structural claim verify | Numbers **and** driver attributions checked vs freeze | **Required design / roadmap** (partial variance tie-out exists) |
| Tie-out / second-pass gates | FAIL blocks emit/deploy | **Required design / roadmap** (partial close/export paths) |
| Fail-closed / don't-know | Unresolved → omit / don't-know | **Required design / roadmap** |
| Human role | IR / exceptions / periodic testing — **not** day-to-day gate | By design (P15 §4.8) |

**Residual scenario for this exercise:** one or more machine-primary gates **failed open** (bug/misconfig) — e.g. MDA variance tie-out returned warnings-only instead of blocking emit, or structural claim verify was not enforced on driver attributions — allowing +18% / EMEA packaging despite freeze ~4% / no EMEA. Large commentary-vs-engine variance is itself the detection signal (P15 §4.7).

| Phase | Notes |
|-------|--------|
| **Detect / report** | **Hat: Security owner / Ops.** Customer email to support: board package commentary shows +18% QoQ MRR driven by “EMEA enterprise expansion”; customer’s finance team compared to internal numbers (~4%). Intake: corporate email. Time discovered: T+0 (customer report). Do **not** treat “customer should have caught it” as the control failure — the variance is evidence of gate fail-open. Cross-check: pull freeze ID, period, org (sanitized org id in real incident — no PII in git evidence). |
| **Classify (severity)** | **Sev2** (P04 §4; P15 §4.7–§4.8). Material incorrect financial claim + wrong-context driver packaging delivered externally. Not Sev3: trust-critical, potential board/investor decisions. Not Sev1 unless confirmed widespread wrong data across many tenants with regulatory breach — single-org inject stays Sev2. Data categories: aggregated financial metrics (Confidential). Timeline: T+0 report → T+30 min severity + scope documented. |
| **Contain (planned; not executed)** | **Hat: Engineering.** (1) Identify affected **freeze ID**, package version, org, period — stop further emits for that path. (2) **Technical stop:** disable narrative generation path via env/feature flag or hotfix that fails closed (honest: no customer kill-switch UI — use Railway env disable of commentary job / MD&A path per P15 §6.1). (3) Do **not** re-ship from stale cache. (4) Prepare corrected customer output: values and drivers **only** from freeze evidence / engine export — no LLM re-generation until gates verified. (5) Preserve logs (30-day retention per P15) for RCA. |
| **Eradicate / prevent** | **Root cause (exercise): gate fail-open** — most plausible given partial implementation snapshot: `verify_variance_commentary_tieout` or similar path emitted **warnings** without blocking customer-visible publish; and/or **structural claim verify** + **`_sources` enforcement** not yet product-wide (controls README). **Not** root cause: “skipped human review before send.” Fix path (planned tickets): enforce FAIL-not-warn on commentary-vs-freeze variance over material threshold; implement `_sources` contract on all LLM payloads; harden freeze-ID binding on all customer-facing packages; add second-pass block before emit per [data_integrity_framework.md](../controls/data_integrity_framework.md). Humans remain IR / exceptions / **periodic control testing** — not primary gate. |
| **Recover** | Deliver corrected board package / commentary bound to same freeze ID with figures matching engine (~4% QoQ; no EMEA driver claim). Customer validates against their copy. Re-enable narrative path only after hotfix proves fail-closed behavior in staging (or prod canary) — document which roadmap layers still partial. |
| **Notify (draft only — do not send)** | **Hat: Exec.** Customer correction **required** for exercise narrative. Draft: *“We identified an error in AI-generated commentary in your [period] board package. The correct QoQ MRR change per your frozen data is approximately 4%, and there was no EMEA enterprise expansion driver in that period. We have corrected the output and taken steps to prevent unsupported claims from shipping. We are not aware of other affected packages for your organization.”* Exec approval = Matt (recorded). No broad public notice unless multi-tenant scope expands. |
| **Lessons learned** | IR path for AI Sev2 is walkable and aligned with P15 v1.1 + controls README. **Residual risk (honest):** until `_sources`, structural claim verify, and second-pass emit gates ship **fail-closed** in production, the realistic failure mode is gate fail-open (bug/misconfig or warnings-only partial paths) — not absence of policy. Product safety rises as roadmap gates ship; tabletop validates operability of P04 containment row for AI hallucination. |

### Scenario B — residual risk summary

| Risk | Severity | Mitigation status |
|------|----------|-------------------|
| Unsupported numeric claims reach customers | High (trust) | Partial freeze/tie-out paths; full fail-closed framework **roadmap** |
| Wrong-context driver/region packaging | High (trust) | Structural verify **required design** — not fully enforced |
| Gates fail open (warnings-only, missing `_sources`) | **This exercise’s root cause** | Engineering tickets to harden; periodic control testing when gates ship |
| Over-reliance on human pre-send review | Rejected posture | P15 + IR framing explicitly exclude as primary control |

---

## Cross-cut findings

- **P04 operability:** Solo founder can execute detect → classify → contain → eradicate → recover → notify → lessons for both secret exposure (Sev2+) and AI hallucination (Sev2) without live production actions.
- **Scenario B alignment:** Root-cause language matches P15 v1.1 Approved + controls README — fail-open gates, not human-review skip.
- **Honesty:** Full framework layers (`_sources`, second-pass emit block, Rule Sets A–F publish gate) are **required design / roadmap** where not yet shipping; partial freeze/tie-out paths exist — evidence does not overclaim prod coverage.
- **Facilitation model:** Async/chat tabletop is valid readiness evidence for a solo founder; auditor can review dated notes + runbook traceability.

---

## Follow-ups

| # | Action | Owner | Due | Done? |
|---|--------|-------|-----|-------|
| 1 | Confirm GitHub Dependabot / secret scanning enabled on SMPL repo (P05) | Matt Justice | Month 2 | ☑ **2026-07-28** — PR #19 + 4 Code security toggles — [dependabot-enabled-2026-07-28.md](./dependabot-enabled-2026-07-28.md) |
| 2 | First quarterly-style access review sign-off | Matt Justice | Week 3–4 | ☑ **2026-07-29** — OK/Allow; [access-review-2026-Q3.md](./access-review-2026-Q3.md) |
| 3 | Vendor SOC / ISO report collection started (Vercel, Railway, Neon, Stripe, Anthropic, Resend, …) | Matt Justice | Week 3–4 | ☐ |
| 4 | Customer DPA / MSA — outline → counsel redline | Matt Justice | Week 3–4 | ☐ (outline drafted) |
| 5 | Engineering: harden fail-closed gates per [controls/README.md](../controls/README.md) — `_sources`, structural claim verify, second-pass emit block | Matt Justice | Month 2+ | ☐ |
| 6 | Optional: one-page secret rotation order checklist derived from P04 + Scenario A | Matt Justice | Month 2 | ☐ |
| 7 | Next annual IR tabletop (or before Type I fieldwork if sooner) | Matt Justice | ~2027-07 | ☐ |

---

## Sign-off

| Role | Name | Date | Signature / note |
|------|------|------|------------------|
| Facilitator / all IR hats | Matt Justice | 2026-07-28 | Tabletop complete; notes filed; async/chat closeout |
| Security owner | Matt Justice | 2026-07-28 | Scenario B rewrite Allowed 2026-07-28; exercise closed same date |
| Approver (Scenario B rewrite + closeout) | Matt Justice | 2026-07-28 | Chat Allow recorded on branch `soc2/p15-v11-scenario-b-allow` |

Related: [P04](../policies/P04_incident_response_plan.md) · [P15](../policies/P15_ai_llm_data_handling.md) · [controls](../controls/README.md) · [runbook](../runbooks/ir-tabletop.md) · [PROGRESS](../PROGRESS.md)
