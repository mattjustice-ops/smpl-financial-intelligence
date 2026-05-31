"""HTTP routes for the board reporting package generator.

Three endpoints, one canonical builder:
- POST /api/v1/board-package/generate     -> JSON BoardPackage
- POST /api/v1/board-package/pptx         -> binary .pptx download
- POST /api/v1/board-package/slides-structure -> Google Slides batchUpdate JSON
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from app.services.board_package.schemas import BoardPackage, BoardPackageInputs
from app.services.board_package.service import generate_board_package

board_package_router = APIRouter(prefix="/board-package", tags=["board-package"])


@board_package_router.post("/generate", response_model=BoardPackage)
def generate_package_endpoint(inputs: BoardPackageInputs) -> BoardPackage:
    """Return the canonical 10-slide JSON board package."""
    bundle = generate_board_package(inputs)
    return bundle.package


@board_package_router.post("/pptx")
def generate_pptx_endpoint(inputs: BoardPackageInputs) -> Response:
    """Return a downloadable .pptx file built from the canonical package."""
    try:
        bundle = generate_board_package(inputs, include_pptx=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to render pptx: {exc}") from exc
    assert bundle.pptx_bytes is not None
    safe_period = inputs.period_label.replace(" ", "_").replace("/", "_")
    filename = f"board_package_{safe_period}.pptx"
    return Response(
        content=bundle.pptx_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@board_package_router.post("/slides-structure")
def generate_slides_structure_endpoint(inputs: BoardPackageInputs) -> dict:
    """Return a Google Slides API batchUpdate request payload.

    The response has the shape::

        {"presentation_title": str, "requests": [...batchUpdate request items...]}
    """
    bundle = generate_board_package(inputs, include_google_slides=True)
    return bundle.google_slides_requests or {"presentation_title": "", "requests": []}
