/**
 * Public SOC 2 readiness scoreboard for /compliance.
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

/** Update `lastUpdated` when you change checklist items (YYYY-MM-DD). */
export const complianceProgressMeta = {
  lastUpdated: "2026-07-22",
  title: "SOC 2 readiness",
  subtitle:
    "Honest progress toward SOC 2 Type I. We are not certified until an independent CPA firm issues a report.",
  currentFocus:
    "Matt: MFA on all admin cloud accounts, approve DRAFT policies, pick Vanta/wait date, DPA legal",
  /** What “done” means for Type I — shown prominently on the page. */
  definitionOfDone:
    "An independent CPA firm has issued a SOC 2 Type I report covering Security + Availability + Confidentiality, and that report is in hand (typically shared with customers under NDA).",
  salesLanguage:
    'Say “SOC 2 readiness in progress” or “we are pursuing SOC 2.” Never say “we are SOC 2 certified” until a report exists.',
  dataFile: "frontend/lib/compliance/progress.ts",
  markdownScoreboard: "docs/soc2/PROGRESS.md",
} as const;

export const compliancePhases: CompliancePhase[] = [
  {
    id: "kickoff",
    name: "Kickoff",
    status: "in_progress",
    exitCriteria:
      "Scope frozen in decision log; owners named; scoreboard + artifacts started — owners + scope set; platform/target month still open",
  },
  {
    id: "controls-live",
    name: "Controls live",
    status: "open",
    exitCriteria:
      "Policies approved; MFA + access inventory; change/deploy path; IR; restore test; vendor evidence; tenant isolation evidence",
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
        label: "Decision log — scope + owners recorded",
        status: "done",
        notes: "Sec+Avail+Conf; PI deferred; all owners Matt Justice (2026-07-22)",
      },
      {
        id: "kg-6",
        label: "Freeze Type I criteria: Sec + Avail + Conf; PI deferred; Privacy skip",
        status: "done",
        notes: "Confirmed in decision log 2026-07-22",
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
        status: "needs_owner",
        notes: "TBD — Matt to decide. Do not auto-sign up for Vanta",
      },
      {
        id: "kg-12",
        label: "Target Type I month",
        status: "needs_owner",
        notes: "Even approximate YYYY-MM",
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
        label: "Customer DPA — legal review / ship",
        status: "needs_owner",
      },
      {
        id: "bv-8",
        label: "Security one-pager",
        status: "done",
        notes: "docs/soc2/SECURITY_ONE_PAGER.md — pursuing SOC 2; not certified",
      },
    ],
  },
  {
    id: "access-hardening",
    name: "C. Access hardening",
    summary: "MFA everywhere admins live, plus a living access inventory.",
    items: [
      { id: "ah-1", label: "MFA — GitHub org admins", status: "needs_owner" },
      { id: "ah-2", label: "MFA — Vercel", status: "needs_owner" },
      { id: "ah-3", label: "MFA — Railway", status: "needs_owner" },
      { id: "ah-4", label: "MFA — Neon", status: "needs_owner" },
      { id: "ah-5", label: "MFA — corporate email / IdP", status: "needs_owner" },
      { id: "ah-6", label: "MFA — Stripe", status: "needs_owner" },
      { id: "ah-7", label: "MFA — Sanity (if admin)", status: "needs_owner" },
      { id: "ah-8", label: "MFA — Resend / Anthropic consoles", status: "needs_owner" },
      {
        id: "ah-9",
        label: "Access inventory — people + roles filled",
        status: "in_progress",
        notes: "Matt on all known systems; MFA verified unchecked — needs Matt",
      },
      {
        id: "ah-10",
        label: "Confirm no shared prod passwords",
        status: "needs_owner",
      },
      {
        id: "ah-11",
        label: "First quarterly-style access review sign-off",
        status: "open",
        notes: "After MFA verified + inventory stable",
      },
    ],
  },
  {
    id: "policies",
    name: "D. Policies",
    summary: "Written controls — drafts exist; leadership approval still required.",
    items: [
      { id: "pol-1", label: "Policy index", status: "done" },
      {
        id: "pol-2",
        label: "Draft stubs expanded: ISP, Acceptable Use, Access Control, IR, Change Mgmt",
        status: "done",
        notes: "P01–P05 DRAFT / not approved",
      },
      {
        id: "pol-3",
        label: "Remaining core policies (P06–P17)",
        status: "in_progress",
        notes: "P06, P08, P09, P11, P12 drafted; P07/P10/P13–P17 open",
      },
      {
        id: "pol-4",
        label: "Leadership approve core policies",
        status: "needs_owner",
        notes: "Draft ≠ approved; Matt must approve",
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
        status: "needs_owner",
        notes: "Confirm in GitHub settings",
      },
      {
        id: "eng-2",
        label: "Document deploy path (Vercel FE, Railway API) + who can promote",
        status: "done",
        notes: "docs/soc2/CHANGE_MANAGEMENT.md",
      },
      {
        id: "eng-3",
        label: "Secrets only in env stores (not git)",
        status: "open",
      },
      {
        id: "eng-4",
        label: "Calendar or complete Neon backup restore test",
        status: "open",
        notes: "Evidence required before Type I — P12 drafted",
      },
      {
        id: "eng-5",
        label: "Tenant isolation evidence (Org A ≠ Org B)",
        status: "open",
      },
      {
        id: "eng-6",
        label: "AI/LLM data-handling write-up aligned with P15",
        status: "open",
      },
    ],
  },
  {
    id: "pre-type-i-bar",
    name: "F. Pre–Type I readiness bar",
    summary: "Book the auditor only when these controls are live, not merely drafted.",
    items: [
      { id: "bar-1", label: "MFA on admin/cloud accounts", status: "open" },
      {
        id: "bar-2",
        label: "Written policies approved by leadership",
        status: "open",
      },
      {
        id: "bar-3",
        label: "Access inventory + first review artifact",
        status: "open",
      },
      {
        id: "bar-4",
        label: "Documented change/deploy path + PR review on main",
        status: "in_progress",
        notes: "Path documented; PR protection still needs Matt",
      },
      {
        id: "bar-5",
        label: "Incident response plan (approved + operable)",
        status: "open",
        notes: "Draft exists; not approved",
      },
      { id: "bar-6", label: "Backup restore test evidence", status: "open" },
      {
        id: "bar-7",
        label: "Subprocessor inventory + vendor reports collected",
        status: "open",
        notes: "Inventory draft; reports not collected",
      },
      { id: "bar-8", label: "Tenant isolation evidence", status: "open" },
      {
        id: "bar-9",
        label: "AI/subprocessor write-up for Anthropic",
        status: "open",
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
  const percent =
    total === 0 ? 0 : Math.round((done / total) * 100);
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
