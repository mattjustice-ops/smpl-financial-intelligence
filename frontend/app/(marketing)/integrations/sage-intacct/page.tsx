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

const path = "/integrations/sage-intacct";
const crumb = "Sage Intacct";
const title = "Sage Intacct FP&A, Reporting & Planning for SaaS | SMPL.ai";
const description =
  "SMPL.ai combines Sage Intacct GL and dimension data with CRM, billing, and HR data for SaaS reporting, budgeting, and Plan Assurance, implemented by SMPL.";
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
    title: "A management P&L built from your dimensions",
    body: "Sage Intacct tags each transaction with dimensions such as department, location, class, project, customer, and vendor. SMPL maps the dimensions you report on into the management P&L, so functional and departmental views come straight from the ledger.",
  },
  {
    title: "Built on Sage Intacct's consolidated results",
    body: "For companies running several entities, SMPL uses Sage Intacct's consolidated financial actuals, including the currency translation and intercompany elimination adjustments Sage Intacct has already made. For USD-reporting companies, that means the consolidated USD results. Sage Intacct remains the system of record for consolidation, and SMPL builds reporting and planning on that foundation rather than recreating the consolidation engine. Entity and currency information is retained, and entity-level views are scoped during implementation.",
  },
  {
    title: "Financial statements and cash",
    body: "Posted GL balances become the income statement, balance sheet, and cash flow statement. Cash, receivables, payables, and deferred revenue feed the cash forecast and the budget's opening balances.",
  },
  {
    title: "Budget versus actual by dimension",
    body: "Actuals by department or location are compared with the driver-based budget and the latest forecast, with variances explained by the drivers behind them rather than by account alone.",
  },
  {
    title: "Contract and statistical data where you keep it",
    body: "If you manage subscription contracts or record statistical accounts such as headcount in Sage Intacct, SMPL can use that data for ARR and operating metrics alongside the ledger.",
  },
];

const COMBINED = [
  {
    title: "CRM pipeline",
    body: "Opportunities from Salesforce or HubSpot supply pipeline, bookings, and coverage for the revenue forecast.",
  },
  {
    title: "Billing and ARR",
    body: "Subscription data from Maxio, Stripe, Chargebee, or Sage Intacct contracts produces the ARR waterfall and retention next to recognized revenue.",
  },
  {
    title: "Workforce",
    body: "HRIS and payroll data drive the headcount plan, which flows into departmental opex, EBITDA, and cash.",
  },
];

const OUTCOMES = [
  {
    title: "A board package that ties to Sage Intacct",
    body: "ARR, revenue, the three statements, cash, and headcount from one model, with commentary drafted from calculated variances and figures traceable to the ledger.",
  },
  {
    title: "A three-statement budget from drivers",
    body: "Growth, retention, hiring, and spend drivers produce the budgeted income statement, balance sheet, and cash flow, organized by the same dimensions as your actuals.",
  },
  {
    title: "Plans tested before approval",
    body: "Plan Assurance checks the budget against cash floors, coverage, and other constraints, and runs named stress cases before the plan goes to the board.",
  },
  {
    title: "Departmental accountability",
    body: "Budget owners see actuals, budget, and forecast for their department with the same numbers Finance reports to the board.",
  },
];

const STEPS = [
  {
    title: "Agree scope and access",
    body: "We confirm which entities, dimensions, and periods are in scope, and that the extraction method delivers the consolidation context you need. SMPL connects to Sage Intacct with read-only access or works from structured extracts, whichever fits your security requirements.",
  },
  {
    title: "SMPL maps accounts and dimensions",
    body: "SMPL maps your chart of accounts and reporting dimensions to statement lines and the management P&L, and documents each mapping decision for your review.",
  },
  {
    title: "SMPL configures the model",
    body: "Sage Intacct actuals are connected to CRM, billing, and workforce data, with your definitions for ARR, bookings, and departments applied consistently.",
  },
  {
    title: "Validate together",
    body: "SMPL reconciles the imported results to Sage Intacct's consolidated reports and ties ARR to your billing source. Your team reviews the results and confirms definitions.",
  },
  {
    title: "Refresh on your close calendar",
    body: "After go-live, your team initiates each refresh when your books close, on your own close calendar, and can load intra-month cash or pipeline data whenever you need a current view.",
  },
];

