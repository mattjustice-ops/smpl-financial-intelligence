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

const path = "/integrations/netsuite";
const crumb = "NetSuite";
const title = "NetSuite FP&A, Reporting & Planning Software | SMPL.ai";
const description =
  "SMPL.ai combines NetSuite GL data with CRM, billing, and workforce data for SaaS reporting, forecasting, budgets, and Plan Assurance, implemented by SMPL.";
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
    title: "Financial statements from the posted ledger",
    body: "Posted GL activity by account and period becomes the income statement, balance sheet, and cash flow statement. Closed periods are checked against statement identities before they are locked, so the board version ties to what NetSuite shows.",
  },
  {
    title: "Built on NetSuite's consolidated results",
    body: "For multi-subsidiary companies, SMPL uses NetSuite's consolidated financial actuals, including the currency translation and intercompany elimination adjustments NetSuite has already made. For USD-reporting companies, that means the consolidated USD results. NetSuite remains the system of record for consolidation, and SMPL builds reporting and planning on that foundation rather than recreating the consolidation engine. Entity and currency information is retained, and subsidiary views are scoped during implementation.",
  },
  {
    title: "A management P&L that follows your structure",
    body: "Departments, classes, locations, and subsidiaries are mapped to the management view your leadership team uses. Allocations appear as a bridge between the income statement and the management P&L, so totals stay equal while costs move between functions.",
  },
  {
    title: "Budget versus actual by department",
    body: "NetSuite actuals sit alongside a driver-based budget and the latest forecast. Variances are calculated at the account and department level and explained by the drivers behind them, such as hiring timing or program spend.",
  },
  {
    title: "Cash and the balance sheet",
    body: "Cash, receivables, payables, and deferred revenue balances feed the cash forecast and the budget's opening balances. A cash bridge line can be traced back to the GL entries that make it up.",
  },
  {
    title: "Opex and vendor spend",
    body: "Expense lines by department and vendor show where spend is running ahead of plan and connect to the headcount plan, so payroll and non-payroll cost are planned in one place.",
  },
];

const COMBINED = [
  {
    title: "CRM pipeline for bookings",
    body: "Opportunities from Salesforce or HubSpot supply pipeline, bookings, and coverage. NetSuite shows the revenue that was recognized; the CRM shows what is likely to close next.",
  },
  {
    title: "Billing data for ARR",
    body: "ARR is not in the general ledger. Subscription data from Maxio, Stripe, Chargebee, or NetSuite itself if you bill there supplies the ARR waterfall that sits next to recognized revenue.",
  },
  {
    title: "Workforce data for headcount and payroll",
    body: "Employee and compensation data from your HRIS or payroll system drives the headcount plan, which then flows into opex, EBITDA, and cash.",
  },
];

const OUTCOMES = [
  {
    title: "A board package that ties to the ledger",
    body: "ARR, revenue, the three statements, cash, and headcount come from one model, with commentary drafted from calculated variances and each figure traceable to its source.",
  },
  {
    title: "A three-statement budget built from drivers",
    body: "The operating budget produces an income statement, balance sheet, and cash flow statement from growth, retention, hiring, and spend drivers, starting from NetSuite's prior-year ending balances.",
  },
  {
    title: "Plans tested before they are approved",
    body: "Plan Assurance checks the budget against cash floors, coverage, and other constraints, and runs named stress cases, so you can see which assumption breaks first.",
  },
  {
    title: "Faster answers to leadership questions",
    body: "Why did margin move? Can we afford two more engineers in Q3? What happens to runway if bookings slip a quarter? Each answer draws on NetSuite actuals and the operating data around them.",
  },
];

const STEPS = [
  {
    title: "Agree scope and access",
    body: "We confirm which subsidiaries, periods, and dimensions matter, and that the extraction method delivers the consolidation context you need. Your NetSuite administrator grants read-only access or sets up structured extracts, whichever fits your security requirements.",
  },
  {
    title: "SMPL maps the ledger",
    body: "SMPL maps your chart of accounts, departments, classes, and subsidiaries to statement lines and the management P&L, and documents every mapping decision for your review.",
  },
  {
    title: "SMPL configures the model",
    body: "SMPL connects NetSuite actuals to your CRM, billing, and workforce data and applies your company's definitions for ARR, bookings, and departments.",
  },
  {
    title: "Validate together",
    body: "SMPL reconciles the imported results to NetSuite's consolidated reports and ties ARR and cash back to your other systems. Your team reviews the results and confirms definitions.",
  },
  {
    title: "Refresh on your close calendar",
    body: "After go-live, your team initiates each refresh when your books close, on your own close calendar, and can load intra-month cash or pipeline data whenever you need a current view.",
  },
];

