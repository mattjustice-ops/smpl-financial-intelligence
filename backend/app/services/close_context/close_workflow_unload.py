"""Self-serve unload for Customer Close Workflow (no eng ticket)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.models.demo_finance import WarehouseCsvRow
from app.services.close_context.close_workflow_service import record_load_receipt
from app.services.reporting.org_reporting_settings import resolve_org_reporting_window
from app.services.workspace.pipeline_ledger import record_pipeline_event

logger = logging.getLogger(__name__)

# Known physical warehouse tables keyed by entity/csv_kind (replace-all unload).
PHYSICAL_ENTITY_TABLES: dict[str, str] = {
    "gl_actuals": "gl_actuals",
    "mrr_waterfall": "mrr_waterfall",
    "headcount_plan": "headcount_plan",
    "forecast_cash_collections": "forecast_cash_collections",
    "forecast_opportunities": "forecast_opportunities",
}


def unload_entity_dataset(
    db: Session,
    organization_id: uuid.UUID,
    *,
    entity_type: str,
    as_of_period: str | None = None,
) -> dict[str, Any]:
    from app.models.organization import Organization

    org = db.get(Organization, organization_id)
    if org is None:
        raise ValueError("organization not found")
    if as_of_period:
        period = as_of_period
    else:
        period, _, _ = resolve_org_reporting_window(db, org)

    kind = (entity_type or "").strip()
    if not kind:
        raise ValueError("entity_type is required")

    deleted_warehouse = 0
    deleted_physical = 0

    # Raw warehouse_csv_rows for this kind
    result = db.execute(
        delete(WarehouseCsvRow).where(
            WarehouseCsvRow.organization_id == organization_id,
            WarehouseCsvRow.csv_kind == kind,
        )
    )
    deleted_warehouse = int(result.rowcount or 0)

    table = PHYSICAL_ENTITY_TABLES.get(kind)
    if table:
        try:
            result = db.execute(
                text(f'delete from "{table}" where organization_id = :organization_id'),
                {"organization_id": str(organization_id)},
            )
            deleted_physical = int(result.rowcount or 0)
        except Exception:
            logger.exception("Physical unload failed for table=%s", table)
            db.rollback()
            raise ValueError(f"Unload failed for physical table {table}")

    # Mark freeze STALE in-session (avoid mark_blob_stale's early commit).
    from app.models.close_context_blob import CloseContextBlob
    from sqlalchemy import select

    blob = db.scalars(
        select(CloseContextBlob).where(
            CloseContextBlob.organization_id == organization_id,
            CloseContextBlob.as_of_period == period,
            CloseContextBlob.status == "COMPLETE",
        )
    ).first()
    if blob is not None:
        blob.status = "STALE"

    receipt = record_load_receipt(
        db,
        organization_id=organization_id,
        as_of_period=period,
        source="unload",
        status="complete",
        rows_staged=0,
        rows_applied=0,
        rows_rejected=0,
        entity_type=kind,
        error_summary={
            "action": "unload",
            "deleted_warehouse_rows": deleted_warehouse,
            "deleted_physical_rows": deleted_physical,
        },
        filename=None,
    )
    record_pipeline_event(
        db,
        organization_id=organization_id,
        batch_id=None,
        event_type="dataset_unloaded",
        source="unload",
        entity_type=kind,
        period=period,
        metadata={
            "deleted_warehouse_rows": deleted_warehouse,
            "deleted_physical_rows": deleted_physical,
            "receipt_id": str(receipt.id),
        },
    )
    db.commit()
    return {
        "ok": True,
        "entity_type": kind,
        "as_of_period": period,
        "deleted_warehouse_rows": deleted_warehouse,
        "deleted_physical_rows": deleted_physical,
        "receipt_id": str(receipt.id),
        "message": (
            f"Unloaded {kind}. Prior freeze pack (if any) marked STALE. "
            "Re-upload corrected data, then Lock again for a new certified pack."
        ),
    }
