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

const title = "SaaS Board Reporting & Financial Commentary Software | SMPL.ai";
const description =
  "Board reporting software for SaaS Finance: governed numbers, variance commentary tied to calculated results, every figure traceable to the general ledger.";
const url = sitePageUrl("/saas-board-reporting");

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  robots: { index: true, follow: true },
  openGraph: { title, description, url, images: [DEFAULT_OG_IMAGE], type: "website", siteName: "SMPL.ai" },
  twitter: { card: "summary_large_image", title, description },
};

const WORKFLOW = [
  {
    title: "Close and lock the period",
    body: "Data moves through Load, Validate, Lock, and Freeze. Closed actuals are checked against statement identities and cross-source tie-outs before the period is locked. Once a period is frozen, its numbers stay stable, so a report you already issued does not quietly change when a source system is corrected later.",
  },
  {
    title: "Build the statements from one ledger",
    body: "The income statement and the management P&L are produced from the same data. Allocations show as a bridge between them: costs move between departments while revenue, total costs, and EBITDA stay the same.",
  },
  {
    title: "Explain what moved",
    body: "Budget versus actual variances are calculated first. Commentary is then drafted from those calculated variances and checked: figures it states are matched against the calculated values, causes it names must be drivers actually present in the data, and unsupported claims are flagged or removed.",
  },
  {
    title: "Trace any number to source",
    body: "A line on the income statement links to the management P&L, and from there to the general ledger detail behind it. When a director asks where a figure came from, the answer is a click away.",
  },
  {
    title: "Produce the board package",
    body: "Executive summary, ARR waterfall, revenue, cash forecast, three statements, management P&L, workforce, and risks and opportunities in one board view, with a board review deck exported to PowerPoint.",
  },
];

const CRITERIA = [
  {
    title: "Do the numbers tie across the package?",
    body: "ARR on the summary slide, revenue on the income statement, and cash on the forecast should come from one model. If they are assembled from separate exports, they will eventually disagree in the meeting.",
  },
  {
    title: "Is commentary grounded or generated?",
    body: "Ask whether the AI writes from calculated variances or produces its own figures. Anything that reaches a board should come from deterministic calculation.",
  },
  {
    title: "Can a prior report be reproduced?",
    body: "Ask what happens to a report you already issued when a source system is corrected retroactively. Without period locking, the history quietly changes.",
  },
  {
    title: "How long from close to board-ready?",
    body: "Measure the days between books closing and a package you would send. Most of that time is usually assembly and reconciliation, not analysis.",
  },
];

const FAQS: Faq[] = [
  {
    q: "What is the best software for SaaS board reporting?",
    a: "Look for software that produces ARR, revenue, cash, and the financial statements from one governed model, so every number in the package ties. It should trace figures back to source records, lock prior periods so issued reports reproduce, and ground any AI commentary in calculated results. SMPL.ai is built around that workflow for growing SaaS Finance teams.",
  },
  {
    q: "Can software automate monthly finance reporting and commentary?",
    a: "The assembly can be automated: pulling actuals, calculating variances, building the statements, and drafting commentary from the calculated results. The review cannot. Finance still validates the numbers and edits the narrative before it goes to the board.",
  },
  {
    q: "How does SMPL.ai check AI commentary before it reaches the board?",
    a: "Commentary is written only from a package of calculated results. After drafting, SMPL extracts every figure and matches it against those results, checks that each cause the text names is a driver actually present in the data, such as a specific expansion or churn movement, and checks that material figures cite their source. Unsupported numbers or causes are flagged or removed before the text reaches a report.",
  },
  {
    q: "How should AI be used in board reporting?",
    a: "AI should explain results that were calculated deterministically: summarizing variances, drafting narrative, and surfacing what changed. It should not produce financial figures of its own, because a fluent explanation of a wrong number is harder to catch than the wrong number alone.",
  },
  {
    q: "What should a SaaS board package include?",
    a: "Typically an executive summary, ARR and its movement (new, expansion, contraction, churn), retention, the income statement and management P&L, budget versus actual with explanations, cash and runway, headcount, and the key risks and opportunities.",
  },
  {
    q: "How can a CFO prepare board reporting faster?",
    a: "Remove the assembly work. When the statements, SaaS metrics, and cash forecast come from one model and the commentary is drafted from calculated variances, the time between close and a board-ready package goes into review rather than rebuilding spreadsheets.",
  },
];

export default function SaasBoardReportingPage() {
  return (
    <SolutionPage
      crumb="Board reporting & commentary"
      h1="SaaS board reporting and financial commentary"
      ld={solutionPageLd({ title, url, description, faqs: FAQS, crumb: "Board reporting & commentary" })}
      faqs={FAQS}
      related={[
        { href: "/blog/saas-board-reporting-arr-cash-pl", label: "Why SaaS board reporting breaks down" },
        { href: "/blog/ai-variance-commentary-cfo-standard", label: "What CFOs should demand from AI variance commentary" },
        { href: "/blog/explainable-ai-in-finance", label: "Explainable AI in Finance: explain, don't create" },
        { href: "/fpa-software-for-saas", label: "FP&A software for SaaS companies" },
      ]}
      lead={
        <p>
          <strong className="font-semibold text-white">
            SMPL.ai produces SaaS board reporting from one governed financial model.
          </strong>{" "}
          The monthly close, the financial statements, variance explanations, and the board
          package are connected, so every number ties across the package, commentary is
          grounded in calculated results, and any figure can be traced back to the general
          ledger.
        </p>
      }
    >
      <Section title="Why board reporting takes so long">
        <p>
          In most growing SaaS companies, the analysis is not the slow part. The slow part is
          assembly: exporting from billing, the CRM, and the ledger, reconciling them against
          each other, rebuilding the same slides, and writing commentary by hand. Each step
          is a chance for the ARR on one page to disagree with the revenue on another.
        </p>
        <p>
          Board members notice when numbers do not tie. Once they stop trusting one figure,
          every other figure in the package gets questioned too.
        </p>
      </Section>

      <Section title="One workflow from close to board package">
        <PointList items={WORKFLOW} />
      </Section>

      <Section title="Reporting validation and Plan Assurance answer different questions">
        <p>
          Reporting validation asks whether the actuals in the package are correct: do the
          statements tie, does ARR foot, does the cash bridge agree with the ledger. Plan
          Assurance asks whether the plan the board is approving can be delivered, by testing
          it against cash floors, pipeline coverage, and stress cases. SMPL keeps the two
          separate, so a package that ties is never mistaken for a plan that holds. See{" "}
          <Link
            href="/budgeting-and-plan-assurance"
            className="text-teal-300 underline-offset-2 hover:underline"
          >
            budgeting and Plan Assurance
          </Link>
          .
        </p>
      </Section>

      <Section title="What to ask a vendor">
        <PointList items={CRITERIA} />
      </Section>

      <Section title="Implementation led by SMPL">
        <p>
          The package is only as good as the data behind it. SMPL connects your ERP, CRM,
          billing, and workforce systems as part of implementation, maps them into one model,
          and reconciles the results to your source systems before the first package goes
          out. See{" "}
          <Link href="/integrations" className="text-teal-300 underline-offset-2 hover:underline">
            integrations and implementation
          </Link>
          .
        </p>
      </Section>

      <Section title="What SMPL.ai does not do">
        <p>
          SMPL.ai does not post transactions to your general ledger or replace your ERP, and
          there are no automatic journal entries. The AI explains results the engine
          calculated; it does not decide what the numbers are. Your team still reviews the
          package and owns what goes to the board.
        </p>
      </Section>
    </SolutionPage>
  );
}
