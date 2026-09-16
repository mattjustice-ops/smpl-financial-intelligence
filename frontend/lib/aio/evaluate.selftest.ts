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

console.log("aio evaluate rules_v1 ok");
