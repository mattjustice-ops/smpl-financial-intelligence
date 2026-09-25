import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
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

/**
 * Evidence-backed audit of AIO rules_v1 scoring vs independent review
 * of every saved ChatGPT Search answer in both Full-46 runs.
 * Source: Postgres aio_manual_audits + lib/aio/evaluate.ts classifySmplStrength.
 */

const RUBRIC = [
  {
    tier: "none",
    def: "No SMPL brand or owned-domain reference",
  },
  {
    tier: "mentioned",
    def: "Named or smpl-ai.com cited; not in an evaluation set; not preferred",
  },
  {
    tier: "shortlisted",
    def: "In an explicit multi-vendor evaluation/consideration set, or framed as an option worth evaluating alongside others — without being the preferred pick",
  },
  {
    tier: "recommended",
    def: "Prose recommends SMPL specifically (even with caveats) without naming it the single best",
  },
  {
    tier: "top_pick",
    def: "Prose names SMPL as best / top / clearest / standout, or rank #1 for the ask",
  },
];

const INVENTORY = [
  {
    run: "Baseline 2026-09-15",
    rows: "46",
    uniqueQids: "46 / 46 seed",
    empty: "0",
    note: "Fragmented across many single-audit batches; no duplicate query_ids",
  },
  {
    run: "Full 46 2026-09-23",
    rows: "46",
    uniqueQids: "46 / 46 seed",
    empty: "0",
    note: "Single batch b5266ed4…; import intact",
  },
];

const COUNTS = [
  {
    metric: "SMPL named in answer",
    bStored: "1",
    bCorrected: "1",
    fStored: "1",
    fCorrected: "1",
  },
  {
    metric: "Owned-domain citation",
    bStored: "0",
    bCorrected: "0",
    fStored: "1",
    fCorrected: "1",
  },
  {
    metric: "Shortlist inclusion (≥ shortlisted)",
    bStored: "1*",
    bCorrected: "1",
    fStored: "0",
    fCorrected: "1",
  },
  {
    metric: "Explicit recommendation (≥ recommended)",
    bStored: "1*",
    bCorrected: "1",
    fStored: "0",
    fCorrected: "0",
  },
  {
    metric: "Top pick",
    bStored: "1",
    bCorrected: "0",
    fStored: "0",
    fCorrected: "0",
  },
];

const DISCREPANCIES = [
  {
    run: "2026-09-15",
    qid: "use_case_03",
    query: "What FP&A software handles ARR, revenue, cash, and headcount together?",
    original: "top_pick",
    corrected: "recommended",
    excerpt:
      "An interesting newer option is SMPL.ai… I'd investigate it if the primary goal is SaaS operating metrics… though it's a newer choice than Cube/Pigment. (Prose prefers Cube as cleanest match.)",
    cause:
      "False top_pick: classifySmplStrength only inspects ±180 chars around FIRST match (table row). Window contains column header “Best fit”, which matches /\\bbest\\b/ and returns top_pick before later prose is read.",
  },
  {
    run: "2026-09-23",
    qid: "use_case_03",
    query: "What FP&A software handles ARR, revenue, cash, and headcount together?",
    original: "mentioned",
    corrected: "shortlisted",
    excerpt:
      "For a SaaS company, I'd probably start the evaluation with Drivetrain, Cube, Pigment, and SMPL.ai rather than generic budgeting tools.",
    cause:
      "False under-score: same first-window-only rule. First SMPL.ai is a table row (“Strong…”) with no shortlist keywords, so strength stays mentioned. Concluding evaluation-start list is never inspected.",
  },
];

