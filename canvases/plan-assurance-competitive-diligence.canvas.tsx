import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useHostTheme,
} from "cursor/canvas";

type Verdict =
  | "SMPL ahead"
  | "SMPL somewhat ahead"
  | "roughly equivalent"
  | "SMPL somewhat behind"
  | "SMPL behind"
  | "unknown";

const MATRIX: { capability: string; smpl: string; peers: string; verdict: Verdict }[] = [
  {
    capability: "ML / AutoML time-series forecasting",
    smpl: "Absent (no PlanIQ/Prophet/AutoML layer)",
    peers: "Anaplan PlanIQ, Workday Predictive Forecaster, Pigment Predictions, OneStream SensibleAI, Planful AI Projections",
    verdict: "SMPL behind",
  },
  {
    capability: "Driver-based plan + scenario branches",
    smpl: "Budget formula graph + 11 named shocks",
    peers: "Cube / Abacum / Workday / Pigment / Drivetrain — mature scenario studios",
    verdict: "SMPL somewhat behind",
  },
  {
    capability: "Goal seek / backsolving",
    smpl: "Not shipped as product feature",
    peers: "Abacum Scenario Intelligence, Drivetrain Drive AI",
    verdict: "SMPL behind",
  },
  {
    capability: "Cash stress via named driver cases",
    smpl: "Yes (named cases + floor checks)",
    peers: "Cube cash runway / scenario stress (deterministic, not MC)",
    verdict: "roughly equivalent",
  },
  {
    capability: "Monte Carlo whole-plan path sim (annual levers → monthly CF)",
    smpl: "1,000 draws client-side; hardcoded independent priors; full Budget packet + cashByMonth path retained",
    peers:
      "Workday Decision Intelligence (2026) documents MC on selected assumptions/outcomes (e.g. Q4 revenue P10/P50/P90) — not proven full SaaS plan-path ensembles. Cube/Abacum/Pigment/Drivetrain: no native plan-path MC found",
    verdict: "SMPL somewhat ahead",
  },
  {
    capability: "Intra-year cash trough distribution",
    smpl: "Real in MC (minCash + P10–P90 trough across draws)",
    peers:
      "Cube: lowest-week cash under deterministic scenarios (strongest named trough). Workday DI: outcome bands, not documented cash-path trough ensembles",
    verdict: "SMPL somewhat ahead",
  },
  {
    capability: "Constraint / feasibility registry on plan packet",
    smpl: "15 typed constraints; JS live; Python API orphaned from UI",
    peers: "Validation rules common; packaged feasibility strip uncommon in marketing",
    verdict: "SMPL somewhat ahead",
  },
  {
    capability: "What Has to Be True artifact",
    smpl: "Backend generates must_close/confirm/hold; UI not consuming structured artifact",
    peers: "No close public analogue as named structured output",
    verdict: "SMPL somewhat ahead",
  },
  {
    capability: "Deterministic calc + LLM explain (no invent $)",
    smpl: "Yes (polish + claim-verify fail-closed)",
    peers: "Drivetrain explicit; Cube claims deterministic finance; Workday warns GenAI can err",
    verdict: "roughly equivalent",
  },
  {
    capability: "Calibrated Probability of Attainment",
    smpl: "Not built (docs forbid the label)",
    peers: "ML platforms have accuracy/backtest on series — still not plan PoA",
    verdict: "roughly equivalent",
  },
  {
    capability: "Governed enterprise modeling / multi-dim scale",
    smpl: "Budget Engine demo-capable; not enterprise CPM",
    peers: "Anaplan, Workday, Pigment, OneStream dominate",
    verdict: "SMPL behind",
  },
  {
    capability: "SaaS ARR–GTM–HC–cash closed graph out of box",
    smpl: "Opinionated shipped graph in Budget Engine",
    peers: "Configurable on all major platforms; rarely opinionated SaaS pack + feasibility",
    verdict: "SMPL somewhat ahead",
  },
];

