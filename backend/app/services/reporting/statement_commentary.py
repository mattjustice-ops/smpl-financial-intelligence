"""Statement commentary for the close month.

The paragraph above a statement is built from that statement's lines. The overview
reads those paragraphs in order. Account and department rows are filled only where
both sides of the comparison have the operating-expense account. A missing side stays
blank. Compensation, for month over month and versus budget, cites the saved labor
bridge as hires, departures, and everything else.
"""

from __future__ import annotations

import re
from typing import Any

REVIEW_CUTOFF = 10_000.0
_ABSENT = object()
_DOLLAR = re.compile(r"\$([0-9][0-9,]*(?:\.\d+)?)")

_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

# (id, label, always reviewed, statement key)
_IS_LINES = (
    ("revenue", "Revenue", True),
    ("cogs", "Cost of revenue", False),
    ("gross_profit", "Gross profit", True),
    ("sm", "Sales and marketing", False),
    ("rd", "Research and development", False),
    ("ga", "General and administrative", False),
    ("total_opex", "Operating expenses", True),
    ("ebitda", "EBITDA", False),
    ("da", "Depreciation and amortization", False),
    ("interest", "Interest", False),
    ("pretax", "Pretax income", False),
    ("tax", "Tax", False),
    ("net_income", "Net income", True),
)
_IS_WALK = ("revenue", "cogs", "total_opex", "da", "interest", "tax")
_IS_SUBTRACT = frozenset({"cogs", "total_opex", "da", "interest", "tax"})

_BS_LINES = (
    ("cash", "Cash", True),
    ("ar", "Accounts receivable", False),
    ("deferred_rev", "Deferred revenue", False),
    ("debt", "Debt", False),
    ("total_assets", "Total assets", True),
    ("total_liabilities", "Total liabilities", True),
    ("total_le", "Total liabilities and equity", False),
)
_BS_PARAGRAPH = ("cash", "total_assets", "total_liabilities")

_CF_LINES = (
    ("cfo", "Operating cash flow", True),
    ("cfi", "Investing cash flow", False),
    ("cff", "Financing cash flow", False),
    ("net_change", "Net change in cash", True),
    ("ending_cash", "Ending cash", True),
)
_CF_WALK = ("cfo", "cfi", "cff")

_DETAIL_COMPARISONS = frozenset({"mom", "budget"})


def _parts(period: str) -> tuple[int, int]:
    year, month = period.split("-")
    return int(year), int(month)


def _year_to_date(period: str) -> list[str]:
    year, month = _parts(period)
    return [_period(year, index) for index in range(1, month + 1)]


