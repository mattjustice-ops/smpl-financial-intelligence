export type HubSpotPropertyOption = {
  label: string;
  value: string;
  hidden?: boolean;
};

const FORM_INDUSTRY_HINTS: Record<string, string[]> = {
  "B2B SaaS": ["computer software", "software", "information technology"],
  FinTech: ["financial services", "finance", "banking"],
  HealthTech: ["health", "hospital", "medical"],
  EdTech: ["education"],
  Cybersecurity: ["security", "information technology", "computer software"],
  "Infrastructure / DevTools": ["information technology", "internet", "software"],
  Marketplace: ["internet", "retail", "consumer"],
  Other: ["computer software", "information technology"],
};

function normalize(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, " ");
}

export function resolveIndustryOption(
  formIndustry: string,
  options: HubSpotPropertyOption[]
): HubSpotPropertyOption | undefined {
  if (!formIndustry || options.length === 0) return undefined;

  const visible = options.filter((option) => !option.hidden);
  const normalizedForm = normalize(formIndustry);

  const exactLabel = visible.find((option) => normalize(option.label) === normalizedForm);
  if (exactLabel) return exactLabel;

  const exactValue = visible.find((option) => normalize(option.value) === normalizedForm);
  if (exactValue) return exactValue;

  const hints = FORM_INDUSTRY_HINTS[formIndustry] ?? [normalizedForm];
  for (const hint of hints) {
    const normalizedHint = normalize(hint);
    const labelMatch = visible.find((option) => normalize(option.label).includes(normalizedHint));
    if (labelMatch) return labelMatch;
    const valueMatch = visible.find((option) => normalize(option.value).includes(normalizedHint));
    if (valueMatch) return valueMatch;
  }

  return undefined;
}
