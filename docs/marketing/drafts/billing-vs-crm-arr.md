---
seoTitle: Billing ARR vs CRM ARR: Pick One Source of Truth | SMPL.ai
seoDescription: Billing ARR and CRM ARR often disagree. Why SaaS finance teams get two ending ARR numbers, which should own the board pack, and how to reconcile without averaging them.
slug: billing-vs-crm-arr
title: Billing ARR vs CRM ARR: Pick One Source of Truth
category: ARR & revenue
status: draft → publish Sep 2026
---

# Billing ARR vs CRM ARR: Pick One Source of Truth

## Two ending ARRs, one board meeting

Ask billing for ending ARR. Ask sales ops for ending ARR. Get two numbers. Both teams are sincere. Both can defend their spreadsheet. The board still has to pick one.

That gap — [billing ARR](/glossary/billing-arr) vs [CRM ARR](/glossary/crm-arr) — is one of the most common reconciliation failures in growth-stage SaaS finance. It is not a rounding problem. It is usually two different definitions of “active recurring value,” sitting in two different systems, with two different owners.

This piece is about why the numbers diverge, which view should certify the [board pack](/glossary/board-pack), and how to build a bridge instead of averaging the conflict away. Short definitions live in the glossary; this is the operating decision.

## What billing ARR actually is

**Billing ARR** is recurring value taken from the billing or subscription system of record — entitlements, invoices, and contract schedules customers are actually on.

Done well, it answers: *what recurring contracts are live right now under finance’s ARR policy?* It ties naturally to cash timing, [deferred revenue](/glossary/deferred-revenue), and the subscription objects ops and finance already fight over at close.

It is not automatically perfect. Manual invoices, mis-skued products, free seats, and usage that never became “recurring under policy” will still distort it. But when finance needs a number that can survive diligence, billing is usually the strongest candidate for **source of truth** — because you can walk from a logo to a subscription to an invoice to cash.

## What CRM ARR actually is

**CRM ARR** is recurring value inferred from CRM — opportunity products, account ARR fields, or rolled-up closed-won amounts.

It answers a different question: *what does sales believe the book looks like?* That belief is essential for [pipeline](/glossary/pipeline), [bookings](/glossary/bookings), and forecasting. It is a weak foundation for certified ending ARR when stage hygiene is loose, amount fields mean ACV one week and ARR the next, or closed-won never reaches billing.

CRM ARR is not “wrong.” It is often *early* — a commercial model of the book before the subscription object exists. Trouble starts when that early view is pasted into the board pack as if it were the close.

## Why they diverge (the usual suspects)

Most gaps are not mysterious. They are repeatable:

- **Timing:** Closed-won in CRM this week; billing provisioning next week (or never).
- **Product mapping:** CRM sells a bundle; billing invoices three SKUs — or a services line that should not be ARR.
- **Multi-year math:** TCV or ACV in CRM treated as ARR; billing annualizes correctly (or the reverse).
- **Stale account fields:** Someone typed ARR on the account page six months ago and nobody owns the refresh.
- **Churn and contraction lag:** Sales marks a save; billing already cancelled — or billing is still live while CRM shows lost.
- **Free, pilot, and internal logos:** Counted in one system, excluded in the other.
- **Usage and overages:** CRM optimistic; billing policy says non-recurring until committed.

If your [ARR waterfall](/glossary/waterfall) is built from CRM movements but ending ARR is taken from billing (or vice versa), GRR and NRR will not reproduce from the same bridge. That is a governance failure, not a metric debate — see also [ARR waterfall vs GAAP revenue](/blog/arr-waterfall-vs-gaap-revenue) and [ARR methodology](/blog/arr-governance).

## Which number belongs in the board pack?

**Default rule for growth-stage SaaS:** certify **board ending ARR from billing** (or a documented hybrid that starts in billing), and use **CRM ARR for pipeline, bookings, and coverage** — with an explicit bridge when leadership asks why the two differ.

Why billing wins the close:

1. It is closer to entitlements and cash.
2. It is harder to “optimistic-edit” without leaving an audit trail.
3. Diligence will eventually ask for invoices and schedules anyway.

Why CRM still matters:

1. Sales cannot run on last month’s billing alone.
2. Bookings and pipeline are forward-looking; billing is the rear-view of what is live.
3. The CRM→billing lag *is* an operating KPI worth managing — not a number to hide.

**Do not average them.** An average of two definitions is a third definition with no owner.

## How to reconcile without starting a war

A practical monthly (or weekly) pattern:

1. **Publish one ARR policy** — what counts, what does not, multi-year and usage rules ([ARR](/glossary/arr)).
2. **Freeze a billing-sourced ending ARR** as the certified close number.
3. **Extract CRM ARR** on the same as-of date with the same logo universe (or a documented difference).
4. **Build a bridge:** timing, product mapping, non-ARR lines, churn lag, manual overrides — name the buckets.
5. **Assign owners:** finance owns certified ARR; sales ops owns CRM hygiene; both own the bridge narrative.
6. **Feed the waterfall from the same source as ending ARR.** Retention metrics ([NRR](/glossary/nrr), [GRR](/glossary/grr)) must foot to that bridge.

When the gap is large, treat it as an implementation defect (mapping, process, or tooling) — not as “Finance and Sales seeing different truths.” There is one customer book. Two systems are lagging copies of it.

## What “good” looks like

Healthy teams can answer, in one slide:

- Ending ARR (billing-certified)
- Net new ARR and the waterfall components
- CRM ARR (or bookings) for the commercial view
- The bridge: top three reasons they differ this period
- As-of timestamp and policy link

That is board-ready. Two competing ARR headlines without a bridge is not.

## Where SMPL fits

SMPL is built for the connected close: treat subscription/billing as the recurring-revenue foundation, reconcile CRM and ERP around it, and put one explainable ARR spine into planning and the board pack — without writing transactions back into billing.

If your team is tired of reconciling two ARRs the week before the board, [book a demo](/book-demo) and we can walk the billing vs CRM bridge on data that looks like yours.
