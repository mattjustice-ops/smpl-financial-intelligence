import type { SolutionCard } from "./SolutionPage";

/** Systems with a dedicated page under /integrations/[system]. */
export const INTEGRATION_PAGES: readonly (SolutionCard & { category: string })[] = [
  {
    href: "/integrations/maxio",
    label: "Maxio",
    category: "Billing, ARR & revenue recognition",
    body: "Billing and ARR actuals plus the revenue recognition sub-ledger, connected to your CRM and general ledger.",
  },
  {
    href: "/integrations/netsuite",
    label: "NetSuite",
    category: "ERP & general ledger",
    body: "Consolidated general ledger results, with subsidiary and department detail, feeding financial statements, the management P&L, and the budget.",
  },
  {
    href: "/integrations/salesforce",
    label: "Salesforce",
    category: "CRM & pipeline",
    body: "Opportunities and pipeline feeding bookings, revenue forecasting, and GTM capacity planning.",
  },
  {
    href: "/integrations/netsuite-salesforce",
    label: "NetSuite + Salesforce",
    category: "Accounting actuals + CRM pipeline",
    body: "Accounting actuals and CRM pipeline in one model for connected revenue forecasting and planning.",
  },
  {
    href: "/integrations/sage-intacct",
    label: "Sage Intacct",
    category: "ERP & general ledger",
    body: "Dimensional general ledger and consolidated multi-entity results carried into management reporting and planning.",
  },
  {
    href: "/integrations/xero",
    label: "Xero",
    category: "Accounting",
    body: "Accounts, invoices, and tracking categories turned into SaaS reporting, cash planning, and a three-statement budget.",
  },
  {
    href: "/integrations/rillet",
    label: "Rillet",
    category: "Accounting & ERP",
    body: "Ledger and recognized revenue from Rillet combined with pipeline and workforce data for forecasting and board reporting.",
  },
  {
    href: "/integrations/campfire",
    label: "Campfire",
    category: "Accounting & ERP",
    body: "Accounting actuals from Campfire extended with CRM, billing, and headcount data for planning and Plan Assurance.",
  },
] as const;

export function trademarkNote(...names: string[]): string {
  const list =
    names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}` : names[0];
  const verb = names.length > 1 ? "are trademarks of their respective owners" : "is a trademark of its owner";
  return `${list} ${verb}. Names are used only to identify the systems SMPL.ai works with and do not imply affiliation with, or endorsement by, ${names.length > 1 ? "those companies" : "that company"}.`;
}

export function otherIntegrations(currentHref: string): SolutionCard[] {
  return INTEGRATION_PAGES.filter((p) => p.href !== currentHref)
    .slice(0, 6)
    .map(({ href, label, body }) => ({ href, label, body }));
}