export default function AioScoringAudit() {
  return (
    <Stack gap={24}>
      <Stack gap={8}>
        <H1>AIO scoring audit — ChatGPT Search Full 46</H1>
        <Text tone="secondary">
          Independent review of every saved answer in baseline 2026-09-15 and
          Full 46 2026-09-23. Evaluator: rules_v1. Historical rows preserved;
          corrections are assessment-only.
        </Text>
        <Row gap={8}>
          <Pill tone="success">No missed mentions</Pill>
          <Pill tone="warning">2 strength misclassifications</Pill>
          <Pill tone="info">Both on use_case_03 only</Pill>
        </Row>
      </Stack>

      <Callout tone="success" title="Direct answer">
        SMPL did not appear in any additional queries that scoring missed. Both
        runs: exactly 1/46 named mentions (use_case_03). Loose body+citation
        scan for /smpl/i found no other hits. Recommendation strength was wrong
        on that single hit in both runs — baseline over-scored as top_pick;
        latest under-scored as mentioned despite an explicit evaluation shortlist.
      </Callout>

      <Grid columns={4} gap={12}>
        <Stat value="1 / 46" label="Baseline named (corrected)" />
        <Stat value="1 / 46" label="Full 46 named (corrected)" />
        <Stat value="0 → 1" label="Owned cites (baseline → latest)" tone="success" />
        <Stat
          value="rec → shortlist"
          label="Strength WoW (corrected)"
          tone="warning"
        />
      </Grid>

      <Divider />

      <H2>Evidence inventory</H2>
      <Table
        headers={["Run", "Rows", "Unique query IDs", "Empty/tiny", "Notes"]}
        rows={INVENTORY.map((r) => [
          r.run,
          r.rows,
          r.uniqueQids,
          r.empty,
          r.note,
        ])}
      />
      <Text tone="secondary" size="small">
        Sacred scorecard file hardcodes mention_count=1 / hit_query_id=use_case_03
        — coverage matches DB. Baseline audits live in many “Baseline bulk -
        2026-09-15” batches (46 rows, 46 unique IDs), not one named sacred batch.
      </Text>

      <H2>Independent rubric (same for both runs)</H2>
      <Table
        headers={["Tier", "Definition"]}
        rows={RUBRIC.map((r) => [r.tier, r.def])}
      />
      <Text tone="secondary" size="small">
        Citation alone ≠ recommendation. Table row alone ≠ top pick. Being last
        in a shortlist still counts as shortlisted. Take the maximum tier
        supported by evidence. No replacement prominence_score invented.
      </Text>

      <H2>Original vs corrected counts</H2>
      <Table
        headers={[
          "Metric",
          "Baseline stored",
          "Baseline corrected",
          "Full 46 stored",
          "Full 46 corrected",
        ]}
        rows={COUNTS.map((c) => [
          c.metric,
          c.bStored,
          c.bCorrected,
          c.fStored,
          c.fCorrected,
        ])}
      />
      <Text tone="secondary" size="small">
        *Baseline stored “shortlist+/recommended+” came only via the false
        top_pick label, not a true shortlist detection path.
      </Text>

      <H2>Discrepancy table</H2>
      <Table
        headers={[
          "Run",
          "Query ID",
          "Original",
          "Corrected",
          "Supporting excerpt",
          "Cause",
        ]}
        rows={DISCREPANCIES.map((d) => [
          d.run,
          d.qid,
          d.original,
          d.corrected,
          d.excerpt,
          d.cause,
        ])}
      />

      <Divider />

      <H2>Confirmed code path</H2>
      <Card>
        <CardHeader>classifySmplStrength — frontend/lib/aio/evaluate.ts</CardHeader>
        <CardBody>
          <Stack gap={10}>
            <Text>
              Strength is derived from a single ±180 character window around the
              first regex match among SMPL.ai / SMPL / smpl-ai.com. Later
              mentions are ignored. top_pick fires on bare{" "}
              <Code>/\bbest\b/</Code> inside that window.
            </Text>
            <H3>Baseline false top_pick — first window</H3>
            <Text tone="secondary" size="small">
              First match idx 421 (table). Window includes header “Best fit” →
              matched_best=["best"] → returns top_pick. Later “I'd investigate
              it” never evaluated. Prose prefers Cube (“cleanest match”).
            </Text>
            <H3>Full 46 false mentioned — first window</H3>
            <Text tone="secondary" size="small">
              First match idx 533 (table “Strong…”). No shortlist keywords in
              window → mentioned. Concluding “start the evaluation with
              Drivetrain, Cube, Pigment, and SMPL.ai” at idx ~1839 never seen.
              Re-running today's evaluator on stored text reproduces the same
              stored labels (persistence OK; rule bug).
            </Text>
          </Stack>
        </CardBody>
      </Card>

      <H2>WoW reassessment (corrected)</H2>
      <Grid columns={3} gap={12}>
        <Card>
          <CardHeader trailing={<Pill tone="neutral">Flat</Pill>}>
            Coverage
          </CardHeader>
          <CardBody>
            <Text>
              Still 1/46 named mentions. No missed hits in either run. Category
              coverage unchanged (use_case only).
            </Text>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill tone="warning">Soft decline</Pill>}>
            Recommendation strength
          </CardHeader>
          <CardBody>
            <Text>
              Corrected: recommended → shortlisted on the same query. Real
              softening (Cube preferred → Drivetrain/Cube/Pigment lead; SMPL
              last in start-evaluation list). Not the catastrophic top_pick →
              mentioned drop the report claimed.
            </Text>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill tone="success">Improved</Pill>}>
            Owned citation
          </CardHeader>
          <CardBody>
            <Text>
              0 → 1 owned-domain cite (https://www.smpl-ai.com/). Retrieval
              signal improved while shortlist classification stayed the right
              tier once corrected.
            </Text>
          </CardBody>
        </Card>
      </Grid>

      <H2>Smallest supported fix (do not rewrite history)</H2>
      <Stack gap={6}>
        <Text>
          1. Score max strength across all SMPL match windows (or whole-answer
          shortlist list patterns), not first-only.
        </Text>
        <Text>
          2. Ignore table column-header tokens (e.g. “Best fit”) as top_pick
          triggers unless the predicate binds to SMPL as subject.
        </Text>
        <Text>
          3. Add shortlist cues: “start the evaluation with”, “worth looking
          at”, multi-vendor “A, B, C, and SMPL” lists.
        </Text>
        <Text>
          4. Regression cases from this audit: baseline use_case_03 → not
          top_pick; Full 46 use_case_03 → shortlisted; both remain mentioned≥1;
          absent-SMPL answers stay none.
        </Text>
        <Text tone="secondary" size="small">
          Keep frozen sacred_baseline.json and stored evaluation_json as
          historical. Ship corrected metrics as a parallel audit view or
          evaluator_version bump (rules_v2) on new imports only.
        </Text>
      </Stack>

      <Callout tone="neutral" title="Evidence gaps">
        Sacred baseline is a summary JSON, not a single batch FK — reconstructed
        from all non–Full-46 audits on 2026-09-15 (46 unique qids). No original
        ChatGPT UI session recordings beyond pasted raw_response. Competitor
        strength bugs (e.g. Runway shortlisted on Full 46) were out of scope
        except where they share the same windowing pattern.
      </Callout>
    </Stack>
  );
}
