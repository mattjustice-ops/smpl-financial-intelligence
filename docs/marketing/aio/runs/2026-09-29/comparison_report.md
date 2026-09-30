# SMPL.ai ChatGPT AIO benchmark — Sep 29, 2026 audit and controlled rerun

Generated 2026-09-29T21:34:17.140Z · scorer `visibility_v1` · rerun capture `rerun_capture_v2.jsonl`

Three outcomes are scored separately:
- **Prose mention**: SMPL.ai named in the answer's own text (citation-pill labels excluded).
- **Vendor recommendation**: SMPL.ai presented as a product (listed < shortlisted < recommended < top pick).
- **Source citation**: a SMPL.ai page is shown as a source. `unknown` / `not_in_visible_sources` mean the capture could not show every source, not that SMPL was absent.

## 1. Rerun conditions

- Interface: chatgpt.com web app (Cursor embedded browser, signed-in account)
- Model selector label: Instant (63), not rendered at send time (3); the underlying model version is not exposed by the UI
- Search: web search selected on every prompt: yes
- Session: temporary chat on every prompt: yes; personalization: Unpersonalized; "ignores memory, plugins, and custom instructions" notice shown: yes
- Independent conversations: 66 distinct conversation URLs for 66 answered prompts
- Prompts sent verbatim: yes (composer text matched the benchmark text before every send)
- Time window: 2026-09-29T20:59:35.336Z → 2026-09-29T21:27:49.151Z (UTC); viewport 672x484
- Captures with errors: none

## 2. Historical results: original vs corrected

| Run | Original: mentioned | Original: cited | Corrected: prose mention | Corrected: recommendation | Corrected: SMPL citation (URL verified) | Citation capture status |
|---|---|---|---|---|---|---|
| Sep 15 baseline | 1 | 0 | 1 | 1 (use_case_03:recommended) | 1 (0) | not_collected 1, labels_only 45 |
| Sep 23 full 46 | 1 | 1 | 1 | 1 (use_case_03:shortlisted) | 1 (1) | labels_only 9, partial 37 |
| Sep 29 initial run | 1 | 1 | 0 | 0 (none) | 1 (1) | partial 44, complete 1, labels_only 1 |

Changes from the original reports:
- Sep 15 baseline · use_case_03: originally mentioned=true, cited=false → prose mention true, recommendation recommended, citation yes (label only; URL never captured).
- Sep 23 full 46: no change to mention/citation counts.
- Sep 29 initial run · category_06: originally mentioned=true, cited=true → prose mention false, recommendation none, citation yes.

## 3. Sep 29: initial run vs controlled rerun (46 prompts)

| | Prose mentions | Recommendations | SMPL citations | Citation status |
|---|---|---|---|---|
| Initial run (corrected) | 0 | 0 | 1 | partial 44, complete 1, labels_only 1 |
| Controlled rerun | 1 | 1 | 3 | complete 46 |

By query class (rerun / initial):

| Class | Queries | Prose mentions | Recommendations | SMPL citations |
|---|---|---|---|---|
| Informational | 12 | 0 / 0 | 0 / 0 | 2 / 1 |
| Vendor selection | 34 | 1 / 0 | 1 / 0 | 1 / 0 |

## 4. Query-level SMPL appearances across runs

Every query where SMPL.ai appeared in any run, by any of the three outcomes. All other queries: no appearance in any run.

| Query | Class | Sep 15 baseline | Sep 23 full 46 | Sep 29 initial run | Rerun (trial 1) | Priority trial 2 | Priority trial 3 |
|---|---|---|---|---|---|---|---|
| authority_05 | informational | prose — · rec none · cite not_in_visible_sources | prose — · rec none · cite not_in_visible_sources | prose — · rec none · cite not_in_visible_sources | prose — · rec none · cite yes | — | — |
| category_06 | informational | prose — · rec none · cite not_in_visible_sources | prose — · rec none · cite not_in_visible_sources | prose — · rec none · cite yes | prose — · rec none · cite no | prose — · rec none · cite yes | prose — · rec none · cite yes |
| lean_finance_05 | informational | prose — · rec none · cite not_in_visible_sources | prose — · rec none · cite not_in_visible_sources | prose — · rec none · cite not_in_visible_sources | prose — · rec none · cite yes | — | — |
| use_case_03 | vendor_selection | prose yes · rec recommended · cite yes | prose yes · rec shortlisted · cite yes | prose — · rec none · cite not_in_visible_sources | prose yes · rec shortlisted · cite yes | prose yes · rec recommended · cite yes | prose — · rec none · cite no |

