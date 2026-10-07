"""Returning customers: winback, restart after pause, returning new business, unknown."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.demo_finance import Customer, Subscription
from app.models.organization import Organization
from app.services.mrr import service
from app.services.mrr.engine import (
    Departure,
    MovementType,
    ReturnPolicy,
    ReturnType,
    classify_customer,
    compute_waterfall,
    summarize_company,
)
from app.services.mrr.repository import customer_departures

AUG = date(2026, 8, 1)
SIX_MONTHS = ReturnPolicy(winback_window_months=6, pause_treatment="removes_arr")


def _d(v) -> Decimal:
    return Decimal(str(v))


def back(current, departure: Departure | None, policy: ReturnPolicy | None = SIX_MONTHS, period: date = AUG):
    row = classify_customer("C", period, _d(0), _d(current), had_historical_mrr=True,
                            departure=departure, policy=policy)
    assert row is not None
    assert row.beginning_mrr + row.new_mrr + row.reactivation_mrr == row.ending_mrr
    return row


def terminated(churn: date, prior=100) -> Departure:
    return Departure(churn_period=churn, prior_mrr=_d(prior), paused=False)


def test_winback_within_window_splits_restored_and_above_baseline():
    row = back(120, terminated(date(2026, 6, 1)))
    assert (row.movement_type, row.return_type, row.months_away) == (MovementType.REACTIVATION, ReturnType.WINBACK, 2)
    assert row.reactivation_mrr == _d("120.00")
    assert (row.baseline_mrr, row.restored_mrr, row.above_baseline_mrr) == (_d("100.00"), _d("100.00"), _d("20.00"))


def test_winback_window_is_inclusive_in_calendar_months():
    # Last billed January; first month without MRR is February; August is 6 months later.
    assert back(100, terminated(date(2026, 2, 1))).return_type is ReturnType.WINBACK
    row = back(100, terminated(date(2026, 1, 1)))
    assert (row.return_type, row.months_away) == (ReturnType.RETURNING_NEW_BUSINESS, 7)


def test_terminated_customer_back_after_window_is_new_business_and_flagged():
    row = back(150, terminated(date(2025, 12, 1)))
    assert (row.movement_type, row.return_type) == (MovementType.NEW, ReturnType.RETURNING_NEW_BUSINESS)
    assert row.new_mrr == _d("150.00") and row.reactivation_mrr == 0
    assert row.baseline_mrr is None and row.above_baseline_mrr is None


def test_restart_after_pause_has_no_time_limit_and_returns_below_baseline_restore_only():
    row = back(80, Departure(churn_period=date(2024, 1, 1), prior_mrr=_d(100), paused=True))
    assert (row.movement_type, row.return_type, row.months_away) == (MovementType.REACTIVATION, ReturnType.RESTART, 31)
    assert (row.restored_mrr, row.above_baseline_mrr) == (_d("80.00"), _d("0.00"))
    assert row.return_note is None


def test_unanswered_window_never_moves_a_return_to_new_business():
    row = back(150, terminated(date(2024, 1, 1)), policy=ReturnPolicy())
    assert (row.movement_type, row.return_type) == (MovementType.REACTIVATION, ReturnType.UNKNOWN)
    assert row.return_note == "winback window (4.10) not answered"
    assert row.above_baseline_mrr == _d("50.00")


def test_no_pause_evidence_is_unknown_when_pauses_remove_arr():
    inside = back(100, Departure(churn_period=date(2026, 5, 1), prior_mrr=_d(100)))
    assert (inside.movement_type, inside.return_type) == (MovementType.REACTIVATION, ReturnType.UNKNOWN)
    assert inside.return_note == "pause or termination not recorded"
    outside = back(100, Departure(churn_period=date(2025, 1, 1), prior_mrr=_d(100)))
    assert (outside.movement_type, outside.return_type) == (MovementType.REACTIVATION, ReturnType.UNKNOWN)
    assert "new business" in (outside.return_note or "")


@pytest.mark.parametrize("pause_treatment", ["keeps_arr", "not_offered"])
def test_gap_is_a_termination_when_pauses_do_not_remove_arr(pause_treatment):
    policy = ReturnPolicy(winback_window_months=6, pause_treatment=pause_treatment)
    gone = Departure(churn_period=date(2025, 1, 1), prior_mrr=_d(100))
    assert back(100, gone, policy=policy).return_type is ReturnType.RETURNING_NEW_BUSINESS


def test_recorded_pause_conflicting_with_keeps_arr_is_noted():
    policy = ReturnPolicy(winback_window_months=6, pause_treatment="keeps_arr")
    row = back(100, Departure(churn_period=date(2026, 5, 1), prior_mrr=_d(100), paused=True), policy=policy)
    assert row.return_type is ReturnType.RESTART
    assert row.return_note == "recorded pause, but 4.11 says pauses keep ARR"


def test_no_window_keeps_every_termination_a_winback():
    row = back(100, terminated(date(2023, 1, 1)), policy=ReturnPolicy(no_window=True))
    assert row.return_type is ReturnType.WINBACK


def test_no_departure_on_record_has_no_baseline():
    row = back(100, None)
    assert (row.return_type, row.months_away, row.baseline_mrr) == (ReturnType.UNKNOWN, None, None)


def test_first_ever_customer_has_no_return_fields():
    row = classify_customer("C", AUG, _d(0), _d(100), had_historical_mrr=False, policy=SIX_MONTHS)
    assert row is not None and row.movement_type is MovementType.NEW and row.return_type is None


def test_summary_counts_returns_and_keeps_the_waterfall_identity():
    rows = compute_waterfall(
        period=AUG,
        prior_mrr_by_customer={"STAY": _d(100), "LEAVE": _d(40)},
        current_mrr_by_customer={"STAY": _d(100), "WIN": _d(120), "RESTART": _d(90), "LATE": _d(70),
                                 "UNK": _d(30), "NEW": _d(50)},
        historical_active_customers={"WIN", "RESTART", "LATE", "UNK"},
        departures={
            "WIN": terminated(date(2026, 6, 1)),
            "RESTART": Departure(churn_period=date(2025, 3, 1), prior_mrr=_d(60), paused=True),
            "LATE": terminated(date(2025, 1, 1)),
        },
        policy=SIX_MONTHS,
    )
    s = summarize_company(AUG, rows)
    assert s.beginning_mrr + s.new_mrr + s.expansion_mrr + s.reactivation_mrr - s.contraction_mrr - s.churn_mrr \
        == s.ending_mrr
    assert (s.reactivated_customers, s.winback_customers, s.restarted_customers, s.unknown_return_customers) \
        == (3, 1, 1, 1)
    assert (s.new_customers, s.returning_new_customers, s.returning_new_mrr) == (2, 1, _d("70.00"))
    assert s.new_mrr == _d("120.00") and s.reactivation_mrr == _d("240.00")
    assert s.reactivation_above_baseline_mrr == _d("50.00")  # WIN 20 + RESTART 30
    assert s.reactivation_without_baseline_mrr == _d("30.00")  # UNK


def test_return_policy_reads_onboarding_answers():
    def session(answers):
        return SimpleNamespace(get=lambda _model, _org: SimpleNamespace(answers=answers) if answers else None)

    org = uuid.uuid4()
    assert service.return_policy(session({"4.10": "6", "4.11": "removes_arr"}), org) == SIX_MONTHS
    assert service.return_policy(session({"4.10": "no_window"}), org) == ReturnPolicy(no_window=True)
    assert service.return_policy(session({"4.10": "5"}), org) == ReturnPolicy()  # not a catalog choice
    assert service.return_policy(session(None), org) == ReturnPolicy()


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Organization.__table__, Customer.__table__, Subscription.__table__])
    s = sessionmaker(bind=engine)()
    org = uuid.uuid4()
    s.add(Organization(id=org, name="Test Co"))
    s.add_all([Customer(organization_id=org, customer_id=c, customer_name=c) for c in ("P", "T", "M", "U", "X")])

    def sub(sid, cid, start, end, mrr, status):
        s.add(Subscription(organization_id=org, subscription_id=sid, customer_id=cid, start_date=start,
                           end_date=end, current_mrr=_d(mrr), status=status))

    sub("p1", "P", date(2024, 1, 1), date(2025, 3, 15), 60, "paused")
    sub("t0", "T", date(2023, 1, 1), date(2024, 6, 30), 30, "canceled")
    sub("t1", "T", date(2024, 7, 1), date(2026, 5, 31), 100, "canceled")
    sub("m1", "M", date(2024, 1, 1), date(2026, 4, 30), 40, "paused")
    sub("m2", "M", date(2024, 1, 1), date(2026, 4, 30), 50, "canceled")
    sub("u1", "U", date(2024, 1, 1), date(2026, 2, 28), 25, "active")
    s.commit()
    yield s, org
    s.close()


def test_customer_departures_reads_last_exit_mrr_and_pause_status(db):
    s, org = db
    got = customer_departures(s, org, AUG, {"P", "T", "M", "U", "X"})
    assert got["P"] == Departure(churn_period=date(2025, 4, 1), prior_mrr=_d("60.00"), paused=True)
    assert got["T"] == Departure(churn_period=date(2026, 6, 1), prior_mrr=_d("100.00"), paused=False)
    assert got["M"] == Departure(churn_period=date(2026, 5, 1), prior_mrr=_d("90.00"), paused=None)  # mixed
    assert got["U"].paused is None  # status does not say
    assert "X" not in got  # nothing ended: no departure on record
