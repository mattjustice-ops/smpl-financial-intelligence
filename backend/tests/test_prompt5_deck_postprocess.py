"""Unit tests for Prompt 5 deterministic deck post-process (Matt bugs 1–4)."""

from __future__ import annotations

from app.services.reporting.export.prompt5_deck import (
    _fix_slide5_ytd_summary_overlap,
    _fix_slide11_source_overlap,
    _format_node_script_error,
    _inject_deck_runtime_guards,
    _postprocess_prompt5_script,
    _reinject_cfs_variances,
    _reinject_period_matrix_ending_cash_row,
    _sanitize_pptxgen_script,
    _strip_slide2_kpi_sparklines,
    _wrap_writefile_catch,
)


_SPARK_SAMPLE = """
  cards.forEach((c, i) => { kpiCard(slide, 0.35 + i, 0.95, 2.45, 1.0, c.label, c.value, c.sub); });

  // Sparkline charts (slide 2 only)
  const months = ["Jan","Feb","Mar","Apr","May","Jun"];
  const arrData = [76.31, 77.82, 79.51, 81.39, 83.45, 85.31];
  const revData = [5.9, 6.1, 6.4, 6.7, 7.0, 7.35];
  const cashData = [45.30, 46.0, 47.0, 47.5, 49.76, 48.43];

  const sparkDefs = [
    { data: arrData, x: 0.35, color: C.cyan },
    { data: revData, x: 2.87, color: C.amber },
    { data: cashData, x: 5.39, color: C.green }
  ];
  sparkDefs.forEach(sp => {
    slide.addChart(pptx.ChartType.line, [{
      name: "Trend", labels: months, values: sp.data
    }], {
      x: sp.x, y: 1.62, w: 2.3, h: 0.55,
      showLegend: false, showTitle: false, showValue: false,
      chartColors: [sp.color],
      lineDataSymbol: "none"
    });
  });

  addDivider(slide, 0.35, 2.28, 12.63);
  slide.addChart(pptx.ChartType.bar, [{ name: "Keep", labels: ["A"], values: [1] }], { x: 1, y: 3, w: 4, h: 2 });
"""


def test_strip_slide2_kpi_sparklines_removes_sparkdefs_keeps_other_charts() -> None:
    out = _strip_slide2_kpi_sparklines(_SPARK_SAMPLE)
    assert "sparkDefs" not in out
    assert "arrData" not in out
    assert "KPI sparklines removed" in out
    assert "ChartType.bar" in out  # non-sparkline chart kept
    assert "addDivider" in out


def test_fix_slide5_ytd_summary_overlap_nudges_low_y() -> None:
    src = 'addSectionLabel(slide, "YTD Cash Summary", 0.35, 3.60, 4.2);'
    assert "4.05" in _fix_slide5_ytd_summary_overlap(src)
    keep = 'addSectionLabel(slide, "YTD Cash Summary", 0.35, 4.20, 4.2);'
    assert keep == _fix_slide5_ytd_summary_overlap(keep)


def test_fix_slide11_source_overlap_nudges_low_y() -> None:
    src = (
        'slide.addText("Source: build_ts_data.cfs  |  Period: Jan–Jun 2026", '
        "{ x: 0.35, y: 5.35, w: 12.63, h: 0.22 });"
    )
    assert "y: 5.65" in _fix_slide11_source_overlap(src)


def test_reinject_ending_cash_ytd_variance_from_payload() -> None:
    payload = {
        "period_matrix": {
            "rows": [
                {
                    "metric": "Ending Cash",
                    "cm": {
                        "actual": "$50.26M",
                        "budget": "$31.46M",
                        "variance": "+$16.98M",
                    },
                    "ytd": {
                        "actual": "$50.26M",
                        "budget": "$31.46M",
                        "variance": "+$16.98M",
                    },
                }
            ]
        }
    }
    script = (
        '["Ending Cash", "$48.43M", "$31.46M", "+$16.98M", '
        '"$48.43M", "$23.85M", "—"]'
    )
    out = _reinject_period_matrix_ending_cash_row(script, payload)
    assert '"+$16.98M"' in out
    assert "$23.85M" not in out
    assert '"—"' not in out.split("Ending Cash")[1][:120]


