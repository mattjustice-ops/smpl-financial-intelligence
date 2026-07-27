/**
 * Internal SOC 2 readiness scoreboard for /app/compliance (ops-admin only).
 *
 * Source of truth for *work*: docs/soc2/PROGRESS.md
 * Source of truth for *this page*: this file — keep them in sync when statuses change.
 *
 * Status mapping from PROGRESS.md:
 *   [x] → done
 *   [~] → in_progress
 *   [ ] → open
 *   [!] → needs_owner
 */

export type ComplianceStatus = "done" | "in_progress" | "open" | "needs_owner";

export type CompliancePhaseId =
  | "kickoff"
  | "controls-live"
  | "type-i-audit"
  | "type-ii";

export type CompliancePhase = {
  id: CompliancePhaseId;
  name: string;
  status: ComplianceStatus;
  exitCriteria: string;
};

export type ComplianceChecklistItem = {
  id: string;
  label: string;
  status: ComplianceStatus;
  notes?: string;
};

export type ComplianceSection = {
  id: string;
  name: string;
  summary: string;
  items: ComplianceChecklistItem[];
};

export type ComplianceTimelineWindow = {
  id: string;
  window: string;
  approxDates: string;
  focus: string;
};

export type ComplianceRemainingItem = {
  id: string;
  label: string;
  status: ComplianceStatus;
  owner: string;
  targetWindow: string;
  notes?: string;
};

/** Update `lastUpdated` when you change checklist items (YYYY-MM-DD). */
export const complianceProgressMeta = {
  lastUpdated: "2026-07-27",
  title: "SOC 2 readiness",
  subtitle:
    "Honest progress toward SOC 2 Type I. We are not certified until an independent CPA firm issues a report.",
  currentFocus:
    "Week 1 complete 2026-07-26. P01–P12 Approved 2026-07-27. Neon restore test Pass 2026-07-27. Platform deferred DIY. P15 draft ready (not approved). Next: DPA legal path; approve P15. Approval ≠ SOC 2 certified",
  scopeLocked:
    "Scope APPROVED 2026-07-22 by Matt Justice: Security + Availability + Confidentiality IN; Processing Integrity and Privacy DEFERRED. All roles: Matt Justice.",
  /** What “done” means for Type I — shown prominently on the page. */
  definitionOfDone:
    "An independent CPA firm has issued a SOC 2 Type I report covering Security + Availability + Confidentiality, and that report is in hand (typically shared with customers under NDA).",
  salesLanguage:
    'Say “SOC 2 readiness in progress” or “we are pursuing SOC 2.” Never say “we are SOC 2 certified” until a report exists.',
  timelineNote:
    "Solo-founder calendar — realistic targets, not commitments. Type I is “compliant” only when the CPA report is in hand.",
  dataFile: "frontend/lib/compliance/progress.ts",
  markdownScoreboard: "docs/soc2/PROGRESS.md",
} as const;

/** Target calendar mirrored from docs/soc2/PROGRESS.md */
export const complianceTimeline: ComplianceTimelineWindow[] = [
  {
    id: "week-1",
    window: "Week 1",
    approxDates: "~2026-07-22 → 2026-07-29",
    focus:
      "COMPLETE 2026-07-26 — MFA + inventory; protect main + required PR (GitHub ruleset); break-glass = Neon/Railway MFA",
  },
  {
    id: "week-2",
    window: "Week 2 (now)",
    approxDates: "~2026-07-29 → 2026-08-05",
    focus:
      "P01–P12 Approved; platform deferred DIY 2026-07-27; P15 draft ready (not approved); DPA legal path next",
  },
  {
    id: "week-3-4",
    window: "Week 3–4",
    approxDates: "~2026-08-05 → 2026-08-19",
    focus:
      "Access review #1 signed; restore test Pass 2026-07-27; IR tabletop notes; vendor SOC collection started; DPA legal path",
  },
  {
    id: "month-2",
    window: "Month 2",
    approxDates: "~2026-08-19 → 2026-09-19",
    focus:
      "Controls habitually running; secrets spot-check; tenant isolation evidence; AI/LLM write-up finalized; security one-pager published for sales",
  },
  {
    id: "month-3-4",
    window: "Month 3–4",
    approxDates: "~2026-09-19 → 2026-11-19",
    focus: "Engage CPA / Type I fieldwork TARGET (adjustable — not a commitment)",
  },
  {
    id: "after-type-i",
    window: "After Type I",
    approxDates: "Report in hand + 3–12 months",
    focus: "Type II observation window, then Type II report",
  },
];

