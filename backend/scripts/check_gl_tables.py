"""Quick GL warehouse + Management P&L source diagnostic."""
from __future__ import annotations

import json
import uuid
from datetime import date
from pathlib import Path

from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.management_pl.service import build_management_pl_dashboard

ORG = uuid.UUID("8571e520-0687-4516-bdee-379f37c58c1f")


def main() -> None:
    out: dict = {"org_id": str(ORG), "database_url": settings.database_url.split("@")[-1]}
    db = SessionLocal()
    try:
        def scalar(q: str, **params):
            return db.execute(text(q), params).scalar()

        def rows(q: str, **params):
            return [dict(r._mapping) for r in db.execute(text(q), params)]

        tables = [
            "gl_actuals",
            "forecast_gl_detail",
            "actual_income_statement",
            "forecast_income_statement",
            "budget_income_statement",
        ]
        out["table_counts"] = {}
        for t in tables:
            try:
                out["table_counts"][t] = scalar(
                    f'SELECT count(*) FROM "{t}" WHERE organization_id = :oid', oid=str(ORG)
                )
            except Exception as exc:
                out["table_counts"][t] = f"ERROR: {exc}"

        out["gl_actuals_by_version"] = rows(
            """
            SELECT coalesce(version, '') AS version,
                   count(*) AS rows,
                   round(sum(amount)::numeric, 2) AS total_amount
            FROM gl_actuals
            WHERE organization_id = :oid
            GROUP BY 1
            ORDER BY 1
            """,
            oid=str(ORG),
        )

        out["gl_actuals_fy2026"] = rows(
            """
            SELECT to_char(period, 'YYYY-MM') AS period,
                   version,
                   count(*) AS rows,
                   round(sum(CASE WHEN lower(coalesce(statement_category, category, '')) LIKE '%revenue%'
                             THEN amount ELSE 0 END)::numeric, 0) AS revenue,
                   round(sum(CASE WHEN amount < 0 THEN abs(amount) ELSE 0 END)::numeric, 0) AS expenses_abs
            FROM gl_actuals
            WHERE organization_id = :oid
              AND period >= '2026-01-01' AND period <= '2026-12-31'
            GROUP BY 1, 2
            ORDER BY 1, 2
            """,
            oid=str(ORG),
        )

        out["forecast_gl_fy2026"] = rows(
            """
            SELECT to_char(period, 'YYYY-MM') AS period,
                   count(*) AS rows,
                   round(sum(CASE WHEN lower(coalesce(statement_category, '')) LIKE '%revenue%'
                             THEN forecast_amount ELSE 0 END)::numeric, 0) AS revenue,
                   round(sum(CASE WHEN lower(coalesce(line_type, '')) = 'expense'
                             THEN abs(forecast_amount) ELSE 0 END)::numeric, 0) AS expense
            FROM forecast_gl_detail
            WHERE organization_id = :oid
              AND period >= '2026-01-01' AND period <= '2026-12-31'
            GROUP BY 1
            ORDER BY 1
            """,
            oid=str(ORG),
        )

        dash = build_management_pl_dashboard(
            db,
            ORG,
            start_period=date(2026, 1, 1),
            end_period=date(2026, 12, 31),
            as_of_period=date(2026, 5, 1),
            period_mode="fy",
            view_mode="management",
        )
        rev_line = next((l for l in dash.pl_lines if l.id == "revenue"), None)
        gp_line = next((l for l in dash.pl_lines if l.id == "gross_profit"), None)
        ebitda_line = next((l for l in dash.pl_lines if l.id == "ebitda"), None)
        out["management_pl"] = {
            "build_metadata": dash.metadata,
            "gl_primary_mode": dash.metadata.get("gl_primary_mode"),
            "validations": [v.model_dump() for v in dash.validations],
            "revenue_fy_outlook": str(rev_line.metrics.outlook) if rev_line else None,
            "revenue_fy_budget": str(rev_line.metrics.budget) if rev_line else None,
            "gross_profit_fy_outlook": str(gp_line.metrics.outlook) if gp_line else None,
            "ebitda_fy_outlook": str(ebitda_line.metrics.outlook) if ebitda_line else None,
            "monthly_revenue_jan": str(dash.monthly_series[0].revenue_outlook) if dash.monthly_series else None,
            "monthly_revenue_jun": str(dash.monthly_series[5].revenue_outlook) if len(dash.monthly_series) > 5 else None,
        }
    finally:
        db.close()

    report_path = Path(__file__).resolve().parents[2] / "gl-table-check.json"
    report_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(str(report_path))


if __name__ == "__main__":
    main()
