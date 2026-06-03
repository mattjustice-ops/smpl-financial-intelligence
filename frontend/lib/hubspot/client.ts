import fs from "node:fs";

const HUBSPOT_API = "https://api.hubapi.com";

export function getHubSpotToken(): string | null {
  const direct = process.env.HUBSPOT_PRIVATE_APP_TOKEN?.trim();
  if (direct) return direct;

  const tokenFile = process.env.HUBSPOT_TOKEN_FILE?.trim();
  if (!tokenFile) return null;

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

type HubSpotErrorBody = {
  message?: string;
  errors?: Array<{ message?: string; context?: { propertyName?: string[] } }>;
  status?: string;
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
      throw new Error(formatHubSpotHttpError(response.status, body, text || response.statusText));
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

  async findCompanyByName(name: string): Promise<string | null> {
    if (!name) return null;

    const result = await this.request<{
      results: Array<{ id: string }>;
    }>("/crm/v3/objects/companies/search", {
      method: "POST",
      body: JSON.stringify({
        filterGroups: [
          {
            filters: [
              {
                propertyName: "name",
                operator: "EQ",
                value: name,
              },
            ],
          },
        ],
        limit: 1,
      }),
    });

    return result.results?.[0]?.id ?? null;
  }

  async findCompanyByDomainVariants(domain: string): Promise<string | null> {
    const variants = new Set([
      domain,
      domain.replace(/^www\./, ""),
      `www.${domain.replace(/^www\./, "")}`,
    ]);

    for (const variant of variants) {
      const id = await this.findCompanyByDomain(variant);
      if (id) return id;
    }

    return null;
  }

  async batchUpsertCompanyByDomain(domain: string, properties: Record<string, string>): Promise<string> {
    const result = await this.request<{
      results: Array<{ id: string }>;
    }>(`/crm/v3/objects/companies/batch/upsert?idProperty=domain`, {
      method: "POST",
      body: JSON.stringify({
        inputs: [
          {
            id: domain,
            properties: {
              ...properties,
              domain,
              website: properties.website || `https://${domain}`,
            },
          },
        ],
      }),
    });

    const id = result.results?.[0]?.id;
    if (!id) throw new Error("HubSpot company upsert returned no id.");
    return id;
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

  async updateCompanyResilient(
    companyId: string,
    properties: Record<string, string>
  ): Promise<{ applied: string[]; skipped: Array<{ property: string; reason: string }> }> {
    const applied: string[] = [];
    const skipped: Array<{ property: string; reason: string }> = [];
    const description = properties.description;
    const aboutUs = properties.about_us;
    const coreEntries = Object.entries(properties).filter(
      ([key]) => key !== "description" && key !== "about_us"
    );

    for (const [property, value] of coreEntries) {
      if (!value) continue;
      try {
        await this.updateCompany(companyId, { [property]: value });
        applied.push(property);
      } catch (error) {
        skipped.push({
          property,
          reason: error instanceof Error ? error.message : "Unknown error",
        });
      }
    }

    if (description) {
      try {
        await this.updateCompany(companyId, { description });
        applied.push("description");
      } catch (error) {
        try {
          await this.updateCompany(companyId, { about_us: description });
          applied.push("about_us");
        } catch (aboutError) {
          skipped.push({
            property: "description",
            reason: error instanceof Error ? error.message : "Unknown error",
          });
          if (aboutUs) {
            try {
              await this.updateCompany(companyId, { about_us: aboutUs });
              applied.push("about_us");
            } catch (aboutUsError) {
              skipped.push({
                property: "about_us",
                reason: aboutUsError instanceof Error ? aboutUsError.message : "Unknown error",
              });
            }
          }
        }
      }
    }

    return { applied, skipped };
  }

  async applyCompanyIdentity(
    companyId: string,
    identity: Record<string, string>
  ): Promise<{ applied: string[]; skipped: Array<{ property: string; reason: string }> }> {
    const applied: string[] = [];
    const skipped: Array<{ property: string; reason: string }> = [];

    const name = identity.name;
    if (name) {
      try {
        await this.updateCompany(companyId, { name });
        applied.push("name");
      } catch (error) {
        skipped.push({
          property: "name",
          reason: error instanceof Error ? error.message : "Unknown error",
        });
      }
    }

    const rest = { ...identity };
    delete rest.name;
    const resilient = await this.updateCompanyResilient(companyId, rest);
    applied.push(...resilient.applied);
    skipped.push(...resilient.skipped);

    return { applied, skipped };
  }

  async upsertCompany(properties: Record<string, string>): Promise<string> {
    const domain = properties.domain?.replace(/^www\./, "");
    const name = properties.name;

    if (domain) {
      try {
        const companyId = await this.batchUpsertCompanyByDomain(domain, {
          ...properties,
          name: name || domain,
          domain,
          website: properties.website || `https://${domain}`,
        });
        await this.applyCompanyIdentity(companyId, {
          name: name || domain,
          domain,
          website: properties.website || `https://${domain}`,
          ...(properties.industry ? { industry: properties.industry } : {}),
        });
        return companyId;
      } catch {
        // Fall back to search/update/create when domain is not a unique upsert key in this portal.
      }
    }

    const existingId =
      (domain ? await this.findCompanyByDomainVariants(domain) : null) ||
      (name ? await this.findCompanyByName(name) : null);

    if (existingId) {
      await this.applyCompanyIdentity(existingId, cleanProperties({
        name,
        domain,
        website: domain ? properties.website || `https://${domain}` : properties.website,
        industry: properties.industry,
      }));
      return existingId;
    }

    const createProps = cleanProperties({
      name: name || domain,
      domain,
      website: domain ? `https://${domain}` : properties.website,
    });
    if (!createProps.name && !createProps.domain) {
      throw new Error("Company name or domain is required.");
    }

    const companyId = await this.createCompany(createProps);
    await this.applyCompanyIdentity(companyId, cleanProperties({
      name,
      domain,
      website: domain ? properties.website || `https://${domain}` : properties.website,
      industry: properties.industry,
    }));
    return companyId;
  }

  async resolvePipeline(): Promise<{ pipelineId: string; dealstage: string; pipelineLabel: string }> {
    const configuredPipelineId = process.env.HUBSPOT_PIPELINE_ID?.trim();
    const configuredStageId = process.env.HUBSPOT_DEAL_STAGE_ID?.trim();
    if (configuredPipelineId && configuredStageId) {
      return {
        pipelineId: configuredPipelineId,
        dealstage: configuredStageId,
        pipelineLabel: getHubSpotPipelineName(),
      };
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
      const available = pipelines.results.map((p) => p.label).join(", ");
      throw new Error(
        `HubSpot pipeline "${pipelineName}" was not found. Available pipelines: ${available || "none"}.`
      );
    }

    const firstStage = [...pipeline.stages].sort((a, b) => a.displayOrder - b.displayOrder)[0];
    if (!firstStage) {
      throw new Error(`HubSpot pipeline "${pipeline.label}" has no stages.`);
    }

    return { pipelineId: pipeline.id, dealstage: firstStage.id, pipelineLabel: pipeline.label };
  }

  async createDeal(properties: Record<string, string>): Promise<string> {
    const result = await this.request<{ id: string }>("/crm/v3/objects/deals", {
      method: "POST",
      body: JSON.stringify({ properties }),
    });
    return result.id;
  }

  async updateDeal(dealId: string, properties: Record<string, string>): Promise<void> {
    await this.request(`/crm/v3/objects/deals/${dealId}`, {
      method: "PATCH",
      body: JSON.stringify({ properties }),
    });
  }

  async updateContact(contactId: string, properties: Record<string, string>): Promise<void> {
    await this.request(`/crm/v3/objects/contacts/${contactId}`, {
      method: "PATCH",
      body: JSON.stringify({ properties }),
    });
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

  async associateContactToCompany(contactId: string, companyId: string): Promise<void> {
    try {
      await this.request("/crm/v4/associations/contacts/companies/batch/create", {
        method: "POST",
        body: JSON.stringify({
          inputs: [
            {
              from: { id: contactId },
              to: { id: companyId },
              types: [{ associationCategory: "HUBSPOT_DEFINED", associationTypeId: 1 }],
            },
          ],
        }),
      });
      return;
    } catch {
      await this.associateDefault("contacts", contactId, "companies", companyId);
    }
  }

  async associateDeal(dealId: string, toType: "contacts" | "companies", toId: string): Promise<void> {
    const associationTypeId = toType === "contacts" ? 3 : 5;
    try {
      await this.request(`/crm/v4/associations/deals/${toType}/batch/create`, {
        method: "POST",
        body: JSON.stringify({
          inputs: [
            {
              from: { id: dealId },
              to: { id: toId },
              types: [{ associationCategory: "HUBSPOT_DEFINED", associationTypeId }],
            },
          ],
        }),
      });
      return;
    } catch {
      await this.associateDefault("deals", dealId, toType, toId);
    }
  }

  async patchExtendedProperties(
    objectType: "companies" | "deals" | "contacts",
    objectId: string,
    properties: Record<string, string>
  ): Promise<{ applied: string[]; skipped: Array<{ property: string; reason: string }> }> {
    const applied: string[] = [];
    const skipped: Array<{ property: string; reason: string }> = [];

    for (const [property, value] of Object.entries(properties)) {
      if (!value) continue;
      try {
        await this.request(`/crm/v3/objects/${objectType}/${objectId}`, {
          method: "PATCH",
          body: JSON.stringify({ properties: { [property]: value } }),
        });
        applied.push(property);
      } catch (error) {
        skipped.push({
          property,
          reason: error instanceof Error ? error.message : "Unknown error",
        });
      }
    }

    return { applied, skipped };
  }
}

export function cleanProperties(properties: Record<string, string | undefined>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(properties).filter(([, value]) => value !== undefined && value !== "")
  ) as Record<string, string>;
}

function formatHubSpotHttpError(status: number, body: unknown, fallback: string): string {
  if (typeof body === "object" && body !== null) {
    const parsed = body as HubSpotErrorBody;
    const parts = [`HubSpot ${status}: ${parsed.message || fallback}`];
    if (parsed.errors?.length) {
      for (const err of parsed.errors) {
        const property = err.context?.propertyName?.[0];
        parts.push(property ? `- ${property}: ${err.message || "invalid"}` : `- ${err.message || "invalid"}`);
      }
    }
    return parts.join(" ");
  }
  return `HubSpot ${status}: ${fallback}`;
}

export async function checkHubSpotHealth(): Promise<{
  tokenConfigured: boolean;
  pipelineName: string;
  pipelineFound: boolean;
  pipelineLabel?: string;
  stageLabel?: string;
  availablePipelines?: string[];
  error?: string;
}> {
  const pipelineName = getHubSpotPipelineName();
  const token = getHubSpotToken();
  if (!token) {
    return {
      tokenConfigured: false,
      pipelineName,
      pipelineFound: false,
      error: "HUBSPOT_PRIVATE_APP_TOKEN is not configured on the server.",
    };
  }

  try {
    const client = new HubSpotClient(token);
    const resolved = await client.resolvePipeline();
    const pipelines = await client.request<{ results: Array<{ label: string }> }>("/crm/v3/pipelines/deals");
    return {
      tokenConfigured: true,
      pipelineName,
      pipelineFound: true,
      pipelineLabel: resolved.pipelineLabel,
      availablePipelines: pipelines.results.map((p) => p.label),
    };
  } catch (error) {
    return {
      tokenConfigured: true,
      pipelineName,
      pipelineFound: false,
      error: error instanceof Error ? error.message : "Unknown HubSpot health check error",
    };
  }
}
