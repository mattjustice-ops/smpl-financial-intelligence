export const SALES_EMAIL = "mattjustice@smpl-ai.com";
export const SALES_INQUIRY_MAILTO = `mailto:${SALES_EMAIL}?subject=${encodeURIComponent("SMPL.ai demo request")}`;
export const DEFAULT_SCHEDULING_URL = "https://calendar.app.google/R8yf5HpyPwAitKq16";

/** Always an absolute https URL — ignores relative env values like `/book-demo`. */
export function resolveSchedulingUrl(): string {
  const candidate = process.env.NEXT_PUBLIC_SCHEDULING_URL?.trim();
  if (candidate && /^https?:\/\//i.test(candidate)) {
    return candidate;
  }
  return DEFAULT_SCHEDULING_URL;
}

export const SCHEDULING_URL = resolveSchedulingUrl();

/** Collect the same fields as request-quote, then send users to the calendar. */
export const BOOK_DEMO_URL = "/book-demo";

/** Customer workspace sign-in (optional — home page stays public). */
export const LOGIN_URL = "/login";

export const HERO_COMMENTARY =
  "Enterprise expansion ARR outperformed plan while paid acquisition efficiency remains the largest GTM optimization opportunity.";

export const DATA_SOURCES = [
  { id: "salesforce", label: "Salesforce", color: "from-sky-500/20 to-sky-600/5" },
  { id: "hubspot", label: "HubSpot", color: "from-orange-500/20 to-orange-600/5" },
  { id: "netsuite", label: "NetSuite", color: "from-blue-500/20 to-blue-600/5" },
  { id: "stripe", label: "Stripe", color: "from-violet-500/20 to-violet-600/5" },
  { id: "workday", label: "Workday", color: "from-amber-500/20 to-amber-600/5" },
  { id: "excel", label: "Excel", color: "from-emerald-500/20 to-emerald-600/5" },
  { id: "csv", label: "CSV", color: "from-teal-500/20 to-teal-600/5" },
  { id: "snowflake", label: "Snowflake", color: "from-cyan-500/20 to-cyan-600/5" },
] as const;

export const OPERATING_MODEL = [
  {
    step: "Pipeline",
    hint: "Qualified demand and coverage by segment, region, and motion.",
  },
  {
    step: "Bookings",
    hint: "Closed-won ARR tied to opportunities and quota attainment.",
  },
  {
    step: "ARR",
    hint: "Expansion, contraction, churn, and net new ARR in one waterfall.",
  },
  {
    step: "Revenue",
    hint: "GAAP revenue bridge from deferred revenue and recognition rules.",
  },
  {
    step: "EBITDA",
    hint: "Operating leverage across S&M, R&D, and G&A with variance drivers.",
  },
  {
    step: "Cash",
    hint: "Collections, burn, runway, and forecast vs actual cash movement.",
  },
  {
    step: "Workforce",
    hint: "Headcount, payroll, quota capacity, and hiring plan scenarios.",
  },
] as const;

