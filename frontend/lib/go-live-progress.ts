export type GoLiveChecklistItem = {
  id: string;
  label: string;
  done: boolean;
};

export type GoLiveMilestone = {
  id: "demo-ready" | "auth-milestone" | "customer-app" | "full-go-live";
  name: string;
  summary: string;
  items: GoLiveChecklistItem[];
};

/** Update `lastUpdated` when you change checklist items (YYYY-MM-DD). */
export const goLiveProgressMeta = {
  lastUpdated: "2026-05-19",
  title: "SMPL go-live progress",
  subtitle: "Track milestone completion as we close remaining deliverables.",
  currentFocus:
    "Full go-live prep: verified Resend domain, customer provisioning, first paying customer",
} as const;

export const goLiveMilestones: GoLiveMilestone[] = [
  {
    id: "demo-ready",
    name: "Demo-ready",
    summary: "Website + board demo shareable with prospects and board members.",
    items: [
      { id: "dr-1", label: "Marketing site (landing, pricing, book demo, request quote)", done: true },
      { id: "dr-2", label: "June 2026 board demo at /board with export downloads", done: true },
      { id: "dr-3", label: "Vercel frontend deployed (Root Directory = frontend)", done: true },
      { id: "dr-4", label: "Local dev stack documented (Docker, backend, frontend scripts)", done: true },
      { id: "dr-5", label: "Board PPT + Excel committed under public/board/exports", done: true },
      { id: "dr-6", label: "Vercel build succeeds without local-only env dependencies", done: true },
    ],
  },
  {
    id: "auth-milestone",
    name: "Auth milestone",
    summary: "Production magic-link login shell on Vercel infrastructure.",
    items: [
      { id: "am-1", label: "Auth.js + Postgres adapter + /login UI implemented", done: true },
      { id: "am-2", label: "Session sync API + invites + seat limits (local)", done: true },
      { id: "am-3", label: "Middleware protects /app and /account", done: true },
      { id: "am-4", label: "Neon/Supabase AUTH_DATABASE_URL on Vercel", done: true },
      { id: "am-5", label: "Alembic migrations run on production auth DB", done: true },
      { id: "am-6", label: "Vercel AUTH_SECRET, AUTH_URL, AUTH_RESEND_KEY, EMAIL_FROM set", done: true },
      { id: "am-7", label: "Prod smoke test: magic link email → /app redirect", done: true },
    ],
  },
  {
    id: "customer-app",
    name: "Customer /app",
    summary: "Logged-in customers see their org data from a hosted API + warehouse.",
    items: [
      { id: "ca-1", label: "/app dashboards built (Executive, P&L, workforce, GTM, etc.)", done: true },
      { id: "ca-2", label: "FastAPI reporting modules + CSV ingest (local)", done: true },
      { id: "ca-3", label: "Hosted FastAPI on Railway/Render with DATABASE_URL", done: true },
      { id: "ca-4", label: "SFI_BACKEND_URL + NEXT_PUBLIC_API_URL → hosted API on Vercel", done: true },
      { id: "ca-5", label: "Warehouse schema + pilot customer data loaded in cloud DB", done: true },
      { id: "ca-6", label: "PR2: /app uses session.user.activeOrganizationId (not demo org)", done: true },
      { id: "ca-7", label: "PR2: Authenticated API proxy + org membership checks", done: true },
      { id: "ca-8", label: "Prod smoke test: customer login → their data in /app", done: true },
    ],
  },
  {
    id: "full-go-live",
    name: "Full go-live",
    summary: "Multi-tenant cloud platform ready for paying customers at scale.",
    items: [
      { id: "gl-1", label: "Customer provisioning playbook (Stripe or manual invite)", done: false },
      { id: "gl-2", label: "Resend verified sending domain (not onboarding@resend.dev)", done: false },
      { id: "gl-3", label: "Plan module entitlements in UI + API", done: false },
      { id: "gl-4", label: "Stripe live keys + webhooks (when charging)", done: false },
      { id: "gl-5", label: "Staging environment + smoke tests before prod pushes", done: false },
      { id: "gl-6", label: "Monitoring, backups, and incident runbook", done: false },
      { id: "gl-7", label: "First paying customer live on production stack", done: false },
    ],
  },
];

export function milestonePercent(milestone: GoLiveMilestone): number {
  if (milestone.items.length === 0) return 0;
  const done = milestone.items.filter((item) => item.done).length;
  return Math.round((done / milestone.items.length) * 100);
}

export function overallPercent(milestones: GoLiveMilestone[] = goLiveMilestones): number {
  const total = milestones.reduce((sum, m) => sum + m.items.length, 0);
  const done = milestones.reduce(
    (sum, m) => sum + m.items.filter((item) => item.done).length,
    0,
  );
  if (total === 0) return 0;
  return Math.round((done / total) * 100);
}

export function milestoneStats(milestone: GoLiveMilestone) {
  const done = milestone.items.filter((item) => item.done).length;
  return { done, total: milestone.items.length, percent: milestonePercent(milestone) };
}
