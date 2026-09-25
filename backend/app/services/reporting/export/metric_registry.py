"""Canonical KPI definitions for board + every PPTX / commentary path.

Net New ARR must never be aliased to New Business alone. Formula matches
``mrr.metrics.compute_period_metrics``:

    net_new = new_business + expansion + reactivation − contraction − churn
"""

from __future__ import annotations

from decimal import Decimal

from app.services.reporting.export.board_chart_service import _wf
from app.services.reporting.export.schemas import ReportingBundle

ZERO = Decimal("0")

NET_NEW_FORMULA_ID = "net_new = nb+exp+react-cont-churn"


def _arr_component(
    bundle: ReportingBundle,
    period: str,
    scenario: str,
    *keys: str,
) -> Decimal:
    for key in keys:
        val = _wf(bundle, "arr", key, period, scenario)
        if val:
            return Decimal(str(val))
    return ZERO


def compute_new_business_arr(
    bundle: ReportingBundle,
    period: str,
    scenario: str = "Actual",
) -> Decimal:
    """New logo / new business ARR for the period (not Net New)."""
    # Prefer new_business spelling; new_arr is an alias for the same movement type
    # in ARR_MOVEMENT_TYPES — never treat it as Net New.
    return _arr_component(bundle, period, scenario, "new_business", "new_arr")


def compute_expansion_arr(
    bundle: ReportingBundle,
    period: str,
    scenario: str = "Actual",
) -> Decimal:
    return _arr_component(bundle, period, scenario, "expansion_arr", "expansion")


def compute_reactivation_arr(
    bundle: ReportingBundle,
    period: str,
    scenario: str = "Actual",
) -> Decimal:
    return _arr_component(bundle, period, scenario, "reactivation_arr", "reactivation")


def compute_contraction_arr(
    bundle: ReportingBundle,
    period: str,
    scenario: str = "Actual",
) -> Decimal:
    return abs(
        _arr_component(bundle, period, scenario, "contraction_arr", "contraction")
    )


def compute_churn_arr(
    bundle: ReportingBundle,
    period: str,
    scenario: str = "Actual",
) -> Decimal:
    return abs(_arr_component(bundle, period, scenario, "churn_arr", "churn"))


def compute_beginning_arr(
    bundle: ReportingBundle,
    period: str,
    scenario: str = "Actual",
) -> Decimal:
    return _arr_component(bundle, period, scenario, "beginning_arr", "beginning")


def compute_ending_arr(
    bundle: ReportingBundle,
    period: str,
    scenario: str = "Actual",
) -> Decimal:
    return _arr_component(bundle, period, scenario, "ending_arr", "ending")


def compute_net_new_arr(
    bundle: ReportingBundle,
    period: str,
    scenario: str = "Actual",
) -> Decimal:
    """True Net New ARR for the period.

    Prefers an explicit ``net_new_arr`` waterfall type only when component rows
    are absent (sparse packs). Otherwise always computes from movements so
    ``new_arr`` / ``new_business`` cannot masquerade as Net New.
    """
    nb = compute_new_business_arr(bundle, period, scenario)
    exp = compute_expansion_arr(bundle, period, scenario)
    react = compute_reactivation_arr(bundle, period, scenario)
    cont = compute_contraction_arr(bundle, period, scenario)
    churn = compute_churn_arr(bundle, period, scenario)
    if nb or exp or react or cont or churn:
        return nb + exp + react - cont - churn

    explicit = _arr_component(bundle, period, scenario, "net_new_arr")
    if explicit:
        return explicit
    return ZERO


def arr_bridge_identity_expected(
    bundle: ReportingBundle,
    period: str,
    scenario: str = "Actual",
) -> tuple[Decimal, Decimal]:
    """Return (expected_ending, actual_ending) for ARR bridge identity.

    expected = begin + nb + exp + react − cont − churn
    """
    begin = compute_beginning_arr(bundle, period, scenario)
    if not begin:
        # Fall back to prior ending when beginning row missing
        from app.services.reporting.period_utils import prior_period

        begin = compute_ending_arr(bundle, prior_period(period), scenario)
    expected = (
        begin
        + compute_new_business_arr(bundle, period, scenario)
        + compute_expansion_arr(bundle, period, scenario)
        + compute_reactivation_arr(bundle, period, scenario)
        - compute_contraction_arr(bundle, period, scenario)
        - compute_churn_arr(bundle, period, scenario)
    )
    actual = compute_ending_arr(bundle, period, scenario)
    return expected, actual
