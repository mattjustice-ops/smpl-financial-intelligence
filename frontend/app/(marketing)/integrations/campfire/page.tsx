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

const path = "/integrations/campfire";
const crumb = "Campfire";
const title = "FP&A, Budgeting & Planning for Campfire Customers | SMPL.ai";
const description =
  "SMPL.ai combines Campfire accounting data with CRM, billing, and workforce data for SaaS budgeting, forecasting, and board reporting, implemented by SMPL.";
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
    title: "From close to board package",
    body: "Once a period closes in Campfire, the posted results become the income statement, balance sheet, and cash flow statement in SMPL, with the management P&L, SaaS metrics, and commentary built on the same numbers.",
  },
  {
    title: "Entity and department structure",
    body: "Entities, departments, and other reporting fields in Campfire are mapped during implementation, so reporting and the budget follow the structure leadership reviews.",
  },
  {
    title: "Revenue and deferred revenue",
    body: "Where revenue is recognized in Campfire, recognized and deferred revenue feed the ARR-to-revenue bridge and the revenue schedule in the forecast.",
  },
  {
    title: "Opening balances for the plan",
    body: "Year-end cash and balance sheet positions become the opening balances of the operating budget, so the plan starts from the ledger rather than a hand-keyed number.",
  },
];

const COMBINED = [
  {
    title: "CRM pipeline",
    body: "Opportunities from Salesforce or HubSpot supply pipeline, bookings, and coverage for the revenue forecast and the GTM plan.",
  },
  {
    title: "Billing and ARR",
    body: "Subscription data from Stripe, Chargebee, Maxio, or another billing platform produces the ARR waterfall and retention alongside Campfire revenue.",
  },
  {
    title: "Workforce",
    body: "HRIS and payroll data drive the headcount plan, which flows into opex, EBITDA, and cash.",
  },
];

const OUTCOMES = [
  {
    title: "A driver-based, three-statement budget",
    body: "Growth, retention, hiring, and spend drivers produce the budgeted income statement, balance sheet, and cash flow by month.",
  },
  {
    title: "Plan Assurance before the board sees the plan",
    body: "The budget is checked against cash floors, coverage, and other constraints, and run through named stress cases and a simulation of the monthly cash path.",
  },
  {
    title: "Workforce and cash decisions together",
    body: "See how a hiring plan changes opex, EBITDA, and the monthly cash low point before approving it.",
  },
  {
    title: "Board reporting that ties",
    body: "ARR, revenue, statements, cash, and headcount from one model, with commentary drafted from calculated variances and traceable to source.",
  },
];

const STEPS = [
  {
    title: "Agree scope and access",
    body: "We confirm entities, periods, and reporting fields. SMPL connects to Campfire with read-only access where available or works from structured exports.",
  },
  {
    title: "SMPL maps the ledger",
    body: "SMPL maps your chart of accounts and reporting fields to statement lines and the management P&L, and documents each decision for your review.",
  },
  {
    title: "SMPL connects the rest of the stack",
    body: "CRM, billing, and workforce data are mapped to the same customers, departments, and months.",
  },
  {
    title: "Validate together",
    body: "SMPL ties the statements and cash to Campfire and ARR to your billing source. Your team reviews the results and confirms definitions.",
  },
  {
    title: "Refresh on your close calendar",
    body: "After go-live, your team initiates each refresh when your books close, on your own close calendar, and can load intra-month cash or pipeline data whenever you need a current view.",
  },
];

const FAQS: Faq[] = [
  {
    q: "What FP&A software works with Campfire?",
    a: "SMPL.ai is FP&A and financial intelligence software for SaaS Finance teams, and it brings Campfire accounting data together with CRM, billing, and workforce information for budgeting, forecasting, Plan Assurance, and board reporting. SMPL leads the integration and implementation, including data mapping, configuration, and financial validation.",
  },
  {
    q: "How does Campfire data get into SMPL.ai?",
    a: "As part of implementation, SMPL connects to Campfire with read-only access where available or works from structured exports. SMPL maps and validates the data. After go-live, your team initiates each refresh when your books close, on your own close calendar, and can load intra-month cash or pipeline data whenever you need a current view.",
  },
  {
    q: "Campfire handles our close. What does SMPL.ai add?",
    a: "Campfire records and closes the books. SMPL takes the closed results and connects them to pipeline, subscriptions, and the workforce plan for forecasting, the three-statement budget, Plan Assurance, and the board package.",
  },
  {
    q: "Does SMPL.ai write back to Campfire?",
    a: "No. SMPL reads from Campfire and does not post entries or change records. Campfire remains your system of record for accounting.",
  },
];

export default function CampfireIntegrationPage() {
  return (
    <SolutionPage
      category={INTEGRATIONS_CATEGORY}
      crumb={crumb}
      h1="SMPL.ai for Finance teams on Campfire"
      ld={solutionPageLd({ title, url, description, faqs: FAQS, crumb, category: INTEGRATIONS_CATEGORY })}
      faqs={FAQS}
      more={{ title: "More integrations", items: otherIntegrations(path) }}
      secondaryCta={{ href: "/integrations", label: "All integrations" }}
      footnote={trademarkNote("Campfire", "Salesforce", "HubSpot", "Stripe", "Chargebee", "Maxio")}
      related={[
        { href: "/budgeting-and-plan-assurance", label: "Budgeting & Plan Assurance" },
        { href: "/saas-board-reporting", label: "SaaS board reporting" },
        { href: "/arr-revenue-cash-headcount", label: "ARR, revenue, cash & headcount in one model" },
        { href: "/blog/fpa-software-implementation", label: "Why FP&A implementations shouldn't take months" },
      ]}
      lead={
        <p>
          <strong className="font-semibold text-white">
            SMPL.ai is FP&A and financial intelligence software for SaaS Finance teams that
            run their accounting on Campfire.
          </strong>{" "}
          Bring Campfire accounting data together with your CRM, billing, and workforce
          information for connected budgeting, forecasting, Plan Assurance, and board
          reporting. SMPL leads the integration and implementation, including data mapping,
          configuration, and financial validation.
        </p>
      }
    >
      <Section title="What Campfire data supports in SMPL">
        <p>
          Campfire is an accounting and ERP platform adopted by growing companies, including
          SaaS businesses, to run the general ledger and the close. In SMPL, the closed
          results drive these workflows.
        </p>
        <PointList items={WORKFLOWS} />
      </Section>

      <Section title="Combined with the rest of your operating data">
        <p>
          A faster close gives Finance more time. Planning puts that time to use, and it needs
          the systems that describe what happens next.
        </p>
        <PointList items={COMBINED} />
      </Section>

      <Section title="What you can produce and decide">
        <PointList items={OUTCOMES} />
        <p className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-sm text-slate-400">
          <span className="font-semibold text-slate-200">Illustrative example.</span> The
          draft budget adds twelve hires and ends December with cash above the floor. Plan
          Assurance shows that if new-business growth lands three points lower, cash dips
          below the floor in August, and names the sales capacity constraint that fails first.
          The team moves four hires to the second half before the plan is approved.
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

      <Section title="Discuss your Campfire environment">
        <p>
          Bring a short description of your entities, where subscriptions are billed, which
          CRM and HRIS you use, and how you plan and report to the board today. We will walk
          through how SMPL would connect it and what your team would see at the end of
          implementation.
        </p>
      </Section>
    </SolutionPage>
  );
}
