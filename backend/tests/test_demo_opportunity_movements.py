"""Demo-data opportunity movements (scripts/demo_data/rebuild_opportunity_movements.py)."""

from __future__ import annotations

import datetime as dt
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo_data"))

import rebuild_opportunity_movements as om  # noqa: E402

D = Decimal


def deal(i: str, amount: str, channel: str = "Search", created: str = "2026-01-05") -> om.Deal:
    return om.Deal(i, om.NB, channel, dt.date.fromisoformat(created), D(amount), {})


def test_spread_adds_up_to_the_cent_and_varies_by_deal() -> None:
    parts = om.spread(D("100000.01"), 7, "Actual|2026-01|New Business|Search")
    assert len(parts) == 7 and sum(parts) == D("100000.01")
    assert len(set(parts)) > 1 and all(D("100000.01") / 7 * D("0.5") < p < D("100000.01") / 7 * D("1.5") for p in parts)
    assert parts == om.spread(D("100000.01"), 7, "Actual|2026-01|New Business|Search")
    assert om.spread(D("5"), 0, "x") == []


def test_take_is_the_best_fit_oldest_on_a_tie() -> None:
    a, b, c = deal("A", "30000", created="2025-11-01"), deal("B", "30000", created="2025-12-01"), deal("C", "90000")
    assert [d.id for d in om.take([a, b, c], D("31000"))] == ["A"]
    assert [d.id for d in om.take([a, b, c], D("58000"))] == ["A", "B"]
    # Never adds a deal that moves the total further from the target.
    assert [d.id for d in om.take([c], D("10000"))] == ["C"]
    assert [d.id for d in om.take([a, c], D("10000"))] == ["A"]


def test_exit_amounts_close_out_an_emptied_channel_at_its_balance() -> None:
    # Search's open balance is 25k though its one deal still shows 30k (an earlier exit this month resized the
    # channel); taking it closes out the 25k, and the Events deal takes the rest of the 40k.
    s, e1, e2 = deal("S", "30000"), deal("E1", "20000", "Events"), deal("E2", "20000", "Events")
    got = om.exit_amounts([s, e1], D("40000"), [s, e1, e2], {"Search": D("25000"), "Events": D("40000")})
    assert got == {"S": D("25000"), "E1": D("15000.00")}


def test_exit_amounts_keep_an_open_balance_in_every_channel_left_open() -> None:
    e1, e2 = deal("E1", "20000", "Events"), deal("E2", "20000", "Events")
    balance = {"Events": D("40000")}
    assert om.exit_amounts([e1], D("39999.99"), [e1, e2], balance) == {"E1": D("39999.99")}
    assert om.exit_amounts([e1], D("40000"), [e1, e2], balance) is None
    assert om.exit_amounts([e1, e2], D("40000"), [e1, e2], balance) == {"E1": D("20000.00"), "E2": D("20000.00")}
    assert om.exit_amounts([e1, e2], D("39000"), [e1, e2], balance) is None


def test_pick_falls_back_to_a_deal_its_channel_can_close() -> None:
    # The best fit for 25k is the Search deal, but Search has only 5k left open: it would close out at 5k, not 25k.
    s, e1, e2 = deal("S", "24000"), deal("E1", "30000", "Events"), deal("E2", "30000", "Events")
    picked, amounts = om.pick([s, e1], [s, e1, e2], D("25000"), {"Search": D("5000"), "Events": D("60000")})
    assert [d.id for d in picked] == ["S", "E1"]
    assert amounts == {"S": D("5000"), "E1": D("20000")}


def test_day_in_stays_in_the_month_and_after_a_given_day() -> None:
    for i in range(50):
        d = om.day_in("2026-02", f"k{i}", dt.date(2026, 2, 20))
        assert dt.date(2026, 2, 20) <= d <= dt.date(2026, 2, 28)
    assert om.day_in("2026-03", "k", dt.date(2026, 2, 20)).month == 3


def test_refuses_relative_folders() -> None:
    with pytest.raises(SystemExit, match="absolute"):
        om.main("relative", "out")
