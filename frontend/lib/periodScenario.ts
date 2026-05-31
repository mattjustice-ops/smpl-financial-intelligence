/** Period/scenario helpers shared by executive and workforce views. */

export function monthRange(startPeriod: string, endPeriod: string) {
  const [startYear, startMonth] = startPeriod.split("-").map(Number);
  const [endYear, endMonth] = endPeriod.split("-").map(Number);
  const periods: string[] = [];
  let year = startYear;
  let month = startMonth;
  while (year < endYear || (year === endYear && month <= endMonth)) {
    periods.push(`${year}-${String(month).padStart(2, "0")}`);
    month += 1;
    if (month === 13) {
      month = 1;
      year += 1;
    }
  }
  return periods;
}

export function normalizePeriodKey(period: string) {
  return period.slice(0, 7);
}

/** Match ExecutiveFlow Combined slice: Actual through close month, Forecast after. */
export function scenarioForPeriod(period: string, selectedScenario: string) {
  if (selectedScenario === "Combined") return period <= "2026-05" ? "Actual" : "Forecast";
  return selectedScenario;
}

export function workforceApiScenario(scenario: string) {
  if (scenario === "Budget") return "Budget";
  if (scenario === "Actual") return "Actual";
  if (scenario === "Combined") return "Combined";
  return "Forecast";
}
