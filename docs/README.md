# Documentation index

Product and domain documentation for the SaaS Financial Intelligence platform.

## Core product & domain

| Document | Description |
|----------|-------------|
| [Architecture_Master.md](./Architecture_Master.md) | System design, stack, service boundaries, principles |
| [Data_Model.md](./Data_Model.md) | Entities, warehouse tables, scenarios, transformations |
| [Forecasting_Assumptions.md](./Forecasting_Assumptions.md) | Forecast drivers, build sequence, roll-forward rules |
| [Close_Process.md](./Close_Process.md) | Month-end close workflow, roles, sign-off |
| [Reporting_Logic.md](./Reporting_Logic.md) | Report definitions, tie-outs, validation catalog |
| [CLOSE_PEAK_WORKLOAD.md](./CLOSE_PEAK_WORKLOAD.md) | **Month-end peak concurrency strategy** — Prompt 5, Copilot, ingest (Rev 4); engineering backlog in §6a–6b |
| [CUSTOMER_CLOSE_WORKFLOW.md](./CUSTOMER_CLOSE_WORKFLOW.md) | **Canonical Customer Close Workflow** — state machine, Lock → Certified Close, UX/API/DB (implementation spec) |
| [CUSTOMER_CLOSE_DATA_READINESS.md](./CUSTOMER_CLOSE_DATA_READINESS.md) | Superseded alignment brief — see Close Workflow |

## Go-live & operations

| Document | Description |
|----------|-------------|
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Deploy overview |
| [ENVIRONMENTS.md](./ENVIRONMENTS.md) | Staging vs production |
| [GO_LIVE_GL6_MONITORING.md](./GO_LIVE_GL6_MONITORING.md) | Production monitoring |
| [CUSTOMER_ACCESS.md](./CUSTOMER_ACCESS.md) | Customer access patterns |
| [SANITY_BLOG_SETUP.md](./SANITY_BLOG_SETUP.md) | Sanity CMS: blog + glossary, `/studio`, seed, Vercel env |

See also `GO_LIVE_GL*.md` and `GO_LIVE_STEP*.md` for provisioning, Stripe, Resend, and staging steps.

## Security & compliance (SOC 2)

Internal readiness only — do not claim SOC 2 certified until a CPA firm issues a report.

| Document | Description |
|----------|-------------|
| [SOC2_TYPE1_KICKOFF.md](./SOC2_TYPE1_KICKOFF.md) | Founder-executable Type I kickoff (Week 1–2, sales language, next moves) |
| [SMPL_SOC2_Readiness_Reference_v2.md](./SMPL_SOC2_Readiness_Reference_v2.md) | Scope, criteria, gap map, evidence bar (source of truth) |
| [soc2/](./soc2/) | Fillable artifacts: decision log, system boundary, subprocessors, access inventory, policy index, Week 1 checklist |

## Implementation notes

API and export specifics live under `backend/docs/`, e.g. [REPORTING_EXPORT.md](../backend/docs/REPORTING_EXPORT.md).

## Archive

Superseded drafts: [archive/](./archive/) — earlier Close Peak Workload revisions (Rev 1–3 supplements). Canonical doc is [CLOSE_PEAK_WORKLOAD.md](./CLOSE_PEAK_WORKLOAD.md).
