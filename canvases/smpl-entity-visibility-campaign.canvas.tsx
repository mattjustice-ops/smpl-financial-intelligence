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
  Link,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  TodoListCard,
  useCanvasState,
} from "cursor/canvas";

type SiteId =
  | "crunchbase"
  | "dealroom"
  | "wellfound"
  | "startupblink"
  | "g2"
  | "capterra"
  | "producthunt";

type Wave = "0" | "1" | "2" | "3";

type SiteStatus = "not_found" | "draft_only" | "owned" | "skipped" | "collision_other_co";

type CampaignState = {
  selected: SiteId;
  done: Partial<Record<string, boolean>>;
};

const INITIAL: CampaignState = {
  selected: "g2",
  done: { "cb-account": true, crunchbase: true, dealroom: true, startupblink: true },
};

const SITES: Record<
  SiteId,
  {
    name: string;
    wave: Wave;
    status: SiteStatus;
    why: string;
    agentCan: string;
    mattMust: string;
    startUrl: string;
    startLabel: string;
    categories: string;
    notes: string;
  }
> = {
  crunchbase: {
    name: "Crunchbase",
    wave: "1",
    status: "owned",
    why: "Highest-citation company database for Google, journalists, and AI answers.",
    agentCan: "Public profile live: https://www.crunchbase.com/organization/smpl-ai",
    mattMust: "Confirm website on the profile is https://www.smpl-ai.com/, not smpl.ai. Do not merge with crunchbase.com/organization/smpl-5617 (Abu Dhabi family office).",
    startUrl: "https://www.crunchbase.com/organization/smpl-ai",
    startLabel: "SMPL.ai on Crunchbase",
    categories: "SaaS; Financial Software; Artificial Intelligence (AI); Enterprise Software; Analytics",
    notes: "Do not merge with crunchbase.com/organization/smpl-5617 (Abu Dhabi family office).",
  },
  dealroom: {
    name: "Dealroom",
    wave: "1",
    status: "owned",
    why: "Investor/analyst graph that complements Crunchbase.",
    agentCan: "Public profile live: https://app.dealroom.co/companies/smpl_ai_1",
    mattMust: "Confirm website is https://www.smpl-ai.com/. Do not confuse with smpl_llc (Charlotte coworking, smpl.io) or the family office.",
    startUrl: "https://app.dealroom.co/companies/smpl_ai_1",
    startLabel: "SMPL.ai on Dealroom",
    categories: "SaaS; Fintech; Enterprise software; Artificial intelligence",
    notes: "Dealroom also has Smpl, llc at app.dealroom.co/companies/smpl_llc — different company.",
  },
  wellfound: {
    name: "Wellfound",
    wave: "1",
    status: "skipped",
    why: "Startup talent graph. Skipped for now — not needed for the entity campaign.",
    agentCan: "Skipped. Revisit only if hiring or if a later AIO gap shows Wellfound citations.",
    mattMust: "No action.",
    startUrl: "https://wellfound.com/join",
    startLabel: "Wellfound join (skipped)",
    categories: "B2B; SaaS; Fintech; Artificial Intelligence",
    notes: "Skipping does not block Crunchbase, Dealroom, StartupBlink, G2, or Capterra.",
  },
  startupblink: {
    name: "StartupBlink",
    wave: "1",
    status: "owned",
    why: "Ecosystem map listing. Fastest directory; weaker buyer intent, still a unique URL with NAP consistency.",
    agentCan: "Startup submitted for review (2026-09-23). No public map URL yet — paste it when StartupBlink approves.",
    mattMust: "When the listing goes live, send the public StartupBlink URL. Confirm Portland + https://www.smpl-ai.com/.",
    startUrl: "https://www.startupblink.com/startups/add",
    startLabel: "Add startup (already submitted)",
    categories: "Fintech; Software",
    notes: "Submitted for review. Public map appearance can lag. Location must be Portland, Oregon.",
  },
  g2: {
    name: "G2",
    wave: "2",
    status: "not_found",
    why: "Primary software-comparison source for buyers and for AI 'best FP&A tools' answers. Listing now; reviews later.",
    agentCan: "Draft the product description and categories. Cannot submit while logged out; G2 also rejects alpha/beta products.",
    mattMust: "Sign in, submit https://www.g2.com/products/new, describe SMPL as generally available (paying customers, not a beta), then claim.",
    startUrl: "https://www.g2.com/products/new",
    startLabel: "G2 product submission",
    categories: "Primary: FP&A (Financial Planning & Analysis). Secondary: Financial Reporting; Budgeting and Forecasting.",
    notes: "Do not write 'pilot', 'beta', or 'coming soon' on this form. After approval, claim the listing within a few days.",
  },
  capterra: {
    name: "Capterra",
    wave: "2",
    status: "not_found",
    why: "Gartner Digital Markets listing. One vendor signup can syndicate to Capterra, GetApp, and Software Advice.",
    agentCan: "Fill the vendor form fields. Expect a Gartner sales follow-up; skip paid upsell unless you want it.",
    mattMust: "Request the free basic listing at Capterra vendor signup. Use product URL = homepage.",
    startUrl: "https://www.capterra.com/vendors/sign-up/",
    startLabel: "Capterra vendor signup",
    categories: "Financial Planning Software; Financial Reporting Software; Budgeting Software",
    notes: "Company name SMPL.ai, product name SMPL.ai, website and product URL both https://www.smpl-ai.com/. Decline sponsored profile unless you explicitly want ads.",
  },
  producthunt: {
    name: "Product Hunt",
    wave: "3",
    status: "draft_only",
    why: "A launch event, not a directory fill. Draft now if you want; do not burn the one-shot public launch until assets and first-hour support are ready.",
    agentCan: "Write tagline, description, first maker comment, and launch checklist. Cannot hunt from a company account.",
    mattMust: "Use your personal PH account. Create Draft (not Launch now). Schedule only after gallery, video, and day-of supporters exist.",
    startUrl: "https://www.producthunt.com/launch/preparing-for-launch",
    startLabel: "PH launch prep",
    categories: "SaaS; Fintech; Artificial Intelligence; Productivity",
    notes: "SimplAI already exists on Product Hunt. Name the product SMPL.ai and link smpl-ai.com so we do not collide. Self-hunt; do not pay a hunter.",
  },
};

