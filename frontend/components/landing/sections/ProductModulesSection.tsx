import {
  GitBranch,
  LineChart,
  Presentation,
  Sparkles,
  Table2,
  Target,
  UsersRound,
  Wallet,
  type LucideIcon,
} from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { PRODUCT_MODULES } from "../constants";
import { SectionReveal } from "../motion";
import { ModulePreview } from "../visuals/ModulePreview";

const ICONS: Record<string, LucideIcon> = {
  LineChart,
  Target,
  UsersRound,
  Table2,
  Wallet,
  Presentation,
  Sparkles,
  GitBranch,
};

const PREVIEW_VARIANTS = ["bars", "line", "grid", "bars", "line", "grid", "chat", "bars"] as const;

export function ProductModulesSection() {
  return (
    <section id="modules" className="bg-slate-100 px-6 py-20 text-slate-950 md:py-24">
      <div className="mx-auto max-w-7xl">
        <SectionReveal>
          <p className="text-sm font-semibold uppercase tracking-widest text-teal-700">
            Platform modules
          </p>
          <h2 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight text-slate-900 md:text-5xl">
            Eight modules. One AI-native CFO operating system.
          </h2>
          <p className="mt-4 max-w-2xl text-lg text-slate-600">
            Not a spreadsheet add-on — a governed intelligence layer for revenue, GTM, workforce,
            cash, and board reporting.
          </p>
        </SectionReveal>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {PRODUCT_MODULES.map((mod, i) => {
            const Icon = ICONS[mod.icon] ?? Sparkles;
            return (
              <Card
                key={mod.title}
                className="h-full overflow-hidden rounded-3xl border-slate-200/80 bg-white text-slate-950 shadow-md transition hover:border-teal-300 hover:shadow-lg"
              >
                <CardContent className="flex h-full flex-col p-6">
                  <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-500/15 to-violet-500/15 text-teal-700">
                    <Icon size={22} />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-900">{mod.title}</h3>
                  <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-600">{mod.benefit}</p>
                  <div className="mt-5 border-t border-slate-100 pt-4">
                    <ModulePreview variant={PREVIEW_VARIANTS[i] ?? "bars"} />
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}
