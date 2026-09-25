"""Management P&L table builder — Section 3 hierarchy from GL detail (spec)."""

from __future__ import annotations

from decimal import Decimal
from typing import Callable

from app.services.management_pl.gl_hierarchy import COGS_ACCOUNT_NAMES, GL_DRILLDOWN_DEPARTMENTS
from app.services.management_pl.period_engine import PeriodContext, sum_metric, variance
from app.services.management_pl.schemas import MetricSlice, PlLine

SALES_COMP_ACCOUNTS = ("Base Salaries", "Employee Benefits", "Payroll Taxes", "Sales Commissions")
MKT_SALARY_ACCOUNTS = ("Base Salaries", "Employee Benefits", "Payroll Taxes")
MKT_PROGRAM_ACCOUNTS = (
    "Paid Search",
    "Paid Social",
    "Content and Syndication",
    "Partner Marketing",
    "Events and Webinars",
)
ENG_ACCOUNTS = ("Base Salaries", "Cloud Infrastructure", "Employee Benefits", "Payroll Taxes")
PRODUCT_ACCOUNTS = ("Base Salaries", "Employee Benefits", "Payroll Taxes")
DA_ACCOUNT = "Depreciation and Amortization"
INTEREST_ACCOUNT = "Interest Expense"
TRUE_UP_ACCOUNT = "Accounting True-Up"

COGS_LINE_ACCOUNTS: tuple[tuple[str, str], ...] = (
    ("Cloud Hosting", "Cloud Hosting COGS"),
    ("Support Labor", "Customer Support Labor COGS"),
    ("CS Labor COGS", "Customer Success Labor COGS"),
    ("Third Party / Product", "Third Party Product Fees COGS"),
    ("Payment Processing", "Payment Processing COGS"),
)

REVENUE_FAVORABLE_KEYS = frozenset(
    {"revenue", "gross_profit", "ebitda", "operating_income", "net_income", "subscription_revenue", "services_revenue"}
)


def _abs_sum(values: list[Decimal]) -> Decimal:
    return sum((abs(v) for v in values), start=Decimal("0"))


def _metric_slice_values(
    *,
    actual: Decimal,
    budget: Decimal,
    forecast: Decimal = Decimal("0"),
    ytd_actual: Decimal | None = None,
    ytd_budget: Decimal | None = None,
) -> MetricSlice:
    var_d, var_p = variance(actual, budget)
    ya = actual if ytd_actual is None else ytd_actual
    yb = budget if ytd_budget is None else ytd_budget
    return MetricSlice(
        actual=actual,
        budget=budget,
        forecast=forecast,
        outlook=actual,
        variance=var_d,
        variance_pct=var_p,
        ytd_actual=ya,
        ytd_budget=yb,
        ytd_variance=ya - yb,
    )


def _is_rollup_slice(
    *,
    ctx: PeriodContext,
    actual_is: dict[str, dict[str, Decimal]],
    budget_is: dict[str, dict[str, Decimal]],
    forecast_is: dict[str, dict[str, Decimal]],
    key: str,
    display_abs: bool = True,
) -> MetricSlice:
    """Income Statement warehouse value for a rollup key — never GL."""
    def take(src: dict[str, dict[str, Decimal]], periods: tuple[str, ...]) -> Decimal:
        v = _is_metric(src, periods, key)
        return abs(v) if display_abs and key not in REVENUE_FAVORABLE_KEYS else v

    period = ctx.current_month
    ytd = ctx.ytd_periods
    h2 = ctx.open_periods
    return _metric_slice_values(
        actual=take(actual_is, period),
        budget=take(budget_is, period),
        forecast=take(forecast_is, h2),
        ytd_actual=take(actual_is, ytd),
        ytd_budget=take(budget_is, ytd),
    )


def _scale_children_to_parent(children: list[PlLine], parent: MetricSlice) -> list[PlLine]:
    """Scale GL detail lines so they foot to the Income Statement parent total.

    Without this, partial GL account lists never equal IS Cost of Revenue / OpEx.
    """
    if not children:
        return children

    def scale_field(getter, target: Decimal) -> list[Decimal]:
        raw = [getter(c) for c in children]
        total = sum(raw, start=Decimal("0"))
        if target == 0:
            return [Decimal("0") for _ in raw]
        if total == 0:
            # Spread evenly when GL detail is missing but IS has a total.
            n = len(raw)
            if n == 0:
                return raw
            base = (target / n).quantize(Decimal("0.01"))
            vals = [base] * n
            vals[-1] = target - base * (n - 1)
            return vals
        scaled = [(v / total * target).quantize(Decimal("0.01")) for v in raw]
        drift = target - sum(scaled, start=Decimal("0"))
        scaled[-1] = scaled[-1] + drift
        return scaled

    acts = scale_field(lambda c: c.metrics.actual, parent.actual)
    buds = scale_field(lambda c: c.metrics.budget, parent.budget)
    fcsts = scale_field(lambda c: c.metrics.forecast, parent.forecast)
    ytd_a = scale_field(lambda c: c.metrics.ytd_actual, parent.ytd_actual)
    ytd_b = scale_field(lambda c: c.metrics.ytd_budget, parent.ytd_budget)

    out: list[PlLine] = []
    for i, child in enumerate(children):
        m = _metric_slice_values(
            actual=acts[i],
            budget=buds[i],
            forecast=fcsts[i],
            ytd_actual=ytd_a[i],
            ytd_budget=ytd_b[i],
        )
        out.append(
            _pl_line(
                child.id,
                child.label,
                child.section_key,
                m,
                line_type=child.line_type,
                indent=child.indent,
                expandable=child.expandable,
                is_bold=child.is_bold,
                is_ebitda=child.is_ebitda,
                children=list(child.children),
                driver=child.driver or "gl_scaled_to_is",
            )
        )
    return out


