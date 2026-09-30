import {
  domainSummary,
  findBrandMentions,
  isSmplUrl,
  legacyCitationStatus,
  normalizeSourceUrl,
  scoreVisibility,
  stripCitationLabelsHeuristic,
  vendorsMentioned,
} from "./visibility-score";

let failures = 0;
function check(cond: unknown, msg: string) {
  if (!cond) {
    failures += 1;
    console.error(`FAIL: ${msg}`);
  }
}

/** Sep 29 category_06: SMPL.ai appears only as a citation pill supporting evaluation advice. */
const citationOnlyText = `Grove FP
Driver-based forecasting. You should be able to forecast from operational drivers rather than simply applying percentages to last year's P&L. 
Anaplan Support
A genuinely connected model. A good test is: increase churn, delay 10 hires, and reduce new bookings by 15%—now show me ARR, recognized revenue, EBITDA, cash, and runway. Those changes should propagate through one model without exporting data between modules. 
SMPL.ai
Strong headcount planning. For most SaaS businesses this is critical. 
CFO Shortlist
+1`;
{
  const s = scoreVisibility({
    answerText: citationOnlyText,
    sources: [{ url: "https://www.smpl-ai.com/fpa-software-for-saas?utm_source=chatgpt.com" }],
    citationStatus: "partial",
  });
  check(!s.proseMention, "citation-only: pill label must not count as prose mention");
  check(s.recommendation === "none", `citation-only: no recommendation, got ${s.recommendation}`);
  check(s.smplCitation === "yes" && s.smplCitationUrlVerified, "citation-only: SMPL source citation with URL");
}

/** Same appearance captured structurally (capture v2). */
{
  const s = scoreVisibility({
    answerText: citationOnlyText,
    proseText: citationOnlyText.replace(/\nSMPL\.ai\n/, "\n").replace(/\n(Grove FP|Anaplan Support|CFO Shortlist|\+1)(?=\n|$)/g, ""),
    citationLabels: ["Grove FP", "Anaplan Support", "SMPL.ai", "CFO Shortlist"],
    sources: [{ url: "https://www.smpl-ai.com/fpa-software-for-saas", publisher: "SMPL.ai" }],
    citationStatus: "complete",
  });
  check(!s.proseMention && s.smplCitation === "yes", "structural citation-only");
  check(s.smplCitationVisibility === "visible", `visible pill → visible, got ${s.smplCitationVisibility}`);
}

/** Sep 29 rerun lean_finance_05: SMPL only among sources hidden behind "+N". */
{
  const s = scoreVisibility({
    answerText: "Plan the rollout in phases.",
    proseText: "Plan the rollout in phases.",
    citationLabels: ["Pigment"],
    sources: [
      { url: "https://pigment.com/x?utm_source=chatgpt.com", publisher: "Pigment" },
      { url: "https://www.smpl-ai.com/blog/fpa-software-implementation?utm_source=chatgpt.com", publisher: "SMPL.ai", hidden: true },
    ],
    citationStatus: "complete",
  });
  check(s.smplCitation === "yes" && s.smplCitationVisibility === "hidden_only", `hidden-only, got ${s.smplCitationVisibility}`);
  check(!s.proseMention && !s.vendorRecommended, "hidden-only citation is not a mention or recommendation");
  const legacy = scoreVisibility({ answerText: citationOnlyText, sources: [], citationStatus: "partial" });
  check(legacy.smplCitationVisibility === "unknown", `legacy capture → visibility unknown, got ${legacy.smplCitationVisibility}`);
  const none = scoreVisibility({ answerText: "Cube.", proseText: "Cube.", citationStatus: "none_shown" });
  check(none.smplCitationVisibility === "none", "no citation → none");
}

/** Sep 15 use_case_03: table row + "newer option ... I'd investigate it" + pill label, no URLs collected. */
const recommendText = `Platform\tARR / SaaS metrics\tRevenue\tCash / runway\tHeadcount\tBest fit
Cube\t★★★★★\t★★★★★\t★★★★★\t★★★★★\tSaaS companies wanting flexibility + Excel/Sheets
SMPL.ai\t★★★★★\t★★★★★\t★★★★★\t★★★★★\tSaaS-specific operating model

Pigment is the stronger candidate if your modeling is more sophisticated. The downside is that it's generally a heavier platform. 
Pigment
+2
Pigment
+2

An interesting newer option is SMPL.ai, which is unusually explicit about the exact SaaS chain you're asking for: pipeline → bookings → ARR → GAAP revenue → EBITDA → cash → workforce. It connects CRM, ERP, billing, HRIS, spreadsheets and warehouse data into that operating model. I'd investigate it if the primary goal is SaaS operating metrics rather than generic enterprise planning, though it's a newer choice than Cube/Pigment. 
SMPL.ai

For a smaller Series A/B company, Mosaic or Runway are also worth considering. 
CFO Advisors`;
{
  const status = legacyCitationStatus(recommendText, []);
  check(status === "labels_only", `labels-only status expected, got ${status}`);
  const s = scoreVisibility({ answerText: recommendText, sources: [], citationStatus: status });
  check(s.proseMention, "recommendation: prose mention");
  check(s.recommendation === "recommended", `recommendation: expected recommended, got ${s.recommendation}`);
  check(s.smplCitation === "yes" && !s.smplCitationUrlVerified, "recommendation: label evidences a citation but URL is unverified");
  const stripped = stripCitationLabelsHeuristic(recommendText);
  check(!/\nPigment\n/.test(stripped.prose), "consecutive pills are stripped");
  check(stripped.hiddenMarkers === 4, `hidden markers expected 4, got ${stripped.hiddenMarkers}`);
}