const FAQS: Faq[] = [
  {
    q: "Is SMPL.ai an FP&A option for companies on Sage Intacct?",
    a: "Yes. SMPL.ai is FP&A and financial intelligence software for SaaS Finance teams, and it brings Sage Intacct general ledger and dimension data together with CRM, billing, and workforce information for connected reporting, forecasting, budgeting, and Plan Assurance. SMPL leads the integration and implementation, including data mapping, configuration, and financial validation.",
  },
  {
    q: "How does Sage Intacct data get into SMPL.ai?",
    a: "As part of implementation, SMPL either connects to Sage Intacct with read-only access or works from structured extracts, depending on your environment and security requirements. SMPL maps and validates the data. After go-live, your team initiates each refresh when your books close, on your own close calendar, and can load intra-month cash or pipeline data whenever you need a current view.",
  },
  {
    q: "How does SMPL.ai handle Sage Intacct multi-entity consolidation and currencies?",
    a: "SMPL uses Sage Intacct's consolidated financial actuals, including Sage Intacct's currency translation and intercompany elimination adjustments. For USD-reporting companies, SMPL uses the consolidated USD results. Sage Intacct remains the system of record for consolidation: SMPL supports reporting and planning on that consolidated foundation rather than recreating the consolidation engine. During implementation, SMPL confirms that the extraction method delivers the required consolidation context, reconciles the imported results to Sage Intacct's consolidated reports, and scopes the entity-level views you need.",
  },
  {
    q: "Does this page apply to other Sage products?",
    a: "This page describes Sage Intacct, the cloud financial management product used by many SaaS companies. Other Sage accounting products have different data structures. If you use one of them, SMPL confirms the approach for your product during scoping, typically working from structured exports.",
  },
  {
    q: "Does SMPL.ai write back to Sage Intacct?",
    a: "No. SMPL reads from Sage Intacct and does not post journal entries or change records. Sage Intacct remains your system of record for accounting.",
  },
];

export default function SageIntacctIntegrationPage() {
  return (
    <SolutionPage
      category={INTEGRATIONS_CATEGORY}
      crumb={crumb}
      h1="SMPL.ai for Finance teams on Sage Intacct"
      ld={solutionPageLd({ title, url, description, faqs: FAQS, crumb, category: INTEGRATIONS_CATEGORY })}
      faqs={FAQS}
      more={{ title: "More integrations", items: otherIntegrations(path) }}
      secondaryCta={{ href: "/integrations", label: "All integrations" }}
      footnote={trademarkNote("Sage Intacct", "Salesforce", "HubSpot", "Maxio", "Stripe", "Chargebee")}
      related={[
        { href: "/saas-board-reporting", label: "SaaS board reporting" },
        { href: "/budgeting-and-plan-assurance", label: "Budgeting & Plan Assurance" },
        { href: "/integrations/maxio", label: "SMPL.ai for Maxio" },
        { href: "/blog/fpa-software-implementation", label: "Why FP&A implementations shouldn't take months" },
      ]}
      lead={
        <p>
          <strong className="font-semibold text-white">
            SMPL.ai is FP&A and financial intelligence software for SaaS Finance teams that
            run their accounting on Sage Intacct.
          </strong>{" "}
          Bring Sage Intacct financial data and dimensions together with your CRM, billing,
          and workforce information for connected reporting, forecasting, budgeting, and Plan
          Assurance. SMPL leads the integration and implementation, including data mapping,
          configuration, and financial validation.
        </p>
      }
    >
      <Section title="What Sage Intacct data supports in SMPL">
        <p>
          Sage Intacct&apos;s strength is its dimensional ledger: one chart of accounts, with
          department, location, class, and other dimensions carrying the reporting detail. In
          SMPL, that structure drives these workflows.
        </p>
        <PointList items={WORKFLOWS} />
      </Section>

      <Section title="Combined with the rest of your operating data">
        <p>
          The ledger explains what happened financially. SMPL connects it with the systems
          that explain why, so bookings, churn, and hiring flow through revenue, opex, EBITDA,
          and cash together.
        </p>
        <PointList items={COMBINED} />
      </Section>

      <Section title="What you can produce and decide">
        <PointList items={OUTCOMES} />
        <p className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-sm text-slate-400">
          <span className="font-semibold text-slate-200">Illustrative example.</span> A
          company runs a US and a UK entity in Sage Intacct. The management P&L shows Customer
          Success over budget. Tracing the variance to the underlying ledger lines shows it
          sits in the UK entity: two contractors covering open roles in the workforce plan. The forecast replaces the
          contractors with the planned hires from October, and the effect on EBITDA and cash
          is visible before the next board meeting.
        </p>
      </Section>

      <Section title="SMPL leads the implementation">
        <p>
          SMPL takes responsibility for the data integration, mapping, configuration, and
          financial validation. Your team supplies the definitions, reviews the results, and
          makes the decisions. Your Sage Intacct setup stays as it is.
        </p>
        <Steps items={STEPS} />
      </Section>

      <Section title="Discuss your Sage Intacct environment">
        <p>
          Bring a short description of your entities and dimensions, where ARR and
          subscriptions live, which CRM and HRIS you use, and what your board package includes
          today. We will walk through how SMPL would connect it and what your team would see
          at the end of implementation.
        </p>
      </Section>
    </SolutionPage>
  );
}
