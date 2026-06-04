"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, CalendarClock, CheckCircle2, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { resolveSchedulingUrl } from "@/components/landing/constants";
import { PRICING_TIERS, type PricingTierId } from "@/lib/billing/plans";
import { DATA_RELIABILITY_OPTIONS } from "@/lib/request-quote/form-options";
import {
  EMPTY_FORM,
  type RequestQuoteFormData,
  type RequestQuoteResponse,
  type SubmissionIntent,
} from "@/lib/request-quote/types";
import { validateForm } from "@/lib/request-quote/validation";

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
  placeholder,
  rows = 4,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
}) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      rows={rows}
      className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-teal-400/50 focus:ring-2 focus:ring-teal-400/20"
    />
  );
}

function tierFromParam(value: string | undefined): PricingTierId | null {
  if (!value) return null;
  const key = value.toLowerCase() as PricingTierId;
  return key in PRICING_TIERS ? key : null;
}

const COPY: Record<
  SubmissionIntent,
  {
    formTitle: string;
    formSubtitle: string;
    submitLabel: string;
    successTitle: string;
    successBody: (first: string, pkg: string) => string;
    primarySuccessCta: { label: string; show: boolean };
  }
> = {
  quote: {
    formTitle: "Tell us about your team",
    formSubtitle: "A short form is enough — we'll go deeper on your stack and goals on the demo.",
    submitLabel: "Submit request",
    successTitle: "Request received",
    successBody: (first, pkg) =>
      `Thanks, ${first}. Based on what you shared, we're preparing a ${pkg} recommendation. Our team will reach out shortly.`,
    primarySuccessCta: { label: "Pick a time now", show: true },
  },
  demo: {
    formTitle: "Book your SMPL demo",
    formSubtitle:
      "Share the same details we use for quote requests. After you continue, we save your info and take you to our calendar.",
    submitLabel: "Continue to scheduling",
    successTitle: "You're almost booked",
    successBody: (first, _pkg) =>
      `Thanks, ${first}. Your details are saved. We’re taking you to our calendar to pick a time.`,
    primarySuccessCta: { label: "Go to calendar now", show: true },
  },
};

type Props = {
  intent: SubmissionIntent;
  preferredTier?: string;
  /** Called when a demo submission succeeds (form is replaced; parent can hide page chrome). */
  onDemoSubmitted?: () => void;
};

const demoContinueClassName =
  "inline-flex h-12 items-center justify-center gap-2 whitespace-nowrap rounded-full bg-teal-400 px-7 text-base font-semibold text-slate-950 transition-colors hover:bg-teal-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-400/50";

