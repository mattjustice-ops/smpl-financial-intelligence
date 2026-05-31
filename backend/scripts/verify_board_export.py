"""Verify board export pipeline — run: .venv\\Scripts\\python.exe scripts\\verify_board_export.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.board_package.pptx_builder import PRESENTATION_ENGINE_VERSION, render_pptx_bytes
from app.services.reporting.export.board_export_service import build_board_package_from_bundle
from app.services.reporting.export.schemas import ReportingBundle
from app.services.dashboard.schemas import ExecutiveFlowResponse
from app.services.reporting.export.schemas import ExportValidationSummary, ValidationCheck


def main() -> None:
    bundle = ReportingBundle(
        organization_id="00000000-0000-0000-0000-000000000001",
        organization_name="SMPL",
        scenario="Combined",
        period_label="May 2026",
        as_of_period="2026-05",
        start_period="2026-01",
        end_period="2026-12",
        currency="USD",
        executive_flow=ExecutiveFlowResponse(
            organization_id="00000000-0000-0000-0000-000000000001",
            scenario="Combined",
            start_period="2026-01",
            end_period="2026-12",
        ),
        validation=ExportValidationSummary(
            status="pass",
            failed_count=0,
            warning_count=0,
            passed_count=1,
            checks=[ValidationCheck(validation_name="stub", status="pass")],
        ),
    )
    pkg = build_board_package_from_bundle(bundle)
    print(f"ENGINE={PRESENTATION_ENGINE_VERSION}")
    print(f"SLIDES={len(pkg.slides)}")
    for s in pkg.slides:
        print(f"  {s.slide_id:28} layout={s.layout:22} chart={bool(s.chart)} table={bool(s.table)}")
    raw = render_pptx_bytes(pkg)
    out = ROOT.parent / "docs" / "reference-decks" / "_verify_output.pptx"
    out.write_bytes(raw)
    print(f"WROTE {out} ({len(raw)} bytes)")


if __name__ == "__main__":
    main()
