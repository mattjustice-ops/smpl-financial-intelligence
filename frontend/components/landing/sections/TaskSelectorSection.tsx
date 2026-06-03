import { MessageSquareQuote } from "lucide-react";

import { UNDERSTAND_TASKS } from "../constants";
import { SectionReveal } from "../motion";

export function TaskSelectorSection() {
  return (
    <section id="understand" className="bg-slate-950 px-6 py-20 md:py-24">
      <div className="mx-auto max-w-7xl">
        <SectionReveal className="max-w-3xl">
          <p className="text-sm font-semibold uppercase tracking-widest text-violet-400">
            Executive questions
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-5xl">
            What do you want to understand?
          </h2>
          <p className="mt-4 text-lg text-slate-400">
            Select a question — SMPL surfaces drivers, impact, and recommended actions from your
            governed operating model.
          </p>
        </SectionReveal>

        <div className="understand-root mt-12">
          {UNDERSTAND_TASKS.map((_, index) => (
            <input
              key={`radio-${index}`}
              type="radio"
              name="smpl-understand"
              id={`sq-${index}`}
              defaultChecked={index === 0}
              className="sr-only"
            />
          ))}

          <div className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr]">
            <div className="understand-labels grid gap-2 sm:grid-cols-2">
              {UNDERSTAND_TASKS.map((t, index) => (
                <label
                  key={t.id}
                  htmlFor={`sq-${index}`}
                  className="understand-tab cursor-pointer rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3.5 text-left text-sm font-medium text-slate-300 transition hover:border-white/25 hover:bg-white/[0.08]"
                >
                  {t.question}
                </label>
              ))}
            </div>

            <div className="understand-answers relative min-h-[280px]">
              {UNDERSTAND_TASKS.map((task, index) => (
                <div
                  key={task.id}
                  className="understand-panel rounded-[1.75rem] border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 p-6 shadow-2xl"
                  data-sq-panel={index}
                >
                  <div className="mb-4 flex items-center gap-2 text-teal-300">
                    <MessageSquareQuote size={18} />
                    <span className="text-sm font-medium">SMPL answer</span>
                  </div>
                  <div className="space-y-4">
                    <h3 className="text-xl font-semibold text-white">{task.answer.headline}</h3>
                    <div className="space-y-3 text-sm leading-relaxed text-slate-400">
                      <p>
                        <span className="font-medium text-slate-200">Primary driver · </span>
                        {task.answer.driver}
                      </p>
                      <p>
                        <span className="font-medium text-slate-200">Financial impact · </span>
                        {task.answer.impact}
                      </p>
                      <p>
                        <span className="font-medium text-teal-300">Recommendation · </span>
                        {task.answer.action}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
