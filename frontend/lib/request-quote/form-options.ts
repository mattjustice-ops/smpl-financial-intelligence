export const FORM_STEPS = [
  { id: "contact", title: "Contact", description: "Who should we follow up with?" },
  { id: "company", title: "Company", description: "Tell us about your business." },
  { id: "stack", title: "Tech stack", description: "What systems power finance today?" },
  { id: "needs", title: "Needs", description: "What are you trying to solve?" },
  { id: "review", title: "Review", description: "Confirm and submit." },
] as const;

export const INDUSTRIES = [
  "B2B SaaS",
  "FinTech",
  "HealthTech",
  "EdTech",
  "Cybersecurity",
  "Infrastructure / DevTools",
  "Marketplace",
  "Other",
];

export const ARR_RANGES = [
  "Under $5M",
  "$5M–$20M",
  "$20M–$50M",
  "$50M–$100M",
  "$100M+",
];

export const EMPLOYEE_COUNTS = ["1–50", "51–200", "201–500", "501–1,000", "1,000+"];

export const FINANCE_TEAM_SIZES = ["1–2", "3–5", "6–10", "11–20", "20+"];

export const COMPANY_STAGES = [
  "Seed / Series A",
  "Series B",
  "Series C+",
  "Growth / PE-backed",
  "Public",
];

export const SYSTEM_OPTIONS = [
  "NetSuite",
  "QuickBooks",
  "Sage Intacct",
  "Xero",
  "Salesforce",
  "HubSpot",
  "Stripe",
  "Chargebee",
  "Workday",
  "Rippling",
  "Excel / Google Sheets",
  "Adaptive / Anaplan",
  "Pigment",
  "Mosaic",
  "Other",
  "None / Not sure",
];

export const DATA_RELIABILITY_OPTIONS = [
  "Highly reliable — single source of truth",
  "Mostly reliable — minor reconciliation gaps",
  "Mixed — multiple versions of truth",
  "Unreliable — heavy manual work each close",
];

export const SMPL_MODULES = [
  "Revenue Intelligence",
  "GTM Intelligence",
  "Workforce Planning",
  "Management P&L",
  "Cash Forecasting",
  "Board Reporting",
  "AI CFO Copilot",
  "Scenario Planning",
];

export const EXPECTED_USERS = ["1–3", "4–10", "11–25", "26–50", "50+"];

export const IMPLEMENTATION_TIMELINES = [
  "Immediate (0–30 days)",
  "Near-term (1–3 months)",
  "This quarter",
  "Next quarter",
  "Exploring / no timeline yet",
];

export const DEPLOYMENT_PREFERENCES = ["Cloud (SMPL-hosted)", "Private cloud", "Hybrid", "Not sure yet"];

export const BUDGET_RANGES = [
  "Under $50K / year",
  "$50K–$100K / year",
  "$100K–$250K / year",
  "$250K–$500K / year",
  "$500K+ / year",
  "Not determined yet",
];

export const FIELD_LABELS: Record<string, string> = {
  firstname: "First name",
  lastname: "Last name",
  email: "Work email",
  jobtitle: "Job title",
  phone: "Phone",
  companyName: "Company name",
  domain: "Company domain",
  industry: "Industry",
  arrRange: "ARR range",
  employeeCount: "Employee count",
  financeTeamSize: "Finance team size",
  companyStage: "Company stage",
  currentErp: "Current ERP / GL",
  currentCrm: "Current CRM",
  currentBilling: "Billing system",
  currentHris: "HRIS",
  currentPlanning: "Planning tool",
  dataReliability: "Data reliability",
  requestedModules: "Requested modules",
  businessNeeds: "Business needs",
  biggestChallenge: "Biggest challenge",
  currentSolution: "Current solution",
  expectedUsers: "Expected users",
  implementationTimeline: "Implementation timeline",
  deploymentPreference: "Deployment preference",
  budgetRange: "Budget range",
};
