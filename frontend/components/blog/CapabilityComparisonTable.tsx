export type ComparisonMark = "yes" | "partial" | "no" | string;

export type CapabilityComparisonTableProps = {
  columns?: string[] | null;
  rows?: Array<{
    _key?: string;
    capability?: string | null;
    marks?: ComparisonMark[] | null;
  }> | null;
  caption?: string | null;
  showLegend?: boolean | null;
};

const MARK_DISPLAY: Record<string, { glyph: string; className: string; label: string }> = {
  yes: {
    glyph: "✓",
    className: "text-teal-300",
    label: "core strength",
  },
  partial: {
    glyph: "~",
    className: "text-slate-400",
    label: "partial or possible with effort",
  },
  no: {
    glyph: "—",
    className: "text-slate-500",
    label: "not what it's designed for",
  },
};

function resolveMark(mark: ComparisonMark | undefined) {
  if (!mark) return MARK_DISPLAY.no;
  if (MARK_DISPLAY[mark]) return MARK_DISPLAY[mark];
  // Allow seed/CMS to pass glyphs directly
  if (mark === "✓") return MARK_DISPLAY.yes;
  if (mark === "~") return MARK_DISPLAY.partial;
  if (mark === "—" || mark === "-") return MARK_DISPLAY.no;
  return { glyph: mark, className: "text-slate-400", label: mark };
}

export function CapabilityComparisonTable({
  columns,
  rows,
  caption,
  showLegend = true,
}: CapabilityComparisonTableProps) {
  const cols = (columns ?? []).filter(Boolean);
  const dataRows = (rows ?? []).filter((row) => row?.capability);

  if (!cols.length || !dataRows.length) return null;

  return (
    <figure className="mt-8">
      <div className="overflow-x-auto rounded-xl border border-white/10 bg-slate-900/70 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
        <table className="w-full min-w-[44rem] border-collapse text-sm">
          {caption ? <caption className="sr-only">{caption}</caption> : null}
          <thead>
            <tr className="border-b border-white/10 bg-slate-800/90">
              <th
                scope="col"
                className="sticky left-0 z-10 bg-slate-800 px-3 py-3 text-left text-xs font-semibold uppercase tracking-[0.08em] text-slate-300 sm:px-4"
              >
                Capability
              </th>
              {cols.map((col) => (
                <th
                  key={col}
                  scope="col"
                  className="px-2 py-3 text-center text-xs font-semibold leading-snug text-slate-200 sm:px-3"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataRows.map((row, rowIndex) => {
              const marks = row.marks ?? [];
              return (
                <tr
                  key={row._key || `${row.capability}-${rowIndex}`}
                  className="border-b border-white/10 last:border-b-0 odd:bg-white/[0.02] even:bg-transparent"
                >
                  <th
                    scope="row"
                    className="sticky left-0 z-10 bg-slate-900/95 px-3 py-2.5 text-left font-medium text-slate-200 sm:px-4"
                  >
                    {row.capability}
                  </th>
                  {cols.map((col, colIndex) => {
                    const resolved = resolveMark(marks[colIndex]);
                    return (
                      <td
                        key={`${row.capability}-${col}`}
                        className={`px-2 py-2.5 text-center text-base font-medium sm:px-3 ${resolved.className}`}
                        title={resolved.label}
                        aria-label={`${row.capability}: ${col} — ${resolved.label}`}
                      >
                        {resolved.glyph}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {showLegend !== false ? (
        <figcaption className="mt-3 text-xs leading-relaxed text-slate-500">
          <span className="text-teal-300">✓</span> core strength
          <span className="mx-2 text-slate-600">·</span>
          <span className="text-slate-400">~</span> partial or possible with
          effort
          <span className="mx-2 text-slate-600">·</span>
          <span className="text-slate-500">—</span> not what it&apos;s designed
          for
        </figcaption>
      ) : null}
    </figure>
  );
}