const WAVES: { id: Wave; title: string; when: string }[] = [
  { id: "0", title: "Lock the entity", when: "Today, no new logins" },
  { id: "1", title: "Company databases", when: "This week, 60–90 min with you logged in" },
  { id: "2", title: "Buyer review sites", when: "After Wave 1, 45 min + 3–5 day review" },
  { id: "3", title: "Product Hunt launch", when: "Later, timed event — not this week" },
];

const SHORT_DESC =
  "SMPL.ai is SaaS FP&A and financial intelligence software for growing finance teams. It connects pipeline, ARR, revenue, cash, headcount, and financial statements into one governed model for forecasting, reporting, and board packages.";

const CB_SHORT =
  "SMPL.ai develops SaaS FP&A and financial intelligence software that connects pipeline, ARR, revenue, cash, and financial statements for reporting and board packages.";

const MEDIUM_DESC =
  "SMPL.ai is an FP&A and financial intelligence platform for B2B SaaS companies. It connects CRM, ERP/GL, billing, and HRIS data into one governed operating model covering pipeline, ARR, GAAP revenue, cash, headcount, and financial statements. Finance and executive teams use it for forecasting, variance analysis, workforce planning, and board-ready reporting with lineage back to source records — not generic AI commentary.";

const LONG_DESC =
  "SMPL.ai is a privately held software company based in Portland, Oregon. Founded in 2026 by Matt Justice, it builds SaaS FP&A and financial intelligence software for CFOs, FP&A teams, and executive leaders at growth-stage B2B software companies. The platform ingests data from systems such as CRM, ERP/general ledger, billing, and HRIS, then reconciles that data into a governed model of pipeline, bookings, ARR, recognized revenue, profitability, cash, and workforce. Capabilities include ARR waterfall reporting, management P&L, cash forecasting, scenario analysis, workforce planning, and board packages with driver-based commentary. SMPL.ai is not a replacement for ERP, CRM, or billing systems of record.";

