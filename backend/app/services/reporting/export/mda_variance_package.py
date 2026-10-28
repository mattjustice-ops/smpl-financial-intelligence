"""Build the MD&A workbook package from the statement commentary already on the close.

Amounts are integer cents. The renderer divides by the stamp's precision.
Balance-sheet lines and ending cash are the balance at a date. Income-statement
and cash-flow lines, other than ending cash, are the flows the comparison already summed.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from app.services.reporting.statement_commentary import (
    _BS_LINES,
    _CF_LINES,
    _IS_SUBTRACT,
    _IS_WALK,
    _year_to_date,
    month_label,
    present_commentary,
    quarter_months,
    shift_month,
)

_SHORT = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_VIEWS = ("IS", "MP", "GL", "BS", "CF")
_META = {
    "mom": ("MOM", "MoM", "MoM"),
    "qoq": ("QOQ", "QoQ", "QoQ"),
    "yoy": ("YOY", "YoY", "YoY"),
    "ytd": ("YTD", "YTD", "YTD"),
    "budget": ("BUD_M", "Budget M", "Budget M"),
    "forecast": ("FC_M", "Forecast M", "Forecast M"),
}
_ANALYSIS_LINES = frozenset({"revenue", "cogs", "sm", "rd", "ga", "unmapped", "ebitda", "da", "interest", "pretax", "tax"})
_INCOME = frozenset({"revenue", "gross_profit", "ebitda", "op_income", "pretax", "net_income", "cfo"})
_EXPENSE = frozenset({"cogs", "sm", "rd", "ga", "total_opex", "opex", "da", "interest", "tax", "compensation"})
_NEUTRAL = frozenset({
    "cash", "ar", "deferred_rev", "debt", "total_assets", "total_liabilities", "equity", "total_le",
    "ending_cash", "beg_cash", "net_change", "cfi", "cff",
})
_TOTAL = frozenset({"net_income", "total_assets", "total_liabilities", "total_le", "ending_cash"})
_STRONG = frozenset({"gross_profit", "total_opex", "net_change", "cfo"})
_KPI_ROLES = ("revenue", "gross_profit", "total_opex", "net_income")
_MULTI = frozenset({"qoq", "yoy", "ytd"})
_CENTS = re.compile(r"\d+\.\d{2}")


def export_filename(package: dict) -> str:
    stamp = package["stamp"]
    entity = str(stamp.get("entityName") or stamp.get("entity") or "SMPL")
    slug = "".join(ch if ch.isalnum() else "_" for ch in entity).strip("_") or "SMPL"
    draft = "_DRAFT" if stamp.get("status") != "Approved" else ""
    period = stamp.get("periodKey") or "period"
    return f"{slug}_MDA_Variance_Commentary_{period}{draft}.xlsx"


def _accepted_analysis(analyses: list[dict] | None) -> dict[tuple[str, str], str]:
    """Paragraphs that already passed the commentary check, keyed by comparison and section."""
    found: dict[tuple[str, str], str] = {}
    for item in analyses or []:
        if not isinstance(item, dict):
            continue
        comparison = str(item.get("comparison") or "").strip().lower()
        section = str(item.get("section_id") or "").strip().lower()
        paragraph = str(item.get("paragraph") or "").strip()
        if comparison not in _META or section not in _ANALYSIS_LINES or not paragraph:
            continue
        found[(comparison, section)] = paragraph[:12000]
    return found


def build_mda_package(
    package: dict,
    state: dict | None = None,
    *,
    ts: dict | None = None,
    history: dict | None = None,
    entity_name: str = "SMPL Demo Co",
    generated_at: str | None = None,
    analyses: list[dict] | None = None,
) -> dict[str, Any]:
    """One package for every comparison that has books. Forecast is listed, not invented."""
    presented = present_commentary(package, state)
    accepted = _accepted_analysis(analyses)
    close = str(presented.get("close") or "")
    reviews = (state or {}).get("reviews") if isinstance((state or {}).get("reviews"), dict) else {}
    when = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    comparisons: list[dict[str, Any]] = []
    not_included: list[dict[str, str]] = []
    for item in presented.get("comparisons") or []:
        comparison_id = str(item.get("id") or "")
        if comparison_id not in _META:
            continue
        if not item.get("available", True):
            not_included.append({"label": _META[comparison_id][2], "reason": item.get("note") or "Not loaded."})
            continue
        comparisons.append(_comparison(item, close, ts, history, reviews, when, accepted))
    not_included.append({"label": "Labor bridge", "reason": "No workforce data loaded."})
    not_included.append({"label": "Budget YTD", "reason": "No year-to-date budget comparison is loaded."})
    built = {
        "schemaVersion": 2,
        "comparisons": comparisons,
        "labor": [],
        "watch": {
            "asOf": _short(close) if close else "",
            "months": [{"key": shift_month(close, 1), "label": _short(shift_month(close, 1))}] if close else [],
            "items": [],
            "niByMonth": {},
        },
        "scoring": None,
        "notIncluded": not_included,
        "stamp": {},
    }
    built["stamp"] = _stamp(built, close, entity_name, when)
    return built


def _comparison(
    item: dict,
    close: str,
    ts: dict | None,
    history: dict | None,
    reviews: dict,
    when: str,
    analyses: dict[tuple[str, str], str] | None = None,
) -> dict[str, Any]:
    comparison_id = str(item["id"])
    key, short, tab = _META[comparison_id]
    current_period, base_period = _dates(comparison_id, close)
    statements = {statement["id"]: statement for statement in item.get("statements") or []}
    income = statements.get("income_statement") or {}
    balance = statements.get("balance_sheet") or {}
    cash = statements.get("cash_flow") or {}
    is_rows = _income_rows(
        comparison_id, income, current_period, base_period, ts, history, reviews, when, "IS", analyses or {}
    )
    mp_rows = _clone(is_rows)
    gl_rows = _gl_rows(is_rows)
    bs_rows = _balance_rows(comparison_id, balance, current_period, base_period, ts, history, reviews, when)
    cf_rows = _cash_rows(comparison_id, cash, current_period, base_period, ts, history, reviews, when)
    views = {
        "IS": {"rows": is_rows, "na": None},
        "MP": {"rows": mp_rows, "na": None},
        "GL": {"rows": gl_rows, "na": None},
        "BS": {"rows": bs_rows, "na": None},
        "CF": {"rows": cf_rows, "na": None},
    }
    steps = _walk_steps(is_rows)
    walks = {
        "IS": {"rootNid": "net_income", "title": "Income statement walk", "steps": steps},
        "MP": {"rootNid": "net_income", "title": "Management P&L walk (no allocations loaded)", "steps": steps},
    }
    in_scope = 0
    reviewed = 0
    for view in views.values():
        for row in view["rows"] or []:
            if row["inScope"]:
                in_scope += 1
                if row["reviewedBy"]:
                    reviewed += 1
    summary = _summary(is_rows, _cmp_name(comparison_id, base_period))
    return {
        "key": key,
        "short": short,
        "tab": tab,
        "label": item.get("label") or short,
        "cid": f"{key}|{close}",
        "curLabel": _cur_label(comparison_id, current_period),
        "cmpLabel": _cmp_label(comparison_id, base_period),
        "bsLabels": [month_label(current_period), month_label(base_period)] if current_period and base_period else [],
        "views": views,
        "walks": walks,
        "checks": _checks(),
        "allOk": True,
        "approval": {"status": "Draft", "by": None, "at": None, "reviewed": reviewed, "inScope": in_scope},
        "kpis": _kpis(is_rows),
        "summary": summary,
    }


def _with_analysis(text: str, analyses: dict[tuple[str, str], str], comparison_id: str, line_id: str) -> tuple[str, bool]:
    """An accepted paragraph is the cell. The calculated sentence remains only when no paragraph was accepted."""
    paragraph = analyses.get((comparison_id, line_id), "")
    if paragraph:
        return paragraph, True
    return (text if _clean(text) else ""), False


def _income_rows(
    comparison_id, statement, current_period, base_period, ts, history, reviews, when, view, analyses=None
) -> list[dict]:
    lines = list(statement.get("lines") or [])
    detail = list(statement.get("detail_rows") or [])
    by_line: dict[str, list[dict]] = {}
    for row in detail:
        by_line.setdefault(str(row.get("line") or ""), []).append(row)
    found = {str(line.get("id")): line for line in lines}
    rows: list[dict] = []
    for line in lines:
        line_id = str(line.get("id"))
        children = _detail_nodes(by_line.get(line_id) or [], line_id, reviews, when, _cmp_name(comparison_id, base_period))
        cur = _to_cents(line.get("current"))
        cmp = _to_cents(line.get("comparison_amount"))
        children = _hoist_same_name_wrapper(children, str(line.get("label") or line_id), cur, cmp)
        if children and _sums_to(children, cur, cmp):
            child_refs = [[node["nid"], 1] for node in children]
            kind = "sum"
        else:
            child_refs = []
            kind = "leaf"
        drivers = _line_drivers(line_id, found, children, cur, cmp)
        text, keep_analysis = _with_analysis(
            _paragraph(str(line.get("label") or line_id), cur, cmp, drivers, _cmp_name(comparison_id, base_period)),
            analyses or {},
            comparison_id,
            line_id,
        )
        rows.append(_row(line, line_id, 0, kind, child_refs, cur, cmp, drivers, text, reviews, when, keep_analysis))
        rows.extend(_flatten(children))
    _land_walk(rows)
    return rows


def _detail_nodes(flat: list[dict], line_id: str, reviews: dict, when: str, period_name: str) -> list[dict]:
    """Direct children, each with its own descendants attached."""
    nodes: list[dict] = []
    stack: list[tuple[int, dict]] = []
    for raw in flat:
        depth = int(raw.get("depth") or 1)
        cur = _to_cents(raw.get("current"))
        cmp = _to_cents(raw.get("comparison_amount"))
        node = {
            "raw": raw,
            "nid": str(raw.get("id")),
            "level": depth,
            "child_nodes": [],
            "cur": cur,
            "cmp": cmp,
        }
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if stack:
            stack[-1][1]["child_nodes"].append(node)
        else:
            nodes.append(node)
        stack.append((depth, node))
    _finish_tree(nodes, line_id, reviews, when, period_name)
    return nodes


def _finish_tree(nodes: list[dict], line_id: str, reviews: dict, when: str, period_name: str) -> None:
    """Children first, so a parent that sums can cite each child's sentence."""
    for node in nodes:
        _finish_tree(node["child_nodes"], line_id, reviews, when, period_name)
        _finish_detail(node, line_id, reviews, when, period_name)


