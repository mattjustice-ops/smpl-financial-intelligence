"""Read-only QuickBooks Online sandbox → SMPL CSV shapes (first-pass mapping).

Pulls Account + JournalEntry (+ Invoice summary) via refresh-token auth,
maps to exact-header ``gl_actuals`` CSV (expanded warehouse profile) and a
Chart of Accounts staging CSV, then validates headers against the demo CSV
detector (no DB ingest by default).

Usage (from repo root):
  python backend/scripts/qbo_export_to_smpl.py
  python backend/scripts/qbo_export_to_smpl.py --max-accounts 200 --max-journal-entries 100

Output (gitignored):
  backend/tmp/qbo_export/gl_actuals.csv
  backend/tmp/qbo_export/chart_of_accounts.csv
  backend/tmp/qbo_export/invoices_staging.csv
  backend/tmp/qbo_export/export_manifest.json

Product constraint: READ ONLY — never POST/write back to QBO.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.parse
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qbo_oauth_once import load_qbo_config, upsert_secrets  # noqa: E402
from qbo_sandbox_probe import (  # noqa: E402
    SANDBOX_BASE,
    _mask,
    _query_entities,
    qbo_get,
    refresh_access_token,
)

BACKEND = Path(__file__).resolve().parent.parent
OUT_DIR = BACKEND / "tmp" / "qbo_export"
SOURCE_SYSTEM = "quickbooks"
SOURCE_FILE = "qbo_journal_entry"

# Exact expanded warehouse headers (detector EXPANDED_EXPECTED["gl_actuals"])
GL_ACTUALS_HEADERS = [
    "version",
    "period",
    "account_number",
    "account_name",
    "statement",
    "statement_category",
    "account_group",
    "expense_type",
    "department",
    "cost_center",
    "sub_department",
    "vendor_id",
    "vendor_name",
    "source_file",
    "source_record_id",
    "amount",
    "currency",
    "subsidiary",
    "source_system",
    "notes",
]

# Staging CoA (matches templates/csv/01-source-inputs/erp/ERP_Chart_of_Accounts_Export.csv)
COA_HEADERS = [
    "account_code",
    "account_name",
    "account_type",
    "parent_account_code",
    "statement",
    "category",
]

# Lightweight invoice staging (not an exact invoices mart profile — see docs)
INVOICE_STAGING_HEADERS = [
    "invoice_id",
    "doc_number",
    "txn_date",
    "total_amt",
    "balance",
    "currency",
    "customer_ref_id",
    "source_system",
]


def _as_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _period_from_txn_date(txn_date: str | None) -> str:
    """SMPL period = first day of month (YYYY-MM-DD)."""
    if not txn_date:
        return ""
    raw = str(txn_date)[:10]
    try:
        d = date.fromisoformat(raw)
    except ValueError:
        return raw
    return date(d.year, d.month, 1).isoformat()


def _ref_value(ref: Any) -> str:
    if isinstance(ref, dict):
        return str(ref.get("value") or "").strip()
    return ""


def _ref_name(ref: Any) -> str:
    if isinstance(ref, dict):
        return str(ref.get("name") or "").strip()
    return ""


def _map_statement_category(
    classification: str | None,
    account_type: str | None,
    account_sub_type: str | None,
) -> tuple[str, str]:
    """Return (statement, category) for SMPL gl_actuals / CoA."""
    cls = (classification or "").strip()
    at = (account_type or "").strip()
    sub = (account_sub_type or "").strip()
    at_l = at.lower()
    sub_l = sub.lower()

    if cls == "Revenue" or at in {"Income", "Other Income"}:
        cat = "revenue"
        if "discount" in sub_l:
            cat = "contra_revenue"
        return "income", cat
    if at == "Cost of Goods Sold" or "cogs" in sub_l or "costofgoods" in sub_l.replace(" ", ""):
        return "income", "cogs"
    if cls == "Expense" or at in {"Expense", "Other Expense"}:
        cat = "opex"
        if "payroll" in sub_l or "wage" in sub_l or "salary" in sub_l:
            cat = "payroll"
        elif "depreciat" in sub_l or "amort" in sub_l:
            cat = "non_cash"
        return "income", cat
    if cls == "Asset" or "asset" in at_l or at in {
        "Bank",
        "Accounts Receivable",
        "Other Current Asset",
        "Fixed Asset",
        "Other Asset",
    }:
        return "balance_sheet", "asset"
    if cls == "Liability" or "payable" in at_l or "liabilit" in at_l or at in {
        "Accounts Payable",
        "Credit Card",
        "Other Current Liability",
        "Long Term Liability",
    }:
        return "balance_sheet", "liability"
    if cls == "Equity" or "equity" in at_l or at in {"Equity"}:
        return "balance_sheet", "equity"
    return "unknown", (at or sub or "unmapped").lower().replace(" ", "_")[:64] or "unmapped"


def _signed_amount(
    *,
    amount: Decimal,
    posting_type: str,
    statement: str,
    category: str,
) -> Decimal:
    """Natural P&L / BS sign: revenue & liability/equity credits positive; expense & asset debits positive."""
    posting = (posting_type or "").strip().lower()
    is_credit = posting == "credit"
    if statement == "income":
        if category in {"revenue", "contra_revenue"}:
            return amount if is_credit else -amount
        # cogs / opex / payroll / non_cash
        return amount if not is_credit else -amount
    if statement == "balance_sheet":
        if category in {"liability", "equity"}:
            return amount if is_credit else -amount
        # asset
        return amount if not is_credit else -amount
    # unknown: debit positive / credit negative
    return amount if not is_credit else -amount


def _paginate_query(
    access: str,
    realm_id: str,
    entity: str,
    *,
    max_results: int,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    """Fetch up to max_results entities via QBO SQL-like query + startposition."""
    rows: list[dict[str, Any]] = []
    start = 1
    while len(rows) < max_results:
        batch = min(page_size, max_results - len(rows))
        q = f"select * from {entity} startposition {start} maxresults {batch}"
        path = (
            f"/v3/company/{realm_id}/query?"
            f"query={urllib.parse.quote(q)}&minorversion=65"
        )
        payload = qbo_get(access, path)
        page = _query_entities(payload, entity)
        if not page:
            break
        rows.extend(page)
        if len(page) < batch:
            break
        start += len(page)
    return rows


def _account_code(acct: dict[str, Any]) -> str:
    acct_num = str(acct.get("AcctNum") or "").strip()
    if acct_num:
        return acct_num
    aid = str(acct.get("Id") or "").strip()
    return f"QBO-{aid}" if aid else ""


def _build_account_index(accounts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(a.get("Id")): a for a in accounts if a.get("Id") is not None}


def map_accounts_to_coa(accounts: list[dict[str, Any]]) -> list[dict[str, str]]:
    id_to_code = {str(a.get("Id")): _account_code(a) for a in accounts}
    rows: list[dict[str, str]] = []
    for acct in accounts:
        code = _account_code(acct)
        if not code:
            continue
        statement, category = _map_statement_category(
            acct.get("Classification"),
            acct.get("AccountType"),
            acct.get("AccountSubType"),
        )
        parent_id = _ref_value(acct.get("ParentRef"))
        rows.append(
            {
                "account_code": code,
                "account_name": str(acct.get("Name") or acct.get("FullyQualifiedName") or ""),
                "account_type": str(acct.get("AccountType") or ""),
                "parent_account_code": id_to_code.get(parent_id, ""),
                "statement": statement,
                "category": category,
            }
        )
    return rows


def map_journal_entries_to_gl(
    journal_entries: list[dict[str, Any]],
    accounts_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for je in journal_entries:
        je_id = str(je.get("Id") or "").strip()
        txn_date = str(je.get("TxnDate") or "")
        period = _period_from_txn_date(txn_date)
        currency = _ref_value(je.get("CurrencyRef")) or "USD"
        private_note = str(je.get("PrivateNote") or "").strip()
        lines = je.get("Line") or []
        if not isinstance(lines, list):
            continue
        for line in lines:
            if not isinstance(line, dict):
                continue
            detail = line.get("JournalEntryLineDetail") or {}
            if not isinstance(detail, dict) or not detail:
                continue
            acct_id = _ref_value(detail.get("AccountRef"))
            acct = accounts_by_id.get(acct_id) or {}
            account_number = _account_code(acct) if acct else (f"QBO-{acct_id}" if acct_id else "")
            account_name = (
                str(acct.get("Name") or "")
                or _ref_name(detail.get("AccountRef"))
                or ""
            )
            statement, category = _map_statement_category(
                acct.get("Classification"),
                acct.get("AccountType") or "",
                acct.get("AccountSubType") or "",
            )
            amt = _as_decimal(line.get("Amount"))
            if amt is None:
                continue
            posting = str(detail.get("PostingType") or "")
            signed = _signed_amount(
                amount=amt,
                posting_type=posting,
                statement=statement,
                category=category,
            )
            line_id = str(line.get("Id") or line.get("LineNum") or "").strip()
            source_record_id = f"{je_id}:{line_id}" if line_id else je_id
            dept = _ref_name(detail.get("DepartmentRef")) or _ref_value(detail.get("DepartmentRef"))
            class_name = _ref_name(detail.get("ClassRef")) or _ref_value(detail.get("ClassRef"))
            entity = detail.get("Entity") if isinstance(detail.get("Entity"), dict) else {}
            entity_ref = entity.get("EntityRef") if isinstance(entity, dict) else None
            vendor_id = _ref_value(entity_ref) if entity_ref else ""
            vendor_name = _ref_name(entity_ref) if entity_ref else ""
            desc = str(line.get("Description") or "").strip()
            notes_parts = [p for p in (private_note, desc, f"posting={posting}" if posting else "") if p]

            out.append(
                {
                    "version": "Actual",
                    "period": period,
                    "account_number": account_number,
                    "account_name": account_name,
                    "statement": statement,
                    "statement_category": category,
                    "account_group": str(acct.get("AccountType") or ""),
                    "expense_type": str(acct.get("AccountSubType") or ""),
                    "department": dept,
                    "cost_center": class_name,
                    "sub_department": "",
                    "vendor_id": vendor_id,
                    "vendor_name": vendor_name,
                    "source_file": SOURCE_FILE,
                    "source_record_id": source_record_id,
                    "amount": f"{signed:.2f}",
                    "currency": currency,
                    "subsidiary": "",
                    "source_system": SOURCE_SYSTEM,
                    "notes": " | ".join(notes_parts)[:500],
                }
            )
    return out


def map_invoices_staging(invoices: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for inv in invoices:
        rows.append(
            {
                "invoice_id": str(inv.get("Id") or ""),
                "doc_number": str(inv.get("DocNumber") or ""),
                "txn_date": str(inv.get("TxnDate") or "")[:10],
                "total_amt": str(inv.get("TotalAmt") if inv.get("TotalAmt") is not None else ""),
                "balance": str(inv.get("Balance") if inv.get("Balance") is not None else ""),
                "currency": _ref_value(inv.get("CurrencyRef")) or "USD",
                # id only — avoid customer display names in export artifacts
                "customer_ref_id": _ref_value(inv.get("CustomerRef")),
                "source_system": SOURCE_SYSTEM,
            }
        )
    return rows


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in headers})


def _validate_gl_headers(path: Path) -> dict[str, Any]:
    """Dry-run: exact-header detect against demo CSV profiles (no DB)."""
    sys.path.insert(0, str(BACKEND))
    from app.services.demo_csv.detector import detect_csv_kind, header_mismatch_report

    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        headers = next(reader, [])
    kind = detect_csv_kind(headers)
    report = header_mismatch_report(headers).get("gl_actuals", {})
    return {
        "detected_kind": kind,
        "gl_actuals_missing": report.get("missing", []),
        "gl_actuals_extra": report.get("extra", []),
        "ok": kind == "gl_actuals",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export QBO sandbox → SMPL CSV shapes (read-only)")
    parser.add_argument("--max-accounts", type=int, default=500)
    parser.add_argument("--max-journal-entries", type=int, default=200)
    parser.add_argument("--max-invoices", type=int, default=50)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    cfg = load_qbo_config()
    import os

    for key in ("CONNECTOR_QBO_REALM_ID", "CONNECTOR_QBO_REFRESH_TOKEN"):
        if os.environ.get(key):
            cfg[key] = os.environ[key]

    client_id = (cfg.get("CONNECTOR_QBO_CLIENT_ID") or "").strip()
    client_secret = (cfg.get("CONNECTOR_QBO_CLIENT_SECRET") or "").strip()
    realm_id = (cfg.get("CONNECTOR_QBO_REALM_ID") or "").strip()
    refresh_token = (cfg.get("CONNECTOR_QBO_REFRESH_TOKEN") or "").strip()
    missing = [
        name
        for name, val in (
            ("CONNECTOR_QBO_CLIENT_ID", client_id),
            ("CONNECTOR_QBO_CLIENT_SECRET", client_secret),
            ("CONNECTOR_QBO_REALM_ID", realm_id),
            ("CONNECTOR_QBO_REFRESH_TOKEN", refresh_token),
        )
        if not val
    ]
    if missing:
        raise SystemExit(f"Missing required secrets: {', '.join(missing)}")

    print("QBO -> SMPL export (read-only)")
    print(f"  realm_id:  {_mask(realm_id, keep=3)}")
    print(f"  base:      {SANDBOX_BASE}")
    print(f"  out_dir:   {args.out_dir}")
    print()

    tokens = refresh_access_token(client_id, client_secret, refresh_token)
    access = (tokens.get("access_token") or "").strip()
    if not access:
        raise SystemExit(f"Refresh response missing access_token. Keys: {list(tokens)}")
    print(f"  access_token: refreshed (expires_in={tokens.get('expires_in')}s)")

    new_refresh = (tokens.get("refresh_token") or "").strip()
    if new_refresh and new_refresh != refresh_token:
        upsert_secrets({"CONNECTOR_QBO_REFRESH_TOKEN": new_refresh})
        print("  refresh_token: rotated and saved to secrets.env")

    accounts = _paginate_query(
        access, realm_id, "Account", max_results=args.max_accounts
    )
    print(f"  Account: {len(accounts)} row(s)")
    journal_entries = _paginate_query(
        access, realm_id, "JournalEntry", max_results=args.max_journal_entries
    )
    print(f"  JournalEntry: {len(journal_entries)} row(s)")
    invoices = _paginate_query(
        access, realm_id, "Invoice", max_results=args.max_invoices
    )
    print(f"  Invoice: {len(invoices)} row(s)")

    # Ensure JE account refs resolve even if not in the first Account page
    accounts_by_id = _build_account_index(accounts)
    missing_ids: set[str] = set()
    for je in journal_entries:
        for line in je.get("Line") or []:
            if not isinstance(line, dict):
                continue
            detail = line.get("JournalEntryLineDetail") or {}
            if not isinstance(detail, dict):
                continue
            aid = _ref_value(detail.get("AccountRef"))
            if aid and aid not in accounts_by_id:
                missing_ids.add(aid)
    for aid in sorted(missing_ids):
        try:
            payload = qbo_get(
                access,
                f"/v3/company/{realm_id}/account/{aid}?minorversion=65",
            )
            acct = payload.get("Account")
            if isinstance(acct, dict) and acct.get("Id"):
                accounts_by_id[str(acct["Id"])] = acct
                accounts.append(acct)
        except Exception as exc:  # noqa: BLE001
            print(f"  warn: could not fetch Account {aid}: {exc}")

    coa_rows = map_accounts_to_coa(accounts)
    gl_rows = map_journal_entries_to_gl(journal_entries, accounts_by_id)
    inv_rows = map_invoices_staging(invoices)

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    gl_path = out_dir / "gl_actuals.csv"
    coa_path = out_dir / "chart_of_accounts.csv"
    inv_path = out_dir / "invoices_staging.csv"
    manifest_path = out_dir / "export_manifest.json"

    _write_csv(gl_path, GL_ACTUALS_HEADERS, gl_rows)
    _write_csv(coa_path, COA_HEADERS, coa_rows)
    _write_csv(inv_path, INVOICE_STAGING_HEADERS, inv_rows)

    validation = _validate_gl_headers(gl_path)
    print()
    print(f"  wrote {gl_path} ({len(gl_rows)} rows)")
    print(f"  wrote {coa_path} ({len(coa_rows)} rows)")
    print(f"  wrote {inv_path} ({len(inv_rows)} rows)")
    print(
        f"  header validation: detected={validation['detected_kind']!r} "
        f"ok={validation['ok']}"
    )
    if not validation["ok"]:
        print(f"    missing: {validation['gl_actuals_missing']}")
        print(f"    extra:   {validation['gl_actuals_extra']}")

    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "environment": "sandbox",
        "api_base": SANDBOX_BASE,
        "realm_id_masked": _mask(realm_id, keep=3),
        "read_only": True,
        "ingest": "export_only",
        "counts": {
            "accounts_pulled": len(accounts),
            "journal_entries_pulled": len(journal_entries),
            "invoices_pulled": len(invoices),
            "coa_rows": len(coa_rows),
            "gl_actuals_rows": len(gl_rows),
            "invoice_staging_rows": len(inv_rows),
        },
        "files": {
            "gl_actuals": str(gl_path),
            "chart_of_accounts": str(coa_path),
            "invoices_staging": str(inv_path),
        },
        "validation": validation,
        "notes": [
            "gl_actuals.csv matches expanded demo CSV profile (detect_csv_kind == gl_actuals).",
            "chart_of_accounts.csv matches ERP_Chart_of_Accounts_Export staging columns (not a typed mart).",
            "invoices_staging.csv is a slim QBO-oriented staging file — not exact invoices mart headers.",
            "No org ingest performed by this script.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"  wrote {manifest_path}")
    print()
    if not validation["ok"]:
        sys.exit(1)
    print("Export complete (export-only; not ingested into an org).")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)
