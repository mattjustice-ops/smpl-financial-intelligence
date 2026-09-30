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

const path = "/integrations/maxio";
const crumb = "Maxio";
const title = "FP&A and Planning Software for Maxio Customers | SMPL.ai";
const description =
  "SMPL.ai combines Maxio billing, ARR, and revenue recognition data with your CRM and ledger for forecasting, budgeting, and board reporting, implemented by SMPL.";
const url = sitePageUrl(path);

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  robots: { index: true, follow: true },
  openGraph: { title, description, url, type: "website", siteName: "SMPL.ai" },
  twitter: { title, description },
};

const WORKFLOWS = [
  {
    title: "ARR waterfall and retention from billing actuals",
    body: "Subscriptions, components, and MRR movements in Maxio become the monthly ARR waterfall: beginning ARR, new business, expansion, contraction, churn, and ending ARR, with net and gross revenue retention calculated using your company's definitions.",
  },
  {
    title: "Recognized and deferred revenue",
    body: "Revenue schedules and contract data from Maxio's revenue recognition sub-ledger show how ARR turns into recognized revenue and deferred revenue, which then feed the income statement and balance sheet.",
  },
  {
    title: "Invoicing and cash timing",
    body: "Invoices and payments show when billed revenue becomes cash. Annual prepaid and monthly contracts with the same ARR produce very different cash curves, and the cash forecast reflects that difference.",
  },
  {
    title: "Budget and forecast measured against billing",
    body: "The budget and forecast are built from plan drivers. Maxio supplies the actual ARR they are measured against, so variance is plan versus billed reality rather than one plan compared with another.",
  },
];

const COMBINED = [
  {
    title: "CRM for pipeline and bookings",
    body: "Maxio records the subscription once a deal is won. Salesforce or HubSpot shows what is still in the pipeline. Together they support a bookings forecast and an ARR forecast that start from the same customers.",
  },
  {
    title: "General ledger for the financial statements",
    body: "NetSuite, Sage Intacct, QuickBooks Online, or another ledger holds posted revenue, expense, and cash. SMPL ties billing ARR and recognized revenue to the ledger and shows the bridge where they differ.",
  },
  {
    title: "Workforce data for cost and capacity",
    body: "Headcount and compensation from your HRIS drive operating expense and sales capacity, so a hiring change shows up in both the cost base and the bookings the team can deliver.",
  },
];

const OUTCOMES = [
  {
    title: "Board-grade ARR that reconciles",
    body: "An ARR waterfall and retention view built on Maxio actuals, tied to CRM bookings and ledger revenue, with the differences explained rather than averaged away.",
  },
  {
    title: "A budget built on governed actuals",
    body: "A driver-based operating budget across the income statement, balance sheet, and cash flow statement, starting from the ARR and balances Maxio and your ledger already hold.",
  },
  {
    title: "An answer to whether the plan can be delivered",
    body: "Plan Assurance tests the plan built on those actuals against coverage, retention floors, and cash floors, and shows which assumption breaks first under stress.",
  },
  {
    title: "Explanations the board can follow",
    body: "Commentary is drafted from calculated movements, such as expansion or churn in a given segment, and every figure can be traced to the billing, CRM, or ledger record behind it.",
  },
];

const STEPS = [
  {
    title: "Agree scope and access",
    body: "We confirm which Maxio products you use for billing and for revenue recognition, which periods matter, and whether SMPL connects to Maxio with read-only access or works from standard Maxio exports.",
  },
  {
    title: "SMPL maps billing to the model",
    body: "SMPL maps customers, products, subscriptions, invoices, and MRR movement categories to the ARR waterfall and applies your definitions, such as when a contract counts toward ARR.",
  },
  {
    title: "SMPL connects the rest of the stack",
    body: "CRM pipeline, the general ledger, and workforce data are mapped to the same customers, departments, and periods, so ARR, revenue, and cash are calculated together.",
  },
  {
    title: "Validate together",
    body: "SMPL ties ending ARR to Maxio, recognized revenue to the ledger, and closed-won bookings to new ARR. Your team reviews the differences and confirms the treatment.",
  },
  {
    title: "Refresh on your close calendar",
    body: "After go-live, your team initiates each refresh when your books close, on your own close calendar, and can load intra-month cash or pipeline data whenever you need a current view.",
  },
];