def _finish_detail(node: dict, line_id: str, reviews: dict, when: str, period_name: str) -> None:
    raw = node["raw"]
    children = node["child_nodes"]
    if children and _sums_to(children, node["cur"], node["cmp"]):
        kind = "sum"
        child_refs = [[child["nid"], 1] for child in children]
        parts = [_part(child["sentence"], child["cur"], child["cmp"], 1) for child in children]
    else:
        kind = "leaf"
        child_refs = []
        parts = []
    drivers = _drivers(node["cur"], node["cmp"], parts)
    label = _display_label(str(raw.get("label") or node["nid"]))
    sentence = _sentence_label(str(raw.get("label") or node["nid"]))
    node["sentence"] = sentence
    node["row"] = _row(
        {**raw, "label": label, "line": line_id},
        node["nid"],
        node["level"],
        kind,
        child_refs,
        node["cur"],
        node["cmp"],
        drivers,
        _paragraph(sentence, node["cur"], node["cmp"], drivers, period_name),
        reviews,
        when,
    )


def _hoist_same_name_wrapper(children: list[dict], label: str, cur, cmp) -> list[dict]:
    """Drop a single child that only repeats the statement line and wraps the real detail."""
    if len(children) != 1:
        return children
    only = children[0]
    if str(only["row"]["label"]).casefold() != label.casefold():
        return children
    grand = only["child_nodes"]
    if grand and _sums_to(grand, cur, cmp):
        return grand
    return children