def _gl_dept_acct_sum(
    gl: dict[tuple[str, str, str], Decimal],
    periods: tuple[str, ...],
    *,
    department: str | None = None,
    accounts: tuple[str, ...] | None = None,
    exclude_accounts: frozenset[str] | None = None,
    account: str | None = None,
) -> Decimal:
    total = Decimal("0")
    for (p, dept, ac), amt in gl.items():
        if p not in periods:
            continue
        if department and dept != department:
            continue
        if account and ac != account:
            continue
        if accounts and ac not in accounts:
            continue
        if exclude_accounts and ac in exclude_accounts:
            continue
        total += abs(amt)
    return total


def _cogs_acct_sum(
    gl: dict[tuple[str, str, str], Decimal],
    periods: tuple[str, ...],
    account_name: str,
) -> Decimal:
    total = Decimal("0")
    for (p, _dept, ac), amt in gl.items():
        if p in periods and ac == account_name:
            total += abs(amt)
    return total


def _gl_acct_contains(
    gl: dict[tuple[str, str, str], Decimal],
    periods: tuple[str, ...],
    substring: str,
    *,
    department: str | None = "Revenue",
) -> Decimal:
    """Sum GL amounts whose account name contains ``substring`` (case-insensitive)."""
    total = Decimal("0")
    needle = substring.lower()
    for (p, dept, ac), amt in gl.items():
        if p not in periods:
            continue
        if department is not None and dept != department:
            continue
        if needle in (ac or "").lower():
            total += abs(amt)
    return total


def _gl_subscription_revenue(gl: dict[tuple[str, str, str], Decimal], periods: tuple[str, ...]) -> Decimal:
    v = _gl_dept_acct_sum(gl, periods, department="Revenue", account="Subscription Revenue")
    if v:
        return v
    v = _gl_acct_contains(gl, periods, "subscription", department="Revenue")
    if v:
        return v
    return _gl_acct_contains(gl, periods, "subscription", department=None)


def _gl_services_revenue(gl: dict[tuple[str, str, str], Decimal], periods: tuple[str, ...]) -> Decimal:
    v = _gl_dept_acct_sum(gl, periods, department="Revenue", account="Services Revenue")
    if v:
        return v
    v = _gl_acct_contains(gl, periods, "service", department="Revenue")
    if v:
        return v
    return _gl_acct_contains(gl, periods, "service", department=None)


def _resolve_revenue_split(
    income: dict[str, dict[str, Decimal]],
    gl: dict[tuple[str, str, str], Decimal],
    periods: tuple[str, ...],
) -> tuple[Decimal, Decimal, Decimal]:
    """Return (subscription, services, total) with Sub + Svc == Total.

    Income Statement is absolute SoT. When the warehouse omits the split, assign
    all revenue to subscription (same as Financial Statements ensure_income_formulas).
    Never invent a GL split that the Income Statement does not show — that was the
    $7.35M Subscription vs $0 IS mismatch.
    """
    rev = _is_metric(income, periods, "revenue")
    sub = _is_metric(income, periods, "subscription_revenue")
    svc = _is_metric(income, periods, "services_revenue")

    if sub or svc:
        if not rev:
            rev = sub + svc
        if sub and not svc:
            svc = rev - sub
        elif svc and not sub:
            sub = rev - svc
        elif sub + svc != rev and rev:
            gap = rev - (sub + svc)
            if abs(sub) >= abs(svc):
                sub = sub + gap
            else:
                svc = svc + gap
        return sub, svc, rev

    if rev:
        return rev, Decimal("0"), rev

    # No IS revenue for these periods (e.g. open forecast without IS rows) — GL last resort.
    gl_sub = _gl_subscription_revenue(gl, periods)
    gl_svc = _gl_services_revenue(gl, periods)
    return gl_sub, gl_svc, gl_sub + gl_svc


