import type { LeadScoringResult, RequestQuoteFormData } from "./types";

const DATA_RELIABILITY_SCORES: Record<string, number> = {
  "Highly reliable — single source of truth": 8,
  "Mostly reliable — minor reconciliation gaps": 12,
  "Mixed — multiple versions of truth": 18,
  "Unreliable — heavy manual work each close": 22,
};

const PLAN_SCORES: Record<string, number> = {
  starter: 8,
  professional: 14,
  enterprise: 20,
};

const PACKAGE_BY_PLAN: Record<string, string> = {
  starter: "SMPL Starter",
  professional: "SMPL Professional",
  enterprise: "SMPL Enterprise",
};

const DEAL_BY_PLAN: Record<string, number> = {
  starter: 30000,
  professional: 60000,
  enterprise: 120000,
};

function scoreTier(score: number): LeadScoringResult["tier"] {
  if (score >= 75) return "priority";
  if (score >= 55) return "hot";
  if (score >= 35) return "warm";
  return "cold";
}

function recommendPackage(form: RequestQuoteFormData, score: number): string {
  const plan = form.preferredPlan;
  if (plan && PACKAGE_BY_PLAN[plan]) {
    return PACKAGE_BY_PLAN[plan];
  }

  if (score >= 75) return "SMPL Enterprise";
  if (score >= 55) return "SMPL Professional";
  return "SMPL Starter";
}

export function scoreLead(form: RequestQuoteFormData): LeadScoringResult {
  const rationale: string[] = [];
  let score = 28;

  const reliabilityPoints = DATA_RELIABILITY_SCORES[form.dataReliability] ?? 0;
  score += reliabilityPoints;
  if (reliabilityPoints) {
    rationale.push(`Data reliability contributed ${reliabilityPoints} points.`);
  }

  const needsLength = form.primaryNeeds.trim().length;
  if (needsLength >= 120) {
    score += 12;
    rationale.push("Detailed needs description (+12).");
  } else if (needsLength >= 50) {
    score += 6;
    rationale.push("Needs description provided (+6).");
  }

  const planPoints = form.preferredPlan ? (PLAN_SCORES[form.preferredPlan] ?? 0) : 0;
  if (planPoints) {
    score += planPoints;
    rationale.push(`Pricing tier interest (${form.preferredPlan}) contributed ${planPoints} points.`);
  }

  const freeDomains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"];
  const domain = form.email.split("@")[1]?.toLowerCase() ?? "";
  if (domain && !freeDomains.includes(domain)) {
    score += 6;
    rationale.push("Business email domain (+6).");
  }

  if (form.phone.trim()) {
    score += 2;
    rationale.push("Phone provided (+2).");
  }

  score = Math.min(score, 100);
  const recommendedPackage = recommendPackage(form, score);
  const estimatedDealAmount = form.preferredPlan
    ? (DEAL_BY_PLAN[form.preferredPlan] ?? 50000)
    : score >= 75
      ? 120000
      : score >= 55
        ? 60000
        : 30000;

  return {
    score,
    tier: scoreTier(score),
    recommendedPackage,
    estimatedDealAmount,
    rationale,
  };
}
