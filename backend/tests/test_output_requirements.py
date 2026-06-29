"""Tests for report output requirement specs and export registry."""

from app.services.reporting.export.export_sheet_registry import MDA_PACKAGE_SHEETS
from app.services.reporting.export.output_requirements import (
    BOARD_PLATFORM_EXPORTS,
    board_platform_export,
    monthly_close_requirements_prompt,
    requirements_for,
    requirements_prompt_block,
)


def test_board_variance_button_uses_full_mda_package() -> None:
    spec = board_platform_export("mda_package_xlsx")
    assert spec.endpoint == "/api/v1/export/mda-package.xlsx"
    assert spec.excel_sheets == tuple(MDA_PACKAGE_SHEETS)
    assert len(spec.excel_sheets) >= 10
    assert "Variance Commentary" in spec.excel_sheets
    assert "Q2 vs Budget" in spec.excel_sheets


def test_board_mda_deck_uses_prompt5_pptx() -> None:
    spec = board_platform_export("mda_deck_pptx")
    assert spec.endpoint == "/api/v1/export/mda-deck.pptx"
    assert spec.pptx_package_mode == "full_board"


def test_monthly_close_prompt_includes_mda_package_tabs() -> None:
    block = monthly_close_requirements_prompt()
    assert "SMPL MD&A Excel Package" in block
    assert "Tab: Variance Commentary" in block
    assert "Tab: ARR Waterfall" in block


def test_copilot_requirements_block() -> None:
    block = requirements_prompt_block("copilot_answer")
    assert "SMPL Copilot" in block
    assert "Primary driver" in block


def test_board_platform_has_two_exports() -> None:
    assert len(BOARD_PLATFORM_EXPORTS) == 2