export function LeadIntakeForm({ intent, preferredTier, onDemoSubmitted }: Props) {
  const schedulingUrl = resolveSchedulingUrl();
  const selectedTier = tierFromParam(preferredTier);
  const copy = COPY[intent];
  const [form, setForm] = useState<RequestQuoteFormData>(() => ({
    ...EMPTY_FORM,
    preferredPlan: preferredTier?.toLowerCase() ?? "",
    submissionIntent: intent,
  }));
  const [errors, setErrors] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<RequestQuoteResponse | null>(null);
  const [hubspotWarning, setHubspotWarning] = useState<string | null>(null);
  const [submittedContact, setSubmittedContact] = useState({ firstname: "", email: "" });

  function updateField<K extends keyof RequestQuoteFormData>(key: K, value: RequestQuoteFormData[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function saveDemoLead(
    payload: RequestQuoteFormData
  ): Promise<
    | { ok: true; data: RequestQuoteResponse; hubspotWarning: string | null }
    | { ok: false; error: string }
  > {
    const res = await fetch("/api/request-quote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = (await res.json()) as RequestQuoteResponse & { errors?: string[]; error?: string };

    if (!res.ok) {
      return {
        ok: false,
        error: data.errors?.join(" ") ?? data.error ?? "Could not save your details. Please try again.",
      };
    }

    const hubspotWarning =
      data.hubspot?.contactId
        ? null
        : data.hubspot?.error ?? "CRM sync did not fully complete, but your request was received.";

    return { ok: true, data: { ...data, ok: true }, hubspotWarning };
  }

  async function handleDemoContinue(event: React.MouseEvent<HTMLButtonElement>) {
    event.preventDefault();

    const payload = { ...form, submissionIntent: intent };
    const formErrors = validateForm(payload);
    if (formErrors.length > 0) {
      setErrors(formErrors);
      return;
    }

    setErrors([]);
    setSubmitting(true);

    try {
      const outcome = await saveDemoLead(payload);
      if (!outcome.ok) {
        setErrors([outcome.error]);
        return;
      }

      setHubspotWarning(outcome.hubspotWarning);
      setSubmittedContact({ firstname: form.firstname, email: form.email });
      setResult(outcome.data);
      onDemoSubmitted?.();

      window.setTimeout(() => {
        window.location.replace(schedulingUrl);
      }, 1500);
    } catch {
      setErrors(["Network error while saving your details. Please try again."]);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmit() {
    const payload = { ...form, submissionIntent: intent };
    const formErrors = validateForm(payload);
    if (formErrors.length > 0) {
      setErrors(formErrors);
      return;
    }

    setErrors([]);
    setSubmitting(true);

    try {
      const res = await fetch("/api/request-quote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = (await res.json()) as RequestQuoteResponse & { errors?: string[]; error?: string };

      if (!res.ok) {
        setErrors(data.errors ?? [data.error ?? "Submission failed. Please try again."]);
        return;
      }

      setResult(data);
    } catch {
      setErrors(["Network error. Please try again."]);
    } finally {
      setSubmitting(false);
    }
  }

  if (result?.ok) {
    const openCalendarInSameTab = intent === "demo";

    return (
      <div className="rounded-[2rem] border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 p-8 shadow-2xl md:p-12">
        <div className="mx-auto max-w-2xl text-center">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-teal-400/15 text-teal-300">
            <CheckCircle2 size={32} />
          </div>
          <h2 className="text-3xl font-semibold text-white">{copy.successTitle}</h2>
          <p className="mt-4 text-lg text-slate-400">
            {copy.successBody(
              intent === "demo" ? submittedContact.firstname || form.firstname : form.firstname,
              result.recommendedPackage
            )}
          </p>
          {intent === "demo" ? (
            <>
              {hubspotWarning ? (
                <p className="mt-3 text-sm text-amber-200/90">{hubspotWarning}</p>
              ) : null}
              <p className="mt-3 text-sm text-slate-500">
                Use the same work email (
                {submittedContact.email || form.email}) when the calendar asks for your details.
              </p>
              <p className="mt-4 inline-flex items-center gap-2 text-sm text-teal-200/90">
                <Loader2 size={16} className="animate-spin" />
                Redirecting to the calendar…
              </p>
            </>
          ) : null}
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            {copy.primarySuccessCta.show ? (
              <a
                href={schedulingUrl}
                {...(openCalendarInSameTab
                  ? {}
                  : { target: "_blank", rel: "noopener noreferrer" })}
                className="inline-flex h-12 items-center gap-2 rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-7 text-base font-semibold text-slate-950 shadow-lg shadow-teal-500/25 transition hover:brightness-110"
              >
                <CalendarClock size={18} />
                {copy.primarySuccessCta.label}
              </a>
            ) : null}
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
      {selectedTier ? (
        <div className="mb-6 rounded-2xl border border-teal-400/25 bg-teal-400/10 px-5 py-4 text-sm text-teal-100">
          You selected the <span className="font-semibold text-white">{PRICING_TIERS[selectedTier].name}</span>{" "}
          plan ({PRICING_TIERS[selectedTier].support}). We&apos;ll align pricing and contract terms after your demo.
        </div>
      ) : null}

      <div className="mb-8">
        <h2 className="text-2xl font-semibold text-white md:text-3xl">{copy.formTitle}</h2>
        <p className="mt-2 text-slate-400">{copy.formSubtitle}</p>
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
          <FieldLabel required>Company</FieldLabel>
          <TextInput value={form.companyName} onChange={(v) => updateField("companyName", v)} />
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
          <FieldLabel>Phone number</FieldLabel>
          <TextInput value={form.phone} onChange={(v) => updateField("phone", v)} placeholder="Optional" />
        </div>
        <div>
          <FieldLabel required>Country</FieldLabel>
          <TextInput value={form.country} onChange={(v) => updateField("country", v)} placeholder="United States" />
        </div>
        <div>
          <FieldLabel required>State / region</FieldLabel>
          <TextInput value={form.state} onChange={(v) => updateField("state", v)} placeholder="California" />
        </div>
        <div className="md:col-span-2">
          <FieldLabel required>How reliable is your finance data today?</FieldLabel>
          <SelectInput
            value={form.dataReliability}
            onChange={(v) => updateField("dataReliability", v)}
            options={DATA_RELIABILITY_OPTIONS}
            placeholder="Select one"
          />
        </div>
        <div className="md:col-span-2">
          <FieldLabel required>Primary needs or issues</FieldLabel>
          <TextArea
            value={form.primaryNeeds}
            onChange={(v) => updateField("primaryNeeds", v)}
            placeholder="What are you trying to fix or accomplish? Board reporting, close process, forecasting, data quality..."
            rows={5}
          />
        </div>
      </div>

      <div className="mt-10 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-6">
        <Link href="/" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white">
          <ArrowLeft size={16} />
          Back to home
        </Link>
        {intent === "demo" ? (
          <button
            type="button"
            onClick={(event) => void handleDemoContinue(event)}
            disabled={submitting}
            className={demoContinueClassName}
          >
            {submitting ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Saving details...
              </>
            ) : (
              <>
                <CalendarClock size={16} />
                {copy.submitLabel}
              </>
            )}
          </button>
        ) : (
          <form
            className="contents"
            onSubmit={(event) => {
              event.preventDefault();
              void handleSubmit();
            }}
          >
            <Button type="submit" disabled={submitting}>
              {submitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Submitting...
                </>
              ) : (
                copy.submitLabel
              )}
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
