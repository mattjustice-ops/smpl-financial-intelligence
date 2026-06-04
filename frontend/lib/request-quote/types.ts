export type SubmissionIntent = "quote" | "demo";

export type RequestQuoteFormData = {
  firstname: string;
  lastname: string;
  companyName: string;
  email: string;
  jobtitle: string;
  phone: string;
  country: string;
  state: string;
  dataReliability: string;
  primaryNeeds: string;
  /** From /request-quote?plan= or /book-demo?plan= when linked from pricing */
  preferredPlan?: string;
  submissionIntent?: SubmissionIntent;
};

export type LeadScoringResult = {
  score: number;
  tier: "cold" | "warm" | "hot" | "priority";
  recommendedPackage: string;
  estimatedDealAmount: number;
  rationale: string[];
};

/** Full payload stored and sent to HubSpot (includes legacy fields for CRM descriptions). */
export type RequestQuotePayload = RequestQuoteFormData & {
  submissionIntent: SubmissionIntent;
  domain: string;
  businessNeeds: string;
  biggestChallenge: string;
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
  requestedModules: string[];
  currentSolution: string;
  expectedUsers: string;
  implementationTimeline: string;
  deploymentPreference: string;
  budgetRange: string;
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
  associationDebug?: {
    applied: string[];
    verifiedContactCompanies: string[];
    verifiedCompanyContacts: string[];
  };
  companyDebug?: {
    applied: string[];
    skipped: Array<{ property: string; reason: string }>;
    verified?: {
      name?: string | null;
      industry?: string | null;
      domain?: string | null;
    };
    resolvedFrom?: string;
    contactCompanyIds?: string[];
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
  companyName: "",
  email: "",
  jobtitle: "",
  phone: "",
  country: "",
  state: "",
  dataReliability: "",
  primaryNeeds: "",
  preferredPlan: "",
};
