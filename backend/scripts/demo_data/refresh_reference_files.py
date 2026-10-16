"""Reference files carried with the dataset, recomputed from the final files so none describes an earlier build.

  python refresh_reference_files.py <dataset_folder> <gl_folder> <out_folder>

Run it last (after rebuild_marketing_funnel.py). Copies <dataset_folder> to <out_folder>, takes the GL detail from
<gl_folder> (the rebuilt GL the loader loads), and rewrites, each in its own layout:
  * {Actual,Budget,Forecast}_dataset_summary.csv: December 31, 2023 ARR (documented input), customer count and ARR at the Jan 2026 start, version months, file
    row counts, renewal pipeline rows and ARR, the income tax rate the GL applies, DSO at the close.
  * Actual_pipeline_marketing_reconciliation.csv: each CRM month, by channel, closed-won vs the Actual marketing
    pipeline. Forecast_pipeline_marketing_reconciliation.csv: the months after the close, Forecast new-business
    weighted ARR vs the Forecast marketing pipeline.
  * Actual_marketing_pipeline_validation.csv: the same over every CRM month.
  * Forecast_marketing_pipeline_validation.csv and Forecast_rebalance_validation_summary.csv: totals of the Forecast
    marketing pipeline summary.
  * forecast_ebitda_sm_validation.csv and Forecast_income_statement_da_interest_validation.csv: the Forecast
    months from the statements. The close stays on the Actual statements.
  * {Actual,Budget,Forecast}_opportunity_mix_summary.csv: deal count and ARR by opportunity type, totaled from
    that version's opportunities file (the deal ledger). The input snapshot is not kept.
  * Forecast_assumptions.csv: exit ARR growth, DSO, NRR and pipeline coverage, calculated from Actual.
    The input file's typed values are not kept.
  * normalized_operating_model_summary.csv: Forecast marketing pipeline, closed-won and spend, totaled from
    the forecast marketing pipeline. The input snapshot is not kept.
  * forecast_file_manifest.csv: every Forecast data file in the folder and whether master_upload_order.csv lists it.
"""

from __future__ import annotations

import os
import shutil
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.services.readiness.manifest import is_reference  # noqa: E402
from documented_inputs import OPENING_ARR, OPENING_ARR_METRIC, OPENING_ARR_WATERFALL_MONTH  # noqa: E402
from rebuild_gl_to_summary import INCOME_TAX_RATE  # noqa: E402
from sync_v5_statements import ZERO, num, q, read, write  # noqa: E402

CLOSE = "2026-06"
PLAN_START = "2026-01"
NB = "New Business"
GL_FILES = ("Actual_gl_detail.csv", "Budget_gl_detail.csv", "Forecast_gl_detail.csv")
HISTORY_LABEL = "Synthetic backcast for PPI - not audited"
MIX_FIELDS = ["opportunity_type", "count", "sum"]
VERSIONS = ("Actual", "Budget", "Forecast")


def _padd(period: str, n: int) -> str:
    i = int(period[:4]) * 12 + int(period[5:7]) - 1 + n
    return f"{i // 12}-{i % 12 + 1:02d}"


