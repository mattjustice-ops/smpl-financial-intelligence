"use client";

import { useState } from "react";

const PANELS = [
  {
    id: "campfire",
    label: "Campfire data",
    title: "Actuals that anchor your financial model.",
    body: "The partner-built integration brings Campfire data into SMPL.ai. Accounts, entities, and departments map to your model, with a tie-out reviewed before go-live.",
    note: "Read-only · No changes posted back to Campfire",
    items: [
      "General ledger actuals",
      "Chart of accounts, departments, and entities",
      "Balance sheet balances and cash activity",
      "Revenue contracts, recognized and deferred revenue, MRR",
      "Historical actuals imported during onboarding",
    ],
  },
  {
    id: "planning",
    label: "Connected planning",
    title: "One model for the decisions ahead.",
    body: "Connect Campfire actuals with data from your CRM, billing, and workforce systems. Update the plan using the same definitions your team already works with.",
    note: "Built around your accounts and metrics",
    items: [
      "Budgeting and forecast updates",
      "Revenue and subscription planning",
      "Headcount and hiring scenarios",
      "Cash planning and runway",
      "Connected financial statements",
    ],
  },
  {
    id: "reporting",
    label: "Reporting outputs",
    title: "From financial results to a useful business discussion.",
    body: "Bring the numbers and their supporting context into the monthly package. Review performance, explain material movements, and carry the implications into your plans.",
    note: "Validated results with supporting detail",
    items: [
      "Monthly management reporting",
      "Budget versus actuals",
      "Variance commentary",
      "SaaS performance metrics",
      "Board-ready financial reporting",
    ],
  },
] as const;

function Chevron() {
  return (
    <svg viewBox="0 0 20 20" className="h-4 w-4 shrink-0 text-slate-500" aria-hidden>
      <path d="M7 4 L13 10 L7 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function CampfireGets() {
  const [id, setId] = useState<(typeof PANELS)[number]["id"]>("campfire");
  const panel = PANELS.find((p) => p.id === id) ?? PANELS[0];

  return (
    <div>
      <div className="border-b border-white/10" role="tablist" aria-label="What the connection includes">
        <div className="flex flex-wrap gap-x-8">
          {PANELS.map((p) => {
            const selected = p.id === panel.id;
            return (
              <button
                key={p.id}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => setId(p.id)}
                className={`-mb-px border-b-2 pb-3 text-sm ${
                  selected ? "border-teal-300 text-teal-300" : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                {p.label}
              </button>
            );
          })}
        </div>
      </div>
      <div className="mt-8 grid items-start gap-8 md:grid-cols-2 md:gap-12" role="tabpanel">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 md:p-8">
          <h3 className="text-2xl font-semibold tracking-tight text-white md:text-3xl">{panel.title}</h3>
          <p className="mt-4 text-sm leading-relaxed text-slate-400">{panel.body}</p>
          <p className="mt-6 inline-block rounded-md bg-teal-400/15 px-2.5 py-1 text-xs font-medium text-teal-300">{panel.note}</p>
        </div>
        <ul>
          {panel.items.map((item) => (
            <li key={item} className="flex items-center justify-between gap-4 border-b border-white/10 py-4 text-slate-200">
              <span>{item}</span>
              <Chevron />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
