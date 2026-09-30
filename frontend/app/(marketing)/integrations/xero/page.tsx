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

const path = "/integrations/xero";
const crumb = "Xero";
const title = "Xero FP&A, SaaS Reporting & Cash Planning | SMPL.ai";
const description =
  "SMPL.ai combines Xero with billing, CRM, and payroll data for SaaS metrics, cash planning, a three-statement budget, and board reporting, implemented by SMPL.";
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
    title: "Financial statements from Xero",
    body: "Accounts, manual journals, invoices, and bills become the income statement, balance sheet, and cash flow statement, reported the same way every month.",
  },
  {
    title: "Departmental reporting from tracking categories",
    body: "Xero tracking categories, often used for department or region, are mapped to the management P&L so spend can be reviewed by function rather than only by account.",
  },
  {
    title: "Cash position and runway",
    body: "Bank transactions, receivables, and payables give a current cash position, which becomes the starting point for a monthly cash forecast and runway that respond to hiring and bookings.",
  },
  {
    title: "Budget versus actual",
    body: "Xero actuals sit alongside a driver-based budget and forecast, with variances explained by the drivers behind them.",
  },
];

const COMBINED = [
  {
    title: "Billing for ARR and retention",
    body: "Xero records invoices but not subscription movements. Billing data from Stripe, Chargebee, Maxio, or another platform supplies the ARR waterfall, churn, and retention.",
  },
  {
    title: "CRM for pipeline",
    body: "Deals from HubSpot or Salesforce supply pipeline and expected bookings for the revenue forecast.",
  },
  {
    title: "Payroll and HR for headcount",
    body: "Employee and compensation data from your payroll or HR system, such as Gusto, Rippling, or Deel, drives the headcount plan and its effect on opex and cash.",
  },
];

const OUTCOMES = [
  {
    title: "SaaS metrics next to the ledger",
    body: "ARR, net and gross revenue retention, and churn reported next to recognized revenue from Xero, with the reasons they differ explained.",
  },
  {
    title: "A three-statement budget",
    body: "A driver-based budget across the income statement, balance sheet, and cash flow statement, starting from Xero's ending balances.",
  },
  {
    title: "Cash decisions made early",
    body: "Plan Assurance shows the monthly cash low point and how it moves under stress cases, so a financing or hiring decision is made before cash gets tight.",
  },
  {
    title: "Investor and board reporting",
    body: "A consistent monthly package with ARR, the statements, cash, and headcount from one model, and commentary drafted from calculated variances.",
  },
];

const STEPS = [
  {
    title: "Agree scope and access",
    body: "We confirm which Xero organisations, tracking categories, and periods are in scope. SMPL connects to Xero with read-only access or works from structured exports.",
  },
  {
    title: "SMPL maps the accounts",
    body: "SMPL maps your chart of accounts and tracking categories to statement lines and the management P&L, and documents each decision for your review.",
  },
  {
    title: "SMPL connects billing, CRM, and payroll",
    body: "Subscription, pipeline, and headcount data are mapped to the same customers, departments, and months as your Xero actuals.",
  },
  {
    title: "Validate together",
    body: "SMPL ties the statements and cash to Xero and ARR to your billing source. Your team reviews the results and confirms definitions.",
  },
  {
    title: "Run on your reporting cadence",
    body: "Reporting data is kept current on the refresh arrangement agreed during implementation, aligned to your close and board calendar.",
  },
];

const FAQS: Faq[] = [
  {
    q: "What FP&A software works for SaaS companies on Xero?",
    a: "SMPL.ai is FP&A and financial intelligence software for SaaS Finance teams, and it brings Xero accounting data together with billing, CRM, and workforce information for SaaS metrics, cash planning, budgeting, Plan Assurance, and board reporting. SMPL leads the integration and implementation, including data mapping, configuration, and financial validation.",
  },
  {
    q: "How does Xero data get into SMPL.ai?",
    a: "As part of implementation, SMPL either connects to Xero with read-only access or works from structured exports. SMPL maps and validates the data, and the reporting data is kept current on the refresh cadence agreed during implementation.",
  },
  {
    q: "Can SMPL.ai calculate ARR if our ledger is Xero?",
    a: "Yes, using subscription data from your billing platform. Xero records invoices and revenue, while ARR, churn, and expansion come from subscription movements. SMPL combines both and reports ARR next to recognized revenue.",
  },
  {
    q: "We run more than one Xero organisation. Does that work?",
    a: "Yes. Each Xero organisation is mapped during implementation, and the reporting structure for entity-level and combined views is agreed with your team during scoping.",
  },
];

export default function XeroIntegrationPage() {
  return (
    <SolutionPage
      category={INTEGRATIONS_CATEGORY}
      crumb={crumb}
      h1="SMPL.ai for Finance teams on Xero"
      ld={solutionPageLd({ title, url, description, faqs: FAQS, crumb, category: INTEGRATIONS_CATEGORY })}
      faqs={FAQS}
      more={{ title: "More integrations", items: otherIntegrations(path) }}
      secondaryCta={{ href: "/integrations", label: "All integrations" }}
      footnote={trademarkNote("Xero", "Stripe", "Chargebee", "Maxio", "HubSpot", "Salesforce", "Gusto", "Rippling", "Deel")}
      related={[
        { href: "/arr-revenue-cash-headcount", label: "ARR, revenue, cash & headcount in one model" },
        { href: "/blog/saas-cash-forecasting", label: "SaaS cash forecasting" },
        { href: "/budgeting-and-plan-assurance", label: "Budgeting & Plan Assurance" },
        { href: "/fpa-software-for-lean-finance-teams", label: "FP&A for lean Finance teams" },
      ]}
      lead={
        <p>
          <strong className="font-semibold text-white">
            SMPL.ai is FP&A and financial intelligence software for SaaS Finance teams that
            keep their books in Xero.
          </strong>{" "}
          Bring Xero accounting data together with your billing, CRM, and workforce
          information for SaaS metrics, cash planning, a three-statement budget, and board
          reporting. SMPL leads the integration and implementation, including data mapping,
          configuration, and financial validation.
        </p>
      }
    >
      <Section title="What Xero data supports in SMPL">
        <p>
          Xero holds the accounting record: the chart of accounts, invoices, bills, bank
          transactions, journals, and the tracking categories many companies use for
          departments or regions. In SMPL, that record drives these workflows.
        </p>
        <PointList items={WORKFLOWS} />
      </Section>

      <Section title="Combined with the rest of your operating data">
        <p>
          The metrics investors ask a SaaS company for are not in the ledger. SMPL connects
          Xero to the systems that hold them, in one model.
        </p>
        <PointList items={COMBINED} />
      </Section>

      <Section title="What you can produce and decide">
        <PointList items={OUTCOMES} />
        <p className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-sm text-slate-400">
          <span className="font-semibold text-slate-200">Illustrative example.</span> A
          company bills monthly through Stripe and keeps its books in Xero. ARR grew 8% in the
          quarter, but cash fell faster than expected. The model shows that three larger
          customers moved from annual prepayment to monthly billing at renewal. Revenue is
          unchanged, but the cash forecast now shows a lower low point in November, and the
          hiring plan is resequenced accordingly.
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

      <Section title="Discuss your Xero environment">
        <p>
          Bring a short description of your Xero setup, where subscriptions and billing live,
          which CRM and payroll systems you use, and what your investors or board ask for
          today. We will walk through how SMPL would connect it and what your team would see
          at the end of implementation.
        </p>
      </Section>
    </SolutionPage>
  );
}
