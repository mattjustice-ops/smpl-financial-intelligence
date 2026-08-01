"""Prompt 5: Claude generates a complete PptxGenJS deck from ReportingBundle data.

Authoring principle (Matt / Prompt 5 product intent — do not reintroduce template-fill):
- Claude creates slide decks on its own (generative authorship of layout, charts,
  and commentary) — not by filling rigid template slots.
- Prompts teach *craft criteria*: when Claude chooses a visual or commentary form
  (waterfall, Key Takeaways, closed-month Actuals), it must follow the matching
  construction / layout / data rules.
- Board / R&O / GTM / KT packages are **evidence inputs** Claude may cite when
  authoring. They are NOT a post-process source that patches blank takeaways
  after claim-verify soft-strip (no seed-refill / canned slot-fill).
- Soft-strip may redact unmatched $/% tokens inside bullets without blanking the
  whole bullet; do not "fix" emptied strings from seed afterward.
"""

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
    """Structured risks + opportunities for slide 8 — board platform R&O evidence.

    Prefer Board Platform Risks & Opportunities tab cards (renderRisks) as
    authorship evidence over thin heuristic fillers so Claude can keep driver +
    magnitude + action. Live slipped / closed-lost magnitudes are attached as
    package cross-checks.
    """
    from app.services.reporting.export.board_platform_ro_seed import board_ro_cards_for_payload

    seeded = board_ro_cards_for_payload()
    # Cross-check magnitudes from the close package (do not displace board cards).
    package_cross_check: dict[str, Any] = {
        "source": "board_platform_ro_seed",
        "close_period": bundle.as_of_period,
        "slipped_pipeline": _money_k(m.slipped) if m.slipped else "—",
        "slipped_pipeline_raw": float(m.slipped or 0),
        "closed_lost": _money_k(m.closed_lost) if m.closed_lost else "—",
        "closed_lost_raw": float(m.closed_lost or 0),
        "churn": _money_k(m.churn) if m.churn else "—",
        "churn_raw": float(m.churn or 0),
        "ending_arr": _money_k(m.ending_arr) if m.ending_arr else "—",
        "ending_arr_raw": float(m.ending_arr or 0),
        "validation_status": getattr(bundle.validation, "status", None),
    }
    return {
        "risks": seeded["risks"][:4],
        "opportunities": seeded["opportunities"][:4],
        "package_cross_check": package_cross_check,
        "rewrite_policy": (
            "Author card detail+action from BOARD R&O EVIDENCE / these cards — "
            "keep driver, magnitude, action; PPTX-succinct; no thin stubs. "
            "Evidence for authorship, not a blank-slot template."
        ),
    }


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
    from app.services.reporting.export.board_chart_service import _wf
    from app.services.reporting.export.board_platform_metrics import (
        build_pipeline_waterfall_chart,
    )
    from app.services.reporting.period_utils import prior_period

    channels = _marketing_by_channel(bundle, as_of)
    total_spend = sum(c.get("spend_raw") or 0 for c in channels)
    total_pipe = sum(c.get("pipeline_raw") or 0 for c in channels)
    best_wr = max(channels, key=lambda c: c["win_rate_pct"], default=None)
    closed_lost = m.closed_lost or Decimal("0")
    closed_lost_bud = abs(_wf(bundle, "pipeline", "closed_lost", as_of, "Budget"))
    slipped = m.slipped or Decimal("0")
    slipped_bud = abs(_wf(bundle, "pipeline", "slipped_pipeline", as_of, "Budget"))
    ending_pipeline = abs(_wf(bundle, "pipeline", "ending_pipeline", as_of, "Actual"))
    beginning_pipeline = abs(_wf(bundle, "pipeline", "beginning_pipeline", as_of, "Actual"))
    if not beginning_pipeline:
        beginning_pipeline = abs(
            _wf(bundle, "pipeline", "ending_pipeline", prior_period(as_of), "Actual")
        )
    beginning_pipeline_bud = abs(
        _wf(bundle, "pipeline", "beginning_pipeline", as_of, "Budget")
    ) or abs(_wf(bundle, "pipeline", "ending_pipeline", prior_period(as_of), "Budget"))
    ending_pipeline_bud = abs(_wf(bundle, "pipeline", "ending_pipeline", as_of, "Budget"))
    pipe_wf = build_pipeline_waterfall_chart(bundle)
    if not beginning_pipeline and pipe_wf.get("beginning_pipeline_raw"):
        beginning_pipeline = Decimal(str(pipe_wf["beginning_pipeline_raw"]))
    coverage_vs_arr = (
        float(ending_pipeline / m.ending_arr)
        if ending_pipeline and m.ending_arr
        else None
    )
    closed_lost_var_pct = (
        float((closed_lost - closed_lost_bud) / closed_lost_bud * 100)
        if closed_lost_bud
        else None
    )
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
            f"{coverage_vs_arr:.1f}x"
            if coverage_vs_arr is not None
            else (
                f"{float(m.pipeline_created / m.closed_won):.1f}x" if m.closed_won else "n/a"
            )
        ),
        "beginning_pipeline": _money_k(beginning_pipeline) if beginning_pipeline else "—",
        "beginning_pipeline_raw": float(beginning_pipeline or 0),
        "beginning_pipeline_budget": (
            _money_k(beginning_pipeline_bud) if beginning_pipeline_bud else "—"
        ),
        "ending_pipeline": _money_k(ending_pipeline) if ending_pipeline else "—",
        "ending_pipeline_raw": float(ending_pipeline),
        "ending_pipeline_budget": (
            _money_k(ending_pipeline_bud) if ending_pipeline_bud else "—"
        ),
        "ending_arr": _money_k(m.ending_arr) if m.ending_arr else "—",
        "ending_arr_raw": float(m.ending_arr or 0),
        "closed_won": _money_k(m.closed_won),
        "closed_won_raw": float(m.closed_won or 0),
        # Copilot-depth GTM evidence (pipeline waterfall)
        "closed_lost": _money_k(closed_lost) if closed_lost else "—",
        "closed_lost_raw": float(closed_lost),
        "closed_lost_budget": _money_k(closed_lost_bud) if closed_lost_bud else "—",
        "closed_lost_budget_raw": float(closed_lost_bud),
        "closed_lost_variance_pct": closed_lost_var_pct,
        "slipped_pipeline": _money_k(slipped) if slipped else "—",
        "slipped_pipeline_raw": float(slipped),
        "slipped_pipeline_budget": _money_k(slipped_bud) if slipped_bud else "—",
        "slipped_pipeline_budget_raw": float(slipped_bud),
        "pipeline_created": _money_k(m.pipeline_created) if m.pipeline_created else "—",
        "pipeline_created_raw": float(m.pipeline_created or 0),
        "pipeline_waterfall_chart": pipe_wf,
        "narrative_must_cover": [
            "closed_lost actual vs budget + variance",
            "slipped pipeline actual vs budget",
            "coverage vs ending ARR",
            "recommended board action (losses review or channel reallocation)",
        ],
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
    from app.services.reporting.export.board_platform_kt_seed import build_seed_key_takeaways

    # Authorship evidence only — never used for post-soft-strip slot refill.
    payload["key_takeaways_by_slide"] = build_seed_key_takeaways(payload)
    payload["key_takeaways_policy"] = (
        "Claude authors Key Takeaways. key_takeaways_by_slide is optional board-"
        "platform evidence to cite/draw from — not a template of slots to fill."
    )
    payload["payload_warnings"] = validate_deck_payload(payload)
    from app.services.commentary.attribution_verify import (
        build_attribution_package_from_deck_payload,
    )

    payload["attribution_package"] = build_attribution_package_from_deck_payload(payload)
    from app.services.reporting.export.board_platform_metrics import (
        build_evidence_package_from_deck_payload,
    )

    evidence_package = build_evidence_package_from_deck_payload(
        payload,
        org_id=str(getattr(bundle, "organization_id", "") or "") or None,
        loaded_at=None,
        is_final=None,
    )
    payload["evidence_package"] = {
        k: v
        for k, v in evidence_package.items()
        if k != "values_decimal"
    }
    payload["_sources"] = evidence_package.get("_sources") or {}
    return payload


