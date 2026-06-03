import fs from "node:fs";

const HUBSPOT_API = "https://api.hubapi.com";

export function getHubSpotToken(): string | null {
  const direct = process.env.HUBSPOT_PRIVATE_APP_TOKEN?.trim();
  if (direct) return direct;

  const tokenFile =
    process.env.HUBSPOT_TOKEN_FILE?.trim() ||
    "C:\\Users\\mattj\\OneDrive\\Documents\\HubSpot Token.txt";

  try {
    if (!fs.existsSync(tokenFile)) return null;
    const content = fs.readFileSync(tokenFile, "utf-8");
    const match = content.match(/pat-[a-z0-9-]+/i);
    return match?.[0] ?? null;
  } catch {
    return null;
  }
}

export function getHubSpotPipelineName(): string {
  return process.env.HUBSPOT_PIPELINE_NAME?.trim() || "SMPL Inbound Sales";
}

type HubSpotRequestInit = Omit<RequestInit, "headers"> & {
  headers?: Record<string, string>;
};

export class HubSpotClient {
  constructor(private readonly token: string) {}

  async request<T>(endpoint: string, init: HubSpotRequestInit = {}): Promise<T> {
    const response = await fetch(`${HUBSPOT_API}${endpoint}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${this.token}`,
        "Content-Type": "application/json",
        ...init.headers,
      },
      cache: "no-store",
    });

    const text = await response.text();
    let body: unknown = null;
    if (text) {
      try {
        body = JSON.parse(text);
      } catch {
        body = text;
      }
    }

    if (!response.ok) {
      const message =
        typeof body === "object" &&
        body !== null &&
        "message" in body &&
        typeof (body as { message: unknown }).message === "string"
          ? (body as { message: string }).message
          : text || response.statusText;
      throw new Error(`HubSpot ${response.status}: ${message}`);
    }

    return body as T;
  }

  async upsertContact(properties: Record<string, string>): Promise<string> {
    const email = properties.email;
    if (!email) throw new Error("Contact email is required for upsert.");

    const result = await this.request<{
      results: Array<{ id: string }>;
    }>("/crm/v3/objects/contacts/batch/upsert", {
      method: "POST",
      body: JSON.stringify({
        inputs: [
          {
            idProperty: "email",
            id: email,
            properties,
          },
        ],
      }),
    });

    const id = result.results?.[0]?.id;
    if (!id) throw new Error("HubSpot contact upsert returned no id.");
    return id;
  }

  async findCompanyByDomain(domain: string): Promise<string | null> {
    if (!domain) return null;

    const result = await this.request<{
      results: Array<{ id: string }>;
    }>("/crm/v3/objects/companies/search", {
      method: "POST",
      body: JSON.stringify({
        filterGroups: [
          {
            filters: [
              {
                propertyName: "domain",
                operator: "EQ",
                value: domain,
              },
            ],
          },
        ],
        limit: 1,
      }),
    });

    return result.results?.[0]?.id ?? null;
  }

  async createCompany(properties: Record<string, string>): Promise<string> {
    const result = await this.request<{ id: string }>("/crm/v3/objects/companies", {
      method: "POST",
      body: JSON.stringify({ properties }),
    });
    return result.id;
  }

  async updateCompany(companyId: string, properties: Record<string, string>): Promise<string> {
    await this.request(`/crm/v3/objects/companies/${companyId}`, {
      method: "PATCH",
      body: JSON.stringify({ properties }),
    });
    return companyId;
  }

  async upsertCompany(properties: Record<string, string>): Promise<string> {
    const domain = properties.domain;
    if (domain) {
      const existing = await this.findCompanyByDomain(domain);
      if (existing) return this.updateCompany(existing, properties);
    }
    return this.createCompany(properties);
  }

  async resolvePipeline(): Promise<{ pipelineId: string; dealstage: string }> {
    const configuredPipelineId = process.env.HUBSPOT_PIPELINE_ID?.trim();
    const configuredStageId = process.env.HUBSPOT_DEAL_STAGE_ID?.trim();
    if (configuredPipelineId && configuredStageId) {
      return { pipelineId: configuredPipelineId, dealstage: configuredStageId };
    }

    const pipelineName = getHubSpotPipelineName();
    const pipelines = await this.request<{
      results: Array<{
        id: string;
        label: string;
        stages: Array<{ id: string; label: string; displayOrder: number }>;
      }>;
    }>("/crm/v3/pipelines/deals");

    const pipeline =
      pipelines.results.find((p) => p.label.toLowerCase() === pipelineName.toLowerCase()) ??
      pipelines.results.find((p) => p.label.toLowerCase().includes("smpl"));

    if (!pipeline) {
      throw new Error(`HubSpot pipeline "${pipelineName}" was not found.`);
    }

    const firstStage = [...pipeline.stages].sort((a, b) => a.displayOrder - b.displayOrder)[0];
    if (!firstStage) {
      throw new Error(`HubSpot pipeline "${pipeline.label}" has no stages.`);
    }

    return { pipelineId: pipeline.id, dealstage: firstStage.id };
  }

  async createDeal(properties: Record<string, string>): Promise<string> {
    const result = await this.request<{ id: string }>("/crm/v3/objects/deals", {
      method: "POST",
      body: JSON.stringify({ properties }),
    });
    return result.id;
  }

  async associateDefault(
    fromType: "contacts" | "companies" | "deals",
    fromId: string,
    toType: "contacts" | "companies" | "deals",
    toId: string
  ): Promise<void> {
    await this.request(`/crm/v4/objects/${fromType}/${fromId}/associations/default/${toType}/${toId}`, {
      method: "PUT",
    });
  }
}

export function cleanProperties(properties: Record<string, string | undefined>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(properties).filter(([, value]) => value !== undefined && value !== "")
  ) as Record<string, string>;
}