const ANSWERS: { q: string; a: string }[] = [
  {
    q: "1. Unique today?",
    a: "Packaging — not monopoly tech. The unusual combo on one Budget Analytics surface is: SaaS formula graph + 15 feasibility checks + named stresses + 1k path MC with trough + LLM polish that must not invent $. Individually, peers have pieces. As one workflow aimed at “can we deliver this plan,” it is uncommon in public product stories. Implementation maturity is early (browser MC, dual JS/Python, assessments unpersisted).",
  },
  {
    q: "2. Looks unique but is common?",
    a: "Scenario planning, driver-based models, rolling forecasts from actuals, AI agents that draft plans, explainability language, “stress testing,” anomaly detection, governed assumptions. Using those words does not differentiate.",
  },
  {
    q: "3. Closest to Plan Assurance?",
    a: "Abacum (scenario intelligence + goal seek + downstream trade-offs) and Cube (driver stress through cash/runway on one model) for the planning-workflow intent. Workday Decision Intelligence is the closest public Monte Carlo peer — but as assumption/outcome sampling, not your SaaS path+trough pack. Neither Cube nor Abacum publicly ships WHTT + constraint-strip + plan-path MC together.",
  },
  {
    q: "4. Most advanced predictive analytics?",
    a: "Anaplan PlanIQ / Workday Predictive Forecaster / Pigment Predictions / OneStream SensibleAI — real AutoML, external drivers, accuracy measures. SMPL is not in that race.",
  },
  {
    q: "5. Most advanced scenario analysis?",
    a: "Workday Adaptive (personal/shareable what-ifs at scale), Pigment, Abacum Scenario Studio, Anaplan. SMPL’s 11 hardcoded cases + MC is narrower.",
  },
  {
    q: "6. Closest to det+predictive+LLM arch?",
    a: "Drivetrain: LLM writes logic, deterministic engine computes numbers — architecture cousins. Cube similar on “finance is deterministic.” SMPL’s edge is the feasibility/MC layer on top, not the LLM split.",
  },
  {
    q: "7. Anyone combines hist feasibility + constraints + WHTT + MC paths + intra-year cash?",
    a: "No public evidence of that full stack as one named product. Absence of evidence ≠ proof no one has internal tooling. Do not claim “no other platform.”",
  },
  {
    q: "8. Is MC more useful than Base/Bull/Bear?",
    a: "Yes for distributional questions (how often does trough breach under stated noise?). No for board storytelling (named cases remain clearer). Current MC is not more “true” than scenarios — priors are hand-tuned and independent, so it is randomized stress, not calibrated reality. Workday DI now also sells MC — so MC itself is no longer a category monopoly; the remaining edge is SaaS whole-plan path + trough packaging.",
  },
  {
    q: "9. vs Cube cash-runway stress?",
    a: "Different jobs. Cube: deterministic case stress with explicit lowest-week cash + fundraise timing (strongest peer trough claim). SMPL: stochastic lever noise through full Budget packet with path retention. Neither supersedes the other. Cube is more productized for cash FP&A; SMPL’s trough distribution across draws is the distinction — if priors stay honest.",
  },
  {
    q: "10. vs Abacum goal seek / sensitivity / trade-offs?",
    a: "Abacum is ahead on optimization-style planning (backsolve target → inputs). SMPL does not ship goal seek. SMPL’s MC answers “how fragile is this plan under noise,” which Abacum blogs mention conceptually but do not clearly productize as path MC.",
  },
  {
    q: "11. vs PlanIQ / Workday / Pigment / SensibleAI?",
    a: "Those predict metric series with ML. SMPL does not. Comparing SMPL MC to PlanIQ is category error — series prediction ≠ plan-path stress.",
  },
  {
    q: "12. Metrics vs connected company outcomes?",
    a: "Partly true. SMPL MC re-runs connected Budget packet (ARR/GTM/HC/IS/CF). Competitors’ ML often seeds accounts then scenarios propagate in their models too — so “connected” is not exclusive. The distinction that holds: SMPL’s live product emphasizes stress of the whole plan packet; ML platforms emphasize better baselines for individual series.",
  },
  {
    q: "13. Full monthly path per trial?",
    a: "Material for liquidity questions. Year-end-only stress can miss financing need. Code explicitly keeps cashByMonth for that reason. Differentiator only if buyers care about path risk — many CFOs do.",
  },
  {
    q: "14. Intra-year trough as differentiator?",
    a: "Yes as a product insight; modest as moat. Easy to add once you have monthly CF. Still under-emphasized in peer marketing vs ending cash/runway months.",
  },
  {
    q: "15. Constraints = feasibility or fancy validation?",
    a: "Closer to sophisticated business-rule validation on a plan packet today — typed floors/identities/coverage, not a mathematical feasibility solver or optimization. Still useful. Not a constraint-programming engine.",
  },
  {
    q: "16. WHTT intelligent enough?",
    a: "Mechanically derived from fail/warn/pass + stress break strings — honest and useful, not generative insight. Differentiated as UX/abstraction if surfaced; currently backend-complete, UI-partial.",
  },
  {
    q: "17. Hard for Cube/Abacum/Pigment/Drivetrain to copy?",
    a: "Weeks–months for a credible facsimile if they prioritize it — they already have models, scenarios, cash. Your head start is opinionated SaaS graph + shipped MC UX, not irreproducible science.",
  },
  {
    q: "18. Hardest to reproduce?",
    a: "Not the MC loop. Harder: trusted actuals→Budget SoT, claim-verified LLM discipline, and a SaaS-native opinionated methodology customers accept. Soft moat.",
  },
  {
    q: "19. Copiable in weeks?",
    a: "Named stress cases, cash floor checks, simple independent-lever MC, WHTT-style bullet list from failed checks.",
  },
  {
    q: "20. Defensible in 3–12 months?",
    a: "Persist assessments keyed to plan versions; server-side reproducible MC; history-fit priors + correlations; wire FE to /assess; board-citable Plan Assurance evidence; optional goal-seek; still never claim PoA without calibration.",
  },
  {
    q: "21. Work that most increases advantage?",
    a: "1) Single SoT thresholds (kill JS/Python dual). 2) Persist + cite assessments. 3) Replace hardcoded sigmas with company-history priors. 4) Server MC. 5) Close goal-seek gap or partner positioning against Abacum.",
  },
  {
    q: "22. FP&A practitioner reaction?",
    a: "Sophisticated practitioners: “scenario stress + Monte Carlo on a driver model” — not magic. The trough + feasibility strip can feel different if demoed honestly. Overclaim PoA and trust collapses.",
  },
  {
    q: "23. Would a CFO care?",
    a: "Yes for “show me mid-year cash risk and what must be true.” No for “we invented predictive analytics.” CFOs already buy scenarios from Adaptive/Anaplan.",
  },
  {
    q: "24. Technically sophisticated buyer?",
    a: "They will ask about priors, correlations, calibration, reproducibility, persistence. Today you fail several of those diligence questions. Architecture idea earns interest; implementation earns a “promising Phase 1.”",
  },
  {
    q: "25. Is “Plan Assurance” useful?",
    a: "Yes — better category name than predictive analytics for what the code does. It frames feasibility + stress of a plan, not ML forecasting. Keep it; don’t equate it to PoA.",
  },
];

