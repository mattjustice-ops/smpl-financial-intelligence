"""Evidence Pack + outlook _sources for Continuity / cite-to-calc."""

from __future__ import annotations

from app.services.reporting.export.evidence_pack import (
    build_evidence_pack,
    post_render_to_dict,
    render_evidence_pack_html,
)


def test_evidence_pack_includes_defendable_claim() -> None:
    pack = build_evidence_pack(
        as_of_period="2026-06",
        export_kind="mda_deck",
        pptx_source="claude_prompt5_adapt",
        freeze_status="COMPLETE",
        post_render={
            "ok": True,
            "summary": "post-render ok",
            "numeric_failures": 0,
            "anchor_failures": 0,
            "narrative_issues": 0,
            "slide_count": 11,
            "text_shape_count": 40,
        },
    )
    assert pack["schema"] == "smpl.evidence_pack.v1"
    assert "does not invent the dollars" in pack["claim"]
    assert "SOC 2 certified" in pack["not_claimed"]
    assert "Evidence Pack" in pack["html"]
    assert "2026-06" in pack["html"]
    assert pack["post_render_ok"] is True


def test_render_evidence_pack_html_escapes() -> None:
    html = render_evidence_pack_html(
        {
            "summary": "a <b>sum",
            "claim": "safe",
            "as_of_period": "2026-06",
            "not_claimed": ["chart <tag>"],
        }
    )
    assert "<b>" not in html
    assert "&lt;b&gt;" in html or "a &lt;b&gt;sum" in html


def test_post_render_to_dict_duck_type() -> None:
    class _N:
        failures = [1, 2]

        def summary(self):
            return "2 failed"

    class _R:
        ok = False
        numeric = _N()
        anchors = _N()
        narrative = type("Narr", (), {"issues": [1], "summary": lambda self: "n"})()
        slide_count = 11
        text_shape_count = 3

        def summary(self):
            return "soft-warn"

    d = post_render_to_dict(_R())
    assert d["ok"] is False
    assert d["numeric_failures"] == 2
    assert d["slide_count"] == 11
