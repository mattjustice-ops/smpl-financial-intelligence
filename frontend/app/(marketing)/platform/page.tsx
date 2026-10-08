import type { Metadata } from "next";
import Link from "next/link";

import {
  PointList,
  Section,
  SOLUTIONS,
  SolutionPage,
  solutionPageLd,
  type Faq,
} from "@/components/landing/SolutionPage";
import { SAMPLE_DASHBOARD_URL } from "@/components/landing/constants";
import { DEFAULT_OG_IMAGE, sitePageUrl } from "@/lib/site";

const crumb = "Platform";
const title = "SMPL.ai Platform: SaaS FP&A, Budgeting & Plan Assurance";
const description =
  "Browser-based FP&A for SaaS Finance: connected ERP, CRM, billing, and HR data, board reporting, forecasting, a three-statement budget, and Plan Assurance.";
const url = sitePageUrl("/platform");

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  robots: { index: true, follow: true },
  openGraph: { title, description, url, images: [DEFAULT_OG_IMAGE], type: "website", siteName: "SMPL.ai" },
  twitter: { card: "summary_large_image", title, description },
};

const CAPABILITIES = [
  {
    title: "Connected financial foundation",
    body: "ERP, CRM, billing, and workforce data mapped into one model with your company's definitions for ARR, bookings, departments, and other metrics. SMPL builds this foundation during implementation.",
  },
  {
    title: "Close and board reporting",
    body: "Periods move through load, validate, lock, and freeze. The income statement, management P&L, balance sheet, cash flow, ARR waterfall, and board package come from the same numbers, with a board review deck exported to PowerPoint.",
  },
  {
    title: "AI commentary that is checked against the numbers",
    body: "Commentary is drafted from calculated results and then checked: figures it states are matched against the calculated values, causes it names are checked against the drivers actually present in the data, and unsupported claims are flagged or removed before the text reaches a report.",
  },
  {
    title: "Revenue, retention, and GTM",
    body: "ARR waterfall, net and gross revenue retention, a pipeline waterfall with drill-down to the opportunities behind each movement, bookings coverage, and sales capacity.",
  },
  {
    title: "Forecasting and scenarios",
    body: "Driver-based forecasts where a change in bookings, churn, or hiring flows through ARR, revenue, opex, EBITDA, cash, and runway together.",
  },
  {
    title: "Three-statement budgeting",
    body: "An operating budget calculated from drivers across the income statement, balance sheet, and cash flow statement, with version control from draft to final.",
  },
  {
    title: "Plan Assurance",
    body: "The budget tested against prior-year performance, 15 constraints, named stress cases, and a 1,000-draw simulation of the monthly cash path. The simulation reports stress frequency under stated assumptions, not a calibrated probability of hitting the plan.",
  },
  {
    title: "Workforce and cash planning",
    body: "Headcount and compensation by department feeding opex and cash, and a cash forecast whose lines trace back to the ledger entries behind them.",
  },
];

const TRUST = [
  {
    title: "Deterministic calculation",
    body: "The same inputs and definitions produce the same figures every time. AI explains the results and never computes or edits a financial value.",
  },
  {
    title: "Validation before reporting",
    body: "Closed actuals are checked against statement identities and cross-source tie-outs before a period is locked, and a frozen period stays stable when a source system is corrected later.",
  },
  {
    title: "Traceability",
    body: "Board figures link to the management P&L and from there to the general ledger detail. Pipeline and cash movements drill down to the records behind them.",
  },
  {
    title: "Feasibility kept separate from arithmetic",
    body: "Validation asks whether the numbers are correct. Plan Assurance asks whether the plan can be delivered. SMPL reports the two separately.",
  },
];

const FAQS: Faq[] = [
  {
    q: "What is SMPL.ai?",
    a: "SMPL.ai is a browser-based FP&A and financial intelligence platform for SaaS Finance teams. It connects financial and operating data from ERP, CRM, billing, and workforce systems into one model for reporting, forecasting, budgeting, and Plan Assurance. SMPL leads the implementation, including data integration, mapping, configuration, and financial validation.",
  },
  {
    q: "Do we have to model in spreadsheets to use SMPL.ai?",
    a: "No. SMPL is a browser-based platform and the model lives in the platform, not in a spreadsheet. Board decks export to PowerPoint.",
  },
  {
    q: "Who is SMPL.ai for?",
    a: "Growing SaaS companies whose financial and operating data is spread across several systems and whose reporting and planning needs have become more demanding: board reporting, revenue complexity, workforce planning, cash visibility, and connected forecasts. That includes smaller Finance teams and established Finance organizations that need more capacity.",
  },
  {
    q: "Does SMPL.ai replace our ERP?",
    a: "No. SMPL reads from your ERP, CRM, billing platform, and HRIS and does not write back to them. Each remains the system of record for its domain.",
  },
];

export default function PlatformPage() {
  return (
    <SolutionPage
      category={null}
      crumb={crumb}
      h1="The SMPL.ai platform"
      ld={solutionPageLd({ title, url, description, faqs: FAQS, crumb, category: null })}
      faqs={FAQS}
      more={{ title: "Explore by need", items: SOLUTIONS }}
      related={[
        { href: "/fpa-software-for-saas", label: "FP&A software for SaaS companies" },
        { href: "/blog/best-fpa-software-saas-companies", label: "Best FP&A software for SaaS companies" },
        { href: "/integrations/salesforce", label: "Salesforce integration" },
        { href: SAMPLE_DASHBOARD_URL, label: "View the sample board" },
        { href: "/blog/ai-variance-commentary-cfo-standard", label: "What CFOs should demand from AI variance commentary" },
        { href: "/about", label: "About SMPL.ai" },
      ]}
      lead={
        <p>
          <strong className="font-semibold text-white">
            SMPL.ai is a browser-based FP&A and financial intelligence platform for SaaS
            Finance teams.
          </strong>{" "}
          It is a unified SaaS operating model that connects financial and operating data for
          reporting, forecasting, budgeting, and Plan Assurance. Finance keeps its definitions,
          methodology, and decisions; SMPL leads the implementation and provides the connected
          financial foundation.
        </p>
      }
    >
      <Section title="What is in the platform">
        <PointList items={CAPABILITIES} />
      </Section>

      <Section title="How the numbers stay trustworthy">
        <PointList items={TRUST} />
      </Section>

      <Section title="Implementation is part of the platform">
        <p>
          SMPL connects your ERP, CRM, billing, and workforce systems, maps the data, configures
          the model with your definitions, and reconciles the results to your source systems.
          Your team provides access, definitions, review, and decisions. See{" "}
          <Link href="/integrations" className="text-teal-300 underline-offset-2 hover:underline">
            integrations and implementation
          </Link>{" "}
          for the systems SMPL works with, including{" "}
          <Link href="/integrations/salesforce" className="text-teal-300 underline-offset-2 hover:underline">
            Salesforce
          </Link>
          , and how the connection is delivered. For how these platforms compare, see the{" "}
          <Link
            href="/blog/best-fpa-software-saas-companies"
            className="text-teal-300 underline-offset-2 hover:underline"
          >
            buyer&apos;s guide to FP&A software for SaaS companies
          </Link>
          .
        </p>
      </Section>
    </SolutionPage>
  );
}
