import Link from "next/link";

export function ResourcesEmptyState({
  title,
  description,
  hint,
}: {
  title: string;
  description: string;
  hint?: string;
}) {
  return (
    <div className="mx-auto max-w-2xl rounded-2xl border border-white/10 bg-white/[0.03] px-6 py-12 text-center">
      <h2 className="text-xl font-semibold text-white">{title}</h2>
      <p className="mt-3 text-slate-400">{description}</p>
      {hint ? <p className="mt-4 text-sm text-slate-500">{hint}</p> : null}
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <Link
          href="/book-demo"
          className="inline-flex h-10 items-center rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-5 text-sm font-semibold text-slate-950"
        >
          Book a demo
        </Link>
        <Link
          href="/studio"
          className="inline-flex h-10 items-center rounded-full border border-white/15 px-5 text-sm text-slate-300 transition hover:bg-white/5"
        >
          Open Studio
        </Link>
      </div>
    </div>
  );
}
