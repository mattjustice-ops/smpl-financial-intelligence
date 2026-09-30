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
import { INTEGRATION_PAGES } from "@/components/landing/integrationsCatalog";
import { sitePageUrl } from "@/lib/site";

const crumb = "Integrations";
const title = "Integrations for SaaS FP&A: ERP, CRM, Billing & HRIS | SMPL.ai";
const description =
  "SMPL.ai connects ERP, CRM, billing, and HRIS data into one SaaS financial model. SMPL leads the integration, mapping, configuration, and financial validation.";
const url = sitePageUrl("/integrations");

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  robots: { index: true, follow: true },
  openGraph: { title, description, url, type: "website", siteName: "SMPL.ai" },
  twitter: { title, description },
};

const OTHER_SYSTEMS: { category: string; systems: { name: string; body: string }[] }[] = [
  {
    category: "Accounting and ERP",
    systems: [
      {
        name: "QuickBooks Online",
        body: "Chart of accounts, journal entries, invoices, and classes for the financial statements, departmental reporting, and cash.",
      },
    ],
  },
  {
    category: "CRM",
    systems: [
      {
        name: "HubSpot",
        body: "Deals, pipelines, and stages for pipeline, bookings, and revenue forecasting, in the same way as Salesforce.",
      },
    ],
  },
  {
    category: "Billing and subscriptions",
    systems: [
      {
        name: "Stripe Billing",
        body: "Customers, subscriptions, invoices, and payments for the ARR waterfall, retention, and cash timing.",
      },
      {
        name: "Chargebee",
        body: "Subscriptions, plans, and invoices for ARR, churn, expansion, and billing-to-cash timing.",
      },
      {
        name: "Recurly",
        body: "Subscription and invoice data for ARR and retention reporting.",
      },
    ],
  },
  {
    category: "HRIS and payroll",
    systems: [
      {
        name: "Rippling, Gusto, BambooHR, Workday, HiBob, and Deel",
        body: "Employees, departments, start dates, and compensation for the headcount plan, payroll cost, and the effect of hiring on opex and cash.",
      },
    ],
  },
  {
    category: "Data warehouses and file delivery",
    systems: [
      {
        name: "Snowflake, cloud storage, and secure file transfer",
        body: "Where your data already sits in a warehouse or scheduled exports, SMPL can read a secure share or a file drop instead of each source system.",
      },
    ],
  },
];

const OWNERSHIP = [
  {
    title: "SMPL is responsible for",
    body: "Connecting to your systems or working from structured extracts, mapping accounts, customers, products, and departments, configuring the model, and reconciling the results to your source systems.",
  },
  {
    title: "Your team provides",
    body: "Read-only access or structured extracts, your company's definitions for metrics such as ARR and bookings, review of the mapping decisions SMPL documents, validation of the first results, and the decisions about what goes to the board. After go-live, your team initiates each refresh when your books close, on your own close calendar.",
  },
  {
    title: "Your systems keep doing their jobs",
    body: "SMPL reads from your ERP, CRM, billing platform, and HRIS and does not write back to them. Each remains the system of record for its own domain.",
  },
];

const FAQS: Faq[] = [
  {
    q: "Which systems does SMPL.ai integrate with?",
    a: "SMPL works with the ERP, CRM, billing, and HRIS systems SaaS Finance teams commonly use, including NetSuite, Sage Intacct, QuickBooks Online, Xero, Rillet, and Campfire for accounting; Salesforce and HubSpot for CRM; Maxio, Stripe, Chargebee, and Recurly for billing; and Rippling, Gusto, BambooHR, Workday, HiBob, and Deel for workforce data. SMPL leads the integration as part of implementation.",
  },
  {
    q: "How does data get from our systems into SMPL.ai?",
    a: "As part of implementation, SMPL connects to each system with read-only access or works from structured extracts, a warehouse share, or secure file delivery, depending on the system and your security requirements. Teams with their own data pipelines can also send data through SMPL's ingest API. SMPL maps and validates the data. After go-live, your team initiates each refresh when your books close, on your own close calendar, and can load intra-month cash or pipeline data whenever you need a current view.",
  },
  {
    q: "Does SMPL.ai work with multi-entity, multi-currency companies?",
    a: "Yes. For ERPs such as NetSuite and Sage Intacct, SMPL uses the ERP's consolidated financial actuals, including its currency translation and intercompany elimination adjustments, and for USD-reporting companies the consolidated USD results. The ERP remains the system of record for consolidation: SMPL supports reporting and planning on that consolidated foundation rather than recreating the consolidation engine. During implementation, SMPL confirms that the extraction method delivers the required consolidation context, reconciles the imported results to the ERP's consolidated reports, retains entity and currency information, and scopes the subsidiary views you need.",
  },
  {
    q: "Our system is not listed. Can SMPL.ai still work with it?",
    a: "Usually, yes. If a system can provide read-only access or structured exports of the data SMPL needs, SMPL can map it into the model as part of implementation. Tell us what you use and we will confirm the approach during scoping.",
  },
  {
    q: "Who does the data mapping and reconciliation?",
    a: "SMPL does. Mapping accounts, customers, products, and departments across systems and reconciling the results to your source systems is part of SMPL's implementation. Your team reviews the decisions and confirms the definitions.",
  },
  {
    q: "Does SMPL.ai write data back to our ERP or CRM?",
    a: "No. SMPL reads from your systems and does not post journal entries, invoices, or changes back to them.",
  },
];

