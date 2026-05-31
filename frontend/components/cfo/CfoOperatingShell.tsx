"use client";

import type { ReactNode } from "react";

export type OperatingSection = {
  id: string;
  label: string;
};

type Props = {
  periodLabel: string;
  sections: OperatingSection[];
  activeSection: string;
  onSectionChange: (id: string) => void;
  validationStatus: "ok" | "warn" | "fail" | "unknown";
  validationDetail?: string;
  onRefresh?: () => void;
  busy?: boolean;
  controls: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
};

export function CfoOperatingShell({
  periodLabel,
  sections,
  activeSection,
  onSectionChange,
  validationStatus,
  validationDetail,
  onRefresh,
  busy,
  controls,
  footer,
  children,
}: Props) {
  const chipClass =
    validationStatus === "ok"
      ? "ok"
      : validationStatus === "fail"
        ? "fail"
        : validationStatus === "warn"
          ? "warn"
          : "";

  return (
    <div className="os-shell">
      <header className="os-header">
        <div>
          <div className="os-logo">
            SMPL <em>· Operating Intelligence</em>
          </div>
          <div className="os-tagline">We make finance simple — live executive operating review</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span className="os-period-pill">{periodLabel}</span>
          {chipClass ? (
            <span className={`os-validation-chip ${chipClass}`} title={validationDetail}>
              {validationStatus === "ok" ? "Validation clear" : validationDetail ?? "Review validation"}
            </span>
          ) : null}
          {onRefresh && (
            <button type="button" className="os-btn-primary" onClick={onRefresh} disabled={busy}>
              {busy ? "Refreshing…" : "Refresh"}
            </button>
          )}
        </div>
      </header>

      <nav className="os-nav" aria-label="Operating review sections">
        {sections.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`os-nav-btn${activeSection === s.id ? " active" : ""}`}
            onClick={() => onSectionChange(s.id)}
          >
            {s.label}
          </button>
        ))}
      </nav>

      <div className="os-controls">{controls}</div>

      <div className="os-slide">{children}</div>

      {footer && (
        <footer className="os-footer">
          <div className="os-footer-note">
            Primary experience: operating intelligence on this dashboard. Exports are secondary close artifacts.
          </div>
          {footer}
        </footer>
      )}
    </div>
  );
}
