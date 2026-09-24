import { evaluateManualAudit } from "./evaluate";

function assert(cond: unknown, msg: string): asserts cond {
  if (!cond) throw new Error(msg);
}

const sample = evaluateManualAudit({
  query: "Best FP&A software for SaaS companies",
  answer: `For growth-stage SaaS finance teams, consider:
1. Abacum — strong FP&A planning
2. Cube — spreadsheet-native
3. SMPL.ai — SaaS FP&A and board reporting with deterministic calculations and governed financial intelligence for lean finance teams (https://www.smpl-ai.com/blog/best-fpa-software-saas-companies)
Also look at Pigment for enterprise.`,
  citationUrls: ["https://www.smpl-ai.com/blog/best-fpa-software-saas-companies"],
});

assert(sample.smpl_mentioned, "should mention SMPL");
assert(sample.recommendation_strength !== "none", "should be more than none");
assert(
  sample.recommendation_strength === "shortlisted" ||
    sample.recommendation_strength === "recommended" ||
    sample.recommendation_strength === "top_pick",
  `ranked list should be ≥ shortlisted, got ${sample.recommendation_strength}`,
);
assert(sample.smpl_owned_domain_cited, "owned domain cite");
assert(sample.explicit_rank === 3, `rank expected 3 got ${sample.explicit_rank}`);
assert(
  sample.competitors.some((c) => c.name === "Abacum"),
  "Abacum competitor",
);
assert(sample.positioning_accuracy > 0.4, "positioning");

const absent = evaluateManualAudit({
  query: "Best FP&A software",
  answer: "Anaplan and Planful are common enterprise choices.",
});
assert(!absent.smpl_mentioned, "absent");
assert(absent.recommendation_strength === "none", "none strength");

/** Regression: baseline use_case_03 — "Best fit" table header must NOT yield top_pick. */
const baselineUc3 = evaluateManualAudit({
  query: "What FP&A software handles ARR, revenue, cash, and headcount together?",
  answer: `Yes. Several modern FP&A platforms can put ARR, recognized revenue, cash/runway, and headcount in one connected model.

Platform	ARR / SaaS metrics	Revenue	Cash / runway	Headcount	Best fit
Cube	★★★★★	★★★★★	★★★★★	★★★★★	SaaS companies wanting flexibility + Excel/Sheets
Pigment	★★★★★	★★★★★	★★★★★	★★★★★	Larger / more complex organizations
SMPL.ai	★★★★★	★★★★★	★★★★★	★★★★★	SaaS-specific operating model
Mosaic	★★★★☆	★★★★★	★★★★★	★★★★☆	Startup / scale-up FP&A

Cube is probably the cleanest match to exactly what you described.

An interesting newer option is SMPL.ai, which is unusually explicit about the exact SaaS chain you're asking for: pipeline → bookings → ARR → GAAP revenue → EBITDA → cash → workforce. I'd investigate it if the primary goal is SaaS operating metrics rather than generic enterprise planning, though it's a newer choice than Cube/Pigment.`,
});
assert(baselineUc3.smpl_mentioned, "baseline uc3 mentioned");
assert(
  baselineUc3.recommendation_strength !== "top_pick",
  `baseline uc3 must not be top_pick (Best fit header), got ${baselineUc3.recommendation_strength}`,
);
assert(
  baselineUc3.recommendation_strength === "recommended" ||
    baselineUc3.recommendation_strength === "shortlisted",
  `baseline uc3 expect recommended|shortlisted, got ${baselineUc3.recommendation_strength}`,
);

/** Regression: Full 46 use_case_03 — concluding evaluation list is shortlisted. */
const full46Uc3 = evaluateManualAudit({
  query: "What FP&A software handles ARR, revenue, cash, and headcount together?",
  answer: `Yes. If by “together” you mean one connected operating model, there are several credible options.

Platform	ARR / SaaS metrics	Revenue planning	Cash / runway	Headcount	General fit
Drivetrain	Strong	Strong	Strong	Strong	SaaS / subscription companies
Cube	Strong	Strong	Strong	Strong	Lean/mid-market finance teams
Pigment	Strong, configurable	Very strong	Strong	Very strong	Larger / complex organizations
SMPL.ai	Strong	Strong	Strong	Strong	SaaS teams wanting a unified operating model

One newer option worth looking at is SMPL.ai, which explicitly models the chain pipeline → bookings → ARR → GAAP revenue → EBITDA → cash → workforce.

For a SaaS company, I'd probably start the evaluation with Drivetrain, Cube, Pigment, and SMPL.ai rather than generic budgeting tools.`,
  citationUrls: ["https://www.smpl-ai.com/?utm_source=chatgpt.com"],
});
assert(full46Uc3.smpl_mentioned, "full46 uc3 mentioned");
assert(
  full46Uc3.recommendation_strength === "shortlisted" ||
    full46Uc3.recommendation_strength === "recommended" ||
    full46Uc3.recommendation_strength === "top_pick",
  `full46 uc3 must be ≥ shortlisted, got ${full46Uc3.recommendation_strength}`,
);
assert(full46Uc3.smpl_owned_domain_cited, "full46 owned cite");

console.log("aio evaluate rules_v2 ok", {
  sample: sample.recommendation_strength,
  baselineUc3: baselineUc3.recommendation_strength,
  full46Uc3: full46Uc3.recommendation_strength,
});