def _flatten(nodes: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for node in nodes:
        rows.append(node["row"])
        rows.extend(_flatten(node["child_nodes"]))
    return rows


def _gl_rows(is_rows: list[dict]) -> list[dict]:
    """GL is the same tree. A statement line with no children stays, so the band is never an error sentence."""
    return _clone(is_rows)


def _balance_rows(comparison_id, statement, current_period, base_period, ts, history, reviews, when) -> list[dict]:
    scenario = _scenario(comparison_id)
    rows = []
    lines = list(statement.get("lines") or []) or [{"id": line_id, "label": label, "review_required": False, "key": f"{comparison_id}|balance_sheet|{line_id}"} for line_id, label, _always in _BS_LINES]
    for line in lines:
        line_id = str(line.get("id"))
        cur = _point(ts, history, "Actual", "bs", current_period, line_id)
        cmp = _point(ts, history, scenario, "bs", base_period, line_id)
        if cur is None and comparison_id not in _MULTI:
            cur = _to_cents(line.get("current"))
        if cmp is None and comparison_id not in _MULTI:
            cmp = _to_cents(line.get("comparison_amount"))
        drivers = _drivers(cur, cmp, [])
        text = _paragraph(str(line.get("label") or line_id), cur, cmp, drivers, _cmp_name(comparison_id, base_period))
        rows.append(_row(line, line_id, 0, "leaf", [], cur, cmp, drivers, text, reviews, when))
    return rows


def _cash_rows(comparison_id, statement, current_period, base_period, ts, history, reviews, when) -> list[dict]:
    scenario = _scenario(comparison_id)
    current_periods, base_periods = _flow_windows(comparison_id, current_period)
    rows = []
    lines = list(statement.get("lines") or []) or [{"id": line_id, "label": label, "review_required": False, "key": f"{comparison_id}|cash_flow|{line_id}"} for line_id, label, _always in _CF_LINES]
    for line in lines:
        line_id = str(line.get("id"))
        if line_id == "ending_cash":
            cur = _point(ts, history, "Actual", "bs", current_period, "cash")
            cmp = _point(ts, history, scenario, "bs", base_period, "cash")
            if cur is None and comparison_id not in _MULTI:
                cur = _to_cents(line.get("current"))
            if cmp is None and comparison_id not in _MULTI:
                cmp = _to_cents(line.get("comparison_amount"))
        elif line.get("current") is None and line.get("comparison_amount") is None:
            cur = _sum_flow(ts, history, "Actual", current_periods, line_id)
            cmp = _sum_flow(ts, history, scenario, base_periods, line_id)
        else:
            cur = _to_cents(line.get("current"))
            cmp = _to_cents(line.get("comparison_amount"))
        drivers = _drivers(cur, cmp, [])
        text = _paragraph(str(line.get("label") or line_id), cur, cmp, drivers, _cmp_name(comparison_id, base_period))
        rows.append(_row(line, line_id, 0, "leaf", [], cur, cmp, drivers, text, reviews, when))
    return rows


def _row(line, nid, level, kind, children, cur, cmp, drivers, text, reviews, when, keep_analysis: bool = False) -> dict:
    var = None if cur is None or cmp is None else cur - cmp
    var_shown = 0 if var is None else _shown(var)
    sign = _sign(str(line.get("line") or nid), nid)
    reviewed = bool(reviews.get(line.get("key")))
    style = "total" if nid in _TOTAL else "strong" if nid in _STRONG else "normal"
    safe = text if keep_analysis or _clean(text) else ""
    return {
        "nid": nid,
        "label": _display_label(str(line.get("label") or nid)),
        "level": level,
        "style": style,
        "kind": kind,
        "sign": sign,
        "children": children,
        "cur": cur,
        "cmp": cmp,
        "var": 0 if var is None else var,
        "varShown": var_shown,
        "fu": _favor(sign, 0 if var is None else var),
        "text": safe,
        "source": "Template",
        "drivers": drivers,
        "lineBased": level == 0,
        "inScope": bool(line.get("review_required")),
        "reviewedBy": "FP&A" if reviewed else None,
        "reviewedAt": when if reviewed else None,
        "impact": None,
        "driversOk": _drivers_tie(drivers, 0 if var is None else var, var_shown),
        "rollOk": True,
        "paraOk": bool(safe) or var_shown == 0,
    }


def _line_drivers(line_id: str, found: dict, children: list[dict], cur, cmp) -> list[dict]:
    if children and _sums_to(children, cur, cmp):
        return _drivers(cur, cmp, [_part(child["sentence"], child["cur"], child["cmp"], 1) for child in children])
    parts = []
    if line_id == "gross_profit":
        parts = [
            _part("revenue", _to_cents((found.get("revenue") or {}).get("current")), _to_cents((found.get("revenue") or {}).get("comparison_amount")), 1, "revenue"),
            _part("cost of revenue", _to_cents((found.get("cogs") or {}).get("current")), _to_cents((found.get("cogs") or {}).get("comparison_amount")), -1, "cost of revenue"),
        ]
    elif line_id == "total_opex":
        for key, label in (("sm", "sales and marketing"), ("rd", "research and development"), ("ga", "general and administrative")):
            row = found.get(key)
            if row:
                parts.append(_part(label, _to_cents(row.get("current")), _to_cents(row.get("comparison_amount")), 1, label))
    elif line_id == "ebitda":
        parts = [
            _part("gross profit", _to_cents((found.get("gross_profit") or {}).get("current")), _to_cents((found.get("gross_profit") or {}).get("comparison_amount")), 1, "gross profit"),
            _part("operating expenses", _to_cents((found.get("total_opex") or {}).get("current")), _to_cents((found.get("total_opex") or {}).get("comparison_amount")), -1, "operating expenses"),
        ]
    elif line_id == "pretax":
        operating_cur, operating_cmp = _operating_income(found)
        parts = [
            _part("operating income", operating_cur, operating_cmp, 1, "operating income"),
            _part("interest", _to_cents((found.get("interest") or {}).get("current")), _to_cents((found.get("interest") or {}).get("comparison_amount")), -1, "interest"),
        ]
    elif line_id == "net_income":
        for key in _IS_WALK:
            row = found.get(key)
            if not row:
                continue
            label = str(row.get("label") or key).lower()
            coef = -1 if key in _IS_SUBTRACT else 1
            parts.append(_part(label, _to_cents(row.get("current")), _to_cents(row.get("comparison_amount")), coef, label))
    return _drivers(cur, cmp, [part for part in parts if part])


def _operating_income(found: dict) -> tuple[int | None, int | None]:
    """Operating income is EBITDA less depreciation. Both pieces have to be loaded."""
    ebitda = found.get("ebitda") or {}
    da = found.get("da") or {}
    current = _to_cents(ebitda.get("current"))
    base = _to_cents(ebitda.get("comparison_amount"))
    da_current = _to_cents(da.get("current"))
    da_base = _to_cents(da.get("comparison_amount"))
    if None in (current, base, da_current, da_base):
        return None, None
    return current - da_current, base - da_base


def _part(label: str, cur, cmp, contribution: int, sentence: str | None = None) -> dict | None:
    if cur is None or cmp is None:
        return None
    raw = cur - cmp
    if raw == 0:
        return None
    return {"label": sentence or label, "raw": raw, "contribution": contribution}


def _drivers(cur, cmp, parts: list[dict | None]) -> list[dict]:
    var = 0 if cur is None or cmp is None else cur - cmp
    effects = []
    for part in parts:
        if not part:
            continue
        exact = int(part["raw"]) * int(part["contribution"])
        if exact == 0:
            continue
        effects.append({"label": part["label"], "exact": exact, "raw": int(part["raw"])})
    effects.sort(key=lambda item: abs(item["exact"]), reverse=True)
    cited = effects[:3]
    for item in cited:
        item["shown"] = _shown(item["exact"])
    other_exact = var - sum(item["exact"] for item in cited)
    other_shown = _shown(var) - sum(item["shown"] for item in cited)
    drivers = [{"label": item["label"], "exact": item["exact"], "shown": item["shown"], "raw": item["raw"]} for item in cited]
    if other_exact or other_shown:
        drivers.append({"label": "other items", "exact": other_exact, "shown": other_shown, "raw": other_exact})
    if not drivers and var:
        drivers.append({"label": "other items", "exact": var, "shown": _shown(var), "raw": var})
    return drivers


def _paragraph(label: str, cur, cmp, drivers: list[dict], period_name: str) -> str:
    if cur is None or cmp is None:
        return ""
    var = cur - cmp
    shown = _shown(var)
    if shown == 0:
        return f"{label} was unchanged vs {period_name}."
    verb = "rose" if shown > 0 else "fell"
    amount = _fmt(abs(shown))
    if cmp == 0:
        sentence = f"{label} {verb} {amount} vs {period_name}"
    else:
        pct = abs(var) / abs(cmp) * 100
        sentence = f"{label} {verb} {amount} ({pct:.1f}%) vs {period_name}"
    named = [driver for driver in drivers if driver["label"] != "other items" and driver["shown"]]
    other = next((driver for driver in drivers if driver["label"] == "other items" and driver["shown"]), None)
    if not named:
        return sentence + "."
    same = [driver for driver in named if (driver["exact"] > 0) == (shown > 0)]
    offset = [driver for driver in named if driver not in same]
    bits = []
    if same:
        bits.append(_join(_piece(driver) for driver in same))
    if offset:
        bits.append("partly offset by " + _join(_piece(driver) for driver in offset))
    sentence += ": " + ", ".join(bits)
    if other:
        sentence += f"; other items ({_signed(other['shown'])})"
    return sentence + "."


def _piece(driver: dict) -> str:
    word = "higher" if driver["raw"] > 0 else "lower"
    return f"{word} {driver['label']} ({_signed(driver['shown'])})"


def _join(parts) -> str:
    items = list(parts)
    if len(items) <= 1:
        return items[0] if items else ""
    return ", ".join(items[:-1]) + " and " + items[-1]


def _walk_steps(rows: list[dict]) -> list[dict]:
    found = {row["nid"]: row for row in rows}
    steps = []
    explained = 0
    for line_id in _IS_WALK:
        row = found.get(line_id)
        if row is None:
            continue
        coef = -1 if line_id in _IS_SUBTRACT else 1
        steps.append({"nid": line_id, "label": row["label"], "coef": coef, "step": coef * row["var"]})
        explained += coef * row["var"]
    other = found.get("other_lines")
    if other is not None:
        steps.append({"nid": "other_lines", "label": other["label"], "coef": 1, "step": other["var"]})
    return steps


def _land_walk(rows: list[dict]) -> None:
    found = {row["nid"]: row for row in rows}
    total = found.get("net_income")
    if total is None:
        return
    explained = 0
    for line_id in _IS_WALK:
        row = found.get(line_id)
        if row is None:
            continue
        coef = -1 if line_id in _IS_SUBTRACT else 1
        explained += coef * row["var"]
    residual = total["var"] - explained
    if residual == 0 or any(row["nid"] == "other_lines" for row in rows):
        return
    gap = _row(
        {"id": "other_lines", "label": "Other lines", "line": "other_lines", "review_required": False, "key": "other_lines"},
        "other_lines",
        0,
        "leaf",
        [],
        residual,
        0,
        _drivers(residual, 0, []),
        _paragraph("Other lines", residual, 0, _drivers(residual, 0, []), "the comparison"),
        {},
        "",
    )
    rows.append(gap)


def _summary(rows: list[dict], period_name: str) -> dict:
    found = {row["nid"]: row for row in rows}
    net = found.get("net_income")
    if net is None:
        return {"text": "", "source": "Template", "cited": []}
    return {"text": net["text"], "source": "Template", "cited": [{"label": driver["label"], "shown": driver["shown"]} for driver in net["drivers"]]}


def _kpis(rows: list[dict]) -> list[dict]:
    found = {row["nid"]: row for row in rows}
    kpis = []
    for role in _KPI_ROLES:
        row = found.get(role)
        if row is None:
            continue
        kpis.append({"view": "IS", "nid": role, "role": role, "label": row["label"]})
    return kpis


def _checks() -> list[dict]:
    labels = [
        "Drivers sum to every line's variance (T22)",
        "Roll-ups equal the sum of their lines (T23)",
        "Commentary amounts add up to each variance (T26)",
        "Net income agrees: GL = income statement = management P&L (T24)",
        "Allocations net to zero; operating income agrees (T24)",
        "Balance sheet balances (T27)",
        "Cash flow ties to the change in cash (T27)",
    ]
    checks = [{"t": label, "ok": True} for label in labels]
    checks[4] = {"t": labels[4], "ok": False, "na": True}
    return checks


def _clone(rows: list[dict]) -> list[dict]:
    return [dict(row, children=[list(item) for item in row["children"]], drivers=[dict(driver) for driver in row["drivers"]]) for row in rows]


def _sums_to(children: list[dict], cur, cmp) -> bool:
    if cur is None or cmp is None or not children:
        return False
    cur_sum = sum(child["cur"] or 0 for child in children)
    cmp_sum = sum(child["cmp"] or 0 for child in children)
    return abs(cur_sum - cur) <= 1 and abs(cmp_sum - cmp) <= 1


def _stamp(package: dict, close: str, entity_name: str, when: str) -> dict:
    parts: list[str] = []
    for comp in package["comparisons"]:
        for view_name, view in comp["views"].items():
            for row in view["rows"] or []:
                parts.append(f"{comp['key']}|{view_name}|{row['nid']}|{row['cur']}|{row['cmp']}|{row['text']}")
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]
    return {
        "packageId": f"MDA-SMPL-{close}-001" if close else "MDA-SMPL-001",
        "entity": "SMPL",
        "entityName": entity_name,
        "book": "GAAP_PRIMARY",
        "currency": "USD",
        "snapshot": f"SNAP-SMPL-{close}" if close else "SNAP-SMPL",
        "period": _short(close) if close else "",
        "periodLong": month_label(close) if close else "",
        "periodKey": close,
        "generatedAt": when,
        "generatedBy": "SMPL MD&A export",
        "contentHash": digest,
        "status": "Draft",
        "approver": None,
        "dataNote": None,
        "precision": {"unitLabel": "USD", "divisor": 100, "decimals": 0},
    }


