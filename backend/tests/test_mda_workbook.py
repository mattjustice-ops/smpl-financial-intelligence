"""The August reference package still renders, and a draft package does not invent a labor tab."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

from app.services.reporting.export.mdna_workbook import render_mdna_workbook

_REFERENCE = Path(__file__).resolve().parents[2] / "docs" / "mda-export" / "reference" / "mdna_package.json"


def test_reference_package_keeps_the_august_sheets() -> None:
    package = json.loads(_REFERENCE.read_text(encoding="utf-8"))
    book = load_workbook(BytesIO(render_mdna_workbook(package)))
    assert book.sheetnames == [
        "Cover",
        "Executive summary",
        "NI walk",
        "Comparison matrix",
        "MoM",
        "QoQ",
        "YoY",
        "YTD",
        "Budget M",
        "Budget YTD",
        "Forecast M",
        "Labor bridge",
        "Watch list",
        "Tie-outs",
        "Line data",
        "Commentary drivers",
    ]
    assert book["Cover"]["A1"].value == "SMPL · MD&A variance commentary"
    assert book["Cover"]["A2"].value == "Aug 2026 close · US01 · GAAP_PRIMARY · USD thousands"
    assert book["Executive summary"]["A1"].value == "Executive summary · August 2026"
    assert "Package JSON" not in book.sheetnames
