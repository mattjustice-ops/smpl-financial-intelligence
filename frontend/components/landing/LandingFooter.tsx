import Link from "next/link";

export function LandingFooter() {
  return (
    <footer className="border-t border-white/10 bg-slate-950 px-6 py-10">
      <div className="mx-auto flex max-w-7xl flex-col justify-between gap-6 text-sm text-slate-500 md:flex-row md:items-center">
        <p>© 2026 SMPL.ai · The AI operating system for SaaS finance teams.</p>
        <div className="flex flex-wrap gap-6">
          <Link href="/board" className="transition hover:text-white">
            Board demo
          </Link>
          <Link href="/app" className="transition hover:text-white">
            Platform
          </Link>
          <a href="#trust" className="transition hover:text-white">
            Trust layer
          </a>
        </div>
      </div>
    </footer>
  );
}
