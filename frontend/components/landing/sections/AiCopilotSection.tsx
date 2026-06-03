import { Bot, User } from "lucide-react";

import { SectionReveal } from "../motion";

const RESPONSE = {
  driver: "GTM spend ran 4.2% above plan while revenue beat by 1.1%.",
  impact: "EBITDA miss of $186K vs plan for May; YTD −3.2% vs budget.",
  root: "Paid acquisition CAC increased 18% with flat SQL→opportunity conversion.",
  recommendation: "Reallocate $400K from paid to partner-sourced pipeline in Q3.",
  board: "Growth quality is improving; efficiency is the board focus for H2.",
};

export function AiCopilotSection() {
  return (
    <section id="copilot" className="bg-white px-6 py-20 text-slate-950 md:py-24">
      <div className="mx-auto max-w-7xl">
        <div className="grid items-start gap-12 lg:grid-cols-2 lg:gap-14">
          <SectionReveal>
            <p className="text-sm font-semibold uppercase tracking-widest text-violet-600">
              AI CFO Copilot
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900 md:text-5xl">
              Ask why — get drivers, impact, and a board-ready summary.
            </h2>
            <p className="mt-4 text-lg leading-relaxed text-slate-600">
              SMPL is not generic AI text generation. Answers are grounded in reconciled financial
              and operating data with clear lineage to source systems.
            </p>
            <ul className="mt-8 space-y-3 text-sm text-slate-600">
              <li className="flex gap-2">
                <span className="font-semibold text-slate-900">1.</span> Primary driver with variance context
              </li>
              <li className="flex gap-2">
                <span className="font-semibold text-slate-900">2.</span> Financial and operational root cause
              </li>
              <li className="flex gap-2">
                <span className="font-semibold text-slate-900">3.</span> Recommended action + board summary
              </li>
            </ul>
          </SectionReveal>

          <div className="rounded-[2rem] border border-slate-200 bg-slate-50 p-6 shadow-xl">
            <div className="mb-4 flex items-center gap-2 border-b border-slate-200 pb-4">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-100 text-violet-700">
                <Bot size={18} />
              </div>
              <span className="font-semibold text-slate-900">SMPL Copilot</span>
            </div>

            <div className="mb-4 flex justify-end">
              <div className="flex max-w-[90%] gap-2 rounded-2xl rounded-br-md bg-slate-900 px-4 py-3 text-sm text-white">
                <User size={16} className="mt-0.5 shrink-0 opacity-70" />
                <span>Why did EBITDA miss plan this month?</span>
              </div>
            </div>

            <div className="space-y-3 rounded-2xl border border-teal-200 bg-gradient-to-br from-teal-50 to-white p-5 text-sm">
              <p>
                <span className="font-semibold text-slate-900">Primary driver · </span>
                <span className="text-slate-700">{RESPONSE.driver}</span>
              </p>
              <p>
                <span className="font-semibold text-slate-900">Financial impact · </span>
                <span className="text-slate-700">{RESPONSE.impact}</span>
              </p>
              <p>
                <span className="font-semibold text-slate-900">Operational root cause · </span>
                <span className="text-slate-700">{RESPONSE.root}</span>
              </p>
              <p>
                <span className="font-semibold text-teal-800">Recommendation · </span>
                <span className="text-slate-700">{RESPONSE.recommendation}</span>
              </p>
              <div className="rounded-xl border border-violet-200 bg-violet-50 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-violet-800">
                  Board-ready summary
                </p>
                <p className="mt-1 text-slate-800">{RESPONSE.board}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
