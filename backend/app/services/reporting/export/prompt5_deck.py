"""Prompt 5: Claude generates a complete PptxGenJS deck from ReportingBundle data."""

from __future__ import annotations

import calendar
import json
import logging
import os
import re
import subprocess
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.core.config import _BACKEND_ROOT
from app.services.commentary.llm_factory import build_commentary_llm_client
from app.services.reporting.export.board_metrics_snapshot import build_metrics_snapshot
from app.services.reporting.export.board_slide_commentary_payload import fmt_deck_money
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.period_utils import to_period

from app.services.reporting.export.prompt5_v3 import PROMPT5_V3_SYSTEM

logger = logging.getLogger(__name__)

DECK_GEN_DIR = _BACKEND_ROOT / "scripts" / "deck-gen"
ARCHIVE_DIR = _BACKEND_ROOT / "tmp" / "deck-archive"
DECK_OUTPUT_MAX_TOKENS = 64000
DECK_CONTINUATION_MAX_TOKENS = 32000
MAX_SCRIPT_CONTINUATIONS = 2

PROMPT5_SYSTEM = PROMPT5_V3_SYSTEM


def _money_m(value: Decimal | float | int | None) -> str:
    if value is None:
        return "0.00"
    v = Decimal(str(value))
    sign = "-" if v < 0 else ""
    return f"{sign}{abs(v) / Decimal('1000000'):.2f}"