/** Shortlist phrasing (Sep 23 use_case_03). */
{
  const s = scoreVisibility({
    answerText:
      "For a SaaS company, I'd probably start the evaluation with Drivetrain, Cube, Pigment, and SMPL.ai rather than generic budgeting tools.",
    sources: [{ url: "https://www.smpl-ai.com/?utm_source=chatgpt.com" }],
    citationStatus: "complete",
  });
  check(s.recommendation === "shortlisted", `shortlist expected, got ${s.recommendation}`);
}

/** Sep 29 rerun use_case_03 phrasings. */
{
  const focus = scoreVisibility({
    answerText:
      "One newer option worth knowing about is SMPL.ai.\n\nIf your real requirement is live ARR-to-cash scenarios, I'd focus the evaluation on Abacum, Runway, Pigment, Cube, and SMPL.ai, rather than generic budgeting tools.",
    citationStatus: "complete",
  });
  check(focus.recommendation === "shortlisted", `focus-the-evaluation expected shortlisted, got ${focus.recommendation}`);
  const match = scoreVisibility({
    answerText:
      "A particularly direct match is SMPL.ai: it explicitly positions its model around pipeline, ARR, revenue, cash, headcount, and financial statements together.",
    citationStatus: "complete",
  });
  check(match.recommendation === "recommended", `direct match expected recommended, got ${match.recommendation}`);
}

/** Brand variants. */
for (const v of ["SMPL.ai", "SMPL AI", "smpl-ai.com", "www.smpl-ai.com", "SMPL-AI"]) {
  check(findBrandMentions(`One option is ${v} for SaaS teams.`).length === 1, `variant ${v} detected`);
}
check(isSmplUrl("https://smpl-ai.com/pricing"), "apex domain");
check(isSmplUrl("https://www.smpl-ai.com/blog/x?utm_source=chatgpt.com"), "www domain");

/** Unrelated matches. */
check(findBrandMentions("The SMPL body model is used in 3D human pose estimation.").length === 0, "bare SMPL alone is ignored");
check(findBrandMentions("SMPL-X extends the SMPL model with hands.").length === 0, "SMPL-X ignored");
check(findBrandMentions("Simple planning tools like Simpl help.").length === 0, "Simpl ignored");
check(!isSmplUrl("https://notsmpl-ai.com/x"), "lookalike domain rejected");
check(!isSmplUrl("https://smpl-ai.com.evil.example/x"), "suffix-spoof domain rejected");
check(!isSmplUrl("https://www.smplfinance.com/"), "different domain rejected");
check(
  findBrandMentions("SMPL.ai models ARR. SMPL also handles cash.").length === 2,
  "bare SMPL counts when a strong variant is present",
);

/** Attribution without recommendation. */
{
  const s = scoreVisibility({
    answerText: "According to SMPL.ai, the board pack should tie ARR to GAAP revenue before commentary is written.",
    sources: [],
    citationStatus: "none_shown",
  });
  check(s.proseMention && s.recommendation === "none", `attribution: prose mention only, got ${s.recommendation}`);
  const t = scoreVisibility({
    answerText: "SMPL.ai recommends reconciling billing ARR to CRM ARR monthly.",
    sources: [],
    citationStatus: "none_shown",
  });
  check(t.recommendation === "none", `"SMPL.ai recommends X" is not a recommendation of SMPL, got ${t.recommendation}`);
}

/** Missing metadata must not read as zero. */
{
  const s = scoreVisibility({ answerText: "Cube and Pigment are common choices.", sources: [], citationStatus: "not_collected" });
  check(s.smplCitation === "unknown", `not collected → unknown, got ${s.smplCitation}`);
  const p = scoreVisibility({
    answerText: "Cube is common. \nCube\n+2",
    sources: [{ url: "https://www.cubesoftware.com/" }],
    citationStatus: legacyCitationStatus("Cube is common. \nCube\n+2", ["https://www.cubesoftware.com/"]),
  });
  check(p.citationStatus === "partial" && p.smplCitation === "not_in_visible_sources", "hidden +N sources → not_in_visible_sources");
  const c = scoreVisibility({ answerText: "Cube is common.", sources: [{ url: "https://www.cubesoftware.com/" }], citationStatus: "complete" });
  check(c.smplCitation === "no", "complete capture without SMPL → no");
}

/** Interface links (utm_source=chatgpt.com) are sources; chatgpt.com links are not. */
{
  const rows = domainSummary([
    {
      sources: [
        { url: "https://www.getaleph.com/blog/a?utm_source=chatgpt.com" },
        { url: "https://www.getaleph.com/blog/a" },
        { url: "https://www.getaleph.com/blog/b?utm_source=chatgpt.com" },
        { url: "https://chatgpt.com/c/123" },
      ],
    },
    { sources: [{ url: "https://pigment.com/x?utm_source=chatgpt.com" }] },
  ]);
  const aleph = rows.find((r) => r.domain === "getaleph.com");
  check(aleph?.answers === 1 && aleph?.sources === 2, "domain summary dedupes pages and counts answers");
  check(!rows.some((r) => r.domain === "chatgpt.com"), "interface links excluded");
  check(
    normalizeSourceUrl("https://www.smpl-ai.com/fpa-software-for-saas?utm_source=chatgpt.com") ===
      "https://www.smpl-ai.com/fpa-software-for-saas",
    "utm stripped",
  );
}

// Vendor extraction ignores FP&A vocabulary that shares a vendor's name.
{
  const v = vendorsMentioned("Extend cash runway with a data cube. Compare Cube, Runway, and OneStream; Cube again.");
  check(JSON.stringify(v) === JSON.stringify(["Cube", "OneStream", "Runway"]), `vendorsMentioned: ${v}`);
}

if (failures) {
  console.error(`${failures} visibility-score check(s) failed`);
  process.exit(1);
}
console.log("visibility-score checks ok");
