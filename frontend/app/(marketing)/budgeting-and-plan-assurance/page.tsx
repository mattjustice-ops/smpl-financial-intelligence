import type { Metadata } from "next";
import Link from "next/link";

import {
  PointList,
  Section,
  SolutionPage,
  Steps,
  solutionPageLd,
  type Faq,
} from "@/components/landing/SolutionPage";
import { sitePageUrl } from "@/lib/site";

const crumb = "Budgeting & Plan Assurance";
const title = "SaaS Budgeting Software with Plan Stress Testing | SMPL.ai";
const description =
  "Driver-based SaaS budgeting across the income statement, balance sheet, and cash flow, tested with Plan Assurance: 15 constraints, stress cases, and a cash simulation.";
const url = sitePageUrl("/budgeting-and-plan-assurance");

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  robots: { index: true, follow: true },
  openGraph: { title, description, url, type: "website", siteName: "SMPL.ai" },
  twitter: { title, description },
};

const DRIVERS = [
  {
    title: "Growth and retention",
    body: "Ending ARR growth, net new ARR by month, churn and contraction mix, and retention floors.",
  },
  {
    title: "Go-to-market",
    body: "Pipeline coverage, marketing spend, cost per lead, channel mix, and lead targets.",
  },
  {
    title: "Sales capacity",
    body: "Account executive and customer success headcount, quota, ramp, attrition, and the hiring plan by month.",
  },
  {
    title: "Cost and cash",
    body: "Departmental operating expense, EBITDA targets, collection and payment timing, and a minimum cash floor for December and for every month in between.",
  },
];

const BUILD = [
  {
    title: "Pipeline and GTM funnel",
    body: "Marketing spend, leads, and coverage determine the pipeline available to the sales team.",
  },
  {
    title: "ARR schedule",
    body: "Beginning ARR plus new business, less churn and contraction, gives ending ARR for every month.",
  },
  {
    title: "Bookings capacity",
    body: "The ARR plan is checked against the bookings the planned sales team can deliver.",
  },
  {
    title: "Revenue and deferred revenue",
    body: "Recognized and deferred revenue are scheduled from the ARR plan.",
  },
  {
    title: "Headcount and opex",
    body: "The hiring plan and departmental spend build the cost base, with January headcount starting from the prior December.",
  },
  {
    title: "Three statements",
    body: "The income statement, cash flow statement, and balance sheet are produced for every month, with opening balances rolled forward from prior-year actuals.",
  },
];

const ASSURANCE = [
  {
    title: "Comparison with prior-year performance",
    body: "The plan's shape is compared with prior-year results: growth step-ups against last year's own rate, first-half and second-half tilt, peak-quarter shifts, and inconsistencies such as marketing spend rising while leads fall.",
  },
  {
    title: "Fifteen constraints",
    body: "The plan is tested against 15 checks across the ARR bridge, gross retention floor, December and intra-year cash floors, new-business and customer success coverage, pipeline coverage, GTM spend and mix, January headcount, EBITDA, and the sales and marketing tie. Each returns pass, warn, fail, or advisory. A check with missing inputs is reported as skipped, never as a pass.",
  },
  {
    title: "What has to be true",
    body: "Failed and warned checks are restated as plain conditions: what has to close, what has to be confirmed, and what holds today but breaks under stress.",
  },
  {
    title: "Named stress cases",
    body: "Deterministic shocks such as lower growth, higher cost per lead, higher sales attrition, a heavier churn mix, and combined and liquidity cases, each showing the change in December ARR, December cash, and full-year EBITDA with a break, watch, or hold outcome.",
  },
  {
    title: "Simulation of the monthly cash path",
    body: "1,000 draws of four annual operating assumptions (ARR growth, cost per lead, sales attrition, and pipeline coverage), each run through the full monthly model. The result is a P10 to P90 cash band for every month, the distribution of the cash low point, the tightest month, and the share of draws that fall below the cash floor in any month compared with December.",
  },
];

const STEPS = [
  {
    title: "SMPL connects your actuals",
    body: "ERP, CRM, billing, and workforce data are connected and validated during implementation, so the budget starts from reconciled prior-year results.",
  },
  {
    title: "Agree the driver set",
    body: "Your team sets the growth, retention, GTM, capacity, cost, and cash assumptions. SMPL configures them in the model with your definitions.",
  },
  {
    title: "Build and test the draft",
    body: "The budget is calculated through all three statements and tested with Plan Assurance. You adjust drivers and re-run until the plan holds.",
  },
  {
    title: "Approve and lock",
    body: "An approved budget becomes the final version and cannot be edited. A later approved version supersedes it and the history is kept.",
  },
  {
    title: "Measure it through the year",
    body: "Actuals arrive each month for budget versus actual. Reforecasts happen in the forecast, so the budget stays a stable yardstick.",
  },
];

