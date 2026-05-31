# CFO operating system — product UX

**Primary surface:** live dashboard (`ExecutiveFlowDashboard` + `CfoOperatingShell`)  
**Secondary:** close exports (Excel / board PPTX) in footer — not the hero experience

## Design intent

Inspired by modern SaaS OS products (Stripe, Linear, Ramp) and the reference prototype `saas_cfo_board_reporting_platform.html`:

- Executive readability — KPI strip, serif titles, mono numbers
- Strategic prioritization — “Where to focus” narrative, validation chip
- Narrative guidance — section nav mimics board pacing without exporting slides
- Operational drilldowns — existing waterfall tables + attribution
- Decision support — Risks & Validation section
- Forecast trust — validation visibility in header + decisions tab

## Not optimizing for

- PowerPoint as primary output
- BI-style dense grid dashboards
- Ad-hoc chart builders

## Frontend structure

```
frontend/
  app/globals.css          — os-* design tokens
  components/cfo/          — shell, KPI strip, commentary
  lib/deriveExecutiveKpis.ts — live KPI derivation
  components/ExecutiveFlowDashboard.tsx — section tabs + API data
```

## Section map

| Nav | Content |
|-----|---------|
| Executive Summary | KPIs, focus narrative, GTM pulse |
| ARR Waterfall | MRR/ARR waterfall |
| Revenue & P&L | GAAP, billings, statements |
| GTM / Marketing | Channel efficiency |
| Pipeline | Pipeline + opportunities |
| Cash Forecast | Cash waterfall |
| Risks & Validation | Checks + commentary prompts |

## Executive summary — close artifacts & AI

- **Board & MD&A close artifacts** — featured export cards (PPTX, MD&A Excel, mgmt review, variance)
- **AI executive commentary** — `GET /api/v1/export/executive-commentary` (OpenAI via `OPENAI_API_KEY`)
- **Regenerate** refreshes ChatGPT narrative without exporting

## Next evolutions

- Scenario pills in header (Actual / Budget / Forecast)
- Scenario pills (Actual / Budget / Forecast) in header
- Headcount & productivity section when HC API exists
- Chart.js or shared chart primitives for trend lines in executive tab