Initial → rerun, same day: gained lean_finance_05, use_case_03, authority_05; lost category_06.

## 5. Priority queries: appearance frequency across 3 trials

Priority set fixed in `benchmark_design.json` before any rerun result was seen. Trial 1 is the query's response inside the controlled 46-prompt rerun; trials 2–3 are repeats under identical conditions. The earlier Sep 29 run used a different capture method and is shown separately, not counted as a trial.

| Query | Class | Prose mention (of 3) | Recommended (of 3) | SMPL cited (of 3) | Cited-domain overlap across trials | Vendor-list overlap across trials | Sep 29 initial (not a trial) |
|---|---|---|---|---|---|---|---|
| category_06 | informational | 0/3 | 0/3 | 2/3 | 0% | 0% | prose — · rec none · cite yes |
| use_case_03 | vendor_selection | 2/3 | 2/3 | 2/3 | 43% | 57% | prose — · rec none · cite not_in_visible_sources |
| lean_finance_03 | vendor_selection | 0/3 | 0/3 | 0/3 | 17% | 38% | prose — · rec none · cite not_in_visible_sources |
| competitive_05 | vendor_selection | 0/3 | 0/3 | 0/3 | 8% | 45% | prose — · rec none · cite not_in_visible_sources |
| use_case_01 | vendor_selection | 0/3 | 0/3 | 0/3 | 10% | 57% | prose — · rec none · cite not_in_visible_sources |
| use_case_02 | vendor_selection | 0/3 | 0/3 | 0/3 | 9% | 57% | prose — · rec none · cite not_in_visible_sources |
| use_case_07 | vendor_selection | 0/3 | 0/3 | 0/3 | 8% | 86% | prose — · rec none · cite not_in_visible_sources |
| use_case_05 | vendor_selection | 0/3 | 0/3 | 0/3 | 20% | 57% | prose — · rec none · cite not_in_visible_sources |
| use_case_08 | vendor_selection | 0/3 | 0/3 | 0/3 | 14% | 0% | prose — · rec none · cite not_in_visible_sources |
| systems_04 | vendor_selection | 0/3 | 0/3 | 0/3 | 10% | 33% | prose — · rec none · cite not_in_visible_sources |

Overlap = items present in all trials ÷ items present in any trial (Jaccard). Low overlap means the same prompt produced materially different sources or vendor lists within hours.

## 6. Citation capture completeness and comparability

- Rerun: 66 answers, 582 source entries, of which 239 (41%) were hidden behind "+N" pills. Earlier captures never collected those, so their citation results are lower bounds.
- Like-for-like with earlier runs (visible sources only, as their capture saw them): 1 of 3 rerun SMPL citations would have been detected; the rest appeared only behind "+N" pills.
- Rerun citation status: complete 66.
- Historical label-strip heuristic vs structural capture on the same rerun answers: prose-mention agreement 66/66; recommendation-level agreement 66/66; pill-label count exact match 66/66.
- Model version was not recorded for Sep 15, Sep 23, or the Sep 29 initial run; the rerun records only the UI selector label. Sep 15 citation URLs were never collected; Sep 23's first 9 queries have no URLs.

## 7. Cited domains (controlled rerun, 46 prompts)

Reconciliation: the domain table is built from the same per-answer source lists printed in the export. Sum of per-answer distinct domains = 203; sum of the table's "answers" column = 203 → reconciled.