const FAQS: Faq[] = [
  {
    q: "What is the best budgeting software for a SaaS company?",
    a: "Look for software that builds the budget from SaaS drivers such as ARR growth, churn, pipeline coverage, and hiring, produces all three financial statements rather than only a P&L, starts from reconciled actuals, and lets you test the plan before approving it. SMPL.ai is budgeting and planning software for SaaS Finance teams that does this in one connected model and adds Plan Assurance to stress-test the plan.",
  },
  {
    q: "Does SMPL.ai build a balance sheet and cash flow budget, or only a P&L?",
    a: "All three. The budget produces a monthly income statement, balance sheet, and cash flow statement, along with the ARR waterfall and bookings plan, with opening balances rolled forward from prior-year actuals.",
  },
  {
    q: "What is Plan Assurance?",
    a: "Plan Assurance is SMPL's way of testing an operating plan before it is approved. It compares the plan with prior-year performance, checks it against 15 constraints such as cash floors and pipeline coverage, runs named stress cases, and simulates the monthly cash path across 1,000 draws of key assumptions.",
  },
  {
    q: "Is the simulation a probability that we will hit the plan?",
    a: "No. The simulation reports how often the plan breaks a constraint given the stated variability in four assumptions. It is stress frequency under those stated assumptions, not a calibrated probability of attainment. The assumptions and their ranges are shown on screen so your team can challenge them.",
  },
  {
    q: "How is Plan Assurance different from validating the numbers?",
    a: "Validation asks whether the plan is arithmetically correct, for example whether the ARR bridge ties. Plan Assurance asks whether the business can deliver it, for example whether pipeline coverage is enough. A plan can pass validation and still fail a feasibility check, and SMPL reports them separately.",
  },
  {
    q: "Does AI calculate the budget?",
    a: "No. The budget and every figure in Plan Assurance are calculated by SMPL's deterministic engine. AI summarizes and explains the findings from that structured output and never computes or edits a number. If the AI is unavailable, the analysis still renders with a deterministic narrative.",
  },
];

export default function BudgetingAndPlanAssurancePage() {
  return (
    <SolutionPage
      crumb={crumb}
      h1="SaaS budgeting and Plan Assurance"
      ld={solutionPageLd({ title, url, description, faqs: FAQS, crumb })}
      faqs={FAQS}
      related={[
        { href: "/arr-revenue-cash-headcount", label: "ARR, revenue, cash & headcount in one model" },
        { href: "/blog/saas-cash-forecasting", label: "SaaS cash forecasting" },
        { href: "/blog/finance-uncertainty-problem", label: "Finance's uncertainty problem" },
        { href: "/integrations", label: "Integrations & implementation" },
      ]}
      lead={
        <p>
          <strong className="font-semibold text-white">
            SMPL.ai builds a SaaS operating budget from drivers across the income statement,
            balance sheet, and cash flow statement, then tests whether the business can deliver
            it.
          </strong>{" "}
          Plan Assurance checks the plan against prior-year performance, 15 constraints, named
          stress cases, and a simulation of the monthly cash path, so leadership sees which
          assumption breaks first before the board approves the plan.
        </p>
      }
    >
      <Section title="A budget calculated from drivers">
        <p>
          Every month of the budget is calculated, not typed. Your team sets the drivers, and
          the model computes the plan in a fixed order so each step reads the one before it.
        </p>
        <PointList items={DRIVERS} />
        <h3 className="pt-4 text-lg font-semibold text-white">How the plan is built</h3>
        <Steps items={BUILD} />
        <p>
          The output is a budgeted ARR waterfall, income statement, balance sheet, cash flow
          statement, and bookings plan by month, ready for{" "}
          <Link href="/saas-board-reporting" className="text-teal-300 underline-offset-2 hover:underline">
            board reporting
          </Link>{" "}
          and for budget versus actual once the year starts.
        </p>
      </Section>

      <Section title="Two separate questions: is it correct, and can it be delivered?">
        <p>
          A plan can tie perfectly and still be unachievable. SMPL keeps the two questions
          apart. Validation checks the arithmetic, such as whether the ARR bridge and the
          statements tie, and blocks export when they do not. Plan Assurance checks
          feasibility, such as whether there is enough pipeline and sales capacity for the
          bookings plan, and surfaces the risk for Finance to judge.
        </p>
      </Section>

      <Section title="What Plan Assurance checks">
        <PointList items={ASSURANCE} />
        <p className="text-sm text-slate-400">
          <span className="font-semibold text-slate-200">How to read the simulation.</span>{" "}
          The simulation reports stress frequency under stated assumptions, not a calibrated
          probability of hitting the plan. Each draw samples the four annual assumptions once
          and carries them through the monthly model; shocks are not resampled month to month.
          The monthly bands are percentiles across draws rather than a single scenario&apos;s
          path. The assumption ranges are shown on screen.
        </p>
        <p className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-sm text-slate-400">
          <span className="font-semibold text-slate-200">Illustrative example.</span> A draft
          plan ends December with cash comfortably above the $5M floor, and only 6% of draws
          end the year below it. But 24% of draws dip below the floor at some point, with July
          the tightest month, because hiring is front-loaded and the largest renewals bill in
          the fourth quarter. The team moves three hires to September, and the plan clears the
          floor in every month under the named stress cases.
        </p>
      </Section>

      <Section title="Where AI fits">
        <p>
          The deterministic engine calculates every figure in the budget and in Plan
          Assurance. AI reads the structured findings and explains them: whether the plan is
          aggressive, whether its shape is credible, and which risk leadership should look at
          first. It never produces or changes a number, and every lane has a deterministic
          fallback, so the analysis does not depend on the AI being available.
        </p>
      </Section>

      <Section title="From build to approval to monthly review">
        <p>
          SMPL leads the implementation that connects your actuals, and your team owns the
          assumptions and the approval.
        </p>
        <Steps items={STEPS} />
      </Section>
    </SolutionPage>
  );
}
