"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BarChart3,
  Brain,
  BriefcaseBusiness,
  CalendarClock,
  CheckCircle2,
  DatabaseZap,
  Layers3,
  LineChart,
  PieChart,
  ShieldCheck,
  Sparkles,
  UsersRound,
} from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

const modules = [
  {
    icon: LineChart,
    title: "Revenue Intelligence",
    description:
      "Connect pipeline, bookings, ARR, revenue recognition, and cash collections into one trusted revenue story.",
  },
  {
    icon: BarChart3,
    title: "Board Reporting",
    description:
      "Generate executive-ready board packages, MD&A narratives, variance commentary, and KPI summaries from live data.",
  },
  {
    icon: UsersRound,
    title: "Workforce Planning",
    description:
      "Model employees, open reqs, hiring timing, quota capacity, payroll, productivity ramps, and scenario impacts.",
  },
  {
    icon: DatabaseZap,
    title: "Financial Forecasting",
    description:
      "Unify budget, actuals, forecast, cash flow, department spend, and operating leverage analysis.",
  },
];

const outcomes = [
  "Reduce manual board reporting effort",
  "Improve forecast confidence",
  "Explain ARR, revenue, cash, and headcount movement",
  "Identify risks before they become misses",
  "Align Finance, Sales, Marketing, CS, and Operations",
  "Turn reporting into executive decision support",
];

const operatingModel = ["Pipeline", "Bookings", "ARR", "Revenue", "EBITDA", "Cash", "Workforce"];

