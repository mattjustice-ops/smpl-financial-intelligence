# SMPL.ai — Company & Product Context
### For AI agent briefing (Claude Code, or any new project) — condensed from the full internal documentation set

This is a curated briefing, not the full architecture corpus. It's written to give an agent enough accurate context to help with marketing, positioning, or product-adjacent work — like a video — without needing to ingest 30+ engineering documents. If deeper technical detail is ever needed, it exists; ask for it specifically rather than assuming this document is incomplete.

---

## 1. What SMPL is

SMPL is a real-time financial intelligence platform built for B2B SaaS finance teams — CFOs, FP&A, RevOps, and executive leadership. It connects to a company's existing systems (CRM, ERP/GL, billing, HRIS) and turns fragmented data into one trusted, explainable, always-current operating model.

**Core vision, in one line:** every SaaS company should be able to operate like it has a world-class CFO team.

**It is not** a dashboard tool, a BI tool, or a reporting add-on. It's a decision-support system — it doesn't just show numbers, it explains what changed, why, and what to do about it.

## 2. The problem it solves

Finance teams spend most of their close cycle assembling data by hand across systems that were never built to talk to each other. The same number — revenue, ARR, headcount cost — often looks different depending on which system or spreadsheet you pull it from, and nobody can quickly explain why. Board decks go out with numbers nobody fully trusts, and by the time a report circulates, it's already stale.

## 3. What SMPL actually does (today, in production)

- **Fully reconciled financial statements** — GL detail rolled into an income statement, cash flow statement, and balance sheet where every number actually ties, automatically, every close.
- **Management P&L with real drilldown** — click any line, see the actual GL accounts behind it, actual vs. budget vs. forecast.
- **ARR and revenue intelligence** — the full waterfall (new, expansion, contraction, churn, reactivation), correct sign conventions, continuous view from actuals into forecast.
- **GTM and marketing efficiency** — pipeline and spend analyzed together, channel by channel.
- **Cash forecasting that understands SaaS billing cycles** — annual contract billing spikes and troughs modeled explicitly, not smoothed away by GAAP revenue recognition timing.
- **Workforce as a financial driver** — headcount, ramp, quota, and comp modeled as inputs to EBITDA and cash scenarios, not a static table.
- **Board-ready output** — narrative commentary generated automatically, in the tone and specificity of a real FP&A leader.

## 4. What makes SMPL different — the real differentiators

This matters more than it might seem: several competitors (including at least one — Cube — whose own marketing video looks and sounds very close to SMPL's positioning) already claim "one unified number across every tool." That claim alone is not a differentiator anymore. SMPL's actual, structural differences are:

- **No black boxes.** Every number traces back to its source record — the invoice, the opportunity, the GL entry. This isn't a UI feature, it's built into how the platform stores and calculates data.
- **Deterministic, reproducible calculations.** Run the same calculation twice, get the identical answer, always. Nothing is silently recalculated or rewritten — a board deck from March will always reproduce exactly as it was, even after later corrections.
- **Real explanations, not generic commentary.** The platform is explicitly designed to produce commentary like: *"Expansion ARR was favorable to forecast by $420K, driven by three enterprise upsells that closed early. New business bookings missed plan due to delayed opportunities in the West region."* Never: *"Revenue increased due to strong performance."* Specific, evidence-backed, or it says nothing at all.
- **It knows what it doesn't know.** Every number and every explanation carries an honest confidence signal. A shaky number is flagged as shaky — never quietly presented as certain.
- **Built for SaaS finance specifically**, not general BI — it understands ARR waterfalls, NRR/GRR, quota ramp curves, and the difference between management EBITDA and GAAP net income natively, not as a bolt-on.
- **Institutional memory.** The platform remembers why a forecast assumption changed, what the board was told last quarter, and what happened afterward — so that knowledge doesn't leave when someone on the team does.

**Strategic note for whoever is directing the creative work:** don't lead with "unified data across every tool" as the hero message — that's table stakes in this category now. Lead with trust, explainability, and evidence. That's the wedge competitors making similar-sounding videos are not actually built to back up structurally.

## 5. Honest status (important for anything customer-facing)

SMPL's production system serves real, paying customers today. In parallel, a much larger target architecture has been fully designed (not yet fully built) to deliver deeper guarantees — full determinism, complete evidence chains, institutional memory, formal governance over restatements — as the platform matures. Anything written for an external audience should describe current capability honestly and not imply the full target architecture is live today. When in doubt, favor present-tense claims only for what's actually running in production.

## 6. Audience and tone

**Audience:** CFOs, FP&A leaders, RevOps, and CEOs at growth-stage B2B SaaS companies — people who are financially sophisticated and skeptical of hype.

**Tone:** confident, plain-spoken, specific. Short sentences. No generic SaaS marketing language ("empower," "seamless," "revolutionize"). If a claim can't be made concrete with a real example, don't make it abstractly instead — cut it.

## 7. Light glossary (enough to not garble anything)

| Term | Meaning |
|---|---|
| ARR | Annual recurring revenue — forward-looking run-rate metric, not the same as GAAP revenue |
| ARR waterfall | New business + expansion − contraction − churn + reactivation = ending ARR |
| NRR / GRR | Net / gross revenue retention |
| GL | General ledger — the system of record for accounting entries |
| Close | The monthly/quarterly process of finalizing financial statements |
| MD&A | Management Discussion & Analysis — narrative accompanying financial statements, common in board reporting |
| Evidence / lineage | The ability to trace a reported number back to its exact source records |
| Confidence | An explicit signal of how trustworthy a given number or explanation is — never collapsed into false certainty |

## 8. What's needed from the human side before creative work starts

- **Brand assets:** logo, color palette, and fonts (if none exist yet, note that explicitly — don't let an agent invent brand identity unprompted)
- **Confirmation of the current differentiator angle** (§4) as the one to lead with, or a correction if leadership wants a different wedge
- **Any real customer proof points** (a real number, a real quote) that can replace the illustrative example in §4 with something even more credible
