"""Prompt 2: Claude generates MD&A variance commentary JSON; inject into Excel template."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.core.config import _BACKEND_ROOT
from app.services.commentary.llm_factory import build_commentary_llm_client
from app.services.reporting.export.mda_package_injection import (
    build_mda_package_xlsx_bytes,
    resolve_mda_package_template,
    trim_commentary_response,
)
from app.services.reporting.export.mda_package_payload import build_mda_package_payload
from app.services.reporting.export.prompt2_system import PROMPT2_SYSTEM
from app.services.reporting.export.prompt5_deck import _marketing_by_channel
from app.services.reporting.export.schemas import ReportingBundle

logger = logging.getLogger(__name__)

ARCHIVE_DIR = _BACKEND_ROOT / "tmp" / "mda-package-archive"
MDA_COMMENTARY_MAX_TOKENS = 24000


def build_prompt2_user_message(
    bundle: ReportingBundle,
    *,
    ts_data: dict[str, Any] | None = None,
    cash_bridge_data: dict[str, Any] | None = None,
    freeze_context_text: str | None = None,
    freeze_context_as_of: str | None = None,
    freeze_status: str | None = None,
    freeze_stale: bool = False,
) -> str:
    from app.services.reporting.export.freeze_prompt import format_freeze_prompt_block

    payload = build_mda_package_payload(
        bundle, ts_data=ts_data, cash_bridge_data=cash_bridge_data
    )
    # Quality-first: never truncate freeze prose for Prompt 2 — numbers still come from JSON.
    freeze_max = None
    freeze_block = format_freeze_prompt_block(
        context_text=freeze_context_text,
        context_as_of=freeze_context_as_of,
        status=freeze_status,
        stale=freeze_stale,
        max_chars=freeze_max,
        number_guidance=(
            "Use this freeze for narrative tone, operational drivers, and period framing. "
            "Dollar / percent figures must still come from DATA PAYLOAD JSON only — never invent."
        ),
    )
    return (
        "Generate the complete MD&A variance commentary package for the close period below.\n"
        "Return a single JSON object keyed by sheet name. Each row_id must include the three "
        "commentary columns (or description/recommended_action for risks_and_opportunities).\n"
        "Be comprehensive: cover each payload row with specific, board-ready commentary — "
        "do not shorten into generic summaries.\n"
        "Use only metrics present in the payload — never invent dollars or percentages.\n"
        "Causal / attribution language may only name drivers in "
        "attribution_package.allowed_drivers; if that list is empty, restate metrics "
        "without inventing causes.\n\n"
        f"{freeze_block}"
        f"DATA PAYLOAD (JSON):\n{json.dumps(payload, separators=(',', ':'))}"
    )


def _archive_artifacts(period: str, payload: dict[str, Any], commentary: dict[str, Any], xlsx: bytes) -> None:
    try:
        dest = ARCHIVE_DIR / period
        dest.mkdir(parents=True, exist_ok=True)
        (dest / f"mda_package_payload_{period}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        (dest / f"mda_package_commentary_{period}.json").write_text(
            json.dumps(commentary, indent=2), encoding="utf-8"
        )
        (dest / f"SMPL_MDA_Package_{period}.xlsx").write_bytes(xlsx)
    except OSError as exc:
        logger.warning("Could not archive MDA package artifacts: %s", exc)


def build_claude_mda_package_xlsx_bytes(
    bundle: ReportingBundle,
    *,
    ts_data: dict[str, Any] | None = None,
    cash_bridge_data: dict[str, Any] | None = None,
    max_retries: int = 1,
    skip_claude: bool = False,
    freeze_context_text: str | None = None,
    freeze_context_as_of: str | None = None,
    freeze_status: str | None = None,
    freeze_stale: bool = False,
) -> tuple[bytes, str]:
    """Prompt 2: Claude commentary JSON + SMPL_MDA_Package template injection."""
    template = resolve_mda_package_template()
    if template is None:
        raise FileNotFoundError(
            "SMPL_MDA_Package template not found. Set MDA_PACKAGE_TEMPLATE or place "
            "SMPL_MDA_Package_June2026.xlsx in frontend/public/board/exports/."
        )

    payload = build_mda_package_payload(
        bundle, ts_data=ts_data, cash_bridge_data=cash_bridge_data
    )
    deck = payload.get("deck_payload") or {}
    channels = _marketing_by_channel(bundle, bundle.as_of_period)
    display = payload.get("variance_commentary_display")

    if skip_claude:
        commentary: dict[str, Any] = {}
        xlsx_bytes = build_mda_package_xlsx_bytes(
            template_path=template,
            commentary=commentary,
            close_period=bundle.as_of_period,
            display=display,
            bundle=bundle,
            deck=deck,
            ts_data=ts_data,
            cash_bridge_data=cash_bridge_data,
            channels=channels,
        )
        _archive_artifacts(bundle.as_of_period, payload, commentary, xlsx_bytes)
        return xlsx_bytes, "metrics_only"

    client = build_commentary_llm_client(purpose="export")
    user_message = build_prompt2_user_message(
        bundle,
        ts_data=ts_data,
        cash_bridge_data=cash_bridge_data,
        freeze_context_text=freeze_context_text,
        freeze_context_as_of=freeze_context_as_of,
        freeze_status=freeze_status,
        freeze_stale=freeze_stale,
    )

    last_error = ""
    commentary = {}
    for attempt in range(max_retries + 1):
        try:
            if hasattr(client, "generate"):
                raw = client.generate(  # type: ignore[attr-defined]
                    system_prompt=PROMPT2_SYSTEM,
                    user_prompt=user_message,
                    max_tokens=MDA_COMMENTARY_MAX_TOKENS,
                )
            else:
                raise RuntimeError("LLM client does not support JSON generation.")
            commentary = trim_commentary_response(raw)
            if not commentary.get("variance_commentary"):
                raise RuntimeError("Claude response missing variance_commentary sheet.")

            # P15 hard block: variance display must tie to period_matrix before emit.
            from app.services.reporting.export.board_platform_metrics import (
                evidence_values_from_mda_payload,
                verify_variance_commentary_tieout,
            )
            from app.services.commentary.attribution_verify import (
                build_attribution_package_from_mda_payload,
                raise_if_attribution_fully_unverifiable,
                verify_nested_commentary_attribution,
            )
            from app.services.commentary.claim_verify import (
                CommentaryIntegrityError,
                verify_nested_commentary_strings,
            )

            display = payload.get("variance_commentary_display") or {}
            matrix = (payload.get("deck_payload") or {}).get("period_matrix") or {}
            verify_variance_commentary_tieout(display, matrix, fail_closed=True)

            evidence_values = evidence_values_from_mda_payload(payload)
            # Prefer serialized evidence_package.values when present (same dict shown to LLM).
            ep = payload.get("evidence_package") or {}
            if ep.get("values"):
                from app.services.commentary.claim_verify import _to_decimal

                merged = dict(evidence_values)
                for k, v in (ep.get("values") or {}).items():
                    num = _to_decimal(v)
                    if num is not None:
                        merged[str(k)] = num
                evidence_values = merged

            commentary, claim_result = verify_nested_commentary_strings(
                commentary, evidence_values
            )
            if not claim_result.ok:
                logger.warning(
                    "P15 MD&A claim-verify stripped/omitted unverifiable claims: %s",
                    claim_result.summary(),
                )
            # If every variance cell was wiped to don't-know after inventing numbers, block emit.
            vc = commentary.get("variance_commentary") or {}
            dont_know_marker = "could not be verified against engine evidence"
            vc_texts = []
            for row in vc.values():
                if isinstance(row, dict):
                    vc_texts.extend(str(v) for v in row.values() if isinstance(v, str))
            if vc_texts and all(dont_know_marker in t for t in vc_texts):
                raise CommentaryIntegrityError(
                    "P15 fail-closed: MD&A variance commentary had no verifiable numeric claims; "
                    "blocking package emit. " + claim_result.summary(),
                    result=claim_result,
                )

            attribution = payload.get("attribution_package") or build_attribution_package_from_mda_payload(
                payload
            )
            commentary, attr_result = verify_nested_commentary_attribution(
                commentary, attribution
            )
            if not attr_result.ok:
                logger.warning(
                    "P15 MD&A attribution-verify stripped/omitted unverifiable drivers: %s",
                    attr_result.summary(),
                )
            raise_if_attribution_fully_unverifiable(commentary, attr_result)

            payload_warnings = payload.get("payload_warnings") or []
            if payload_warnings:
                logger.warning("MDA package payload warnings: %s", "; ".join(payload_warnings))
            xlsx_bytes = build_mda_package_xlsx_bytes(
                template_path=template,
                commentary=commentary,
                close_period=bundle.as_of_period,
                display=display,
                bundle=bundle,
                deck=deck,
                ts_data=ts_data,
                cash_bridge_data=cash_bridge_data,
                channels=channels,
            )
            _archive_artifacts(bundle.as_of_period, payload, commentary, xlsx_bytes)
            return xlsx_bytes, "claude_prompt2"
        except Exception as exc:
            last_error = str(exc)
            logger.warning("Prompt 2 MDA package attempt %s failed: %s", attempt + 1, last_error)

    raise RuntimeError(
        f"Claude MDA package generation failed after retries. Last error: {last_error or 'unknown'}"
    )