const FOUNDER =
  "Matt Justice is founder and CEO of SMPL.ai (Jun 2026–Present). Based in Portland, Oregon. Background in SaaS Finance, corporate FP&A, GTM Finance, and revenue and billings operations. Earlier career: managed and forecasted a $600M capital budget and a billion-dollar trading portfolio.";

const TAGLINE = "SaaS FP&A software for trusted board reporting";

function statusLabel(status: SiteStatus): string {
  if (status === "not_found") return "No SMPL.ai listing found";
  if (status === "draft_only") return "Create draft only — do not launch";
  if (status === "owned") return "Profile added";
  if (status === "skipped") return "Skipped";
  return "Different company — do not claim";
}

const LOCKED_DONE = new Set(["cb-account", "crunchbase", "dealroom", "startupblink"]);
const LOCKED_SKIPPED = new Set(["wellfound"]);

export default function SmplEntityVisibilityCampaign() {
  const [state, setState] = useCanvasState<CampaignState>("campaign", INITIAL);
  const selected = SITES[state.selected];

  const waveTodos = (wave: Wave) => {
    const items =
      wave === "0"
        ? [
            { id: "kit", content: "Approve canonical name, URL, categories, and descriptions below" },
            { id: "linkedin-co", content: "Update LinkedIn company About to the medium description (already live)" },
            { id: "linkedin-founder", content: "Remove stale 'pilot deployments' language from Matt's LinkedIn" },
            { id: "legal", content: "Confirm legal entity name and founding month (year 2026 is public)" },
          ]
        : wave === "1"
          ? [
              { id: "cb-account", content: "Crunchbase account created (Gmail)" },
              { id: "crunchbase", content: "Crunchbase — https://www.crunchbase.com/organization/smpl-ai" },
              { id: "dealroom", content: "Dealroom — https://app.dealroom.co/companies/smpl_ai_1" },
              { id: "wellfound", content: "Wellfound — skipped" },
              { id: "startupblink", content: "StartupBlink — submitted for review (paste public URL when live)" },
            ]
          : wave === "2"
            ? [
                { id: "g2", content: "G2 — submit product as GA/FP&A, then claim (current)" },
                { id: "capterra", content: "Capterra — free basic listing (skip paid upsell)" },
              ]
            : [
                { id: "ph-draft", content: "Product Hunt — create Draft with SMPL.ai + smpl-ai.com" },
                { id: "ph-assets", content: "Gallery, 60-char tagline, maker first comment, YouTube demo" },
                { id: "ph-launch", content: "Schedule launch only when first-hour supporters are lined up" },
              ];
    return items.map((item) => ({
      ...item,
      status: LOCKED_SKIPPED.has(item.id)
        ? ("cancelled" as const)
        : LOCKED_DONE.has(item.id) || state.done[item.id]
          ? ("completed" as const)
          : ("pending" as const),
    }));
  };

  const toggleTodo = (id: string) => {
    setState((prev) => ({
      ...prev,
      done: { ...prev.done, [id]: !prev.done[id] },
    }));
  };

  return (
    <Stack gap={24}>
      <Stack gap={8}>
        <H1>SMPL.ai entity visibility</H1>
        <Text tone="secondary">
          First-priority campaign: make SMPL easier to find by putting one consistent
          company entity on the databases buyers, journalists, and AI systems already
          trust. Crunchbase, Dealroom, and StartupBlink are in. Wellfound is skipped.
          Next: G2, then Capterra (Wave 2).
        </Text>
      </Stack>

      <Grid columns={4} gap={16}>
        <Stat value="3 / 7" label="Target directories added" tone="info" />
        <Stat value="1" label="Owned profile (LinkedIn)" />
        <Stat value="2" label="Name collisions to avoid" tone="danger" />
        <Stat value="G2" label="Current step" />
      </Grid>

      <Callout tone="info" title="Who creates the accounts">
        You do — it is faster. Every site emails mattjustice@smpl-ai.com a verify
        link, and Crunchbase/G2/Product Hunt are quicker via LinkedIn or Google than
        via a password I cannot complete. I should not invent passwords or submit
        signups I cannot verify. Once you are in, I fill the company profiles.
      </Callout>

      <Callout tone="danger" title="Never use smpl.ai as the company URL">
        https://smpl.ai/ is a different company — an Abu Dhabi family office (Crunchbase
        smpl-5617, LinkedIn smpl-ai-fund). Our canonical URL is{" "}
        <Link href="https://www.smpl-ai.com/">https://www.smpl-ai.com/</Link>. Brand
        name stays SMPL.ai. Product Hunt already has SimplAI, a different product —
        launch as SMPL.ai with the hyphenated domain so those entities do not merge.
      </Callout>

      <H2>StartupBlink paste pack</H2>
      <Text tone="secondary">
        Form: <Link href="https://www.startupblink.com/startups/add">startupblink.com/startups/add</Link>.
        Submissions are reviewed before they appear on the map. If SMPL already
        appears for Portland, claim it instead of adding a duplicate.
      </Text>
      <Table
        headers={["Field", "Paste this"]}
        rows={[
          ["Name", "SMPL.ai"],
          ["Website", "https://www.smpl-ai.com/"],
          ["City / country", "Portland, Oregon, United States"],
          ["Founded", "2026"],
          ["Industry", "Fintech (or Software if Fintech is not listed)"],
          ["Email", "mattjustice@smpl-ai.com"],
          ["LinkedIn", "https://www.linkedin.com/company/smpl-financial-intelligence"],
          ["Short description", SHORT_DESC],
        ]}
      />

      <H2>Account status</H2>
      <Table
        headers={["Site", "Status", "Login", "Next"]}
        rows={[
          [
            "Crunchbase",
            "Profile added",
            "Gmail",
            "Paste the public organization URL when you have it.",
          ],
          [
            "Dealroom",
            "Profile added",
            "mattjustice@smpl-ai.com",
            "Paste the public company URL. Confirm it is not smpl_llc (smpl.io).",
          ],
          ["Wellfound", "Skipped", "—", "No action."],
          [
            "StartupBlink",
            "Current",
            "mattjustice@smpl-ai.com",
            "Submit with the paste pack above.",
          ],
        ]}
        rowTone={["success", "success", "neutral", "warning"]}
      />
      <Text>
        Wave 2 can wait: G2 at{" "}
        <Link href="https://www.g2.com/users/sign_up">g2.com/users/sign_up</Link>,
        Capterra at{" "}
        <Link href="https://www.capterra.com/vendors/sign-up/">
          capterra.com/vendors/sign-up
        </Link>
        .
      </Text>

      <H2>Execution order</H2>
      <Text tone="secondary">
        Company databases first (they mint the entity). Review sites second (they need
        GA product language). Product Hunt last (one public launch; drafts are fine
        now). LinkedIn already exists — align it in Wave 0 so new listings copy the
        same signals.
      </Text>

      <Table
        headers={["Wave", "What", "When", "Why this order"]}
        rows={WAVES.map((wave) => [
          wave.id,
          wave.title,
          wave.when,
          wave.id === "0"
            ? "Inconsistent copy on LinkedIn vs homepage will get copied onto every new profile."
            : wave.id === "1"
              ? "Crunchbase and Dealroom are the pages other sites and models scrape."
              : wave.id === "2"
                ? "G2/Capterra reject beta language and take days to verify."
                : "A weak launch cannot be rerun. Draft now; go live when ready.",
        ])}
        rowTone={["info", "warning", "neutral", "neutral"]}
      />

      <Grid columns={2} gap={16}>
        {WAVES.map((wave) => (
          <Stack key={wave.id} gap={8}>
            <H3>
              Wave {wave.id} · {wave.title}
            </H3>
            <TodoListCard
              todos={waveTodos(wave.id)}
              defaultExpanded={wave.id === "0" || wave.id === "1"}
              onTodoClick={(todo) => toggleTodo(todo.id)}
            />
          </Stack>
        ))}
      </Grid>

      <H2>Canonical entity kit</H2>
      <Text tone="secondary">
        Use these strings on every profile. Homepage H1, LinkedIn, and directory
        listings should all say SaaS FP&A / financial intelligence first. "AI operating
        system for SaaS finance" stays brand narrative, not the directory category.
      </Text>

      <Table
        headers={["Field", "Canonical value"]}
        columnAlign={["left", "left"]}
        rows={[
          ["Name", "SMPL.ai"],
          ["Website", "https://www.smpl-ai.com/"],
          ["Do not use", "https://smpl.ai/"],
          ["LinkedIn company", "https://www.linkedin.com/company/smpl-financial-intelligence"],
          ["HQ", "Portland, Oregon, United States"],
          ["Founded", "2026 (confirm month before Crunchbase)"],
          ["Company size", "1–10 / 2–10 employees"],
          ["Type", "Privately held"],
          ["Founder", "Matt Justice, Founder & CEO"],
          ["Founder LinkedIn", "https://www.linkedin.com/in/matt-justice-a136a14b"],
          ["Demo URL", "https://www.smpl-ai.com/book-demo"],
          ["Industry (LinkedIn today)", "Software Development — leave unless you can pick Computer Software"],
          ["Work email", "mattjustice@smpl-ai.com"],
          ["Legal name", "Confirm before Crunchbase (do not invent Inc/LLC)"],
        ]}
      />

      <H3>Category language</H3>
      <Table
        headers={["Use", "Do not use as primary"]}
        rows={[
          [
            "SaaS FP&A software; board reporting software; financial intelligence platform; ARR reporting",
            "AI OS / Finance OS as the category; BI; dashboard tool; spreadsheet add-on; accounting software; ChatGPT for finance; NetSuite/Salesforce replacement",
          ],
        ]}
      />

      <Grid columns={2} gap={16}>
        <Card>
          <CardHeader>Tagline (47 chars)</CardHeader>
          <CardBody>
            <Text>{TAGLINE}</Text>
            <Text tone="secondary" size="small">
              Product Hunt limit is 60 characters. Also usable as G2/Capterra headline.
            </Text>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>Crunchbase short</CardHeader>
          <CardBody>
            <Text>{CB_SHORT}</Text>
          </CardBody>
        </Card>
      </Grid>

      <Card>
        <CardHeader>Short description (all directories)</CardHeader>
        <CardBody>
          <Text>{SHORT_DESC}</Text>
        </CardBody>
      </Card>

      <Card collapsible defaultOpen>
        <CardHeader>Medium description (LinkedIn, G2, Capterra, Wellfound)</CardHeader>
        <CardBody>
          <Text>{MEDIUM_DESC}</Text>
        </CardBody>
      </Card>

      <Card collapsible defaultOpen={false}>
        <CardHeader>Long description (Crunchbase / Dealroom — objective)</CardHeader>
        <CardBody>
          <Text>{LONG_DESC}</Text>
          <Text tone="secondary" size="small">
            Crunchbase rejects sales copy. This version is factual on purpose.
          </Text>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>Founder blurb</CardHeader>
        <CardBody>
          <Text>{FOUNDER}</Text>
        </CardBody>
      </Card>

      <Divider />

      <H2>Site-by-site</H2>
      <Text tone="secondary">
        Select a site for the exact start URL, categories, and what has to happen in
        your browser. Status from public search on 19 Sep 2026.
      </Text>

      <Row gap={8} wrap>
        {(Object.keys(SITES) as SiteId[]).map((id) => (
          <Pill
            key={id}
            active={state.selected === id}
            onClick={() => setState((prev) => ({ ...prev, selected: id }))}
          >
            {SITES[id].name}
          </Pill>
        ))}
      </Row>

      <Stack gap={12}>
        <Row gap={8} align="center">
          <H3>{selected.name}</H3>
          <Pill active={selected.status === "not_found"}>{statusLabel(selected.status)}</Pill>
        </Row>
        <Text>
          Wave {selected.wave}. {selected.why}
        </Text>
        <Grid columns={2} gap={16}>
          <Card>
            <CardHeader>What I can do</CardHeader>
            <CardBody>
              <Text>{selected.agentCan}</Text>
            </CardBody>
          </Card>
          <Card>
            <CardHeader>What you must do</CardHeader>
            <CardBody>
              <Text>{selected.mattMust}</Text>
            </CardBody>
          </Card>
        </Grid>
        <Text>
          Categories: {selected.categories}
        </Text>
        <Text tone="secondary">{selected.notes}</Text>
        <Text>
          Start here: <Link href={selected.startUrl}>{selected.startLabel}</Link>
        </Text>
      </Stack>

      <Table
        headers={["Site", "Wave", "Public status", "Login"]}
        rows={(Object.keys(SITES) as SiteId[]).map((id) => {
          const site = SITES[id];
          return [
            site.name,
            site.wave,
            statusLabel(site.status),
            id === "dealroom" || id === "g2" || id === "capterra"
              ? "@smpl-ai.com"
              : "Personal account (Matt)",
          ];
        })}
        rowTone={(Object.keys(SITES) as SiteId[]).map((id) => {
          const status = SITES[id].status;
          if (status === "owned") return "success";
          if (status === "skipped") return "neutral";
          if (status === "not_found") return "warning";
          return "info";
        })}
      />

      <H2>Product Hunt strategy</H2>
      <Text>
        Treat PH as a launch, not a Yellow Pages listing. Product Hunt indexes drafts
        privately; a public launch is a 24-hour PST event that you should not spend
        early. Self-hunt from Matt's personal account. First maker comment is required
        quality — 70% of Product of the Day posts include one.
      </Text>
      <Table
        headers={["Asset", "Canonical copy / rule"]}
        rows={[
          ["Product name", "SMPL.ai (not SimplAI, not SMPL AI Fund)"],
          ["URL", "https://www.smpl-ai.com/ — no UTM, no short links"],
          ["Tagline", TAGLINE],
          ["Topics", "SaaS, Fintech, Artificial Intelligence, Productivity"],
          ["Maker first comment", "Lead with the finance problem (board packs nobody trusts), then what SMPL actually reconciles. Invite FP&A people to ask questions."],
          ["Gallery", "Homepage, ARR waterfall, board commentary, copilot Q&A — production UI, not mockups"],
          ["Video", "Public YouTube only; no private links"],
          ["When to launch", "Tue–Thu, after Wave 1–2 URLs exist so PH visitors can also find Crunchbase/G2"],
          ["When not to launch", "No demo path, no first-hour supporters, or while still describing the product as a pilot"],
        ]}
      />

      <H2>LinkedIn already live — align it in Wave 0</H2>
      <Text>
        Company page:{" "}
        <Link href="https://www.linkedin.com/company/smpl-financial-intelligence">
          smpl-financial-intelligence
        </Link>
        . Website is already correct. Tagline today is "AI-Powered Financial
        Intelligence for SaaS Companies" — change to the tagline above so Crunchbase
        editors and models see the same primary category. Founder profile still says
        SMPL is "preparing for pilot customer deployments," which contradicts paying
        customers in production and will get G2 rejected if copied.
      </Text>

      <Callout tone="warning" title="Current step">
        Finish StartupBlink with the paste pack. Then send the Crunchbase and
        Dealroom public URLs when they appear so we can add them as official
        sameAs links.
      </Callout>

      <Text tone="tertiary" size="small">
        Sources: smpl-ai.com homepage, LinkedIn company and founder pages, Exa company
        graph, Crunchbase/Dealroom/G2/Capterra/Wellfound/StartupBlink help docs. Public
        directory search on 19 Sep 2026. This board is the campaign tracker, not a
        submitted listing.
      </Text>
    </Stack>
  );
}
