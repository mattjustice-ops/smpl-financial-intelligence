"""Unit tests for cash continuity spine checks."""

from app.services.reporting.cash_continuity import CashCheck, CashContinuityReport, _close


def test_close_tolerates_dollar_noise():
    assert _close(100.0, 100.4) is True
    assert _close(100.0, 102.0) is False
    assert _close(None, None) is True
    assert _close(1.0, None) is False


def test_report_summary_ok():
    r = CashContinuityReport(
        checks=[
            CashCheck("C1", "2026-06", "Budget", "CFS↔BS", 27.91e6, 27.91e6, True),
        ]
    )
    assert r.ok
    assert "ok" in r.summary()


def test_report_summary_lists_failures():
    r = CashContinuityReport(
        checks=[
            CashCheck("C3", "2026-06", "Budget", "bridge↔CFS", 31.46e6, 27.91e6, False),
            CashCheck("C5", "2026-07", "Forecast", "opens on close", 47.9e6, 30.0e6, False),
        ]
    )
    assert not r.ok
    s = r.summary()
    assert "2 cash continuity failures" in s
    assert "C3" in s and "C5" in s
