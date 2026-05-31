"""Top-level orchestrator: inputs -> BoardPackage (+ optional artifacts)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.services.board_package.package import build_board_package
from app.services.board_package.pptx_builder import render_pptx_bytes
from app.services.board_package.schemas import BoardPackage, BoardPackageInputs
from app.services.board_package.slides_structure import to_google_slides_requests


@dataclass
class BoardPackageBundle:
    """Holds every artifact produced for a single board package request."""

    package: BoardPackage
    pptx_bytes: Optional[bytes] = None
    google_slides_requests: Optional[dict] = None


def generate_board_package(
    inputs: BoardPackageInputs,
    *,
    include_pptx: bool = False,
    include_google_slides: bool = False,
) -> BoardPackageBundle:
    """Build the canonical board package; optionally render artifacts.

    The canonical `BoardPackage` is always returned. Set `include_pptx` /
    `include_google_slides` to also render the binary .pptx and the Google
    Slides batchUpdate payload respectively.
    """
    package = build_board_package(inputs)
    return BoardPackageBundle(
        package=package,
        pptx_bytes=render_pptx_bytes(package) if include_pptx else None,
        google_slides_requests=(
            to_google_slides_requests(package) if include_google_slides else None
        ),
    )
