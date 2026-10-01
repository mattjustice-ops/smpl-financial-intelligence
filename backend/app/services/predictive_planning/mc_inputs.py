"""Server-issued Monte Carlo inputs for the Budget full-plan engine.

The server decides the seed, lever priors and lever correlations. The Budget
Engine runs its full formula graph in the browser with exactly those inputs and
a seeded sampler (``SAMPLER``), so a run reproduces from the seed and the
recorded inputs on the same plan. The server packet model
(``run_packet_monte_carlo``) is a labeled fallback for when the full-plan engine
cannot run.

``reconcile_simulation_priors`` makes the method card and the persisted
assessment describe the priors a simulation actually used, never a history fit
the simulation did not use.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any

from app.services.predictive_planning.monte_carlo import (
    LEVERS,
    correlation_cholesky,
    normalize_correlations,
)
from app.services.predictive_planning.priors import fit_priors_from_history

FULL_PLAN_ENGINE = "full_plan_browser"
#: /simulate output. Forecast uses it as its primary engine; Budget records
#: "server_packet_fallback" when it falls back to it.
PACKET_ENGINE = "server_packet"
#: Browser sampler contract: mulberry32 uniforms -> Box-Muller normals (cos
#: branch, two uniforms per normal) -> Cholesky-correlated lever shocks, four
#: normals per trial in LEVERS order. Bump the suffix if the sampler changes.
SAMPLER = "mulberry32_box_muller_cholesky_v1"
_PRIOR_KEYS = (*LEVERS, "cashResidMo")
_TOL = 1e-9


def mc_inputs_hash(
    seed: int,
    n_trials: int,
    priors: dict[str, Any],
    correlations: dict[str, Any] | None,
    sampler: str = SAMPLER,
) -> str:
    payload = {
        "seed": int(seed),
        "n_trials": int(n_trials),
        "priors": {k: float(priors[k]) for k in LEVERS if k in priors},
        "correlations": {k: float(v) for k, v in sorted((correlations or {}).items())},
        "sampler": sampler,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def build_mc_inputs(
    history: dict[str, Any] | None,
    *,
    seed: int = 42,
    n_trials: int = 1000,
) -> dict[str, Any]:
    """Seed, lever priors and applied correlations for one full-plan run."""

    fit = fit_priors_from_history(history)
    priors = {k: float(fit["priors"][k]) for k in LEVERS}
    supplied, _ = normalize_correlations(fit["correlations"])
    _, applied, corr_notes = correlation_cholesky(supplied)
    inputs_hash = mc_inputs_hash(seed, n_trials, priors, applied)

    card = copy.deepcopy(fit["method_card"])
    card["priors"] = dict(priors)
    card["correlations"] = dict(applied)
    card["notes"] = [*card["notes"][:2], *corr_notes, *card["notes"][2:]]
    card["simulation"] = {
        "engine": FULL_PLAN_ENGINE,
        "seed": int(seed),
        "trials": int(n_trials),
        "sampler": SAMPLER,
        "inputs_hash": inputs_hash,
    }
    return {
        "seed": int(seed),
        "n_trials": int(n_trials),
        "priors": priors,
        "prior_source": fit["prior_source"],
        "correlations": dict(applied),
        "sampler": SAMPLER,
        "engine": FULL_PLAN_ENGINE,
        "inputs_hash": inputs_hash,
        "label": fit["label"],
        "method_card": card,
    }


def _numeric_priors(priors: dict[str, Any] | None) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in (priors or {}).items():
        if k not in _PRIOR_KEYS:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if not math.isnan(f):
            out[k] = f
    return out


def _same_correlations(a: dict[str, float], b: dict[str, float]) -> bool:
    keys = {k for k, v in a.items() if abs(v) > _TOL} | {k for k, v in b.items() if abs(v) > _TOL}
    return all(abs(a.get(k, 0.0) - b.get(k, 0.0)) <= _TOL for k in keys)


def reconcile_simulation_priors(
    history: dict[str, Any] | None,
    simulation: dict[str, Any] | None,
) -> dict[str, Any]:
    """Method card + prior source describing the priors a simulation used.

    With no recorded simulation priors, returns the server's history fit. With
    recorded priors that match what the server issues for this history, the
    fitted card is returned with the used values. When they differ, the card
    shows the used priors and says so; nothing is labeled as fitted.
    """

    fit = fit_priors_from_history(history)
    sim = simulation or {}
    used = _numeric_priors(sim.get("priors"))
    if not any(k in used for k in LEVERS):
        return {
            "method_card": fit["method_card"],
            "prior_source": fit["prior_source"],
            "notes": fit["method_card"]["notes"][:2],
            "simulation_inputs": None,
        }

    seed = sim.get("seed")
    if seed is None:
        seed = (sim.get("priors") or {}).get("seed")
    trials = sim.get("trials") or 1000
    raw_corr = sim.get("correlations")
    if raw_corr is None:
        raw_corr = (sim.get("priors") or {}).get("correlations")
    used_corr, _ = normalize_correlations(raw_corr)
    used_source = (sim.get("priors") or {}).get("source") or "caller_supplied"
    engine = sim.get("engine")

    issued = build_mc_inputs(history, seed=int(seed) if seed is not None else 42, n_trials=int(trials))
    matches = all(
        k in used and abs(used[k] - issued["priors"][k]) <= _TOL for k in LEVERS
    ) and _same_correlations(used_corr, issued["correlations"])

    supplied_hash = sim.get("inputs_hash")
    hash_verified = None
    if supplied_hash and seed is not None:
        hash_verified = supplied_hash == mc_inputs_hash(int(seed), int(trials), used, used_corr)

    simulation_inputs = {
        "engine": engine,
        "sampler": sim.get("sampler"),
        "seed": int(seed) if seed is not None else None,
        "trials": int(trials),
        "inputs_hash": supplied_hash,
        "inputs_hash_verified": hash_verified,
        "matches_server_fit": matches,
    }

    if matches:
        card = copy.deepcopy(issued["method_card"])
        card["priors"] = dict(used)
        card["simulation"] = {**card["simulation"], **simulation_inputs}
        return {
            "method_card": card,
            "prior_source": issued["prior_source"],
            "notes": card["notes"][:2],
            "simulation_inputs": simulation_inputs,
        }

    if used_corr:
        corr_label = "Correlated draws: " + ", ".join(
            f"{k} rho={v:+.2f}" for k, v in sorted(used_corr.items())
        )
    else:
        corr_label = "Independent draws — the simulation used no lever correlations."
    label = (
        f"Priors shown are the ones the simulation used (source: {used_source}). They differ "
        "from the server's fit of the supplied history, so none is claimed as fitted from company history."
    )
    card = copy.deepcopy(fit["method_card"])
    card["source"] = used_source
    card["priors"] = dict(used)
    card["correlations"] = dict(used_corr)
    card["simulation"] = simulation_inputs
    card["notes"] = [
        label,
        corr_label,
        f"For reference, the server's fit of the supplied history: {fit['label']}",
        "Breach rates are stress frequencies under these priors, not PoA.",
    ]
    return {
        "method_card": card,
        "prior_source": used_source,
        "notes": card["notes"][:2],
        "simulation_inputs": simulation_inputs,
    }
