"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, CalendarClock, CheckCircle2, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  ARR_RANGES,
  BUDGET_RANGES,
  COMPANY_STAGES,
  DATA_RELIABILITY_OPTIONS,
  DEPLOYMENT_PREFERENCES,
  EMPLOYEE_COUNTS,
  EXPECTED_USERS,
  FIELD_LABELS,
  FINANCE_TEAM_SIZES,
  FORM_STEPS,
  IMPLEMENTATION_TIMELINES,
  INDUSTRIES,
  SMPL_MODULES,
  SYSTEM_OPTIONS,
} from "@/lib/request-quote/form-options";
import { scoreLead } from "@/lib/request-quote/scoring";
import { EMPTY_FORM, type RequestQuoteFormData, type RequestQuoteResponse } from "@/lib/request-quote/types";
import { validateStep } from "@/lib/request-quote/validation";

function FieldLabel({ children, required }: { children: React.ReactNode; required?: boolean }) {
  return (
    <label className="mb-1.5 block text-sm font-medium text-slate-200">
      {children}
      {required ? <span className="text-teal-400"> *</span> : null}
    </label>
  );
}

function TextInput({
  value,
  onChange,
  type = "text",
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-teal-400/50 focus:ring-2 focus:ring-teal-400/20"
    />
  );
}

function SelectInput({
  value,
  onChange,
  options,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  options: string[];
  placeholder?: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-white outline-none transition focus:border-teal-400/50 focus:ring-2 focus:ring-teal-400/20"
    >
      <option value="">{placeholder ?? "Select..."}</option>
      {options.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </select>
  );
}

function TextArea({
  value,
  onChange,
  rows = 4,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  rows?: number;
  placeholder?: string;
}) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      rows={rows}
      placeholder={placeholder}
      className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-teal-400/50 focus:ring-2 focus:ring-teal-400/20"
    />
  );
}

function ModulePicker({
  selected,
  onChange,
}: {
  selected: string[];
  onChange: (modules: string[]) => void;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {SMPL_MODULES.map((module) => {
        const active = selected.includes(module);
        return (
          <button
            key={module}
            type="button"
            onClick={() =>
              onChange(active ? selected.filter((m) => m !== module) : [...selected, module])
            }
            className={`rounded-xl border px-4 py-3 text-left text-sm transition ${
              active
                ? "border-teal-400/60 bg-teal-400/10 text-white"
                : "border-white/10 bg-white/[0.03] text-slate-300 hover:border-white/20"
            }`}
          >
            {module}
          </button>
        );
      })}
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <div className="grid gap-1 border-b border-white/5 py-3 sm:grid-cols-[180px_1fr]">
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="text-sm text-slate-200">{value}</dd>
    </div>
  );
}