def _ensure_prompt5_packages(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach evidence / attribution / _sources on the payload if missing; return evidence pkg."""
    from app.services.commentary.attribution_verify import (
        build_attribution_package_from_deck_payload,
    )
    from app.services.reporting.export.board_platform_metrics import (
        build_evidence_package_from_deck_payload,
        evidence_values_from_deck_payload,
    )

    pc = payload.get("period_context") or {}
    evidence_package = payload.get("evidence_package")
    if not isinstance(evidence_package, dict) or not evidence_package.get("values"):
        evidence_package = build_evidence_package_from_deck_payload(payload)
        payload["evidence_package"] = {
            k: v for k, v in evidence_package.items() if k != "values_decimal"
        }
        payload["_sources"] = evidence_package.get("_sources") or payload.get("_sources") or {}

    if "attribution_package" not in payload or not payload.get("attribution_package"):
        payload["attribution_package"] = build_attribution_package_from_deck_payload(payload)

    sources = payload.get("_sources") or evidence_package.get("_sources") or {}
    if not sources:
        from app.services.commentary.claim_verify import attach_sources_to_values

        sources = attach_sources_to_values(
            evidence_values_from_deck_payload(payload),
            period_label=str(pc.get("close_period") or "") or None,
        )
        payload["_sources"] = sources
    return evidence_package


def build_prompt5_package_preamble(
    payload: dict[str, Any],
    *,
    freeze_context_text: str | None = None,
    freeze_context_as_of: str | None = None,
    freeze_status: str | None = None,
    freeze_stale: bool = False,
) -> str:
    """Freeze + evidence + attribution + citation blocks for fresh and adapt Prompt 5."""
    from app.services.reporting.export.board_platform_metrics import (
        evidence_values_from_deck_payload,
    )
    from app.services.reporting.export.freeze_prompt import format_freeze_prompt_block
    from app.services.reporting.export.prompt5_narrative import (
        PROMPT5_BOARD_NARRATIVE_RULES,
        PROMPT5_CRAFT_CRITERIA,
    )

    pc = payload["period_context"]
    evidence_package = _ensure_prompt5_packages(payload)

    # Quality-first: never truncate freeze prose for Prompt 5 — slide numbers still from JSON.
    freeze_block = format_freeze_prompt_block(
        context_text=freeze_context_text,
        context_as_of=freeze_context_as_of,
        status=freeze_status,
        stale=freeze_stale,
        max_chars=None,
        number_guidance=(
            "Use this freeze for narrative tone, drivers, retention/pipeline context, "
            "and period framing — inject into Key Takeaways / risks / board actions. "
            "Copy slide numbers from DATA PAYLOAD / EVIDENCE PACKAGE verbatim — "
            "do not invent figures. Prefer package + freeze for rich board story."
        ),
    )

    evidence_for_prompt = {
        "close_period": evidence_package.get("close_period") or pc.get("close_period"),
        "tolerance_actuals": evidence_package.get("tolerance_actuals"),
        "series_kinds": evidence_package.get("series_kinds"),
        "policy": evidence_package.get("policy"),
        "values": evidence_package.get("values") or {
            k: str(v) for k, v in list(evidence_values_from_deck_payload(payload).items())[:400]
        },
    }
    evidence_block = (
        "EVIDENCE PACKAGE (P15 — prefer every customer-visible $ / % / Nx from these "
        "values within TOL_ACTUALS=$1.00. Actuals ≤ close_period; forecast after close; "
        "pipeline/opportunity dollars from pipeline-tagged keys. Use this package for "
        "rich board narrative in takeaways — do not invent outside it):\n"
        f"{json.dumps(evidence_for_prompt, separators=(',', ':'))}\n\n"
    )

    attribution = payload["attribution_package"]
    attribution_block = (
        "ATTRIBUTION PACKAGE (P15 — causal / driver language may only name "
        "allowed_drivers id/label/aliases; forward-looking watch-outs must ground in "
        "forecast/pipeline allowlist entries; empty allowlist means no causal claims; "
        "rich story from allowlisted drivers is required in takeaways — do not invent causes):\n"
        f"{json.dumps(attribution, separators=(',', ':'))}\n\n"
    )

    sources = payload.get("_sources") or evidence_package.get("_sources") or {}
    citation_preview = {
        k: {
            "source_type": (v or {}).get("source_type"),
            "table": (v or {}).get("table"),
            "column": (v or {}).get("column"),
            "formula_id": (v or {}).get("formula_id"),
            "path": (v or {}).get("path"),
            "series_kind": (v or {}).get("series_kind"),
            "period": (v or {}).get("period"),
        }
        for k, v in list(sources.items())[:250]
        if isinstance(v, dict)
    }
    citation_block = (
        "CITATION PACKAGE (P15 — cite _sources keys in Key Takeaways / narrative "
        "bullets where feasible, e.g. '$7.4M (income_statement.revenue)'. "
        "Do NOT put (source.key) parentheses inside KPI value cells or period_matrix "
        "/ table number cells — those copy payload numbers verbatim. Citation verify "
        "is warn-only on Prompt 5 (does not wipe cells):\n"
        f"{json.dumps(citation_preview, separators=(',', ':'))}\n\n"
    )

    craft_block = (
        "CRAFT CRITERIA (mandatory — generative authorship, not slot-fill):\n"
        f"{PROMPT5_CRAFT_CRITERIA}\n"
    )
    narrative_block = (
        "TAKEAWAY / COMMENTARY SHAPE (mandatory — see also system prompt):\n"
        f"{PROMPT5_BOARD_NARRATIVE_RULES}\n"
    )

    from app.services.reporting.export.board_platform_kt_seed import format_kt_seed_block
    from app.services.reporting.export.board_platform_ro_seed import (
        format_board_ro_seed_block,
        format_gtm_narrative_requirements_block,
    )

    ro_seed_block = format_board_ro_seed_block()
    gtm_seed_block = format_gtm_narrative_requirements_block()
    kt_seed_block = format_kt_seed_block(payload)

    return (
        freeze_block
        + evidence_block
        + attribution_block
        + citation_block
        + craft_block
        + ro_seed_block
        + gtm_seed_block
        + kt_seed_block
        + narrative_block
    )


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

    package_preamble = build_prompt5_package_preamble(
        payload,
        freeze_context_text=freeze_context_text,
        freeze_context_as_of=freeze_context_as_of,
        freeze_status=freeze_status,
        freeze_stale=freeze_stale,
    )
    evidence_package = payload.get("evidence_package") or {}
    close_label = pc.get("close_period_label") or pc.get("close_period") or ""
    close_period = pc.get("close_period") or evidence_package.get("close_period") or ""

    return (
        "Build the complete SMPL.ai board deck PptxGenJS script using the JSON data payload below.\n"
        "You AUTHOR the deck (generative authorship). Follow CRAFT CRITERIA and per-slide "
        "layout assignments in the system prompt — when you choose a waterfall or Key "
        "Takeaways, apply those construction rules. Evidence packages inform authorship; "
        "they are not blank slots to fill and not a post-process refill source.\n"
        "Slide 1: centered cover (cyan SMPL.ai, divider, no CONFIDENTIAL). "
        "Slide 3: waterfall_chart.shape_bars with addShape rectangles ONLY — no addChart on slide 3.\n"
        "Slides 1–10 main deck; slide 11 appendix CFS. Copy numbers from EVIDENCE PACKAGE / "
        "DATA PAYLOAD verbatim into KPI/table cells (numbers or '—' only). "
        "Key Takeaways / risks / board actions = 3–5 insight bullets each "
        "(PRIMARY DRIVER + VARIANCE, RETENTION/PIPELINE QUALITY, ROOT CAUSE, "
        "FORWARD READ labeled Actual vs Forecast vs Pipeline, RECOMMENDED BOARD ACTION) — "
        "cite _sources in narrative takeaways only, never inside KPI/table cells. "
        "Never emit blank or lone '—' takeaways.\n"
        "GTM/Pipeline Key Takeaways: follow GTM NARRATIVE REQUIREMENTS craft criteria "
        "(closed-lost, slipped, coverage, recommended board action) from package evidence.\n"
        "Strategic Assessment risk/opportunity cards: author from BOARD R&O EVIDENCE "
        "(driver + magnitude + action) — never thin stubs or empty '-'.\n"
        "When a freeze block is present above, inject its drivers into takeaway narrative. "
        "Use the full package for board-ready story — do not invent outside the packages; "
        "do not keep thin one-line delta stubs.\n\n"
        f"{package_preamble}"
        f"PERIOD CONTEXT\n"
        f"Close period: {close_label} ({close_period})\n"
        f"Actuals: periods ≤ {close_period or close_label}\n"
        f"Forecast / outlook: periods after {close_period or close_label}\n"
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


def _excerpt_for_prompt(text: str, *, limit: int = 24000) -> str:
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
        f"FAILED SCRIPT:\n{_excerpt_for_prompt(failed_script)}\n\n"
        f"DATA PAYLOAD (JSON):\n{_excerpt_for_prompt(payload_json, limit=60000)}\n\n"
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


def _verify_prompt5_script_or_raise(script: str, payload: dict[str, Any]) -> str:
    """P15 Prompt 5: soft-strip invented numbers + attribution; always export.

    Numeric / attribution: soft-strip failed PPTX string literals to ``—``
    (never multi-sentence don't-know essays). Citation: **warn-only** — board
    KPI/table cells come from DATA PAYLOAD / evidence and must not be wiped
    for missing ``(source.key)`` parentheses (that produced unreadable
    don't-know decks). Prefer export with stripped text over hard-block.
    """
    from app.services.commentary.attribution_verify import (
        apply_fail_closed_attribution_to_pptx_script,
        build_attribution_package_from_deck_payload,
    )
    from app.services.commentary.citation_verify import (
        verify_text_citations,
    )
    from app.services.commentary.claim_verify import (
        apply_fail_closed_claims_to_pptx_script,
        attach_sources_to_values,
        evidence_values_from_package,
        extract_js_string_literal_text,
    )
    from app.services.reporting.export.board_platform_metrics import (
        build_evidence_package_from_deck_payload,
        evidence_values_from_deck_payload,
    )

    # Rebuild full package at verify time (prompt preview omits values_decimal).
    evidence_package = build_evidence_package_from_deck_payload(payload)
    evidence = evidence_values_from_package(evidence_package) or evidence_values_from_deck_payload(
        payload
    )
    if not payload.get("_sources"):
        payload["_sources"] = evidence_package.get("_sources") or {}
    working, claim_result = apply_fail_closed_claims_to_pptx_script(script, evidence)
    if claim_result.ok:
        logger.info("P15 Prompt 5 claim-verify passed (%s checks)", len(claim_result.checks))
        working = script
    else:
        logger.warning(
            "P15 Prompt 5 claim-verify soft-stripped unmatched $/%%/Nx "
            "(export continues): %s",
            claim_result.summary(max_failures=8),
        )

    attribution = payload.get("attribution_package") or build_attribution_package_from_deck_payload(
        payload
    )
    rewritten, attr_result = apply_fail_closed_attribution_to_pptx_script(working, attribution)
    if attr_result.ok:
        if attr_result.checks:
            logger.info(
                "P15 Prompt 5 attribution-verify passed (%s checks, allowlist=%s)",
                len(attr_result.checks),
                attr_result.allowlist_size,
            )
    else:
        logger.warning(
            "P15 Prompt 5 attribution-verify stripped off-allowlist drivers "
            "(export continues): %s",
            attr_result.summary(),
        )
        working = rewritten

    sources = payload.get("_sources")
    if not isinstance(sources, dict) or not sources:
        period = str(
            (payload.get("period_context") or {}).get("close_period")
            or payload.get("close_period")
            or ""
        ) or None
        sources = attach_sources_to_values(evidence, period_label=period)
        payload["_sources"] = sources

    # Warn-only citation: do not rewrite script. Requiring (source.key) on every
    # KPI/table cell is unusable for board decks and previously nuked exports.
    cite_result = verify_text_citations(extract_js_string_literal_text(working), sources)
    if cite_result.ok:
        if cite_result.checks:
            logger.info(
                "P15 Prompt 5 citation-verify passed (%s checks, sources=%s)",
                len(cite_result.checks),
                cite_result.sources_size,
            )
    else:
        logger.warning(
            "P15 Prompt 5 citation-verify warn-only (uncited material numbers kept; "
            "export continues): %s",
            cite_result.summary(),
        )
    # Intentionally NO seed-refill of blank/"—" takeaways. Soft-strip may redact
    # unmatched $/% inside bullets; Claude must author complete takeaways up front.
    return working


def _try_adapt_from_reference(
    client: Any,
    *,
    period: str,
    payload_json: str,
    payload: dict[str, Any] | None = None,
    freeze_context_text: str | None = None,
    freeze_context_as_of: str | None = None,
    freeze_status: str | None = None,
    freeze_stale: bool = False,
) -> tuple[bytes, str] | None:
    """Adapt a known-good reference script to the current payload (layout-preserving)."""
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
    package_preamble = ""
    if payload is not None:
        package_preamble = build_prompt5_package_preamble(
            payload,
            freeze_context_text=freeze_context_text,
            freeze_context_as_of=freeze_context_as_of,
            freeze_status=freeze_status,
            freeze_stale=freeze_stale,
        )
    adapt_prompt = (
        f"Adapt the reference PptxGenJS script for close period {period}.\n"
        "Preserve layout/helpers; replace KPI/table/chart numbers from the payload "
        "(numbers or '—' only in cells).\n"
        "AUTHOR all Key Takeaways, risks/opportunities detail+action, board-action "
        "copy, and commentary strings for this period using BOARD NARRATIVE DEPTH + "
        "CRAFT CRITERIA — 3–5 insight bullets (PRIMARY DRIVER + VARIANCE, "
        "RETENTION/PIPELINE QUALITY, ROOT CAUSE, FORWARD READ with Actual vs Forecast "
        "vs Pipeline labels, RECOMMENDED BOARD ACTION). Do not keep thin reference "
        "one-liners. Evidence packages inform authorship — not slot-fill / seed-refill.\n"
        "GTM/Pipeline takeaways: follow GTM NARRATIVE REQUIREMENTS craft criteria "
        "(closed-lost, slipped, coverage, recommended action) from gtm_performance + "
        "EVIDENCE PACKAGE.\n"
        "Risks/Opportunities cards: author from BOARD R&O EVIDENCE (board risk matrix) "
        "— keep driver, magnitude, action; PPTX-succinct; never 'Close validation' "
        "fillers or empty '-'.\n"
        "Return complete raw JavaScript ending with pptx.writeFile({ fileName: 'OUTPUT.pptx' }).\n\n"
        f"{package_preamble}"
        "LAYOUT LOCKS (craft criteria — apply even when adapting):\n"
        "- Slide 3: Key Takeaways FULL WIDTH under the ARR waterfall (not cramped right of bridge).\n"
        "- Slide 5: Use cash_liquidity.ytd_cash_summary (not a thin liquidity-headroom stub); "
        "KT box must end above footer (y+h ≤ 6.85).\n"
        "- Slide 6: MARKETING FUNNEL section label must not overlap the period title; "
        "author complete KT bullets (never blank/—).\n"
        "- Slide 7: Pipeline waterfall from gtm_performance.pipeline_waterfall_chart.shape_bars "
        "(Begin AND End totals, additive, real beginning value). Category labels on x-axis "
        "(bar.category_y). Key Takeaways FULL WIDTH below the waterfall.\n"
        "- Slide 11 CFS: copy appendix.ytd_cash_flow_statement Actual/Budget/Variance — "
        "Actual for periods ≤ close only; never Forecast.\n"
        "- Every Key Takeaways panel you include: 3–5 authored bullets (never lone '—');\n\n"
        f"REFERENCE SCRIPT:\n{_excerpt_for_prompt(ref_script, limit=40000)}\n\n"
        f"DATA PAYLOAD (JSON):\n{_excerpt_for_prompt(payload_json, limit=60000)}\n"
    )
    script_text = _generate_deck_script_text(
        client, adapt_prompt, system_prompt=PROMPT5_ADAPT_SYSTEM
    )
    if not _script_is_complete(script_text):
        raise RuntimeError(
            f"Adapt fallback incomplete ({len(script_text)} chars, no pptx.writeFile)"
        )
    if payload is not None:
        script_text = _verify_prompt5_script_or_raise(script_text, payload)
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
    # Freeze + evidence packages are injected so takeaways rewrite at regenerate/Copilot depth.
    try:
        adapted = _try_adapt_from_reference(
            client,
            period=bundle.as_of_period,
            payload_json=payload_json,
            payload=payload,
            freeze_context_text=freeze_context_text,
            freeze_context_as_of=freeze_context_as_of,
            freeze_status=freeze_status,
            freeze_stale=freeze_stale,
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

            script_text = _verify_prompt5_script_or_raise(script_text, payload)
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
