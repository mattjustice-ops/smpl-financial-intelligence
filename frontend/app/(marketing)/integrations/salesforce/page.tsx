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

const path = "/integrations/salesforce";
const crumb = "Salesforce";
const title = "Salesforce Pipeline for SaaS Revenue Forecasting & FP&A | SMPL.ai";
const description =
  "SMPL.ai combines Salesforce pipeline with billing and ledger data for bookings and revenue forecasts, GTM capacity plans, and board reporting, implemented by SMPL.";
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
    title: "Pipeline waterfall",
    body: "Opportunity amounts, stages, and close dates become a monthly pipeline waterfall: pipeline created, closed won, closed lost, and slipped. Clicking a movement shows the opportunities behind it.",
  },
  {
    title: "Bookings forecast and coverage",
    body: "Open pipeline by stage and close month is compared with the bookings the plan requires, so coverage gaps show up by quarter rather than at quarter end.",
  },
  {
    title: "Revenue forecasting from pipeline and existing ARR",
    body: "Expected new bookings are combined with the ARR already under contract, renewal timing, and churn assumptions to forecast ARR, recognized revenue, and cash by month.",
  },
  {
    title: "GTM capacity and efficiency",
    body: "Quota, ramp, and attrition assumptions for account executives translate into bookings capacity. Pipeline created is set against sales and marketing spend from the ledger to show efficiency by period.",
  },
];

const COMBINED = [
  {
    title: "Billing data for actual ARR",
    body: "Salesforce shows what sales believes was sold. Billing data from Maxio, Stripe, Chargebee, or your ERP shows what customers are actually subscribed to. SMPL reports ARR from billing and shows the bridge to CRM bookings.",
  },
  {
    title: "General ledger for revenue and spend",
    body: "Recognized revenue and sales and marketing expense come from NetSuite, Sage Intacct, QuickBooks Online, or another ledger, so pipeline and bookings sit next to the financial results they produce.",
  },
  {
    title: "Workforce data for sales capacity",
    body: "Account executive and customer success headcount, start dates, and attrition come from the HRIS, so the capacity behind the bookings plan reflects the team you actually have.",
  },
];

const OUTCOMES = [
  {
    title: "A bookings plan the pipeline can support",
    body: "See whether current and expected pipeline covers next quarter's bookings target, and which segment or month falls short.",
  },
  {
    title: "Hiring decisions tied to capacity and cash",
    body: "Model adding or delaying account executives and see the effect on bookings capacity, operating expense, and runway together.",
  },
  {
    title: "A board pipeline view that reconciles",
    body: "Pipeline, bookings, and ARR on the board slides come from one model, and a closed-won figure can be traced to the opportunities that make it up.",
  },
  {
    title: "Budget drivers grounded in CRM history",
    body: "Win rates, cycle times, and pipeline coverage from Salesforce history inform the driver-based budget, and Plan Assurance tests whether the GTM plan is feasible.",
  },
];

const STEPS = [
  {
    title: "Agree scope and access",
    body: "We confirm which record types, stages, and fields your team relies on. SMPL connects to Salesforce with read-only access or works from report exports, whichever fits your security requirements.",
  },
  {
    title: "SMPL maps opportunities",
    body: "SMPL maps opportunity types, stages, amount fields, and custom fields to new business, expansion, and renewal, and matches Salesforce accounts to billing customers.",
  },
  {
    title: "SMPL configures the model",
    body: "Pipeline is connected to ARR, the ledger, and workforce data, and your definitions for bookings and coverage are applied consistently.",
  },
  {
    title: "Validate together",
    body: "SMPL ties closed-won bookings to new ARR in billing and pipeline totals to Salesforce reports. Your team reviews the differences and confirms the treatment.",
  },
  {
    title: "Refresh on your close calendar",
    body: "After go-live, your team initiates each refresh when your books close, on your own close calendar, and can load pipeline data intra-month whenever you need a current view of bookings and coverage.",
  },
];