const FAQS: Faq[] = [
  {
    q: "What FP&A software works with Maxio?",
    a: "SMPL.ai is FP&A and financial intelligence software for SaaS Finance teams, and it uses Maxio billing, ARR, and revenue recognition data together with CRM, general ledger, and workforce data for connected reporting, forecasting, budgeting, and Plan Assurance. SMPL leads the integration and implementation, including data mapping, configuration, and financial validation.",
  },
  {
    q: "Does SMPL.ai replace Maxio?",
    a: "No. Maxio stays where it is and continues to own quote-to-cash, billing, and revenue recognition. SMPL reads Maxio data and builds planning, forecasting, and board reporting on top of it. SMPL does not write back to Maxio.",
  },
  {
    q: "How does Maxio data get into SMPL.ai?",
    a: "As part of implementation, SMPL either connects to Maxio with read-only access or works from standard Maxio exports, depending on which Maxio products you use and your security requirements. SMPL maps and validates the data. After go-live, your team initiates each refresh when your books close, on your own close calendar, and can load intra-month cash or pipeline data whenever you need a current view.",
  },
  {
    q: "Will SMPL.ai use Maxio's ARR or calculate its own?",
    a: "SMPL applies your company's ARR definition consistently. Where your Maxio configuration already reflects that definition, SMPL uses it; where the board definition differs, SMPL documents the adjustment and shows the bridge, so both numbers are explainable.",
  },
  {
    q: "Why would a company that already has Maxio reporting need SMPL?",
    a: "Maxio reports billing and recurring revenue actuals. SMPL connects those actuals to pipeline, the general ledger, and workforce data to build the forecast, the three-statement budget, Plan Assurance, and the board package, so Finance does not assemble that picture by hand each month.",
  },
];

export default function MaxioIntegrationPage() {
  return (
    <SolutionPage
      category={INTEGRATIONS_CATEGORY}
      crumb={crumb}
      h1="SMPL.ai for Finance teams on Maxio"
      ld={solutionPageLd({ title, url, description, faqs: FAQS, crumb, category: INTEGRATIONS_CATEGORY })}
      faqs={FAQS}
      more={{ title: "More integrations", items: otherIntegrations(path) }}
      secondaryCta={{ href: "/integrations", label: "All integrations" }}
      footnote={trademarkNote("Maxio", "Salesforce", "HubSpot", "NetSuite", "Sage Intacct", "QuickBooks Online")}
      related={[
        { href: "/blog/billing-vs-crm-arr", label: "Billing ARR vs CRM ARR" },
        { href: "/arr-revenue-cash-headcount", label: "ARR, revenue, cash & headcount in one model" },
        { href: "/budgeting-and-plan-assurance", label: "Budgeting & Plan Assurance" },
        { href: "/blog/arr-waterfall-vs-gaap-revenue", label: "ARR waterfall vs GAAP revenue" },
      ]}
      lead={
        <p>
          <strong className="font-semibold text-white">
            SMPL.ai is FP&A and financial intelligence software for SaaS Finance teams that
            run billing and revenue recognition on Maxio.
          </strong>{" "}
          Maxio holds your recurring revenue actuals between the CRM and the ERP. SMPL brings
          them together with pipeline, general ledger, and workforce data for connected
          reporting, forecasting, budgeting, and Plan Assurance. SMPL leads the integration
          and implementation, including data mapping, configuration, and financial
          validation.
        </p>
      }
    >
      <Section title="What Maxio data supports in SMPL">
        <p>
          In a typical SaaS stack, the CRM holds the pipeline, Maxio holds billing, ARR, and
          the revenue recognition sub-ledger, and the ERP holds the general ledger. Maxio is
          the source of truth for what customers are actually subscribed to and billed for,
          which makes it the foundation for these workflows.
        </p>
        <PointList items={WORKFLOWS} />
      </Section>

      <Section title="Combined with the rest of your operating data">
        <p>
          The questions a board asks cross all three systems. Why did ARR grow faster than
          revenue? Why did cash lag both? Answering them requires billing, pipeline, and the
          ledger in one model.
        </p>
        <PointList items={COMBINED} />
      </Section>

      <Section title="What you can produce and decide">
        <PointList items={OUTCOMES} />
        <p className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-sm text-slate-400">
          <span className="font-semibold text-slate-200">Illustrative example.</span> Salesforce
          shows $1.2M of closed-won new business for the quarter, but new ARR in Maxio is
          $0.95M. The bridge shows two contracts with start dates next quarter and one
          multi-year deal whose ramp starts lower. The board sees one reconciled ARR figure,
          and the forecast moves the delayed starts into the right months for revenue and
          cash.
        </p>
      </Section>

      <Section title="SMPL leads the implementation">
        <p>
          Your Finance team should not have to redesign its billing setup or build a data
          model to get planning and board reporting on top of Maxio. SMPL takes
          responsibility for the data integration, mapping, configuration, and financial
          validation. Your team supplies the definitions, reviews the results, and makes the
          decisions.
        </p>
        <Steps items={STEPS} />
      </Section>

      <Section title="Discuss your Maxio environment">
        <p>
          Bring a short description of how you use Maxio for billing and revenue
          recognition, which CRM and ledger sit on either side of it, and what your board
          package includes today. We will walk through how SMPL would connect it and what
          your team would see at the end of implementation.
        </p>
      </Section>
    </SolutionPage>
  );
}
