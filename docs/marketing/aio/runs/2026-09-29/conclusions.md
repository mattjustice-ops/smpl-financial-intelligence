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
