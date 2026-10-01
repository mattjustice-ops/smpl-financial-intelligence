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
import { DEFAULT_OG_IMAGE, sitePageUrl } from "@/lib/site";

const path = "/integrations/rillet";
const crumb = "Rillet";
const title = "FP&A, Forecasting & Planning for Rillet Customers | SMPL.ai";
const description =
  "SMPL.ai combines Rillet ledger and revenue data with CRM, billing, and workforce data for SaaS forecasting, budgeting, and board reporting, implemented by SMPL.";
const url = sitePageUrl(path);

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  robots: { index: true, follow: true },
  openGraph: { title, description, url, images: [DEFAULT_OG_IMAGE], type: "website", siteName: "SMPL.ai" },
  twitter: { card: "summary_large_image", title, description },
};

const WORKFLOWS = [
  {
    title: "Recognized and deferred revenue with the ledger",
    body: "Rillet keeps revenue recognition alongside the general ledger, so recognized revenue, deferred revenue, and the contracts behind them arrive together. SMPL uses them to bridge ARR to revenue and to schedule future revenue in the forecast.",
  },
  {
    title: "Financial statements and the management P&L",
    body: "Posted activity becomes the income statement, balance sheet, and cash flow statement, with departments and other reporting fields mapped to the management P&L your leadership team uses.",
  },
  {
    title: "Cash and working capital",
    body: "Receivables, payables, and cash balances feed the cash forecast and the budget's opening balance sheet.",
  },
  {
    title: "Budget and forecast versus actual",
    body: "Rillet actuals are compared with a driver-based budget and a rolling forecast, with variances explained by the drivers behind them.",
  },
];

const COMBINED = [
  {
    title: "CRM pipeline",
    body: "Salesforce or HubSpot opportunities supply the pipeline and expected bookings that the recognized-revenue history in Rillet cannot show.",
  },
  {
    title: "Billing and subscription movements",
    body: "Where subscriptions are billed in Stripe, Chargebee, or Maxio, SMPL uses that data for the ARR waterfall and retention and ties it to revenue in Rillet.",
  },
  {
    title: "Workforce",
    body: "Headcount and compensation from your HRIS or payroll system drive the headcount plan, opex, and cash.",
  },
];

const OUTCOMES = [
  {
    title: "A revenue forecast that starts from contracts",
    body: "Revenue already scheduled from signed contracts is shown separately from revenue that depends on renewals and open pipeline.",
  },
  {
    title: "A three-statement budget",
    body: "A driver-based budget across the income statement, balance sheet, and cash flow statement, starting from Rillet's ending balances.",
  },
  {
    title: "Plans tested before approval",
    body: "Plan Assurance checks the budget against coverage, retention, and cash floors, and runs named stress cases before the plan goes to the board.",
  },
  {
    title: "A board package built on the same numbers",
    body: "ARR, revenue, statements, cash, and headcount from one model, with commentary drafted from calculated variances and traceable to source.",
  },
];

const STEPS = [
  {
    title: "Agree scope and access",
    body: "We confirm entities, periods, and reporting fields. SMPL connects to Rillet with read-only access or works from structured exports, whichever fits your environment.",
  },
  {
    title: "SMPL maps the ledger and revenue data",
    body: "SMPL maps accounts, reporting fields, and revenue schedules to statement lines, the management P&L, and the ARR-to-revenue bridge.",
  },
  {
    title: "SMPL connects the rest of the stack",
    body: "CRM, billing, and workforce data are mapped to the same customers, departments, and months.",
  },
  {
    title: "Validate together",
    body: "SMPL ties the statements, revenue, and cash to Rillet and ARR to your billing source. Your team reviews the results and confirms definitions.",
  },
  {
    title: "Refresh on your close calendar",
    body: "After go-live, your team initiates each refresh when your books close, on your own close calendar, and can load intra-month cash or pipeline data whenever you need a current view.",
  },
];