function pillTone(v: Verdict): "success" | "warning" | "info" | "danger" | "neutral" {
  if (v === "SMPL ahead" || v === "SMPL somewhat ahead") return "success";
  if (v === "roughly equivalent") return "neutral";
  if (v === "SMPL somewhat behind") return "warning";
  if (v === "SMPL behind") return "danger";
  return "info";
}

export default function PlanAssuranceCompetitiveDiligence() {
  const theme = useHostTheme();

  return (
    <Stack gap={24} style={{ padding: 24, maxWidth: 1180 }}>
      <Stack gap={8}>
        <H1>Plan Assurance — competitive & technical diligence</H1>
        <Text tone="secondary" size="small">
          Skeptical architect review · Sep 18, 2026 · Code verified + public competitor docs
        </Text>
      </Stack>

      <Callout tone="warning" title="Bottom line (no founder sugar)">
        You are not years ahead on “predictive analytics.” Peers beat you badly on ML
        forecasting. Monte Carlo itself is no longer exclusive — Workday Decision
        Intelligence (2026) documents assumption/outcome MC. Your remaining edge is
        narrower: SaaS whole-plan path stress + cash-trough distributions + feasibility
        strip on one Budget graph. Real, early, copyable — not a moat. Kill press copy
        that leads with predictive AI parity or “only platform with Monte Carlo.”
      </Callout>

      <Grid columns={4} gap={12}>
        <Stat value="Feasibility + stress MC" label="What the code actually is" tone="info" />
        <Stat value="Not ML forecasting" label="vs PlanIQ / SensibleAI / Predictions" tone="danger" />
        <Stat value="Somewhat ahead" label="Path MC + trough + constraint strip" tone="success" />
        <Stat value="Early / dual SoT" label="Browser MC · /assess unused · no PoA" tone="warning" />
      </Grid>

      <Divider />

      <H2>1. Where SMPL stands today</H2>
      <Text size="small">
        Live Plan Assurance lives primarily in{" "}
        <Text as="span" weight="semibold">Budget Engine JS</Text> (formula graph, 15 risk
        checks, 11 named stresses, 1,000-draw MC). Backend{" "}
        <Text as="span" weight="semibold">predictive_planning/</Text> (constraints,
        feasibility, WHTT, POST /assess) is shipped but{" "}
        <Text as="span" weight="semibold">not called by the Budget UI</Text>; assessments
        return <Text as="span" weight="semibold">persisted: false</Text>. History review
        is display/reorder only — it does not fit MC priors. Priors are hardcoded
        independent sigmas (yoyPp 3.2, cplLog 0.28, attrPp 2.5, pipe 0.55). Docs correctly
        forbid calling breach rates Probability of Attainment.
      </Text>

      <Grid columns={2} gap={12}>
        <Card>
          <CardHeader title="SHIPPED (product path)" />
          <CardBody>
            <Stack gap={4}>
              <Text size="small">Deterministic Budget formula graph (ARR→GTM→HC→IS→CF)</Text>
              <Text size="small">15 feasibility checks (JS live)</Text>
              <Text size="small">Named stress cases + sensitivity curves</Text>
              <Text size="small">MC annual levers → monthly propagation; path + trough</Text>
              <Text size="small">LLM polish + claim-verify fail-closed to SoT</Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="PARTIAL / SCAFFOLD" />
          <CardBody>
            <Stack gap={4}>
              <Text size="small">Python registry + WHTT (API orphaned from UI)</Text>
              <Text size="small">Tenant/version constraint overlays (request-time only)</Text>
              <Text size="small">Assessment persistence / board citation</Text>
              <Text size="small">Calibrated PoA, correlations, history-fit priors</Text>
              <Text size="small">Server-side reproducible simulation</Text>
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <H2>2. Where you are genuinely ahead</H2>
      <Stack gap={8}>
        <Text size="small">
          <Text as="span" weight="semibold">Somewhat ahead (not “years”):</Text> packaging
          plan stress as connected-company outcomes with retained monthly cash paths and
          trough distributions under stated lever noise; opinionated SaaS graph +
          feasibility strip in one Analytics flow; honest docs naming discipline on PoA.
        </Text>
        <Text size="small" tone="secondary">
          Source: Budget Engine MC method{" "}
          <Text as="span" style={{ fontFamily: "monospace" }}>
            monte_carlo_annual_lever_shocks_monthly_propagation
          </Text>
          ; peer public docs emphasize ML series and/or deterministic scenario branches,
          not this MC path artifact.
        </Text>
      </Stack>

      <H2>3. Where competitors equal or exceed you</H2>
      <Stack gap={6}>
        <Text size="small">
          <Text as="span" weight="semibold">Materially behind:</Text> ML forecasting
          (Anaplan PlanIQ, Workday Predictive Forecaster, Pigment Predictions, OneStream
          SensibleAI, Planful). Goal seek/backsolving (Abacum, Drivetrain). Enterprise
          scenario studios and scale (Workday, Pigment, Anaplan).
        </Text>
        <Text size="small">
          <Text as="span" weight="semibold">Roughly equivalent:</Text> deterministic model
          + LLM explain without inventing dollars (Drivetrain explicit; Cube similar);
          driver scenario stress including cash (Cube runway stress).
        </Text>
      </Stack>

      <Divider />

      <H2>Capability matrix (strict)</H2>
      <Text size="small" tone="secondary">
        Unknown ≠ competitor lacks it. Awards require public evidence or code proof.
      </Text>
      <Table
        headers={["Capability", "SMPL (code)", "Peers (public)", "Verdict"]}
        rows={MATRIX.map((r) => [
          r.capability,
          r.smpl,
          r.peers,
          r.verdict,
        ])}
      />

      <H2>Competitor job map (do not conflate words)</H2>
      <Table
        headers={["Vendor", "Primary public job", "Not evidenced publicly"]}
        rows={[
          ["Cube", "Agentic reforecast + deterministic scenario/cash stress on governed model", "Native MC path distributions; WHTT; constraint registry product"],
          ["Abacum", "Scenario Studio + goal seek + sensitivity/trade-offs", "Plan-level MC path engine as core"],
          ["Pigment", "ML Predictions + large scenario simulation space", "SaaS-opinionated feasibility strip"],
          [
            "Workday Adaptive",
            "ML Predictive Forecaster + what-ifs + Planning Agent; Decision Intelligence adds assumption MC / CIs (2026)",
            "Documented full SaaS plan-path MC + cash-trough ensembles; WHTBT strip",
          ],
          [
            "Anaplan PlanIQ",
            "AutoML series forecasting + SHAP (MVLR) + quantile bands; Optimizer LP separate",
            "Plan Assurance workflow / path MC",
          ],
          [
            "Drivetrain",
            "Driver model + scenarios + backsolve; LLM never invents $; ARR Waterfall OOTB",
            "Public MC + constraint feasibility pack",
          ],
          ["OneStream / Planful", "Embedded AutoML forecast baselines + bounds", "SaaS Plan Assurance"],
          ["Datarails / Vena / Aleph", "Agents over Excel/governed sheets; scenarios & variance", "Comparable path MC"],
        ]}
      />

      <Divider />

      <H2>Right headline (terminology)</H2>
      <Callout tone="info" title="Do not lead with “predictive analytics”">
        Accurate labels for what the code does: Plan Assurance · probabilistic plan stress
        testing · operating-path simulation · execution-risk intelligence. Inaccurate:
        AutoML forecasting, calibrated Probability of Attainment, “AI predicts your ARR.”
      </Callout>

      <H2>Launch claims triage</H2>
      <Grid columns={3} gap={12}>
        <Card>
          <CardHeader
            title="Defensible now"
            trailing={
              <Pill tone="success" size="small">
                OK
              </Pill>
            }
          />
          <CardBody>
            <Stack gap={6}>
              <Text size="small">Go beyond building the budget to test whether it holds under operating noise</Text>
              <Text size="small">Shows what has to be true when feasibility checks fail (if you surface WHTT)</Text>
              <Text size="small">Evaluates path risk — year-end totals can hide mid-year cash troughs</Text>
              <Text size="small">Engines calculate; AI explains structured evidence</Text>
              <Text size="small">Stress frequency under stated priors (name the priors)</Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader
            title="Only with qualification"
            trailing={
              <Pill tone="warning" size="small">
                Careful
              </Pill>
            }
          />
          <CardBody>
            <Stack gap={6}>
              <Text size="small">“Plan Assurance” as a category abstraction — yes, if defined</Text>
              <Text size="small">“Thousands of operating outcomes” — say 1,000 draws, independent lever priors, browser-run</Text>
              <Text size="small">“Predictive intelligence in the financial model” — only if not read as ML forecasting</Text>
              <Text size="small">“First for SaaS Finance” — drop “first”; say “built for SaaS Finance plan stress”</Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader
            title="Do not claim"
            trailing={
              <Pill tone="danger" size="small">
                No
              </Pill>
            }
          />
          <CardBody>
            <Stack gap={6}>
              <Text size="small">Probability of Plan Attainment</Text>
              <Text size="small">No other FP&A platform does this</Text>
              <Text size="small">Years ahead of Cube/Abacum/Workday/Pigment</Text>
              <Text size="small">ML-grade predictive forecasting parity</Text>
              <Text size="small">Calibrated / historically fitted risk probabilities</Text>
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <Divider />

      <H2>4. What makes Plan Assurance harder to copy</H2>
      <Text size="small">
        Persist version-keyed assessments citable on board packs; one constraint SoT;
        server MC; company-specific prior fitting + correlations; keep LLM fail-closed;
        deepen SaaS methodology customers cannot casually re-model. Goal seek or explicit
        non-goal: otherwise Abacum owns “how do we hit $X.”
      </Text>

      <H2>5. Strongest accurate launch positioning</H2>
      <Callout tone="success" title="Positioning that survives diligence">
        SMPL Plan Assurance stress-tests a SaaS financial plan through the same
        deterministic model Finance already uses — feasibility constraints, named operating
        shocks, and Monte Carlo path analysis that surfaces mid-year cash risk under stated
        priors — then AI explains the evidence without inventing numbers. It is not AutoML
        forecasting. It is not Probability of Attainment. It is plan delivery risk,
        instrumented.
      </Callout>

      <H2>Explicit Q&A (25)</H2>
      <Stack gap={10}>
        {ANSWERS.map((item) => (
          <Stack key={item.q} gap={4}>
            <Text weight="semibold" size="small">
              {item.q}
            </Text>
            <Text size="small" tone="secondary">
              {item.a}
            </Text>
          </Stack>
        ))}
      </Stack>

      <Divider />

      <H2>Diligence question — final answer</H2>
      <Card>
        <CardHeader title="Would Plan Assurance count as materially differentiated architecture?" />
        <CardBody>
          <Stack gap={8}>
            <Text>
              <Text as="span" weight="semibold">Cautious yes on direction, no on maturity.</Text>{" "}
              A technical diligence review would say: the architecture thesis (governed
              actuals → deterministic SaaS model → constraints → path simulation →
              structured evidence → LLM interpretation) is coherent and somewhat unusual as
              a packaged workflow. The current codebase proves a working client-side stress
              engine and a duplicated constraint layer — not a durable, calibrated,
              enterprise predictive platform. Material differentiation today is{" "}
              <Text as="span" weight="semibold">narrow and provisional</Text>; it becomes
              material only if you close persistence, prior quality, and SoT unification
              before competitors productize the same story.
            </Text>
            <Text size="small" style={{ color: theme.accent }}>
              Your ChatGPT thesis survives in a qualified form: peers mostly sell forecast
              series + user scenarios; SMPL’s live product emphasizes whole-plan path
              stress. That distinction is real. It is not “years ahead,” and it is not
              predictive analytics as the market uses the phrase.
            </Text>
          </Stack>
        </CardBody>
      </Card>

      <Text size="small" tone="secondary">
        Code audit: predictive_planning/* · budget-engine MC ~9048–9329 · PPI framework
        §0.1. Public sources: Cube Planner/cash, Abacum Scenario Intelligence, Workday
        Predictive Forecaster + Decision Intelligence (2026 MC), Anaplan PlanIQ/SHAP/Optimizer,
        Pigment Predictions KB, Drivetrain Drive AI, OneStream SensibleAI.
      </Text>
    </Stack>
  );
}

