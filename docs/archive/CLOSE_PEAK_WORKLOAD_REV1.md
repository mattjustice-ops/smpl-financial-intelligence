# Close Peak Workload — Alignment Brief

**Status:** Draft for team review  
**Owner:** TBD  
**Goal:** Align on how we design Prompt 5 + Copilot for month-end concurrency before we build more of the queue/context layer.

Use this doc to confirm the problem, the proposed job model, and anything we are missing. Reply with edits, additions, or “disagree / need more” on the open questions at the bottom.

---

## 1. Problem statement

Our customers are B2B SaaS finance teams. They **close the books on roughly the same calendar** — typically the first few business days after month-end.

That means **Prompt 5 (MD&A / board deck generation)** and **SMPL Copilot** will be hit hard on the **same ~4 days of the month**, not spread evenly.

We must design for **peak close concurrency**, not average daily traffic. Sizing for quiet days will look like an outage during close week.

**Planning assumptions (working):**

| Assumption | Working value | Notes |
|------------|---------------|--------|
| Busy window | ~4 days / month | Days customers need decks + Q&A most |
| Near-term cohort | 10 → 20–40 orgs | First paid customers through early scale |
| Data volume | Up to ~100× today’s synthetic / early loads | Warehouse + LLM context cost grows with data |
| Peak shape | Many orgs, same morning | Not one org with huge traffic |

---

## 2. Workload profile (what gets hammered)

### Prompt 5 — MD&A / board deck export

| Attribute | Today | Close-peak implication |
|-----------|--------|-------------------------|
| Trigger | User clicks generate / regenerate | Many orgs click in the same hours |
| Cost | Long Claude call + data collect + PPTX build | Minutes per job; expensive if parallel unbounded |
| Job model today | In-memory queue, `ThreadPoolExecutor(max_workers=2)` | Global bottleneck; jobs lost on Railway restart |
| Failure mode | Timeout / 502 / silent loss | All customers blocked the same morning |

### Copilot — board Q&A

| Attribute | Today | Close-peak implication |
|-----------|--------|-------------------------|
| Trigger | Interactive chat during close review | Concurrent sessions across orgs |
| Cost | Live warehouse context rebuild + Claude | Slow + expensive if every turn rebuilds full context |
| Failure mode | Latency / Claude 429 / Neon stampede | Noisy-neighbor: one heavy org slows others |

### Related close work (same window)

- CSV / ingest uploads and validation
- Commentary regenerate
- Package downloads (XLSX + PPTX)
- Ops visibility (`usage_events`, queue depth)

---

## 3. Design principle

**Precompute before the crush; serve during the crush.**

```text
Pre-close (T−3 … T0)          Close peak (T+1 … T+4)         Post-close (T+5+)
─────────────────────          ──────────────────────         ────────────────
Ingest + validate              Serve frozen context packs     Light refresh
Build (org, period) blobs      Fair queue for Prompt 5        Archive / prep next month
Nightly / on-ready freeze      Cap Copilot live rebuilds      Cost + capacity review
```

During the busy 4 days, Prompt 5 and Copilot should mostly **read prepared close context**, not re-scrape Neon and rebuild Claude context from scratch on every click.

---

## 4. Proposed job & context model

### A. Durable export jobs (Prompt 5 / packages)

Replace in-memory 2-worker jobs with a **durable queue** (survive restarts):

| Rule | Proposal |
|------|----------|
| Persistence | Job state in DB (or Redis + DB), not process RAM only |
| Global workers | Sized for peak (e.g. 6–12), not 2 |
| Per-org concurrency | Max **1 heavy Prompt 5** per org at a time |
| Fairness | Avoid pure FIFO stampede; optional priority for first close export vs Nth regenerate |
| UX | Async job + ETA (“~8 min, 3 ahead of you”) — never block HTTP until PPTX finishes |
| Caps | Soft/hard limit: N Prompt 5 runs per org per close period (stop regenerate loops) |

### B. Materialized close context (“freeze blob”)

For each `(organization_id, as_of_period)` when close-ready:

- Sectioned context pack: ARR / CFS / GTM / pipeline summary / KPIs / validation status
- Refresh triggers: ingest complete, validation pass, scheduled pre-close cron, explicit “freeze for close”
- Consumers:
  - **Copilot** → prefer frozen pack
  - **Prompt 5** → frozen pack + structured metrics payload
  - Regenerate deck → **reuse pack**, do not rebuild warehouse bundles every time

### C. Copilot under peak load

