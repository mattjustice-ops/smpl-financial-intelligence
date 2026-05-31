# SMPL Executive Design Language

This folder encodes **how elite SaaS CFOs communicate** — not how to copy reference decks pixel-for-pixel.

Reference materials live in `docs/reference-decks/`. They inform **presentation grammar**; data logic stays in `reporting_semantic_mappings.py`.

## Principles

1. **Deterministic templates** — Every board `slide_id` maps to one archetype in `backend/app/presentation/templates/archetypes.py`.
2. **AI fills slots only** — Metrics, commentary, recommendations, insights. No runtime layout invention.
3. **Single primary visual** — One chart or one table in the executive band; overflow → appendix.
4. **Fixed grid** — Title / KPI / visual / footer zones (`design_system/zones.py`).
5. **Chart primitives** — Standardized archetypes (`chart_primitives/registry.py`), not dashboard exports.

## Documents

| Doc | Topic |
|-----|--------|
| [layout-hierarchy.md](./layout-hierarchy.md) | Focal points, KPI emphasis, scan order |
| [spacing.md](./spacing.md) | Margins, zone rhythm, whitespace |
| [typography.md](./typography.md) | Title, body, table, chart labels |
| [charts.md](./charts.md) | Axis restraint, legends, archetypes |
| [narrative.md](./narrative.md) | Section flow, transitions, pacing |
| [commentary.md](./commentary.md) | What / why / so what / action tone |
| [reference-deck-grammar.md](./reference-deck-grammar.md) | Patterns extracted from CARET + BOD refs |

## Code map

```
backend/app/presentation/
  design_system/   tokens, zones
  templates/       slide archetype catalog
  components/      KPI strip, commentary panel, etc.
  chart_primitives/  arr waterfall, funnel, cash bridge, …
  visual_qa/       template validation + remediate pipeline
  orchestration/   story order, appendix escalation
```

Engine id: `smpl-board-v2` — see `docs/EXECUTIVE_PRESENTATION_SYSTEM.md`.
