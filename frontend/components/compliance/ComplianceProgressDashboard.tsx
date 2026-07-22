import {
  compliancePhases,
  complianceProgressMeta,
  complianceSections,
  overallCounts,
  overallPercent,
  sectionStats,
  statusLabel,
  type ComplianceStatus,
} from "@/lib/compliance/progress";

function progressBarColor(percent: number): string {
  if (percent >= 80) return "bg-teal-400";
  if (percent >= 50) return "bg-cyan-400";
  if (percent >= 25) return "bg-amber-400";
  return "bg-slate-500";
}

function ProgressBar({ percent }: { percent: number }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
      <div
        className={`h-full rounded-full transition-all ${progressBarColor(percent)}`}
        style={{ width: `${percent}%` }}
      />
    </div>
  );
}

function statusMark(status: ComplianceStatus): string {
  switch (status) {
    case "done":
      return "✓";
    case "in_progress":
      return "~";
    case "needs_owner":
      return "!";
    default:
      return "";
  }
}

function statusCircleClass(status: ComplianceStatus): string {
  switch (status) {
    case "done":
      return "border-teal-400/50 bg-teal-400/15 text-teal-300";
    case "in_progress":
      return "border-cyan-400/50 bg-cyan-400/15 text-cyan-200";
    case "needs_owner":
      return "border-amber-400/50 bg-amber-400/15 text-amber-200";
    default:
      return "border-white/15 bg-white/5 text-slate-500";
  }
}

function statusPillClass(status: ComplianceStatus): string {
  switch (status) {
    case "done":
      return "border-teal-400/40 bg-teal-400/10 text-teal-300";
    case "in_progress":
      return "border-cyan-400/40 bg-cyan-400/10 text-cyan-200";
    case "needs_owner":
      return "border-amber-400/40 bg-amber-400/10 text-amber-200";
    default:
      return "border-white/15 bg-white/5 text-slate-400";
  }
}

function phaseCardClass(status: ComplianceStatus): string {
  if (status === "in_progress") {
    return "border-cyan-400/30 bg-cyan-400/[0.06] ring-1 ring-cyan-400/20";
  }
  if (status === "done") {
    return "border-teal-400/30 bg-teal-400/[0.06]";
  }
  return "border-white/10 bg-slate-900/60";
}

