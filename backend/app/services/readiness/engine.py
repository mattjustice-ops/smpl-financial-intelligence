"""Capability Assessment Layer — Readiness Score (Agent Playbooks CAL.4–CAL.7, SOF 7.2).

Pure functions: ``assess(evidence, answers)`` takes canonical-object evidence (presence and
confidence per object) and questionnaire answers, and returns per-module status, the Readiness
Score, and ranked next improvements. No database access here — see ``evidence.py``.

Rules carried from the spec:
  * PARTIAL is never rounded up to READY.
  * ARR-related modules cannot be READY with an unresolved Subscription Normalization Gate;
    CRM pipeline modules cannot be READY with unresolved stage normalization.
  * If any readiness gate (questionnaire Section 0) fails, no score is produced.
  * SMPL never closes a gap by adjusting customer data — every path is a customer action,
    a connector, or a questionnaire decision.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from app.services.readiness.registry import (
    ALL_QUESTIONS,
    CONNECTOR_TYPES,
    MODULES,
    NORMALIZATION_GATES,
    OBJECTS,
    READINESS_GATES,
    SCORE_INPUTS,
    Module,
    ObjectEvidence,
)

READY = "READY"
PARTIAL = "PARTIAL"
UNAVAILABLE = "UNAVAILABLE"

STATUS_FACTOR = {READY: 1.0, PARTIAL: 0.5, UNAVAILABLE: 0.0}


def normalize_answers(raw: Mapping[str, Any] | None) -> dict[str, str]:
    """Keep only catalog questions with an allowed choice."""
    out: dict[str, str] = {}
    for qid, value in (raw or {}).items():
        q = ALL_QUESTIONS.get(str(qid))
        if q is None or value is None:
            continue
        v = str(value).strip().lower()
        if v in q.choices:
            out[q.id] = v
    return out


def validate_answers(raw: Mapping[str, Any]) -> list[str]:
    """Human-readable errors for unknown questions or invalid choices (None clears an answer)."""
    errors: list[str] = []
    for qid, value in raw.items():
        q = ALL_QUESTIONS.get(str(qid))
        if q is None:
            errors.append(f"Unknown question id: {qid}")
        elif value is not None and str(value).strip().lower() not in q.choices:
            errors.append(f"{qid}: '{value}' is not one of {', '.join(q.choices)}")
    return errors


def _gate_status(answers: dict[str, str]) -> dict[str, Any]:
    items = []
    for q in READINESS_GATES:
        a = answers.get(q.id)
        items.append({"id": q.id, "prompt": q.prompt, "answer": a,
                      "status": "pass" if a == "yes" else "fail" if a == "no" else "pending"})
    failed = [i["id"] for i in items if i["status"] == "fail"]
    pending = [i["id"] for i in items if i["status"] == "pending"]
    return {
        "status": "fail" if failed else "pending" if pending else "pass",
        "failed": failed,
        "pending": pending,
        "items": items,
    }


def _normalization_status(answers: dict[str, str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for gid, g in NORMALIZATION_GATES.items():
        resolved_values = g["resolved_values"]
        unresolved = []
        for q in g["questions"]:  # type: ignore[union-attr]
            a = answers.get(q.id)
            ok = a is not None and (resolved_values is None or a in resolved_values)  # type: ignore[operator]
            if not ok:
                unresolved.append(q.id)
        out[gid] = {"id": gid, "name": g["name"], "resolved": not unresolved, "unresolved_questions": unresolved}
    return out


def _policy_effects(module: Module, answers: dict[str, str]) -> tuple[float, list[dict[str, Any]]]:
    penalty = 1.0
    limits: list[dict[str, Any]] = []
    for qid in module.policy_inputs:
        q = ALL_QUESTIONS[qid]
        if answers.get(qid) != "no":
            continue
        if q.effect == "confidence_penalty":
            penalty *= q.penalty
        limits.append({"question": qid, "effect": q.effect, "consequence": q.consequence,
                       "path": {"kind": "customer_action", "text": f"Customer action: {q.customer_action}"}})
    return penalty, limits


def _assess_module(
    module: Module,
    evidence: Mapping[str, ObjectEvidence],
    answers: dict[str, str],
    normalization: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    objs = []
    for oid in module.required_objects:
        ev = evidence.get(oid) or ObjectEvidence(present=False, confidence=0.0)
        spec = OBJECTS[oid]
        objs.append({
            "id": oid, "name": spec.name, "connector": spec.connector,
            "present": ev.present, "confidence": round(ev.confidence, 4) if ev.present else 0.0,
            "structural": ev.structural, "rows": ev.rows, "sources": ev.sources,
            "missing_periods": ev.missing_periods,
        })
    present = [o for o in objs if o["present"]]
    missing = [o for o in objs if not o["present"]]
    penalty, policy_limits = _policy_effects(module, answers)
    reasons: list[str] = []
    paths: list[dict[str, str]] = []

    if not missing:
        confidence = min(o["confidence"] for o in objs) * penalty
        if confidence >= module.ready_threshold:
            status = READY
        elif confidence >= module.partial_threshold:
            status = PARTIAL
            reasons.append("CONFIDENCE_BELOW_READY_THRESHOLD")
        else:
            status = UNAVAILABLE
            reasons.append("INSUFFICIENT_CONFIDENCE")
        for o in objs:
            if o["confidence"] < module.ready_threshold and o["missing_periods"]:
                paths.append({"kind": "customer_action",
                              "text": f"Customer action: load {o['name']} for "
                                      f"{', '.join(o['missing_periods'][:6])}"
                                      f"{'…' if len(o['missing_periods']) > 6 else ''}"})
    elif any(o["structural"] for o in missing):
        status = UNAVAILABLE
        confidence = 0.0
        reasons.append("STRUCTURAL_CEILING")
        for o in missing:
            if o["structural"]:
                paths.append({"kind": "structural",
                              "text": f"Platform limitation of the connected {o['connector']} system — "
                                      f"{o['name']} is not available; not resolvable by implementation"})
    else:
        status = PARTIAL
        base = min((o["confidence"] for o in present), default=0.0)
        confidence = base * len(present) / len(objs) * penalty
        reasons.append("MISSING_REQUIRED_OBJECTS")
        by_connector: dict[str, list[str]] = {}
        for o in missing:
            by_connector.setdefault(o["connector"], []).append(o["name"])
        for conn, names in by_connector.items():
            paths.append({"kind": "connector", "connector": conn,
                          "text": f"Connect {CONNECTOR_TYPES[conn]} to provide {', '.join(names)}"})

    for gid in module.gates:
        g = normalization[gid]
        if g["resolved"]:
            continue
        reasons.append("GATE_UNRESOLVED")
        paths.append({"kind": "questionnaire",
                      "text": f"Resolve the {g['name']} (questions {', '.join(g['unresolved_questions'])})"})
        if status == READY:
            status = PARTIAL

    for lim in policy_limits:
        reasons.append("POLICY_GAP")
        paths.append(lim["path"])
        if lim["effect"] == "cap_partial" and status == READY:
            status = PARTIAL

    contribution = confidence * module.weight * STATUS_FACTOR[status]
    return {
        "id": module.id,
        "name": module.name,
        "status": status,
        "reasons": list(dict.fromkeys(reasons)),
        "confidence": round(confidence, 4),
        "weight": module.weight,
        "ready_threshold": module.ready_threshold,
        "partial_threshold": module.partial_threshold,
        "contribution": round(contribution, 6),
        "required_objects": objs,
        "missing_objects": [o["id"] for o in missing],
        "policy_limits": [{k: v for k, v in lim.items() if k != "path"} for lim in policy_limits],
        "improvement_paths": paths,
    }


def _score(modules: list[dict[str, Any]]) -> float:
    total_w = sum(m["weight"] for m in modules)
    if not total_w:
        return 0.0
    return round(sum(m["contribution"] for m in modules) / total_w * 100, 1)


def _core(evidence: Mapping[str, ObjectEvidence], answers: dict[str, str]) -> tuple[list[dict[str, Any]], float]:
    normalization = _normalization_status(answers)
    modules = [_assess_module(m, evidence, answers, normalization) for m in MODULES]
    return modules, _score(modules)


def _recommendations(
    evidence: Mapping[str, ObjectEvidence],
    answers: dict[str, str],
    modules: list[dict[str, Any]],
    base_score: float,
) -> list[dict[str, Any]]:
    """CAL.6 — simulate each next step and rank by Readiness Score delta."""
    base_status = {m["id"]: m["status"] for m in modules}
    candidates: list[tuple[str, str, str, dict[str, ObjectEvidence], dict[str, str]]] = []

    missing_by_conn: dict[str, list[str]] = {}
    for oid, spec in OBJECTS.items():
        ev = evidence.get(oid)
        if (ev is None or not ev.present) and not (ev and ev.structural):
            missing_by_conn.setdefault(spec.connector, []).append(oid)
    for conn, oids in missing_by_conn.items():
        sim = dict(evidence)
        for oid in oids:
            sim[oid] = ObjectEvidence(present=True, confidence=1.0, rows=1)
        candidates.append(("connector", conn, f"Connect {CONNECTOR_TYPES[conn]}", sim, answers))

    for oid, ev in evidence.items():
        if ev.present and ev.missing_periods:
            sim = dict(evidence)
            sim[oid] = replace(ev, confidence=1.0, missing_periods=[])
            candidates.append(("customer_action", oid,
                               f"Customer action: load {OBJECTS[oid].name} for all periods "
                               f"({len(ev.missing_periods)} missing)", sim, answers))

    for gid, g in _normalization_status(answers).items():
        if g["resolved"]:
            continue
        sim_answers = dict(answers)
        for qid in g["unresolved_questions"]:
            q = ALL_QUESTIONS[qid]
            sim_answers[qid] = "resolved" if "resolved" in q.choices else q.choices[0]
        candidates.append(("questionnaire", gid, f"Resolve the {g['name']}", evidence, sim_answers))

    for q in SCORE_INPUTS:
        if answers.get(q.id) == "no":
            candidates.append(("customer_action", q.id, f"Customer action: {q.customer_action}",
                               evidence, {**answers, q.id: "yes"}))

    out = []
    for kind, ref, label, sim_ev, sim_ans in candidates:
        sim_modules, sim_score = _core(sim_ev, sim_ans)
        delta = round(sim_score - base_score, 1)
        if delta <= 0:
            continue
        unlocked = [m["name"] for m in sim_modules if m["status"] == READY and base_status[m["id"]] != READY]
        out.append({"kind": kind, "ref": ref, "label": label, "expected_delta": delta,
                    "expected_score": sim_score, "modules_to_ready": unlocked})
    out.sort(key=lambda r: (-r["expected_delta"], r["label"]))
    return out


def assess(evidence: Mapping[str, ObjectEvidence], raw_answers: Mapping[str, Any] | None) -> dict[str, Any]:
    answers = normalize_answers(raw_answers)
    gates = _gate_status(answers)
    normalization = _normalization_status(answers)
    modules, score = _core(evidence, answers)
    counts = {s: sum(1 for m in modules if m["status"] == s) for s in (READY, PARTIAL, UNAVAILABLE)}
    gate_failed = gates["status"] == "fail"
    score_inputs = [
        {"id": q.id, "prompt": q.prompt, "answer": answers.get(q.id), "effect": q.effect,
         "consequence": q.consequence, "customer_action": q.customer_action}
        for q in SCORE_INPUTS
    ]
    return {
        "readiness_score": None if gate_failed else score,
        "score_state": "not_scored" if gate_failed else "provisional" if gates["status"] == "pending" else "final",
        "gates": gates,
        "normalization_gates": list(normalization.values()),
        "score_inputs": score_inputs,
        "unanswered": [qid for qid in ALL_QUESTIONS if qid not in answers],
        "summary": {"ready": counts[READY], "partial": counts[PARTIAL], "unavailable": counts[UNAVAILABLE],
                    "modules": len(modules)},
        "modules": modules,
        "recommended_next": [] if gate_failed else _recommendations(evidence, answers, modules, score),
        "method": {
            "formula": "Σ(confidence × weight × {READY 1.0, PARTIAL 0.5, UNAVAILABLE 0}) ÷ Σ(weight) × 100",
            "confidence": "Module confidence = lowest required-object confidence × policy penalties; "
                          "object confidence = share of expected reporting periods loaded",
            "weights": "SMPL default module weights (SOF 7.2 defines the formula, not the weights)",
            "gates": "Any failed readiness gate (Section 0) stops scoring until the customer resolves it",
        },
    }