const FAQS: Faq[] = [
  {
    q: "Is SMPL.ai a good FP&A tool for companies on NetSuite?",
    a: "SMPL.ai is FP&A software for SaaS Finance teams, and NetSuite is one of the most common general ledgers it works with. SMPL brings NetSuite financial data together with CRM, billing, and workforce information for connected reporting, forecasting, budgeting, and Plan Assurance. SMPL leads the integration and implementation, including data mapping, configuration, and financial validation.",
  },
  {
    q: "How does NetSuite data get into SMPL.ai?",
    a: "As part of implementation, SMPL either connects to NetSuite with read-only access or works from structured extracts, depending on your environment and security requirements. SMPL maps and validates the data. After go-live, your team initiates each refresh when your books close, on your own close calendar, and can load intra-month cash or pipeline data whenever you need a current view.",
  },
  {
    q: "Does SMPL.ai write anything back to NetSuite?",
    a: "No. SMPL reads from NetSuite and does not post journal entries or change records. NetSuite remains your system of record for accounting.",
  },
  {
    q: "Can SMPL.ai report on NetSuite subsidiaries and departments?",
    a: "Yes. Subsidiaries, departments, classes, and locations are mapped during implementation so that the financial statements, the management P&L, and the budget follow the structure your leadership team reports on. Entity and currency information is retained, and the subsidiary views you need are scoped during implementation.",
  },
  {
    q: "How does SMPL.ai handle NetSuite consolidation and multiple currencies?",
    a: "SMPL uses NetSuite's consolidated financial actuals, including NetSuite's currency translation and intercompany elimination adjustments. For USD-reporting companies, SMPL uses the consolidated USD results. NetSuite remains the system of record for consolidation: SMPL supports reporting and planning on that consolidated foundation rather than recreating NetSuite's consolidation engine. During implementation, SMPL confirms that the extraction method delivers the required consolidation context and reconciles the imported results to NetSuite's consolidated reports.",
  },
  {
    q: "What does our Finance team need to do during implementation?",
    a: "Grant access or provide extracts, explain how your company defines its metrics and reporting structure, review the mappings SMPL proposes, and validate the first results. SMPL does the mapping, configuration, and reconciliation work.",
  },
];

export default function NetSuiteIntegrationPage() {
  return (
    <SolutionPage
      category={INTEGRATIONS_CATEGORY}
      crumb={crumb}
      h1="SMPL.ai for Finance teams on NetSuite"
      ld={solutionPageLd({ title, url, description, faqs: FAQS, crumb, category: INTEGRATIONS_CATEGORY })}
      faqs={FAQS}
      more={{ title: "More integrations", items: otherIntegrations(path) }}
      secondaryCta={{ href: "/integrations", label: "All integrations" }}
      footnote={trademarkNote("NetSuite", "Salesforce", "HubSpot", "Maxio", "Stripe", "Chargebee")}
      related={[
        { href: "/integrations/netsuite-salesforce", label: "NetSuite and Salesforce together" },
        { href: "/saas-board-reporting", label: "SaaS board reporting" },
        { href: "/budgeting-and-plan-assurance", label: "Budgeting & Plan Assurance" },
        { href: "/blog/fpa-software-implementation", label: "Why FP&A implementations shouldn't take months" },
      ]}
      lead={
        <p>
          <strong className="font-semibold text-white">
            SMPL.ai is FP&A and financial intelligence software for SaaS Finance teams that
            run their accounting on NetSuite.
          </strong>{" "}
          Bring NetSuite financial data together with your CRM, billing, and workforce
          information for connected reporting, forecasting, budgeting, and Plan Assurance.
          SMPL leads the integration and implementation, including data mapping,
          configuration, and financial validation.
        </p>
      }
    >
      <Section title="What NetSuite data supports in SMPL">
        <p>
          NetSuite holds the posted financial record: the general ledger, the chart of
          accounts, and the subsidiary, department, class, and location dimensions your
          reporting is organized around. In SMPL, that record drives these workflows.
        </p>
        <PointList items={WORKFLOWS} />
      </Section>

      <Section title="Combined with the rest of your operating data">
        <p>
          NetSuite explains what happened financially. The reasons usually sit in other
          systems. SMPL connects them in one model, so a change in bookings, churn, or hiring
          shows up in revenue, opex, EBITDA, and cash at the same time.
        </p>
        <PointList items={COMBINED} />
      </Section>

      <Section title="What you can produce and decide">
        <PointList items={OUTCOMES} />
        <p className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-sm text-slate-400">
          <span className="font-semibold text-slate-200">Illustrative example.</span> March
          closes in NetSuite. Operating expense is 6% over budget in the management P&L. The
          variance traces to two causes: contractor spend in Marketing, and a sales hire whose
          start date moved a month earlier in the workforce plan. The same hire also lowers
          the June cash low point in the forecast, so the CFO sees the cost and the cash
          effect together before the board meeting.
        </p>
      </Section>

      <Section title="SMPL leads the implementation">
        <p>
          Implementation is part of what SMPL provides, not a project your team has to staff.
          SMPL takes responsibility for the data integration, mapping, configuration, and
          financial validation. Your team supplies the definitions, reviews the results, and
          makes the decisions.
        </p>
        <Steps items={STEPS} />
      </Section>

      <Section title="Discuss your NetSuite environment">
        <p>
          Bring a short description of your stack: which subsidiaries you report on, where
          ARR and subscriptions live, which CRM and HRIS you use, and what your board package
          includes today. We will walk through how SMPL would connect it and what your team
          would see at the end of implementation.
        </p>
      </Section>
    </SolutionPage>
  );
}