export function ComplianceProgressDashboard() {
  const overall = overallPercent();
  const counts = overallCounts();
  const sectionRows = complianceSections.map((section) => ({
    section,
    stats: sectionStats(section),
  }));

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 md:py-16">
      <div
        className="mb-8 rounded-2xl border border-amber-400/30 bg-amber-400/10 px-5 py-4 md:px-6"
        role="status"
      >
        <p className="text-sm font-semibold text-amber-100 md:text-base">
          Not SOC 2 certified — readiness in progress
        </p>
        <p className="mt-1.5 text-sm leading-relaxed text-amber-100/80">
          SMPL is pursuing SOC 2 Type I. We are not “SOC 2 compliant” or “SOC 2 certified”
          until an independent CPA firm issues a report. This page tracks readiness work only.
        </p>
      </div>

      <div className="mb-10">
        <p className="text-xs font-semibold uppercase tracking-widest text-teal-400">
          Trust · Security
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white md:text-4xl">
          {complianceProgressMeta.title}
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-400 md:text-base">
          {complianceProgressMeta.subtitle}
        </p>
        <p className="mt-2 text-xs text-slate-500">
          Last updated {complianceProgressMeta.lastUpdated} · statuses live in{" "}
          <code className="rounded bg-white/5 px-1.5 py-0.5 text-teal-300">
            {complianceProgressMeta.dataFile}
          </code>
        </p>
        {complianceProgressMeta.currentFocus ? (
          <p className="mt-3 rounded-lg border border-teal-400/20 bg-teal-400/5 px-3 py-2 text-sm text-teal-200">
            Current focus: {complianceProgressMeta.currentFocus}
          </p>
        ) : null}
      </div>

      <section className="mb-8 rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 p-6 md:p-8">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
          What “done” means
        </h2>
        <p className="mt-3 text-base leading-relaxed text-slate-200 md:text-lg">
          {complianceProgressMeta.definitionOfDone}
        </p>
        <p className="mt-3 text-sm text-slate-500">{complianceProgressMeta.salesLanguage}</p>
      </section>

      <section className="mb-10 rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 p-6 md:p-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-slate-500">Readiness</p>
            <p className="mt-1 text-4xl font-semibold tabular-nums text-white md:text-5xl">
              {overall}%
            </p>
          </div>
          <p className="max-w-sm text-sm text-slate-400">
            {counts.done} done · {counts.inProgress} in progress · {counts.needsOwner} needs
            owner · {counts.open} open ({counts.total} items). In-progress counts half toward
            the percentage.
          </p>
        </div>
        <div className="mt-5">
          <ProgressBar percent={overall} />
        </div>
      </section>

      <section className="mb-10">
        <h2 className="mb-4 text-lg font-semibold text-white">Phase map</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {compliancePhases.map((phase, index) => (
            <div
              key={phase.id}
              className={`rounded-xl border p-4 ${phaseCardClass(phase.status)}`}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Phase {index + 1}
                </p>
                <span
                  className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${statusPillClass(phase.status)}`}
                >
                  {statusLabel(phase.status)}
                </span>
              </div>
              <p className="mt-2 text-lg font-semibold text-white">{phase.name}</p>
              <p className="mt-2 text-xs leading-relaxed text-slate-500">{phase.exitCriteria}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="mb-6 flex flex-wrap gap-3 text-xs text-slate-500">
        {(
          [
            ["done", "Done"],
            ["in_progress", "In progress"],
            ["needs_owner", "Needs owner"],
            ["open", "Open"],
          ] as const
        ).map(([status, label]) => (
          <span key={status} className="inline-flex items-center gap-1.5">
            <span
              className={`inline-flex h-4 w-4 items-center justify-center rounded-full border text-[9px] font-bold ${statusCircleClass(status)}`}
            >
              {statusMark(status)}
            </span>
            {label}
          </span>
        ))}
      </div>

      <div className="space-y-6">
        {sectionRows.map(({ section, stats }) => (
          <section
            key={section.id}
            className="rounded-2xl border border-white/10 bg-slate-950/80 p-5 md:p-6"
          >
            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-white/5 pb-4">
              <div>
                <h2 className="text-lg font-semibold text-white">{section.name}</h2>
                <p className="mt-1 text-sm text-slate-400">{section.summary}</p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-semibold tabular-nums text-teal-300">
                  {stats.percent}%
                </p>
                <p className="text-xs text-slate-500">
                  {stats.done}/{stats.total} done
                  {stats.needsOwner > 0 ? ` · ${stats.needsOwner} need owner` : ""}
                </p>
              </div>
            </div>

            <ul className="mt-4 space-y-2">
              {section.items.map((item) => (
                <li
                  key={item.id}
                  className={`flex items-start gap-3 rounded-lg px-2 py-2 text-sm hover:bg-white/[0.02] ${
                    item.status === "needs_owner"
                      ? "border border-amber-400/15 bg-amber-400/[0.03]"
                      : item.status === "in_progress"
                        ? "border border-cyan-400/15 bg-cyan-400/[0.03]"
                        : ""
                  }`}
                >
                  <span
                    className={`mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-bold ${statusCircleClass(item.status)}`}
                    aria-label={statusLabel(item.status)}
                  >
                    {statusMark(item.status)}
                  </span>
                  <code
                    className={`mt-0.5 shrink-0 rounded border px-1.5 py-0.5 font-mono text-[11px] font-semibold leading-snug ${statusPillClass(item.status)}`}
                  >
                    {item.id}
                  </code>
                  <span className="min-w-0 flex-1">
                    <span
                      className={
                        item.status === "done"
                          ? "text-slate-400 line-through"
                          : "text-slate-200"
                      }
                    >
                      {item.label}
                    </span>
                    {item.notes ? (
                      <span className="mt-0.5 block text-xs text-slate-500">{item.notes}</span>
                    ) : null}
                  </span>
                  <span
                    className={`mt-0.5 shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${statusPillClass(item.status)}`}
                  >
                    {statusLabel(item.status)}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      <p className="mt-10 text-center text-xs text-slate-600">
        Detailed internal scoreboard:{" "}
        <code className="text-slate-500">{complianceProgressMeta.markdownScoreboard}</code>
      </p>
    </main>
  );
}
