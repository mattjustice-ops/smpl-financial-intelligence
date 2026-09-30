import type { Metadata } from "next";

import {
  INTEGRATIONS_CATEGORY,
  PointList,
  Section,
  SolutionPage,
  Steps,
  solutionPageLd,
  type Faq,
} from "@/components/landing/SolutionPage";
import { otherIntegrations, trademarkNote } from "@/components/landing/integrationsCatalog";
import { sitePageUrl } from "@/lib/site";

const path = "/integrations/netsuite-salesforce";
const crumb = "NetSuite + Salesforce";
const title = "NetSuite + Salesforce Revenue Forecasting & Planning | SMPL.ai";
const description =
  "Connect NetSuite actuals and Salesforce pipeline in one SaaS model for revenue forecasting, budgeting, and board reporting. SMPL leads the integration and validation.";
const url = sitePageUrl(path);

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  robots: { index: true, follow: true },
  openGraph: { title, description, url, type: "website", siteName: "SMPL.ai" },
  twitter: { title, description },
};

const GAP = [
  {
    title: "Different customers",
    body: "A Salesforce account and a NetSuite customer rarely share a name or an ID. Until they are matched, pipeline cannot be connected to the revenue and receivables it produces.",
  },
  {
    title: "Different products",
    body: "Salesforce products and NetSuite items are maintained by different teams and drift apart, so revenue by product in the ledger does not line up with bookings by product in the CRM.",
  },
  {
    title: "Different clocks",
    body: "Salesforce records a booking at close. NetSuite recognizes revenue over the service period and records cash when the invoice is paid. A revenue forecast has to follow all three dates.",
  },
];

const CHAIN = [
  {
    title: "Pipeline to bookings",
    body: "Open opportunities by stage and close month, with slippage and win rates from Salesforce history, forecast next quarter's bookings.",
  },
  {
    title: "Bookings to ARR",
    body: "Closed-won deals become ARR on their start dates, using your ARR definition and your billing records, whether billing runs in NetSuite or a separate platform.",
  },
  {
    title: "ARR to recognized revenue",
    body: "Contracted and expected ARR is converted into recognized revenue by month and compared with what NetSuite has already recognized.",
  },
  {
    title: "Revenue to cash",
    body: "Billing terms and collection patterns from NetSuite receivables turn the revenue forecast into a cash forecast and runway.",
  },
];

const OUTCOMES = [
  {
    title: "A revenue forecast with visible components",
    body: "Recognized revenue to date from NetSuite, revenue already under contract, and revenue that depends on open pipeline are shown separately, so leadership can see how much of the plan is still at risk.",
  },
  {
    title: "Sales and marketing efficiency by period",
    body: "Sales and marketing spend from NetSuite is set against pipeline created and bookings from Salesforce for the same months.",
  },
  {
    title: "A budget that starts from both systems",
    body: "The driver-based budget uses Salesforce win rates and coverage for the GTM plan and NetSuite ending balances for the opening balance sheet and cash.",
  },
  {
    title: "Board slides that agree with each other",
    body: "Pipeline, bookings, ARR, revenue, and cash in the board package come from one model instead of a CRM export and a ledger export reconciled by hand.",
  },
];

const STEPS = [
  {
    title: "Agree scope and access",
    body: "We confirm which NetSuite subsidiaries and which Salesforce record types are in scope. SMPL connects to each system with read-only access or works from structured extracts.",
  },
  {
    title: "SMPL matches customers and products",
    body: "SMPL builds the mapping between Salesforce accounts and NetSuite customers, and between CRM products and ledger items, and flags the records that need a decision from your team.",
  },
  {
    title: "SMPL configures the chain",
    body: "Pipeline, bookings, ARR, revenue, and cash are connected in one model with your definitions and reporting structure.",
  },
  {
    title: "Validate together",
    body: "SMPL ties closed-won bookings to new ARR, and revenue and cash to NetSuite. Your team reviews the differences and confirms the treatment.",
  },
  {
    title: "Run on your reporting cadence",
    body: "Reporting data is kept current on the refresh arrangement agreed during implementation, aligned to your close, forecast, and board calendar.",
  },
];

