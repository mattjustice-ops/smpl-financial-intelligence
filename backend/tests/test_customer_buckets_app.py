"""New Business / Customer Success buckets: MRR engine, KPIs, dashboard waterfall, board and MD&A."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.demo_finance import Customer, MrrWaterfall, Subscription
from app.models.organization import Organization
from app.services.kpis.repository import load_customer_success_mrr
from app.services.mrr import service as mrr_service
from app.services.mrr.repository import customer_active_months
from app.services.dashboard.schemas import ExecutiveFlowResponse, WaterfallAttributionRow, WaterfallSummaryRow
from app.services.dashboard.waterfall_attribution_service import _bucket_metrics, _movement_metrics
from app.services.dashboard.waterfall_service import _summarize, _validate
from app.services.kpis.engine import KpiInputs, calculate_kpis
from app.services.mrr.bucket_columns import (
    CLOSED_WON_NEW_BUSINESS,
    CUSTOMER_SUCCESS_BEGINNING,
    has_bucket_columns,
)
from app.services.mrr.engine import (
    CUSTOMER_SUCCESS,
    NEW_BUSINESS,
    BucketPolicy,
    MovementType,
    compute_waterfall,
    customer_age,
    first_mrr_period,
    summarize_company,
)
from app.services.mrr.metrics import ALL_CUSTOMERS, CUSTOMER_SUCCESS_BASE, compute_period_metrics
from app.services.reporting.export.board_chart_service import _grr, _nrr, retention_base_label
from app.services.reporting.export.board_platform_metrics import build_arr_waterfall_chart
from app.services.reporting.export.mda_pptx import _slide_arr_waterfall
from app.services.reporting.export.schemas import ExportValidationSummary, ReportingBundle
from app.services.reporting.export.validation_precheck import _cross_source_checks
from app.services.reporting.three_statement_payload import _aggregate_mrr_by_period, _normalize_mrr_metrics

PERIOD = date(2026, 6, 1)
POLICY = BucketPolicy()


def _d(v) -> Decimal:
    return Decimal(str(v))


def _months(start: date, end: date) -> list[date]:
    out, cur = [], start
    while cur <= end:
        out.append(cur)
        cur = date(cur.year + cur.month // 12, cur.month % 12 + 1, 1)
    return out


# ---------------------------------------------------------------------------
# Age of first MRR
# ---------------------------------------------------------------------------


def test_first_mrr_period_restarts_only_after_more_than_the_window() -> None:
    six_away = [date(2025, 1, 1), date(2025, 8, 1)]
    seven_away = [date(2025, 1, 1), date(2025, 9, 1)]
    assert first_mrr_period(six_away, 6) == date(2025, 1, 1)
    assert first_mrr_period(seven_away, 6) == date(2025, 9, 1)
    assert first_mrr_period(seven_away, None) == date(2025, 1, 1)


def test_new_customer_without_history_is_a_new_logo() -> None:
    age = customer_age(PERIOD, MovementType.NEW, [], POLICY)
    assert (age.line, age.bucket, age.age_months, age.first_mrr_period) == ("new_logo", NEW_BUSINESS, 0, PERIOD)


def test_return_after_more_than_six_months_is_a_winback_and_restarts_the_age() -> None:
    history = _months(date(2023, 1, 1), date(2025, 10, 1))  # gone Nov 2025, back Jun 2026 = 7 months away
    age = customer_age(PERIOD, MovementType.REACTIVATION, history, POLICY)
    assert (age.line, age.bucket, age.age_months, age.first_mrr_period) == ("winback", NEW_BUSINESS, 0, PERIOD)


def test_return_within_six_months_after_the_first_year_is_reactivation() -> None:
    history = _months(date(2024, 1, 1), date(2025, 12, 1))  # gone Jan 2026, back Jun 2026 = 5 months away
    age = customer_age(PERIOD, MovementType.REACTIVATION, history, POLICY)
    assert (age.line, age.bucket, age.first_mrr_period) == ("reactivation", CUSTOMER_SUCCESS, date(2024, 1, 1))


def test_return_within_six_months_during_the_first_year_is_a_winback() -> None:
    history = _months(date(2025, 6, 1), date(2025, 12, 1))  # left at 7 months old
    age = customer_age(PERIOD, MovementType.REACTIVATION, history, POLICY)
    assert (age.line, age.bucket) == ("winback", NEW_BUSINESS)
    assert age.first_mrr_period == date(2025, 6, 1)


@pytest.mark.parametrize(
    ("movement", "start", "line", "bucket"),
    [
        (MovementType.CHURN, date(2026, 1, 1), "no_start", NEW_BUSINESS),
        (MovementType.CHURN, date(2025, 1, 1), "churn", CUSTOMER_SUCCESS),
        (MovementType.EXPANSION, date(2026, 1, 1), "first_year_expansion", NEW_BUSINESS),
        (MovementType.EXPANSION, date(2025, 6, 1), "expansion", CUSTOMER_SUCCESS),
        (MovementType.CONTRACTION, date(2025, 7, 1), "first_year_contraction", NEW_BUSINESS),
        (MovementType.CONTRACTION, date(2024, 6, 1), "contraction", CUSTOMER_SUCCESS),
        (MovementType.UNCHANGED, date(2024, 6, 1), "", CUSTOMER_SUCCESS),
        (MovementType.UNCHANGED, date(2026, 2, 1), "", NEW_BUSINESS),
    ],
)
def test_existing_customer_line_follows_age(movement, start, line, bucket) -> None:
    age = customer_age(PERIOD, movement, _months(start, date(2026, 5, 1)), POLICY)
    assert (age.line, age.bucket) == (line, bucket)


def test_twelve_months_old_is_customer_success() -> None:
    age = customer_age(PERIOD, MovementType.EXPANSION, _months(date(2025, 6, 1), date(2026, 5, 1)), POLICY)
    assert age.age_months == 12
    assert age.line == "expansion"


def test_new_business_period_answer_moves_the_boundary() -> None:
    history = _months(date(2025, 4, 1), date(2026, 5, 1))  # 14 months old
    eighteen = BucketPolicy(new_business_months=18)
    assert customer_age(PERIOD, MovementType.EXPANSION, history, eighteen).line == "first_year_expansion"
    assert customer_age(PERIOD, MovementType.EXPANSION, history, POLICY).line == "expansion"


def test_existing_customer_without_history_has_no_age() -> None:
    assert customer_age(PERIOD, MovementType.EXPANSION, [], POLICY) is None


# ---------------------------------------------------------------------------
# Engine summary and retention metrics
# ---------------------------------------------------------------------------


def _bucketed_waterfall(with_history: bool = True):
    prior = {"A": _d(100), "B": _d(50), "D": _d(40)}
    current = {"A": _d(110), "C": _d(30), "E": _d(20)}
    history = {
        "A": _months(date(2025, 1, 1), date(2026, 5, 1)),
        "B": _months(date(2026, 1, 1), date(2026, 5, 1)),
        "D": _months(date(2024, 6, 1), date(2026, 5, 1)),
        "E": _months(date(2024, 1, 1), date(2025, 12, 1)),
    }
    return compute_waterfall(
        PERIOD,
        prior,
        current,
        historical_active_customers={"A", "B", "D", "E"},
        mrr_history=history if with_history else None,
    )


def test_summary_splits_lines_and_customer_success_beginning() -> None:
    rows = _bucketed_waterfall()
    lines = {r.customer_id: r.waterfall_line for r in rows}
    assert lines == {"A": "expansion", "B": "no_start", "C": "new_logo", "D": "churn", "E": "reactivation"}

    summary = summarize_company(PERIOD, rows)
    assert summary.bucket_lines_mrr["no_start"] == _d(50)
    assert summary.bucket_lines_mrr["reactivation"] == _d(20)
    assert summary.customer_success_beginning_mrr == _d(140)  # A + D; B is still New Business
    assert summary.new_business_bucket_mrr == _d(-20)  # new logo 30 - no-start 50


def test_retention_is_measured_on_customer_success() -> None:
    metrics = compute_period_metrics(summarize_company(PERIOD, _bucketed_waterfall()))
    assert metrics.retention_base == CUSTOMER_SUCCESS_BASE
    assert metrics.retention_beginning_mrr == _d(140)
    assert metrics.grr == _d("0.7143")  # (140 - 40) / 140
    assert metrics.nrr == _d("0.9286")  # (140 + 10 + 20 - 40) / 140


def test_retention_falls_back_to_all_customers_without_history() -> None:
    summary = summarize_company(PERIOD, _bucketed_waterfall(with_history=False))
    assert summary.bucket_lines_mrr is None
    metrics = compute_period_metrics(summary)
    assert metrics.retention_base == ALL_CUSTOMERS
    assert metrics.retention_beginning_mrr == _d(190)
    assert metrics.grr == _d("0.5263")  # (190 - 50 - 40) / 190


def test_kpis_use_customer_success_mrr_when_given() -> None:
    cs = {"beginning": _d(140), "expansion": _d(10), "contraction": _d(0), "churn": _d(40), "reactivation": _d(20)}
    base = dict(
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        beginning_mrr=_d(190),
        ending_mrr=_d(160),
        expansion_mrr=_d(10),
        churn_mrr=_d(90),
        reactivation_mrr=_d(20),
    )
    bucketed = calculate_kpis(KpiInputs(**base, customer_success_mrr=cs))
    assert (bucketed.grr, bucketed.nrr, bucketed.retention_base) == (_d("0.7143"), _d("0.9286"), "customer_success")
    whole = calculate_kpis(KpiInputs(**base))
    assert whole.retention_base == "all_customers"
    assert whole.grr == _d("0.5263")


# ---------------------------------------------------------------------------
# Onboarding answers and stored history
# ---------------------------------------------------------------------------


def _answers_session(answers):
    return SimpleNamespace(get=lambda _model, _org: SimpleNamespace(answers=answers) if answers else None)


def test_bucket_policy_uses_defaults_for_unanswered_questions() -> None:
    org = uuid.uuid4()
    assert mrr_service.bucket_policy(_answers_session(None), org) == BucketPolicy(
        restart_window_months=6, new_business_months=12, defaults_used=("4.10", "4.12")
    )
    assert mrr_service.bucket_policy(_answers_session({"4.10": "3"}), org).restart_window_months == 3
    assert mrr_service.bucket_policy(_answers_session({"4.10": "no_window"}), org).restart_window_months is None


def test_bucket_policy_reads_the_new_business_period(monkeypatch) -> None:
    monkeypatch.setattr(mrr_service, "normalize_answers", lambda answers: answers)
    got = mrr_service.bucket_policy(_answers_session({"4.10": "12", "4.12": "18"}), uuid.uuid4())
    assert got == BucketPolicy(restart_window_months=12, new_business_months=18, defaults_used=())


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Organization.__table__, Customer.__table__, Subscription.__table__, MrrWaterfall.__table__],
    )
    s = sessionmaker(bind=engine)()
    org = uuid.uuid4()
    s.add(Organization(id=org, name="Test Co"))
    s.add_all([Customer(organization_id=org, customer_id=c, customer_name=c) for c in "ABCDEZ"])

    def sub(sid, cid, start, end, mrr):
        s.add(Subscription(organization_id=org, subscription_id=sid, customer_id=cid, start_date=start,
                           end_date=end, current_mrr=_d(mrr), status="active"))

    sub("a1", "A", date(2025, 1, 1), None, 110)
    sub("b1", "B", date(2026, 1, 1), date(2026, 5, 31), 50)
    sub("c1", "C", date(2026, 6, 1), None, 30)
    sub("d1", "D", date(2024, 6, 1), date(2026, 5, 31), 40)
    sub("e1", "E", date(2024, 1, 1), date(2025, 12, 31), 20)
    sub("e2", "E", date(2026, 6, 1), None, 20)

    def row(cid, begin, end, movement):
        s.add(MrrWaterfall(organization_id=org, period=PERIOD, customer_id=cid, beginning_mrr=_d(begin),
                           ending_mrr=_d(end), movement_type=movement))

    row("A", 100, 110, "expansion")
    row("B", 50, 0, "churn")
    row("C", 0, 30, "new")
    row("D", 40, 0, "churn")
    row("E", 0, 20, "reactivation")
    s.commit()
    yield s, org
    s.close()


def test_customer_active_months_reads_subscription_history(db):
    s, org = db
    got = customer_active_months(s, org, PERIOD, {"A", "C", "E"})
    assert got["A"] == _months(date(2025, 1, 1), date(2026, 5, 1))
    assert got["E"] == _months(date(2024, 1, 1), date(2025, 12, 1))  # the June return is not history yet
    assert "C" not in got


def test_kpi_customer_success_mrr_from_stored_rows(db):
    s, org = db
    got = load_customer_success_mrr(s, org, PERIOD, POLICY)
    assert got == {
        "beginning": _d(140),
        "expansion": _d(10),
        "contraction": _d(0),
        "churn": _d(40),
        "reactivation": _d(20),
    }


def test_kpi_customer_success_mrr_is_unavailable_when_an_age_is_unknown(db):
    s, org = db
    s.add(MrrWaterfall(organization_id=org, period=PERIOD, customer_id="Z", beginning_mrr=_d(30),
                       ending_mrr=_d(30), movement_type="unchanged"))
    s.commit()
    assert load_customer_success_mrr(s, org, PERIOD, POLICY) is None


# ---------------------------------------------------------------------------
# Dashboard ARR waterfall
# ---------------------------------------------------------------------------

BUCKET_ROW = {
    "period": "2026-06",
    "beginning_arr": "1000",
    "new_business_arr": "90",
    "expansion_arr": "60",
    "contraction_arr": "20",
    "churn_arr": "60",
    "reactivation_arr": "10",
    "ending_arr": "1080",
    "new_logo_arr": "80",
    "winback_arr": "10",
    "first_year_expansion_arr": "15",
    "first_year_contraction_arr": "5",
    "no_start_arr": "30",
    "new_business_bucket_arr": "70",
    "customer_success_beginning_arr": "800",
    "customer_success_expansion_arr": "45",
    "customer_success_contraction_arr": "15",
    "customer_success_churn_arr": "20",
    "customer_success_reactivation_arr": "0",
}


def test_bucket_metrics_sign_lines_and_carry_memos() -> None:
    assert has_bucket_columns(BUCKET_ROW)
    m = _bucket_metrics(BUCKET_ROW)
    assert m["new_business"] == _d(70)
    assert (m["first_year_contraction"], m["no_start"]) == (_d(-5), _d(-30))
    assert (m["contraction"], m["churn"]) == (_d(-15), _d(-20))
    assert m[CUSTOMER_SUCCESS_BEGINNING] == _d(800)
    assert m[CLOSED_WON_NEW_BUSINESS] == _d(90)
    rollforward = m["beginning"] + m["new_business"] + m["expansion"] + m["reactivation"] + m["contraction"] + m["churn"]
    assert rollforward == m["ending"]


def test_legacy_rows_have_no_bucket_lines() -> None:
    legacy = {k: v for k, v in BUCKET_ROW.items() if not k.startswith(("new_logo", "winback", "first_year", "no_start",
                                                                         "new_business_bucket", "customer_success"))}
    assert not has_bucket_columns(legacy)
    m = _movement_metrics(legacy)
    assert m["new_business"] == _d(90)
    assert CUSTOMER_SUCCESS_BEGINNING not in m


def _attribution(metrics: dict[str, Decimal]) -> list[WaterfallAttributionRow]:
    return [
        WaterfallAttributionRow(
            organization_id="00000000-0000-0000-0000-000000000001",
            scenario="Actual",
            period="2026-06",
            waterfall_type=t,
            amount=a,
            source_table="actual_mrr_waterfall",
        )
        for t, a in metrics.items()
    ]


def test_summary_rows_nest_new_business_and_mark_memos() -> None:
    rows = _summarize(uuid.UUID(int=1), "arr", _attribution(_bucket_metrics(BUCKET_ROW)))
    by_type = {r.waterfall_type: r for r in rows}
    assert by_type["new_logo"].row_kind == "sub_line"
    assert by_type["new_logo"].parent_type == "new_business"
    assert by_type["new_business"].row_kind == "line"
    assert by_type[CUSTOMER_SUCCESS_BEGINNING].row_kind == "memo"
    assert by_type[CLOSED_WON_NEW_BUSINESS].row_kind == "memo"
    assert by_type["no_start"].line_item == "No-Start"
    order = [r.waterfall_type for r in rows]
    assert order.index("new_business") < order.index("new_logo") < order.index("expansion")
    assert order.index("ending") < order.index(CUSTOMER_SUCCESS_BEGINNING)

    checks = {c.validation_name: c for c in _validate(rows, "arr")}
    assert checks["arr_waterfall_ties"].status == "pass"
    assert checks["arr_new_business_ties_to_its_lines"].status == "pass"


def test_new_business_that_does_not_tie_to_its_lines_fails() -> None:
    broken = dict(BUCKET_ROW, new_logo_arr="180")
    rows = _summarize(uuid.UUID(int=1), "arr", _attribution(_bucket_metrics(broken)))
    checks = {c.validation_name: c for c in _validate(rows, "arr")}
    assert checks["arr_new_business_ties_to_its_lines"].status == "fail"


def test_missing_buckets_are_flagged() -> None:
    legacy = {k: v for k, v in BUCKET_ROW.items() if k in ("beginning_arr", "new_business_arr", "expansion_arr",
                                                            "contraction_arr", "churn_arr", "reactivation_arr",
                                                            "ending_arr")}
    rows = _summarize(uuid.UUID(int=1), "arr", _attribution(_movement_metrics(legacy)))
    checks = {c.validation_name: c for c in _validate(rows, "arr")}
    assert checks["arr_customer_buckets_unavailable"].status == "warning"


# ---------------------------------------------------------------------------
# Board, MD&A and three-statement payload
# ---------------------------------------------------------------------------


def _bundle(arr_rows: list[tuple[str, str, Decimal]], pipeline_rows=()) -> ReportingBundle:
    def wf(name: str, period: str, wtype: str, amount: Decimal, kind: str = "line") -> WaterfallSummaryRow:
        return WaterfallSummaryRow(
            organization_id="test-org",
            scenario="Actual",
            period=period,
            waterfall_name=name,
            waterfall_type=wtype,
            line_item=wtype,
            line_item_order=0,
            amount=amount,
            source_table="test",
            row_kind=kind,
        )

    return ReportingBundle(
        organization_id="test-org",
        organization_name="Test Co",
        scenario="Combined",
        start_period="2026-01",
        end_period="2026-12",
        as_of_period="2026-06",
        period_label="June 2026",
        currency="USD",
        executive_flow=ExecutiveFlowResponse(
            organization_id="test-org",
            scenario="Combined",
            start_period="2026-01",
            end_period="2026-12",
            as_of_period="2026-06",
        ),
        comparison_waterfalls={
            "arr": [wf("arr", p, t, a) for p, t, a in arr_rows],
            "pipeline": [wf("pipeline", p, t, a) for p, t, a in pipeline_rows],
        },
        validation=ExportValidationSummary(status="pass"),
    )


BOARD_ROWS = list(_bucket_metrics(BUCKET_ROW).items())


def test_board_retention_uses_customer_success_base() -> None:
    bundle = _bundle([("2026-06", t, a) for t, a in BOARD_ROWS])
    assert _grr(bundle, "2026-06") == (_d(800) - 15 - 20) / 800
    assert _nrr(bundle, "2026-06") == (_d(800) + 45 - 15 - 20) / 800
    assert retention_base_label(bundle, "2026-06").startswith("Customer Success")


def test_board_retention_without_buckets_uses_all_beginning_arr() -> None:
    bundle = _bundle([("2026-06", t, a) for t, a in _movement_metrics(BUCKET_ROW).items()])
    assert _grr(bundle, "2026-06") == (_d(1000) - 20 - 60) / 1000
    assert retention_base_label(bundle, "2026-06").startswith("all customers")


def test_board_chart_draws_negative_new_business_as_a_decrease() -> None:
    bundle = _bundle([
        ("2026-05", "ending_arr", _d(10_000_000)),
        ("2026-06", "new_business", _d(-500_000)),
    ])
    wf = build_arr_waterfall_chart(bundle)
    assert wf["steps"][1]["kind"] == "decrease"
    assert wf["offsets_m"][1] == pytest.approx(9.5)
    assert wf["heights_m"][1] == pytest.approx(0.5)


def test_closed_won_ties_to_bookings_memo_when_buckets_are_loaded() -> None:
    bundle = _bundle(
        [("2026-06", t, a) for t, a in BOARD_ROWS],
        pipeline_rows=[("2026-06", "closed_won", _d(90))],
    )
    check = next(c for c in _cross_source_checks(bundle) if c.validation_name == "closed_won_arr_ties_mrr_new_business_arr")
    assert check.expected_value == _d(90)
    assert check.status == "pass"


def test_mda_slide_lists_new_business_lines_and_retention_base() -> None:
    slide = _slide_arr_waterfall(_bundle([("2026-06", t, a) for t, a in BOARD_ROWS]))
    labels = [row[0] for row in slide.table.rows]
    assert labels.index("New Business") < labels.index("   New Logo") < labels.index("Expansion")
    assert "   No-Start" in labels
    assert labels[-1].startswith("Customer Success Beginning ARR")
    assert any("excluded from GRR and NRR" in b for b in slide.bullets)


def test_three_statement_retention_uses_customer_success_base() -> None:
    metrics = _normalize_mrr_metrics(_aggregate_mrr_by_period([BUCKET_ROW])["2026-06"])
    assert metrics["arr_nb"] == 70
    assert metrics["grr"] == pytest.approx((800 - 15 - 20) / 800)
    assert metrics["nrr"] == pytest.approx((800 + 45 - 15 - 20) / 800)
    assert metrics["arr_nn"] == pytest.approx(80)  # ties to ending - beginning

    legacy = {k: v for k, v in BUCKET_ROW.items() if k in ("period", "beginning_arr", "new_business_arr",
                                                            "expansion_arr", "contraction_arr", "churn_arr",
                                                            "reactivation_arr", "ending_arr")}
    whole = _normalize_mrr_metrics(_aggregate_mrr_by_period([legacy])["2026-06"])
    assert "arr_cs_bop" not in whole
    assert whole["grr"] == pytest.approx((1000 - 20 - 60) / 1000)
    assert whole["arr_nn"] == pytest.approx(80)