def test_reinject_cfs_ap_and_prepaids_variances() -> None:
    payload = {
        "appendix": {
            "ytd_cash_flow_statement": {
                "actual": {
                    "change_in_ap": "$373.5K",
                    "change_in_prepaids": "$75.0K",
                },
                "budget": {
                    "change_in_ap": "$917.7K",
                    "change_in_prepaids": "$75.0K",
                },
                "variance": {
                    "change_in_ap": "-$544.2K",
                    "change_in_prepaids": "+$0.00",
                },
            }
        }
    }
    script = (
        '{ label: "Change in Accounts Payable", actual: "$373.5K", '
        'budget: "$917.7K", variance: "—" },\n'
        '{ label: "Change in Prepaids", actual: "$75.0K", '
        'budget: "$75.0K", variance: "—" },'
    )
    out = _reinject_cfs_variances(script, payload)
    assert 'variance: "-$544.2K"' in out
    assert 'variance: "+$0.00"' in out


def test_postprocess_composes_fixes() -> None:
    payload = {
        "period_matrix": {
            "rows": [
                {
                    "metric": "Ending Cash",
                    "cm": {"actual": "$50.26M", "budget": "$31.46M", "variance": "+$16.98M"},
                    "ytd": {"actual": "$50.26M", "budget": "$31.46M", "variance": "+$16.98M"},
                }
            ]
        },
        "appendix": {
            "ytd_cash_flow_statement": {
                "actual": {"ending_cash": "$50.26M"},
                "budget": {"ending_cash": "$48.17M"},
                "variance": {"ending_cash": "+$2.09M"},
            }
        },
    }
    script = (
        _SPARK_SAMPLE
        + '\naddSectionLabel(slide, "YTD Cash Summary", 0.35, 3.60, 4.2);\n'
        + 'slide.addText("Source: build_ts_data.cfs", { x: 0.35, y: 5.35, w: 12, h: 0.22 });\n'
        + '["Ending Cash", "$1", "$2", "+$3", "$4", "$5", "—"]\n'
        + '{ label: "Ending Cash", actual: "$50.26M", budget: "$48.17M", variance: "—" }\n'
    )
    out = _postprocess_prompt5_script(script, payload)
    assert "sparkDefs" not in out
    assert "4.05" in out
    assert "y: 5.65" in out
    assert '"+$16.98M"' in out
    assert 'variance: "+$2.09M"' in out


def test_format_node_script_error_prefers_message_over_path_prefix() -> None:
    stderr = (
        "/app/scripts/deck-gen/node_modules/pptxgenjs/dist/pptxgen.cjs.js:1234\n"
        "TypeError: Cannot read properties of undefined (reading 'forEach')\n"
    )
    msg = _format_node_script_error(stderr, "")
    assert "TypeError" in msg
    assert "forEach" in msg


def test_sanitize_injects_runtime_guards_and_writefile_catch() -> None:
    src = 'const pptxgen = require("pptxgenjs");\nconst pptx = new pptxgen();\npptx.writeFile({ fileName: "OUTPUT.pptx" });'
    out = _sanitize_pptxgen_script(src)
    assert "_deckArr" in out
    assert "PPTX_WRITE_ERROR" in out
    assert ".catch(" in out


def test_inject_deck_runtime_guards_idempotent() -> None:
    once = _inject_deck_runtime_guards('require("pptxgenjs");')
    twice = _inject_deck_runtime_guards(once)
    assert once.count("_deckArr") == 1
    assert twice == once


def test_wrap_writefile_catch_idempotent() -> None:
    src = 'pptx.writeFile({ fileName: "OUTPUT.pptx" });'
    once = _wrap_writefile_catch(src)
    twice = _wrap_writefile_catch(once)
    assert once.count(".catch(") == 1
    assert twice == once
