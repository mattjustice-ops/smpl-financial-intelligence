import Link from "next/link";

export function ResourcesEmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="mx-auto max-w-2xl rounded-2xl border border-white/10 bg-white/[0.03] px-6 py-12 text-center">
      <h2 className="text-xl font-semibold text-white">{title}</h2>
      <p className="mt-3 text-slate-400">{description}</p>
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <Link
          href="/book-demo"
          className="inline-flex h-10 items-center rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-5 text-sm font-semibold text-slate-950"
        >
          Book a demo
        </Link>
      </div>
    </div>
  );
}
