"""Customer-facing load domains for CSV + API Push (workspace Data tab)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.close_workflow import CloseLoadReceipt
from app.models.pipeline import IngestBatch
from app.services.reporting.period_utils import to_period

# Domains customers reason about (ABS-012-style), mapped to SMPL entity types.
LOAD_DOMAINS: list[dict[str, Any]] = [
    {
        "id": "erp_gl",
        "label": "ERP / General ledger",
        "description": "Actual GL, income statement, balance sheet, cash flow",
        "entity_types": [
            "gl_actuals",
            "forecast_gl_detail",
            "forecast_income_statement",
            "forecast_balance_sheet",
            "forecast_cash_flow_statement",
        ],
        "typical_systems": ["NetSuite", "QuickBooks", "Xero", "Sage"],
    },
    {
        "id": "crm",
        "label": "CRM / Pipeline",
        "description": "Opportunities, closed-won, bookings",
        "entity_types": [
            "opportunities",
            "forecast_opportunities",
            "forecast_bookings_summary",
            "forecast_marketing_pipeline",
        ],
        "typical_systems": ["Salesforce", "HubSpot"],
    },
    {
        "id": "billing_arr",
        "label": "Billing / ARR",
        "description": "MRR waterfall, subscriptions, invoices, deferred revenue",
        "entity_types": [
            "mrr_waterfall",
            "forecast_mrr_waterfall",
            "subscriptions",
            "invoices",
            "payments",
            "forecast_deferred_revenue_waterfall",
            "forecast_revenue_schedule",
            "customers",
        ],
        "typical_systems": ["Stripe", "Chargebee", "Maxio", "Salesforce CPQ"],
    },
    {
        "id": "cash",
        "label": "Cash / Treasury",
        "description": "Collections and operating cash bridge inputs",
        "entity_types": [
            "forecast_cash_collections",
            "forecast_operating_cash_flow_bridge",
            "forecast_working_capital_metrics",
        ],
        "typical_systems": ["Treasury system", "Bank CSV via API"],
    },
    {
        "id": "workforce",
        "label": "Workforce / HRIS",
        "description": "Headcount plan and workforce feeds",
        "entity_types": [
            "headcount_plan",
            "forecast_headcount_plan",
            "workforce_employees",
            "workforce_open_requisitions",
            "workforce_hiring_ramp_assumptions",
            "workforce_compensation_bands",
            "workforce_department_allocation_rules",
        ],
        "typical_systems": ["BambooHR", "Workday", "ADP"],
    },
]

ENTITY_TO_DOMAIN: dict[str, str] = {
    entity: domain["id"]
    for domain in LOAD_DOMAINS
    for entity in domain["entity_types"]
}


def build_load_domain_status(
    db: Session,
    organization_id: uuid.UUID,
    *,
    as_of_period: str,
) -> dict[str, Any]:
    """Per-domain push/load status for the close period (CSV + API)."""
    period = to_period(as_of_period)
    batches = db.scalars(
        select(IngestBatch)
        .where(IngestBatch.organization_id == organization_id)
        .order_by(IngestBatch.created_at.desc())
        .limit(80)
    ).all()
    receipts = db.scalars(
        select(CloseLoadReceipt)
        .where(
            CloseLoadReceipt.organization_id == organization_id,
            CloseLoadReceipt.as_of_period == period,
        )
        .order_by(CloseLoadReceipt.created_at.desc())
        .limit(80)
    ).all()

    domain_rows: list[dict[str, Any]] = []
    for domain in LOAD_DOMAINS:
        entities = set(domain["entity_types"])
        domain_batches = [
            b
            for b in batches
            if (b.entity_type in entities)
            or (b.period == period and b.entity_type in entities)
        ]
        # Prefer period-tagged batches when present; else match by entity alone (API often omits period).
        period_batches = [b for b in domain_batches if b.period == period]
        relevant = period_batches or [
            b for b in domain_batches if b.entity_type in entities
        ][:8]

        domain_receipts = [r for r in receipts if r.entity_type in entities]
        latest = relevant[0] if relevant else None
        meta = latest.metadata_json if latest and isinstance(latest.metadata_json, dict) else {}
        source_system = meta.get("source_system") if isinstance(meta.get("source_system"), str) else None

        rows_imported = sum(int(b.rows_imported or 0) for b in relevant)
        rows_rejected = sum(int(b.rows_rejected or 0) for b in relevant)
        api_batches = sum(1 for b in relevant if b.source == "api")
        csv_batches = sum(1 for b in relevant if b.source == "csv_upload")

        if any(b.status == "failed" for b in relevant) or any(
            r.status == "failed" for r in domain_receipts
        ):
            status = "failed"
        elif any(b.status == "partial" for b in relevant) or any(
            r.status == "partial" for r in domain_receipts
        ):
            status = "partial"
        elif rows_imported > 0 or any(r.rows_applied > 0 for r in domain_receipts):
            status = "loaded"
        elif relevant or domain_receipts:
            status = "in_progress"
        else:
            status = "not_loaded"

        domain_rows.append(
            {
                "id": domain["id"],
                "label": domain["label"],
                "description": domain["description"],
                "entity_types": domain["entity_types"],
                "typical_systems": domain["typical_systems"],
                "status": status,
                "source_system": source_system,
                "last_source": latest.source if latest else None,
                "last_entity_type": latest.entity_type if latest else None,
                "last_status": latest.status if latest else None,
                "last_at": latest.created_at.isoformat() if latest and latest.created_at else None,
                "rows_imported": rows_imported,
                "rows_rejected": rows_rejected,
                "api_batches": api_batches,
                "csv_batches": csv_batches,
                "receipt_count": len(domain_receipts),
            }
        )

    return {
        "as_of_period": period,
        "domains": domain_rows,
        "push_endpoint": "/api/v1/ingest/batches",
        "supported_entity_types": sorted({e for d in LOAD_DOMAINS for e in d["entity_types"]}),
    }