export function RequestQuoteForm() {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<RequestQuoteFormData>(EMPTY_FORM);
  const [errors, setErrors] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<RequestQuoteResponse | null>(null);

  const previewScore = useMemo(() => scoreLead(form), [form]);

  function updateField<K extends keyof RequestQuoteFormData>(key: K, value: RequestQuoteFormData[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function goNext() {
    const stepErrors = validateStep(step, form);
    if (stepErrors.length > 0) {
      setErrors(stepErrors);
      return;
    }
    setErrors([]);
    setStep((prev) => Math.min(prev + 1, FORM_STEPS.length - 1));
  }

  function goBack() {
    setErrors([]);
    setStep((prev) => Math.max(prev - 1, 0));
  }

  async function handleSubmit() {
    const stepErrors = validateStep(3, form);
    if (stepErrors.length > 0) {
      setErrors(stepErrors);
      setStep(3);
      return;
    }

    setSubmitting(true);
    setErrors([]);

    try {
      const res = await fetch("/api/request-quote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = (await res.json()) as RequestQuoteResponse & { errors?: string[]; error?: string };

      if (!res.ok) {
        setErrors(data.errors ?? [data.error ?? "Submission failed. Please try again."]);
        return;
      }

      setResult(data);
      setStep(FORM_STEPS.length - 1);
    } catch {
      setErrors(["Network error. Please try again."]);
    } finally {
      setSubmitting(false);
    }
  }

  if (result?.ok) {
    return (
      <div className="rounded-[2rem] border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 p-8 shadow-2xl md:p-12">
        <div className="mx-auto max-w-2xl text-center">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-teal-400/15 text-teal-300">
            <CheckCircle2 size={32} />
          </div>
          <h2 className="text-3xl font-semibold text-white">Request received</h2>
          <p className="mt-4 text-lg text-slate-400">
            Thanks, {form.firstname}. Based on what you shared, we&apos;re preparing a{" "}
            <span className="text-white">{result.recommendedPackage}</span> recommendation. Our team
            will reach out shortly to schedule a follow-up at a time that works for you.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <a
              href={SCHEDULING_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-12 items-center gap-2 rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-7 text-base font-semibold text-slate-950 shadow-lg shadow-teal-500/25 transition hover:brightness-110"
            >
              <CalendarClock size={18} />
              Pick a time now
            </a>
            <Link href="/">
              <Button variant="outline">Back to home</Button>
            </Link>
            <Link href="/board">
              <Button variant="ghost">View sample dashboard</Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-[2rem] border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 p-6 shadow-2xl md:p-10">
      <div className="mb-8">
        <div className="flex flex-wrap gap-2">
          {FORM_STEPS.map((item, index) => (
            <div
              key={item.id}
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                index === step
                  ? "bg-teal-400 text-slate-950"
                  : index < step
                    ? "bg-teal-400/15 text-teal-300"
                    : "bg-white/5 text-slate-500"
              }`}
            >
              {index + 1}. {item.title}
            </div>
          ))}
        </div>
        <h2 className="mt-5 text-2xl font-semibold text-white md:text-3xl">{FORM_STEPS[step].title}</h2>
        <p className="mt-2 text-slate-400">{FORM_STEPS[step].description}</p>
      </div>

      {errors.length > 0 ? (
        <div className="mb-6 rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-200">
          <ul className="space-y-1">
            {errors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {step === 0 ? (
        <div className="grid gap-5 md:grid-cols-2">
          <div>
            <FieldLabel required>First name</FieldLabel>
            <TextInput value={form.firstname} onChange={(v) => updateField("firstname", v)} />
          </div>
          <div>
            <FieldLabel required>Last name</FieldLabel>
            <TextInput value={form.lastname} onChange={(v) => updateField("lastname", v)} />
          </div>
          <div className="md:col-span-2">
            <FieldLabel required>Work email</FieldLabel>
            <TextInput
              type="email"
              value={form.email}
              onChange={(v) => updateField("email", v)}
              placeholder="you@company.com"
            />
          </div>
          <div>
            <FieldLabel required>Job title</FieldLabel>
            <TextInput value={form.jobtitle} onChange={(v) => updateField("jobtitle", v)} />
          </div>
          <div>
            <FieldLabel>Phone</FieldLabel>
            <TextInput value={form.phone} onChange={(v) => updateField("phone", v)} />
          </div>
        </div>
      ) : null}

      {step === 1 ? (
        <div className="grid gap-5 md:grid-cols-2">
          <div>
            <FieldLabel required>Company name</FieldLabel>
            <TextInput value={form.companyName} onChange={(v) => updateField("companyName", v)} />
          </div>
          <div>
            <FieldLabel required>Company domain</FieldLabel>
            <TextInput
              value={form.domain}
              onChange={(v) => updateField("domain", v)}
              placeholder="company.com"
            />
          </div>
          <div>
            <FieldLabel required>Industry</FieldLabel>
            <SelectInput value={form.industry} onChange={(v) => updateField("industry", v)} options={INDUSTRIES} />
          </div>
          <div>
            <FieldLabel required>ARR range</FieldLabel>
            <SelectInput value={form.arrRange} onChange={(v) => updateField("arrRange", v)} options={ARR_RANGES} />
          </div>
          <div>
            <FieldLabel required>Employee count</FieldLabel>
            <SelectInput
              value={form.employeeCount}
              onChange={(v) => updateField("employeeCount", v)}
              options={EMPLOYEE_COUNTS}
            />
          </div>
          <div>
            <FieldLabel required>Finance team size</FieldLabel>
            <SelectInput
              value={form.financeTeamSize}
              onChange={(v) => updateField("financeTeamSize", v)}
              options={FINANCE_TEAM_SIZES}
            />
          </div>
          <div className="md:col-span-2">
            <FieldLabel required>Company stage</FieldLabel>
            <SelectInput
              value={form.companyStage}
              onChange={(v) => updateField("companyStage", v)}
              options={COMPANY_STAGES}
            />
          </div>
        </div>
      ) : null}

      {step === 2 ? (
        <div className="grid gap-5 md:grid-cols-2">
          <div>
            <FieldLabel required>Current ERP / GL</FieldLabel>
            <SelectInput value={form.currentErp} onChange={(v) => updateField("currentErp", v)} options={SYSTEM_OPTIONS} />
          </div>
          <div>
            <FieldLabel required>Current CRM</FieldLabel>
            <SelectInput value={form.currentCrm} onChange={(v) => updateField("currentCrm", v)} options={SYSTEM_OPTIONS} />
          </div>
          <div>
            <FieldLabel required>Billing system</FieldLabel>
            <SelectInput
              value={form.currentBilling}
              onChange={(v) => updateField("currentBilling", v)}
              options={SYSTEM_OPTIONS}
            />
          </div>
          <div>
            <FieldLabel required>HRIS</FieldLabel>
            <SelectInput value={form.currentHris} onChange={(v) => updateField("currentHris", v)} options={SYSTEM_OPTIONS} />
          </div>
          <div>
            <FieldLabel required>Planning tool</FieldLabel>
            <SelectInput
              value={form.currentPlanning}
              onChange={(v) => updateField("currentPlanning", v)}
              options={SYSTEM_OPTIONS}
            />
          </div>
          <div>
            <FieldLabel required>Data reliability</FieldLabel>
            <SelectInput
              value={form.dataReliability}
              onChange={(v) => updateField("dataReliability", v)}
              options={DATA_RELIABILITY_OPTIONS}
            />
          </div>
        </div>
      ) : null}

      {step === 3 ? (
        <div className="space-y-6">
          <div>
            <FieldLabel required>Requested SMPL modules</FieldLabel>
            <ModulePicker
              selected={form.requestedModules}
              onChange={(modules) => updateField("requestedModules", modules)}
            />
          </div>
          <div>
            <FieldLabel required>Business needs</FieldLabel>
            <TextArea
              value={form.businessNeeds}
              onChange={(v) => updateField("businessNeeds", v)}
              placeholder="What outcomes are you trying to achieve with SMPL?"
            />
          </div>
          <div>
            <FieldLabel required>Biggest challenge</FieldLabel>
            <TextArea
              value={form.biggestChallenge}
              onChange={(v) => updateField("biggestChallenge", v)}
              placeholder="What is hardest about your current finance operating process?"
            />
          </div>
          <div className="grid gap-5 md:grid-cols-2">
            <div className="md:col-span-2">
              <FieldLabel>Current solution</FieldLabel>
              <TextInput
                value={form.currentSolution}
                onChange={(v) => updateField("currentSolution", v)}
                placeholder="Spreadsheets, BI tool, other FP&A platform..."
              />
            </div>
            <div>
              <FieldLabel required>Expected users</FieldLabel>
              <SelectInput
                value={form.expectedUsers}
                onChange={(v) => updateField("expectedUsers", v)}
                options={EXPECTED_USERS}
              />
            </div>
            <div>
              <FieldLabel required>Implementation timeline</FieldLabel>
              <SelectInput
                value={form.implementationTimeline}
                onChange={(v) => updateField("implementationTimeline", v)}
                options={IMPLEMENTATION_TIMELINES}
              />
            </div>
            <div>
              <FieldLabel required>Deployment preference</FieldLabel>
              <SelectInput
                value={form.deploymentPreference}
                onChange={(v) => updateField("deploymentPreference", v)}
                options={DEPLOYMENT_PREFERENCES}
              />
            </div>
            <div>
              <FieldLabel required>Budget range</FieldLabel>
              <SelectInput
                value={form.budgetRange}
                onChange={(v) => updateField("budgetRange", v)}
                options={BUDGET_RANGES}
              />
            </div>
          </div>
        </div>
      ) : null}

      {step === 4 && !result ? (
        <div>
          <div className="mb-6 rounded-2xl border border-teal-400/20 bg-teal-400/5 p-5">
            <p className="text-sm text-slate-400">Preview before submit</p>
            <div className="mt-3 flex flex-wrap gap-6">
              <div>
                <p className="text-xs uppercase tracking-wider text-slate-500">Lead score</p>
                <p className="text-2xl font-semibold text-white">{previewScore.score}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wider text-slate-500">Package</p>
                <p className="text-lg font-semibold text-teal-300">{previewScore.recommendedPackage}</p>
              </div>
            </div>
          </div>
          <dl>
            {(Object.keys(FIELD_LABELS) as Array<keyof RequestQuoteFormData>).map((key) => {
              const value = form[key];
              const display =
                Array.isArray(value) ? value.join(", ") : typeof value === "string" ? value : "";
              return <ReviewRow key={key} label={FIELD_LABELS[key]} value={display} />;
            })}
          </dl>
        </div>
      ) : null}

      <div className="mt-10 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-6">
        <div>
          {step > 0 && !result ? (
            <Button variant="ghost" onClick={goBack}>
              <ArrowLeft size={16} />
              Back
            </Button>
          ) : (
            <Link href="/" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white">
              <ArrowLeft size={16} />
              Back to home
            </Link>
          )}
        </div>
        <div>
          {step < FORM_STEPS.length - 2 ? (
            <Button onClick={goNext}>
              Continue
              <ArrowRight size={16} />
            </Button>
          ) : step === FORM_STEPS.length - 2 ? (
            <Button onClick={goNext}>Review</Button>
          ) : (
            <Button onClick={handleSubmit} disabled={submitting}>
              {submitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Submitting...
                </>
              ) : (
                "Submit request"
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