export default function IntegrationsHubPage() {
  const ld = [
    ...solutionPageLd({ title, url, description, faqs: FAQS, crumb, category: null }),
    {
      "@context": "https://schema.org",
      "@type": "ItemList",
      name: "SMPL.ai integration pages",
      itemListElement: INTEGRATION_PAGES.map((p, i) => ({
        "@type": "ListItem",
        position: i + 1,
        name: p.label,
        url: sitePageUrl(p.href),
      })),
    },
  ];

  return (
    <SolutionPage
      category={null}
      crumb={crumb}
      h1="Integrations and implementation"
      ld={ld}
      faqs={FAQS}
      more={{
        title: "More from FP&A for SaaS",
        items: SOLUTIONS.filter((s) => s.href !== "/integrations"),
      }}
      related={[
        { href: "/blog/fpa-software-implementation", label: "Why FP&A implementations shouldn't take months" },
        { href: "/blog/connected-systems-financial-data", label: "Connected systems vs aligned financial data" },
        { href: "/platform", label: "The SMPL.ai platform" },
        { href: "/fpa-software-for-saas", label: "FP&A software for SaaS companies" },
      ]}
      lead={
        <p>
          <strong className="font-semibold text-white">
            SMPL.ai connects the systems your Finance team already runs, including your ERP,
            CRM, billing platform, and HRIS, into one SaaS financial model.
          </strong>{" "}
          That model supports reporting, forecasting, budgeting, and Plan Assurance. Connecting
          your systems is part of what SMPL delivers: SMPL leads the integration and
          implementation, including data mapping, configuration, and financial validation.
        </p>
      }
    >
      <Section title="How SMPL connects your systems">
        <p>
          During implementation, SMPL connects to each system with read-only access or works
          from structured extracts, depending on the system and your security requirements.
          Where your data already sits in a warehouse such as Snowflake or in scheduled
          exports, SMPL can read from there instead. Teams with their own data pipelines can
          send data through SMPL&apos;s ingest API.
        </p>
        <p>
          SMPL then maps the data into one model, applies your company&apos;s definitions,
          and reconciles the results to your source systems. For multi-entity companies, SMPL
          builds on your ERP&apos;s consolidated results, including its currency translation
          and intercompany eliminations, so the ERP remains the system of record for
          consolidation.
        </p>
        <p>
          After go-live, your team initiates each refresh when your books close, on your own
          close calendar, and can load intra-month cash or pipeline data whenever you need a
          current view.
        </p>
      </Section>

      <Section title="Systems with dedicated pages">
        <p>
          Each page covers the data SMPL uses from that system, the reporting and planning it
          supports, and how SMPL connects it to the rest of your stack.
        </p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {INTEGRATION_PAGES.map((p) => (
            <Link
              key={p.href}
              href={p.href}
              className="group rounded-xl border border-white/10 bg-white/[0.02] p-4 transition hover:border-teal-400/40 hover:bg-white/[0.04]"
            >
              <span className="block text-xs font-medium uppercase tracking-wide text-slate-500">
                {p.category}
              </span>
              <span className="mt-1 block text-sm font-semibold text-white group-hover:text-teal-200">
                {p.label} <span aria-hidden>→</span>
              </span>
              <span className="mt-2 block text-xs leading-relaxed text-slate-400">{p.body}</span>
            </Link>
          ))}
        </div>
      </Section>

      <Section title="Other systems SMPL works with">
        <p>
          These systems supply one part of the model and are connected through the same
          implementation process.
        </p>
        <div className="mt-6 space-y-6">
          {OTHER_SYSTEMS.map((group) => (
            <div key={group.category}>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                {group.category}
              </h3>
              <ul className="mt-3 space-y-3">
                {group.systems.map((s) => (
                  <li key={s.name} className="border-l border-teal-400/30 pl-4">
                    <span className="text-base font-semibold text-white">{s.name}</span>
                    <p className="mt-1 text-sm leading-relaxed text-slate-400">{s.body}</p>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <p>
          Using something else? If it can provide read-only access or structured exports, SMPL
          can usually map it into the model. Tell us what you use and we will confirm the
          approach during scoping.
        </p>
      </Section>

      <Section title="Who does what">
        <PointList items={OWNERSHIP} />
      </Section>

      <Section title="What the connected model produces">
        <p>
          Once your systems are connected, the same numbers feed every output: ARR and
          retention, the three financial statements, the management P&L, cash and runway,
          headcount, a{" "}
          <Link href="/budgeting-and-plan-assurance" className="text-teal-300 underline-offset-2 hover:underline">
            driver-based budget tested with Plan Assurance
          </Link>
          , and the{" "}
          <Link href="/saas-board-reporting" className="text-teal-300 underline-offset-2 hover:underline">
            board package
          </Link>
          . A change in bookings, churn, or hiring flows through{" "}
          <Link href="/arr-revenue-cash-headcount" className="text-teal-300 underline-offset-2 hover:underline">
            ARR, revenue, cash, and headcount
          </Link>{" "}
          together.
        </p>
      </Section>

      <Section title="Discuss your environment">
        <p>
          Bring a list of your systems and a copy of what your board package looks like
          today. We will walk through how SMPL would connect them and what your team would see
          at the end of implementation.
        </p>
      </Section>

      <p className="mt-10 text-xs leading-relaxed text-slate-500">
        NetSuite, Sage Intacct, QuickBooks Online, Xero, Rillet, Campfire, Salesforce, HubSpot,
        Maxio, Stripe, Chargebee, Recurly, Rippling, Gusto, BambooHR, Workday, HiBob, Deel,
        Snowflake, and other product names are trademarks of their respective owners. They are
        used only to identify the systems SMPL.ai works with. SMPL.ai is not affiliated with,
        sponsored by, or endorsed by these companies, and no partnership or certification is
        implied.
      </p>
    </SolutionPage>
  );
}
