"""Trial-balance rollup.

One tree for a requested entity scope, period, and scenario. Entity is the
scope, not a level. A level is drawn only when the rows under it actually
split. A single child merges into its parent. A memo is evidence on the leaf,
never a level.

Statement line comes from the source category. A department alias applies only
to operating expense, and only when the caller passes it. Depreciation moves
to its own line. Cost of revenue is never given an operating-expense function.

Amounts follow the general-ledger sign in ``gl_income_statement``: revenue
credits are shown as positive; expenses stay as posted.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Iterable

from app.services.reporting.gl_income_statement import (
    LINE_BY_CATEGORY,
    OPEX_LINE_BY_ACCOUNT_GROUP,
)

FUNCTION_LINES = ("sm", "rd", "ga")
OPEX_STATEMENT = "opex"

LINE_LABELS = {
    "revenue": "Revenue",
    "cogs": "Cost of revenue",
    "opex": "Operating expenses",
    "sm": "Sales and marketing",
    "rd": "Research and development",
    "ga": "General and administrative",
    "da": "Depreciation and amortization",
    "interest": "Interest",
    "tax": "Tax",
    "other": "Other",
    "unmapped": "Unmapped",
}

# Expense-type or account name. Payroll tax needs both words so income tax
# is not treated as labor. Applied only on cost of revenue and operating expense.
_LABOR: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("base", "Base salaries", re.compile(r"base salar|salaries and wages|^wages|regular wages|\bsalar", re.I)),
    ("labor", "Labor", re.compile(r"^labor$|\blabor\b", re.I)),
    ("bonus", "Bonuses", re.compile(r"bonus", re.I)),
    ("commission", "Commissions", re.compile(r"commission", re.I)),
    ("benefits", "Employee benefits", re.compile(r"benefit|health|medical", re.I)),
    ("payroll_tax", "Payroll taxes", re.compile(r"payroll tax|employer tax", re.I)),
    ("match", "401(k) employer match", re.compile(r"401|retirement match|employer match", re.I)),
    ("sbc", "Stock-based compensation", re.compile(r"stock|share-based|\bsbc\b", re.I)),
    ("severance", "Severance", re.compile(r"severance", re.I)),
)

_PUNCT = re.compile(r"[^a-z0-9 ]+")
_SPACE = re.compile(r"\s+")


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _account_key(row: dict[str, Any]) -> str:
    return _text(row.get("account_id") or row.get("account_number"))


def chart_number(row: dict[str, Any]) -> str:
    """The chart number when the row has one. A name used as a stand-in is not a number."""
    number = _text(row.get("account_number"))
    if number:
        return number
    ident = _text(row.get("account_id"))
    name = _text(row.get("account_name"))
    if ident and ident != name:
        return ident
    return ""


def is_control_row(row: dict[str, Any]) -> bool:
    """A statement row is an account only when it resolves to a chart account."""
    return not _account_key(row)


def same_fact(left: str, right: str) -> bool:
    """Labels match after case, punctuation, '&' versus 'and', and a trailing plural."""

    def fold(value: str) -> str:
        text = value.lower().replace("&", " and ")
        text = _SPACE.sub(" ", _PUNCT.sub(" ", text)).strip()
        words = []
        for word in text.split():
            if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
                word = word[:-1]
            words.append(word)
        return " ".join(words)

    return fold(left) == fold(right)


def is_depreciation(row: dict[str, Any]) -> bool:
    """Type or subtype wins. A name matches only when it says depreciation.

    'Amortization' alone does not match, so amortized commissions stay put.
    'Depreciation and amortization' matches because it says depreciation.
    """
    subtype = _norm(row.get("account_subtype") or row.get("account_type"))
    if "depreciat" in subtype:
        return True
    return "depreciation" in _norm(row.get("account_name"))


def labor_bucket(name: str) -> tuple[str, str] | None:
    for key, label, pattern in _LABOR:
        if pattern.search(name or ""):
            return key, label
    return None


def classify_fact(row: dict[str, Any], department_aliases: dict[str, str] | None = None) -> tuple[str, str]:
    """Return ``(statement_line, function)``. Function is set only for operating expense."""
    if is_depreciation(row):
        return "da", ""
    aliases = {_norm(key): value for key, value in (department_aliases or {}).items()}
    category = _norm(row.get("statement_category") or row.get("category") or row.get("statement"))
    line = LINE_BY_CATEGORY.get(category)
    group = _norm(row.get("account_group"))
    grouped = OPEX_LINE_BY_ACCOUNT_GROUP.get(group)
    if line in FUNCTION_LINES:
        return OPEX_STATEMENT, line
    if grouped == "da":
        return "da", ""
    if grouped in FUNCTION_LINES and line in (None, "opex", "unmapped"):
        return OPEX_STATEMENT, grouped
    if line == "cogs":
        return "cogs", ""
    if line in (None, "opex", "unmapped"):
        function = aliases.get(_norm(row.get("department")))
        if function in FUNCTION_LINES:
            return OPEX_STATEMENT, function
        return OPEX_STATEMENT, ""
    return line or "unmapped", ""


def _display_amount(statement_line: str, amount: float) -> float:
    if statement_line == "revenue":
        return -amount
    return amount


def _node(
    *,
    node_id: str,
    role: str,
    label: str,
    statement_line: str,
    amount: float = 0.0,
    evidence: list[str] | None = None,
    line_key: str = "",
) -> dict[str, Any]:
    return {
        "id": node_id,
        "role": role,
        "label": label,
        "statement_line": statement_line,
        "line_key": line_key,
        "amount": round(amount, 2),
        "evidence": list(evidence or []),
        "merged_child": "",
        "children": [],
    }


def _add_child(parent: dict[str, Any], child: dict[str, Any]) -> None:
    parent["children"].append(child)
    parent["amount"] = round(parent["amount"] + child["amount"], 2)


def _collapse(node: dict[str, Any]) -> dict[str, Any]:
    node["children"] = [_collapse(child) for child in node["children"]]
    if len(node["children"]) != 1:
        return node
    child = node["children"][0]
    if not same_fact(node["label"], child["label"]):
        node["label"] = f"{node['label']} · {child['label']}"
        node["merged_child"] = child["label"]
    node["id"] = child["id"]
    node["evidence"] = list(child["evidence"] or node["evidence"])
    node["children"] = child["children"]
    node["amount"] = child["amount"]
    if child.get("account_number"):
        node["account_number"] = child["account_number"]
    if child.get("vendor"):
        node["vendor"] = child["vendor"]
    return node


def _bucket_accounts(accounts: list[dict[str, Any]], statement_line: str) -> list[dict[str, Any]]:
    """Labor becomes Compensation. Every other account stays beside it."""
    if statement_line not in ("cogs", OPEX_STATEMENT):
        return accounts
    labor: dict[str, dict[str, Any]] = {}
    other: list[dict[str, Any]] = []
    for account in accounts:
        bucket = labor_bucket(account["label"])
        if bucket is None:
            other.append(account)
            continue
        key, label = bucket
        slot = labor.get(key)
        if slot is None:
            slot = _node(node_id=account["id"] + "|labor:" + key, role="labor", label=label, statement_line=statement_line)
            labor[key] = slot
        _add_child(slot, account)
        if account["evidence"]:
            slot["evidence"].extend(account["evidence"])
    ordered = [_collapse(labor[key]) for key, _label, _pattern in _LABOR if key in labor]
    if not ordered:
        return other
    compensation = _node(
        node_id=ordered[0]["id"].rsplit("|labor:", 1)[0] + "|compensation",
        role="compensation",
        label="Compensation",
        statement_line=statement_line,
    )
    for child in ordered:
        _add_child(compensation, child)
    return [_collapse(compensation), *other]


def _group(rows: list[dict[str, Any]], key_fn, role: str, statement_line: str, parent_id: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    labels: dict[str, str] = {}
    for row in rows:
        key, label = key_fn(row)
        grouped[key].append(row)
        labels[key] = label
    nodes = []
    for key in sorted(grouped, key=lambda item: labels[item].lower()):
        child_rows = grouped[key]
        node = _node(
            node_id=f"{parent_id}|{role}:{key}",
            role=role,
            label=labels[key],
            statement_line=statement_line,
        )
        node["_rows"] = child_rows
        nodes.append(node)
    return nodes


def _fill_dimensions(node: dict[str, Any], rows: list[dict[str, Any]], statement_line: str) -> None:
    """Department, expense type, account, then vendor. Skip a dimension that does not split."""
    departments = {_text(row.get("department")) for row in rows}
    if departments == {""}:
        _fill_expense(node, rows, statement_line)
        return
    nodes = _group(
        rows,
        lambda row: (_text(row.get("department")) or "__blank__", _text(row.get("department")) or "No department"),
        "department",
        statement_line,
        node["id"],
    )
    blank = [item for item in nodes if item["label"] == "No department"]
    named = [item for item in nodes if item["label"] != "No department"]
    for child in [*named, *blank]:
        child_rows = child.pop("_rows")
        _fill_expense(child, child_rows, statement_line)
        _add_child(node, _collapse(child))


def _fill_expense(node: dict[str, Any], rows: list[dict[str, Any]], statement_line: str) -> None:
    types = {_text(row.get("expense_type")) for row in rows}
    if types == {""}:
        _fill_accounts(node, rows, statement_line, typed=False)
        return
    nodes = _group(
        rows,
        lambda row: (_text(row.get("expense_type")) or "__blank__", _text(row.get("expense_type")) or "No expense type"),
        "expense_type",
        statement_line,
        node["id"],
    )
    for child in nodes:
        child_rows = child.pop("_rows")
        _fill_accounts(child, child_rows, statement_line, typed=True)
        _add_child(node, _collapse(child))


def _account_node(row: dict[str, Any], statement_line: str, parent_id: str) -> dict[str, Any]:
    name = _text(row.get("account_name")) or _account_key(row) or "Account"
    memo = _text(row.get("memo") or row.get("notes"))
    node = _node(
        node_id=f"{parent_id}|acct:{_account_key(row) or name}",
        role="account",
        label=name,
        statement_line=statement_line,
        amount=row["_amount"],
        evidence=[memo] if memo else [],
    )
    number = chart_number(row)
    if number:
        node["account_number"] = number
    vendor = _text(row.get("vendor") or row.get("vendor_name"))
    if vendor:
        vendor_node = _node(
            node_id=node["id"] + "|vendor:" + vendor,
            role="vendor",
            label=vendor,
            statement_line=statement_line,
            amount=row["_amount"],
            evidence=list(node["evidence"]),
        )
        node["children"] = [vendor_node]
        node["_vendors"] = [vendor]
    else:
        node["_vendors"] = []
    return node


def _fill_accounts(node: dict[str, Any], rows: list[dict[str, Any]], statement_line: str, *, typed: bool) -> None:
    by_account: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = _account_key(row) or _text(row.get("account_name"))
        existing = by_account.get(key)
        built = _account_node(row, statement_line, node["id"])
        if existing is None:
            by_account[key] = built
            continue
        existing["amount"] = round(existing["amount"] + built["amount"], 2)
        existing["evidence"].extend(built["evidence"])
        existing["_vendors"].extend(built["_vendors"])
        existing["children"].extend(built["children"])
    accounts = []
    for account in by_account.values():
        vendors = [child for child in account["children"] if child["role"] == "vendor"]
        distinct = sorted({child["label"] for child in vendors})
        if len(distinct) <= 1:
            account["children"] = []
            if len(distinct) == 1:
                account["vendor"] = distinct[0]
                if distinct[0] not in account["evidence"]:
                    account["evidence"].append(distinct[0])
        else:
            rolled: dict[str, dict[str, Any]] = {}
            for child in vendors:
                slot = rolled.get(child["label"])
                if slot is None:
                    rolled[child["label"]] = child
                else:
                    slot["amount"] = round(slot["amount"] + child["amount"], 2)
                    slot["evidence"].extend(child["evidence"])
            account["children"] = list(rolled.values())
        account.pop("_vendors", None)
        accounts.append(account)
    # When expense type is empty, labor groups account names. When it is filled,
    # the expense type is already the rollup and accounts stay under it.
    children = accounts if typed else _bucket_accounts(accounts, statement_line)
    for child in children:
        _add_child(node, child)


def _prepare(row: dict[str, Any], aliases: dict[str, str]) -> dict[str, Any]:
    statement_line, function = classify_fact(row, aliases)
    prepared = dict(row)
    prepared["_line"] = statement_line
    prepared["_function"] = function
    prepared["_amount"] = round(_display_amount(statement_line, float(row.get("amount") or 0.0)), 2)
    return prepared


def build_rollup(
    rows: Iterable[dict[str, Any]],
    *,
    department_aliases: dict[str, str] | None = None,
    period: str | None = None,
    collapse_roots: bool = True,
) -> dict[str, Any]:
    """Build the tree for one period.

    Rows whose ``period_status`` is ``preliminary`` are omitted. Pass
    ``period`` to keep a single month. Control rows (no account id) are kept
    as tie totals and are not summed into the tree.
    """
    aliases = department_aliases or {}
    controls: dict[str, float] = defaultdict(float)
    facts: list[dict[str, Any]] = []
    for raw in rows:
        if _norm(raw.get("period_status")) == "preliminary":
            continue
        row_period = _text(raw.get("period"))[:7]
        if period and row_period and row_period != period:
            continue
        if is_control_row(raw):
            line, _function = classify_fact(raw, aliases)
            controls[line] += _display_amount(line, float(raw.get("amount") or 0.0))
            continue
        facts.append(_prepare(raw, aliases))

    by_line: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in facts:
        by_line[fact["_line"]].append(fact)

    order = ["revenue", "cogs", "opex", "da", "interest", "tax", "other", "unmapped"]
    lines = []
    for line in order:
        group = by_line.get(line) or []
        if not group and line not in controls:
            continue
        if line == OPEX_STATEMENT:
            node = _opex_node(group)
        else:
            node = _node(
                node_id=line,
                role="statement_line",
                label=LINE_LABELS.get(line, line),
                statement_line=line,
                line_key=line,
            )
            _fill_dimensions(node, group, line)
        control = round(controls.get(line, 0.0), 2)
        if line in controls and abs(control - node["amount"]) >= 0.5:
            plug = _node(
                node_id=node["id"] + "|plug",
                role="plug",
                label="Items not yet mapped",
                statement_line=line,
                amount=round(control - node["amount"], 2),
            )
            _add_child(node, plug)
        lines.append(_collapse(node) if collapse_roots else node)

    totals = {node["statement_line"]: node["amount"] for node in lines}
    return {
        "period": period or "",
        "controls": {key: round(value, 2) for key, value in controls.items()},
        "lines": lines,
        "totals": totals,
    }


def _opex_node(rows: list[dict[str, Any]]) -> dict[str, Any]:
    node = _node(
        node_id="opex",
        role="statement_line",
        label=LINE_LABELS["opex"],
        statement_line=OPEX_STATEMENT,
        line_key=OPEX_STATEMENT,
    )
    functions = {row["_function"] for row in rows}
    if functions == {""}:
        _fill_dimensions(node, rows, OPEX_STATEMENT)
        return node
    for function in (*FUNCTION_LINES, ""):
        subset = [row for row in rows if row["_function"] == function]
        if not subset:
            continue
        label = LINE_LABELS[function] if function else "No function"
        child = _node(
            node_id="opex|" + (function or "undivided"),
            role="function" if function else "statement_line",
            label=label,
            line_key=function or "undivided",
            statement_line=OPEX_STATEMENT,
        )
        _fill_dimensions(child, subset, OPEX_STATEMENT)
        _add_child(node, child)
    return node


def iter_nodes(node: dict[str, Any]):
    yield node
    for child in node.get("children") or []:
        yield from iter_nodes(child)


def opex_contains_cost_of_revenue(tree: dict[str, Any]) -> bool:
    for line in tree["lines"]:
        if line["statement_line"] != OPEX_STATEMENT:
            continue
        for node in iter_nodes(line):
            if node["statement_line"] == "cogs":
                return True
    return False


def gl_row_for_rollup(row: dict[str, Any]) -> dict[str, Any] | None:
    """One warehouse P&L row in the rollup's shape.

    Balance-sheet rows are not part of this tree. A row with no account id uses
    its account name, because this extract is general-ledger detail, not a
    statement control total.
    """
    if "balance" in _norm(row.get("statement")):
        return None
    number = chart_number(row)
    name = _text(row.get("account_name"))
    account = number or _text(row.get("account_id")) or name
    if not account:
        return None
    return {
        "period": _text(row.get("period"))[:7],
        "account_id": account,
        "account_number": number,
        "account_name": name or account,
        "account_type": row.get("account_type") or "",
        "account_subtype": row.get("account_subtype") or "",
        "statement_category": row.get("statement_category") or row.get("category") or row.get("statement") or "",
        "account_group": row.get("account_group") or "",
        "department": row.get("department") or "",
        "expense_type": row.get("expense_type") or "",
        "vendor": row.get("vendor") or row.get("vendor_name") or "",
        "memo": row.get("memo") or row.get("notes") or "",
        "amount": row.get("amount") or 0,
        "period_status": row.get("period_status") or "",
    }


def trees_by_period(
    rows: Iterable[dict[str, Any]],
    *,
    department_aliases: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    """One rollup per month. Statement lines stay addressable for the report."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in rows:
        prepared = gl_row_for_rollup(raw)
        if prepared is None or not prepared["period"]:
            continue
        grouped[prepared["period"]].append(prepared)
    return {
        period: build_rollup(
            facts,
            department_aliases=department_aliases,
            period=period,
            collapse_roots=False,
        )
        for period, facts in grouped.items()
    }