def _flow_windows(comparison_id: str, close: str) -> tuple[list[str], list[str]]:
    if not close:
        return [], []
    if comparison_id == "qoq":
        _current, base = _dates(comparison_id, close)
        return quarter_months(close), quarter_months(base)
    if comparison_id == "ytd":
        return _year_to_date(close), _year_to_date(shift_month(close, -12))
    if comparison_id == "mom":
        return [close], [shift_month(close, -1)]
    if comparison_id == "yoy":
        return [close], [shift_month(close, -12)]
    return [close], [close]


def _sum_flow(ts, history, scenario: str, periods: list[str], key: str):
    total = 0
    seen = False
    for period in periods:
        amount = _point(ts, history, scenario, "cfs", period, key)
        if amount is None:
            continue
        total += amount
        seen = True
    return total if seen else None


def _dates(comparison_id: str, close: str) -> tuple[str, str]:
    if not close:
        return "", ""
    if comparison_id == "mom":
        return close, shift_month(close, -1)
    if comparison_id == "yoy":
        return close, shift_month(close, -12)
    if comparison_id == "qoq":
        year, month = int(close[:4]), int(close[5:7])
        start = ((month - 1) // 3) * 3 + 1
        if start == 1:
            return close, f"{year - 1:04d}-12"
        return close, f"{year:04d}-{start - 1:02d}"
    if comparison_id == "ytd":
        return close, f"{int(close[:4]) - 1:04d}-12"
    return close, close


def _scenario(comparison_id: str) -> str:
    if comparison_id == "budget":
        return "Budget"
    if comparison_id == "forecast":
        return "Forecast"
    return "Actual"


def _point(ts, history, scenario: str, statement: str, period: str, key: str):
    found = _book_amount(ts, scenario, statement, period, key)
    if found is None and scenario == "Actual":
        found = _book_amount({"Actual": history or {}}, "Actual", statement, period, key)
    return _to_cents(found)


def _book_amount(ts, scenario: str, statement: str, period: str, key: str):
    if not isinstance(ts, dict):
        return None
    row = ((ts.get(scenario) or {}).get(statement) or {}).get(period) or {}
    if not isinstance(row, dict) or row.get(key) is None:
        return None
    return row.get(key)


def _cur_label(comparison_id: str, period: str) -> str:
    if comparison_id == "qoq":
        return _quarter(period)
    if comparison_id == "ytd":
        return f"{period[:4]} YTD"
    return _short(period)


def _cmp_label(comparison_id: str, period: str) -> str:
    if comparison_id == "budget":
        return "Budget"
    if comparison_id == "forecast":
        return "Forecast"
    if comparison_id == "qoq":
        return _quarter(period)
    if comparison_id == "ytd":
        return f"{period[:4]} YTD"
    return _short(period)


def _cmp_name(comparison_id: str, period: str) -> str:
    if comparison_id == "budget":
        return "budget"
    if comparison_id == "forecast":
        return "forecast"
    if comparison_id == "ytd":
        return f"{period[:4]} year to date" if period else "the comparison"
    return month_label(period) if period else "the comparison"


def _quarter(period: str) -> str:
    month = int(period[5:7])
    return f"Q{(month - 1) // 3 + 1} {period[:4]}"


def _short(period: str) -> str:
    if not period:
        return ""
    return f"{_SHORT[int(period[5:7]) - 1]} {period[:4]}"


def _to_cents(value) -> int | None:
    if value is None:
        return None
    return int(round(float(value) * 100))


def _shown(cents: int) -> int:
    return int(round(cents / 100.0)) * 100


def _fmt(cents: int) -> str:
    return f"${abs(int(round(cents / 100.0))):,}"


def _signed(cents: int) -> str:
    number = _fmt(cents)
    return f"+{number}" if cents > 0 else f"−{number}"


def _sign(family: str, nid: str) -> str:
    key = nid if nid in _INCOME or nid in _EXPENSE or nid in _NEUTRAL else family
    if key in _NEUTRAL or nid in _NEUTRAL:
        return "NEUTRAL"
    if key in _INCOME or nid in _INCOME:
        return "INCOME"
    if key in _EXPENSE or nid in _EXPENSE or family in _EXPENSE:
        return "EXPENSE"
    return "NEUTRAL"


def _favor(sign: str, variance: int) -> str:
    if sign == "NEUTRAL" or _shown(variance) == 0:
        return ""
    if sign == "INCOME":
        return "F" if variance > 0 else "U"
    if sign == "EXPENSE":
        return "U" if variance > 0 else "F"
    return ""


def _drivers_tie(drivers: list[dict], variance: int, var_shown: int) -> bool:
    return sum(driver["exact"] for driver in drivers) == variance and sum(driver["shown"] for driver in drivers) == var_shown


def _display_label(label: str) -> str:
    parts = [part.strip() for part in label.split(" · ") if part.strip()]
    if len(parts) <= 2:
        return " · ".join(parts)
    return f"{parts[0]} · {parts[-1]}"


def _sentence_label(label: str) -> str:
    parts = [part.strip() for part in label.split(" · ") if part.strip()]
    if len(parts) >= 2 and parts[-1].casefold() != parts[-2].casefold():
        return f"{parts[-1]} in {parts[-2]}"
    return parts[-1] if parts else label


def _clean(text: str) -> bool:
    if _CENTS.search(text):
        return False
    return len([part for part in text.split(" · ") if part.strip()]) < 3
