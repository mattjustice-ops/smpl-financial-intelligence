import type { EmailConfig } from "@auth/core/providers/email";

export type BackendOrganization = {
  organizationId: string;
  organizationName: string;
  role: string;
  status: string;
  plan: string;
  seatLimit: number;
  organizationStatus: string;
};

export type SendVerificationRequestParams = Parameters<EmailConfig["sendVerificationRequest"]>[0];