| Mode | When | Behavior |
|------|------|----------|
| Frozen | Default in close window | Answer from freeze blob; fast first token |
| Live rebuild | Drilldowns / “refresh context” only | Explicit, rate-limited, usage-metered |
| Guardrails | Always | Per-org concurrency; Claude backoff on 429; no unbounded parallel blob rebuilds |

### D. Tenant fairness & Claude protection

- Per-org + global AI concurrency limits
- Prompt caching on stable system prompts where useful
- Alert on queue depth, wait time, Claude 429s, Neon p95
- Deploy freeze during peak close days unless hotfix
- Optional: pre-warm freeze blobs night-before for orgs that finished ingest

---

## 5. Capacity framing (how we talk about “ready”)

Do **not** ask only: “Can we handle 20 customers?”

Ask: **Can we handle N concurrent Prompt 5 jobs + M Copilot sessions for 4 days straight with wait time &lt; X and zero silent job loss?**

### Suggested cohort gates

| Cohort | Orgs (guide) | Must prove before certifying |
|--------|--------------|------------------------------|
| A | ~5 | Durable jobs; no silent loss; basic per-org lock |
| B | ~15 | Freeze blobs for Copilot + Prompt 5; queue wait P95 target; Claude caps |
| C | ~40 | Worker scale-out; stronger fairness; alerts + close-week runbook |

### Example SLA targets (first paid cohort — draft)

| Metric | Draft target |
|--------|--------------|
| Concurrent Prompt 5 workers | 4–8 durable workers |
| Per-org heavy export | 1 at a time |
| Queue wait P95 (close window) | &lt; 15–20 minutes |
| Copilot latency (frozen blob) | &lt; 5–10 s to first token |
| Job durability | Survive Railway restart |
| Claude | Caps + 429 backoff; no unbounded parallel |

*(Team: adjust numbers; keep the metric list.)*

---

## 6. Proposed workstreams (backlog shape)

Ordered for close-peak risk reduction:

1. **Durable export queue** — replace in-memory `max_workers=2`
2. **Per-org + global concurrency limits** — Prompt 5 + Copilot
3. **Month-end freeze / materialized context** — sectioned `(org, period)` blobs
4. **Prompt 5 regenerate caps** — per org per period
5. **Close-week ops** — queue/Claude/Neon alerts + deploy freeze policy
6. **Optional stagger** — night-before blob build; white-glove export slots for early customers
7. Later: separate ingest vs export workers; indexes / incremental ingest; partitioning / cold archive

Aligns with platform bias: **correctness over speed**; jobs &gt;1s async; back-pressure; certify per cohort.

---

## 7. What is explicitly out of scope (for this workload update)

- Changing Prompt 5 slide quality / layout rules (separate track)
- Full ERP close / GL posting (see Close Process doc — we are reporting + reconciliation)
- Customer-facing self-serve usage dashboards (nice-to-have after hard caps)
- Multi-region HA (not required for first cohorts)

---

## 8. Team prompt — please reply with

Copy/paste replies under each item, or comment in-doc.

### Confirm or challenge

1. Is **~4 days / month** the right peak model for our ICP (SaaS finance close), or do we also see mid-month board / forecast spikes that matter as much?
2. Is **Prompt 5 + Copilot** the right pair to prioritize for peak design, or should **ingest + validation** be treated as equally peak-critical in the same window?
3. Do we agree **precompute / freeze blob before close** is the right principle vs “always live from Neon”?
4. Are the **cohort gates (5 / 15 / 40)** useful planning units, or do we prefer different cutovers?

### Add / missing

5. What **SLA numbers** should we commit to for first paying customers (wait time, Copilot latency, max regenerates)?
6. Any **product** requirements for close week (ETA UI, regenerate caps messaging, “close prep” CTA)?
7. Any **ops** requirements (on-call, Slack alerts, Anthropic capacity, Neon plan upgrades)?
8. Anything else that will hammer the platform the same week (Slack intake, continuity agent, multi-export packages, white-glove scripts)?

### Decide

9. Who owns **queue/infra**, **freeze-blob product**, and **close-week runbook**?
10. What is the **minimum ship set** before first close with paid customers vs what can wait until cohort B?

---

## 9. One-paragraph summary (for email / Slack)

> Our usage will not be flat. Customers close around the same time, so Prompt 5 and Copilot will spike for ~4 days each month. Today’s in-memory 2-worker export jobs and live Copilot context rebuilds will not survive that. We propose durable fair queues, per-org concurrency caps, and precomputed `(org, period)` freeze blobs so close week serves prepared context instead of rebuilding everything live. Please review the brief, challenge the assumptions, and add anything we missed before we lock the backlog order.

---

## Revision log

| Date | Change |
|------|--------|
| 2026-07-12 | Initial draft for team alignment |
