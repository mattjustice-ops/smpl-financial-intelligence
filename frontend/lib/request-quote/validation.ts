import type { RequestQuoteFormData } from "./types";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function normalizeDomain(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .split("/")[0];
}

export function validateStep(stepIndex: number, data: RequestQuoteFormData): string[] {
  const errors: string[] = [];

  if (stepIndex === 0) {
    if (!data.firstname.trim()) errors.push("First name is required.");
    if (!data.lastname.trim()) errors.push("Last name is required.");
    if (!data.email.trim()) errors.push("Work email is required.");
    else if (!EMAIL_RE.test(data.email.trim())) errors.push("Enter a valid email address.");
    if (!data.jobtitle.trim()) errors.push("Job title is required.");
  }

  if (stepIndex === 1) {
    if (!data.companyName.trim()) errors.push("Company name is required.");
    if (!data.domain.trim()) errors.push("Company domain is required.");
    if (!data.industry) errors.push("Select an industry.");
    if (!data.arrRange) errors.push("Select an ARR range.");
    if (!data.employeeCount) errors.push("Select an employee count.");
    if (!data.financeTeamSize) errors.push("Select a finance team size.");
    if (!data.companyStage) errors.push("Select a company stage.");
  }

  if (stepIndex === 2) {
    if (!data.currentErp) errors.push("Select your current ERP / GL.");
    if (!data.currentCrm) errors.push("Select your current CRM.");
    if (!data.currentBilling) errors.push("Select your billing system.");
    if (!data.currentHris) errors.push("Select your HRIS.");
    if (!data.currentPlanning) errors.push("Select your planning tool.");
    if (!data.dataReliability) errors.push("Select your data reliability level.");
  }

  if (stepIndex === 3) {
    if (data.requestedModules.length === 0) errors.push("Select at least one SMPL module.");
    if (!data.businessNeeds.trim()) errors.push("Describe your business needs.");
    if (!data.biggestChallenge.trim()) errors.push("Describe your biggest challenge.");
    if (!data.expectedUsers) errors.push("Select expected user count.");
    if (!data.implementationTimeline) errors.push("Select an implementation timeline.");
    if (!data.deploymentPreference) errors.push("Select a deployment preference.");
    if (!data.budgetRange) errors.push("Select a budget range.");
  }

  return errors;
}

export function validateFullForm(data: RequestQuoteFormData): string[] {
  return FORM_STEP_COUNT.flatMap((_, index) => validateStep(index, data));
}

const FORM_STEP_COUNT = [0, 1, 2, 3];

export function sanitizeForm(data: RequestQuoteFormData): RequestQuoteFormData {
  return {
    ...data,
    firstname: data.firstname.trim(),
    lastname: data.lastname.trim(),
    email: data.email.trim().toLowerCase(),
    jobtitle: data.jobtitle.trim(),
    phone: data.phone.trim(),
    companyName: data.companyName.trim(),
    domain: normalizeDomain(data.domain),
    businessNeeds: data.businessNeeds.trim(),
    biggestChallenge: data.biggestChallenge.trim(),
    currentSolution: data.currentSolution.trim(),
    requestedModules: [...new Set(data.requestedModules.map((m) => m.trim()).filter(Boolean))],
  };
}