def _revenue_metric_slice(
    *,
    ctx: PeriodContext,
    actual_is: dict[str, dict[str, Decimal]],
    budget_is: dict[str, dict[str, Decimal]],
    forecast_is: dict[str, dict[str, Decimal]],
    gl_act: dict[tuple[str, str, str], Decimal],
    gl_bud: dict[tuple[str, str, str], Decimal],
    gl_fcst: dict[tuple[str, str, str], Decimal],
    which: str,
) -> MetricSlice:
    """Build Actual/Budget/Forecast metrics for subscription, services, or total revenue."""
    period = ctx.current_month
    ytd = ctx.ytd_periods
    h2 = ctx.open_periods

    def pick(triple: tuple[Decimal, Decimal, Decimal]) -> Decimal:
        sub, svc, rev = triple
        if which == "subscription":
            return sub
        if which == "services":
            return svc
        return rev

    period_a = pick(_resolve_revenue_split(actual_is, gl_act, period))
    period_b = pick(_resolve_revenue_split(budget_is, gl_bud, period))
    ytd_a = pick(_resolve_revenue_split(actual_is, gl_act, ytd))
    ytd_b = pick(_resolve_revenue_split(budget_is, gl_bud, ytd))
    h2_f = pick(_resolve_revenue_split(forecast_is, gl_fcst, h2))

    var_d, var_p = variance(period_a, period_b)
    return MetricSlice(
        actual=period_a,
        budget=period_b,
        forecast=h2_f,
        outlook=period_a,
        variance=var_d,
        variance_pct=var_p,
        ytd_actual=ytd_a,
        ytd_budget=ytd_b,
        ytd_variance=ytd_a - ytd_b,
    )


def _is_metric(
    income: dict[str, dict[str, Decimal]],
    periods: tuple[str, ...],
    key: str,
) -> Decimal:
    return sum_metric(income, periods, key)


def _build_metric(
    *,
    section_key: str,
    ctx: PeriodContext,
    gl_act: dict[tuple[str, str, str], Decimal],
    gl_bud: dict[tuple[str, str, str], Decimal],
    gl_fcst: dict[tuple[str, str, str], Decimal],
    outlook: dict[str, dict[str, Decimal]],
    budget: dict[str, dict[str, Decimal]],
    actual_is: dict[str, dict[str, Decimal]],
    forecast_is: dict[str, dict[str, Decimal]],
    amount_fn: Callable[[dict[tuple[str, str, str], Decimal], tuple[str, ...]], Decimal],
    is_key_fn: Callable[[dict[str, dict[str, Decimal]], tuple[str, ...]], Decimal] | None = None,
    is_percent: bool = False,
    prefer_is: bool = False,
    budget_is: dict[str, dict[str, Decimal]] | None = None,
) -> MetricSlice:
    period = ctx.current_month
    ytd = ctx.ytd_periods
    h2 = ctx.open_periods
    bud_is = budget_is if budget_is is not None else budget

    def pull(
        gl: dict[tuple[str, str, str], Decimal],
        periods: tuple[str, ...],
        *,
        fallback: dict[str, dict[str, Decimal]] | None = None,
        is_source: dict[str, dict[str, Decimal]] | None = None,
    ) -> Decimal:
        # prefer_is: Income Statement is absolute SoT — never fall through to GL.
        if prefer_is and is_key_fn:
            if is_source is not None:
                return is_key_fn(is_source, periods)
            if fallback is not None:
                return is_key_fn(fallback, periods)
        g = amount_fn(gl, periods)
        if g != 0:
            return g
        if is_key_fn and fallback is not None:
            return is_key_fn(fallback, periods)
        return Decimal("0")

    period_a = pull(gl_act, period, fallback=outlook, is_source=actual_is)
    period_b = pull(gl_bud, period, fallback=budget, is_source=bud_is)
    ytd_a = pull(gl_act, ytd, fallback=outlook, is_source=actual_is)
    ytd_b = pull(gl_bud, ytd, fallback=budget, is_source=bud_is)
    h2_f = pull(gl_fcst, h2, fallback=forecast_is)

    var_d, var_p = variance(period_a, period_b)
    ytd_var = ytd_a - ytd_b

    if is_percent:
        return MetricSlice(
            actual=period_a,
            budget=period_b,
            forecast=h2_f,
            outlook=period_a,
            variance=var_d,
            variance_pct=var_p,
            ytd_actual=ytd_a,
            ytd_budget=ytd_b,
            ytd_variance=ytd_var,
        )

    display = section_key in REVENUE_FAVORABLE_KEYS
    return MetricSlice(
        actual=period_a if display else abs(period_a),
        budget=period_b if display else abs(period_b),
        forecast=abs(h2_f) if not display else h2_f,
        outlook=period_a if display else abs(period_a),
        variance=var_d if display else var_d,
        variance_pct=var_p,
        ytd_actual=ytd_a if display else abs(ytd_a),
        ytd_budget=ytd_b if display else abs(ytd_b),
        ytd_variance=ytd_var if display else ytd_var,
    )


