import type { LeadScoringResult, RequestQuoteFormData } from "./types";

const ARR_SCORES: Record<string, number> = {
  "Under $5M": 8,
  "$5M–$20M": 14,
  "$20M–$50M": 20,
  "$50M–$100M": 24,
  "$100M+": 25,
};

const EMPLOYEE_SCORES: Record<string, number> = {
  "1–50": 3,
  "51–200": 6,
  "201–500": 8,
  "501–1,000": 9,
  "1,000+": 10,
};

const FINANCE_TEAM_SCORES: Record<string, number> = {
  "1–2": 4,
  "3–5": 6,
  "6–10": 8,
  "11–20": 9,
  "20+": 10,
};

const BUDGET_SCORES: Record<string, number> = {
  "Under $50K / year": 6,
  "$50K–$100K / year": 10,
  "$100K–$250K / year": 15,
  "$250K–$500K / year": 18,
  "$500K+ / year": 20,
  "Not determined yet": 4,
};

const TIMELINE_SCORES: Record<string, number> = {
  "Immediate (0–30 days)": 10,
  "Near-term (1–3 months)": 8,
  "This quarter": 6,
  "Next quarter": 4,
  "Exploring / no timeline yet": 2,
};

const STAGE_SCORES: Record<string, number> = {
  "Seed / Series A": 4,
  "Series B": 6,
  "Series C+": 8,
  "Growth / PE-backed": 9,
  Public: 10,
};

const DATA_RELIABILITY_SCORES: Record<string, number> = {
  "Highly reliable — single source of truth": 2,
  "Mostly reliable — minor reconciliation gaps": 3,
  "Mixed — multiple versions of truth": 4,
  "Unreliable — heavy manual work each close": 5,
};

const DEAL_AMOUNTS: Record<string, number> = {
  "Under $5M": 35000,
  "$5M–$20M": 75000,
  "$20M–$50M": 120000,
  "$50M–$100M": 180000,
  "$100M+": 250000,
};

function scoreTier(score: number): LeadScoringResult["tier"] {
  if (score >= 80) return "priority";
  if (score >= 60) return "hot";
  if (score >= 40) return "warm";
  return "cold";
}

function recommendPackage(form: RequestQuoteFormData, score: number): string {
  const moduleCount = form.requestedModules.length;
  const arr = form.arrRange;
  const budget = form.budgetRange;

  if (
    score >= 80 ||
    arr === "$100M+" ||
    (arr === "$50M–$100M" && moduleCount >= 5) ||
    budget === "$500K+ / year"
  ) {
    return "SMPL Platform";
  }

  if (
    score >= 60 ||
    arr === "$50M–$100M" ||
    arr === "$20M–$50M" ||
    moduleCount >= 5 ||
    budget === "$250K–$500K / year"
  ) {
    return "SMPL Enterprise";
  }

  if (
    score >= 40 ||
    arr === "$5M–$20M" ||
    moduleCount >= 3 ||
    budget === "$100K–$250K / year"
  ) {
    return "SMPL Growth";
  }

  return "SMPL Starter";
}

export function scoreLead(form: RequestQuoteFormData): LeadScoringResult {
  const rationale: string[] = [];
  let score = 0;

  const arrPoints = ARR_SCORES[form.arrRange] ?? 0;
  score += arrPoints;
  if (arrPoints) rationale.push(`ARR range contributed ${arrPoints} points.`);

  const employeePoints = EMPLOYEE_SCORES[form.employeeCount] ?? 0;
  score += employeePoints;
  if (employeePoints) rationale.push(`Company size contributed ${employeePoints} points.`);

  const financePoints = FINANCE_TEAM_SCORES[form.financeTeamSize] ?? 0;
  score += financePoints;
  if (financePoints) rationale.push(`Finance team size contributed ${financePoints} points.`);

  const budgetPoints = BUDGET_SCORES[form.budgetRange] ?? 0;
  score += budgetPoints;
  if (budgetPoints) rationale.push(`Budget range contributed ${budgetPoints} points.`);

  const timelinePoints = TIMELINE_SCORES[form.implementationTimeline] ?? 0;
  score += timelinePoints;
  if (timelinePoints) rationale.push(`Timeline urgency contributed ${timelinePoints} points.`);

  const stagePoints = STAGE_SCORES[form.companyStage] ?? 0;
  score += stagePoints;
  if (stagePoints) rationale.push(`Company stage contributed ${stagePoints} points.`);

  const reliabilityPoints = DATA_RELIABILITY_SCORES[form.dataReliability] ?? 0;
  score += reliabilityPoints;
  if (reliabilityPoints) {
    rationale.push(`Data pain / reliability contributed ${reliabilityPoints} points.`);
  }

  const modulePoints = Math.min(form.requestedModules.length * 2, 10);
  score += modulePoints;
  if (modulePoints) {
    rationale.push(`${form.requestedModules.length} requested modules contributed ${modulePoints} points.`);
  }

  if (form.currentSolution.trim()) {
    score += 2;
    rationale.push("Existing solution noted (+2).");
  }

  score = Math.min(score, 100);
  const recommendedPackage = recommendPackage(form, score);
  const estimatedDealAmount = DEAL_AMOUNTS[form.arrRange] ?? 50000;

  return {
    score,
    tier: scoreTier(score),
    recommendedPackage,
    estimatedDealAmount,
    rationale,
  };
}
