# Validation Engine vs Executive Board

> **Not SOC 2 certified.** Product posture for who sees ties, mapping, and monthly align.

## Posture

| Surface | Audience | Job |
|---------|----------|-----|
| **Board / Platform** | Executives and leadership | Review **validated outcomes** and decide |
| **Validation Engine** | FP&A / Controller / platform owner | Prove **how and why** numbers align each month |

Adaptive and Anaplan earn trust because leadership assumes a system owner already validated the cube. SMPL keeps that executive experience clean, and productizes the owner workshop that Adaptive leaves invisible (ties, Evidence Pack, GL→management mapping, Monthly Align).

**Hard identification** for production actuals remains an **import/close** concern (see [WAREHOUSE_GATE_NEAR_TERM_PLAN.md](./WAREHOUSE_GATE_NEAR_TERM_PLAN.md)). Export-time client A–F and Evidence Pack stay advisory companions; the Validation Engine is where owners **review** them and record **Allow**.

## What lives where

**Board (exec)**

- Clean KPIs, narrative, board actions
- One-line stamp: `Close validated · {period} · by {owner}` (or `Validation pending` with owner deep-link)
- Cite-to-calc: owner mode only (`?owner=1` or Ctrl+Shift+V), not default chrome

**Validation Engine (owner)** — `/validation/`

1. **Close status** — freeze, as-of, last Allow, blockers vs advisories  
2. **Ties** — client A–F, cash spine C1–C5, Evidence Pack / post-render  
3. **Mapping** — new GL / dimension accounts since last Allow; map to management IS / BS / CFS / ARR  
4. **Exports gate** — MD&A / Variance ready when freeze COMPLETE + required ties + mapping queue clear + Allow  

## Monthly Align

Owner ritual per close (~15–30 min): Ties → Mapping queue → Deck fidelity → **Allow**. Allow is persisted on the freeze pack (`sections.validation_allow`) and drives the Board stamp.

## Mapping / new GL accounts

On ingest, accounts (or dimensions) **new since last Allow** enter an Unmapped queue. Material amounts quarantine to Unassigned until mapped. Import/close hard-ID can block when the queue has open material items (Phase 3).

## Sales / partner language (safe)

- “Leadership sees outcomes; finance owns the Validation Engine.”
- “Ties and Evidence Packs are for the system owner — not homework for the board room.”
- Do **not** claim SOC 2 certification or that every warehouse SQL check is live.

## Code map

| Piece | Location |
|-------|----------|
| Owner UI | `frontend/public/validation/index.html` |
| Ties / Continuity module | `frontend/public/shared/board-continuity.js` (engine mode) |
| Board stamp | `frontend/public/board/index.html` + continuity `refreshValidatedStamp` |
| Allow + mapping API | `backend/app/api/validation_engine_routes.py` |
| Service | `backend/app/services/validation_engine/` |
