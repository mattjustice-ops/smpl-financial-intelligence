"""Server-side Monte Carlo — reproducible plan-path stress under stated priors.

Naming discipline: outputs are stress frequencies under stated priors, NOT
calibrated Probability of Attainment.

v1 propagates lever shocks onto the supplied deterministic plan packet
(ARR / cash path / capacity) with seeded RNG so the same (packet, priors, seed)
reproduces. Full Budget formula-graph recomputation remains available client-side
as a fallback; server runs are the diligence-grade SoT for persisted assessments.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any


DEFAULT_PRIORS: dict[str, float] = {
    "yoyPp": 3.2,
    "cplLog": 0.28,
    "attrPp": 2.5,
    "pipe": 0.55,
    # Residual open-month cash-flow noise as a fraction of Dec plan cash
    # per open month (Brownian step). Keeps the corridor fan visible when
    # the deterministic path is nearly flat Jul→Dec.
    "cashResidMo": 0.04,
}

METHOD = "monte_carlo_packet_lever_shocks_open_month_cash_flow"

#: Lever order for the joint draw. Correlation keys are "<a>:<b>" pairs of these.
LEVERS: tuple[str, ...] = ("yoyPp", "cplLog", "attrPp", "pipe")
MAX_ABS_CORRELATION = 0.95


def correlation_key(a: str, b: str) -> str:
    """Canonical "<a>:<b>" key with levers in LEVERS order."""

    ia, ib = LEVERS.index(a), LEVERS.index(b)
    return f"{a}:{b}" if ia < ib else f"{b}:{a}"


def normalize_correlations(
    correlations: dict[str, Any] | None,
) -> tuple[dict[str, float], list[str]]:
    """Validate "<a>:<b>" -> rho pairs; drop anything unusable with a note."""

    out: dict[str, float] = {}
    rejected: list[str] = []
    for raw_key, raw_val in (correlations or {}).items():
        parts = [p.strip() for p in str(raw_key).replace("|", ":").split(":")]
        if len(parts) != 2 or parts[0] == parts[1] or not all(p in LEVERS for p in parts):
            rejected.append(f"{raw_key}: unknown lever pair")
            continue
        try:
            rho = float(raw_val)
        except (TypeError, ValueError):
            rejected.append(f"{raw_key}: not a number")
            continue
        if math.isnan(rho) or abs(rho) > MAX_ABS_CORRELATION:
            rejected.append(f"{raw_key}: |rho| must be <= {MAX_ABS_CORRELATION}")
            continue
        out[correlation_key(parts[0], parts[1])] = rho
    return out, rejected


def _cholesky(matrix: list[list[float]]) -> list[list[float]] | None:
    n = len(matrix)
    lower = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = sum(lower[i][k] * lower[j][k] for k in range(j))
            if i == j:
                d = matrix[i][i] - s
                if d <= 1e-12:
                    return None
                lower[i][j] = math.sqrt(d)
            else:
                lower[i][j] = (matrix[i][j] - s) / lower[j][j]
    return lower


def correlation_cholesky(
    correlations: dict[str, float],
) -> tuple[list[list[float]], dict[str, float], list[str]]:
    """Lower-triangular factor for the lever correlation matrix.

    A pair set that is not jointly consistent (not positive definite) is shrunk
    toward independence until it is, and the shrink is reported — never silently
    altered.
    """

    notes: list[str] = []
    applied = dict(correlations)
    n = len(LEVERS)
    for attempt in range(40):
        matrix = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        for key, rho in applied.items():
            a, b = key.split(":")
            i, j = LEVERS.index(a), LEVERS.index(b)
            matrix[i][j] = matrix[j][i] = rho
        lower = _cholesky(matrix)
        if lower is not None:
            if attempt:
                notes.append(
                    f"Supplied correlations were not jointly consistent; shrunk toward "
                    f"independence by {(1 - 0.9 ** attempt) * 100:.0f}% to make them usable."
                )
            return lower, applied, notes
        applied = {k: v * 0.9 for k, v in applied.items()}
    notes.append("Supplied correlations could not be made consistent; drawing levers independently.")
    identity = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    return identity, {}, notes


def _pctl(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = q * (len(sorted_vals) - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return sorted_vals[lo]
    w = idx - lo
    return sorted_vals[lo] * (1 - w) + sorted_vals[hi] * w


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _sd(vals: list[float], mu: float) -> float:
    if len(vals) < 2:
        return 0.0
    return math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1))


def _histogram(samples: list[float], bins: int = 16) -> dict[str, Any]:
    if not samples:
        return {"bins": [], "counts": [], "mean": 0.0, "n": 0}
    lo, hi = min(samples), max(samples)
    if hi <= lo:
        hi = lo + 1.0
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in samples:
        i = min(bins - 1, int((v - lo) / width))
        counts[i] += 1
    edges = [lo + i * width for i in range(bins + 1)]
    return {"bins": edges, "counts": counts, "mean": _mean(samples), "n": len(samples)}


@dataclass
class MonteCarloResult:
    n: int
    seed: int
    sig: dict[str, float]
    method: str
    prior_source: str
    p_arr_miss: float
    p_cash_below_floor: float
    p_ops_liquidity: float
    p_ae_short: float
    p_trough_breach: float
    arr: dict[str, Any]
    cash: dict[str, Any]
    trough: dict[str, Any] | None
    cash_path_monthly: list[dict[str, Any]]
    method_notes: list[str]
    correlations: dict[str, float] = field(default_factory=dict)

    def to_simulation_summary(self) -> dict[str, Any]:
        return {
            "trials": self.n,
            "breaks": [],
            "watches": [],
            "p_arr_miss": self.p_arr_miss,
            "p_cash_below_floor": self.p_cash_below_floor,
            "p_cash_watch_25": self.cash.get("pWatch25") if isinstance(self.cash, dict) else None,
            "p_ops_liquidity": self.p_ops_liquidity,
            "p_ae_short": self.p_ae_short,
            "priors": {
                **self.sig,
                "source": self.prior_source,
                "seed": self.seed,
                "method": self.method,
                "p_trough_breach": self.p_trough_breach,
                "correlations": dict(self.correlations),
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "seed": self.seed,
            "sig": self.sig,
            "method": self.method,
            "prior_source": self.prior_source,
            "correlations": dict(self.correlations),
            "p_arr_miss": self.p_arr_miss,
            "p_cash_below_floor": self.p_cash_below_floor,
            "p_ops_liquidity": self.p_ops_liquidity,
            "p_ae_short": self.p_ae_short,
            "p_trough_breach": self.p_trough_breach,
            "arr": self.arr,
            "cash": self.cash,
            "trough": self.trough,
            "cash_path": {"monthly": self.cash_path_monthly, "trough": self.trough},
            "method_notes": self.method_notes,
            "simulation_summary": self.to_simulation_summary(),
        }


def run_packet_monte_carlo(
    packet: dict[str, Any],
    *,
    n: int = 1000,
    seed: int = 42,
    priors: dict[str, float] | None = None,
    prior_source: str = "independent_defaults",
    correlations: dict[str, Any] | None = None,
) -> MonteCarloResult:
    """Seeded MC: shock YoY / CPL / attrition / pipeline; open-month cash flows.

    ``correlations`` maps "<a>:<b>" lever pairs (see LEVERS) to rho. The four
    lever shocks are drawn jointly through a Cholesky factor; with no
    correlations the factor is the identity and draws match independent sampling.
    """

    sig = {**DEFAULT_PRIORS, **(priors or {})}
    rng = random.Random(seed)
    corr_in, corr_rejected = normalize_correlations(correlations)
    chol, corr_applied, corr_notes = correlation_cholesky(corr_in)

    bop = float(packet.get("bop_arr") or packet.get("bopArr") or 0.0)
    target = float(packet.get("target_arr") or packet.get("targetArr") or 0.0)
    base_yoy = float(packet.get("yoy_growth_pct") or packet.get("yoyGrowthPct") or 20.0)
    end_cash = float(packet.get("end_cash") or packet.get("endCash") or 0.0)
    cash_floor = float(packet.get("cash_floor") or packet.get("cashFloor") or 10_000_000.0)
    sales_end = float(packet.get("sales_end") or packet.get("salesEnd") or 0.0)
    ae_needed = float(packet.get("ae_needed") or packet.get("aeNeeded") or 0.0)
    cash_by_month = [
        float(v or 0.0)
        for v in (
            packet.get("cash_by_month") or packet.get("cashByMonth") or ([end_cash] * 12)
        )
    ]
    if len(cash_by_month) < 12:
        cash_by_month = (cash_by_month + [end_cash] * 12)[:12]

    close_idx = int(
        packet.get("close_month_idx")
        if packet.get("close_month_idx") is not None
        else (
            packet.get("closeMonthIdx")
            if packet.get("closeMonthIdx") is not None
            else 5
        )
    )
    close_idx = max(0, min(10, close_idx))
    cash_resid_mo = float(sig.get("cashResidMo") or 0.04)
    resid_sd = max(250_000.0, abs(end_cash) * cash_resid_mo)

    arr_samples: list[float] = []
    cash_samples: list[float] = []
    trough_samples: list[float] = []
    paths: list[list[float]] = []
    p_arr = p_cash = p_ae = p_ops = p_trough = p_watch_25 = 0

    base_attr = float(packet.get("hire_pct") or packet.get("hirePct") or 10.0)
    base_pipe = float(packet.get("pipeline_coverage") or packet.get("pipelineCoverage") or 3.0)

    for _ in range(n):
        e = [rng.gauss(0.0, 1.0) for _ in LEVERS]
        z = [sum(chol[i][k] * e[k] for k in range(i + 1)) for i in range(len(LEVERS))]
        dy = sig["yoyPp"] * z[0]
        dcpl = math.exp(sig["cplLog"] * z[1])
        dattr = max(0.0, base_attr + sig["attrPp"] * z[2])
        dpipe = max(1.0, base_pipe + sig["pipe"] * z[3])

        shocked_yoy = max(0.0, base_yoy + dy)
        # ARR path: BOP * (1 + shocked YoY/100), then CPL tax (~elasticity 0.15 on growth)
        cpl_drag = min(0.25, max(-0.05, (dcpl - 1.0) * 0.15))
        pipe_boost = min(0.08, max(-0.12, (dpipe - 3.0) * 0.02))
        dec_arr = bop * (1.0 + shocked_yoy / 100.0) * (1.0 - cpl_drag + pipe_boost)

        # Capacity: attrition raises AE need slightly; shortfall if sales_end < need
        ae_need_shock = ae_needed * (1.0 + max(0.0, (dattr - 10.0) / 100.0) * 0.2)
        ae_short = sales_end < ae_need_shock

        # Cash: pin closed months; shock open-month net change (not the whole stock).
        # Lever elasticity on flows + residual WC/collections noise that compounds Jul→Dec.
        flow_scale = 1.0 - (dy / 100.0) * 1.15 - (dcpl - 1.0) * 0.45
        flow_scale = max(0.25, min(1.85, flow_scale))
        path = list(cash_by_month)
        for m in range(close_idx + 1, 12):
            plan_delta = cash_by_month[m] - cash_by_month[m - 1]
            step = rng.gauss(0.0, resid_sd)
            path[m] = max(0.0, path[m - 1] + plan_delta * flow_scale + step)

        trial_end = path[-1]
        # Trough only over open months (actuals already happened)
        open_slice = path[close_idx:]
        trial_trough = min(open_slice) if open_slice else trial_end

        arr_samples.append(dec_arr)
        cash_samples.append(trial_end)
        trough_samples.append(trial_trough)
        paths.append(path)

        if dec_arr < target * 0.995:
            p_arr += 1
        if trial_end < cash_floor:
            p_cash += 1
        if ae_short:
            p_ae += 1
        drop = (end_cash - trial_end) / max(1.0, end_cash)
        if trial_end < cash_floor or drop >= 0.50:
            p_ops += 1
        if trial_end <= end_cash * 0.75:
            p_watch_25 += 1
        if trial_trough < cash_floor:
            p_trough += 1

    monthly: list[dict[str, Any]] = []
    for m in range(12):
        col = sorted(p[m] for p in paths)
        below = sum(1 for v in col if v < cash_floor) / n
        monthly.append(
            {
                "month_index": m,
                "p10": _pctl(col, 0.10),
                "p25": _pctl(col, 0.25),
                "p50": _pctl(col, 0.50),
                "p75": _pctl(col, 0.75),
                "p90": _pctl(col, 0.90),
                "pBelowFloor": below,
            }
        )

    arr_sorted = sorted(arr_samples)
    cash_sorted = sorted(cash_samples)
    trough_sorted = sorted(trough_samples)
    arr_mu = _mean(arr_samples)
    cash_mu = _mean(cash_samples)
    trough_mu = _mean(trough_samples)

    if corr_applied:
        pairs = ", ".join(f"{k} rho={v:+.2f}" for k, v in sorted(corr_applied.items()))
        corr_note = f"Correlated lever draws (Cholesky): {pairs}. Unlisted pairs are independent."
    else:
        corr_note = "Independent lever draws (no correlations supplied or fitted)."
    notes = [
        f"Server Monte Carlo n={n}, seed={seed}, method={METHOD}.",
        f"Priors source: {prior_source}.",
        corr_note,
        *corr_notes,
        *(f"Correlation ignored — {r}." for r in corr_rejected),
        "Stress frequency under stated priors — not calibrated Probability of Attainment.",
        "Closed months stay pinned to the plan packet. Open months re-roll net cash change "
        f"under lever flow shocks plus residual WC noise (cashResidMo={cash_resid_mo:.3f} of Dec cash / month) "
        "so the Jul–Dec corridor fan opens even when the mean path is nearly flat.",
    ]

    return MonteCarloResult(
        n=n,
        seed=seed,
        sig={
            k: float(sig[k])
            for k in ("yoyPp", "cplLog", "attrPp", "pipe", "cashResidMo")
            if k in sig
        },
        method=METHOD,
        prior_source=prior_source,
        p_arr_miss=p_arr / n,
        p_cash_below_floor=p_cash / n,
        p_ops_liquidity=p_ops / n,
        p_ae_short=p_ae / n,
        p_trough_breach=p_trough / n,
        arr={
            "hist": _histogram(arr_samples),
            "mean": arr_mu,
            "sd": _sd(arr_samples, arr_mu),
            "p10": _pctl(arr_sorted, 0.10),
            "p50": _pctl(arr_sorted, 0.50),
            "p90": _pctl(arr_sorted, 0.90),
            "pMiss": p_arr / n,
        },
        cash={
            "hist": _histogram(cash_samples),
            "mean": cash_mu,
            "sd": _sd(cash_samples, cash_mu),
            "p10": _pctl(cash_sorted, 0.10),
            "p50": _pctl(cash_sorted, 0.50),
            "p90": _pctl(cash_sorted, 0.90),
            "pBreak": p_cash / n,
            "pWatch25": p_watch_25 / n,
        },
        # top-level alias for clients that read flat keys

        trough={
            "hist": _histogram(trough_samples),
            "mean": trough_mu,
            "sd": _sd(trough_samples, trough_mu),
            "p10": _pctl(trough_sorted, 0.10),
            "p50": _pctl(trough_sorted, 0.50),
            "p90": _pctl(trough_sorted, 0.90),
            "pBreachAnyMonth": p_trough / n,
        },
        cash_path_monthly=monthly,
        method_notes=notes,
        correlations=corr_applied,
    )
