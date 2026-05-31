import type { CSSProperties } from "react";

/** Fixed width for each month column so sections 2–10 line up visually. */
export const DASHBOARD_PERIOD_COLUMN_WIDTH = 108;

const CATEGORY_COLUMN_WIDTH = 220;

export function normalizeDashboardPeriod(period: string): string {
  const match = period.match(/^(\d{4}-\d{2})/);
  return match ? match[1] : period;
}

export function formatDashboardPeriodHeader(periodKey: string): string {
  const match = periodKey.match(/^(\d{4})-(\d{2})$/);
  if (!match) {
    const d = new Date(periodKey);
    if (!Number.isNaN(d.getTime())) {
      return d.toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
    }
    return periodKey;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  return new Date(Date.UTC(year, month - 1, 1)).toLocaleDateString("en-US", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function dashboardTableStyle(periodCount: number, extraTrailingColumns = 0): CSSProperties {
  const periodWidth = periodCount * DASHBOARD_PERIOD_COLUMN_WIDTH;
  const trailingWidth = extraTrailingColumns * DASHBOARD_PERIOD_COLUMN_WIDTH;
  return {
    width: "100%",
    minWidth: CATEGORY_COLUMN_WIDTH + periodWidth + trailingWidth,
    tableLayout: "fixed",
    borderCollapse: "collapse",
    fontSize: 13,
  };
}

export function categoryHeaderStyle(baseTh: CSSProperties): CSSProperties {
  return {
    ...baseTh,
    position: "sticky",
    left: 0,
    background: "#f9fafb",
    zIndex: 2,
    width: CATEGORY_COLUMN_WIDTH,
    minWidth: CATEGORY_COLUMN_WIDTH,
  };
}

export function categoryCellStyle(baseTd: CSSProperties): CSSProperties {
  return {
    ...baseTd,
    position: "sticky",
    left: 0,
    background: "#fff",
    width: CATEGORY_COLUMN_WIDTH,
    minWidth: CATEGORY_COLUMN_WIDTH,
  };
}

export function periodHeaderStyle(baseTh: CSSProperties): CSSProperties {
  return {
    ...baseTh,
    textAlign: "right",
    width: DASHBOARD_PERIOD_COLUMN_WIDTH,
    minWidth: DASHBOARD_PERIOD_COLUMN_WIDTH,
    maxWidth: DASHBOARD_PERIOD_COLUMN_WIDTH,
  };
}

export function periodCellStyle(baseTd: CSSProperties, extra?: CSSProperties): CSSProperties {
  return {
    ...baseTd,
    textAlign: "right",
    width: DASHBOARD_PERIOD_COLUMN_WIDTH,
    minWidth: DASHBOARD_PERIOD_COLUMN_WIDTH,
    maxWidth: DASHBOARD_PERIOD_COLUMN_WIDTH,
    ...extra,
  };
}
