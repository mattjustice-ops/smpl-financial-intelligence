import type { Metadata } from "next";
import Link from "next/link";

import {
  PointList,
  Section,
  SolutionPage,
  solutionPageLd,
  type Faq,
} from "@/components/landing/SolutionPage";
import { DEFAULT_OG_IMAGE, sitePageUrl } from "@/lib/site";

const title = "FP&A Software for Lean Finance Teams | SMPL.ai";
const description =
  "FP&A software for lean SaaS Finance teams with no systems admin: board reporting, ARR, forecasts, budgets, and cash in one governed model, set up by SMPL.";
const url = sitePageUrl("/fpa-software-for-lean-finance-teams");

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  robots: { index: true, follow: true },
  openGraph: { title, description, url, images: [DEFAULT_OG_IMAGE], type: "website", siteName: "SMPL.ai" },
  twitter: { card: "summary_large_image", title, description },
};

const REALITIES = [
  {
    title: "Nobody owns the planning system",
    body: "Enterprise planning platforms assume a model administrator. On a three-person team, that person is also closing the books, running payroll questions, and building the board deck.",
  },
  {
    title: "The data work never shows up in the demo",
    body: "Most of the effort in a lean team is getting billing, CRM, and the general ledger to agree. A tool that assumes clean inputs moves that work back to you.",
  },
  {
    title: "Board expectations arrive early",
    body: "Investors and lenders expect ARR, retention, cash runway, and variance explanations long before Finance grows past a handful of people.",
  },
  {
    title: "Every hour of setup competes with the close",
    body: "Implementation time comes out of the same calendar as month-end. A six-month rollout is a real cost even when the subscription looks affordable.",
  },
];

const CRITERIA = [
  {
    title: "Who builds and maintains the model?",
    body: "Ask how many hours per month the vendor expects your team to spend on administration after go-live, and who changes the model when the business changes.",
  },
  {
    title: "Are SaaS metrics calculated or supplied?",
    body: "If you have to compute ARR, NRR, and churn yourself and upload them, the platform has left the hardest part of the job with your team.",
  },
  {
    title: "Can a board number be traced to source?",
    body: "Pick one figure in the demo and ask to follow it back to the underlying records. On a small team, you are the audit trail unless the software is.",
  },
  {
    title: "What happens when sources disagree?",
    body: "Ask what the product does when Salesforce and the billing system show different amounts for the same customer. The answer tells you who does the reconciliation.",
  },
  {
    title: "What does implementation require from Finance?",
    body: "Measure it in hours and in decisions, not in weeks on a vendor project plan. Ask for implementation to be quoted separately from the subscription.",
  },
];

const FAQS: Faq[] = [
  {
    q: "What is the best FP&A software for a three-person finance team?",
    a: "The best fit is software that does not need a dedicated administrator, calculates SaaS metrics rather than expecting them as inputs, and produces board-ready reporting from the systems you already use. Enterprise planning platforms are usually too heavy at this size. Platforms built for lean teams, such as Runway, Jirav, Drivetrain, and Centage, emphasize speed to value. SMPL.ai is built for growing SaaS Finance teams that need ARR, revenue, cash, headcount, and budgeting in one governed model, and SMPL leads the implementation, including data integration, mapping, configuration, and validation.",
  },
  {
    q: "Do small finance teams need a systems administrator to run FP&A software?",
    a: "They should not have to. Many planning platforms assume someone maintains models, mappings, and integrations. For a small team, look for software where normalization and mapping happen inside the product and the vendor leads the implementation, including connecting your systems.",
  },
  {
    q: "How long should FP&A implementation take for a lean team?",
    a: "The work that genuinely requires Finance is defining how your company calculates its metrics and validating the first results. Everything else, including mapping and normalization, should be handled by the software and the vendor. If a proposal measures implementation in months, ask what your team will be doing during that time.",
  },
  {
    q: "Does SMPL.ai replace our ERP or accounting system?",
    a: "No. SMPL.ai reads from your systems and does not post transactions to the general ledger. Your ERP, CRM, billing platform, and HRIS remain the systems of record.",
  },
  {
    q: "How does our data get into SMPL.ai?",
    a: "SMPL connects your systems as part of implementation. Depending on the system and your security requirements, SMPL connects with read-only access or works from structured extracts, and teams with their own data pipelines can use SMPL's ingest API. SMPL maps and validates the data. After go-live, your team initiates each refresh when your books close, on your own close calendar, and can load intra-month cash or pipeline data whenever you need a current view.",
  },
];