def _money_raw(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(Decimal(str(value)))


def _pct(actual: Decimal, budget: Decimal) -> float | None:
    if budget == 0:
        return None
    return float((actual - budget) / budget * 100)


def _bps(actual: Decimal, budget: Decimal) -> float | None:
    if budget == 0:
        return None
    return float((actual - budget) * 10000)


def _period_label(period: str) -> str:
    year, month = period.split("-")
    return f"{calendar.month_name[int(month)]} {year}"


def _quarter_label(period: str) -> str:
    month = int(period.split("-")[1])
    q = (month - 1) // 3 + 1
    return f"Q{q}"


def _fs_line(bundle: ReportingBundle, needle: str, period: str, scenario: str) -> Decimal:
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if not fs:
        return Decimal("0")
    n = needle.lower()
    for row in fs.income_statement.rows:
        p = to_period(str(row.period)[:7])
        if p != period or row.scenario != scenario:
            continue
        if n in row.line_item.lower() and "deferred" not in row.line_item.lower():
            return row.amount
    return Decimal("0")


def _money_k(val: Decimal) -> str:
    v = float(val)
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"${v / 1_000:.0f}K"
    return f"${v:,.0f}"


def _marketing_by_channel(bundle: ReportingBundle, period: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mkt = bundle.marketing_channel_comparison or bundle.marketing_comparison
    if not mkt:
        return rows
    actual_map: dict[str, Any] = {}
    budget_map: dict[str, Any] = {}
    for row in mkt.actual:
        if row.period != period:
            continue
        ch = row.marketing_channel or "Other"
        actual_map[ch] = row
    for row in mkt.budget:
        if row.period != period:
            continue
        ch = row.marketing_channel or "Other"
        budget_map[ch] = row
    for ch in sorted(set(actual_map) | set(budget_map)):
        a = actual_map.get(ch)
        b = budget_map.get(ch)
        spend = a.marketing_spend if a else Decimal("0")
        spend_bud = b.marketing_spend if b else Decimal("0")
        pipe = a.pipeline_arr_created if a else Decimal("0")
        mqls = a.mqls if a else Decimal("0")
        eff = float(pipe / spend) if spend else 0.0
        wr = float(a.win_rate_on_pipeline_created) if a and a.win_rate_on_pipeline_created else 0.0
        rows.append(
            {
                "name": ch,
                "spend": _money_k(spend),
                "spend_budget": _money_k(spend_bud),
                "spend_raw": float(spend),
                "spend_budget_raw": float(spend_bud),
                "mqls": float(mqls),
                "pipeline": _money_k(pipe),
                "pipeline_raw": float(pipe),
                "efficiency_x": round(eff, 1),
                "efficiency_label": f"{eff:.1f}x pipeline/spend" if spend else "n/a",
                "win_rate_pct": round(wr * 100, 1) if wr <= 1 else round(wr, 1),
            }
        )
    rows.sort(key=lambda r: r.get("spend_raw") or 0, reverse=True)
    return rows[:5]


def _risks_and_opportunities(bundle: ReportingBundle, m) -> dict[str, Any]:
    """Structured risks + opportunities for slide 8 two-column grid."""
    risks: list[dict[str, str]] = []
    opps: list[dict[str, str]] = []

    def add_risk(level: str, title: str, detail: str, action: str, impact: str = "") -> None:
        risks.append(
            {"level": level, "type": "RISK", "title": title, "detail": detail, "action": action, "impact": impact}
        )

    def add_opp(level: str, title: str, detail: str, action: str, upside: str = "") -> None:
        opps.append(
            {"level": level, "type": "OPP", "title": title, "detail": detail, "action": action, "upside": upside}
        )

    cur = bundle.currency
    if m.churn and m.ending_arr and m.churn / m.ending_arr > Decimal("0.03"):
        add_risk(
            "HIGH",
            "Churn concentration",
            f"Churn {_money_m(m.churn)}M vs ending ARR {_money_m(m.ending_arr)}M in {bundle.as_of_period}.",
            "Segment churn by cohort; tighten renewal playbook for at-risk accounts.",
            fmt_deck_money(m.churn),
        )
    if m.slipped and m.slipped > Decimal("500000"):
        add_risk(
            "MEDIUM",
            "Deferred pipeline",
            f"Slipped pipeline {_money_m(m.slipped)}M requires next-quarter coverage review.",
            "Re-stage opportunities with validated next steps and owners.",
            fmt_deck_money(m.slipped),
        )
    if m.net_new_arr and m.new_arr_budget and m.net_new_arr > m.new_arr_budget:
        add_opp(
            "HIGH",
            "Net new ARR beat",
            f"Net new ARR {_money_m(m.net_new_arr)}M exceeded budget {_money_m(m.new_arr_budget)}M.",
            "Double down on winning channels and rep capacity in H2.",
            fmt_deck_money(m.net_new_arr - m.new_arr_budget),
        )
    if m.cash_actual and m.cash_actual > Decimal("50000000"):
        add_opp(
            "MEDIUM",
            "Liquidity headroom",
            f"Cash {_money_m(m.cash_actual)}M provides runway for strategic investments.",
            "Prioritize high-ROI GTM and product bets with board approval.",
            fmt_deck_money(m.cash_actual - Decimal("10000000")),
        )
    for field in bundle.mda_commentary or bundle.commentary_fields:
        text = " ".join(
            p for p in [field.unfavorable, field.leadership_attention, field.recommended_actions] if p
        ).strip()
        if not text:
            continue
        if field.unfavorable:
            add_risk("MEDIUM", field.section[:60], text[:240], (field.recommended_actions or "Review.")[:120])
        else:
            add_opp("MEDIUM", field.section[:60], text[:240], (field.recommended_actions or "Review.")[:120])

    while len(risks) < 4:
        risks.append(
            {
                "level": "MEDIUM",
                "type": "RISK",
                "title": "Close validation",
                "detail": f"Validation status: {bundle.validation.status}. Confirm tie-outs before distribution.",
                "action": "Finance to certify waterfall and GL reconciliations.",
                "impact": "",
            }
        )
    while len(opps) < 4:
        opps.append(
            {
                "level": "MEDIUM",
                "type": "OPP",
                "title": "Operating leverage",
                "detail": f"YTD revenue {_money_m(m.revenue_actual)}M with gross margin target on track.",
                "action": "Maintain discipline on opex pacing through H2.",
                "upside": "",
            }
        )
    return {"risks": risks[:4], "opportunities": opps[:4]}


def _board_actions(bundle: ReportingBundle) -> list[dict[str, str]]:
    period = bundle.as_of_period
    month = _period_label(period)
    return [
        {
            "number": "01",
            "type": "FOR APPROVAL",
            "title": f"Approve {month} financial close package",
            "owner": "CFO",
            "due": "Board meeting",
        },
        {
            "number": "02",
            "type": "FOR APPROVAL",
            "title": "Approve updated FY ARR outlook and GTM plan",
            "owner": "CEO / CRO",
            "due": "Next board cycle",
        },
        {
            "number": "03",
            "type": "FOR APPROVAL",
            "title": "Approve headcount and hiring plan adjustments",
            "owner": "CFO / CHRO",
            "due": "Next board cycle",
        },
        {
            "number": "04",
            "type": "FOR DISCUSSION",
            "title": "Pipeline coverage and channel efficiency reallocation",
            "owner": "CRO",
            "due": "Operating review",
        },
    ]


def _marketing_block(bundle, as_of, m):
    channels = _marketing_by_channel(bundle, as_of)
    total_spend = sum(c.get("spend_raw") or 0 for c in channels)
    total_pipe = sum(c.get("pipeline_raw") or 0 for c in channels)
    best_wr = max(channels, key=lambda c: c["win_rate_pct"], default=None)
    return {
        "total_mqls": float(m.mql),
        "total_pipeline": _money_k(m.pipeline_from_marketing or m.pipeline_created),
        "total_spend": _money_k(m.marketing_spend),
        "blended_efficiency_x": round(total_pipe / total_spend, 1) if total_spend else 0,
        "best_win_rate_channel": best_wr["name"] if best_wr else "",
        "best_win_rate_pct": best_wr["win_rate_pct"] if best_wr else 0,
        "channels": channels,
        "table_columns": [
            "Channel",
            "Spend (Act)",
            "Spend (Bud)",
            "Pipeline (Act)",
            "MQLs",
            "Efficiency",
            "Win Rate",
        ],
        "format_note": "Channel spend and pipeline pre-formatted — display verbatim",
        "pipeline_coverage_x": (
            f"{float(m.pipeline_created / m.closed_won):.1f}x" if m.closed_won else "n/a"
        ),
        "closed_won": _money_k(m.closed_won),
    }


def build_prompt5_payload(
    bundle: ReportingBundle,
    ts_data: dict | None = None,
    cash_bridge_data: dict | None = None,
) -> dict[str, Any]:
    """Board-platform-aligned payload for Claude Prompt 5."""
    from app.services.reporting.export.board_platform_metrics import (
        build_deck_payload,
        validate_deck_payload,
    )

    m = build_metrics_snapshot(bundle)
    as_of = bundle.as_of_period
    payload = build_deck_payload(bundle, ts_data=ts_data, cash_bridge_data=cash_bridge_data)
    payload["gtm_performance"] = _marketing_block(bundle, as_of, m)
    payload["risks_and_opportunities"] = _risks_and_opportunities(bundle, m)
    payload["board_actions"] = _board_actions(bundle)
    from app.services.reporting.export.deck_payload_enriched import enrich_deck_payload

    payload = enrich_deck_payload(payload, bundle, ts_data=ts_data)
    payload["payload_warnings"] = validate_deck_payload(payload)
    return payload


def build_prompt5_user_message(
    bundle: ReportingBundle,
    ts_data: dict[str, Any] | None = None,
    cash_bridge_data: dict[str, Any] | None = None,
    *,
    freeze_context_text: str | None = None,
    freeze_context_as_of: str | None = None,
    freeze_status: str | None = None,
    freeze_stale: bool = False,
    payload: dict[str, Any] | None = None,
) -> str:
    if payload is None:
        payload = build_prompt5_payload(bundle, ts_data=ts_data, cash_bridge_data=cash_bridge_data)
    pc = payload["period_context"]
    warnings = payload.get("payload_warnings") or []
    warn_block = ""
    if warnings:
        warn_block = "PAYLOAD WARNINGS (omit empty sections, do not invent data):\n" + "\n".join(
            f"- {w}" for w in warnings
        ) + "\n\n"

    from app.services.reporting.export.freeze_prompt import format_freeze_prompt_block

    # Quality-first: never truncate freeze prose for Prompt 5 — slide numbers still from JSON.
    freeze_max = None
    freeze_block = format_freeze_prompt_block(
        context_text=freeze_context_text,
        context_as_of=freeze_context_as_of,
        status=freeze_status,
        stale=freeze_stale,
        max_chars=freeze_max,
        number_guidance=(
            "Use this freeze for narrative tone, drivers, and period framing. "
            "Copy slide numbers from DATA PAYLOAD JSON verbatim — do not invent figures."
        ),
    )

    from app.services.reporting.export.board_platform_metrics import evidence_values_from_deck_payload

    evidence_values = evidence_values_from_deck_payload(payload)
    evidence_preview = {
        k: str(v) for k, v in list(evidence_values.items())[:400]
    }
    evidence_block = (
        "EVIDENCE PACKAGE (P15 — every customer-visible $ / % / Nx in the script must "
        f"match these values within TOL_ACTUALS=$1.00):\n"
        f"{json.dumps(evidence_preview, separators=(',', ':'))}\n\n"
    )

    return (
        "Build the complete SMPL.ai board deck PptxGenJS script using the JSON data payload below.\n"
        "Follow the per-slide layout assignments in the system prompt exactly.\n"
        "Slide 1: centered cover (cyan SMPL.ai, divider, no CONFIDENTIAL). "
        "Slide 3: waterfall_chart.shape_bars with addShape rectangles ONLY — no addChart on slide 3.\n"
        "Slides 1–10 main deck; slide 11 appendix CFS. Copy numbers verbatim.\n\n"
        f"{freeze_block}"
        f"{evidence_block}"
        f"PERIOD CONTEXT\n"
        f"Close period: {pc['close_period_label']}\n"
        f"Quarter: {pc['quarter']}\n"
        f"YTD label: {pc['ytd_label']}\n"
        f"Output filename: {pc['output_filename']}\n\n"
        f"{warn_block}"
        "DATA PAYLOAD (JSON):\n"
        f"{json.dumps(payload, separators=(',', ':'))}\n\n"
        "Generate the complete Node.js PptxGenJS script now. Return only the script — "
        "no explanation, no markdown fences, no preamble. The script must end with "
        "pptx.writeFile({ fileName: ... }) and be immediately executable with: node generate_deck.js"
    )


def _strip_markdown_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[\w]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    return cleaned.strip()


def _script_is_complete(script: str) -> bool:
    return "pptx.writeFile(" in script and ("require(" in script or "require (" in script)


def _detect_pptx_instance_var(script: str) -> str:
    match = re.search(
        r"(?:const|let|var)\s+(\w+)\s*=\s*new\s+(?:pptxgen|PptxGenJS)\s*\(",
        script,
        re.IGNORECASE,
    )
    return match.group(1) if match else "pptx"


def _fix_spaced_identifiers(script: str) -> str:
    """Merge accidental spaces in declarations: `const bridge Y =` → `const bridgeY =`."""
    return re.sub(
        r"\b(const|let|var)\s+([A-Za-z_][\w]*)\s+([A-Za-z_][\w]*)\s*=",
        r"\1 \2\3 =",
        script,
    )


def _rewrite_redeclared_bindings(script: str) -> str:
    """Fix duplicate const/let bindings Claude emits across slides.

    Redeclaring `const bridgeY` is a SyntaxError. Naively rewriting the second
    line to `bridgeY =` still throws at runtime if the first binding stayed
    `const` ("Assignment to constant variable"). Promote the first decl to
    `let`, then turn later decls into assignments.
    """
    decl_counts: dict[str, int] = {}
    for line in script.splitlines():
        match = re.match(r"^(\s*)(const|let|var)\s+([A-Za-z_]\w*)\s*=", line)
        if match:
            name = match.group(3)
            decl_counts[name] = decl_counts.get(name, 0) + 1
    redeclared = {name for name, count in decl_counts.items() if count > 1}

    seen: set[str] = set()
    out: list[str] = []
    for line in script.splitlines():
        match = re.match(r"^(\s*)(const|let|var)\s+([A-Za-z_]\w*)\s*=", line)
        if match:
            name = match.group(3)
            if name in redeclared:
                if name in seen:
                    line = re.sub(
                        r"^(\s*)(const|let|var)\s+([A-Za-z_]\w*)\s*=",
                        rf"\1{name} =",
                        line,
                        count=1,
                    )
                else:
                    line = re.sub(
                        r"^(\s*)(const|let|var)\s+",
                        r"\1let ",
                        line,
                        count=1,
                    )
                    seen.add(name)
            else:
                seen.add(name)
        out.append(line)
    return "\n".join(out)


def _sanitize_pptxgen_script(script: str) -> str:
    """Fix common Claude PptxGenJS API mistakes before Node execution."""
    script = _fix_spaced_identifiers(script)
    script = _rewrite_redeclared_bindings(script)
    inst = _detect_pptx_instance_var(script)
    # ShapeType / ChartType live on the presentation instance, not the constructor.
    for ctor in ("pptxgen", "PptxGenJS", "PptxGenjs"):
        script = script.replace(f"{ctor}.ShapeType", f"{inst}.ShapeType")
        script = script.replace(f"{ctor}.ChartType", f"{inst}.ChartType")
    # Thin rect is more reliable than line shapes across PptxGenJS versions.
    script = script.replace(f"{inst}.ShapeType.line", f"{inst}.ShapeType.rect")
    return script


def _prepare_script(script: str, output_path: Path) -> str:
    script = _strip_markdown_fences(script)
    script = _sanitize_pptxgen_script(script)
    out = output_path.as_posix().replace("\\", "/")
    if "pptx.writeFile(" in script:
        script = re.sub(
            r"pptx\.writeFile\s*\(\s*\{[^}]*fileName\s*:\s*['\"][^'\"]*['\"]",
            f'pptx.writeFile({{ fileName: "{out}"',
            script,
            count=1,
        )
    else:
        script += f'\npptx.writeFile({{ fileName: "{out}" }});\n'
    return script


def _excerpt_for_fix(text: str, *, limit: int = 24000) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return text[:half] + "\n\n/* ... middle omitted ... */\n\n" + text[-half:]


def _build_fix_prompt(*, last_error: str, failed_script: str, payload_json: str) -> str:
    return (
        "The previous PptxGenJS Node.js script failed. Fix it and return a complete "
        "executable script for all 11 slides.\n\n"
        f"ERROR:\n{last_error}\n\n"
        "HARD RULES:\n"
        "- Valid JavaScript only — no prose, no markdown, no layout notes as code.\n"
        "- Never redeclare the same const/let name (use unique names per slide or reassign).\n"
        "- Identifiers must be camelCase with no spaces (bridgeY not 'bridge Y').\n"
        "- Use pptx.ShapeType / pptx.ChartType on the pptx instance, never pptxgen.ShapeType.\n"
        "- Charts: only slides 2, 6, 9 via addChart; slide 3 waterfall uses ShapeType.rect bars only.\n"
        "- Chart data must be numeric arrays; labels must be string arrays.\n"
        "- End with pptx.writeFile({ fileName: 'OUTPUT.pptx' }).\n"
        "- Copy numbers from DATA PAYLOAD verbatim.\n\n"
        f"FAILED SCRIPT:\n{_excerpt_for_fix(failed_script)}\n\n"
        f"DATA PAYLOAD (JSON):\n{_excerpt_for_fix(payload_json, limit=20000)}\n\n"
        "Return only the corrected raw JavaScript."
    )


def _ensure_deck_gen_runtime() -> None:
    node_modules = DECK_GEN_DIR / "node_modules" / "pptxgenjs"
    if node_modules.exists():
        return
    logger.info("Installing pptxgenjs in %s", DECK_GEN_DIR)
    subprocess.run(
        ["npm", "install", "--omit=dev"],
        cwd=DECK_GEN_DIR,
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )


def _check_node_syntax(script_path: Path) -> None:
    """Fail fast on SyntaxError before pptxgenjs runtime work."""
    result = subprocess.run(
        ["node", "--check", str(script_path)],
        cwd=DECK_GEN_DIR,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Node deck script syntax error: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )


def _run_node_script(script_path: Path, output_path: Path) -> None:
    _ensure_deck_gen_runtime()
    _check_node_syntax(script_path)
    env = os.environ.copy()
    env["NODE_PATH"] = str(DECK_GEN_DIR / "node_modules")
    result = subprocess.run(
        ["node", str(script_path)],
        cwd=DECK_GEN_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Node deck script failed (exit {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    if not output_path.exists() or output_path.stat().st_size < 1000:
        raise RuntimeError(
            f"PptxGenJS did not produce output at {output_path}. "
            f"stdout: {result.stdout[:500]}"
        )


def _archive_failed_script(period: str, script: str, label: str) -> Path:
    dest = ARCHIVE_DIR / period
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{label}.js"
    path.write_text(script, encoding="utf-8")
    return path


def _generate_deck_script_text(client: Any, user_prompt: str, *, system_prompt: str | None = None) -> str:
    """Call Claude; auto-continue if output truncates before pptx.writeFile."""
    sys_prompt = system_prompt or PROMPT5_SYSTEM
    text = _strip_markdown_fences(
        client.generate_text(  # type: ignore[attr-defined]
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
            max_tokens=DECK_OUTPUT_MAX_TOKENS,
        )
    )
    continuations = 0
    while not _script_is_complete(text) and continuations < MAX_SCRIPT_CONTINUATIONS:
        tail = text[-6000:]
        logger.warning(
            "Prompt 5 script incomplete (%s chars) — continuation %s/%s",
            len(text),
            continuations + 1,
            MAX_SCRIPT_CONTINUATIONS,
        )
        cont_prompt = (
            "The PptxGenJS Node.js deck script below was truncated before pptx.writeFile(). "
            "Continue from the exact last character. Output ONLY the remaining JavaScript — "
            "do not restart or repeat earlier slides. Finish slides 9–11 if missing. "
            "End with: pptx.writeFile({ fileName: 'OUTPUT.pptx' }). "
            "Return raw JavaScript only — no markdown fences.\n\n"
            f"--- TRUNCATED TAIL ---\n{tail}"
        )
        chunk = _strip_markdown_fences(
            client.generate_text(  # type: ignore[attr-defined]
                system_prompt=sys_prompt,
                user_prompt=cont_prompt,
                max_tokens=DECK_CONTINUATION_MAX_TOKENS,
            )
        )
        if chunk.lstrip().startswith("const pptxgen"):
            marker = chunk.find("pptx.addSlide")
            if marker > 0:
                chunk = chunk[marker:]
        text = text.rstrip() + "\n" + chunk.lstrip()
        continuations += 1
    return text


def _archive_artifacts(period: str, script: str, pptx_bytes: bytes) -> None:
    try:
        dest = ARCHIVE_DIR / period
        dest.mkdir(parents=True, exist_ok=True)
        (dest / f"generate_deck_{period}.js").write_text(script, encoding="utf-8")
        (dest / f"mda_deck_{period}.pptx").write_bytes(pptx_bytes)
    except OSError as exc:
        logger.warning("Could not archive deck artifacts: %s", exc)


def _render_prepared_script(script_text: str, *, period: str) -> tuple[bytes, str]:
    """Prepare, syntax-check, run Node, archive on success. Returns (bytes, prepared_script)."""
    with tempfile.TemporaryDirectory(prefix="smpl-deck-") as tmp:
        tmp_dir = Path(tmp)
        output_path = tmp_dir / f"mda_deck_{period}.pptx"
        script_path = tmp_dir / "generate_deck.js"
        prepared = _prepare_script(script_text, output_path)
        script_path.write_text(prepared, encoding="utf-8")
        _run_node_script(script_path, output_path)
        pptx_bytes = output_path.read_bytes()
        _archive_artifacts(period, prepared, pptx_bytes)
        return pptx_bytes, prepared


def _verify_prompt5_script_or_raise(script: str, payload: dict[str, Any]) -> None:
    """P15 hard block: invented display $ / % in PPTX script string literals."""
    from app.services.commentary.claim_verify import verify_pptx_script_against_evidence
    from app.services.reporting.export.board_platform_metrics import (
        evidence_values_from_deck_payload,
    )

    evidence = evidence_values_from_deck_payload(payload)
    result = verify_pptx_script_against_evidence(script, evidence, fail_closed=True)
    if result.ok:
        logger.info("P15 Prompt 5 claim-verify passed (%s checks)", len(result.checks))


def _try_adapt_from_reference(
    client: Any,
    *,
    period: str,
    payload_json: str,
    payload: dict[str, Any] | None = None,
) -> tuple[bytes, str] | None:
    """Last-resort: adapt a known-good reference script to the current payload."""
    from app.services.reporting.export.deck_gold import resolve_reference_script
    from app.services.reporting.export.prompt5_adapt import PROMPT5_ADAPT_SYSTEM

    ref_path, kind = resolve_reference_script(period)
    if ref_path is None:
        return None
    try:
        ref_script = ref_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not read reference deck script %s: %s", ref_path, exc)
        return None
    if len(ref_script) < 1000:
        return None

    logger.info(
        "Prompt 5 adapting %s reference script (%s)",
        kind or "bundled",
        ref_path,
    )
    adapt_prompt = (
        f"Adapt the reference PptxGenJS script for close period {period}.\n"
        "Preserve layout/helpers; replace data values from the payload.\n"
        "Return complete raw JavaScript ending with pptx.writeFile({ fileName: 'OUTPUT.pptx' }).\n\n"
        f"REFERENCE SCRIPT:\n{_excerpt_for_fix(ref_script, limit=40000)}\n\n"
        f"DATA PAYLOAD (JSON):\n{_excerpt_for_fix(payload_json, limit=20000)}\n"
    )
    script_text = _generate_deck_script_text(
        client, adapt_prompt, system_prompt=PROMPT5_ADAPT_SYSTEM
    )
    if not _script_is_complete(script_text):
        raise RuntimeError(
            f"Adapt fallback incomplete ({len(script_text)} chars, no pptx.writeFile)"
        )
    if payload is not None:
        _verify_prompt5_script_or_raise(script_text, payload)
    pptx_bytes, _ = _render_prepared_script(script_text, period=period)
    return pptx_bytes, f"claude_adapt_{kind or 'bundled'}"


def build_claude_deck_pptx_bytes(
    bundle: ReportingBundle,
    *,
    ts_data: dict[str, Any] | None = None,
    cash_bridge_data: dict[str, Any] | None = None,
    max_retries: int = 1,
    freeze_context_text: str | None = None,
    freeze_context_as_of: str | None = None,
    freeze_status: str | None = None,
    freeze_stale: bool = False,
) -> tuple[bytes, str]:
    """Prompt 5: adapt known-good layout first; fresh Claude script only if needed."""
    from app.services.commentary.claim_verify import CommentaryIntegrityError

    client = build_commentary_llm_client(purpose="export")
    if not hasattr(client, "generate_text"):
        raise RuntimeError("Configured LLM client does not support raw text generation.")

    payload = build_prompt5_payload(bundle, ts_data=ts_data, cash_bridge_data=cash_bridge_data)
    payload_json = json.dumps(payload, separators=(",", ":"))
    last_error = ""

    # Adapt-first: one Claude call against a shipped reference script is faster and
    # more reliable than 3 fresh layout regenerations (which blow the 10–15 min UI budget).
    try:
        adapted = _try_adapt_from_reference(
            client,
            period=bundle.as_of_period,
            payload_json=payload_json,
            payload=payload,
        )
        if adapted is not None:
            return adapted
    except (RuntimeError, CommentaryIntegrityError) as adapt_exc:
        last_error = str(adapt_exc)
        logger.warning("Prompt 5 adapt-first failed: %s", adapt_exc)

    user_message = build_prompt5_user_message(
        bundle,
        ts_data=ts_data,
        cash_bridge_data=cash_bridge_data,
        freeze_context_text=freeze_context_text,
        freeze_context_as_of=freeze_context_as_of,
        freeze_status=freeze_status,
        freeze_stale=freeze_stale,
        payload=payload,
    )
    system_prompt = PROMPT5_SYSTEM
    script_text = ""

    for attempt in range(max_retries + 1):
        try:
            if attempt == 0:
                script_text = _generate_deck_script_text(
                    client, user_message, system_prompt=system_prompt
                )
            else:
                fix_prompt = _build_fix_prompt(
                    last_error=last_error,
                    failed_script=script_text or "",
                    payload_json=payload_json,
                )
                script_text = _generate_deck_script_text(
                    client, fix_prompt, system_prompt=system_prompt
                )

            if not _script_is_complete(script_text):
                failed = _archive_failed_script(
                    bundle.as_of_period,
                    script_text,
                    f"incomplete_attempt_{attempt + 1}",
                )
                last_error = (
                    f"Script incomplete after continuations ({len(script_text)} chars, "
                    f"no pptx.writeFile). Saved: {failed}"
                )
                logger.error(last_error)
                continue

            _verify_prompt5_script_or_raise(script_text, payload)
            pptx_bytes, _ = _render_prepared_script(
                script_text, period=bundle.as_of_period
            )
            return pptx_bytes, "claude_prompt5"
        except (RuntimeError, CommentaryIntegrityError) as exc:
            last_error = str(exc)
            logger.warning("Prompt 5 deck attempt %s failed: %s", attempt + 1, last_error)
            if script_text:
                _archive_failed_script(
                    bundle.as_of_period,
                    script_text,
                    f"failed_attempt_{attempt + 1}",
                )

    raise RuntimeError(
        f"Claude deck generation failed after adapt + {max_retries + 1} fresh attempts. "
        f"Last error: {last_error or 'unknown'}"
    )