def _pl_line(
    line_id: str,
    label: str,
    section_key: str,
    metrics: MetricSlice,
    *,
    line_type: str = "detail",
    indent: int = 0,
    expandable: bool = False,
    is_bold: bool = False,
    is_ebitda: bool = False,
    children: list[PlLine] | None = None,
    driver: str = "",
) -> PlLine:
    return PlLine(
        id=line_id,
        label=label,
        line_type=line_type,  # type: ignore[arg-type]
        section_key=section_key,
        indent=indent,
        expandable=expandable,
        is_bold=is_bold,
        is_ebitda=is_ebitda,
        metrics=metrics,
        children=children or [],
        driver=driver,
    )


def _margin_line(
    line_id: str,
    label: str,
    section_key: str,
    numerator_fn: Callable[[dict[tuple[str, str, str], Decimal], tuple[str, ...]], Decimal],
    rev_fn: Callable[[dict[tuple[str, str, str], Decimal], tuple[str, ...]], Decimal],
    ctx: PeriodContext,
    gl_act: dict[tuple[str, str, str], Decimal],
    gl_bud: dict[tuple[str, str, str], Decimal],
    gl_fcst: dict[tuple[str, str, str], Decimal],
) -> PlLine:
    def pct(gl: dict[tuple[str, str, str], Decimal], periods: tuple[str, ...]) -> Decimal:
        num = numerator_fn(gl, periods)
        den = rev_fn(gl, periods)
        if den == 0:
            return Decimal("0")
        return (num / den).quantize(Decimal("0.0001"))

    m = _build_metric(
        section_key=section_key,
        ctx=ctx,
        gl_act=gl_act,
        gl_bud=gl_bud,
        gl_fcst=gl_fcst,
        outlook={},
        budget={},
        actual_is={},
        forecast_is={},
        amount_fn=pct,
        is_percent=True,
    )
    return _pl_line(line_id, label, section_key, m, line_type="margin")


