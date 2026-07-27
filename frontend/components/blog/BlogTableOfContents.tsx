import type { TocHeading } from "@/lib/sanity/headings";

type BlogTableOfContentsProps = {
  headings: TocHeading[];
};

function TocList({ headings }: { headings: TocHeading[] }) {
  return (
    <ol className="mt-3 space-y-2.5">
      {headings.map((heading) => (
        <li
          key={heading.id}
          className={heading.level === 3 ? "pl-3" : undefined}
        >
          <a
            href={`#${heading.id}`}
            className="block text-sm leading-snug text-slate-400 transition hover:text-teal-200"
          >
            {heading.text}
          </a>
        </li>
      ))}
    </ol>
  );
}

export function BlogTableOfContents({ headings }: BlogTableOfContentsProps) {
  if (!headings.length) return null;

  return (
    <>
      {/* Mobile: collapsible list at top of article flow */}
      <details className="group mb-8 rounded-2xl border border-white/10 bg-white/[0.02] px-4 py-3 lg:hidden">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-medium text-slate-200 marker:content-none [&::-webkit-details-marker]:hidden">
          <span>On this page</span>
          <span
            aria-hidden
            className="text-slate-500 transition group-open:rotate-180"
          >
            ▾
          </span>
        </summary>
        <nav aria-label="Table of contents" className="pb-2 pt-1">
          <TocList headings={headings} />
        </nav>
      </details>

      {/* Desktop: left sidebar (stickiness applied by parent grid cell) */}
      <nav aria-label="Table of contents" className="hidden lg:block">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
          On this page
        </p>
        <TocList headings={headings} />
      </nav>
    </>
  );
}
