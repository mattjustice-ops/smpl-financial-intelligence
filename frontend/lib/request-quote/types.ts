export type RequestQuoteFormData = {
  firstname: string;
  lastname: string;
  email: string;
  jobtitle: string;
  phone: string;
  companyName: string;
  domain: string;
  industry: string;
  arrRange: string;
  employeeCount: string;
  financeTeamSize: string;
  companyStage: string;
  currentErp: string;
  currentCrm: string;
  currentBilling: string;
  currentHris: string;
  currentPlanning: string;
  dataReliability: string;
  requestedModules: string[];
  businessNeeds: string;
  biggestChallenge: string;
  currentSolution: string;
  expectedUsers: string;
  implementationTimeline: string;
  deploymentPreference: string;
  budgetRange: string;
};

export type LeadScoringResult = {
  score: number;
  tier: "cold" | "warm" | "hot" | "priority";
  recommendedPackage: string;
  estimatedDealAmount: number;
  rationale: string[];
};

export type RequestQuotePayload = RequestQuoteFormData & {
  leadScore: number;
  leadTier: LeadScoringResult["tier"];
  recommendedPackage: string;
  estimatedDealAmount: number;
  scoringRationale: string[];
  submittedAt: string;
};

export type HubSpotSyncResult = {
  ok: boolean;
  contactId?: string;
  companyId?: string;
  dealId?: string;
  error?: string;
  warnings?: string[];
  companyDebug?: {
    applied: string[];
    skipped: Array<{ property: string; reason: string }>;
    verified?: {
      name?: string | null;
      industry?: string | null;
      domain?: string | null;
    };
  };
};

export type RequestQuoteResponse = {
  ok: boolean;
  submissionId?: string;
  leadScore: number;
  leadTier: LeadScoringResult["tier"];
  recommendedPackage: string;
  estimatedDealAmount: number;
  stored: boolean;
  storageMethod: "database" | "log";
  hubspot: HubSpotSyncResult;
};

export const EMPTY_FORM: RequestQuoteFormData = {
  firstname: "",
  lastname: "",
  email: "",
  jobtitle: "",
  phone: "",
  companyName: "",
  domain: "",
  industry: "",
  arrRange: "",
  employeeCount: "",
  financeTeamSize: "",
  companyStage: "",
  currentErp: "",
  currentCrm: "",
  currentBilling: "",
  currentHris: "",
  currentPlanning: "",
  dataReliability: "",
  requestedModules: [],
  businessNeeds: "",
  biggestChallenge: "",
  currentSolution: "",
  expectedUsers: "",
  implementationTimeline: "",
  deploymentPreference: "",
  budgetRange: "",
};
