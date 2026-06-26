"""Tests for template-first board PPTX export."""

from __future__ import annotations

from app.services.reporting.export.pptx_template_export import (
    _is_exec_nav_text,
    _month_label,
    _period_replacements,
    _prior_month,
    _quarter_label,
    _set_shape_text,
    _ytd_range_label,
    map_template_slides_to_slide_keys,
    repair_executive_nav_links,
    resolve_board_pptx_template,
    roll_template_period_labels,
)
from app.services.reporting.export.schemas import ExportValidationSummary, ReportingBundle
from app.services.dashboard.schemas import ExecutiveFlowResponse


def _minimal_bundle(*, as_of: str = "2026-06") -> ReportingBundle:
    org = "00000000-0000-0000-0000-000000000001"
    return ReportingBundle(
        organization_id=org,
        organization_name="Test Co",
        scenario="Combined",
        period_label=_month_label(as_of),
        as_of_period=as_of,
        start_period="2026-01",
        end_period="2026-12",
        currency="USD",
        executive_flow=ExecutiveFlowResponse(
            organization_id=org,
            scenario="Combined",
            start_period="2026-01",
            end_period="2026-12",
        ),
        validation=ExportValidationSummary(status="pass", failed_count=0, warning_count=0, passed_count=0, checks=[]),
    )


def test_period_label_helpers():
    assert _month_label("2026-06") == "June 2026"
    assert _prior_month("2026-06") == "2026-05"
    assert _quarter_label("2026-06") == "Q2 2026"
    assert _ytd_range_label("2026-06") == "Jan-Jun 2026"


def test_period_replacements_roll_may_to_june():
    bundle = _minimal_bundle(as_of="2026-06")
    patterns = _period_replacements(bundle)
    sample = "Board Review — May 2026 | Q2 2026 | Jan-May 2026"
    rolled = sample
    for pattern, repl in patterns:
        rolled = pattern.sub(repl, rolled)
    assert "June 2026" in rolled
    assert "May 2026" not in rolled
    assert "Jan-Jun 2026" in rolled


def test_resolve_template_returns_none_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.services.reporting.export.pptx_template_export._TEMPLATE_SEARCH_GLOBS",
        ((tmp_path, "*.pptx"),),
    )
    assert resolve_board_pptx_template() is None


def test_exec_nav_text_detection():
    assert _is_exec_nav_text("View waterfall →")
    assert _is_exec_nav_text("View P&L →")
    assert not _is_exec_nav_text("June 2026 close")


def test_roll_preserves_exec_nav_paragraph():
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(2))
    tf = box.text_frame
    tf.paragraphs[0].text = "Board Review — May 2026"
    tf.add_paragraph().text = "View waterfall →"

    bundle = _minimal_bundle(as_of="2026-06")
    roll_template_period_labels(prs, bundle)

    assert "June 2026" in box.text
    assert "View waterfall" in box.text
    assert "May 2026" not in box.text


def test_repair_executive_nav_links_binds_internal_jumps():
    from pptx import Presentation
    from pptx.enum.action import PP_ACTION
    from pptx.util import Inches

    prs = Presentation()
    exec_slide = prs.slides.add_slide(prs.slide_layouts[6])
    exec_box = exec_slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(8), Inches(1.5))
    exec_tf = exec_box.text_frame
    exec_tf.paragraphs[0].text = "Executive Operating Summary"
    exec_tf.add_paragraph().text = "View waterfall →"
    exec_tf.add_paragraph().text = "View driver tree →"
    exec_tf.add_paragraph().text = "View P&L →"
    exec_tf.add_paragraph().text = "View cash →"

    arr_slide = prs.slides.add_slide(prs.slide_layouts[6])
    arr_slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(6), Inches(1)).text = "ARR / MRR Waterfall"
    driver_slide = prs.slides.add_slide(prs.slide_layouts[6])
    driver_slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(6), Inches(1)).text = "Net New ARR driver decomposition"
    pl_slide = prs.slides.add_slide(prs.slide_layouts[6])
    pl_slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(6), Inches(1)).text = "Department Spend - P&L"
    cash_slide = prs.slides.add_slide(prs.slide_layouts[6])
    cash_slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(6), Inches(1)).text = "Cash Forecast"

    repaired = repair_executive_nav_links(prs)
    assert repaired == 4

    for label in ("View waterfall", "View driver", "View P&L", "View cash"):
        found = False
        for paragraph in exec_tf.paragraphs:
            for run in paragraph.runs:
                if label.lower() in (run.text or "").lower():
                    r_pr = run._r.rPr
                    assert r_pr is not None and r_pr.hlinkClick is not None
                    assert r_pr.hlinkClick.action == "ppaction://hlinksldjump"
                    assert r_pr.hlinkClick.rId
                    found = True
        assert found, label

    assert exec_box.click_action.action == PP_ACTION.NONE


def test_map_template_slides_to_slide_keys():
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    slides_text = [
        "Executive Summary — Where we stand",
        "ARR Analysis / MRR Waterfall",
        "P&L Review — Income Statement",
        "Cash & Liquidity — Cash Forecast",
        "GTM & Marketing — Channel efficiency",
        "Workforce & Headcount",
        "Risks & Opportunities",
    ]
    for title in slides_text:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(8), Inches(1)).text = title

    mapping = map_template_slides_to_slide_keys(prs)
    assert mapping["executive_summary"] == 1
    assert mapping["arr_waterfall"] == 2
    assert mapping["gaap_revenue"] == 3
    assert mapping["cash_forecast"] == 4
    assert mapping["gtm_performance"] == 5
    assert mapping["headcount"] == 6
    assert mapping["risks_opportunities"] == 7


def test_set_shape_text_preserves_multiline_bullets():
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(2))
    _set_shape_text(box, "Key Takeaways\n• Revenue $7.41M vs budget\n• ARR $86.10M")
    assert box.text_frame.paragraphs[0].text == "Key Takeaways"
    assert "Revenue" in box.text_frame.paragraphs[1].text
    assert "ARR" in box.text_frame.paragraphs[2].text