/** Open [!] and [ ] items with owner + target window (PROGRESS.md remaining table). */
export const complianceRemainingItems: ComplianceRemainingItem[] = [
  {
    id: "rem-mfa-github",
    label: "MFA — GitHub org admins",
    status: "done",
    owner: "Matt",
    targetWindow: "Week 1",
    notes: "Done 2026-07-26",
  },
  {
    id: "rem-mfa-vercel",
    label: "MFA — Vercel",
    status: "done",
    owner: "Matt",
    targetWindow: "Week 1",
    notes: "Done 2026-07-26",
  },
  {
    id: "rem-mfa-railway",
    label: "MFA — Railway",
    status: "done",
    owner: "Matt",
    targetWindow: "Week 1",
    notes: "Done 2026-07-26",
  },
  {
    id: "rem-mfa-neon",
    label: "MFA — Neon",
    status: "done",
    owner: "Matt",
    targetWindow: "Week 1",
    notes: "Done 2026-07-26",
  },
  {
    id: "rem-mfa-email",
    label: "MFA — corporate email / IdP",
    status: "done",
    owner: "Matt",
    targetWindow: "Week 1",
    notes: "Done 2026-07-26",
  },
  {
    id: "rem-mfa-stripe",
    label: "MFA — Stripe",
    status: "done",
    owner: "Matt",
    targetWindow: "Week 1",
    notes: "Done 2026-07-26",
  },
  {
    id: "rem-mfa-sanity",
    label: "MFA — Sanity (if admin)",
    status: "done",
    owner: "Matt",
    targetWindow: "Week 1",
    notes: "Done 2026-07-26 — IdP MFA via Google login (not Sanity-native)",
  },
  {
    id: "rem-mfa-resend",
    label: "MFA — Resend",
    status: "done",
    owner: "Matt",
    targetWindow: "Week 1",
    notes: "Done 2026-07-26",
  },
  {
    id: "rem-mfa-anthropic",
    label: "MFA — Anthropic console",
    status: "done",
    owner: "Matt",
    targetWindow: "Week 1",
    notes: "Done 2026-07-26 — IdP MFA via Google login (not Anthropic-native TOTP)",
  },
  {
    id: "rem-mfa-dns",
    label: "MFA — DNS / domain admin (Squarespace)",
    status: "done",
    owner: "Matt",
    targetWindow: "Week 1",
    notes: "Done 2026-07-26 — Squarespace MFA for smpl-ai.com",
  },
  {
    id: "rem-no-shared-passwords",
    label: "Confirm no shared prod passwords",
    status: "done",
    owner: "Matt",
    targetWindow: "Week 1",
    notes: "Confirmed 2026-07-26 — no shared prod passwords",
  },
  {
    id: "rem-protect-main",
    label: "Protect main + required PR review",
    status: "done",
    owner: "Matt",
    targetWindow: "Week 1",
    notes:
      "Done 2026-07-26 — GitHub branch ruleset; required PR before merge; solo-friendly (approvals may be 0)",
  },
  {
    id: "rem-approve-policies",
    label: "Leadership approve core policies (P01–P12 / core set)",
    status: "done",
    owner: "Matt",
    targetWindow: "Week 2",
    notes:
      "Approved 2026-07-27 by Matt Justice — approval ≠ SOC 2 certified; open evidence remains",
  },
  {
    id: "rem-platform",
    label: 'Compliance platform choice or “wait until ____”',
    status: "done",
    owner: "Matt",
    targetWindow: "Week 2",
    notes:
      "Deferred DIY 2026-07-27 — docs/soc2 + /app/compliance; revisit on enterprise GRC requirement or CPA Type I engagement (whichever first)",
  },
  {
    id: "rem-boundary",
    label: "Confirm boundary matches production",
    status: "needs_owner",
    owner: "Matt",
    targetWindow: "Week 2–3",
  },
  {
    id: "rem-vendor-regions",
    label: "Confirm vendor regions / unused vendors; OpenAI if live",
    status: "needs_owner",
    owner: "Matt",
    targetWindow: "Week 2–3",
  },
  {
    id: "rem-access-review",
    label: "First quarterly-style access review sign-off",
    status: "open",
    owner: "Matt",
    targetWindow: "Week 3–4",
    notes: "After inventory stable — Week 1 inventory complete",
  },
  {
    id: "rem-restore-test",
    label: "Neon backup restore test evidence",
    status: "done",
    owner: "Matt",
    targetWindow: "Week 3–4",
    notes:
      "Pass 2026-07-27 — PITR throwaway restore-test-2026-07-27; Railway URL unchanged — docs/soc2/evidence/neon-restore-test-2026-07-27.md",
  },
  {
    id: "rem-ir-tabletop",
    label: "IR tabletop notes (operable IR)",
    status: "open",
    owner: "Matt",
    targetWindow: "Week 3–4",
  },
  {
    id: "rem-vendor-soc",
    label: "Vendor SOC / ISO reports — collection started",
    status: "open",
    owner: "Matt",
    targetWindow: "Week 3–4",
  },
  {
    id: "rem-dpa",
    label: "Customer DPA / MSA — single legal workstream (privacy, retention, subprocessors)",
    status: "needs_owner",
    owner: "Matt",
    targetWindow: "Week 3–4",
    notes: "← start here — also P10 R16; P07/P08/P09 cross-ref only",
  },
  {
    id: "rem-secrets",
    label: "Secrets only in env stores (spot-check)",
    status: "open",
    owner: "Matt",
    targetWindow: "Month 2",
  },
  {
    id: "rem-tenant-isolation",
    label: "Tenant isolation evidence (Org A ≠ Org B)",
    status: "open",
    owner: "Matt",
    targetWindow: "Month 2",
  },
  {
    id: "rem-ai-writeup",
    label: "P15 AI/LLM Data Handling — draft ready for approval",
    status: "in_progress",
    owner: "Matt",
    targetWindow: "Week 2",
    notes:
      "Draft 2026-07-27 — not approved; Matt review/sign-off next (docs/soc2/policies/P15_ai_llm_data_handling.md)",
  },
  {
    id: "rem-one-pager-publish",
    label: "Security one-pager published for sales",
    status: "open",
    owner: "Matt",
    targetWindow: "Month 2",
    notes: "Draft exists",
  },
  {
    id: "rem-type-i-month",
    label: "Target Type I month (YYYY-MM)",
    status: "needs_owner",
    owner: "Matt",
    targetWindow: "Month 2–3",
    notes: "TARGET, not commitment",
  },
  {
    id: "rem-audit-firm",
    label: "Audit firm shortlist / engagement",
    status: "needs_owner",
    owner: "Matt",
    targetWindow: "Month 3–4",
    notes: "Independent CPA — TARGET fieldwork",
  },
  {
    id: "rem-engage-cpa",
    label: "Engage CPA; schedule Type I fieldwork",
    status: "needs_owner",
    owner: "Matt",
    targetWindow: "Month 3–4",
    notes: "TARGET, not commitment",
  },
  {
    id: "rem-type-i-report",
    label: "Type I report issued → only then Type I is “done”",
    status: "open",
    owner: "Matt + CPA",
    targetWindow: "When report in hand",
  },
  {
    id: "rem-type-ii",
    label: "Type II observation (3–12 months) + Type II report",
    status: "open",
    owner: "Matt + CPA",
    targetWindow: "After Type I",
  },
];

