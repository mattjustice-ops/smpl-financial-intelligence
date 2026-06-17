import {
  goLiveMilestones,
  goLiveProgressMeta,
  milestoneStats,
  overallPercent,
} from "@/lib/go-live-progress";

function progressBarColor(percent: number): string {
  if (percent >= 80) return "bg-teal-400";
  if (percent >= 50) return "bg-cyan-400";
  if (percent >= 25) return "bg-amber-400";
  return "bg-slate-500";
}

/** e.g. "gl-5a: staging..." → "gl-5a" */
function currentFocusItemId(focus: string | undefined): string | null {
  if (!focus) return null;
  const match = focus.match(/^([a-z]{2,3}-\d+[a-z]?)\b/i);
  return match ? match[1]!.toLowerCase() : null;
}

function itemIdBadgeClass(done: boolean, isFocus: boolean): string {
  if (isFocus && !done) {
    return "border-amber-400/50 bg-amber-400/15 text-amber-200";
  }
  if (done) {
    return "border-teal-400/40 bg-teal-400/10 text-teal-300";
  }
  return "border-white/15 bg-white/5 text-slate-400";
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

export function GoLiveProgressDashboard() {
  const overall = overallPercent();
  const focusId = currentFocusItemId(
    "currentFocus" in goLiveProgressMeta ? goLiveProgressMeta.currentFocus : undefined,
  );
  const milestoneRows = goLiveMilestones.map((milestone) => ({
    milestone,
    stats: milestoneStats(milestone),
  }));

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 md:py-16">
      <div className="mb-10">
        <p className="text-xs font-semibold uppercase tracking-widest text-teal-400">
          Internal · temporary
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white md:text-4xl">
          {goLiveProgressMeta.title}
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-400 md:text-base">
          {goLiveProgressMeta.subtitle}
        </p>
        <p className="mt-2 text-xs text-slate-500">
          Last updated {goLiveProgressMeta.lastUpdated} · edit{" "}
          <code className="rounded bg-white/5 px-1.5 py-0.5 text-teal-300">
            frontend/lib/go-live-progress.ts
          </code>{" "}
          and set items to <code className="rounded bg-white/5 px-1.5 py-0.5">done: true</code>
        </p>
        {"currentFocus" in goLiveProgressMeta && goLiveProgressMeta.currentFocus ? (
          <p className="mt-3 rounded-lg border border-teal-400/20 bg-teal-400/5 px-3 py-2 text-sm text-teal-200">
            Current focus:{" "}
            {focusId ? (
              <code className="mr-1.5 rounded bg-amber-400/15 px-1.5 py-0.5 text-xs font-semibold text-amber-200">
                {focusId}
              </code>
            ) : null}
            {focusId
              ? goLiveProgressMeta.currentFocus.replace(new RegExp(`^${focusId}:\\s*`, "i"), "")
              : goLiveProgressMeta.currentFocus}
          </p>
        ) : null}
        <p className="mt-2 text-xs text-slate-500">
          Item IDs: <code className="text-slate-400">gl-*</code> full go-live ·{" "}
          <code className="text-slate-400">poc-*</code> onboarding ·{" "}
          <code className="text-slate-400">dr-/am-/ca-*</code> earlier milestones
        </p>
      </div>

      <section className="mb-10 rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 p-6 md:p-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-slate-500">Overall</p>
            <p className="mt-1 text-4xl font-semibold tabular-nums text-white md:text-5xl">
              {overall}%
            </p>
          </div>
          <p className="max-w-sm text-sm text-slate-400">
            Weighted across all checklist items in the milestones below.
          </p>
        </div>
        <div className="mt-5">
          <ProgressBar percent={overall} />
        </div>
      </section>

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {milestoneRows.map(({ milestone, stats }) => (
          <div
            key={milestone.id}
            className="rounded-xl border border-white/10 bg-slate-900/60 p-4"
          >
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {milestone.name}
            </p>
            <p className="mt-2 text-3xl font-semibold tabular-nums text-white">
              {stats.percent}%
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {stats.done} of {stats.total} complete
            </p>
            <div className="mt-3">
              <ProgressBar percent={stats.percent} />
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-6">
        {milestoneRows.map(({ milestone, stats }) => (
          <section
            key={milestone.id}
            className="rounded-2xl border border-white/10 bg-slate-950/80 p-5 md:p-6"
          >
            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-white/5 pb-4">
              <div>
                <h2 className="text-lg font-semibold text-white">{milestone.name}</h2>
                <p className="mt-1 text-sm text-slate-400">{milestone.summary}</p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-semibold tabular-nums text-teal-300">
                  {stats.percent}%
                </p>
                <p className="text-xs text-slate-500">
                  {stats.done}/{stats.total} done
                </p>
              </div>
            </div>

            <ul className="mt-4 space-y-2">
              {milestone.items.map((item) => {
                const isFocus = focusId === item.id.toLowerCase();
                return (
                  <li
                    key={item.id}
                    className={`flex items-start gap-3 rounded-lg px-2 py-2 text-sm hover:bg-white/[0.02] ${
                      isFocus && !item.done ? "border border-amber-400/20 bg-amber-400/[0.04]" : ""
                    }`}
                  >
                    <span
                      className={`mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-bold ${
                        item.done
                          ? "border-teal-400/50 bg-teal-400/15 text-teal-300"
                          : "border-white/15 bg-white/5 text-slate-500"
                      }`}
                      aria-hidden
                    >
                      {item.done ? "✓" : ""}
                    </span>
                    <code
                      className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 font-mono text-[11px] font-semibold leading-snug ${itemIdBadgeClass(item.done, isFocus)}`}
                      title="Checklist item ID"
                    >
                      {item.id}
                    </code>
                    <span className={item.done ? "text-slate-300 line-through" : "text-slate-200"}>
                      {item.label}
                      {isFocus && !item.done ? (
                        <span className="ml-2 text-xs font-medium text-amber-300/90">← next</span>
                      ) : null}
                    </span>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>
    </main>
  );
}