def _period(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def shift_month(period: str, delta: int) -> str:
    year, month = _parts(period)
    month += delta
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return _period(year, month)


def month_label(period: str) -> str:
    year, month = _parts(period)
    return f"{_MONTHS[month - 1]} {year}"


def short_stamp(period: str) -> str:
    year, month = _parts(period)
    return f"{_MONTHS[month - 1]} {year % 100:02d}"


def comparison_label(comparison_id: str, close: str) -> str:
    """Button label for a discussion comparison. YTD uses a two-digit year."""
    year_ago = shift_month(close, -12)
    if comparison_id == "ytd":
        return f"YTD {short_stamp(close)} vs YTD {short_stamp(year_ago)}"
    if comparison_id == "budget":
        return f"{month_label(close)} vs budget"
    if comparison_id == "forecast":
        return f"{month_label(close)} vs forecast"
    prior = shift_month(close, -1)
    if comparison_id == "mom":
        return f"{month_label(prior)} to {month_label(close)}"
    if comparison_id == "yoy":
        return f"{month_label(year_ago)} to {month_label(close)}"
    last_quarter = quarter_months(shift_month(quarter_months(close)[0], -1))
    return f"{quarter_label(last_quarter[-1])} to {quarter_label(close)}"


def quarter_months(period: str) -> list[str]:
    year, month = _parts(period)
    start = ((month - 1) // 3) * 3 + 1
    return [_period(year, start + offset) for offset in range(3)]


def quarter_label(period: str) -> str:
    year, month = _parts(period)
    return f"Q{(month - 1) // 3 + 1} {year}"


def money(amount: float) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.2f}"


def _moved(label: str, variance: float | None) -> str:
    if variance is None:
        return f"{label} has no comparison amount."
    if abs(variance) < 0.005:
        return f"{label} was unchanged."
    verb = "rose" if variance > 0 else "fell"
    return f"{label} {verb} {money(abs(variance))}."


def _and(parts: list[str]) -> str:
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def _explain(label: str, variance: float | None, parts: list[tuple[str, float]]) -> tuple[str, list[float]]:
    """Say what moved, then the drivers that add up to that move."""
    lead = _moved(label, variance)
    useful = [(name, effect) for name, effect in parts if abs(effect) >= 0.5]
    if variance is None or abs(variance) < 0.005 or not useful:
        return lead, []
    if abs(round(sum(effect for _, effect in useful), 2) - variance) > 1:
        return lead, []
    same = sorted((item for item in useful if (item[1] > 0) == (variance > 0)), key=lambda item: abs(item[1]), reverse=True)
    opposite = sorted((item for item in useful if (item[1] > 0) != (variance > 0)), key=lambda item: abs(item[1]), reverse=True)
    chosen = same[:3]
    if opposite:
        chosen.append(opposite[0])
    cited = [effect for _, effect in chosen]
    rest = round(variance - sum(cited), 2)

    def clause(name: str, effect: float) -> str:
        return f"{'higher' if effect > 0 else 'lower'} {name} ({money(effect)})"

    text = lead[:-1] + " because " + _and([clause(name, effect) for name, effect in chosen])
    if abs(rest) >= 0.5:
        text += f"; other items ({money(rest)})"
        cited.append(rest)
    return text + ".", cited


def _round(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _row(block: dict | None, statement: str, period: str) -> Any:
    rows = (block or {}).get(statement) or {}
    if not isinstance(rows, dict) or period not in rows:
        return _ABSENT
    row = rows.get(period)
    return row if isinstance(row, dict) else {}


def _value(row: Any, key: str) -> float | None:
    if row is _ABSENT or not isinstance(row, dict) or key not in row:
        return None
    return _round(row.get(key))


def _actual(ts: dict, history: dict | None, statement: str, period: str, key: str) -> float | None:
    row = _row((ts or {}).get("Actual"), statement, period)
    if row is _ABSENT:
        row = _row(history, statement, period)
    return _value(row, key)


def _scenario_value(ts: dict, scenario: str, statement: str, period: str, key: str) -> float | None:
    return _value(_row((ts or {}).get(scenario), statement, period), key)


def _sum(values: list[float | None]) -> float | None:
    if any(value is None for value in values):
        return None
    return round(sum(value or 0.0 for value in values), 2)


def _window_amount(statement: str, key: str, periods: list[str], read_one) -> float | None:
    """Flows add up. A balance is the period-end figure, and an opening balance is the first month."""
    if not periods:
        return None
    if statement == "bs" or key == "ending_cash":
        return read_one(periods[-1])
    if key in {"beg_cash", "beginning_cash"}:
        return read_one(periods[0])
    return _sum([read_one(period) for period in periods])


def _amounts(*values: float | None) -> list[float]:
    found: list[float] = []
    for value in values:
        if value is None:
            continue
        rounded = round(float(value), 2)
        for item in (rounded, abs(rounded)):
            if item not in found:
                found.append(item)
    return found


def _line(
    *,
    comparison: str,
    statement: str,
    line_id: str,
    label: str,
    current: float | None,
    base: float | None,
    always: bool,
    suffix: str = "",
) -> dict[str, Any] | None:
    if current is None and base is None:
        return None
    variance = None if current is None or base is None else round(current - base, 2)
    review = bool(always or (variance is not None and abs(variance) >= REVIEW_CUTOFF))
    key = f"{comparison}|{statement}|{line_id}"
    return {
        "id": line_id,
        "label": label,
        "current": current,
        "comparison_amount": base,
        "variance": variance,
        "commentary": _moved(label, variance) + suffix,
        "review_required": review,
        "key": key,
        "amounts": _amounts(current, base, variance),
    }


def _compensation_sentence(bridge: dict) -> tuple[str, list[float], bool]:
    if not bridge.get("available", True):
        reason = str(bridge.get("reason") or "The compensation bridge is not available.")
        return reason, [], True
    bars = [bar for bar in (bridge.get("bars") or []) if isinstance(bar, dict)]
    hires = round(sum(float(bar.get("amount") or 0) for bar in bars if bar.get("id") == "hires"), 2)
    departures = round(
        sum(float(bar.get("amount") or 0) for bar in bars if bar.get("id") == "departures"),
        2,
    )
    origin = bridge.get("from") if isinstance(bridge.get("from"), dict) else {}
    ending = bridge.get("to") if isinstance(bridge.get("to"), dict) else {}
    start = _round(origin.get("total"))
    close_total = _round(ending.get("total"))
    if start is None or close_total is None:
        return "The compensation bridge has no beginning and ending totals.", [], False
    change = round(close_total - start, 2)
    rest = round(change - hires - departures, 2)
    if abs(change) < 0.005:
        lead = "Compensation was unchanged."
    else:
        verb = "rose" if change > 0 else "fell"
        lead = f"Compensation {verb} {money(abs(change))} because of hires {money(hires)}, departures {money(departures)}, and everything else {money(rest)}."
    text = lead if abs(change) >= 0.005 else (
        f"{lead} Hires {money(hires)}. Departures {money(departures)}. Everything else {money(rest)}."
    )
    amounts = _amounts(change, hires, departures, rest, start, close_total)
    tied = abs((hires + departures + rest) - change) < 0.01
    return text, amounts, tied


def _opex(ts: dict, scenario: str, period: str) -> dict[str, float] | None:
    block = (ts or {}).get(scenario) or {}
    gl = block.get("gl_opex")
    if not isinstance(gl, dict) or period not in gl:
        return None
    raw = gl.get(period)
    if not isinstance(raw, dict):
        return None
    out: dict[str, float] = {}
    for key, amount in raw.items():
        number = _round(amount)
        if number is None:
            continue
        out[str(key)] = number
    return out


def _split_key(key: str) -> tuple[str, str, str] | None:
    parts = key.split("|")
    if len(parts) < 3:
        return None
    line, department, account = parts[0], parts[1], "|".join(parts[2:])
    if not line:
        return None
    return line, department or "Unassigned", account or "Unassigned"


def _account_rows(
    comparison: str,
    statement: str,
    current_map: dict[str, float],
    base_map: dict[str, float],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    keys = sorted(set(current_map) | set(base_map))
    accounts: list[dict[str, Any]] = []
    by_dept: dict[str, list[dict[str, Any]]] = {}
    for key in keys:
        parsed = _split_key(key)
        if parsed is None:
            continue
        _line_name, department, account = parsed
        current = current_map.get(key)
        base = base_map.get(key)
        if current is None or base is None:
            variance = None
            commentary = "No comparison amount."
        else:
            variance = round(current - base, 2)
            commentary = _moved(account, variance)
        row = {
            "id": key,
            "label": account,
            "department": department,
            "line": _line_name,
            "current": current,
            "comparison_amount": base,
            "variance": variance,
            "commentary": commentary,
            "review_required": variance is not None and abs(variance) >= REVIEW_CUTOFF,
            "key": f"{comparison}|{statement}|{department}|{account}",
            "amounts": _amounts(current, base, variance),
        }
        accounts.append(row)
        by_dept.setdefault(department, []).append(row)
    departments: list[dict[str, Any]] = []
    for department in sorted(by_dept):
        rows = by_dept[department]
        incomplete = any(row["variance"] is None for row in rows)
        if incomplete:
            current = base = variance = None
            commentary = "Department comparison is incomplete."
        else:
            current = round(sum(row["current"] or 0 for row in rows), 2)
            base = round(sum(row["comparison_amount"] or 0 for row in rows), 2)
            variance = round(current - base, 2)
            commentary = _moved(department, variance)
        departments.append(
            {
                "id": department,
                "label": department,
                "department": department,
                "current": current,
                "comparison_amount": base,
                "variance": variance,
                "commentary": commentary,
                "review_required": variance is not None and abs(variance) >= REVIEW_CUTOFF,
                "key": f"{comparison}|{statement}|dept|{department}",
                "amounts": _amounts(current, base, variance),
            }
        )
    note = ""
    if not accounts:
        note = "No operating-expense accounts for these months."
    return departments, accounts, note


def _rollup_tree(ts: dict, scenario: str, period: str) -> dict[str, Any] | None:
    block = (ts or {}).get(scenario) or {}
    bag = block.get("gl_rollup")
    if not isinstance(bag, dict):
        return None
    tree = bag.get(period)
    if not isinstance(tree, dict) or not isinstance(tree.get("lines"), list):
        return None
    return tree


def _rollup_line(tree: dict[str, Any] | None, key: str) -> dict[str, Any] | None:
    if not tree:
        return None
    if key in {"sm", "rd", "ga", "undivided"}:
        opex = _rollup_line(tree, "opex")
        for child in (opex or {}).get("children") or []:
            if isinstance(child, dict) and child.get("line_key") == key:
                return child
        return None
    for line in tree.get("lines") or []:
        if isinstance(line, dict) and (line.get("line_key") == key or line.get("statement_line") == key):
            return line
    return None


def _zip_rollup(
    current: list[Any] | None,
    base: list[Any] | None,
    depth: int,
    comparison: str,
    line_key: str,
) -> list[dict[str, Any]]:
    cur_map: dict[str, dict[str, Any]] = {}
    base_map: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for side, target in ((current, cur_map), (base, base_map)):
        for node in side or []:
            if not isinstance(node, dict) or not node.get("id"):
                continue
            node_id = str(node["id"])
            if node_id not in target:
                target[node_id] = node
            if node_id not in order and target is cur_map:
                order.append(node_id)
    for node_id in base_map:
        if node_id not in order:
            order.append(node_id)
    rows: list[dict[str, Any]] = []
    for node_id in order:
        cur = cur_map.get(node_id) or {}
        bas = base_map.get(node_id) or {}
        label = str(cur.get("label") or bas.get("label") or "Line")
        current_amount = _round(cur.get("amount")) if node_id in cur_map else None
        base_amount = _round(bas.get("amount")) if node_id in base_map else None
        variance = None if current_amount is None or base_amount is None else round(current_amount - base_amount, 2)
        children = _zip_rollup(cur.get("children"), bas.get("children"), depth + 1, comparison, line_key)
        direct = [row for row in children if row["depth"] == depth + 1 and row.get("variance") is not None]
        commentary, cited = _explain(label, variance, [(row["label"], float(row["variance"])) for row in direct])
        rows.append(
            {
                "id": node_id,
                "label": label,
                "depth": depth,
                "line": line_key,
                "current": current_amount,
                "comparison_amount": base_amount,
                "variance": variance,
                "commentary": commentary,
                "review_required": variance is not None and abs(variance) >= REVIEW_CUTOFF,
                "key": f"{comparison}|income_statement|rollup|{node_id}",
                "amounts": _amounts(current_amount, base_amount, variance, *cited),
            }
        )
        rows.extend(children)
    return rows


def _rollup_detail_rows(comparison: str, current_tree: dict[str, Any], base_tree: dict[str, Any]) -> list[dict[str, Any]]:
    """Children of each statement line, in the same order as the reporting grid."""
    function_keys = ("sm", "rd", "ga", "undivided")
    has_functions = any(_rollup_line(current_tree, key) or _rollup_line(base_tree, key) for key in function_keys)
    keys = ("revenue", "cogs", *function_keys, "da", "interest", "tax") if has_functions else ("revenue", "cogs", "opex", "da", "interest", "tax")
    rows: list[dict[str, Any]] = []
    for key in keys:
        current = _rollup_line(current_tree, key)
        base = _rollup_line(base_tree, key)
        current_children = (current or {}).get("children") or []
        base_children = (base or {}).get("children") or []
        if not current_children and not base_children:
            continue
        line_key = {"undivided": "unmapped", "opex": "total_opex"}.get(key, key)
        rows.extend(_zip_rollup(current_children, base_children, 1, comparison, line_key))
    return rows


def _statement_rows(statement: dict[str, Any]) -> list[dict[str, Any]]:
    return (
        list(statement.get("lines") or [])
        + list(statement.get("departments") or [])
        + list(statement.get("accounts") or [])
        + list(statement.get("detail_rows") or [])
    )


def _statement_lines(
    comparison: str,
    statement: str,
    spec: tuple[tuple[str, str, bool], ...],
    current_of,
    base_of,
) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for line_id, label, always in spec:
        built = _line(
            comparison=comparison,
            statement=statement,
            line_id=line_id,
            label=label,
            current=current_of(line_id),
            base=base_of(line_id),
            always=always,
        )
        if built is not None:
            lines.append(built)
    return lines


def _by_id(lines: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {line["id"]: line for line in lines}


def _income_tie(lines: list[dict[str, Any]]) -> tuple[bool, str]:
    found = _by_id(lines)
    total = found.get("net_income")
    if total is None or total.get("variance") is None:
        return False, "Net income has no comparison amount."
    explained = 0.0
    missing: list[str] = []
    for line_id in _IS_WALK:
        line = found.get(line_id)
        if line is None or line.get("variance") is None:
            missing.append(line["label"] if line else line_id)
            continue
        sign = -1.0 if line_id in _IS_SUBTRACT else 1.0
        explained += sign * float(line["variance"])
    if missing:
        return False, "Not loaded, so the lines cannot equal net income: " + ", ".join(missing) + "."
    if abs(explained - float(total["variance"])) >= 1:
        return False, "The lines do not equal the net income change."
    return (
        True,
        "Revenue, cost of revenue, operating expenses, and the lines below operating income equal the net income change. Gross profit is not added again.",
    )


def _cash_tie(lines: list[dict[str, Any]]) -> tuple[bool, str]:
    found = _by_id(lines)
    total = found.get("net_change")
    if total is None or total.get("variance") is None:
        return False, "Net change in cash has no comparison amount."
    explained = 0.0
    missing: list[str] = []
    for line_id in _CF_WALK:
        line = found.get(line_id)
        if line is None or line.get("variance") is None:
            missing.append(line["label"] if line else line_id)
            continue
        explained += float(line["variance"])
    if missing:
        return False, "Not loaded, so the cash lines cannot equal the net change: " + ", ".join(missing) + "."
    if abs(explained - float(total["variance"])) >= 1:
        return False, "Operating, investing, and financing cash flow do not equal the net change in cash."
    return True, "Operating, investing, and financing cash flow equal the net change in cash. Ending cash is the balance, not part of that sum."


def _balance_tie(lines: list[dict[str, Any]]) -> tuple[bool, str]:
    found = _by_id(lines)
    assets = found.get("total_assets")
    total_le = found.get("total_le")
    if assets and total_le and assets.get("variance") is not None and total_le.get("variance") is not None:
        if abs(float(assets["variance"]) - float(total_le["variance"])) >= 1:
            return False, "The change in total assets does not equal the change in liabilities and equity."
    return True, "Each amount is that line's own change."


def _effect(lines: list[dict[str, Any]], line_id: str, sign: float) -> float | None:
    row = _by_id(lines).get(line_id)
    if row is None or row.get("variance") is None:
        return None
    return round(sign * float(row["variance"]), 2)


def _operating_effect(lines: list[dict[str, Any]]) -> float | None:
    ebitda = _effect(lines, "ebitda", 1)
    depreciation = _effect(lines, "da", -1)
    if ebitda is None or depreciation is None:
        return None
    return round(ebitda + depreciation, 2)


def _named_parts(lines: list[dict[str, Any]], spec: tuple[tuple[str, str, float], ...]) -> list[tuple[str, float]]:
    parts: list[tuple[str, float]] = []
    for line_id, name, sign in spec:
        effect = _effect(lines, line_id, sign)
        if effect is not None:
            parts.append((name, effect))
    return parts


def _apply_reasons(statement_id: str, lines: list[dict[str, Any]], accounts: list[dict[str, Any]]) -> None:
    """Replace a total's sentence with the lines that caused it, when those lines add up."""
    plans: dict[str, list[tuple[str, float]]] = {}
    if statement_id == "income_statement":
        plans["gross_profit"] = _named_parts(lines, (("revenue", "revenue", 1), ("cogs", "cost of revenue", -1)))
        plans["total_opex"] = _named_parts(
            lines,
            (
                ("sm", "sales and marketing", 1),
                ("rd", "research and development", 1),
                ("ga", "general and administrative", 1),
            ),
        )
        plans["ebitda"] = _named_parts(lines, (("gross_profit", "gross profit", 1), ("total_opex", "operating expenses", -1)))
        operating = _operating_effect(lines)
        pretax_parts = [("operating income", operating)] if operating is not None else []
        interest_effect = _effect(lines, "interest", -1)
        if interest_effect is not None:
            pretax_parts.append(("interest", interest_effect))
        plans["pretax"] = pretax_parts
        plans["net_income"] = _named_parts(
            lines,
            (
                ("revenue", "revenue", 1),
                ("cogs", "cost of revenue", -1),
                ("total_opex", "operating expenses", -1),
                ("da", "depreciation and amortization", -1),
                ("interest", "interest", -1),
                ("tax", "tax", -1),
            ),
        )
        for line_id in ("sm", "rd", "ga"):
            plans[line_id] = [
                (f"{row['label']} in {row['department']}", float(row["variance"]))
                for row in accounts
                if row.get("line") == line_id and row.get("variance") is not None
            ]
    elif statement_id == "cash_flow":
        plans["net_change"] = _named_parts(
            lines,
            (("cfo", "operating cash flow", 1), ("cfi", "investing cash flow", 1), ("cff", "financing cash flow", 1)),
        )
    for row in lines:
        parts = plans.get(str(row.get("id")))
        if not parts:
            continue
        text, cited = _explain(str(row.get("label") or ""), row.get("variance"), parts)
        if " because " not in text:
            continue
        row["commentary"] = text
        row["amounts"] = _amounts(*(list(row.get("amounts") or []) + cited))


def _paragraph(lines: list[dict[str, Any]], line_ids: tuple[str, ...] | list[str], extras: list[str]) -> str:
    found = _by_id(lines)
    parts = [found[line_id]["commentary"] for line_id in line_ids if line_id in found]
    parts.extend(found[line_id]["commentary"] for line_id in extras if line_id in found)
    return " ".join(parts)


def _build_statement(
    *,
    comparison: str,
    statement: str,
    title: str,
    spec: tuple[tuple[str, str, bool], ...],
    current_of,
    base_of,
    paragraph_ids: tuple[str, ...],
    extra_ids: list[str],
    tie,
    accounts_note: str,
    departments: list[dict[str, Any]] | None = None,
    accounts: list[dict[str, Any]] | None = None,
    detail_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    lines = _statement_lines(comparison, statement, spec, current_of, base_of)
    _apply_reasons(statement, lines, accounts or [])
    present_ids = [line_id for line_id in paragraph_ids if any(line["id"] == line_id for line in lines)]
    tied, tie_note = tie(lines)
    return {
        "id": statement,
        "title": title,
        "lines": lines,
        "paragraph_line_ids": present_ids,
        "extra_line_ids": [line_id for line_id in extra_ids if any(line["id"] == line_id for line in lines)],
        "paragraph": _paragraph(lines, present_ids, extra_ids),
        "ties": tied,
        "tie_note": tie_note,
        "departments": departments or [],
        "accounts": accounts or [],
        "detail_rows": detail_rows or [],
        "accounts_note": accounts_note,
    }


def _bridge_for(bridges: list | None, comparison: str) -> dict | None:
    for bridge in bridges or []:
        if isinstance(bridge, dict) and bridge.get("id") == comparison:
            return bridge
    return None


def _comparison_statements(
    *,
    comparison: str,
    ts: dict,
    history: dict | None,
    current_periods: list[str],
    base_periods: list[str],
    base_scenario: str,
    bridges: list | None,
    detail: bool,
) -> list[dict[str, Any]]:
    def current_is(key: str) -> float | None:
        return _sum([_actual(ts, history, "is", period, key) for period in current_periods])

    def base_is(key: str) -> float | None:
        if base_scenario == "Actual":
            values = [_actual(ts, history, "is", period, key) for period in base_periods]
        else:
            values = [_scenario_value(ts, base_scenario, "is", period, key) for period in base_periods]
        return _sum(values)

    def current_stmt(statement: str):
        def read(key: str) -> float | None:
            return _window_amount(
                statement,
                key,
                current_periods,
                lambda period: _actual(ts, history, statement, period, key),
            )

        return read

    def base_stmt(statement: str):
        def read(key: str) -> float | None:
            def one(period: str) -> float | None:
                if base_scenario == "Actual":
                    return _actual(ts, history, statement, period, key)
                return _scenario_value(ts, base_scenario, statement, period, key)

            return _window_amount(statement, key, base_periods, one)

        return read

    income_lines_spec = _IS_LINES
    extra = ["gross_profit"]
    accounts_note = "Account and department detail is not used on this comparison."
    departments: list[dict[str, Any]] = []
    accounts: list[dict[str, Any]] = []
    detail_rows: list[dict[str, Any]] = []
    if detail and len(current_periods) == 1 and len(base_periods) == 1:
        base_scenario_name = "Actual" if base_scenario == "Actual" else base_scenario
        current_tree = _rollup_tree(ts, "Actual", current_periods[0])
        base_tree = _rollup_tree(ts, base_scenario_name, base_periods[0])
        if current_tree is not None and base_tree is not None:
            detail_rows = _rollup_detail_rows(comparison, current_tree, base_tree)
            accounts_note = ""
            accounts = [
                {
                    "label": row["label"],
                    "department": row["label"],
                    "line": row["line"],
                    "variance": row["variance"],
                }
                for row in detail_rows
                if row["depth"] == 1 and row["line"] in {"sm", "rd", "ga"} and row.get("variance") is not None
            ]
        else:
            current_map = _opex(ts, "Actual", current_periods[0])
            base_map = _opex(ts, base_scenario_name, base_periods[0])
            if current_map is None or base_map is None:
                accounts_note = "Account and department detail is not loaded."
            else:
                departments, accounts, accounts_note = _account_rows(comparison, "income_statement", current_map, base_map)

    income = _build_statement(
        comparison=comparison,
        statement="income_statement",
        title="Income statement",
        spec=income_lines_spec,
        current_of=current_is,
        base_of=base_is,
        paragraph_ids=_IS_WALK + ("net_income",),
        extra_ids=extra,
        tie=_income_tie,
        accounts_note=accounts_note,
        departments=departments,
        accounts=accounts,
        detail_rows=detail_rows,
    )
    bridge = _bridge_for(bridges, comparison) if comparison in _DETAIL_COMPARISONS else None
    if bridge is not None:
        text, amounts, parts_tie = _compensation_sentence(bridge)
        comp_current = None
        comp_base = None
        if bridge.get("available", True):
            origin = bridge.get("from") if isinstance(bridge.get("from"), dict) else {}
            ending = bridge.get("to") if isinstance(bridge.get("to"), dict) else {}
            comp_base = _round(origin.get("total"))
            comp_current = _round(ending.get("total"))
        variance = None
        if comp_current is not None and comp_base is not None:
            variance = round(comp_current - comp_base, 2)
        compensation = {
            "id": "compensation",
            "label": "Compensation",
            "current": comp_current,
            "comparison_amount": comp_base,
            "variance": variance,
            "commentary": text,
            "review_required": True,
            "key": f"{comparison}|income_statement|compensation",
            "amounts": amounts,
            "parts_tie": parts_tie,
        }
        income["lines"].append(compensation)
        income["extra_line_ids"].append("compensation")
        income["paragraph"] = _paragraph(income["lines"], income["paragraph_line_ids"], income["extra_line_ids"])
        if not parts_tie:
            income["ties"] = False
            income["tie_note"] = "The compensation sentence does not add up to the compensation change."

    balance = _build_statement(
        comparison=comparison,
        statement="balance_sheet",
        title="Balance sheet",
        spec=_BS_LINES,
        current_of=current_stmt("bs"),
        base_of=base_stmt("bs"),
        paragraph_ids=_BS_PARAGRAPH,
        extra_ids=[],
        tie=_balance_tie,
        accounts_note="Account and department detail is not loaded for the balance sheet.",
    )
    cash = _build_statement(
        comparison=comparison,
        statement="cash_flow",
        title="Cash flow",
        spec=_CF_LINES,
        current_of=current_stmt("cfs"),
        base_of=base_stmt("cfs"),
        paragraph_ids=_CF_WALK + ("net_change",),
        extra_ids=["ending_cash"],
        tie=_cash_tie,
        accounts_note="Account and department detail is not loaded for cash flow.",
    )
    return [income, balance, cash]


def build_statement_commentary(
    *,
    close: str,
    ts: dict | None,
    history: dict | None = None,
    labor_bridges: list | None = None,
) -> dict[str, Any]:
    """Comparisons for one close month. Blank means the amount is not loaded."""
    books = ts or {}
    prior = shift_month(close, -1)
    this_quarter = quarter_months(close)
    last_quarter = quarter_months(shift_month(this_quarter[0], -1))
    year_ago = shift_month(close, -12)
    specs = (
        ("mom", comparison_label("mom", close), [close], [prior], "Actual", True),
        (
            "qoq",
            comparison_label("qoq", close),
            this_quarter,
            last_quarter,
            "Actual",
            False,
        ),
        ("yoy", comparison_label("yoy", close), [close], [year_ago], "Actual", False),
        (
            "ytd",
            comparison_label("ytd", close),
            _year_to_date(close),
            _year_to_date(year_ago),
            "Actual",
            False,
        ),
        ("budget", comparison_label("budget", close), [close], [close], "Budget", True),
    )
    comparisons: list[dict[str, Any]] = []
    for comparison_id, label, current_periods, base_periods, scenario, detail in specs:
        statements = _comparison_statements(
            comparison=comparison_id,
            ts=books,
            history=history,
            current_periods=current_periods,
            base_periods=base_periods,
            base_scenario=scenario,
            bridges=labor_bridges,
            detail=detail,
        )
        comparisons.append(
            {
                "id": comparison_id,
                "label": label,
                "available": True,
                "note": "",
                "statements": statements,
                "overview": "\n\n".join(statement["paragraph"] for statement in statements if statement["paragraph"]),
            }
        )
    forecast_ready = any(
        _row((books.get("Forecast") or {}), statement, close) is not _ABSENT
        for statement in ("is", "bs", "cfs")
    )
    if forecast_ready:
        statements = _comparison_statements(
            comparison="forecast",
            ts=books,
            history=history,
            current_periods=[close],
            base_periods=[close],
            base_scenario="Forecast",
            bridges=labor_bridges,
            detail=False,
        )
        comparisons.append(
            {
                "id": "forecast",
                "label": comparison_label("forecast", close),
                "available": True,
                "note": "",
                "statements": statements,
                "overview": "\n\n".join(statement["paragraph"] for statement in statements if statement["paragraph"]),
            }
        )
    else:
        comparisons.append(
            {
                "id": "forecast",
                "label": comparison_label("forecast", close),
                "available": False,
                "note": f"No forecast for {month_label(close)}.",
                "statements": [],
                "overview": "",
            }
        )
    return {
        "close": close,
        "cutoff": REVIEW_CUTOFF,
        "order": ["income_statement", "balance_sheet", "cash_flow"],
        "comparisons": comparisons,
    }


def income_rollup_lines(ts: dict | None, *, close: str) -> dict[str, Any]:
    """P&L rollup the deck may cite. Same lines as the variance workbook.

    Depth-1 lines are always included. A deeper line is included when its
    variance is at or above the review cutoff.
    """
    result = {
        "mom": {"label": "Month over month", "lines": []},
        "budget": {"label": "Versus budget", "lines": []},
    }
    close_period = str(close or "")[:7]
    if not ts or len(close_period) < 7:
        return result
    package = build_statement_commentary(close=close_period, ts=ts)
    for comparison_id in result:
        comparison = next((item for item in package.get("comparisons") or [] if item.get("id") == comparison_id), None)
        income = next(
            (item for item in (comparison or {}).get("statements") or [] if item.get("id") == "income_statement"),
            None,
        )
        lines = []
        for row in (income or {}).get("detail_rows") or []:
            variance = row.get("variance")
            material = variance is not None and abs(float(variance)) >= REVIEW_CUTOFF
            if int(row.get("depth") or 0) != 1 and not material:
                continue
            lines.append(
                {
                    "label": row.get("label"),
                    "depth": row.get("depth") or 1,
                    "line": row.get("line"),
                    "current": row.get("current"),
                    "comparison": row.get("comparison_amount"),
                    "variance": variance,
                    "commentary": row.get("commentary") or "",
                }
            )
        result[comparison_id]["lines"] = lines
    return result


def review_rows(package: dict) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for comparison in package.get("comparisons") or []:
        if not comparison.get("available", True):
            continue
        for statement in comparison.get("statements") or []:
            for row in _statement_rows(statement):
                if row.get("review_required"):
                    rows.append(row)
    return rows


def missing_review_keys(package: dict, commentary_state: dict | None) -> list[str]:
    saved = commentary_state if isinstance(commentary_state, dict) else {}
    reviews = saved.get("reviews") if isinstance(saved.get("reviews"), dict) else {}
    missing: list[str] = []
    for row in review_rows(package):
        record = reviews.get(row["key"])
        reviewed = record is True or (isinstance(record, dict) and record.get("reviewed"))
        if not reviewed:
            missing.append(row["key"])
    return missing


def cited_dollars(text: str) -> list[float] | None:
    """Dollar amounts written in the text. None when a $ is not a readable amount."""
    values: list[float] = []
    for match in _DOLLAR.finditer(text or ""):
        raw = match.group(1).replace(",", "")
        if "." in raw and len(raw.split(".", 1)[1]) != 2:
            return None
        values.append(round(float(raw), 2))
    if (text or "").count("$") != len(values):
        return None
    return values


def _allowed(row: dict) -> set[float]:
    return {round(float(amount), 2) for amount in (row.get("amounts") or [])}


def _text_ties(text: str, allowed: set[float]) -> bool:
    cited = cited_dollars(text)
    if cited is None:
        return False
    return all(any(abs(amount - ok) < 0.01 for ok in allowed) for amount in cited)


def _find_row(package: dict, key: str) -> dict | None:
    for comparison in package.get("comparisons") or []:
        for statement in comparison.get("statements") or []:
            for row in _statement_rows(statement):
                if row.get("key") == key:
                    return row
    return None


def text_problem(package: dict, edits: dict | None, additions: dict | None) -> str | None:
    for key, text in (edits or {}).items():
        if not str(text or "").strip():
            continue
        row = _find_row(package, key)
        if row is None:
            return "line_does_not_tie"
        if not _text_ties(str(text), _allowed(row)):
            return "line_does_not_tie"
    for comparison_id, text in (additions or {}).items():
        if not str(text or "").strip():
            continue
        allowed: set[float] = set()
        comparison = next(
            (item for item in package.get("comparisons") or [] if item.get("id") == comparison_id),
            None,
        )
        if comparison is None:
            return "addition_does_not_tie"
        for statement in comparison.get("statements") or []:
            for row in _statement_rows(statement):
                allowed.update(_allowed(row))
        if not _text_ties(str(text), allowed):
            return "addition_does_not_tie"
    return None


def present_commentary(package: dict, state: dict | None) -> dict[str, Any]:
    """Copy with saved line edits and the overview addition applied."""
    saved = state if isinstance(state, dict) else {}
    edits = saved.get("edits") if isinstance(saved.get("edits"), dict) else {}
    additions = saved.get("additions") if isinstance(saved.get("additions"), dict) else {}
    presented = {
        "close": package.get("close"),
        "cutoff": package.get("cutoff"),
        "order": list(package.get("order") or []),
        "comparisons": [],
    }
    for comparison in package.get("comparisons") or []:
        statements = []
        for statement in comparison.get("statements") or []:
            lines = []
            for line in statement.get("lines") or []:
                edited = dict(line)
                replacement = edits.get(line.get("key"))
                if isinstance(replacement, str) and replacement.strip():
                    edited["commentary"] = replacement.strip()
                    edited["ties"] = _text_ties(edited["commentary"], _allowed(line))
                lines.append(edited)
            paragraph = _paragraph(lines, statement.get("paragraph_line_ids") or [], statement.get("extra_line_ids") or [])
            detail_rows = []
            for row in statement.get("detail_rows") or []:
                edited = dict(row)
                replacement = edits.get(row.get("key"))
                if isinstance(replacement, str) and replacement.strip():
                    edited["commentary"] = replacement.strip()
                detail_rows.append(edited)
            statements.append({**statement, "lines": lines, "detail_rows": detail_rows, "paragraph": paragraph})
        overview = "\n\n".join(statement["paragraph"] for statement in statements if statement["paragraph"])
        addition = additions.get(comparison.get("id"))
        addition_text = addition.strip() if isinstance(addition, str) else ""
        presented["comparisons"].append(
            {
                **comparison,
                "statements": statements,
                "overview": overview,
                "addition": addition_text,
            }
        )
    return presented


_EXPORT_SHEET = {
    "mom": "MoM",
    "qoq": "QoQ",
    "yoy": "YoY",
    "ytd": "YTD",
    "budget": "Budget M",
    "forecast": "Forecast M",
}
_FAVORABLE_UP = frozenset(
    {"revenue", "gross_profit", "net_income", "cash", "total_assets", "cfo", "net_change", "ending_cash"}
)
_FAVORABLE_DOWN = frozenset(
    {"cogs", "sm", "rd", "ga", "total_opex", "da", "interest", "tax", "compensation", "debt"}
)
_WALK_IDS = ("revenue", "cogs", "total_opex", "da", "interest", "tax", "net_income")


def _favorable(row: dict) -> str:
    variance = row.get("variance")
    if variance is None:
        return ""
    line_id = str(row.get("id") or "")
    family = str(row.get("line") or "")
    if line_id in _FAVORABLE_UP or family in _FAVORABLE_UP:
        return "F" if float(variance) >= 0 else "U"
    if line_id in _FAVORABLE_DOWN or family in _FAVORABLE_DOWN or row.get("department"):
        return "F" if float(variance) <= 0 else "U"
    return "F" if float(variance) >= 0 else "U"


def commentary_workbook(
    package: dict,
    state: dict | None = None,
    *,
    allowed: bool = False,
    allowed_at: str | None = None,
    ts: dict | None = None,
    history: dict | None = None,
    entity_name: str = "SMPL Demo Co",
    analyses: list[dict] | None = None,
) -> bytes:
    """MD&A workbook for one close.

    The workbook uses the reference layout: cover, executive summary, net income
    walk, one tab per comparison, and the tie-out checks. Amounts come from
    this close. A package that is not approved is stamped Draft.
    """
    data, _filename = commentary_export(
        package,
        state,
        allowed=allowed,
        allowed_at=allowed_at,
        ts=ts,
        history=history,
        entity_name=entity_name,
        analyses=analyses,
    )
    return data


def commentary_export(
    package: dict,
    state: dict | None = None,
    *,
    allowed: bool = False,
    allowed_at: str | None = None,
    ts: dict | None = None,
    history: dict | None = None,
    entity_name: str = "SMPL Demo Co",
    analyses: list[dict] | None = None,
) -> tuple[bytes, str]:
    """Workbook bytes and the download name. Draft until someone approves the package."""
    from app.services.reporting.export.mda_variance_package import build_mda_package, export_filename
    from app.services.reporting.export.mdna_workbook import render_mdna_workbook

    built = build_mda_package(
        package,
        state,
        ts=ts,
        history=history,
        entity_name=entity_name,
        analyses=analyses,
    )
    return render_mdna_workbook(built), export_filename(built)
