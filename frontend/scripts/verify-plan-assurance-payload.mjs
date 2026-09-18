/**
 * Plan Assurance integrity guards (static source checks).
 * Fails prebuild/demo if Budget Analytics adapters regress into inventable LLM payloads.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const budgetHtml = path.join(root, "public", "budget-engine", "index.html");

const src = fs.readFileSync(budgetHtml, "utf8");
const failures = [];

function ok(name, cond, detail = "") {
  if (cond) {
    console.log(`OK  ${name}`);
  } else {
    console.log(`FAIL  ${name}${detail ? `: ${detail}` : ""}`);
    failures.push(name);
  }
}

ok(
  "Status SoT narrative includes ARR bridge churn/expansion/contraction",
  /function buildDeterministicAssuranceNarrative[\s\S]*?churn \$\{fmtM\(p\.fyChurn/.test(src) &&
    /expansion \$\{fmtM\(p\.fyExp/.test(src) &&
    /contraction \$\{fmtM\(p\.fyCont/.test(src),
);

ok(
  "Assurance packet carries fyNb/fyExp/fyCont/fyChurn",
  /fyNb,\s*\n\s*fyExp,\s*\n\s*fyReact,\s*\n\s*fyCont,\s*\n\s*fyChurn/.test(src) ||
    (/fyNb:/.test(src) && /fyExp:/.test(src) && /fyCont:/.test(src) && /fyChurn:/.test(src)),
);

ok(
  "Status Generate never maps ending cash to forecasted_collections",
  !/forecasted_collections:\s*p\.endCash/.test(src),
);

ok(
  "History adapter does not label prior year as actual vs plan as forecast",
  !/actuals_vs_forecast:\s*\[/.test(src),
);

ok(
  "History SoT forbids actual-vs-forecast framing",
  /not actual vs forecast/.test(src),
);

ok(
  "Constrained polish helpers exist",
  /function resolveAssuranceGenerate/.test(src) &&
    /function assuranceClaimsVerified/.test(src) &&
    /function polishAssuranceNarrative/.test(src) &&
    /POLISH ONLY/.test(src),
);

ok(
  "Status/History Generate use resolveAssuranceGenerate",
  /refreshAssuranceNarrative[\s\S]*?resolveAssuranceGenerate/.test(src) &&
    /refreshAssuranceHistory[\s\S]*?resolveAssuranceGenerate/.test(src),
);

ok(
  "Predictive Generate polishes buildScenarioNarrativeFromSuite via resolveAssuranceGenerate",
  /buildScenarioNarrativeFromSuite\(suite\)[\s\S]*?resolveAssuranceGenerate/.test(src),
);

ok(
  "Structural ban on inventing zero churn when packet has churn",
  /zero\\s\+churn/.test(src) || /zero\s\+churn/.test(src) || /fyChurn \|\| 0\) > 1 && \/zero/.test(src),
);

if (failures.length) {
  console.log(`\n${failures.length} plan-assurance check(s) failed.`);
  process.exit(1);
}

console.log(`\nAll plan-assurance integrity checks passed (${[
  "SoT bridge",
  "packet fields",
  "no cash-as-collections",
  "history labels",
  "history SoT",
  "polish helpers",
  "status/history wire",
  "predictive wire",
  "zero-churn ban",
].length}).`);