const FAQS: Faq[] = [
  {
    q: "Is there FP&A and planning software for companies using Rillet?",
    a: "Yes. SMPL.ai is FP&A and financial intelligence software for SaaS Finance teams, and it brings Rillet ledger and revenue data together with CRM, billing, and workforce information for forecasting, budgeting, Plan Assurance, and board reporting. SMPL leads the integration and implementation, including data mapping, configuration, and financial validation.",
  },
  {
    q: "How does Rillet data get into SMPL.ai?",
    a: "As part of implementation, SMPL either connects to Rillet with read-only access or works from structured exports. SMPL maps and validates the data. After go-live, your team initiates each refresh when your books close, on your own close calendar, and can load intra-month cash or pipeline data whenever you need a current view.",
  },
  {
    q: "Rillet already reports revenue. What does SMPL.ai add?",
    a: "Rillet records and recognizes what has happened. SMPL connects that record to pipeline, subscription movements, and the workforce plan to forecast what comes next, build the three-statement budget, test it with Plan Assurance, and produce the board package.",
  },
  {
    q: "Does SMPL.ai write back to Rillet?",
    a: "No. SMPL reads from Rillet and does not post entries or change records. Rillet remains your system of record for accounting.",
  },
];

export default function RilletIntegrationPage() {
  return (
    <SolutionPage
      category={INTEGRATIONS_CATEGORY}
      crumb={crumb}
      h1="SMPL.ai for Finance teams on Rillet"
      ld={solutionPageLd({ title, url, description, faqs: FAQS, crumb, category: INTEGRATIONS_CATEGORY })}
      faqs={FAQS}
      more={{ title: "More integrations", items: otherIntegrations(path) }}
      secondaryCta={{ href: "/integrations", label: "All integrations" }}
      footnote={trademarkNote("Rillet", "Salesforce", "HubSpot", "Stripe", "Chargebee", "Maxio")}
      related={[
        { href: "/blog/arr-waterfall-vs-gaap-revenue", label: "ARR waterfall vs GAAP revenue" },
        { href: "/blog/saas-revenue-forecasting-arr-bookings-gaap", label: "SaaS revenue forecasting" },
        { href: "/budgeting-and-plan-assurance", label: "Budgeting & Plan Assurance" },
        { href: "/saas-board-reporting", label: "SaaS board reporting" },
      ]}
      lead={
        <p>
          <strong className="font-semibold text-white">
            SMPL.ai is FP&A and financial intelligence software for SaaS Finance teams that
            run their accounting on Rillet.
          </strong>{" "}
          Bring Rillet ledger and revenue data together with your CRM, billing, and workforce
          information for connected forecasting, budgeting, Plan Assurance, and board
          reporting. SMPL leads the integration and implementation, including data mapping,
          configuration, and financial validation.
        </p>
      }
    >
      <Section title="What Rillet data supports in SMPL">
        <p>
          Rillet is an accounting platform used by SaaS companies that keeps the general
          ledger and revenue recognition together. In SMPL, that combination drives these
          workflows.
        </p>
        <PointList items={WORKFLOWS} />
      </Section>

      <Section title="Combined with the rest of your operating data">
        <p>
          A modern ledger shortens the close. Planning still needs the systems that describe
          what happens next, connected in one model.
        </p>
        <PointList items={COMBINED} />
      </Section>

      <Section title="What you can produce and decide">
        <PointList items={OUTCOMES} />
        <p className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-sm text-slate-400">
          <span className="font-semibold text-slate-200">Illustrative example.</span> Revenue
          already scheduled in Rillet covers 85% of next quarter&apos;s plan. The remaining 15%
          depends on renewals in the CRM, and two of the largest renew in the last week of the
          quarter. The forecast shows the revenue and cash effect if either slips, and the
          budget&apos;s stress cases show whether the plan still clears its cash floor.
        </p>
      </Section>

      <Section title="SMPL leads the implementation">
        <p>
          SMPL takes responsibility for the data integration, mapping, configuration, and
          financial validation. Your team supplies the definitions, reviews the results, and
          makes the decisions.
        </p>
        <Steps items={STEPS} />
      </Section>

      <Section title="Discuss your Rillet environment">
        <p>
          Bring a short description of your entities, where subscriptions are billed, which
          CRM and HRIS you use, and what your board package includes today. We will walk
          through how SMPL would connect it and what your team would see at the end of
          implementation.
        </p>
      </Section>
    </SolutionPage>
  );
}
