# Executive presentation system

**Engine:** `smpl-board-v2`  
**Package:** `backend/app/presentation/`

## Architecture

```
ReportingBundle (data)
       ↓
board_slides.py          ← AI/content: metrics + commentary only
       ↓
SlideContent (slots)
       ↓
templates/archetypes     ← force layout from slide_id
       ↓
visual_qa/pipeline       ← remediate + validate
       ↓
orchestration/appendix   ← overflow → appendix slides
       ↓
pptx_builder.py          ← render fixed template handlers only
```

## AI responsibilities

| Allowed | Forbidden |
|---------|-----------|
| Populate KPI values | Choose `layout=` per slide |
| Write commentary bullets | Invent grid positions |
| Select metrics from bundle | Add `secondary_chart` |
| Recommend actions in callouts | Stack chart + full table on story slides |

## Adding a new board slide

1. Add `slide_id` to `NARRATIVE_SLIDE_ORDER` if needed.
2. Register `SlideTemplateSpec` in `templates/archetypes.py`.
3. Implement content in `board_slides._build_slide_by_id` — **no** `layout=` argument; use `assemble_slide(slide_id=...)`.
4. Add renderer branch only if new `layout` id (rare).
5. Map chart primitive in `chart_primitives/registry.py`.
6. Document pattern in `docs/design-language/`.

## Verification

```powershell
cd backend
python -m pytest tests/test_presentation_archetypes.py -q
python scripts/verify_board_export.py
```

Ping: `GET /api/v1/export/ping` → `board_engine: smpl-board-v2`