export const UNDERSTAND_TASKS = [
  {
    id: "arr",
    question: "Why did ARR change?",
    answer: {
      headline: "Net new ARR beat plan by $120K in May",
      driver: "Enterprise expansion (+$340K) offset mid-market contraction (−$220K).",
      impact: "ARR closed at $83.4M vs $83.3M budget.",
      action: "Accelerate CS-led expansion plays in top 20 accounts.",
    },
  },
  {
    id: "cash",
    question: "Why did cash move?",
    answer: {
      headline: "Cash outperformed plan by $37.4M YTD",
      driver: "Annual prepayments and improved collections on enterprise invoices.",
      impact: "Ending cash $66.0M vs $28.6M budget trajectory.",
      action: "Model hiring pace against updated runway scenarios.",
    },
  },
  {
    id: "pipeline",
    question: "Where is pipeline risk?",
    answer: {
      headline: "Q3 coverage soft in mid-market new logo",
      driver: "Paid acquisition CAC up 18% with flat SQL→Opp conversion.",
      impact: "Pipeline coverage 2.1× vs 2.8× target for new ARR.",
      action: "Reallocate $400K to partner-sourced pipeline in H2.",
    },
  },
  {
    id: "hiring",
    question: "Are we hiring too fast?",
    answer: {
      headline: "Headcount 2% above plan; payroll in line",
      driver: "Three enterprise AEs started in May; two reqs still open in CS.",
      impact: "Quota capacity +6% vs plan; fully loaded cost +1.2%.",
      action: "Delay two G&A reqs to Q4 unless pipeline coverage improves.",
    },
  },
  {
    id: "budget",
    question: "What changed vs budget?",
    answer: {
      headline: "Revenue +1.1%; EBITDA −3.2% vs plan YTD",
      driver: "GTM spend ahead of plan while R&D hiring slipped one quarter.",
      impact: "Rule of 40 at 28% vs 30% target.",
      action: "Tighten paid spend and reforecast H2 with updated churn assumptions.",
    },
  },
  {
    id: "board",
    question: "What should the board know?",
    answer: {
      headline: "Growth quality improving; efficiency is the focus",
      driver: "ARR and cash ahead of plan; EBITDA miss driven by GTM investment.",
      impact: "Runway extended 14 months vs prior forecast.",
      action: "Present channel efficiency plan and hiring scenario in board deck.",
    },
  },
  {
    id: "channels",
    question: "Which channels are efficient?",
    answer: {
      headline: "Partner-sourced ARR 2.4× more efficient than paid",
      driver: "Partner CAC $12K vs paid $29K on comparable deal sizes.",
      impact: "42% of net new ARR from partner motion YTD.",
      action: "Increase partner MDF and co-sell capacity in Q3.",
    },
  },
  {
    id: "delay",
    question: "What happens if we delay hiring?",
    answer: {
      headline: "Delaying 4 reqs improves cash $2.1M in H2",
      driver: "Pushes $680K payroll and $1.4M quota ramp cost out of year.",
      impact: "ARR growth −0.8% vs base case in FY26.",
      action: "Run scenario in Workforce Planning with board-ready summary.",
    },
  },
] as const;

export const PRODUCT_MODULES = [
  {
    title: "Revenue Intelligence",
    benefit: "One trusted ARR and revenue story from pipeline to cash.",
    icon: "LineChart",
    preview: ["ARR waterfall", "Net new bridge", "Rev rec tie-out"],
  },
  {
    title: "GTM Intelligence",
    benefit: "Channel efficiency, funnel conversion, and pipeline risk in one view.",
    icon: "Target",
    preview: ["CAC by channel", "Coverage ratio", "SQL → Won"],
  },
  {
    title: "Workforce Planning",
    benefit: "Headcount, payroll, and quota capacity tied to the operating plan.",
    icon: "UsersRound",
    preview: ["Open reqs", "Ramp curves", "Payroll forecast"],
  },
  {
    title: "Management P&L",
    benefit: "Department-level P&L with variance drivers leaders can act on.",
    icon: "Table2",
    preview: ["9-column P&L", "Dept drilldown", "GL bridge"],
  },
  {
    title: "Cash Forecasting",
    benefit: "13-week and long-range cash with scenario-ready assumptions.",
    icon: "Wallet",
    preview: ["CFO bridge", "Runway", "Collections"],
  },
  {
    title: "Board Reporting",
    benefit: "Executive packages and commentary generated from governed data.",
    icon: "Presentation",
    preview: ["Board deck", "MD&A export", "KPI summary"],
  },
  {
    title: "AI CFO Copilot",
    benefit: "Ask why metrics moved and get board-ready answers in seconds.",
    icon: "Sparkles",
    preview: ["Natural language", "Driver trees", "Recommendations"],
  },
  {
    title: "Scenario Planning",
    benefit: "Model hiring, GTM, and churn scenarios with full financial impact.",
    icon: "GitBranch",
    preview: ["What-if", "Sensitivity", "Plan versions"],
  },
] as const;

export const TRUST_CHECKS = [
  "ARR waterfall ties to bookings and CRM closed-won",
  "Net income ties to cash flow statement",
  "Cash ties to balance sheet ending balance",
  "Closed won ties to Salesforce opportunities",
  "Payroll ties to workforce plan and HRIS",
  "Forecast ties to budget and latest actuals",
] as const;
