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


def test_sanitize_rewrites_redeclared_const():
    script = """
const margins = { top: 0.35 };
const bridgeY = margins.top;
const bridgeY = 1.2;
"""
    out = _sanitize_pptxgen_script(script)
    assert out.count("const bridgeY") == 1
    assert "\nbridgeY = 1.2;" in out.replace("\r\n", "\n")


def test_sanitize_merges_spaced_identifiers():
    script = "const bridge Y = margins.top;\n"
    out = _sanitize_pptxgen_script(script)
    assert "const bridgeY =" in out
    assert "bridge Y" not in out