export function SmplAiLandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <header className="sticky top-0 z-50 border-b border-white/10 bg-slate-950/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-teal-400 text-slate-950 shadow-lg shadow-teal-400/20">
              <Sparkles size={18} />
            </div>
            <span className="text-xl font-semibold tracking-tight">SMPL.ai</span>
          </div>
          <nav className="hidden items-center gap-8 text-sm text-slate-300 md:flex">
            <a href="#platform" className="hover:text-white">
              Platform
            </a>
            <a href="#model" className="hover:text-white">
              Operating Model
            </a>
            <a href="#outcomes" className="hover:text-white">
              Outcomes
            </a>
            <a href="#demo" className="hover:text-white">
              Demo
            </a>
          </nav>
          <Link
            href="/board"
            className="inline-flex h-10 items-center justify-center rounded-full bg-white px-5 text-sm font-medium text-slate-950 hover:bg-slate-200"
          >
            Open demo
          </Link>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden px-6 py-24 md:py-32">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(45,212,191,0.22),transparent_35%),radial-gradient(circle_at_bottom_left,rgba(59,130,246,0.16),transparent_35%)]" />
          <div className="relative mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
            <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-teal-300/30 bg-teal-300/10 px-4 py-2 text-sm text-teal-200">
                <Brain size={16} /> AI-powered financial intelligence for SaaS operators
              </div>
              <h1 className="max-w-4xl text-5xl font-semibold tracking-tight md:text-7xl">
                The operating system for SaaS finance teams.
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300 md:text-xl">
                SMPL connects pipeline, ARR, revenue, cash, headcount, and financial statements into one trusted
                platform that explains what happened, why it happened, and what leadership should do next.
              </p>
              <div className="mt-8">
                <Link
                  href="/board"
                  className="inline-flex h-12 items-center justify-center gap-2 rounded-full bg-teal-400 px-7 text-base font-medium text-slate-950 hover:bg-teal-300"
                >
                  View interactive demo <ArrowRight size={18} />
                </Link>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.7, delay: 0.1 }}
            >
              <Card className="rounded-[2rem] border-white/10 bg-white/[0.06] shadow-2xl shadow-black/40 backdrop-blur-xl">
                <CardContent className="p-6">
                  <div className="mb-5 flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-400">May 2026 Board Intelligence</p>
                      <h3 className="text-2xl font-semibold text-white">Executive Summary</h3>
                    </div>
                    <span className="rounded-full bg-emerald-400/15 px-3 py-1 text-xs font-medium text-emerald-300">
                      Validated
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                    {[
                      ["ARR", "$83.4M", "+$0.1M vs plan"],
                      ["Revenue", "$7.18M", "+1.1% vs plan"],
                      ["Cash", "$66.0M", "+$37.4M vs plan"],
                      ["Rule of 40", "28%", "Improving"],
                    ].map(([label, value, note]) => (
                      <div key={label} className="rounded-2xl bg-slate-900/80 p-4">
                        <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
                        <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
                        <p className="mt-1 text-xs text-teal-300">{note}</p>
                      </div>
                    ))}
                  </div>
                  <div className="mt-5 rounded-2xl bg-slate-900/80 p-5">
                    <div className="mb-4 flex items-center justify-between">
                      <p className="font-medium text-white">AI Commentary</p>
                      <Sparkles size={16} className="text-teal-300" />
                    </div>
                    <p className="text-sm leading-6 text-slate-300">
                      Enterprise expansion and partner-sourced pipeline are driving ARR upside, while paid acquisition
                      efficiency remains the largest GTM optimization opportunity. Cash is outperforming plan due to
                      annual billings, creating flexibility to fund targeted enterprise AE hiring.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </section>

        <section id="model" className="border-y border-white/10 bg-white/[0.03] px-6 py-20">
          <div className="mx-auto max-w-7xl">
            <div className="max-w-3xl">
              <p className="text-sm font-semibold uppercase tracking-widest text-teal-300">One connected operating model</p>
              <h2 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">
                See the full path from pipeline to cash.
              </h2>
              <p className="mt-4 text-lg leading-8 text-slate-300">
                Most SaaS teams report these metrics separately. SMPL connects them so leaders can understand how GTM
                activity turns into ARR, GAAP revenue, profitability, cash flow, and workforce decisions.
              </p>
            </div>
            <div className="mt-12 grid gap-4 md:grid-cols-7">
              {operatingModel.map((step, index) => (
                <div key={step} className="relative rounded-3xl border border-white/10 bg-slate-900/80 p-5">
                  <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-2xl bg-teal-400/15 text-teal-300">
                    {index + 1}
                  </div>
                  <p className="font-semibold text-white">{step}</p>
                  {index < operatingModel.length - 1 && (
                    <ArrowRight
                      className="absolute -right-4 top-1/2 hidden -translate-y-1/2 text-slate-600 md:block"
                      size={24}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="platform" className="px-6 py-24">
          <div className="mx-auto max-w-7xl">
            <div className="mb-12 flex flex-col justify-between gap-6 md:flex-row md:items-end">
              <div className="max-w-3xl">
                <p className="text-sm font-semibold uppercase tracking-widest text-teal-300">Platform modules</p>
                <h2 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">
                  Built for how SaaS companies actually operate.
                </h2>
              </div>
              <p className="max-w-md text-slate-300">
                SMPL turns disconnected finance, GTM, HR, and accounting data into board-ready insights and planning
                workflows.
              </p>
            </div>
            <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
              {modules.map((module) => {
                const Icon = module.icon;
                return (
                  <Card key={module.title} className="rounded-3xl border-white/10 bg-white/[0.05] transition hover:bg-white/[0.08]">
                    <CardContent className="p-6">
                      <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-400/15 text-teal-300">
                        <Icon size={22} />
                      </div>
                      <h3 className="text-xl font-semibold text-white">{module.title}</h3>
                      <p className="mt-3 text-sm leading-6 text-slate-300">{module.description}</p>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        </section>

        <section className="px-6 pb-24">
          <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.9fr_1.1fr]">
            <Card className="rounded-[2rem] border-white/10 bg-teal-400 text-slate-950">
              <CardContent className="p-8 md:p-10">
                <Layers3 className="mb-6" size={34} />
                <h2 className="text-4xl font-semibold tracking-tight">Traditional FP&A tools tell you what happened.</h2>
                <p className="mt-5 text-lg leading-8 text-slate-800">
                  SMPL tells you why it happened, what changed operationally, and what to do next.
                </p>
              </CardContent>
            </Card>
            <div className="grid gap-4 sm:grid-cols-2">
              {(
                [
                  [ShieldCheck, "Trusted tie-outs", "Validate ARR, revenue, cash, balance sheet, and workforce assumptions before reporting."],
                  [PieChart, "Scenario planning", "Model hiring delays, GTM reallocation, churn improvement, collections timing, and cash impact."],
                  [CalendarClock, "Month-end ready", "Generate MD&A commentary, variance explanations, and executive reporting packages."],
                  [BriefcaseBusiness, "Board communication", "Translate operating data into decisions, risks, opportunities, and recommendations."],
                ] as const
              ).map(([Icon, title, text]) => (
                <div key={title} className="rounded-3xl border border-white/10 bg-white/[0.05] p-6">
                  <Icon className="mb-4 text-teal-300" size={24} />
                  <h3 className="font-semibold text-white">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-300">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="outcomes" className="border-y border-white/10 bg-white/[0.03] px-6 py-20">
          <div className="mx-auto max-w-7xl">
            <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
              <div>
                <p className="text-sm font-semibold uppercase tracking-widest text-teal-300">Business outcomes</p>
                <h2 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">
                  Less reporting work. Better operating decisions.
                </h2>
                <p className="mt-5 text-lg leading-8 text-slate-300">
                  SMPL helps finance teams move from manual reporting to automated intelligence, giving executives the
                  confidence to act faster.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {outcomes.map((outcome) => (
                  <div key={outcome} className="flex items-start gap-3 rounded-2xl bg-slate-900/80 p-4">
                    <CheckCircle2 className="mt-0.5 shrink-0 text-teal-300" size={18} />
                    <p className="text-sm leading-6 text-slate-200">{outcome}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="demo" className="px-6 py-24">
          <div className="mx-auto max-w-4xl rounded-[2rem] border border-white/10 bg-white/[0.06] p-8 text-center shadow-2xl shadow-black/30 md:p-12">
            <h2 className="text-4xl font-semibold tracking-tight md:text-5xl">Ready to see SMPL in action?</h2>
            <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-slate-300">
              Walk through the May 2026 board package — executive summary, ARR bridge, revenue, GTM, cash, headcount,
              and three-statement views built from the same underlying data model.
            </p>
            <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Link
                href="/board"
                className="inline-flex h-12 items-center justify-center gap-2 rounded-full bg-teal-400 px-7 text-base font-medium text-slate-950 hover:bg-teal-300"
              >
                Open board demo <ArrowRight size={18} />
              </Link>
              <a
                href="mailto:hello@smpl.ai"
                className="inline-flex h-12 items-center justify-center rounded-full border border-white/20 bg-white/5 px-7 text-base font-medium text-white hover:bg-white/10"
              >
                Contact sales
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/10 px-6 py-8">
        <div className="mx-auto flex max-w-7xl flex-col justify-between gap-4 text-sm text-slate-400 md:flex-row md:items-center">
          <p>© 2026 SMPL.ai. Financial intelligence for SaaS operators.</p>
          <div className="flex gap-6">
            <a href="#" className="hover:text-white">
              Privacy
            </a>
            <a href="#" className="hover:text-white">
              Security
            </a>
            <Link href="/board" className="hover:text-white">
              Demo
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