def forecast_assumption_values(rows) -> list[dict]:
    """The four forecast assumptions, from Actual. ``rows`` reads a file in the dataset folder.

    Exit ARR growth is ending ARR at the close divided by ending ARR a year earlier.
    DSO is the close month on the working-capital driver (receivables divided by revenue).
    NRR is the product of the monthly net dollar retention rates for the twelve months ending at the close.
    Pipeline coverage is the average monthly coverage for the twelve months before the close: ending open
    pipeline (new business, expansion, reactivation) divided by the next month's closed-won. The close month
    itself is left out, because the next month is a forecast.
    """
    mrr = {r["period"][:7]: r for r in rows("Actual_MRR_Waterfall.csv")}
    prior = _padd(CLOSE, -12)
    end, base = num(mrr[CLOSE]["ending_arr"]), num(mrr[prior]["ending_arr"])
    growth = ((end / base - 1) * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)
    dso = {r["period"][:7]: r["dso_days"] for r in rows("Actual_Working_Capital_Driver_Summary.csv")}[CLOSE]
    nrr = Decimal(1)
    for k in range(1, 13):
        nrr *= num(mrr[_padd(prior, k)]["net_dollar_retention_rate"])
    booking = ("New Business", "Expansion", "Reactivation")
    pipe = {(r["period"][:7], r["opportunity_type"]): r for r in rows("Actual_pipeline_waterfall.csv")}
    cover = []
    for k in range(12):
        p = _padd(prior, k)
        nxt = _padd(p, 1)
        opened = sum((num(pipe[(p, t)]["ending_pipeline_arr"]) for t in booking), ZERO)
        won = sum((num(pipe[(nxt, t)]["closed_won_arr"]) for t in booking), ZERO)
        cover.append(opened / won)
    coverage = (sum(cover, ZERO) / len(cover)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return [
        {"assumption": "Exit ARR Growth", "value": f"{growth}%"},
        {"assumption": "Historical DSO", "value": dso},
        {"assumption": "Historical NRR", "value": f"{nrr.quantize(Decimal('0.0001'), ROUND_HALF_UP)}"},
        {"assumption": "Pipeline Coverage", "value": f"{coverage}x"},
    ]


def operating_model_summary(rows) -> list[dict]:
    """Forecast marketing totals. ``rows`` reads a file in the dataset folder."""
    pipe = won = spend = ZERO
    for r in rows("Forecast_marketing_pipeline.csv"):
        if r["period"][:7] <= CLOSE:
            continue
        pipe += num(r["pipeline_arr_created"])
        won += num(r["closed_won_arr"])
        spend += num(r["marketing_spend"])
    return [{"file": "Forecast_marketing_pipeline.csv", "pipeline_arr": f"{pipe:.2f}",
             "closed_won_arr": f"{won:.2f}", "marketing_spend": f"{spend:.2f}"}]


def opportunity_mix_rows(deals: list[dict]) -> list[dict]:
    """Count and ARR by opportunity type, from the deal ledger."""
    counts: dict[str, int] = defaultdict(int)
    totals: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for deal in deals:
        kind = deal["opportunity_type"]
        counts[kind] += 1
        totals[kind] += num(deal["amount_arr"])
    return [
        {"opportunity_type": kind, "count": str(counts[kind]), "sum": f"{q(totals[kind]):.2f}"}
        for kind in sorted(counts)
    ]


def span(rows: list[dict]) -> str:
    ps = sorted(r["period"][:7] for r in rows)
    return f"{ps[0]} to {ps[-1]}"


def ratio(a: Decimal, b: Decimal, places: str) -> str:
    return f"{(a / b).quantize(Decimal(places), ROUND_HALF_UP)}" if b else ""


def dataset_summary(path) -> list[dict]:
    hist = read(path("Actual_customer_arr_history.csv"))[1]
    last: dict[str, tuple[str, Decimal]] = {}
    for r in sorted(hist, key=lambda r: r["period"]):
        if r["period"][:7] < PLAN_START:
            last[r["customer_id"]] = (r["period"], num(r["ending_arr"]))
    mrr = {r["period"][:7]: r for r in read(path("Actual_MRR_Waterfall.csv"))[1]}
    if PLAN_START not in mrr:
        raise SystemExit(f"no Actual ARR waterfall month {PLAN_START}")
    if OPENING_ARR_WATERFALL_MONTH not in mrr:
        raise SystemExit(f"no Actual ARR waterfall month {OPENING_ARR_WATERFALL_MONTH}")
    opening_arr = num(mrr[OPENING_ARR_WATERFALL_MONTH]["beginning_arr"])
    if opening_arr != OPENING_ARR:
        raise SystemExit(f"waterfall {OPENING_ARR_WATERFALL_MONTH} beginning {opening_arr} != documented "
                         f"December 31, 2023 ARR {OPENING_ARR}")
    start_arr = num(mrr[PLAN_START]["beginning_arr"])
    on_book = sum((a for _, a in last.values()), ZERO)
    if on_book != start_arr:
        raise SystemExit(f"customer ARR before {PLAN_START} {on_book} != ARR waterfall beginning {start_arr}")
    renewals = read(path("Actual_renewal_pipeline.csv"))[1] + read(path("Forecast_renewal_pipeline.csv"))[1]
    wc = {r["period"][:7]: r for r in read(path("Actual_Working_Capital_Driver_Summary.csv"))[1]}
    if CLOSE not in wc:
        raise SystemExit(f"no Actual working capital month {CLOSE}")
    count = lambda name: str(len(read(path(name))[1]))  # noqa: E731
    return [
        {"metric": "Customers", "value": str(sum(1 for _, a in last.values() if a > 0))},
        {"metric": OPENING_ARR_METRIC, "value": f"{OPENING_ARR:.2f}"},
        {"metric": "Starting January 2026 ARR", "value": f"{start_arr:.2f}"},
        {"metric": "Starting January 2026 MRR", "value": f"{q(start_arr / 12):.2f}"},
        {"metric": "Actual months", "value": span(read(path("Actual_income_statement.csv"))[1])},
        {"metric": "Forecast months", "value": span(read(path("Forecast_income_statement.csv"))[1])},
        {"metric": "Budget months", "value": span(read(path("Budget_income_statement.csv"))[1])},
        {"metric": "Actual IS rows", "value": count("Actual_income_statement.csv")},
        {"metric": "Actual MRR rows", "value": count("Actual_MRR_Waterfall.csv")},
        {"metric": "Forecast IS rows", "value": count("Forecast_income_statement.csv")},
        {"metric": "Actual marketing pipeline rows", "value": count("Actual_marketing_pipeline.csv")},
        {"metric": "Invoices", "value": count("Actual_invoices.csv")},
        {"metric": "GL rows", "value": count("Actual_gl_detail.csv")},
        {"metric": "Forecast opportunities", "value": count("Forecast_opportunities.csv")},
        {"metric": "Renewal pipeline rows", "value": str(len(renewals))},
        {"metric": "Renewal ARR total", "value": f"{sum((num(r['renewal_arr']) for r in renewals), ZERO):.2f}"},
        {"metric": "Tax rate", "value": f"{INCOME_TAX_RATE * 100:.0f}%"},
        {"metric": f"DSO days ({CLOSE})", "value": wc[CLOSE]["dso_days"]},
    ]


def crm_reconciliation(path) -> tuple[list[dict], Decimal, Decimal]:
    crm: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for o in read(path("Actual_opportunities.csv"))[1]:
        if o["opportunity_type"] == NB and o["close_status"] == "Closed Won":
            crm[(o["period"][:7], o["marketing_channel"])] += num(o["amount_arr"])
    months = sorted({p for p, _ in crm})
    if not months:
        raise SystemExit("no CRM New Business deals to reconcile")
    marketing = {(r["period"][:7], r["marketing_channel"]): num(r["closed_won_arr"])
                 for r in read(path("Actual_marketing_pipeline.csv"))[1] if r["period"][:7] in months}
    unknown = sorted({c for _, c in crm} - {c for _, c in marketing})
    if unknown:
        raise SystemExit(f"CRM deals in channels with no marketing rows: {unknown}")
    rows = []
    for p, c in sorted(marketing):
        o, m = crm.get((p, c), ZERO), marketing[(p, c)]
        rows.append({"period": p, "marketing_channel": c, "opportunity_closed_won_arr": f"{o:.2f}",
                     "marketing_closed_won_arr": f"{m:.2f}", "variance": f"{o - m:.2f}"})
    return rows, sum(crm.values(), ZERO), sum(marketing.values(), ZERO)


def forecast_reconciliation(path) -> list[dict]:
    """Forecast months after the close: new-business weighted ARR vs the marketing pipeline, by channel."""
    marketing: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for r in read(path("Forecast_marketing_pipeline.csv"))[1]:
        p = r["period"][:7]
        if p <= CLOSE:
            continue
        marketing[(p, r["marketing_channel"])] += num(r["closed_won_arr"])
    deals: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for o in read(path("Forecast_opportunities.csv"))[1]:
        p = o["period"][:7]
        if o["opportunity_type"] == NB and p > CLOSE:
            deals[(p, o["marketing_channel"])] += num(o["weighted_arr"])
    rows = []
    for p, c in sorted(set(marketing) | set(deals)):
        o, m = deals.get((p, c), ZERO), marketing.get((p, c), ZERO)
        rows.append({"period": p, "marketing_channel": c, "opportunity_closed_won_arr": f"{o:.2f}",
                     "marketing_closed_won_arr": f"{m:.2f}", "variance": f"{o - m:.2f}"})
    return rows


def statement_rows(path, version: str) -> dict[str, dict[str, dict]]:
    return {kind: {r["period"][:7]: r for r in read(path(f"{version}_{kind}.csv"))[1]}
            for kind in ("income_statement", "cash_flow_statement", "balance_sheet")}


def main(src: str, gl: str, dst: str) -> list[str]:
    if not all(os.path.isabs(x) for x in (src, gl, dst)):
        raise SystemExit("folders must be absolute paths")
    if os.path.exists(dst):
        raise SystemExit(f"{dst} exists; pick a new folder")
    shutil.copytree(src, dst)
    for name in GL_FILES:
        shutil.copyfile(os.path.join(gl, name), os.path.join(dst, name))
    path = lambda name: os.path.join(dst, name)  # noqa: E731
    notes = [f"GL detail from {gl}: " + ", ".join(f"{n} {len(read(path(n))[1])} rows" for n in GL_FILES)]

    summary = dataset_summary(path)
    for v in ("Actual", "Budget", "Forecast"):
        rows = summary + ([{"metric": "History label", "value": HISTORY_LABEL}] if v == "Actual" else [])
        write(path(f"{v}_dataset_summary.csv"), ["metric", "value"], rows)
    notes.append("dataset summaries: " + "; ".join(f"{r['metric']} {r['value']}" for r in summary))

    rec, crm_total, mk_total = crm_reconciliation(path)
    rec_fields = ["period", "marketing_channel", "opportunity_closed_won_arr", "marketing_closed_won_arr", "variance"]
    write(path("Actual_pipeline_marketing_reconciliation.csv"), rec_fields, rec)
    fc_rec = forecast_reconciliation(path)
    write(path("Forecast_pipeline_marketing_reconciliation.csv"), rec_fields, fc_rec)
    write(path("Actual_marketing_pipeline_validation.csv"),
          ["validation_name", "actual_opportunities_closed_won_arr", "actual_marketing_pipeline_closed_won_arr",
           "variance", "status"],
          [{"validation_name": "Actual marketing closed won ARR ties to actual opportunities",
            "actual_opportunities_closed_won_arr": f"{crm_total:.2f}",
            "actual_marketing_pipeline_closed_won_arr": f"{mk_total:.2f}", "variance": f"{crm_total - mk_total:.2f}",
            "status": "PASS" if crm_total == mk_total else "FAIL"}])
    notes.append(f"CRM reconciliation: {len(rec)} rows {rec[0]['period']}..{rec[-1]['period']}; CRM {crm_total:,.2f} vs "
                 f"marketing {mk_total:,.2f}")

    fs = read(path("Forecast_marketing_pipeline_summary.csv"))[1]
    pipe = sum((num(r["forecast_marketing_pipeline_arr"]) for r in fs), ZERO)
    won = sum((num(r["forecast_marketing_sourced_closed_won_arr"]) for r in fs), ZERO)
    spend = sum((num(r["forecast_marketing_spend"]) for r in fs), ZERO)
    write(path("Forecast_marketing_pipeline_validation.csv"),
          ["validation_name", "total_forecast_pipeline_arr", "total_forecast_marketing_spend", "total_forecast_closed_won_arr"],
          [{"validation_name": f"Forecast marketing pipeline summary ({span(fs)})", "total_forecast_pipeline_arr": f"{pipe:.2f}",
            "total_forecast_marketing_spend": f"{spend:.2f}", "total_forecast_closed_won_arr": f"{won:.2f}"}])
    write(path("Forecast_rebalance_validation_summary.csv"), ["metric", "value"],
          [{"metric": "forecast_marketing_pipeline_arr", "value": f"{pipe:.2f}"},
           {"metric": "forecast_marketing_closed_won_arr", "value": f"{won:.2f}"},
           {"metric": "forecast_marketing_spend", "value": f"{spend:.2f}"},
           {"metric": "pipeline_coverage_ratio", "value": ratio(pipe, won, "0.01")}])

    forecast = statement_rows(path, "Forecast")
    months = sorted(forecast["income_statement"])
    ebitda_rows, da_rows = [], []
    for p in months:
        s = forecast
        if any(p not in s[k] for k in s):
            raise SystemExit(f"no statements for {p}")
        i, c, b = s["income_statement"][p], s["cash_flow_statement"][p], s["balance_sheet"][p]
        rev, sm, ebitda, da = num(i["revenue"]), num(i["sales_and_marketing"]), num(i["ebitda"]), num(i["depreciation_and_amortization"])
        ebitda_rows.append({"period": p, "revenue": i["revenue"], "sales_and_marketing": i["sales_and_marketing"],
                            "sm_percent_of_revenue": ratio(sm, rev, "0.0001"), "ebitda": i["ebitda"],
                            "operating_cash_flow": c["net_cash_from_operating_activities"], "ending_cash": c["ending_cash"],
                            "balance_check": b["balance_check"]})
        opex = sum((num(i[k]) for k in ("sales_and_marketing", "research_and_development", "general_and_administrative")), ZERO)
        da_rows.append({**{k: i[k] for k in ("period", "revenue", "depreciation_and_amortization", "interest_expense",
                                             "net_income", "cost_of_revenue", "gross_profit", "sales_and_marketing",
                                             "research_and_development", "general_and_administrative", "ebitda",
                                             "tax_expense")},
                        "period": p, "operating_income": f"{ebitda - da:.2f}", "total_operating_expenses": f"{opex:.2f}"})
    write(path("forecast_ebitda_sm_validation.csv"), read(path("forecast_ebitda_sm_validation.csv"))[0], ebitda_rows)
    write(path("Forecast_income_statement_da_interest_validation.csv"),
          read(path("Forecast_income_statement_da_interest_validation.csv"))[0], da_rows)
    notes.append(f"statement validations: Forecast {months[0]}..{months[-1]}")

    mix_notes = []
    for v in VERSIONS:
        deals = read(path(f"{v}_opportunities.csv"))[1]
        rows = opportunity_mix_rows(deals)
        write(path(f"{v}_opportunity_mix_summary.csv"), MIX_FIELDS, rows)
        nb = next(r for r in rows if r["opportunity_type"] == "New Business")
        mix_notes.append(f"{v} {nb['count']} New Business {nb['sum']}")
    notes.append("opportunity mix from the deal ledger: " + "; ".join(mix_notes))

    assumptions = forecast_assumption_values(lambda name: read(path(name))[1])
    write(path("Forecast_assumptions.csv"), ["assumption", "value"], assumptions)
    notes.append("Forecast assumptions from Actual: " + "; ".join(f"{r['assumption']} {r['value']}" for r in assumptions))

    model = operating_model_summary(lambda name: read(path(name))[1])
    write(path("normalized_operating_model_summary.csv"),
          ["file", "pipeline_arr", "closed_won_arr", "marketing_spend"], model)
    notes.append("operating model from the Forecast marketing pipeline: "
                 + ", ".join(f"{k} {model[0][k]}" for k in ("pipeline_arr", "closed_won_arr", "marketing_spend")))

    listed = {r["file_name"].lower() for r in read(path("master_upload_order.csv"))[1]}
    forecast_files = sorted(n for n in os.listdir(dst) if n.lower().startswith("forecast_") and n.endswith(".csv")
                            and not is_reference(n))
    write(path("forecast_file_manifest.csv"), ["forecast_file_name", "included_in_master_upload_order"],
          [{"forecast_file_name": n, "included_in_master_upload_order": "Yes" if n.lower() in listed else "No"}
           for n in forecast_files])
    notes.append(f"forecast file manifest: {len(forecast_files)} files, "
                 f"{sum(1 for n in forecast_files if n.lower() not in listed)} not in master_upload_order.csv")
    return notes


if __name__ == "__main__":
    for line in main(sys.argv[1], sys.argv[2], sys.argv[3]):
        print(line)
