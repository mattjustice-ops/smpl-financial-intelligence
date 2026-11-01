"""Server-side Monte Carlo — reproducible plan-path stress under stated priors.

Naming discipline: outputs are stress frequencies under stated priors, NOT
calibrated Probability of Attainment.

The packet model propagates lever shocks onto the supplied deterministic plan
packet with seeded RNG so the same (packet, priors, seed) reproduces. Each lever
moves the plan only through an accounting identity on loaded packet fields:

- growth: open-month ARR moves by BOP x shock, phased evenly across the open
  months; subscription revenue (and cash) moves by that ARR / 12 per month;
- cost per lead: open-month program spend scales with CPL at planned MQLs;
- pipeline coverage: open-month new business = pipeline / coverage;
- sales attrition: extra open-month exits come off the ending AE count;
- residual: the measured sd of actual-minus-budget monthly cash from operations.

Inputs that are not loaded, and levers with no prior, leave their effect out and
are named in the notes; nothing is defaulted. A rate whose outcome no drawn lever
moves is not reported. This model is the Forecast Engine's primary simulation and
the Budget Engine's fallback; Budget's primary run recomputes the full formula
graph in the browser with server-issued inputs (see mc_inputs.py).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any


METHOD = "monte_carlo_packet_lever_identities_open_months"

#: Forecast packet model. Correlation keys are "<a>:<b>" pairs of these.
LEVERS: tuple[str, ...] = ("yoyPp", "cplLog", "attrPp", "pipe")
#: Budget full-plan draw. December ARR is the bridge; growth is not also drawn.
BUDGET_LEVERS: tuple[str, ...] = (
    "nbLog", "expLog", "contLog", "churnLog",
    "billPp", "cogsPp", "cplLog", "pipe", "attrPp", "attainPp",
)
LEVER_LABELS = {
    "yoyPp": "ARR growth",
    "nbLog": "new business",
    "expLog": "expansion",
    "contLog": "contraction",
    "churnLog": "churn",
    "billPp": "annual billing",
    "cogsPp": "cost of revenue",
    "cplLog": "cost per lead",
    "attrPp": "sales attrition",
    "pipe": "pipeline coverage",
    "attainPp": "quota attainment",
}


def _lever_order(levers: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    return tuple(levers) if levers is not None else LEVERS


def drawn_priors(
    priors: dict[str, Any] | None,
    levers: tuple[str, ...] | list[str] | None = None,
) -> dict[str, float]:
    """The levers with a usable prior (a finite, non-negative sd); every other lever is not drawn."""

    out: dict[str, float] = {}
    for k in _lever_order(levers):
        try:
            v = float((priors or {}).get(k))
        except (TypeError, ValueError):
            continue
        if math.isfinite(v) and v >= 0:
            out[k] = v
    return out


def correlation_key(a: str, b: str, levers: tuple[str, ...] | list[str] | None = None) -> str:
    """Canonical "<a>:<b>" key with levers in draw order."""

    names = _lever_order(levers)
    ia, ib = names.index(a), names.index(b)
    return f"{a}:{b}" if ia < ib else f"{b}:{a}"


def normalize_correlations(
    correlations: dict[str, Any] | None,
    levers: tuple[str, ...] | list[str] | None = None,
) -> tuple[dict[str, float], list[str]]:
    """Validate "<a>:<b>" -> rho pairs; drop anything unusable with a note."""

    names = _lever_order(levers)
    out: dict[str, float] = {}
    rejected: list[str] = []
    for raw_key, raw_val in (correlations or {}).items():
        parts = [p.strip() for p in str(raw_key).replace("|", ":").split(":")]
        if len(parts) != 2 or parts[0] == parts[1] or not all(p in names for p in parts):
            rejected.append(f"{raw_key}: unknown lever pair")
            continue
        try:
            rho = float(raw_val)
        except (TypeError, ValueError):
            rejected.append(f"{raw_key}: not a number")
            continue
        if math.isnan(rho) or abs(rho) >= 1:
            rejected.append(f"{raw_key}: |rho| must be below 1")
            continue
        out[correlation_key(parts[0], parts[1], names)] = rho
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
    levers: tuple[str, ...] | list[str] | None = None,
) -> tuple[list[list[float]], dict[str, float], list[str]]:
    """Lower-triangular factor for the lever correlation matrix.

    A pair set that is not jointly consistent (not positive definite) is shrunk
    toward independence until it is, and the shrink is reported — never silently
    altered.
    """

    names = _lever_order(levers)
    notes: list[str] = []
    applied = dict(correlations)
    n = len(names)
    for attempt in range(40):
        matrix = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        for key, rho in applied.items():
            a, b = key.split(":")
            i, j = names.index(a), names.index(b)
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
    p_arr_miss: float | None
    p_cash_below_floor: float | None
    p_ops_liquidity: float | None
    p_ae_short: float | None
    p_trough_breach: float | None
    arr: dict[str, Any] | None
    cash: dict[str, Any]
    trough: dict[str, Any] | None
    cash_path_monthly: list[dict[str, Any]]
    method_notes: list[str]
    correlations: dict[str, float] = field(default_factory=dict)
    policy: dict[str, float | None] = field(default_factory=dict)

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
            "policy": dict(self.policy),
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
    prior_source: str = "not_fitted",
    correlations: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
) -> MonteCarloResult:
    """Seeded MC: shock growth / CPL / attrition / pipeline through plan identities.

    ``priors`` holds the sd of each lever to draw; a lever without one is not
    drawn. ``correlations`` maps "<a>:<b>" lever pairs (see LEVERS) to rho. The
    four normals are always generated so a seed reproduces; they are combined
    through a Cholesky factor, the identity when no correlations apply.

    ``policy`` is the plan risk policy ``values`` (see readiness.plan_risk_policy):
    ``arr_miss_tolerance`` sets the ARR miss line, ``cash_watch_shortfall`` and
    ``cash_alarm_shortfall`` the cash bands below plan December cash. A rate whose
    cutoff is not set is not reported.
    """

    pol = policy or {}
    arr_tol = pol.get("arr_miss_tolerance")
    watch_cut = pol.get("cash_watch_shortfall")
    alarm_cut = pol.get("cash_alarm_shortfall")
    sig = drawn_priors(priors)
    rng = random.Random(seed)
    corr_in, corr_rejected = normalize_correlations(correlations)
    for key in list(corr_in):
        if any(k not in sig for k in key.split(":")):
            corr_rejected.append(f"{key}: a lever in the pair is not drawn")
            del corr_in[key]
    chol, corr_applied, corr_notes = correlation_cholesky(corr_in)
    model = _packet_model_inputs(packet)
    close_idx = model["close_idx"]
    open_months = list(range(close_idx + 1, 12))
    n_open = len(open_months)
    plan_cash = model["cash_by_month"]
    end_cash = model["end_cash"]
    cash_floor = model["cash_floor"]
    dec_arr_plan, target, bop = model["dec_arr"], model["target_arr"], model["bop_arr"]
    pipe_moves = "pipe" in sig and model["open_nb"] is not None and model["pipeline_coverage"] is not None
    arr_on = dec_arr_plan is not None and bop is not None and n_open > 0 and ("yoyPp" in sig or pipe_moves)
    ae_on = model["sales_end"] is not None and model["ae_needed"] is not None and n_open > 0 and "attrPp" in sig
    cash_on = plan_cash is not None and n_open > 0
    undrawn = [LEVER_LABELS[k] for k in LEVERS if k not in sig]

    arr_samples: list[float] = []
    cash_samples: list[float] = []
    trough_samples: list[float] = []
    paths: list[list[float]] = []
    p_arr = p_cash = p_ae = p_ops = p_trough = p_watch = p_alarm = 0

    for _ in range(n):
        e = [rng.gauss(0.0, 1.0) for _ in LEVERS]
        z = [sum(chol[i][k] * e[k] for k in range(i + 1)) for i in range(len(LEVERS))]
        dy = sig.get("yoyPp", 0.0) * z[0]
        dcpl = math.exp(sig.get("cplLog", 0.0) * z[1])
        dattr = sig.get("attrPp", 0.0) * z[2]
        base_pipe = model["pipeline_coverage"]
        # Coverage below 1x would mean closing more than the pipeline holds.
        dpipe = max(1.0, base_pipe + sig["pipe"] * z[3]) if pipe_moves else None

        # ARR moved by the open months only; closed months already happened.
        d_arr_growth = bop * dy / 100.0 * n_open / 12.0 if arr_on else 0.0
        d_arr_pipe = model["open_nb"] * (base_pipe / dpipe - 1.0) if dpipe else 0.0
        d_arr = d_arr_growth + d_arr_pipe
        if arr_on:
            dec_arr = dec_arr_plan + d_arr
            arr_samples.append(dec_arr)
            if target is not None and arr_tol is not None and dec_arr < target * (1.0 - arr_tol):
                p_arr += 1

        if ae_on:
            extra_exits = max(0.0, dattr) / 100.0 * model["sales_end"] * n_open / 12.0
            if model["sales_end"] - extra_exits < model["ae_needed"]:
                p_ae += 1

        if not cash_on:
            continue
        path = list(plan_cash)
        shock = 0.0
        for k, m in enumerate(open_months, start=1):
            # ARR change reached by this open month, billed as ARR / 12.
            shock += d_arr * k / n_open / 12.0
            spend = model["program_by_month"][m] if model["program_by_month"] else None
            if spend is not None:
                shock -= spend * (dcpl - 1.0)
            if model["resid_sd"] is not None:
                shock += rng.gauss(0.0, model["resid_sd"])
            path[m] = max(0.0, plan_cash[m] + shock)

        trial_end = path[-1]
        open_slice = path[close_idx + 1:]
        trial_trough = min(open_slice)
        cash_samples.append(trial_end)
        trough_samples.append(trial_trough)
        paths.append(path)

        if end_cash is not None and watch_cut is not None and trial_end <= end_cash * (1.0 - watch_cut):
            p_watch += 1
        if end_cash is not None and alarm_cut is not None and trial_end <= end_cash * (1.0 - alarm_cut):
            p_alarm += 1
        if cash_floor is not None:
            if trial_end < cash_floor:
                p_cash += 1
            if alarm_cut is not None and (
                trial_end < cash_floor or (end_cash - trial_end) / max(1.0, end_cash) >= alarm_cut
            ):
                p_ops += 1
            if trial_trough < cash_floor:
                p_trough += 1

    monthly: list[dict[str, Any]] = []
    for m in range(12 if paths else 0):
        col = sorted(p[m] for p in paths)
        below = sum(1 for v in col if v < cash_floor) / n if cash_floor is not None else None
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

    if corr_applied:
        pairs = ", ".join(f"{k} rho={v:+.2f}" for k, v in sorted(corr_applied.items()))
        corr_note = f"Correlated lever draws (Cholesky): {pairs}. Unlisted pairs are independent."
    else:
        corr_note = "Independent lever draws (no correlations supplied or fitted)."
    notes = [
        f"Server Monte Carlo n={n}, seed={seed}, method={METHOD}.",
        f"Priors source: {prior_source}.",
        *(
            [f"Not drawn (no fitted prior): {', '.join(undrawn)} — those shocks are left out."]
            if undrawn else []
        ),
        *(
            ["No ARR lever is drawn — the ARR miss rate is not reported."]
            if dec_arr_plan is not None and bop is not None and n_open > 0 and not arr_on else []
        ),
        *(
            ["Sales attrition is not drawn — AE shortfall is not reported."]
            if model["sales_end"] is not None and model["ae_needed"] is not None and n_open > 0 and not ae_on else []
        ),
        corr_note,
        *corr_notes,
        *(f"Correlation ignored — {r}." for r in corr_rejected),
        "Stress frequency under stated priors — not calibrated Probability of Attainment.",
        "Closed months stay pinned to the plan packet; levers move the open months only.",
        *model["notes"],
        *(
            f"Risk policy {qid} ({what}) not set — {effect}."
            for value, qid, what, effect in (
                (arr_tol, "7.51", "ARR target miss tolerance", "the ARR miss rate is not reported"),
                (watch_cut, "7.43", "cash watch band", "the watch-band cash rate is not reported"),
                (alarm_cut, "7.44", "cash alarm band", "the alarm-band and liquidity rates are not reported"),
            )
            if value is None
        ),
    ]
    floor_on = cash_floor is not None and bool(paths)
    p_arr_miss = p_arr / n if arr_on and target is not None and arr_tol is not None else None
    arr_stats = _stats(arr_samples)
    if arr_stats is not None:
        arr_stats["pMiss"] = p_arr_miss
    cash_stats = _stats(cash_samples)
    if cash_stats is not None:
        cash_stats["pBreak"] = p_cash / n if floor_on else None
        cash_stats["pWatch"] = p_watch / n if end_cash is not None and watch_cut is not None else None
        cash_stats["pAlarm"] = p_alarm / n if end_cash is not None and alarm_cut is not None else None
    trough_stats = _stats(trough_samples)
    if trough_stats is not None:
        trough_stats["pBreachAnyMonth"] = p_trough / n if floor_on else None

    return MonteCarloResult(
        n=n,
        seed=seed,
        sig=dict(sig),
        method=METHOD,
        prior_source=prior_source,
        p_arr_miss=p_arr_miss,
        p_cash_below_floor=p_cash / n if floor_on else None,
        p_ops_liquidity=p_ops / n if floor_on and alarm_cut is not None else None,
        p_ae_short=p_ae / n if ae_on else None,
        p_trough_breach=p_trough / n if floor_on else None,
        arr=arr_stats,
        cash=cash_stats or {},
        trough=trough_stats,
        cash_path_monthly=monthly,
        method_notes=notes,
        correlations=corr_applied,
        policy={
            "arr_miss_tolerance": arr_tol,
            "cash_watch_shortfall": watch_cut,
            "cash_alarm_shortfall": alarm_cut,
        },
    )


def _stats(samples: list[float]) -> dict[str, Any] | None:
    if not samples:
        return None
    ordered = sorted(samples)
    mu = _mean(samples)
    return {
        "hist": _histogram(samples),
        "mean": mu,
        "sd": _sd(samples, mu),
        "p10": _pctl(ordered, 0.10),
        "p50": _pctl(ordered, 0.50),
        "p90": _pctl(ordered, 0.90),
    }


def _num(packet: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = packet.get(key)
        if value is not None:
            try:
                f = float(value)
            except (TypeError, ValueError):
                continue
            if not math.isnan(f):
                return f
    return None


def _packet_model_inputs(packet: dict[str, Any]) -> dict[str, Any]:
    """Loaded packet fields the lever identities use; anything absent is None and named in ``notes``."""

    notes: list[str] = []
    raw_cash = packet.get("cash_by_month") or packet.get("cashByMonth")
    cash = [float(v) for v in raw_cash] if raw_cash and len(raw_cash) == 12 and all(v is not None for v in raw_cash) else None
    if cash is None:
        notes.append("No 12-month plan cash path in the packet — cash is not simulated.")
    raw_close = packet.get("close_month_idx") if packet.get("close_month_idx") is not None else packet.get("closeMonthIdx")
    close_idx = max(-1, min(11, int(raw_close))) if raw_close is not None else -1
    raw_prog = packet.get("program_by_month") or packet.get("programByMonth")
    program = [None if v is None else float(v) for v in raw_prog] if raw_prog and len(raw_prog) == 12 else None
    if program is None:
        notes.append("Program spend by month not loaded — the cost-per-lead shock does not move cash.")
    open_nb = _num(packet, "open_nb", "openNb")
    coverage = _num(packet, "pipeline_coverage", "pipelineCoverage")
    if open_nb is None or coverage is None:
        notes.append("Open-month new business or pipeline coverage not loaded — the coverage shock does not move ARR.")
    resid_sd = _num(packet, "cfo_plan_error_sd", "cfoPlanErrorSd")
    if resid_sd is None:
        notes.append("Actual-vs-budget monthly cash from operations not loaded — no residual cash noise; the fan is lever shocks only.")
    else:
        notes.append(f"Residual cash noise = measured sd of actual minus budget monthly cash from operations (${resid_sd / 1e6:.2f}M / month).")
    dec_arr = _num(packet, "dec_arr", "decArr")
    bop = _num(packet, "bop_arr", "bopArr")
    target = _num(packet, "target_arr", "targetArr")
    if dec_arr is None or bop is None:
        notes.append("Plan December or January beginning ARR not loaded — ARR is not simulated.")
    elif target is None:
        notes.append("No plan ARR target loaded — ARR is simulated but the miss rate is not reported.")
    sales_end = _num(packet, "sales_end", "salesEnd")
    ae_needed = _num(packet, "ae_needed", "aeNeeded")
    if sales_end is None or ae_needed is None:
        notes.append("Ending AEs or AE need not sized — AE shortfall is not reported.")
    end_cash = _num(packet, "end_cash", "endCash")
    if end_cash is None and cash is not None:
        end_cash = cash[-1]
    floor = _num(packet, "cash_floor", "cashFloor")
    if floor is None:
        notes.append("Cash floor not loaded — floor breach and liquidity probabilities are not reported.")
    return {
        "cash_by_month": cash,
        "close_idx": close_idx,
        "program_by_month": program,
        "open_nb": open_nb,
        "pipeline_coverage": coverage,
        "resid_sd": resid_sd,
        "dec_arr": dec_arr,
        "bop_arr": bop,
        "target_arr": target,
        "sales_end": sales_end,
        "ae_needed": ae_needed,
        "end_cash": end_cash,
        "cash_floor": floor,
        "notes": notes,
    }
