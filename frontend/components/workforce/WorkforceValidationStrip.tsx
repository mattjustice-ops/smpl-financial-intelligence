"use client";

export type WorkforceValidationCheck = {
  scenario: string;
  period: string;
  validation_name: string;
  status: "pass" | "warning" | "fail";
  expected_value?: string | number | null;
  actual_value?: string | number | null;
  variance?: string | number | null;
  source_tables_used?: string[];
};

export type WorkforceValidationResponse = {
  organization_id: string;
  scenario: string;
  start_period: string;
  end_period: string;
  status: "pass" | "warning" | "fail";
  checks: WorkforceValidationCheck[];
  failed_count: number;
  warning_count: number;
  passed_count: number;
};

type SectionFilter = "management-pl" | "cash" | "decisions" | "all";

function filterChecks(checks: WorkforceValidationCheck[], section: SectionFilter) {
  const issues = checks.filter((c) => c.status !== "pass");
  if (section === "all" || section === "decisions") return issues;
  if (section === "management-pl") {
    return issues.filter((c) =>
      /pnl|payroll|overlay|allocation|people_cost|source_data|zero_payroll|gtm_quota/i.test(c.validation_name)
    );
  }
  return issues.filter((c) => /cash|payroll/i.test(c.validation_name));
}

function formatCheckMessage(check: WorkforceValidationCheck) {
  const parts = [check.validation_name.replaceAll("_", " ")];
  if (check.period) parts.push(check.period.slice(0, 7));
  if (check.actual_value != null && check.actual_value !== "") {
    parts.push(`actual ${check.actual_value}`);
  }
  if (check.variance != null && check.variance !== "") {
    parts.push(`variance ${check.variance}`);
  }
  return parts.join(" · ");
}

export function WorkforceValidationStrip({
  checks,
  section = "all",
  title = "Workforce validations",
}: {
  checks: WorkforceValidationCheck[];
  section?: SectionFilter;
  title?: string;
}) {
  const issues = filterChecks(checks, section);
  if (!issues.length) return null;

  return (
    <div style={{ marginBottom: 12 }}>
      <div className="mpl-section-label">{title}</div>
      <div className="mpl-validations" style={{ marginTop: 6 }}>
        {issues.map((check) => (
          <div
            key={`${check.scenario}-${check.period}-${check.validation_name}`}
            className={check.status === "fail" ? "fail" : "warning"}
            style={
              check.status === "fail"
                ? {
                    fontSize: 12,
                    padding: "10px 12px",
                    background: "#fef2f2",
                    border: "0.5px solid #fecaca",
                    borderRadius: 8,
                    color: "#991b1b",
                  }
                : undefined
            }
          >
            {formatCheckMessage(check)}
          </div>
        ))}
      </div>
    </div>
  );
}
