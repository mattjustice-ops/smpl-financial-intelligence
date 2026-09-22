import {
  Callout,
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
} from "cursor/canvas";

const FIXED = [
  "Plan Assurance constrained polish + Sales demand SoT + prebuild guards",
  "Bulk board AI + MDA AI claim-verify with SoT / fail-closed fallback",
  "Prompt 5 + interactive: surgically redact unmatched $/%%/Nx",
  "Prompt 5 attribution: strip off-allowlist causal invent sentences",
  "Board $97.5M / $233K dual-SoT purged → pipeline $91.1M + ARR_PER_EMP",
  "Live Board narratives: Exec/ARR/Cash/Revenue/HC/Risks refresh from metrics",
  "Mapper: never label actual cash as forecasted_collections",
  "VE: sync_mapping_queue_from_gl_actuals (ingest) + honesty.mapping_ingest_wired",
  "Export board/MDA packs: block_on_failure=true by default (hard gate)",
  "prebuild: verify-board-stale-arr + repaired verify-forecast-levers",
  "Phase 3: template PPTX charts + scorecard/KPI ink from live ReportingBundle SoT",
  "Budget Sales: watermark book (hire sizing) vs Σ mo capacity labeled distinctly",
  "Docs honesty: Architecture / Map 3 / Maxio prep / AI_SKILL_PRACTICES match hard gates",
  "Forecast computePeriod ARR → SMPLPipeline.computeForecastMonth (shared SoT)",
  "Forecast native Plan Assurance: real /assess packet + Analytics tab + Plan Summary",
];

/** Tabled — founder to re-familiarize before redesign. Source: Forecast GTM Jul 2026 demo seed. */
const GTM_JULY_LAYERS = [
  {
    layer: "Pipeline book",
    line: "Pushed",
    amount: "$2.84M",
    meaning: "Gross $ of all deal types (NB+Exp+React+Cont+Churn)",
  },
  {
    layer: "Pipeline book",
    line: "Closed/Won",
    amount: "$0.33M",
    meaning: "Fcst = Commit-stage only",
  },
  {
    layer: "Pipeline book",
    line: "Ending open",
    amount: "$2.51M",
    meaning: "Pushed − won − lost",
  },
  {
    layer: "Contract events",
    line: "New Business",
    amount: "$1.16M (~$1.2M)",
    meaning: "CRM probability-weighted NB (× attainment)",
  },
];

export default function PlatformIntegrityReview() {
  return (
    <Stack gap={24} style={{ padding: 24, maxWidth: 1100 }}>
      <Stack gap={8}>
        <H1>Platform integrity review</H1>
        <Text tone="secondary" size="small">
          Founder quality pass · Updated Sep 22, 2026 · Forecast PA shipped · GTM tabled
        </Text>
      </Stack>

      <Callout tone="success" title="Shipped — Forecast native Plan Assurance">
        Plan Summary (ex-Overview) + Analytics tab on the same /assess SoT as Budget.
        Packet built from live getResults / display ARR·cash·HC·GTM (not empty res.engine).
        Persist when forecast_version_id is set. Monte Carlo Generate / history outliers remain
        Budget-depth. No Budget Overview rename.
      </Callout>

      <Callout tone="warning" title="Tabled — Forecast GTM layer coherence">
        Coverage numerator (NB gross ~$1.87M in July) is not shown on the GTM table.
        Book pushed / Commit-won / ending open and contract-event weighted NB are three
        different definitions. Parked until founder picks one end-to-end definition.
      </Callout>

      <Grid columns={4} gap={12}>
        <Stat value="0" label="Critical open" tone="success" />
        <Stat value="0" label="High open" tone="success" />
        <Stat value="1" label="Tabled (GTM)" tone="warning" />
        <Stat value="15" label="Closed (incl. FE PA)" tone="success" />
      </Grid>

      <Divider />

      <H2>Tabled — Forecast GTM (July demo)</H2>
      <Text size="small" tone="secondary">
        What the GTM table shows for July · coverage used NB.total / NB.weighted — numerator
        not on-screen.
      </Text>
      <Table
        headers={["Layer", "Line", "Amount", "What it actually is"]}
        rows={GTM_JULY_LAYERS.map((r) => [r.layer, r.line, r.amount, r.meaning])}
        rowTone={GTM_JULY_LAYERS.map(() => "warning" as const)}
        columnAlign={["left", "left", "right", "left"]}
      />

      <Divider />

      <H2>Closed (keep guarding)</H2>
      <Stack gap={6}>
        {FIXED.map((f) => (
          <Row key={f} gap={8} align="center">
            <Pill tone="success" size="small">
              Fixed
            </Pill>
            <Text size="small">{f}</Text>
          </Row>
        ))}
      </Stack>

      <Divider />

      <H3>Still deferred (completeness, not silent invent)</H3>
      <Text size="small" tone="secondary">
        Forecast MC /simulate + history priors (Budget Analytics depth), calibrated PoA,
        Maxio depth, Budget BS/CF stubs, PPI persistence. ARR/Cash PPTX bridge-table cell
        refresh if a customer flags residual table ink. No Budget Plan Overview tab —
        Overview + Analytics already cover that job.
      </Text>
    </Stack>
  );
}