export const compliancePhases: CompliancePhase[] = [
  {
    id: "kickoff",
    name: "Kickoff",
    status: "in_progress",
    exitCriteria:
      "Scope APPROVED + owners named; platform deferred DIY; scoreboard live — target month / CPA still open",
  },
  {
    id: "controls-live",
    name: "Controls live",
    status: "in_progress",
    exitCriteria:
      "Policies approved 2026-07-27; P15 draft ready (not approved); MFA + access inventory; change/deploy path; IR approved (tabletop open); restore test Pass 2026-07-27; vendor reports / tenant isolation still open",
  },
  {
    id: "type-i-audit",
    name: "Type I audit",
    status: "open",
    exitCriteria: "CPA firm engaged; fieldwork complete; Type I report issued",
  },
  {
    id: "type-ii",
    name: "Type II",
    status: "open",
    exitCriteria:
      "Controls operate cleanly over observation window; Type II report issued",
  },
];

export const complianceSections: ComplianceSection[] = [
  {
    id: "kickoff-governance",
    name: "A. Kickoff & governance",
    summary: "Plan, owners, decision log, and engagement framing.",
    items: [
      {
        id: "kg-1",
        label: "Kickoff plan published",
        status: "done",
        notes: "docs/SOC2_TYPE1_KICKOFF.md",
      },
      {
        id: "kg-2",
        label: "Readiness reference (scope + criteria)",
        status: "done",
        notes: "docs/SMPL_SOC2_Readiness_Reference_v2.md",
      },
      {
        id: "kg-3",
        label: "Working folder docs/soc2/ seeded",
        status: "done",
        notes: "Decision log, boundary, subprocessors, access template, policy index",
      },
      {
        id: "kg-4",
        label: "Progress scoreboard created",
        status: "done",
        notes: "docs/soc2/PROGRESS.md + this page",
      },
      {
        id: "kg-5",
        label: "Decision log — scope + owners APPROVED",
        status: "done",
        notes:
          "Sec+Avail+Conf IN; PI + Privacy DEFERRED; all owners Matt Justice (2026-07-22 APPROVED)",
      },
      {
        id: "kg-6",
        label: "Freeze Type I criteria: Sec + Avail + Conf; PI deferred; Privacy skip",
        status: "done",
        notes: "APPROVED in decision log 2026-07-22",
      },
      {
        id: "kg-7",
        label: "Name executive sponsor",
        status: "done",
        notes: "Matt Justice",
      },
      {
        id: "kg-8",
        label: "Name security owner",
        status: "done",
        notes: "Matt Justice",
      },
      {
        id: "kg-9",
        label: "Name engineering owner",
        status: "done",
        notes: "Matt Justice (all roles for now)",
      },
      {
        id: "kg-10",
        label: "Name ops / CS privileged-access owner",
        status: "done",
        notes: "Matt Justice (all roles for now)",
      },
      {
        id: "kg-11",
        label: 'Compliance platform choice or explicit “wait until ____”',
        status: "done",
        notes:
          "Deferred DIY 2026-07-27 — docs/soc2 + /app/compliance; revisit on enterprise GRC req or CPA Type I engagement",
      },
      {
        id: "kg-12",
        label: "Target Type I month",
        status: "needs_owner",
        notes: "Even approximate YYYY-MM — TARGET, not commitment",
      },
      {
        id: "kg-13",
        label: "Audit firm shortlist / engagement",
        status: "needs_owner",
        notes: "Independent CPA; platform partner network OK later",
      },
    ],
  },
  {
    id: "boundary-vendors",
    name: "B. System boundary & vendors",
    summary: "What is in scope and which vendors process customer data.",
    items: [
      {
        id: "bv-1",
        label: "System boundary draft from known stack",
        status: "done",
        notes: "Vercel, Railway, Neon, Auth.js, Resend, Anthropic, Stripe, GitHub, Sanity",
      },
      {
        id: "bv-2",
        label: "Boundary TBDs assigned",
        status: "in_progress",
        notes: "Sanity in/out, staging, hostnames, OpenAI fallback, privileged ops",
      },
      {
        id: "bv-3",
        label: "Confirm boundary matches production",
        status: "needs_owner",
      },
      {
        id: "bv-4",
        label: "Subprocessors named list draft",
        status: "done",
      },
      {
        id: "bv-5",
        label: "Confirm regions / unused vendors; mark OpenAI if live",
        status: "needs_owner",
      },
      {
        id: "bv-6",
        label: "Vendor SOC / ISO reports folder (under NDA)",
        status: "open",
      },
      {
        id: "bv-7",
        label: "Customer DPA / MSA — single legal workstream",
        status: "needs_owner",
        notes: "Also P10 R16 — covers privacy/retention/subprocessors formerly flagged in P07–P09",
      },
      {
        id: "bv-8",
        label: "Security one-pager",
        status: "done",
        notes: "docs/soc2/SECURITY_ONE_PAGER.md — draft done; publish for sales = Month 2",
      },
    ],
  },
  {
    id: "access-hardening",
    name: "C. Access hardening",
    summary: "MFA everywhere admins live, plus a living access inventory.",
    items: [
      {
        id: "ah-1",
        label: "MFA — GitHub org admins",
        status: "done",
        notes: "Done 2026-07-26",
      },
      {
        id: "ah-2",
        label: "MFA — Vercel",
        status: "done",
        notes: "Done 2026-07-26",
      },
      {
        id: "ah-3",
        label: "MFA — Railway",
        status: "done",
        notes: "Done 2026-07-26",
      },
      {
        id: "ah-4",
        label: "MFA — Neon",
        status: "done",
        notes: "Done 2026-07-26",
      },
      {
        id: "ah-5",
        label: "MFA — corporate email / IdP",
        status: "done",
        notes: "Done 2026-07-26",
      },
      {
        id: "ah-6",
        label: "MFA — Stripe",
        status: "done",
        notes: "Done 2026-07-26",
      },
      {
        id: "ah-7",
        label: "MFA — Sanity (if admin)",
        status: "done",
        notes: "Done 2026-07-26 — IdP MFA via Google login (not Sanity-native)",
      },
      {
        id: "ah-8",
        label: "MFA — Resend",
        status: "done",
        notes: "Done 2026-07-26",
      },
      {
        id: "ah-8b",
        label: "MFA — Anthropic console",
        status: "done",
        notes: "Done 2026-07-26 — IdP MFA via Google login (not Anthropic-native TOTP)",
      },
      {
        id: "ah-8c",
        label: "MFA — DNS / domain admin (Squarespace)",
        status: "done",
        notes: "Done 2026-07-26 — Squarespace MFA for smpl-ai.com",
      },
      {
        id: "ah-9",
        label: "Access inventory — people + roles filled",
        status: "done",
        notes:
          "First pass complete 2026-07-26; ops/break-glass = same MFA as Neon/Railway (solo; no separate login)",
      },
      {
        id: "ah-10",
        label: "Confirm no shared prod passwords",
        status: "done",
        notes: "Confirmed 2026-07-26",
      },
      {
        id: "ah-11",
        label: "First quarterly-style access review sign-off",
        status: "open",
        notes: "After inventory stable — Week 3–4",
      },
    ],
  },
  {
    id: "policies",
    name: "D. Policies",
    summary:
      "P01–P12 Approved 2026-07-27 by Matt Justice. Approval ≠ SOC 2 certified. P15 draft ready for approval (not approved).",
    items: [
      { id: "pol-1", label: "Policy index", status: "done" },
      {
        id: "pol-2",
        label: "Draft stubs expanded: ISP, Acceptable Use, Access Control, IR, Change Mgmt",
        status: "done",
        notes: "P01–P05 approved 2026-07-27",
      },
      {
        id: "pol-3",
        label: "Core policies P01–P12 drafted (approval-ready)",
        status: "done",
        notes:
          "P06–P12 expanded; P07 + P10 created 2026-07-26; all Approved 2026-07-27",
      },
      {
        id: "pol-4",
        label: "Leadership approve core policies",
        status: "done",
        notes:
          "Approved 2026-07-27 by Matt Justice — approval ≠ SOC 2 certified",
      },
      {
        id: "pol-5",
        label: "P15 AI / LLM Data Handling — draft ready for approval",
        status: "in_progress",
        notes:
          "Draft 2026-07-27 — not approved; Matt sign-off next",
      },
    ],
  },
  {
    id: "engineering-hygiene",
    name: "E. Engineering hygiene",
    summary: "Branch protection, deploy path, secrets, restore test, tenant isolation.",
    items: [
      {
        id: "eng-1",
        label: "Protect main + required PR review",
        status: "done",
        notes:
          "Done 2026-07-26 — GitHub branch ruleset; required PR before merge; solo-friendly (approvals may be 0)",
      },
      {
        id: "eng-2",
        label: "Document deploy path (Vercel FE, Railway API) + who can promote",
        status: "done",
        notes:
          "docs/soc2/CHANGE_MANAGEMENT.md — MFA + branch protection live 2026-07-26",
      },
      {
        id: "eng-3",
        label: "Secrets only in env stores (not git)",
        status: "open",
        notes: "Month 2",
      },
      {
        id: "eng-4",
        label: "Calendar or complete Neon backup restore test",
        status: "done",
        notes:
          "Pass 2026-07-27 — PITR throwaway validated; docs/soc2/evidence/neon-restore-test-2026-07-27.md",
      },
      {
        id: "eng-5",
        label: "Tenant isolation evidence (Org A ≠ Org B)",
        status: "open",
        notes: "Month 2",
      },
      {
        id: "eng-6",
        label: "P15 draft + AI/LLM / Anthropic write-up",
        status: "in_progress",
        notes: "Draft ready 2026-07-27 — awaiting Matt approval",
      },
    ],
  },
  {
    id: "pre-type-i-bar",
    name: "F. Pre–Type I readiness bar",
    summary: "Book the auditor only when these controls are live, not merely drafted.",
    items: [
      {
        id: "bar-1",
        label: "MFA on admin/cloud accounts",
        status: "done",
        notes:
          "Cloud + DNS (Squarespace) done 2026-07-26 (Anthropic via Google IdP); ops/break-glass = Neon/Railway MFA",
      },
      {
        id: "bar-2",
        label: "Written policies approved by leadership",
        status: "done",
        notes: "P01–P12 Approved 2026-07-27; approval ≠ certified",
      },
      {
        id: "bar-3",
        label: "Access inventory + first review artifact",
        status: "in_progress",
        notes: "Inventory first pass done; quarterly sign-off still open (Week 3–4)",
      },
      {
        id: "bar-4",
        label: "Documented change/deploy path + PR review on main",
        status: "done",
        notes: "Path documented; GitHub ruleset protecting main live 2026-07-26",
      },
      {
        id: "bar-5",
        label: "Incident response plan (approved + operable)",
        status: "in_progress",
        notes: "Approved 2026-07-27; tabletop not scheduled — still open",
      },
      {
        id: "bar-6",
        label: "Backup restore test evidence",
        status: "done",
        notes:
          "Pass 2026-07-27 — PITR throwaway; docs/soc2/evidence/neon-restore-test-2026-07-27.md",
      },
      {
        id: "bar-7",
        label: "Subprocessor inventory + vendor reports collected",
        status: "open",
        notes: "Inventory draft; reports not collected",
      },
      { id: "bar-8", label: "Tenant isolation evidence", status: "open" },
      {
        id: "bar-9",
        label: "P15 draft + AI/subprocessor write-up for Anthropic",
        status: "in_progress",
        notes: "Draft ready — not approved",
      },
    ],
  },
  {
    id: "type-i-type-ii",
    name: "G. Type I → Type II",
    summary: "Engagement, report issuance, then observation window.",
    items: [
      {
        id: "t12-1",
        label: "Engage CPA firm; schedule fieldwork",
        status: "needs_owner",
        notes: "TARGET Month 3–4",
      },
      {
        id: "t12-2",
        label: "Type I report issued → this is when Type I is “done”",
        status: "open",
      },
      {
        id: "t12-3",
        label: "Keep controls operating; start Type II observation clock",
        status: "open",
      },
      { id: "t12-4", label: "Type II report issued", status: "open" },
    ],
  },
];