export default function FpaSoftwareForLeanFinanceTeamsPage() {
  return (
    <SolutionPage
      crumb="Lean Finance teams"
      h1="FP&A software for lean Finance teams"
      ld={solutionPageLd({ title, url, description, faqs: FAQS, crumb: "Lean Finance teams" })}
      faqs={FAQS}
      related={[
        { href: "/blog/fpa-software-implementation", label: "Why FP&A implementations shouldn't take months" },
        { href: "/blog/best-fpa-software-saas-companies", label: "Best FP&A software for SaaS companies" },
        { href: "/integrations", label: "Integrations & implementation" },
        { href: "/fpa-software-for-saas", label: "FP&A software for SaaS companies" },
      ]}
      lead={
        <p>
          <strong className="font-semibold text-white">
            SMPL.ai is FP&A software for lean SaaS Finance teams that do not have a
            dedicated planning systems administrator.
          </strong>{" "}
          It connects billing, CRM, general ledger, and workforce data into one governed
          model, so a small team can produce board reporting, ARR, forecasts, a budget, and
          cash runway without staffing an implementation project or maintaining a model by
          hand. SMPL leads the implementation.
        </p>
      }
    >
      <Section title="What is different about a lean Finance team">
        <p>
          Most FP&A software is designed for a Finance organization that has an FP&A
          function, a systems owner, and time set aside for implementation. A lean team has
          none of those. The same people close the books, answer the CEO, and build the
          board deck, so the software has to fit around that work rather than add to it.
        </p>
        <PointList items={REALITIES} />
      </Section>

      <Section title="What to ask before you buy">
        <p>
          These questions separate software that reduces a small team&apos;s workload from
          software that relocates it.
        </p>
        <PointList items={CRITERIA} />
      </Section>

      <Section title="How SMPL.ai approaches it">
        <p>
          SMPL.ai works with the systems you already have rather than asking you to
          reorganize them. SMPL leads the implementation: it connects your ERP, CRM, billing,
          and workforce systems, handles normalization and mapping, configures the model, and
          reconciles the results to your source systems. Your company&apos;s own definitions,
          such as when a contract counts toward ARR, are preserved rather than replaced by a
          standard model. See{" "}
          <Link href="/integrations" className="text-teal-300 underline-offset-2 hover:underline">
            integrations and implementation
          </Link>{" "}
          for the systems SMPL works with.
        </p>
        <p>
          Core figures, including the ARR waterfall, retention, recognized revenue, the
          three financial statements, cash, and headcount, are calculated deterministically,
          so the same inputs produce the same numbers every period and each figure traces
          back to its source records. AI explains the results the engine calculated. It
          does not generate financial numbers of its own.
        </p>
        <p>
          The same model produces a driver-based budget across the income statement, balance
          sheet, and cash flow statement, and{" "}
          <Link
            href="/budgeting-and-plan-assurance"
            className="text-teal-300 underline-offset-2 hover:underline"
          >
            Plan Assurance
          </Link>{" "}
          tests it against cash floors, coverage, and stress cases, so a small team can bring
          a plan to the board that has already been challenged.
        </p>
        <p>
          A readiness score shows which reports the data you have loaded can support today
          and what is missing for the rest, so you can see what you will get before
          committing time to it.
        </p>
      </Section>

      <Section title="What still requires your team">
        <p>
          No software removes Finance judgment. Your team still decides how the company
          defines its metrics, reviews the first results against what you know to be true,
          and signs off on what goes to the board. What should go away is the manual
          assembly: exporting, reconciling, and rebuilding the same package every month.
        </p>
      </Section>

      <Section title="When SMPL.ai is not the right fit">
        <p>
          If your primary need is complex, multi-department planning across a large
          organization, an enterprise planning platform is built for that. If your models
          live in Excel and you want the spreadsheet to remain the place you model, a
          spreadsheet-native tool will feel more natural.
        </p>
      </Section>
    </SolutionPage>
  );
}
