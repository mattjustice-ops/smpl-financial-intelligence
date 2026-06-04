import type { RequestQuoteFormData, RequestQuotePayload } from "./types";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function normalizeDomain(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .split("/")[0];
}

export function domainFromEmail(email: string): string {
  const part = email.split("@")[1];
  return part ? normalizeDomain(part) : "";
}

export function validateForm(data: RequestQuoteFormData): string[] {
  const errors: string[] = [];

  if (!data.firstname.trim()) errors.push("First name is required.");
  if (!data.lastname.trim()) errors.push("Last name is required.");
  if (!data.companyName.trim()) errors.push("Company name is required.");
  if (!data.email.trim()) errors.push("Work email is required.");
  else if (!EMAIL_RE.test(data.email.trim())) errors.push("Enter a valid email address.");
  if (!data.jobtitle.trim()) errors.push("Job title is required.");
  if (!data.country.trim()) errors.push("Country is required.");
  if (!data.state.trim()) errors.push("State / region is required.");
  if (!data.dataReliability) errors.push("Select how reliable your finance data is today.");
  if (!data.primaryNeeds.trim()) errors.push("Describe your primary needs or issues.");
  else if (data.primaryNeeds.trim().length < 20) {
    errors.push("Please add a bit more detail about your needs (at least 20 characters).");
  }

  return errors;
}

/** @deprecated Use validateForm */
export function validateStep(stepIndex: number, data: RequestQuoteFormData): string[] {
  if (stepIndex === 0) return validateForm(data);
  return [];
}

/** @deprecated Use validateForm */
export function validateFullForm(data: RequestQuoteFormData): string[] {
  return validateForm(data);
}

export function sanitizeForm(data: RequestQuoteFormData): RequestQuoteFormData {
  return {
    firstname: data.firstname.trim(),
    lastname: data.lastname.trim(),
    companyName: data.companyName.trim(),
    email: data.email.trim().toLowerCase(),
    jobtitle: data.jobtitle.trim(),
    phone: data.phone.trim(),
    country: data.country.trim(),
    state: data.state.trim(),
    dataReliability: data.dataReliability,
    primaryNeeds: data.primaryNeeds.trim(),
    preferredPlan: data.preferredPlan?.trim().toLowerCase() || undefined,
    submissionIntent: data.submissionIntent === "demo" ? "demo" : "quote",
  };
}

export function buildQuotePayload(
  form: RequestQuoteFormData,
  scoring: {
    score: number;
    tier: RequestQuotePayload["leadTier"];
    recommendedPackage: string;
    estimatedDealAmount: number;
    rationale: string[];
  }
): RequestQuotePayload {
  const domain = domainFromEmail(form.email);

  return {
    ...form,
    submissionIntent: form.submissionIntent === "demo" ? "demo" : "quote",
    domain,
    businessNeeds: form.primaryNeeds,
    biggestChallenge: form.primaryNeeds,
    industry: "To be qualified on demo",
    arrRange: "Not provided",
    employeeCount: "Not provided",
    financeTeamSize: "Not provided",
    companyStage: "Not provided",
    currentErp: "Not provided",
    currentCrm: "Not provided",
    currentBilling: "Not provided",
    currentHris: "Not provided",
    currentPlanning: "Not provided",
    requestedModules: [],
    currentSolution: "Not provided",
    expectedUsers: "Not provided",
    implementationTimeline: "Not provided",
    deploymentPreference: "Not provided",
    budgetRange: "Not provided",
    leadScore: scoring.score,
    leadTier: scoring.tier,
    recommendedPackage: scoring.recommendedPackage,
    estimatedDealAmount: scoring.estimatedDealAmount,
    scoringRationale: scoring.rationale,
    submittedAt: new Date().toISOString(),
  };
}
