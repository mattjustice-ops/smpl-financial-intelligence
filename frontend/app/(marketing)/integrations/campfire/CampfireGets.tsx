"use client";

import { useState } from "react";

const PANELS = [
  {
    id: "campfire",
    label: "Campfire data",
    title: "Actuals that anchor your financial model.",
    body: "The partner-built integration brings Campfire data into SMPL.ai. Accounts, entities, and departments map to your model, with a tie-out reviewed before go-live.",
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
    items: [
      "Monthly management reporting",
      "Budget versus actuals",
      "Variance commentary",
      "SaaS performance metrics",
      "Board-ready financial reporting",
    ],
  },
] as const;

export function CampfireGets() {
  const [id, setId] = useState<(typeof PANELS)[number]["id"]>("campfire");
  const panel = PANELS.find((p) => p.id === id) ?? PANELS[0];

  return (
    <div>
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="What the connection includes">
        {PANELS.map((p) => {
          const selected = p.id === panel.id;
          return (
            <button
              key={p.id}
              type="button"
              role="tab"
              aria-selected={selected}
              onClick={() => setId(p.id)}
              className={`rounded-full px-4 py-2 text-sm ${
                selected
                  ? "bg-teal-400 text-slate-950"
                  : "border border-white/15 text-slate-300 hover:border-teal-400/40"
              }`}
            >
              {p.label}
            </button>
          );
        })}
      </div>
      <div className="mt-8" role="tabpanel">
        <h3 className="text-2xl font-semibold text-white">{panel.title}</h3>
        <p className="mt-3 max-w-2xl text-slate-300">{panel.body}</p>
        {panel.id === "campfire" ? (
          <p className="mt-3 text-sm text-slate-400">Read-only. No changes are posted back to Campfire.</p>
        ) : null}
        <ul className="mt-6 space-y-3">
          {panel.items.map((item) => (
            <li key={item} className="border-b border-white/10 pb-3 text-slate-200">
              {item}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
