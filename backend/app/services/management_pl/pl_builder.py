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
)

REVENUE_FAVORABLE_KEYS = frozenset(
    {"revenue", "gross_profit", "ebitda", "operating_income", "net_income", "subscription_revenue", "services_revenue"}
)


def _abs_sum(values: list[Decimal]) -> Decimal:
    return sum((abs(v) for v in values), start=Decimal("0"))


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
) -> MetricSlice:
    period = ctx.current_month
    ytd = ctx.ytd_periods
    h2 = ctx.open_periods

    def pull(
        gl: dict[tuple[str, str, str], Decimal],
        periods: tuple[str, ...],
        *,
        fallback: dict[str, dict[str, Decimal]] | None = None,
    ) -> Decimal:
        g = amount_fn(gl, periods)
        if g != 0:
            return g
        if is_key_fn and fallback is not None:
            return is_key_fn(fallback, periods)
        return Decimal("0")

    period_a = pull(gl_act, period, fallback=outlook)
    period_b = pull(gl_bud, period, fallback=budget)
    ytd_a = pull(gl_act, ytd, fallback=outlook)
    ytd_b = pull(gl_bud, ytd, fallback=budget)
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
) -> list[PlLine]:
    lines: list[PlLine] = []

    def rev_fn(gl: dict[tuple[str, str, str], Decimal], periods: tuple[str, ...]) -> Decimal:
        return _gl_dept_acct_sum(gl, periods, department="Revenue", account="Subscription Revenue") or _is_metric(
            outlook, periods, "revenue"
        )

    def sub_rev_fn(_gl: dict, periods: tuple[str, ...]) -> Decimal:
        v = _is_metric(actual_is, periods, "services_revenue")
        if v:
            return v
        return max(Decimal("0"), _is_metric(outlook, periods, "revenue") - rev_fn(gl_act, periods))

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
    lines.append(_pl_line("hdr_revenue", "REVENUE", "revenue", MetricSlice(), line_type="header"))
    sub_line = metric(
        "subscription_revenue",
        "Subscription Revenue",
        "subscription_revenue",
        lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="Revenue", account="Subscription Revenue"),
        is_key_fn=lambda src, ps: _is_metric(src, ps, "revenue"),
    )
    svc_line = metric(
        "services_revenue",
        "Services Revenue",
        "services_revenue",
        lambda _gl, ps: sub_rev_fn(_gl, ps),
        is_key_fn=lambda src, ps: _is_metric(src, ps, "services_revenue"),
        driver="income_statement",
    )
    rev_total_m = _build_metric(
        section_key="revenue",
        ctx=ctx,
        gl_act=gl_act,
        gl_bud=gl_bud,
        gl_fcst=gl_fcst,
        outlook=outlook,
        budget=budget,
        actual_is=actual_is,
        forecast_is=forecast_is,
        amount_fn=lambda gl, ps: rev_fn(gl, ps) + sub_rev_fn(gl, ps),
        is_key_fn=lambda src, ps: _is_metric(src, ps, "revenue"),
    )
    lines.extend(
        [
            sub_line,
            svc_line,
            _pl_line("total_revenue", "Total Revenue", "revenue", rev_total_m, line_type="total", is_bold=True),
        ]
    )

    # --- COGS ---
    lines.append(_pl_line("hdr_cogs", "COST OF REVENUE", "cogs", MetricSlice(), line_type="header"))
    cogs_children: list[PlLine] = []
    for label, acct in COGS_LINE_ACCOUNTS:
        if acct not in COGS_ACCOUNT_NAMES:
            continue
        child = metric(
            f"cogs:{acct}",
            label,
            "cogs",
            lambda gl, ps, account=acct: _cogs_acct_sum(gl, ps, account),
            is_key_fn=lambda src, ps: _is_metric(src, ps, "cost_of_revenue"),
        )
        if child.metrics.actual == 0 and child.metrics.budget == 0:
            continue
        cogs_children.append(child)
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
        amount_fn=lambda gl, ps: sum((_cogs_acct_sum(gl, ps, ac) for ac in COGS_ACCOUNT_NAMES), start=Decimal("0")),
        is_key_fn=lambda src, ps: _is_metric(src, ps, "cost_of_revenue"),
    )
    lines.append(
        _pl_line(
            "cogs_section",
            "Cost of Revenue",
            "cogs",
            cogs_total_m,
            line_type="section",
            expandable=bool(cogs_children),
            children=cogs_children,
        )
    )
    lines.append(_pl_line("total_cogs", "Total COGS", "cogs", cogs_total_m, line_type="total", is_bold=True))

    gp_m = MetricSlice(
        actual=rev_total_m.actual - cogs_total_m.actual,
        budget=rev_total_m.budget - cogs_total_m.budget,
        forecast=rev_total_m.forecast - cogs_total_m.forecast,
        outlook=rev_total_m.outlook - cogs_total_m.outlook,
        variance=(rev_total_m.actual - cogs_total_m.actual) - (rev_total_m.budget - cogs_total_m.budget),
        variance_pct=variance(rev_total_m.actual - cogs_total_m.actual, rev_total_m.budget - cogs_total_m.budget)[1],
        ytd_actual=rev_total_m.ytd_actual - cogs_total_m.ytd_actual,
        ytd_budget=rev_total_m.ytd_budget - cogs_total_m.ytd_budget,
        ytd_variance=(rev_total_m.ytd_actual - cogs_total_m.ytd_actual)
        - (rev_total_m.ytd_budget - cogs_total_m.ytd_budget),
    )
    lines.append(_pl_line("gross_profit", "Gross Profit", "gross_profit", gp_m, line_type="total", is_bold=True))

    def gp_num(_gl: dict[tuple[str, str, str], Decimal], ps: tuple[str, ...]) -> Decimal:
        return rev_fn(_gl, ps) + sub_rev_fn(_gl, ps) - sum(
            (_cogs_acct_sum(_gl, ps, ac) for ac in COGS_ACCOUNT_NAMES), start=Decimal("0")
        )

    lines.append(
        _margin_line(
            "gross_margin_pct",
            "Gross Margin %",
            "gross_margin_pct",
            gp_num,
            lambda gl, ps: rev_fn(gl, ps) + sub_rev_fn(gl, ps),
            ctx,
            gl_act,
            gl_bud,
            gl_fcst,
        )
    )

    # --- S&M ---
    lines.append(_pl_line("hdr_sm", "SALES & MARKETING", "sales_and_marketing", MetricSlice(), line_type="header"))
    sm_lines = [
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
    ]
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
        amount_fn=lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="Sales")
        + _gl_dept_acct_sum(gl, ps, department="Marketing"),
        is_key_fn=lambda src, ps: _is_metric(src, ps, "sales_and_marketing"),
    )
    lines.extend(sm_lines)
    lines.append(_pl_line("total_sm", "Total S&M", "sales_and_marketing", sm_total_m, line_type="total", is_bold=True))
    lines.append(
        _margin_line(
            "sm_pct_rev",
            "S&M % of Revenue",
            "sm_pct_rev",
            lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="Sales")
            + _gl_dept_acct_sum(gl, ps, department="Marketing"),
            lambda gl, ps: rev_fn(gl, ps) + sub_rev_fn(gl, ps),
            ctx,
            gl_act,
            gl_bud,
            gl_fcst,
        )
    )

    # --- R&D ---
    lines.append(_pl_line("hdr_rd", "RESEARCH & DEVELOPMENT", "research_and_development", MetricSlice(), line_type="header"))
    rd_lines = [
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
    ]
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
        amount_fn=lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="Engineering")
        + _gl_dept_acct_sum(gl, ps, department="Product"),
        is_key_fn=lambda src, ps: _is_metric(src, ps, "research_and_development"),
    )
    lines.extend(rd_lines)
    lines.append(_pl_line("total_rd", "Total R&D", "research_and_development", rd_total_m, line_type="total", is_bold=True))
    lines.append(
        _margin_line(
            "rd_pct_rev",
            "R&D % of Revenue",
            "rd_pct_rev",
            lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="Engineering")
            + _gl_dept_acct_sum(gl, ps, department="Product"),
            lambda gl, ps: rev_fn(gl, ps) + sub_rev_fn(gl, ps),
            ctx,
            gl_act,
            gl_bud,
            gl_fcst,
        )
    )

    # --- G&A ---
    lines.append(_pl_line("hdr_ga", "GENERAL & ADMINISTRATIVE", "general_and_administrative", MetricSlice(), line_type="header"))
    ga_dept_m = metric(
        "ga_dept",
        "G&A",
        "general_and_administrative",
        lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="G&A"),
    )
    fin_recurring_m = metric(
        "finance_recurring",
        "Finance — Recurring",
        "general_and_administrative",
        lambda gl, ps: _gl_dept_acct_sum(
            gl, ps, department="Finance", exclude_accounts=frozenset({TRUE_UP_ACCOUNT})
        ),
    )
    fin_onetime_m = metric(
        "finance_onetime",
        "Finance — One-time",
        "general_and_administrative",
        lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="Finance", account=TRUE_UP_ACCOUNT),
        driver="non_recurring",
    )
    da_m = metric(
        "da_ga",
        "D&A",
        "general_and_administrative",
        lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="G&A", account=DA_ACCOUNT),
    )
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
        amount_fn=lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="G&A")
        + _gl_dept_acct_sum(gl, ps, department="Finance")
        + _gl_dept_acct_sum(gl, ps, department="Customer Success")
        + _gl_dept_acct_sum(gl, ps, department="Support"),
        is_key_fn=lambda src, ps: _is_metric(src, ps, "general_and_administrative")
        + _is_metric(src, ps, "customer_success"),
    )
    lines.extend([ga_dept_m, fin_recurring_m, fin_onetime_m, da_m])
    lines.append(
        _pl_line("total_ga_section", "Total G&A", "general_and_administrative", ga_total_m, line_type="total", is_bold=True)
    )

    opex_m = MetricSlice(
        actual=sm_total_m.actual + rd_total_m.actual + ga_total_m.actual,
        budget=sm_total_m.budget + rd_total_m.budget + ga_total_m.budget,
        forecast=sm_total_m.forecast + rd_total_m.forecast + ga_total_m.forecast,
        outlook=sm_total_m.outlook + rd_total_m.outlook + ga_total_m.outlook,
        variance=(sm_total_m.actual + rd_total_m.actual + ga_total_m.actual)
        - (sm_total_m.budget + rd_total_m.budget + ga_total_m.budget),
        variance_pct=variance(
            sm_total_m.actual + rd_total_m.actual + ga_total_m.actual,
            sm_total_m.budget + rd_total_m.budget + ga_total_m.budget,
        )[1],
        ytd_actual=sm_total_m.ytd_actual + rd_total_m.ytd_actual + ga_total_m.ytd_actual,
        ytd_budget=sm_total_m.ytd_budget + rd_total_m.ytd_budget + ga_total_m.ytd_budget,
        ytd_variance=(sm_total_m.ytd_actual + rd_total_m.ytd_actual + ga_total_m.ytd_actual)
        - (sm_total_m.ytd_budget + rd_total_m.ytd_budget + ga_total_m.ytd_budget),
    )
    lines.append(_pl_line("total_opex", "Total OpEx", "total_opex", opex_m, line_type="total", is_bold=True))

    def opex_num(gl: dict[tuple[str, str, str], Decimal], ps: tuple[str, ...]) -> Decimal:
        return (
            _gl_dept_acct_sum(gl, ps, department="Sales")
            + _gl_dept_acct_sum(gl, ps, department="Marketing")
            + _gl_dept_acct_sum(gl, ps, department="Engineering")
            + _gl_dept_acct_sum(gl, ps, department="Product")
            + _gl_dept_acct_sum(gl, ps, department="G&A")
            + _gl_dept_acct_sum(gl, ps, department="Finance")
            + _gl_dept_acct_sum(gl, ps, department="Customer Success")
            + _gl_dept_acct_sum(gl, ps, department="Support")
        )

    lines.append(
        _margin_line(
            "opex_pct_rev",
            "OpEx % of Revenue",
            "opex_pct_rev",
            opex_num,
            lambda gl, ps: rev_fn(gl, ps) + sub_rev_fn(gl, ps),
            ctx,
            gl_act,
            gl_bud,
            gl_fcst,
        )
    )

    ebitda_m = MetricSlice(
        actual=gp_m.actual - opex_m.actual,
        budget=gp_m.budget - opex_m.budget,
        forecast=gp_m.forecast - opex_m.forecast,
        outlook=gp_m.outlook - opex_m.outlook,
        variance=(gp_m.actual - opex_m.actual) - (gp_m.budget - opex_m.budget),
        variance_pct=variance(gp_m.actual - opex_m.actual, gp_m.budget - opex_m.budget)[1],
        ytd_actual=gp_m.ytd_actual - opex_m.ytd_actual,
        ytd_budget=gp_m.ytd_budget - opex_m.ytd_budget,
        ytd_variance=(gp_m.ytd_actual - opex_m.ytd_actual) - (gp_m.ytd_budget - opex_m.ytd_budget),
    )
    lines.append(_pl_line("ebitda", "EBITDA", "ebitda", ebitda_m, line_type="total", is_bold=True, is_ebitda=True))
    lines.append(
        _margin_line(
            "ebitda_margin_pct",
            "EBITDA Margin %",
            "ebitda_margin_pct",
            lambda gl, ps: gp_num(gl, ps) - opex_num(gl, ps),
            lambda gl, ps: rev_fn(gl, ps) + sub_rev_fn(gl, ps),
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
    )
    interest_m = metric(
        "interest_expense",
        "Interest Expense",
        "interest_expense",
        lambda gl, ps: _gl_dept_acct_sum(gl, ps, department="Finance", account=INTEREST_ACCOUNT),
        is_key_fn=lambda src, ps: _is_metric(src, ps, "interest_expense"),
    )
    op_inc_m = MetricSlice(
        actual=ebitda_m.actual - da_below.metrics.actual - interest_m.metrics.actual,
        budget=ebitda_m.budget - da_below.metrics.budget - interest_m.metrics.budget,
        forecast=ebitda_m.forecast - da_below.metrics.forecast - interest_m.metrics.forecast,
        outlook=ebitda_m.outlook - da_below.metrics.outlook - interest_m.metrics.outlook,
        variance=(ebitda_m.actual - da_below.metrics.actual - interest_m.metrics.actual)
        - (ebitda_m.budget - da_below.metrics.budget - interest_m.metrics.budget),
        variance_pct=variance(
            ebitda_m.actual - da_below.metrics.actual - interest_m.metrics.actual,
            ebitda_m.budget - da_below.metrics.budget - interest_m.metrics.budget,
        )[1],
        ytd_actual=ebitda_m.ytd_actual - da_below.metrics.ytd_actual - interest_m.metrics.ytd_actual,
        ytd_budget=ebitda_m.ytd_budget - da_below.metrics.ytd_budget - interest_m.metrics.ytd_budget,
        ytd_variance=(ebitda_m.ytd_actual - da_below.metrics.ytd_actual - interest_m.metrics.ytd_actual)
        - (ebitda_m.ytd_budget - da_below.metrics.ytd_budget - interest_m.metrics.ytd_budget),
    )
    tax_m = metric(
        "tax_expense",
        "Tax Expense",
        "tax_expense",
        lambda _gl, ps: Decimal("0"),
        is_key_fn=lambda src, ps: _is_metric(src, ps, "tax_expense"),
        driver="income_statement",
    )
    net_m = MetricSlice(
        actual=op_inc_m.actual - tax_m.metrics.actual,
        budget=op_inc_m.budget - tax_m.metrics.budget,
        forecast=op_inc_m.forecast - tax_m.metrics.forecast,
        outlook=op_inc_m.outlook - tax_m.metrics.outlook,
        variance=(op_inc_m.actual - tax_m.metrics.actual) - (op_inc_m.budget - tax_m.metrics.budget),
        variance_pct=variance(op_inc_m.actual - tax_m.metrics.actual, op_inc_m.budget - tax_m.metrics.budget)[1],
        ytd_actual=op_inc_m.ytd_actual - tax_m.metrics.ytd_actual,
        ytd_budget=op_inc_m.ytd_budget - tax_m.metrics.ytd_budget,
        ytd_variance=(op_inc_m.ytd_actual - tax_m.metrics.ytd_actual) - (op_inc_m.budget - tax_m.metrics.ytd_budget),
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