const FAQS: Faq[] = [
  {
    q: "How can we forecast revenue using NetSuite and Salesforce together?",
    a: "Connect Salesforce pipeline and NetSuite actuals in one model that follows the chain from pipeline to bookings, ARR, recognized revenue, and cash. SMPL.ai does this for SaaS Finance teams: it matches customers and products across the two systems, applies your definitions, and forecasts revenue with recognized, contracted, and pipeline-dependent components shown separately. SMPL leads the integration and implementation.",
  },
  {
    q: "Do we need a NetSuite-Salesforce sync to use SMPL.ai?",
    a: "No. SMPL reads from each system separately and does the customer and product matching in its own model. If you already sync the two, SMPL uses the shared identifiers you have.",
  },
  {
    q: "What if our billing is not in NetSuite?",
    a: "Many SaaS companies bill in Maxio, Stripe, or Chargebee and post summaries to NetSuite. SMPL adds the billing system as a third source for ARR and connects it to the same customers.",
  },
  {
    q: "Does SMPL.ai write back to NetSuite or Salesforce?",
    a: "No. SMPL reads from both systems. NetSuite remains the system of record for accounting and Salesforce for pipeline.",
  },
];

export default function NetSuiteSalesforcePage() {
  return (
    <SolutionPage
      category={INTEGRATIONS_CATEGORY}
      crumb={crumb}
      h1="NetSuite and Salesforce in one revenue forecast"
      ld={solutionPageLd({ title, url, description, faqs: FAQS, crumb, category: INTEGRATIONS_CATEGORY })}
      faqs={FAQS}
      more={{ title: "More integrations", items: otherIntegrations(path) }}
      secondaryCta={{ href: "/integrations", label: "All integrations" }}
      footnote={trademarkNote("NetSuite", "Salesforce", "Maxio", "Stripe", "Chargebee")}
      related={[
        { href: "/integrations/netsuite", label: "SMPL.ai for NetSuite" },
        { href: "/integrations/salesforce", label: "SMPL.ai for Salesforce" },
        { href: "/blog/saas-revenue-forecasting-arr-bookings-gaap", label: "SaaS revenue forecasting" },
        { href: "/arr-revenue-cash-headcount", label: "ARR, revenue, cash & headcount in one model" },
      ]}
      lead={
        <p>
          <strong className="font-semibold text-white">
            SMPL.ai connects NetSuite accounting actuals with Salesforce pipeline in one SaaS
            financial model.
          </strong>{" "}
          Finance gets a revenue forecast that runs from open opportunities through bookings,
          ARR, recognized revenue, and cash, plus the budget and board reporting built on the
          same numbers. SMPL leads the integration and implementation, including customer and
          product matching, configuration, and financial validation.
        </p>
      }
    >
      <Section title="Why the two systems do not line up on their own">
        <p>
          NetSuite and Salesforce are each reliable for their own purpose. Forecasting revenue
          requires both, and three gaps usually stand in the way.
        </p>
        <PointList items={GAP} />
      </Section>

      <Section title="One chain from pipeline to cash">
        <p>
          Once customers, products, and periods are aligned, SMPL calculates each step from
          the one before it, so a change in pipeline or close dates flows through to revenue
          and cash.
        </p>
        <PointList items={CHAIN} />
      </Section>

      <Section title="What you can produce and decide">
        <PointList items={OUTCOMES} />
        <p className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-sm text-slate-400">
          <span className="font-semibold text-slate-200">Illustrative example.</span> The
          full-year revenue plan is $24M. NetSuite has recognized $11.5M through June and
          contracted ARR accounts for another $10.1M of second-half revenue. The remaining
          $2.4M depends on Salesforce pipeline closing by September. Leadership can see that
          gap, the opportunities behind it, and what a one-quarter slip would do to revenue
          and year-end cash.
        </p>
      </Section>

      <Section title="SMPL leads the implementation">
        <p>
          The matching work between CRM and ledger is usually what stalls a revenue
          forecasting project. SMPL takes responsibility for it, along with the integration,
          configuration, and financial validation. Your team supplies definitions, resolves
          the exceptions SMPL flags, and makes the decisions.
        </p>
        <Steps items={STEPS} />
      </Section>

      <Section title="Discuss your NetSuite and Salesforce environment">
        <p>
          Bring a short description of your subsidiaries, where billing runs, how
          opportunities are structured, and how revenue is forecast today. We will walk
          through how SMPL would connect the two systems and what your team would see at the
          end of implementation.
        </p>
      </Section>
    </SolutionPage>
  );
}