| Domain | Answers citing | Distinct pages |
|---|---|---|
| getaleph.com | 19 | 52 |
| pigment.com | 16 | 27 |
| cubesoftware.com | 16 | 27 |
| cfoshortlist.com | 12 | 12 |
| datarails.com | 9 | 14 |
| drivetrain.ai | 8 | 14 |
| abacum.ai | 7 | 16 |
| metapraxis.com | 6 | 6 |
| workday.com | 5 | 10 |
| anaplan.com | 5 | 8 |
| planful.com | 4 | 11 |
| maxio.com | 4 | 10 |
| kb.pigment.com | 4 | 7 |
| get.runway.com | 4 | 4 |
| smpl-ai.com | 3 | 3 |
| stripe.com | 2 | 7 |
| g2.com | 2 | 5 |
| venasolutions.com | 2 | 3 |
| gartner.com | 2 | 3 |
| getfairview.com | 2 | 2 |

### Most-cited competitor URLs (all 66 rerun answers)

| Vendor | URL | Answers citing | Title |
|---|---|---|---|
| Aleph | https://www.getaleph.com/answers/best-fpa-software-saas-companies | 10 | Best FP&A software for SaaS companies (2026) / Aleph |
| Pigment | https://www.pigment.com/use-case/revenue-planning | 9 | AI-driven Revenue Planning in Pigment |
| Pigment | https://www.pigment.com/blog/best-fpa-software | 9 | Best FP&A Software in 2026: Compare the Top 8 Planning Tools |
| Abacum | https://www.abacum.ai/ | 8 | Abacum: The AI-Native FP&A Platform |
| Cube | https://www.cubesoftware.com/integrations | 6 | Seamlessly Integrate with any ERP or Source System / Cube FP&A Software |
| Aleph | https://www.getaleph.com/answers/mosaic-alternatives-fpa-software | 6 | Best Mosaic FP&A Alternatives After the HiBob Acquisition (2026) / Aleph |
| Pigment | https://www.pigment.com/integrations | 6 | Unified Business Planning with Data Integrations / Pigment |
| Aleph | https://www.getaleph.com/answers/top-fpa-software-2026 | 5 | 12 Best FP&A Software Tools (Q3 2026): Compared by Tier & AI / Aleph |
| Drivetrain | https://www.drivetrain.ai/solutions/saas-financial-planning-software | 5 | Purpose-built Financial Planning Software for SaaS businesses - Drivetrain |
| Runway | https://get.runway.com/ | 5 | Runway – Simulate every business decision in seconds |
| Cube | https://www.cubesoftware.com/cube-for-fpa | 5 | Master Financial Intelligence / AI-Powered FP&A / Cube |
| Abacum | https://www.abacum.ai/industry/software-and-technology | 5 | AI-Native FP&A Software for Software and SaaS / Abacum |
| Workday Adaptive Planning | https://www.workday.com/en-us/products/adaptive-planning/financial-planning/analytics-reporting.html | 5 | Financial Reporting and FP&A Dashboard Software / Workday US |
| Pigment | https://www.pigment.com/platform | 4 | AI-Native Integrated Business Planning / Pigment |
| Pigment | https://www.pigment.com/use-case/finance | 4 | Financial Planning & Analysis (FP&A) Software for Entreprise / Pigment |

Vendors named in prose across the 46 rerun answers: Pigment 30, Cube 29, Anaplan 21, Abacum 19, Aleph 19, Workday 18, Datarails 18, Drivetrain 15, Planful 14, Vena 14, Runway 13, Mosaic 9, OneStream 2, Fathom 1, Jirav 1; SMPL.ai 1.

## 8. Conclusions

### What the evidence supports

