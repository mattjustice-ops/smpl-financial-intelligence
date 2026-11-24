"""Customer-grain compile, billing-derived feeds, and insight pack shapes."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.mrr.engine import (
    BucketPolicy,
    MovementType,
    customer_age,
)
from app.services.warehouse.close_insight_packs import (
    _cohort_curves,
    _customer_behavior,
    _retention,
    _revenue_type_elements,
    build_and_store_insight_packs,
    money,
)
from app.services.warehouse.compile_customer_grain import _arr_by_customer, money as grain_money
from app.services.warehouse.compile_revenue_feeds import DEFAULT_RECURRING_RATE, _dec
from app.services.warehouse.event_labels import EventLabels


def test_young_churn_is_no_start_and_winback_restarts_latest_nb() -> None:
    policy = BucketPolicy(restart_window_months=6, new_business_months=12)
    period = date(2026, 7, 1)
    # First MRR in Feb 2026 → still in New Business period in July
    young = customer_age(
        period,
        MovementType.CHURN,
        [date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1), date(2026, 5, 1), date(2026, 6, 1)],
        policy,
    )
    assert young is not None
    assert young.line == "no_start"
    assert young.bucket == "New Business"

    # Gone more than 6 months → winback; age clock restarts at return month
    winback = customer_age(
        period,
        MovementType.REACTIVATION,
        [date(2024, 1, 1), date(2024, 6, 1)],
        policy,
    )
    assert winback is not None
    assert winback.line == "winback"
    assert winback.first_mrr_period == period
    assert winback.age_months == 0


def test_subscription_book_opens_and_ends_by_customer() -> None:
    begin, end = _arr_by_customer(
        [
            {
                "customer_id": "A",
                "start_date": "2026-01-01",
                "end_date": "2026-07-15",
                "current_arr": "1200",
            },
            {
                "customer_id": "B",
                "start_date": "2026-07-01",
                "end_date": "2026-12-31",
                "current_arr": "500",
            },
            {
                "customer_id": "C",
                "start_date": "2025-01-01",
                "end_date": "2026-06-30",
                "current_arr": "900",
            },
        ],
        "2026-07",
    )
    assert begin["A"] == Decimal("1200")
    assert begin["B"] == Decimal("500")  # starts on the 1st — opens the month
    assert end["B"] == Decimal("500")
    assert "C" not in begin and "C" not in end


def test_billing_bundle_split_uses_default_recurring_rate() -> None:
    bundle = Decimal("1100.00")
    rate = DEFAULT_RECURRING_RATE
    sub = (bundle / (Decimal("1") + rate)).quantize(Decimal("0.01"))
    rsvc = bundle - sub
    assert sub == Decimal("1000.00")
    assert rsvc == Decimal("100.00")
    assert _dec("42") == Decimal("42")


def test_insight_behavior_pack_shape_with_no_history() -> None:
    class _Empty:
        def execute(self, *_args, **_kwargs):
            class _R:
                def mappings(self):
                    return []

                def first(self):
                    return None

                def all(self):
                    return []

                def scalar(self):
                    return None

            return _R()

    # _customer_behavior only needs history rows; table_exists will fail open via try in callers.
    # Call the mix builder with a stub that returns no rows through the SQL path by patching.
    from unittest.mock import patch

    with patch("app.services.warehouse.close_insight_packs.table_exists", return_value=False):
        with patch("app.services.warehouse.close_insight_packs._history_rows", return_value=[]):
            pack = _customer_behavior(_Empty(), "org", "2026-07")
    assert "mix" in pack
    assert pack["upgrade_subtype_mix"] == {}
    assert pack["uom_intensity"] == {}
    assert pack["top_movers"] == []


def test_cohort_curves_empty_without_history(monkeypatch) -> None:
    class _DB:
        def execute(self, *_args, **_kwargs):
            raise AssertionError("should not query when table missing")

    monkeypatch.setattr(
        "app.services.warehouse.close_insight_packs.table_exists",
        lambda *_a, **_k: False,
    )
    assert _cohort_curves(_DB(), "org", "2026-07") == {}
    pack = _retention(_DB(), "org", "2026-07")
    assert pack["cohort_curves"] == {}


def test_cohort_curves_from_stubbed_vintages(monkeypatch) -> None:
    class _DB:
        def execute(self, *_args, **_kwargs):
            class _R:
                def all(self):
                    # customer_id, vintage, ending_arr (post group-by)
                    return [
                        ("c1", "2025-01", Decimal("1200")),
                        ("c2", "2025-01", Decimal("800")),
                        ("c3", "2024-06", Decimal("5000")),
                    ]

                def mappings(self):
                    return []

                def first(self):
                    return None

            return _R()

    monkeypatch.setattr(
        "app.services.warehouse.close_insight_packs.table_exists",
        lambda *_a, **_k: True,
    )
    monkeypatch.setattr(
        "app.services.warehouse.close_insight_packs._table_columns",
        lambda *_a, **_k: {"ending_arr", "first_mrr_period", "customer_id", "period"},
    )
    monkeypatch.setattr(
        "app.services.warehouse.close_insight_packs._waterfall_row",
        lambda *_a, **_k: None,
    )
    curves = _cohort_curves(_DB(), "org", "2026-07")
    assert curves["as_of_period"] == "2026-07"
    assert curves["vintages"] == [
        {"vintage": "2024-06", "logos": 1, "ending_arr": 5000.0},
        {"vintage": "2025-01", "logos": 2, "ending_arr": 2000.0},
    ]
    pack = _retention(_DB(), "org", "2026-07")
    assert pack["cohort_curves"] == curves


def test_upgrade_and_uom_keys_remain_empty(monkeypatch) -> None:
    class _DB:
        def execute(self, *_args, **_kwargs):
            class _R:
                def mappings(self):
                    return []

                def first(self):
                    return None

                def all(self):
                    return []

                def scalar(self):
                    return None

            return _R()

    monkeypatch.setattr(
        "app.services.warehouse.close_insight_packs.table_exists",
        lambda *_a, **_k: False,
    )
    monkeypatch.setattr(
        "app.services.warehouse.close_insight_packs._history_rows",
        lambda *_a, **_k: [],
    )
    behavior = _customer_behavior(_DB(), "org", "2026-07")
    assert behavior["upgrade_subtype_mix"] == {}
    assert behavior["uom_intensity"] == {}


def test_revenue_type_elements_honest_split(monkeypatch) -> None:
    class _DB:
        def execute(self, *_args, **_kwargs):
            class _R:
                def all(self):
                    return [
                        ("Subscription", Decimal("900"), 2),
                        ("Implementation & Onboarding", Decimal("100"), 1),
                    ]

            return _R()

    monkeypatch.setattr(
        "app.services.warehouse.close_insight_packs.table_exists",
        lambda *_a, **_k: True,
    )
    monkeypatch.setattr(
        "app.services.warehouse.close_insight_packs._table_columns",
        lambda *_a, **_k: {"recognized_revenue", "revenue_type"},
    )
    elements = _revenue_type_elements(_DB(), "org", "2026-07")
    assert elements["by_revenue_type"]["Subscription"] == 900.0
    assert "not ASC 606 SSP" in elements["note"]


def test_build_insight_packs_returns_all_six_keys(monkeypatch) -> None:
    class _DB:
        def execute(self, *_args, **_kwargs):
            class _R:
                def mappings(self):
                    return []

                def first(self):
                    return None

                def all(self):
                    return []

                def scalar(self):
                    return 1

            return _R()

    monkeypatch.setattr(
        "app.services.warehouse.close_insight_packs.table_exists",
        lambda *_a, **_k: False,
    )
    packs = build_and_store_insight_packs(_DB(), __import__("uuid").uuid4(), "2026-07")
    for key in (
        "customer_behavior",
        "arr_vs_revenue_deferred",
        "billings_cash",
        "forecast_miss",
        "gtm_capacity",
        "retention",
    ):
        assert key in packs
    assert packs["meta"]["period"] == "2026-07"
    assert packs["retention"]["cohort_curves"] == {}
    assert packs["customer_behavior"]["upgrade_subtype_mix"] == {}
    assert packs["customer_behavior"]["uom_intensity"] == {}
    assert packs["arr_vs_revenue_deferred"]["asc606_elements"] == {}


def test_event_labels_map_opportunity_words() -> None:
    labels = EventLabels()
    assert labels.movement("New Business") == "new"
    assert labels.movement("Expansion") == "expansion"
    assert labels.movement("Churn") == "churn"


def test_money_helpers_round_half_up() -> None:
    assert grain_money(Decimal("1.005")) == "1.01"
    assert money(Decimal("10")) == 10.0