def build_spec_pl_lines(
    *,
    ctx: PeriodContext,
    gl_act: dict[tuple[str, str, str], Decimal],
    gl_bud: dict[tuple[str, str, str], Decimal],
    gl_fcst: dict[tuple[str, str, str], Decimal],
    outlook: dict[str, dict[str, Decimal]],
    budget: dict[str, dict[str, Decimal]],
    actual_is: dict[str, dict[str, Decimal]],
    forecast_is: dict[str, dict[str, Decimal]],
    budget_is: dict[str, dict[str, Decimal]] | None = None,
) -> list[PlLine]:
    lines: list[PlLine] = []
    # Pure budget IS map when provided; merged budget still used for non-revenue prefer_is fallbacks.
    bud_is = budget_is if budget_is is not None else budget

    def metric(
        line_id: str,
        label: str,
        section_key: str,
        amount_fn: Callable[[dict[tuple[str, str, str], Decimal], tuple[str, ...]], Decimal],
        *,
        line_type: str = "detail",
        indent: int = 0,
        is_key_fn: Callable[[dict[str, dict[str, Decimal]], tuple[str, ...]], Decimal] | None = None,
        is_bold: bool = False,
        driver: str = "",
        prefer_is: bool = False,
    ) -> PlLine:
        m = _build_metric(
            section_key=section_key,
            ctx=ctx,
            gl_act=gl_act,
            gl_bud=gl_bud,
            gl_fcst=gl_fcst,
            outlook=outlook,
            budget=budget,
            actual_is=actual_is,
            forecast_is=forecast_is,
            amount_fn=amount_fn,
            is_key_fn=is_key_fn,
            prefer_is=prefer_is,
            budget_is=bud_is,
        )
        return _pl_line(
            line_id,
            label,
            section_key,
            m,
            line_type=line_type,
            indent=indent,
            is_bold=is_bold,
            driver=driver,
        )

    # --- Revenue ---
    # Subscription + Services + Total from one IS-first split so the table always ties
    # and matches Financial Statements line items for actual and budget.
    lines.append(_pl_line("hdr_revenue", "REVENUE", "revenue", MetricSlice(), line_type="header"))
    rev_kwargs = dict(
        ctx=ctx,
        actual_is=actual_is,
        budget_is=bud_is,
        forecast_is=forecast_is,
        gl_act=gl_act,
        gl_bud=gl_bud,
        gl_fcst=gl_fcst,
    )
    sub_m = _revenue_metric_slice(**rev_kwargs, which="subscription")
    svc_m = _revenue_metric_slice(**rev_kwargs, which="services")
    rev_total_m = _revenue_metric_slice(**rev_kwargs, which="total")
    sub_line = _pl_line(
        "subscription_revenue",
        "Subscription Revenue",
        "subscription_revenue",
        sub_m,
        driver="income_statement",
    )
    svc_line = _pl_line(
        "services_revenue",
        "Services Revenue",
        "services_revenue",
        svc_m,
        driver="income_statement",
    )

    def total_rev_fn(gl: dict[tuple[str, str, str], Decimal], ps: tuple[str, ...]) -> Decimal:
        # Margins: IS-first total from outlook map (closed actuals + open forecast).
        _sub, _svc, rev = _resolve_revenue_split(outlook, gl, ps)
        if rev:
            return rev
        return _sub + _svc

    lines.extend(
        [
            sub_line,
            svc_line,
            _pl_line("total_revenue", "Total Revenue", "revenue", rev_total_m, line_type="total", is_bold=True),
        ]
    )

    # --- COGS ---
    # Total = Income Statement cost_of_revenue. GL detail is scaled to foot.
    lines.append(_pl_line("hdr_cogs", "COST OF REVENUE", "cogs", MetricSlice(), line_type="header"))
    cogs_total_m = _is_rollup_slice(
        ctx=ctx,
        actual_is=actual_is,
        budget_is=bud_is,
        forecast_is=forecast_is,
        key="cost_of_revenue",
    )
    # If IS COGS missing, fall back to full GL account set (not a partial child list).
    if cogs_total_m.actual == 0 and cogs_total_m.budget == 0:
        cogs_total_m = _build_metric(
            section_key="cogs",
            ctx=ctx,
            gl_act=gl_act,
            gl_bud=gl_bud,
            gl_fcst=gl_fcst,
            outlook=outlook,
            budget=budget,
            actual_is=actual_is,
            forecast_is=forecast_is,
            budget_is=bud_is,
            amount_fn=lambda gl, ps: sum(
                (_cogs_acct_sum(gl, ps, ac) for ac in COGS_ACCOUNT_NAMES), start=Decimal("0")
            ),
            is_key_fn=lambda src, ps: _is_metric(src, ps, "cost_of_revenue"),
            prefer_is=True,
        )
    cogs_children: list[PlLine] = []
    for label, acct in COGS_LINE_ACCOUNTS:
        if acct not in COGS_ACCOUNT_NAMES:
            continue
        child = metric(
            f"cogs:{acct}",
            label,
            "cogs",
            lambda gl, ps, account=acct: _cogs_acct_sum(gl, ps, account),
        )
        if child.metrics.actual == 0 and child.metrics.budget == 0 and child.metrics.forecast == 0:
            continue
        cogs_children.append(child)
    cogs_children = _scale_children_to_parent(cogs_children, cogs_total_m)
    lines.append(
        _pl_line(
            "cogs_section",
            "Cost of Revenue",
            "cogs",
            cogs_total_m,
            line_type="section",
            expandable=bool(cogs_children),
            children=cogs_children,
            driver="income_statement",
        )
    )
    lines.append(
        _pl_line(
            "total_cogs",
            "Total COGS",
            "cogs",
            cogs_total_m,
            line_type="total",
            is_bold=True,
            driver="income_statement",
        )
    )

    gp_from_is = _is_rollup_slice(
        ctx=ctx,
        actual_is=actual_is,
        budget_is=bud_is,
        forecast_is=forecast_is,
        key="gross_profit",
        display_abs=False,
    )
    if gp_from_is.actual or gp_from_is.budget:
        gp_m = gp_from_is
    else:
        gp_m = _metric_slice_values(
            actual=rev_total_m.actual - cogs_total_m.actual,
            budget=rev_total_m.budget - cogs_total_m.budget,
            forecast=rev_total_m.forecast - cogs_total_m.forecast,
            ytd_actual=rev_total_m.ytd_actual - cogs_total_m.ytd_actual,
            ytd_budget=rev_total_m.ytd_budget - cogs_total_m.ytd_budget,
        )
    lines.append(
        _pl_line(
            "gross_profit",
            "Gross Profit",
            "gross_profit",
            gp_m,
            line_type="total",
            is_bold=True,
            driver="income_statement",
        )
    )

    def gp_num(_gl: dict[tuple[str, str, str], Decimal], ps: tuple[str, ...]) -> Decimal:
        gp = _is_metric(outlook, ps, "gross_profit")
        if gp:
            return gp
        return total_rev_fn(_gl, ps) - _is_metric(outlook, ps, "cost_of_revenue")

    lines.append(
        _margin_line(
            "gross_margin_pct",
            "Gross Margin %",
            "gross_margin_pct",
            gp_num,
            total_rev_fn,
            ctx,
            gl_act,
            gl_bud,
            gl_fcst,
        )
    )

    # --- S&M ---
    lines.append(_pl_line("hdr_sm", "SALES & MARKETING", "sales_and_marketing", MetricSlice(), line_type="header"))
    sm_total_m = _is_rollup_slice(
        ctx=ctx,
        actual_is=actual_is,
        budget_is=bud_is,
        forecast_is=forecast_is,
        key="sales_and_marketing",
    )
    if sm_total_m.actual == 0 and sm_total_m.budget == 0:
        sm_total_m = _build_metric(
            section_key="sales_and_marketing",
            ctx=ctx,
            gl_act=gl_act,
            gl_bud=gl_bud,
            gl_fcst=gl_fcst,
            outlook=outlook,
            budget=budget,
            actual_is=actual_is,
            forecast_is=forecast_is,
            budget_is=bud_is,
            amount_fn=lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="Sales")
            + _gl_dept_acct_sum(gl, ps, department="Marketing"),
            is_key_fn=lambda src, ps: _is_metric(src, ps, "sales_and_marketing"),
            prefer_is=True,
        )
    sm_lines = _scale_children_to_parent(
        [
            metric(
                "sm_sales_comp",
                "Sales — Salaries & Comp",
                "sales_and_marketing",
                lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="Sales", accounts=SALES_COMP_ACCOUNTS),
            ),
            metric(
                "sm_mkt_salary",
                "Marketing — Salaries",
                "sales_and_marketing",
                lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="Marketing", accounts=MKT_SALARY_ACCOUNTS),
            ),
            metric(
                "sm_mkt_programs",
                "Marketing — Programs",
                "sales_and_marketing",
                lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="Marketing", accounts=MKT_PROGRAM_ACCOUNTS),
            ),
        ],
        sm_total_m,
    )
    lines.extend(sm_lines)
    lines.append(
        _pl_line(
            "total_sm",
            "Total S&M",
            "sales_and_marketing",
            sm_total_m,
            line_type="total",
            is_bold=True,
            driver="income_statement",
        )
    )
    lines.append(
        _margin_line(
            "sm_pct_rev",
            "S&M % of Revenue",
            "sm_pct_rev",
            lambda gl, ps: _is_metric(outlook, ps, "sales_and_marketing"),
            lambda gl, ps: total_rev_fn(gl, ps),
            ctx,
            gl_act,
            gl_bud,
            gl_fcst,
        )
    )

    # --- R&D ---
    lines.append(_pl_line("hdr_rd", "RESEARCH & DEVELOPMENT", "research_and_development", MetricSlice(), line_type="header"))
    rd_total_m = _is_rollup_slice(
        ctx=ctx,
        actual_is=actual_is,
        budget_is=bud_is,
        forecast_is=forecast_is,
        key="research_and_development",
    )
    if rd_total_m.actual == 0 and rd_total_m.budget == 0:
        rd_total_m = _build_metric(
            section_key="research_and_development",
            ctx=ctx,
            gl_act=gl_act,
            gl_bud=gl_bud,
            gl_fcst=gl_fcst,
            outlook=outlook,
            budget=budget,
            actual_is=actual_is,
            forecast_is=forecast_is,
            budget_is=bud_is,
            amount_fn=lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="Engineering")
            + _gl_dept_acct_sum(gl, ps, department="Product"),
            is_key_fn=lambda src, ps: _is_metric(src, ps, "research_and_development"),
            prefer_is=True,
        )
    rd_lines = _scale_children_to_parent(
        [
            metric(
                "rd_engineering",
                "Engineering",
                "research_and_development",
                lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="Engineering", accounts=ENG_ACCOUNTS),
            ),
            metric(
                "rd_product",
                "Product",
                "research_and_development",
                lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="Product", accounts=PRODUCT_ACCOUNTS),
            ),
        ],
        rd_total_m,
    )
    lines.extend(rd_lines)
    lines.append(
        _pl_line(
            "total_rd",
            "Total R&D",
            "research_and_development",
            rd_total_m,
            line_type="total",
            is_bold=True,
            driver="income_statement",
        )
    )
    lines.append(
        _margin_line(
            "rd_pct_rev",
            "R&D % of Revenue",
            "rd_pct_rev",
            lambda gl, ps: _is_metric(outlook, ps, "research_and_development"),
            lambda gl, ps: total_rev_fn(gl, ps),
            ctx,
            gl_act,
            gl_bud,
            gl_fcst,
        )
    )

    # --- G&A ---
    lines.append(_pl_line("hdr_ga", "GENERAL & ADMINISTRATIVE", "general_and_administrative", MetricSlice(), line_type="header"))
    ga_total_m = _is_rollup_slice(
        ctx=ctx,
        actual_is=actual_is,
        budget_is=bud_is,
        forecast_is=forecast_is,
        key="general_and_administrative",
    )
    if ga_total_m.actual == 0 and ga_total_m.budget == 0:
        ga_total_m = _build_metric(
            section_key="general_and_administrative",
            ctx=ctx,
            gl_act=gl_act,
            gl_bud=gl_bud,
            gl_fcst=gl_fcst,
            outlook=outlook,
            budget=budget,
            actual_is=actual_is,
            forecast_is=forecast_is,
            budget_is=bud_is,
            amount_fn=lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="G&A")
            + _gl_dept_acct_sum(gl, ps, department="Finance")
            + _gl_dept_acct_sum(gl, ps, department="Customer Success")
            + _gl_dept_acct_sum(gl, ps, department="Support"),
            is_key_fn=lambda src, ps: _is_metric(src, ps, "general_and_administrative"),
            prefer_is=True,
        )
    ga_lines = _scale_children_to_parent(
        [
            metric(
                "ga_dept",
                "G&A",
                "general_and_administrative",
                lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="G&A"),
            ),
            metric(
                "finance_recurring",
                "Finance — Recurring",
                "general_and_administrative",
                lambda gl, ps: _gl_dept_acct_sum(
                    gl, ps, department="Finance", exclude_accounts=frozenset({TRUE_UP_ACCOUNT})
                ),
            ),
            metric(
                "finance_onetime",
                "Finance — One-time",
                "general_and_administrative",
                lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="Finance", account=TRUE_UP_ACCOUNT),
                driver="non_recurring",
            ),
            metric(
                "da_ga",
                "D&A",
                "general_and_administrative",
                lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="G&A", account=DA_ACCOUNT),
            ),
        ],
        ga_total_m,
    )
    lines.extend(ga_lines)
    lines.append(
        _pl_line(
            "total_ga_section",
            "Total G&A",
            "general_and_administrative",
            ga_total_m,
            line_type="total",
            is_bold=True,
            driver="income_statement",
        )
    )

    opex_m = _metric_slice_values(
        actual=sm_total_m.actual + rd_total_m.actual + ga_total_m.actual,
        budget=sm_total_m.budget + rd_total_m.budget + ga_total_m.budget,
        forecast=sm_total_m.forecast + rd_total_m.forecast + ga_total_m.forecast,
        ytd_actual=sm_total_m.ytd_actual + rd_total_m.ytd_actual + ga_total_m.ytd_actual,
        ytd_budget=sm_total_m.ytd_budget + rd_total_m.ytd_budget + ga_total_m.ytd_budget,
    )
    opex_from_is = _is_rollup_slice(
        ctx=ctx,
        actual_is=actual_is,
        budget_is=bud_is,
        forecast_is=forecast_is,
        key="total_opex",
    )
    if opex_from_is.actual or opex_from_is.budget:
        opex_m = opex_from_is
    lines.append(
        _pl_line(
            "total_opex",
            "Total OpEx",
            "total_opex",
            opex_m,
            line_type="total",
            is_bold=True,
            driver="income_statement",
        )
    )

    def opex_num(_gl: dict[tuple[str, str, str], Decimal], ps: tuple[str, ...]) -> Decimal:
        v = _is_metric(outlook, ps, "total_opex")
        if v:
            return v
        return (
            _is_metric(outlook, ps, "sales_and_marketing")
            + _is_metric(outlook, ps, "research_and_development")
            + _is_metric(outlook, ps, "general_and_administrative")
        )

    lines.append(
        _margin_line(
            "opex_pct_rev",
            "OpEx % of Revenue",
            "opex_pct_rev",
            opex_num,
            lambda gl, ps: total_rev_fn(gl, ps),
            ctx,
            gl_act,
            gl_bud,
            gl_fcst,
        )
    )

    ebitda_from_is = _is_rollup_slice(
        ctx=ctx,
        actual_is=actual_is,
        budget_is=bud_is,
        forecast_is=forecast_is,
        key="ebitda",
        display_abs=False,
    )
    if ebitda_from_is.actual or ebitda_from_is.budget:
        ebitda_m = ebitda_from_is
    else:
        ebitda_m = _metric_slice_values(
            actual=gp_m.actual - opex_m.actual,
            budget=gp_m.budget - opex_m.budget,
            forecast=gp_m.forecast - opex_m.forecast,
            ytd_actual=gp_m.ytd_actual - opex_m.ytd_actual,
            ytd_budget=gp_m.ytd_budget - opex_m.ytd_budget,
        )
    lines.append(
        _pl_line(
            "ebitda",
            "EBITDA",
            "ebitda",
            ebitda_m,
            line_type="total",
            is_bold=True,
            is_ebitda=True,
            driver="income_statement",
        )
    )
    lines.append(
        _margin_line(
            "ebitda_margin_pct",
            "EBITDA Margin %",
            "ebitda_margin_pct",
            lambda gl, ps: (_is_metric(outlook, ps, "ebitda") or (gp_num(gl, ps) - opex_num(gl, ps))),
            lambda gl, ps: total_rev_fn(gl, ps),
            ctx,
            gl_act,
            gl_bud,
            gl_fcst,
        )
    )

    # --- Below the line ---
    lines.append(_pl_line("hdr_below", "BELOW THE LINE", "below_the_line", MetricSlice(), line_type="header"))
    da_below = metric(
        "da_below",
        "D&A",
        "depreciation",
        lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="G&A", account=DA_ACCOUNT),
        is_key_fn=lambda src, ps: _is_metric(src, ps, "depreciation_and_amortization"),
        prefer_is=True,
    )
    interest_m = metric(
        "interest_expense",
        "Interest Expense",
        "interest_expense",
        lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="Finance", account=INTEREST_ACCOUNT),
        is_key_fn=lambda src, ps: _is_metric(src, ps, "interest_expense"),
        prefer_is=True,
    )
    # Match FS Income Statement: Operating Income = EBITDA − D&A (interest below OpInc).
    op_inc_m = MetricSlice(
        actual=ebitda_m.actual - da_below.metrics.actual,
        budget=ebitda_m.budget - da_below.metrics.budget,
        forecast=ebitda_m.forecast - da_below.metrics.forecast,
        outlook=ebitda_m.outlook - da_below.metrics.outlook,
        variance=(ebitda_m.actual - da_below.metrics.actual)
        - (ebitda_m.budget - da_below.metrics.budget),
        variance_pct=variance(
            ebitda_m.actual - da_below.metrics.actual,
            ebitda_m.budget - da_below.metrics.budget,
        )[1],
        ytd_actual=ebitda_m.ytd_actual - da_below.metrics.ytd_actual,
        ytd_budget=ebitda_m.ytd_budget - da_below.metrics.ytd_budget,
        ytd_variance=(ebitda_m.ytd_actual - da_below.metrics.ytd_actual)
        - (ebitda_m.ytd_budget - da_below.metrics.ytd_budget),
    )
    tax_m = metric(
        "tax_expense",
        "Tax Expense",
        "tax_expense",
        lambda _gl, ps: Decimal("0"),
        is_key_fn=lambda src, ps: _is_metric(src, ps, "tax_expense"),
        prefer_is=True,
        driver="income_statement",
    )
    net_m = MetricSlice(
        actual=op_inc_m.actual - interest_m.metrics.actual - tax_m.metrics.actual,
        budget=op_inc_m.budget - interest_m.metrics.budget - tax_m.metrics.budget,
        forecast=op_inc_m.forecast - interest_m.metrics.forecast - tax_m.metrics.forecast,
        outlook=op_inc_m.outlook - interest_m.metrics.outlook - tax_m.metrics.outlook,
        variance=(op_inc_m.actual - interest_m.metrics.actual - tax_m.metrics.actual)
        - (op_inc_m.budget - interest_m.metrics.budget - tax_m.metrics.budget),
        variance_pct=variance(
            op_inc_m.actual - interest_m.metrics.actual - tax_m.metrics.actual,
            op_inc_m.budget - interest_m.metrics.budget - tax_m.metrics.budget,
        )[1],
        ytd_actual=op_inc_m.ytd_actual - interest_m.metrics.ytd_actual - tax_m.metrics.ytd_actual,
        ytd_budget=op_inc_m.ytd_budget - interest_m.metrics.ytd_budget - tax_m.metrics.ytd_budget,
        ytd_variance=(
            op_inc_m.ytd_actual - interest_m.metrics.ytd_actual - tax_m.metrics.ytd_actual
        )
        - (op_inc_m.ytd_budget - interest_m.metrics.ytd_budget - tax_m.metrics.ytd_budget),
    )
    lines.extend(
        [
            da_below,
            interest_m,
            _pl_line("operating_income", "Operating Income", "operating_income", op_inc_m, line_type="total", is_bold=True),
            tax_m,
            _pl_line("net_income", "Net Income", "net_income", net_m, line_type="total", is_bold=True),
        ]
    )

    return lines


