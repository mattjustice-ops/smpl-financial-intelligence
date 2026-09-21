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
from dataclasses import dataclass
from typing import Any


DEFAULT_PRIORS: dict[str, float] = {
    "yoyPp": 3.2,
    "cplLog": 0.28,
    "attrPp": 2.5,
    "pipe": 0.55,
}

METHOD = "monte_carlo_packet_lever_shocks_monthly_path_scale"


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

    def to_simulation_summary(self) -> dict[str, Any]:
        return {
            "trials": self.n,
            "breaks": [],
            "watches": [],
            "p_arr_miss": self.p_arr_miss,
            "p_cash_below_floor": self.p_cash_below_floor,
            "p_ops_liquidity": self.p_ops_liquidity,
            "p_ae_short": self.p_ae_short,
            "priors": {
                **self.sig,
                "source": self.prior_source,
                "seed": self.seed,
                "method": self.method,
                "p_trough_breach": self.p_trough_breach,
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "seed": self.seed,
            "sig": self.sig,
            "method": self.method,
            "prior_source": self.prior_source,
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
) -> MonteCarloResult:
    """Seeded MC: shock YoY / CPL / attrition / pipeline; scale cash path."""

    sig = {**DEFAULT_PRIORS, **(priors or {})}
    rng = random.Random(seed)

    bop = float(packet.get("bop_arr") or packet.get("bopArr") or 0.0)
    target = float(packet.get("target_arr") or packet.get("targetArr") or 0.0)
    base_yoy = float(packet.get("yoy_growth_pct") or packet.get("yoyGrowthPct") or 20.0)
    end_cash = float(packet.get("end_cash") or packet.get("endCash") or 0.0)
    cash_floor = float(packet.get("cash_floor") or packet.get("cashFloor") or 10_000_000.0)
    sales_end = float(packet.get("sales_end") or packet.get("salesEnd") or 0.0)
    ae_needed = float(packet.get("ae_needed") or packet.get("aeNeeded") or 0.0)
    cash_by_month = list(
        packet.get("cash_by_month") or packet.get("cashByMonth") or ([end_cash] * 12)
    )
    if len(cash_by_month) < 12:
        cash_by_month = (cash_by_month + [end_cash] * 12)[:12]

    arr_samples: list[float] = []
    cash_samples: list[float] = []
    trough_samples: list[float] = []
    paths: list[list[float]] = []
    p_arr = p_cash = p_ae = p_ops = p_trough = 0

    for _ in range(n):
        dy = rng.gauss(0.0, sig["yoyPp"])
        dcpl = math.exp(rng.gauss(0.0, sig["cplLog"]))
        dattr = max(0.0, (packet.get("hire_pct") or packet.get("hirePct") or 10.0) + rng.gauss(0.0, sig["attrPp"]))
        dpipe = max(
            1.0,
            float(packet.get("pipeline_coverage") or packet.get("pipelineCoverage") or 3.0)
            + rng.gauss(0.0, sig["pipe"]),
        )

        shocked_yoy = max(0.0, base_yoy + dy)
        # ARR path: BOP * (1 + shocked YoY/100), then CPL tax (~elasticity 0.15 on growth)
        cpl_drag = min(0.25, max(-0.05, (dcpl - 1.0) * 0.15))
        pipe_boost = min(0.08, max(-0.12, (dpipe - 3.0) * 0.02))
        dec_arr = bop * (1.0 + shocked_yoy / 100.0) * (1.0 - cpl_drag + pipe_boost)

        # Capacity: attrition raises AE need slightly; shortfall if sales_end < need
        ae_need_shock = ae_needed * (1.0 + max(0.0, (dattr - 10.0) / 100.0) * 0.2)
        ae_short = sales_end < ae_need_shock

        # Cash: scale path by YoY/CPL stress vs base
        cash_scale = 1.0 - (dy / 100.0) * 0.4 - (dcpl - 1.0) * 0.08
        cash_scale = max(0.35, min(1.35, cash_scale))
        path = [float(v) * cash_scale for v in cash_by_month]
        trial_end = path[-1]
        trial_trough = min(path) if path else trial_end

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
                "p50": _pctl(col, 0.50),
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

    notes = [
        f"Server Monte Carlo n={n}, seed={seed}, method={METHOD}.",
        f"Priors source: {prior_source}. Independent lever draws unless correlations supplied.",
        "Stress frequency under stated priors — not calibrated Probability of Attainment.",
        "v1 scales the deterministic cash path and ARR from lever shocks; "
        "full Budget formula-graph recomputation may differ slightly and remains a client fallback.",
    ]

    return MonteCarloResult(
        n=n,
        seed=seed,
        sig={k: float(sig[k]) for k in ("yoyPp", "cplLog", "attrPp", "pipe")},
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
        },
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
    )