const STATUS_WEIGHT: Record<ComplianceStatus, number> = {
  done: 1,
  in_progress: 0.5,
  open: 0,
  needs_owner: 0,
};

export function isItemComplete(status: ComplianceStatus): boolean {
  return status === "done";
}

export function sectionStats(section: ComplianceSection) {
  const total = section.items.length;
  const done = section.items.filter((item) => item.status === "done").length;
  const inProgress = section.items.filter((item) => item.status === "in_progress").length;
  const needsOwner = section.items.filter((item) => item.status === "needs_owner").length;
  const open = section.items.filter((item) => item.status === "open").length;
  const percent = total === 0 ? 0 : Math.round((done / total) * 100);
  return { done, inProgress, needsOwner, open, total, percent };
}

/** Weighted readiness % (done=1, in_progress=0.5) across checklist items. */
export function overallPercent(sections: ComplianceSection[] = complianceSections): number {
  const items = sections.flatMap((s) => s.items);
  if (items.length === 0) return 0;
  const score = items.reduce((sum, item) => sum + STATUS_WEIGHT[item.status], 0);
  return Math.round((score / items.length) * 100);
}

export function overallCounts(sections: ComplianceSection[] = complianceSections) {
  const items = sections.flatMap((s) => s.items);
  return {
    total: items.length,
    done: items.filter((i) => i.status === "done").length,
    inProgress: items.filter((i) => i.status === "in_progress").length,
    needsOwner: items.filter((i) => i.status === "needs_owner").length,
    open: items.filter((i) => i.status === "open").length,
  };
}

export function statusLabel(status: ComplianceStatus): string {
  switch (status) {
    case "done":
      return "Done";
    case "in_progress":
      return "In progress";
    case "needs_owner":
      return "Needs owner";
    default:
      return "Open";
  }
}
