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
    out = _sanitize_pptxgen_script(script).replace("\r\n", "\n")
    assert "const bridgeY" not in out
    assert "let bridgeY =" in out
    assert "\nbridgeY = 1.2;" in out


def test_sanitize_promotes_const_before_reassign():
    """Matches prod failure: Assignment to constant variable after sanitize."""
    script = """
const kpiW = 2.0;
const kpiW = rightCashW / 2 - 0.05;
"""
    out = _sanitize_pptxgen_script(script).replace("\r\n", "\n")
    assert "let kpiW = 2.0;" in out
    assert "kpiW = rightCashW / 2 - 0.05;" in out
    assert "const kpiW" not in out


def test_sanitize_merges_spaced_identifiers():
    script = "const bridge Y = margins.top;\n"
    out = _sanitize_pptxgen_script(script)
    assert "const bridgeY =" in out
    assert "bridge Y" not in out
