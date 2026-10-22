"""Funding-round terms: debt and equity land on different statements."""

from app.services.reporting.financing_rounds import effects, normalize_round


CLOSE = "2026-06"
PERIODS = [f"2026-{m:02d}" for m in range(1, 13)]


def _debt(**extra):
    base = {
        "month": "2026-08",
        "instrument": "debt",
        "gross": 20_000_000,
        "fees": 500_000,
        "ratePct": 12,
        "interestStart": "2026-08",
        "warrantPct": 0,
    }
    base.update(extra)
    return base


def test_equity_round_is_cash_and_paid_in_capital_with_no_interest():
    row = normalize_round(
        {"month": "2026-08", "instrument": "equity", "gross": 20_000_000, "fees": 500_000, "security": "Series C"},
        CLOSE,
    )
    assert row.net == 19_500_000
    assert row.equity_proceeds == 19_500_000
    assert row.debt_proceeds == 0
    august = effects([{"month": "2026-08", "instrument": "equity", "gross": 20_000_000, "fees": 500_000}], PERIODS, CLOSE)
    assert august["2026-08"].financing == 19_500_000
    assert august["2026-08"].equity_delta == 19_500_000
    assert august["2026-08"].debt_delta == 0
    assert august["2026-08"].interest == 0
    assert august["2026-06"].financing == 0
    assert august["2026-09"].interest == 0


def test_debt_round_draws_debt_and_starts_interest_in_the_wire_month():
    august = effects([_debt()], PERIODS, CLOSE)["2026-08"]
    september = effects([_debt()], PERIODS, CLOSE)["2026-09"]
    assert august.financing == 19_500_000
    assert august.debt_delta == 19_500_000
    assert august.equity_delta == 0
    assert august.interest == 195_000
    assert september.financing == 0
    assert september.debt_delta == 0
    assert september.interest == 195_000
    assert september.debt_balance == 19_500_000


def test_warrant_coverage_splits_the_wire_between_debt_and_equity():
    effect = effects([_debt(warrantPct=10)], PERIODS, CLOSE)["2026-08"]
    assert effect.debt_delta == 17_550_000
    assert effect.equity_delta == 1_950_000
    assert effect.financing == 19_500_000
    assert effect.interest == 175_500


def test_principal_repaid_this_year_reduces_debt_and_later_interest():
    rounds = [_debt(principalDue=1_000_000, principalMonth="2026-11")]
    by_month = effects(rounds, PERIODS, CLOSE)
    assert by_month["2026-11"].financing == -1_000_000
    assert by_month["2026-11"].debt_delta == -1_000_000
    assert by_month["2026-11"].debt_balance == 18_500_000
    assert by_month["2026-11"].interest == 195_000
    assert by_month["2026-12"].interest == 185_000


def test_a_round_in_a_closed_month_is_rejected():
    try:
        normalize_round(_debt(month="2026-06"), CLOSE)
    except ValueError as exc:
        assert "after the close" in str(exc)
    else:
        raise AssertionError("closed month was accepted")
