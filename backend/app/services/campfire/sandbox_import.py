"""Pull one Campfire dataset into the Campfire Sandbox company.

The sandbox company is separate from the company already on the board.
Budget and Forecast rows are never written. A second pull of the same name
replaces that name only.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.services.campfire.client import CampfireClient, CampfireError
from app.services.close_context.named_load_remove import ensure_load_name_column, load_display_name

SANDBOX_NAME = "Campfire Sandbox"
SANDBOX_SLUG = "campfire-sandbox"
SYSTEM = "Campfire"

DATASETS = ("General ledger", "Customers", "Invoices", "Subscriptions", "Payments")

STATEMENT_FOR_TYPE = {
    "REVENUE": ("income_statement", "revenue"),
    "COGS": ("income_statement", "cogs"),
    "OPERATING_EXPENSES": ("income_statement", "opex"),
    "OTHER_INCOME": ("income_statement", "other_income"),
    "OTHER_EXPENSE": ("income_statement", "other_expense"),
    "COST_ALLOCATION": ("income_statement", "cost_allocation"),
    "UNCATEGORIZED": ("income_statement", "uncategorized"),
}


def campfire_client() -> CampfireClient:
    key = os.environ.get("CAMPFIRE_API_KEY", "").strip()
    if not key:
        raise ValueError("Campfire is not connected on this server.")
    return CampfireClient(key)


def ensure_sandbox_org(db: Session, *, close_month: str) -> Organization:
    org = db.scalars(select(Organization).where(Organization.slug == SANDBOX_SLUG)).first()
    if org is None:
        org = Organization(name=SANDBOX_NAME, slug=SANDBOX_SLUG, status="active", close_month=close_month)
        db.add(org)
        db.flush()
    elif not org.close_month:
        org.close_month = close_month
    return org


def _text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _day(value: Any) -> date | None:
    raw = str(value or "").strip()
    if len(raw) < 10:
        return None
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _customer_name(row: dict[str, Any]) -> str:
    for key in ("name", "company_name", "display_name"):
        text = _text(row.get(key), 512)
        if text:
            return text
    return ""


def customer_payloads(rows: list[dict[str, Any]], *, organization_id: uuid.UUID, load_name: str) -> tuple[list[dict[str, Any]], int]:
    payloads: list[dict[str, Any]] = []
    rejected = 0
    seen: set[str] = set()
    for row in rows:
        if row.get("is_deleted"):
            continue
        customer_id = _text(row.get("id"), 128)
        name = _customer_name(row)
        if not customer_id or not name or customer_id in seen:
            rejected += 1
            continue
        seen.add(customer_id)
        payloads.append(
            {
                "organization_id": organization_id,
                "customer_id": customer_id,
                "customer_name": name,
                "status": _text(row.get("status"), 64) or None,
                "source_crm": SYSTEM,
                "load_name": load_name,
            }
        )
    return payloads, rejected


def invoice_payloads(
    rows: list[dict[str, Any]],
    *,
    organization_id: uuid.UUID,
    load_name: str,
    known_customers: set[str],
) -> tuple[list[dict[str, Any]], int]:
    payloads: list[dict[str, Any]] = []
    rejected = 0
    seen: set[str] = set()
    for row in rows:
        if row.get("is_deleted"):
            continue
        invoice_id = _text(row.get("id"), 128)
        customer_id = _text(row.get("client"), 128)
        if not invoice_id or not customer_id or customer_id not in known_customers or invoice_id in seen:
            rejected += 1
            continue
        seen.add(invoice_id)
        period = _day(row.get("period_start") or row.get("invoice_date"))
        payloads.append(
            {
                "organization_id": organization_id,
                "invoice_id": invoice_id,
                "customer_id": customer_id,
                "invoice_period": period.isoformat()[:7] if period else None,
                "invoice_date": _day(row.get("invoice_date")),
                "due_date": _day(row.get("due_date")),
                "invoice_amount": _decimal(row.get("total_amount")),
                "payment_status": _text(row.get("status") or row.get("payment_status"), 64) or None,
                "currency": _text(row.get("currency"), 3) or None,
                "load_name": load_name,
            }
        )
    return payloads, rejected


def subscription_payloads(
    rows: list[dict[str, Any]],
    *,
    organization_id: uuid.UUID,
    load_name: str,
    known_customers: set[str],
) -> tuple[list[dict[str, Any]], int]:
    payloads: list[dict[str, Any]] = []
    rejected = 0
    seen: set[str] = set()
    for row in rows:
        if row.get("is_deleted"):
            continue
        subscription_id = _text(row.get("id"), 128)
        customer_id = _text(row.get("client"), 128)
        if not subscription_id or not customer_id or customer_id not in known_customers or subscription_id in seen:
            rejected += 1
            continue
        seen.add(subscription_id)
        mrr = _decimal(row.get("total_mrr"))
        payloads.append(
            {
                "organization_id": organization_id,
                "subscription_id": subscription_id,
                "customer_id": customer_id,
                "billing_cadence": _text(row.get("billing_frequency"), 64) or None,
                "start_date": _day(row.get("contract_start_date")),
                "end_date": _day(row.get("contract_end_date")),
                "current_mrr": mrr,
                "current_arr": (mrr * 12).quantize(Decimal("0.01")) if mrr is not None else None,
                "status": _text(row.get("status"), 64) or None,
                "currency": _text(row.get("currency"), 3) or None,
                "load_name": load_name,
            }
        )
    return payloads, rejected


def payment_payloads(
    rows: list[dict[str, Any]],
    *,
    organization_id: uuid.UUID,
    load_name: str,
    invoice_customers: dict[str, str],
) -> tuple[list[dict[str, Any]], int]:
    payloads: list[dict[str, Any]] = []
    rejected = 0
    seen: set[str] = set()
    for row in rows:
        if row.get("voided_date"):
            continue
        payment_id = _text(row.get("id"), 128)
        invoice_id = _text(row.get("invoice_id"), 128)
        customer_id = invoice_customers.get(invoice_id, "")
        if not payment_id or not invoice_id or not customer_id or payment_id in seen:
            rejected += 1
            continue
        seen.add(payment_id)
        payloads.append(
            {
                "organization_id": organization_id,
                "payment_id": payment_id,
                "invoice_id": invoice_id,
                "customer_id": customer_id,
                "payment_date": _day(row.get("payment_date")),
                "payment_amount": _decimal(row.get("amount")),
                "payment_method": _text(row.get("payment_type"), 128) or None,
                "currency": _text(row.get("currency"), 3) or None,
                "load_name": load_name,
            }
        )
    return payloads, rejected


def _statement_pair(hierarchy: Any) -> tuple[str, str]:
    root = ""
    if isinstance(hierarchy, list) and hierarchy:
        root = str(hierarchy[0])
    return STATEMENT_FOR_TYPE.get(root, ("income_statement", root.lower() or "uncategorized"))


def gl_activity_payloads(
    statement: dict[str, Any],
    *,
    organization_id: uuid.UUID,
    load_name: str,
    month: str,
    subsidiary: str,
    currency: str,
) -> list[dict[str, Any]]:
    """One month of income-statement activity. Department lines replace the total line."""
    rows_in = statement.get("income_statement") if isinstance(statement, dict) else None
    if not isinstance(rows_in, list):
        return []
    staged: list[dict[str, Any]] = []
    for row in rows_in:
        if not isinstance(row, dict):
            continue
        statement_name, category = _statement_pair(row.get("hierarchy"))
        account_number = _text(row.get("account_number") or row.get("account_id"), 64)
        account_name = _text(row.get("account_name"), 512)
        if not account_number:
            continue
        for key, value in row.items():
            raw_key = str(key)
            if len(raw_key) < 11 or raw_key[4] != "-" or raw_key[7] != "-" or raw_key[10] != "_":
                continue
            period = raw_key[:10]
            if period[:7] != month:
                continue
            amount = _decimal(value)
            if amount is None or amount == 0:
                continue
            group = raw_key[11:]
            staged.append(
                {
                    "organization_id": organization_id,
                    "version": "Actual",
                    "period": _day(period),
                    "account_number": account_number,
                    "account_name": account_name or None,
                    "statement": statement_name,
                    "category": category,
                    "statement_category": category,
                    "department": "" if group == "Total" else group[:256],
                    "cost_center": "",
                    "sub_department": "",
                    "vendor_id": "",
                    "vendor_name": None,
                    "source_file": load_name[:256],
                    "source_record_id": f"{account_number}:{period}:{group}"[:256],
                    "amount": amount,
                    "currency": currency[:3] or None,
                    "subsidiary": subsidiary[:128],
                    "source_system": SYSTEM,
                    "notes": None,
                    "load_name": load_name,
                    "_total": group == "Total",
                }
            )
    detailed = {(row["account_number"], row["period"]) for row in staged if not row["_total"]}
    out = []
    for row in staged:
        if row["_total"] and (row["account_number"], row["period"]) in detailed:
            continue
        row.pop("_total", None)
        out.append(row)
    return out


DEMO_ORG_ID = uuid.UUID("8571e520-0687-4516-bdee-379f37c58c1f")

LANDING_TABLES = {
    "Customers": "actual_customers",
    "Invoices": "actual_invoices",
    "Payments": "actual_customer_payments",
    "General ledger": "gl_actuals",
}

KIND_FOR_DATASET = {
    "Customers": "customers",
    "Invoices": "invoices",
    "Subscriptions": "subscriptions",
    "Payments": "payments",
    "General ledger": "gl_actuals",
}


def _guard_org(organization_id: uuid.UUID) -> None:
    if organization_id == DEMO_ORG_ID:
        raise ValueError("Campfire Sandbox cannot write the company already on the board.")


def _known_customer_ids(db: Session, organization_id: uuid.UUID) -> set[str]:
    rows = db.execute(
        text("select customer_id from actual_customers where organization_id = :organization_id"),
        {"organization_id": organization_id},
    ).scalars()
    return {str(row) for row in rows if row}


def _invoice_customers(db: Session, organization_id: uuid.UUID) -> dict[str, str]:
    rows = db.execute(
        text(
            "select invoice_id, customer_id from actual_invoices where organization_id = :organization_id"
        ),
        {"organization_id": organization_id},
    ).all()
    return {str(invoice_id): str(customer_id) for invoice_id, customer_id in rows if invoice_id and customer_id}


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _clear_load(db: Session, organization_id: uuid.UUID, *, dataset: str, load_name: str) -> None:
    _guard_org(organization_id)
    db.execute(
        text(
            "delete from warehouse_csv_rows "
            "where organization_id = :organization_id and source_filename = :load_name"
        ),
        {"organization_id": organization_id, "load_name": load_name},
    )
    table = LANDING_TABLES.get(dataset)
    if table == "gl_actuals":
        ensure_load_name_column(db, "gl_actuals")
        db.execute(
            text(
                "delete from gl_actuals "
                "where organization_id = :organization_id and load_name = :load_name "
                "and version = 'Actual' and source_system = :source_system"
            ),
            {"organization_id": organization_id, "load_name": load_name, "source_system": SYSTEM},
        )
        return
    if table:
        db.execute(
            text(
                f'delete from "{table}" '
                "where organization_id = :organization_id and source_filename = :load_name"
            ),
            {"organization_id": organization_id, "load_name": load_name},
        )


def _collect(
    client: CampfireClient,
    dataset: str,
    *,
    organization_id: uuid.UUID,
    load_name: str,
    period: str,
    db: Session,
) -> tuple[list[dict[str, Any]], int]:
    if dataset == "Customers":
        return customer_payloads(
            client.list_all("/rr/api/v1/customers"),
            organization_id=organization_id,
            load_name=load_name,
        )
    if dataset == "Invoices":
        return invoice_payloads(
            client.list_all("/coa/api/v1/invoice"),
            organization_id=organization_id,
            load_name=load_name,
            known_customers=_known_customer_ids(db, organization_id),
        )
    if dataset == "Subscriptions":
        return subscription_payloads(
            client.list_all("/rr/api/v1/contracts"),
            organization_id=organization_id,
            load_name=load_name,
            known_customers=_known_customer_ids(db, organization_id),
        )
    if dataset == "Payments":
        return payment_payloads(
            client.list_all("/coa/api/v1/invoice-payments"),
            organization_id=organization_id,
            load_name=load_name,
            invoice_customers=_invoice_customers(db, organization_id),
        )
    if dataset != "General ledger":
        raise ValueError("Choose a dataset Campfire can load.")
    entities = client.list_all("/coa/api/entity")
    start = date(int(period[:4]), int(period[5:7]), 1)
    end = date(start.year + (start.month == 12), 1 if start.month == 12 else start.month + 1, 1)
    last = date.fromordinal(end.toordinal() - 1)
    payloads: list[dict[str, Any]] = []
    for entity in entities:
        if entity.get("is_elimination_entity"):
            continue
        name = _text(entity.get("name"), 128)
        entity_id = entity.get("id")
        if not name or entity_id is None:
            continue
        statement = client.get(
            "/ca/api/get_income_statement",
            {
                "start_date": start.isoformat(),
                "end_date": last.isoformat(),
                "cadence": "monthly",
                "entity": entity_id,
            },
        )
        currency = _text(entity.get("currency"), 3)
        payloads.extend(
            gl_activity_payloads(
                statement if isinstance(statement, dict) else {},
                organization_id=organization_id,
                load_name=load_name,
                month=period,
                subsidiary=name,
                currency=currency,
            )
        )
    return payloads, 0


def _store(db: Session, organization_id: uuid.UUID, *, dataset: str, load_name: str, payloads: list[dict[str, Any]]) -> None:
    _guard_org(organization_id)
    kind = KIND_FOR_DATASET[dataset]
    warehouse = []
    for index, row in enumerate(payloads, start=1):
        warehouse.append(
            {
                "organization_id": organization_id,
                "csv_kind": kind,
                "source_filename": load_name,
                "source_row_number": index,
                "payload": {key: _jsonable(value) for key, value in row.items() if key != "organization_id"},
            }
        )
    if warehouse:
        db.execute(
            text(
                "insert into warehouse_csv_rows "
                "(organization_id, csv_kind, source_filename, source_row_number, payload) "
                "values (:organization_id, :csv_kind, :source_filename, :source_row_number, cast(:payload as jsonb))"
            ),
            [{**row, "payload": json.dumps(row["payload"])} for row in warehouse],
        )
    table = LANDING_TABLES.get(dataset)
    if table == "gl_actuals":
        ensure_load_name_column(db, "gl_actuals")
        if not payloads:
            return
        db.execute(
            text(
                "insert into gl_actuals ("
                "organization_id, version, period, account_number, account_name, statement, category, "
                "statement_category, department, cost_center, sub_department, vendor_id, source_file, "
                "source_record_id, amount, currency, subsidiary, source_system, load_name"
                ") values ("
                ":organization_id, :version, :period, :account_number, :account_name, :statement, :category, "
                ":statement_category, :department, :cost_center, :sub_department, :vendor_id, :source_file, "
                ":source_record_id, :amount, :currency, :subsidiary, :source_system, :load_name)"
            ),
            payloads,
        )
        return
    if dataset == "Customers" and payloads:
        db.execute(
            text(
                "insert into actual_customers "
                "(organization_id, source_row_number, source_filename, customer_id, customer_name, status, source_crm) "
                "values (:organization_id, :source_row_number, :source_filename, :customer_id, :customer_name, :status, :source_crm)"
            ),
            [
                {
                    "organization_id": organization_id,
                    "source_row_number": index,
                    "source_filename": load_name,
                    "customer_id": row["customer_id"],
                    "customer_name": row["customer_name"],
                    "status": row.get("status"),
                    "source_crm": SYSTEM,
                }
                for index, row in enumerate(payloads, start=1)
            ],
        )
    elif dataset == "Invoices" and payloads:
        db.execute(
            text(
                "insert into actual_invoices "
                "(organization_id, source_row_number, source_filename, version, invoice_id, customer_id, "
                "invoice_period, invoice_date, due_date, invoice_amount, payment_status, currency) "
                "values (:organization_id, :source_row_number, :source_filename, 'Actual', :invoice_id, :customer_id, "
                ":invoice_period, :invoice_date, :due_date, :invoice_amount, :payment_status, :currency)"
            ),
            [
                {
                    "organization_id": organization_id,
                    "source_row_number": index,
                    "source_filename": load_name,
                    "invoice_id": row["invoice_id"],
                    "customer_id": row["customer_id"],
                    "invoice_period": row.get("invoice_period"),
                    "invoice_date": row.get("invoice_date"),
                    "due_date": row.get("due_date"),
                    "invoice_amount": row.get("invoice_amount"),
                    "payment_status": row.get("payment_status"),
                    "currency": row.get("currency"),
                }
                for index, row in enumerate(payloads, start=1)
            ],
        )
    elif dataset == "Payments" and payloads:
        db.execute(
            text(
                "insert into actual_customer_payments "
                "(organization_id, source_row_number, source_filename, version, customer_payment_id, "
                "customer_id, invoice_id, payment_date, amount, payment_method, currency) "
                "values (:organization_id, :source_row_number, :source_filename, 'Actual', :payment_id, "
                ":customer_id, :invoice_id, :payment_date, :payment_amount, :payment_method, :currency)"
            ),
            [
                {
                    "organization_id": organization_id,
                    "source_row_number": index,
                    "source_filename": load_name,
                    **{key: row.get(key) for key in ("payment_id", "customer_id", "invoice_id", "payment_date", "payment_amount", "payment_method", "currency")},
                }
                for index, row in enumerate(payloads, start=1)
            ],
        )


def import_campfire_dataset(db: Session, *, dataset: str, as_of_period: str) -> dict[str, Any]:
    from app.services.close_context.close_workflow_service import record_load_receipt

    if dataset not in DATASETS:
        raise ValueError("Choose a dataset Campfire can load.")
    if len(as_of_period) != 7 or as_of_period[4] != "-":
        raise ValueError("Period must be YYYY-MM.")
    client = campfire_client()
    org = ensure_sandbox_org(db, close_month=as_of_period)
    _guard_org(org.id)
    load_name = load_display_name(SYSTEM, dataset, as_of_period)
    payloads, rejected = _collect(
        client,
        dataset,
        organization_id=org.id,
        load_name=load_name,
        period=as_of_period,
        db=db,
    )
    _clear_load(db, org.id, dataset=dataset, load_name=load_name)
    _store(db, org.id, dataset=dataset, load_name=load_name, payloads=payloads)
    status = "partial" if rejected else "complete"
    receipt = record_load_receipt(
        db,
        organization_id=org.id,
        as_of_period=as_of_period,
        source="campfire",
        status=status,
        rows_staged=len(payloads) + rejected,
        rows_applied=len(payloads),
        rows_rejected=rejected,
        entity_type=dataset,
        filename=load_name,
        error_summary=None
        if not rejected
        else {"message": "Some rows were skipped because the customer or invoice they belong to is not loaded yet."},
    )
    db.commit()
    message = f"Loaded {len(payloads)} rows into {SANDBOX_NAME} as {load_name}."
    if rejected:
        message += f" {rejected} skipped because the customer or invoice is not in {SANDBOX_NAME} yet."
    return {
        "ok": True,
        "organization_id": str(org.id),
        "organization_name": SANDBOX_NAME,
        "load_name": load_name,
        "dataset": dataset,
        "applied": len(payloads),
        "rejected": rejected,
        "receipt_id": str(receipt.id),
        "message": message,
    }


def remove_sandbox_load(db: Session, *, dataset: str | None, as_of_period: str, scope: str) -> dict[str, Any]:
    from app.services.close_context.close_workflow_service import record_load_receipt

    if len(as_of_period) != 7 or as_of_period[4] != "-":
        raise ValueError("Period must be YYYY-MM.")
    if scope == "name":
        if dataset not in DATASETS:
            raise ValueError("Choose a dataset Campfire can remove.")
        names = [load_display_name(SYSTEM, dataset, as_of_period)]
        datasets = [dataset]
    elif scope == "system":
        datasets = list(DATASETS)
        names = [load_display_name(SYSTEM, item, as_of_period) for item in datasets]
    else:
        raise ValueError("Scope must be name or system.")
    org = ensure_sandbox_org(db, close_month=as_of_period)
    _guard_org(org.id)
    for item, load_name in zip(datasets, names):
        _clear_load(db, org.id, dataset=item, load_name=load_name)
    label = names[0] if scope == "name" else f"{SYSTEM} · {as_of_period}"
    receipt = record_load_receipt(
        db,
        organization_id=org.id,
        as_of_period=as_of_period,
        source="unload",
        status="complete",
        rows_staged=0,
        rows_applied=0,
        rows_rejected=0,
        entity_type=dataset or "system",
        filename=label,
        error_summary={"action": "remove_named_load", "scope": scope, "load_name": label},
    )
    db.commit()
    return {
        "ok": True,
        "organization_name": SANDBOX_NAME,
        "load_name": label,
        "deleted_rows": None,
        "receipt_id": str(receipt.id),
        "message": f"Removed {label} from {SANDBOX_NAME}.",
    }


__all__ = ["CampfireError", "import_campfire_dataset", "remove_sandbox_load"]
