import { CircleDot } from "lucide-react";

import { OPERATING_MODEL } from "../constants";
import { SectionReveal } from "../motion";

export function OperatingModelSection() {
  return (
    <section id="model" className="bg-white px-6 py-20 text-slate-950 md:py-24">
      <div className="mx-auto max-w-7xl">
        <SectionReveal className="max-w-3xl">
          <p className="text-sm font-semibold uppercase tracking-widest text-teal-600">
            Connected operating model
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900 md:text-5xl">
            From pipeline to workforce — one chain of cause and effect.
          </h2>
          <p className="mt-4 text-lg leading-relaxed text-slate-600">
            SMPL links GTM activity to ARR, GAAP revenue, profitability, cash, and headcount so
            leaders see what happened, why it happened, and what is likely next.
          </p>
        </SectionReveal>

        <div className="op-model-root mt-12">
          {OPERATING_MODEL.map((_, index) => (
            <input
              key={`radio-${index}`}
              type="radio"
              name="smpl-operating-model"
              id={`smpl-op-${index}`}
              defaultChecked={index === 0}
              className="sr-only"
            />
          ))}

          <div className="op-model-labels overflow-x-auto pb-2">
            <div className="flex min-w-[720px] gap-2 md:min-w-0">
              {OPERATING_MODEL.map((step, index) => (
                <label
                  key={step.step}
                  htmlFor={`smpl-op-${index}`}
                  className="op-model-tab flex flex-1 cursor-pointer flex-col items-center rounded-2xl border border-slate-200 bg-slate-50 px-2 py-4 text-center transition hover:border-slate-300 md:px-3"
                >
                  <span className="op-model-tab-num mb-2 flex h-9 w-9 items-center justify-center rounded-full bg-slate-200 text-sm font-bold text-slate-700">
                    {index + 1}
                  </span>
                  <span className="text-xs font-semibold text-slate-900 sm:text-sm">{step.step}</span>
                </label>
              ))}
            </div>
          </div>

          {OPERATING_MODEL.map((step, index) => (
            <div
              key={`panel-${step.step}`}
              className="op-model-panel mt-8 rounded-2xl border border-teal-200/80 bg-gradient-to-br from-teal-50/90 to-white p-6 shadow-sm"
              data-op-panel={index}
            >
              <div className="flex items-start gap-3">
                <CircleDot className="mt-1 shrink-0 text-teal-600" size={20} />
                <div>
                  <p className="text-lg font-semibold text-slate-900">{step.step}</p>
                  <p className="mt-2 text-base leading-relaxed text-slate-600">{step.hint}</p>
                </div>
              </div>
            </div>
          ))}

          <div className="op-model-pills mt-5 flex flex-wrap gap-2">
            {OPERATING_MODEL.map((step, index) => (
              <label
                key={`pill-${step.step}`}
                htmlFor={`smpl-op-${index}`}
                className="op-model-pill cursor-pointer rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600 ring-1 ring-slate-200 transition hover:ring-teal-300"
              >
                {step.step}
              </label>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
