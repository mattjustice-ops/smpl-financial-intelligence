"""Tests for PptxGenJS script sanitization."""

from app.services.reporting.export.prompt5_deck import _sanitize_pptxgen_script


def test_sanitize_pptxgen_shape_type_to_instance():
    script = """
const pptxgen = require("pptxgenjs");
const pptx = new pptxgen();
slide.addShape(pptxgen.ShapeType.line, { x: 1, y: 1, w: 5, h: 0 });
"""
    out = _sanitize_pptxgen_script(script)
    assert "pptxgen.ShapeType" not in out
    assert "pptx.ShapeType.rect" in out


def test_sanitize_preserves_correct_instance_usage():
    script = "slide.addShape(pptx.ShapeType.rect, {});"
    assert _sanitize_pptxgen_script(script) == script