const FAQS: Faq[] = [
  {
    q: "What FP&A software uses Salesforce pipeline for revenue forecasting?",
    a: "SMPL.ai is FP&A software for SaaS Finance teams that uses Salesforce opportunities and pipeline together with billing, general ledger, and workforce data for bookings and revenue forecasting, GTM capacity planning, budgeting, and board reporting. SMPL leads the integration and implementation, including data mapping, configuration, and financial validation.",
  },
  {
    q: "Why not report ARR directly from Salesforce?",
    a: "CRM amounts describe what sales expects the book to look like, and they can be recorded before a subscription exists or change meaning between fields. SMPL uses Salesforce for pipeline, bookings, and coverage, reports ending ARR from billing, and shows the bridge between them when leadership asks why they differ.",
  },
  {
    q: "How does Salesforce data get into SMPL.ai?",
    a: "As part of implementation, SMPL either connects to Salesforce with read-only access or works from structured report exports. SMPL maps and validates the data. After go-live, your team initiates each refresh when your books close, on your own close calendar, and can load pipeline data intra-month whenever you need a current view.",
  },
  {
    q: "Can SMPL.ai handle our custom stages and fields?",
    a: "Yes. Stage names, record types, and custom amount fields differ between companies, and SMPL maps yours during implementation rather than asking you to change your Salesforce setup.",
  },
  {
    q: "Does SMPL.ai work with HubSpot instead of Salesforce?",
    a: "Yes. HubSpot deals and pipelines support the same pipeline, bookings, and forecasting workflows, and SMPL leads that integration in the same way.",
  },
];

export default function SalesforceIntegrationPage() {
  return (
    <SolutionPage
      category={INTEGRATIONS_CATEGORY}
      crumb={crumb}
      h1="SMPL.ai for Finance teams using Salesforce"
      ld={solutionPageLd({ title, url, description, faqs: FAQS, crumb, category: INTEGRATIONS_CATEGORY })}
      faqs={FAQS}
      more={{ title: "More integrations", items: otherIntegrations(path) }}
      secondaryCta={{ href: "/integrations", label: "All integrations" }}
      footnote={trademarkNote("Salesforce", "HubSpot", "Maxio", "Stripe", "Chargebee", "NetSuite", "Sage Intacct", "QuickBooks Online")}
      related={[
        { href: "/integrations/netsuite-salesforce", label: "NetSuite and Salesforce together" },
        { href: "/blog/saas-revenue-forecasting-arr-bookings-gaap", label: "SaaS revenue forecasting" },
        { href: "/blog/billing-vs-crm-arr", label: "Billing ARR vs CRM ARR" },
        { href: "/budgeting-and-plan-assurance", label: "Budgeting & Plan Assurance" },
      ]}
      lead={
        <p>
          <strong className="font-semibold text-white">
            SMPL.ai is FP&A and financial intelligence software for SaaS Finance teams whose
            pipeline lives in Salesforce.
          </strong>{" "}
          Bring Salesforce opportunities together with billing, general ledger, and workforce
          data for bookings and revenue forecasting, GTM capacity planning, budgeting, and
          board reporting. SMPL leads the integration and implementation, including data
          mapping, configuration, and financial validation.
        </p>
      }
    >
      <Section title="What Salesforce data supports in SMPL">
        <p>
          Salesforce is where the commercial story starts: accounts, opportunities, stages,
          amounts, close dates, and products, usually before any accounting entry exists. In
          SMPL, that data drives these workflows.
        </p>
        <PointList items={WORKFLOWS} />
      </Section>

      <Section title="Combined with the rest of your operating data">
        <p>
          Pipeline on its own is a forecast of intent. Connected to billing, the ledger, and
          the workforce plan, it becomes a revenue and cash forecast Finance can defend.
        </p>
        <PointList items={COMBINED} />
      </Section>

      <Section title="What you can produce and decide">
        <PointList items={OUTCOMES} />
        <p className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-sm text-slate-400">
          <span className="font-semibold text-slate-200">Illustrative example.</span> The
          plan needs $2.0M of new ARR in Q3. Salesforce shows enough total pipeline, but
          most of it sits in early stages with close dates in September, and two of eight
          account executives are still ramping. The pipeline waterfall shows how much slipped
          out of Q2, and the forecast shifts expected bookings, revenue, and cash into Q4
          before the board sees a missed quarter.
        </p>
      </Section>

      <Section title="SMPL leads the implementation">
        <p>
          SMPL takes responsibility for the data integration, mapping, configuration, and
          financial validation. Your team, including RevOps where it owns Salesforce, explains
          how stages and fields are used, reviews the results, and makes the decisions.
        </p>
        <Steps items={STEPS} />
      </Section>

      <Section title="Discuss your Salesforce environment">
        <p>
          Bring a short description of how your team uses Salesforce opportunities, where
          billing and the general ledger live, and how pipeline appears in your board package
          today. We will walk through how SMPL would connect it and what your team would see
          at the end of implementation.
        </p>
      </Section>
    </SolutionPage>
  );
}