def build_department_summary(
    *,
    ctx: PeriodContext,
    gl_act: dict[tuple[str, str, str], Decimal],
    gl_bud: dict[tuple[str, str, str], Decimal],
    headcount_by_dept: dict[str, Decimal],
) -> list[dict[str, Decimal | str | None]]:
    rows: list[dict[str, Decimal | str | None]] = []
    for dept in GL_DRILLDOWN_DEPARTMENTS:
        period_a = _gl_dept_acct_sum(gl_act, ctx.current_month, department=dept)
        period_b = _gl_dept_acct_sum(gl_bud, ctx.current_month, department=dept)
        ytd_a = _gl_dept_acct_sum(gl_act, ctx.ytd_periods, department=dept)
        ytd_b = _gl_dept_acct_sum(gl_bud, ctx.ytd_periods, department=dept)
        if period_a == 0 and period_b == 0 and ytd_a == 0:
            continue
        var_d, var_p = variance(period_a, period_b)
        rows.append(
            {
                "department": dept,
                "headcount": headcount_by_dept.get(dept, Decimal("0")),
                "period_actual": period_a,
                "period_budget": period_b,
                "variance": var_d,
                "variance_pct": var_p,
                "ytd_actual": ytd_a,
                "ytd_budget": ytd_b,
                "ytd_variance": ytd_a - ytd_b,
            }
        )
    return sorted(rows, key=lambda r: abs(r["variance"] or Decimal("0")), reverse=True)  # type: ignore[arg-type]
