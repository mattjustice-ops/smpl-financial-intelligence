import type { Metadata } from "next";

import {
  PointList,
  Section,
  SolutionPage,
  solutionPageLd,
  type Faq,
} from "@/components/landing/SolutionPage";
import { sitePageUrl } from "@/lib/site";

const title = "ARR, Revenue, Cash & Headcount in One Financial Model | SMPL.ai";
const description =
  "FP&A software that handles ARR, recognized revenue, cash, and headcount together in one SaaS financial model, so a change in bookings, churn, or hiring flows through every number.";
const url = sitePageUrl("/arr-revenue-cash-headcount");

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  robots: { index: true, follow: true },
  openGraph: { title, description, url, type: "website", siteName: "SMPL.ai" },
  twitter: { title, description },
};

const CLOCKS = [
  {
    title: "ARR",
    body: "Contract value annualized, moving through new, expansion, contraction, and churn. It lives in subscription and CRM data and changes when contracts do.",
  },
  {
    title: "Recognized revenue",
    body: "What the income statement reports, recognized over the service period. Implementation fees and usage can appear here and not in ARR, with deferred revenue in between.",
  },
  {
    title: "Cash",
    body: "When customers actually pay, which depends on billing terms and collections. An annual prepaid contract and a monthly one with the same ARR produce very different cash curves.",
  },
  {
    title: "Headcount",
    body: "The largest cost line for most SaaS companies. Hiring dates, compensation, and attrition drive operating expense, margin, and cash burn.",
  },
];

const MODEL = [
  {
    title: "ARR and retention",
    body: "ARR waterfall by month with new, expansion, contraction, and churn, plus net and gross revenue retention, calculated from your subscription data using your company's ARR definition.",
  },
  {
    title: "Revenue and the statements",
    body: "Recognized and deferred revenue, the income statement, balance sheet, and cash flow, with the management P&L built from the same ledger.",
  },
  {
    title: "Cash and runway",
    body: "A cash forecast and runway that respond to bookings, churn, billing timing, and hiring rather than a separate spreadsheet that has to be updated by hand.",
  },
  {
    title: "Workforce",
    body: "Headcount and compensation by department, feeding operating expense, the P&L, and cash in the same model.",
  },
  {
    title: "Scenarios across all four",
    body: "Change new bookings, churn, or hiring in a forecast scenario and see the effect on ARR, revenue, EBITDA, cash, and runway together.",
  },
];

const FAQS: Faq[] = [
  {
    q: "What FP&A software handles ARR, revenue, cash, and headcount together?",
    a: "Look for software that calculates all four from one model rather than showing them in separate modules. SMPL.ai is built around that connected SaaS operating model: the ARR waterfall, recognized revenue and the financial statements, cash and runway, and headcount are calculated together, so a change in bookings, churn, or hiring flows through every number.",
  },
  {
    q: "Why don't ARR and GAAP revenue match?",
    a: "They measure different things on different clocks. ARR annualizes current contract value, while recognized revenue follows the service period and includes items ARR excludes, such as one-time implementation fees and usage overages. Deferred revenue sits between them.",
  },
  {
    q: "How does headcount affect a SaaS cash forecast?",
    a: "Payroll is usually the largest cash outflow, so hiring dates and compensation assumptions move runway more than almost anything else. A cash forecast that is not connected to the headcount plan will be wrong as soon as a hire slips or accelerates.",
  },
  {
    q: "How do I test whether an FP&A tool really connects these numbers?",
    a: "Ask for one integrated scenario in the demo: delay several hires, lower new ARR, and increase churn. Then ask to see ARR, recognized revenue, operating expense, EBITDA, cash, and runway by month in the same model. If the vendor has to switch tools or rebuild a spreadsheet, the numbers are not connected.",
  },
  {
    q: "Does SMPL.ai use its own ARR definition?",
    a: "No. Companies define ARR differently, for example whether a contract counts at signature or at go-live. SMPL.ai preserves your company's definitions and applies them consistently across every report.",
  },
];

export default function ArrRevenueCashHeadcountPage() {
  return (
    <SolutionPage
      eyebrow="SaaS FP&A · Connected financial model"
      h1="ARR, revenue, cash, and headcount in one financial model"
      ld={solutionPageLd({ title, url, description, faqs: FAQS })}
      faqs={FAQS}
      related={[
        { href: "/blog/arr-waterfall-vs-gaap-revenue", label: "ARR waterfall vs GAAP revenue" },
        { href: "/blog/saas-cash-forecasting", label: "SaaS cash forecasting: what belongs in the model" },
        { href: "/blog/grr-vs-nrr", label: "GRR vs NRR" },
        { href: "/blog/saas-revenue-forecasting-arr-bookings-gaap", label: "SaaS revenue forecasting" },
        { href: "/fpa-software-for-saas", label: "FP&A software for SaaS companies" },
      ]}
      lead={
        <p>
          <strong className="font-semibold text-white">
            SMPL.ai handles ARR, recognized revenue, cash, and headcount together in one
            SaaS financial model.
          </strong>{" "}
          Change new bookings, churn, or hiring dates and the effect shows up in ARR,
          revenue, operating expense, EBITDA, cash, and runway at the same time, because
          every number is calculated from the same governed data.
        </p>
      }
    >
      <Section title="Four numbers, four different clocks">
        <p>
          Most SaaS reporting problems come from treating these as one number viewed four
          ways. They are four different measurements, each coming from a different system
          and changing at a different time.
        </p>
        <PointList items={CLOCKS} />
        <p>
          When each one is maintained in a separate tool or spreadsheet, they drift apart.
          The board deck shows one ARR, the forecast assumes another, and the cash plan was
          built before the last three hires were approved.
        </p>
      </Section>

      <Section title="What one model means in practice">
        <p>
          Many FP&A tools can show an ARR chart, a P&L, and a headcount plan in different
          modules. The harder requirement is that they are the same model, so the
          relationships between them are calculated rather than reconciled by hand.
        </p>
        <PointList items={MODEL} />
      </Section>

      <Section title="How SMPL.ai keeps them consistent">
        <p>
          SMPL.ai reads billing, CRM, general ledger, and workforce data into one canonical
          model and applies your company&apos;s definitions the same way every period. The
          calculations are deterministic, so the same inputs always produce the same
          figures, and each figure traces back to the records behind it. AI explains what
          moved and why; it does not produce the numbers.
        </p>
        <p>
          SMPL.ai reads from your systems and does not write back to them. Your ERP, CRM,
          billing platform, and HRIS remain the systems of record.
        </p>
      </Section>
    </SolutionPage>
  );
}