- **The earlier "1 of 46 on both dates" hid three different outcomes.** Corrected: Sep 15 and Sep 23 each had one prose mention + vendor recommendation (use_case_03: recommended, then shortlisted). The Sep 29 initial run had zero prose mentions and zero recommendations; its only appearance was a citation of `/fpa-software-for-saas` in category_06. The old scorer counted that citation label as a mention.
- **Sep 15 had a SMPL.ai citation that was reported as 0.** The use_case_03 answer carried a SMPL.ai citation pill; the URL was never captured, so it is counted as a citation with an unverified URL.
- **SMPL.ai content is being used as a source more often than it is named.** Controlled rerun: SMPL pages were cited in 3 of 46 answers (use_case_03, lean_finance_05, authority_05) and in 2 of 3 category_06 trials, but SMPL.ai was named in prose in only one query (use_case_03). In informational queries SMPL is cited as background and never named.
- **Vendor-selection visibility is concentrated in a single query.** 33 of 34 vendor-selection prompts never named SMPL.ai in any run. use_case_03 ("ARR, revenue, cash, and headcount together") named and shortlisted/recommended SMPL.ai in 2 of 3 same-day trials, and in both earlier runs.
- **Same-day results are variable, not stable.** Across the 3 trials of each priority query, only 0–43% of cited domains recurred in all trials (most 8–20%), and vendor lists overlapped 0–86%. The Sep 29 initial run's "loss" of use_case_03 falls inside this same-day variance: the rerun recovered it 2 times out of 3. One run per date cannot distinguish a real change from sampling noise.
- **Earlier citation counts are lower bounds.** 41% of all rerun sources were hidden behind "+N" pills, and 2 of the 3 rerun SMPL citations were hidden-only. The Sep 23 and Sep 29 initial capture methods could not have seen them.
- **The historical rescoring method is validated.** On all 66 rerun answers, the label-strip heuristic applied to the old innerText format matched the structural capture on prose mention, recommendation level, and pill-label count (66/66 each).
- **Competitor sources dominate.** getaleph.com was cited in 19 of 46 answers (52 distinct pages, mostly `/answers/...` comparison pages); pigment.com and cubesoftware.com each appeared in 16, and cfoshortlist.com in 12. smpl-ai.com appeared in 3.

### What remains uncertain

- The underlying model version: the UI shows only "Instant", and no model was recorded for Sep 15, Sep 23, or the Sep 29 initial run. Model changes between dates cannot be ruled out.
- Whether today's variability is typical: 3 trials per priority query shows variance exists but cannot estimate a true appearance rate (2 of 3 is statistically compatible with a true rate anywhere from about 10% to 99%).
- Environment effects: one signed-in account, one browser (Cursor embedded, 672×484 viewport), one region, and a 30-minute window. Temporary chat and "Unpersonalized" were confirmed for every prompt, but account-level signals outside those settings are unknown.
- Sep 15 citation URLs and Sep 23's first 9 queries' URLs cannot be recovered; those rows are reported as `labels_only` / `unknown`, not as zero.
- Scorer tuning: two recommendation cues ("focus the evaluation on", "direct/close match") were added after reading the rerun answers. They are covered by regression checks and were applied to every run; historical results did not change.

### Three highest-priority actions

1. **Adopt this protocol as the baseline and stop comparing single runs.** Use capture v2 (structured citations, hidden sources, environment metadata) with the `visibility_v1` scorer. Report prose mention, recommendation, and citation separately, and measure the 10 priority queries at least 3 times per checkpoint. Judge change by appearance frequency, not by whether one run flipped.
2. **Diagnose the cited-but-not-named gap before changing content.** SMPL pages are already retrieved for informational and implementation questions, but the vendor lists ChatGPT builds come from sources like Aleph `/answers`, Pigment and Cube blog listicles, cfoshortlist.com, and G2. The rerun's source data (`rerun_scored_visibility_v1.json`) shows which pages feed which vendor lists. That is the evidence base for deciding between on-site and third-party distribution work.
3. **Protect and replicate the use_case_03 signal.** It is the only query where SMPL.ai is recommended, and ChatGPT's evidence there is SMPL's own connected ARR → revenue → cash → headcount positioning (homepage and `/fpa-software-for-saas`). Keep those pages stable while measuring, and test whether the adjacent connected-workflow queries (use_case_01/02/05/07, systems_04 — 0 of 3 each today) can be moved.
