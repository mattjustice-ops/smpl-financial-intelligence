"""Tests for board deck Claude prompt payloads (Prompt 1)."""

from decimal import Decimal

from app.services.dashboard.schemas import ExecutiveFlowResponse
from app.services.reporting.export.board_api_prompts import (
    format_key_takeaway_bullets,
    parse_board_deck_bullets_response,
    validate_and_trim_bullets,
)
from app.services.reporting.export.board_slide_commentary_payload import (
    BOARD_DECK_SLIDE_KEYS,
    build_single_slide_payload,
    fmt_deck_money,
    fmt_deck_var,
    interactive_slide_prompt_limits,
    slide_prompt_limits,
)
from app.services.reporting.export.schemas import ReportingBundle, ExportValidationSummary


def _minimal_bundle(**overrides) -> ReportingBundle:
    base = dict(
        organization_id="org-1",
        organization_name="SMPL.ai",
        scenario="Combined",
        start_period="2026-01",
        end_period="2026-12",
        as_of_period="2026-06",
        period_label="June 2026",
        currency="USD",
        executive_flow=ExecutiveFlowResponse(
            organization_id="org-1",
            scenario="Combined",
            start_period="2026-01",
            end_period="2026-12",
            as_of_period="2026-06",
            waterfalls={},
        ),
        validation=ExportValidationSummary(status="pass", failed_count=0, warning_count=0, passed_count=0),
    )
    base.update(overrides)
    return ReportingBundle(**base)


def test_fmt_deck_money_millions() -> None:
    assert fmt_deck_money(Decimal("86100000")) == "$86.10M"
    assert fmt_deck_money(Decimal("-1300000")) == "-$1.30M"


def test_fmt_deck_var_sign() -> None:
    assert fmt_deck_var(Decimal("86100000"), Decimal("84890000")) == "+$1.21M"


def test_build_executive_slide_payload_shape() -> None:
    bundle = _minimal_bundle()
    payload = build_single_slide_payload(bundle, "executive_summary")
    assert payload["close_period"] == "2026-06"
    assert payload["close_period_label"] == "June"
    slide = payload["slide"]
    assert slide["slide_number"] == 2
    assert slide["slide_title"] == "Executive Summary"
    assert "revenue_actual" in slide["metrics"]
    assert slide["max_bullets"] == 5


def test_board_deck_slide_keys_match_platform_aliases() -> None:
    from app.api.board_platform_routes import BOARD_SLIDE_KEY_ALIASES

    # headcount uses the legacy paragraph path (not Prompt-1 bullet specs).
    deck_aliases = {v for v in BOARD_SLIDE_KEY_ALIASES.values() if v != "headcount"}
    assert deck_aliases <= BOARD_DECK_SLIDE_KEYS


def test_parse_bullets_response_shapes() -> None:
    assert parse_board_deck_bullets_response({"bullets": ["• A", "• B"]}, "executive_summary") == [
        "• A",
        "• B",
    ]
    assert parse_board_deck_bullets_response({"2": ["• X"]}, "executive_summary") == ["• X"]


def test_validate_and_trim_bullets_enforces_limits() -> None:
    long = "• " + " ".join(["word"] * 30)
    out = validate_and_trim_bullets(
        [long, "• second", "• third", "• fourth", "• fifth", "• sixth"],
        max_bullets=4,
        max_words_per_bullet=25,
    )
    assert len(out) == 4
    assert _word_count(out[0]) <= 25


def _word_count(text: str) -> int:
    return len(text.lstrip("•").split())


_LEGACY_TINY_WORD_CAPS = {6, 15, 16, 18, 20, 22, 24, 28}
_LEGACY_TINY_CHAR_CAPS = {38, 85, 90, 100, 115, 135, 160, 165, 200}


def test_gaap_revenue_limits_allow_full_board_sentence() -> None:
    """Regression: old 85-char cap clipped Revenue Narrative mid-sentence with …"""
    _, max_words, max_chars = interactive_slide_prompt_limits("gaap_revenue")
    assert max_words >= 60
    assert max_chars >= 480

    bullet = (
        "• Revenue $7.35M vs $7.72M budget (−$370K, −4.8%); "
        "EBITDA beat at $661.5K vs $480.0K budget as opex timing normalized."
    )
    assert len(bullet) > 85  # would have been truncated under the old cap
    out = validate_and_trim_bullets(
        [bullet],
        max_bullets=5,
        max_words_per_bullet=max_words,
        max_chars_per_bullet=max_chars,
    )
    assert out == [bullet]
    assert "…" not in out[0]


def test_all_board_deck_interactive_limits_floor_full_sentences() -> None:
    """Every narrative slide key must use the interactive floor — not legacy 15/85 stubs."""
    sample_bullet = (
        "• Net new ARR $2.655M vs $2.185M budget (+$0.47M); churn favorable at $0.115M "
        "vs $0.50M as Commit renewals closed at 95% and H2 forecast tracks above plan."
    )
    assert len(sample_bullet) > 85
    assert _word_count(sample_bullet) > 15

    for slide_key in sorted(BOARD_DECK_SLIDE_KEYS):
        max_bullets, max_words, max_chars = interactive_slide_prompt_limits(slide_key)
        deck_bullets, deck_words, deck_chars = slide_prompt_limits(slide_key)

        assert max_bullets == deck_bullets
        assert max_words >= 60, f"{slide_key}: interactive words {max_words}"
        assert max_chars >= 480, f"{slide_key}: interactive chars {max_chars}"
        assert deck_words not in _LEGACY_TINY_WORD_CAPS, f"{slide_key}: deck words still tiny ({deck_words})"
        assert deck_chars not in _LEGACY_TINY_CHAR_CAPS, f"{slide_key}: deck chars still tiny ({deck_chars})"
        assert deck_words >= 60, f"{slide_key}: deck words {deck_words}"
        assert deck_chars >= 480, f"{slide_key}: deck chars {deck_chars}"

        out = validate_and_trim_bullets(
            [sample_bullet],
            max_bullets=max_bullets,
            max_words_per_bullet=max_words,
            max_chars_per_bullet=max_chars,
        )
        assert out == [sample_bullet], f"{slide_key}: unexpectedly trimmed board sentence"
        assert "…" not in out[0]


def test_validate_and_trim_prefers_sentence_boundary() -> None:
    bullet = (
        "• Revenue beat budget by $60K. Gross margin expanded 220bps on hosting efficiency "
        "and Q3 opex is expected to normalize toward plan."
    )
    out = validate_and_trim_bullets(
        [bullet],
        max_bullets=1,
        max_words_per_bullet=80,
        max_chars_per_bullet=70,
    )
    assert out[0] == "• Revenue beat budget by $60K."
    assert "…" not in out[0]


def test_interactive_limits_floor_above_deck_specs() -> None:
    for slide_key in ("gaap_revenue", "arr_waterfall", "gtm_performance", "cash_forecast", "risks_opportunities"):
        deck = slide_prompt_limits(slide_key)
        interactive = interactive_slide_prompt_limits(slide_key)
        assert interactive[0] == deck[0]
        assert interactive[1] >= deck[1]
        assert interactive[2] >= deck[2]
        assert interactive[1] >= 60
        assert interactive[2] >= 480


def test_format_key_takeaway_bullets() -> None:
    text = format_key_takeaway_bullets(["Revenue beat budget", "• ARR up"])
    assert text.startswith("• Revenue")
    assert "\n• ARR" in text
