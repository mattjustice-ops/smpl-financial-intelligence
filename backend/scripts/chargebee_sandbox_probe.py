"""Read-only Chargebee TEST site probe.

Loads CONNECTOR_CHARGEBEE_SITE + CONNECTOR_CHARGEBEE_API_KEY from
backend/secrets.env, lists customers / subscriptions / invoices / items
(or legacy plans), writes a summary JSON under backend/tmp/, and optionally
a thin export stub under backend/tmp/chargebee_export/ mapped toward SMPL
billing CSV headers. Export-only — no org ingest (especially not Demo Co).

Usage (from repo root):
  python backend/scripts/chargebee_sandbox_probe.py
"""
from __future__ import annotations

import base64
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parent.parent
SECRETS_PATH = BACKEND / "secrets.env"
ENV_PATH = BACKEND / ".env"
OUT_PATH = BACKEND / "tmp" / "chargebee_sandbox_probe_summary.json"
EXPORT_DIR = BACKEND / "tmp" / "chargebee_export"

# Compact demo_csv headers (same spine as Stripe export) — stub only
SUBSCRIPTIONS_HEADERS = [
    "subscription_id",
    "customer_id",
    "product",
    "billing_cadence",
    "start_date",
    "end_date",
    "current_mrr",
    "current_arr",
    "status",
    "currency",
]
INVOICES_HEADERS = [
    "invoice_id",
    "customer_id",
    "invoice_period",
    "invoice_date",
    "due_date",
    "invoice_amount",
    "payment_status",
    "billing_cadence",
    "currency",
]

# Safety cap so a huge site cannot hang the probe
MAX_PAGES = 50
PAGE_LIMIT = 100


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            out[key] = val
    return out


def load_chargebee_config() -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in (ENV_PATH, SECRETS_PATH):
        merged.update(_parse_env_file(path))
    for key in ("CONNECTOR_CHARGEBEE_SITE", "CONNECTOR_CHARGEBEE_API_KEY"):
        if os.environ.get(key):
            merged[key] = os.environ[key]
    return merged


def _mask(value: str, keep: int = 4) -> str:
    if not value:
        return "(empty)"
    if len(value) <= keep * 2:
        return "***"
    return f"{value[:keep]}...{value[-keep:]} (len={len(value)})"


def _assert_test_key(api_key: str) -> None:
    if not api_key.startswith("test_"):
        raise SystemExit(
            "Refusing to run: CONNECTOR_CHARGEBEE_API_KEY must be a TEST key "
            "(prefix test_). Live keys are not allowed for this probe."
        )


def chargebee_get(site: str, api_key: str, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    qs = f"?{urllib.parse.urlencode(params)}" if params else ""
    url = f"https://{site}.chargebee.com/api/v2/{path.lstrip('/')}{qs}"
    basic = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Basic {basic}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Chargebee GET /{path} failed ({exc.code}): {detail[:500]}") from exc


def _unwrap_list(payload: dict[str, Any], resource: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in payload.get("list") or []:
        if not isinstance(entry, dict):
            continue
        obj = entry.get(resource)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def list_all(
    site: str,
    api_key: str,
    resource: str,
    *,
    path: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Paginate a Chargebee list endpoint. Returns (rows, meta)."""
    endpoint = path or resource
    rows: list[dict[str, Any]] = []
    offset: str | None = None
    pages = 0
    truncated = False
    while pages < MAX_PAGES:
        params: dict[str, str] = {"limit": str(PAGE_LIMIT)}
        if offset:
            params["offset"] = offset
        payload = chargebee_get(site, api_key, endpoint, params)
        batch = _unwrap_list(payload, resource)
        rows.extend(batch)
        pages += 1
        next_offset = payload.get("next_offset")
        if not next_offset:
            break
        offset = str(next_offset)
    else:
        truncated = True
    meta = {
        "ok": True,
        "count": len(rows),
        "pages": pages,
        "truncated": truncated,
        "path": endpoint,
    }
    return rows, meta


def _sample_fields(rows: list[dict[str, Any]], n: int = 3) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows[:n]:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                keys.append(k)
    return keys[:25]


def _id_samples(rows: list[dict[str, Any]], n: int = 5) -> list[str]:
    out: list[str] = []
    for row in rows[:n]:
        rid = row.get("id")
        if rid:
            out.append(str(rid))
    return out


def _ts_to_date(ts: Any) -> str:
    if ts is None or ts == "":
        return ""
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError):
        return ""


def _cents_to_money(cents: Any) -> str:
    if cents is None or cents == "":
        return ""
    try:
        return f"{int(cents) / 100:.2f}"
    except (TypeError, ValueError):
        return ""


def _billing_cadence(sub: dict[str, Any]) -> str:
    # PC2: subscription_items; PC1: plan_unit_price + billing_period_unit
    unit = (sub.get("billing_period_unit") or "").lower()
    period = sub.get("billing_period")
    if unit == "month" and period == 1:
        return "monthly"
    if unit == "month" and period == 3:
        return "quarterly"
    if unit == "year" and (period in (None, 1)):
        return "annual"
    if unit:
        return f"{period or 1}_{unit}"
    return ""


def _product_label(sub: dict[str, Any]) -> str:
    items = sub.get("subscription_items") or []
    if isinstance(items, list) and items:
        first = items[0] if isinstance(items[0], dict) else {}
        return str(first.get("item_price_id") or first.get("item_id") or "")
    return str(sub.get("plan_id") or "")


def write_export_stub(
    *,
    site: str,
    subscriptions: list[dict[str, Any]],
    invoices: list[dict[str, Any]],
) -> dict[str, Any]:
    """Header + lightly mapped rows toward SMPL billing shapes (not full export)."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    sub_rows: list[dict[str, str]] = []
    for sub in subscriptions:
        mrr = _cents_to_money(sub.get("mrr"))
        arr = ""
        if mrr:
            try:
                arr = f"{float(mrr) * 12:.2f}"
            except ValueError:
                arr = ""
        sub_rows.append(
            {
                "subscription_id": str(sub.get("id") or ""),
                "customer_id": str(sub.get("customer_id") or ""),
                "product": _product_label(sub),
                "billing_cadence": _billing_cadence(sub),
                "start_date": _ts_to_date(sub.get("started_at") or sub.get("start_date")),
                "end_date": _ts_to_date(sub.get("cancelled_at") or sub.get("current_term_end")),
                "current_mrr": mrr,
                "current_arr": arr,
                "status": str(sub.get("status") or ""),
                "currency": str(sub.get("currency_code") or ""),
            }
        )

    inv_rows: list[dict[str, str]] = []
    for inv in invoices:
        inv_rows.append(
            {
                "invoice_id": str(inv.get("id") or ""),
                "customer_id": str(inv.get("customer_id") or ""),
                "invoice_period": _ts_to_date(inv.get("date"))[:7] if inv.get("date") else "",
                "invoice_date": _ts_to_date(inv.get("date")),
                "due_date": _ts_to_date(inv.get("due_date")),
                "invoice_amount": _cents_to_money(inv.get("total")),
                "payment_status": str(inv.get("status") or ""),
                "billing_cadence": "",
                "currency": str(inv.get("currency_code") or ""),
            }
        )

    sub_path = EXPORT_DIR / "subscriptions.csv"
    inv_path = EXPORT_DIR / "invoices.csv"
    with sub_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SUBSCRIPTIONS_HEADERS)
        writer.writeheader()
        writer.writerows(sub_rows)
    with inv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=INVOICES_HEADERS)
        writer.writeheader()
        writer.writerows(inv_rows)

    next_step = (
        "Align Chargebee sample customers/subscriptions to Net Demo Co naming "
        "(shared customer_master spine like Stripe Quick Demo Co), then flesh out "
        "customers/payments/mrr_waterfall export. Do not ingest into SMPL Demo Co."
    )
    manifest = {
        "written_at": datetime.now(timezone.utc).isoformat(),
        "site": site,
        "source_system": "chargebee",
        "read_only": True,
        "ingest": False,
        "files": {
            "subscriptions.csv": {"rows": len(sub_rows), "headers": SUBSCRIPTIONS_HEADERS},
            "invoices.csv": {"rows": len(inv_rows), "headers": INVOICES_HEADERS},
        },
        "mapping_notes": [
            "subscription.mrr (cents) → current_mrr; ARR = MRR*12 when mrr present",
            "subscription_items[0].item_price_id (or plan_id) → product",
            "invoice.total (cents) → invoice_amount; invoice.status → payment_status",
            "Stub pass — billing_cadence on invoices left blank; no payments/mrr_waterfall yet",
        ],
        "next_step": next_step,
    }
    (EXPORT_DIR / "export_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "written": True,
        "dir": str(EXPORT_DIR),
        "subscription_rows": len(sub_rows),
        "invoice_rows": len(inv_rows),
        "next_step": next_step,
    }


def main() -> None:
    cfg = load_chargebee_config()
    site = (cfg.get("CONNECTOR_CHARGEBEE_SITE") or "").strip()
    api_key = (cfg.get("CONNECTOR_CHARGEBEE_API_KEY") or "").strip()

    if not site:
        raise SystemExit("Missing CONNECTOR_CHARGEBEE_SITE (hostname only, e.g. smpl-ai-test)")
    if not api_key:
        raise SystemExit("Missing CONNECTOR_CHARGEBEE_API_KEY")
    if "." in site or "/" in site or "chargebee" in site.lower():
        raise SystemExit(
            "CONNECTOR_CHARGEBEE_SITE must be the subdomain only "
            "(e.g. smpl-ai-test), not a full URL."
        )
    _assert_test_key(api_key)

    api_base = f"https://{site}.chargebee.com/api/v2/"
    print("Chargebee sandbox probe (read-only)")
    print(f"  site:     {site}")
    print(f"  api_key:  {_mask(api_key)}")
    print(f"  base:     {api_base}")
    print()

    entities: dict[str, Any] = {}
    errors: list[dict[str, str]] = []
    customers: list[dict[str, Any]] = []
    subscriptions: list[dict[str, Any]] = []
    invoices: list[dict[str, Any]] = []

    for resource in ("customer", "subscription", "invoice"):
        plural = f"{resource}s"
        try:
            rows, meta = list_all(site, api_key, resource, path=plural)
            meta["field_names_sample"] = _sample_fields(rows)
            meta["id_samples"] = _id_samples(rows)
            if resource == "subscription":
                meta["status_samples"] = sorted(
                    {str(r.get("status")) for r in rows if r.get("status")}
                )[:10]
            if resource == "invoice":
                meta["status_samples"] = sorted(
                    {str(r.get("status")) for r in rows if r.get("status")}
                )[:10]
            entities[plural] = meta
            print(f"  {plural}: {meta['count']} (pages={meta['pages']})")
            if resource == "customer":
                customers = rows
            elif resource == "subscription":
                subscriptions = rows
            else:
                invoices = rows
        except Exception as exc:  # noqa: BLE001
            entities[plural] = {"ok": False, "count": 0, "path": plural}
            errors.append({"entity": plural, "error": str(exc)[:300]})
            print(f"  {plural}: FAIL — {exc}")

    # Product Catalog 2.0 items; fall back to PC1 plans
    items_ok = False
    try:
        item_rows, item_meta = list_all(site, api_key, "item", path="items")
        item_meta["field_names_sample"] = _sample_fields(item_rows)
        item_meta["id_samples"] = _id_samples(item_rows)
        item_meta["catalog"] = "pc2_items"
        entities["items"] = item_meta
        items_ok = True
        print(f"  items: {item_meta['count']} (pages={item_meta['pages']})")
    except Exception as exc:  # noqa: BLE001
        entities["items"] = {"ok": False, "count": 0, "path": "items", "catalog": "pc2_items"}
        errors.append({"entity": "items", "error": str(exc)[:300]})
        print(f"  items: FAIL — {exc}")

    if not items_ok:
        try:
            plan_rows, plan_meta = list_all(site, api_key, "plan", path="plans")
            plan_meta["field_names_sample"] = _sample_fields(plan_rows)
            plan_meta["id_samples"] = _id_samples(plan_rows)
            plan_meta["catalog"] = "pc1_plans"
            entities["plans"] = plan_meta
            print(f"  plans (PC1 fallback): {plan_meta['count']} (pages={plan_meta['pages']})")
        except Exception as exc:  # noqa: BLE001
            entities["plans"] = {"ok": False, "count": 0, "path": "plans", "catalog": "pc1_plans"}
            errors.append({"entity": "plans", "error": str(exc)[:300]})
            print(f"  plans: FAIL — {exc}")

    sample_data_present = any(
        (entities.get(k) or {}).get("ok") and (entities.get(k) or {}).get("count", 0) > 0
        for k in ("customers", "subscriptions", "invoices")
    )

    export_info: dict[str, Any]
    if sample_data_present and (subscriptions or invoices):
        export_info = write_export_stub(
            site=site, subscriptions=subscriptions, invoices=invoices
        )
        print(
            f"  export stub: {export_info['subscription_rows']} subs / "
            f"{export_info['invoice_rows']} invoices -> {EXPORT_DIR}"
        )
    else:
        export_info = {
            "written": False,
            "reason": "no customers/subscriptions/invoices to map",
            "next_step": (
                "Confirm sample data in Chargebee UI or seed a Net Demo Co–aligned "
                "catalog, then re-run this probe / add chargebee_export_to_smpl.py."
            ),
        }
        print("  export stub: skipped (no sample billing rows)")

    summary = {
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "environment": "test",
        "site": site,
        "api_base": api_base,
        "api_key_masked": _mask(api_key),
        "read_only": True,
        "ingest": False,
        "sample_data_present": sample_data_present,
        "counts": {
            "customers": len(customers),
            "subscriptions": len(subscriptions),
            "invoices": len(invoices),
            "items": (entities.get("items") or {}).get("count", 0)
            if (entities.get("items") or {}).get("ok")
            else 0,
            "plans": (entities.get("plans") or {}).get("count", 0)
            if (entities.get("plans") or {}).get("ok")
            else 0,
        },
        "entities": entities,
        "export_stub": export_info,
        "errors": errors,
        "success": bool(entities.get("customers", {}).get("ok")) and not any(
            e.get("entity") == "customers" for e in errors
        ),
        "next_step": export_info.get("next_step")
        or (
            "Map Chargebee sample billing to Net Demo Co customer_master and "
            "add a full chargebee_export_to_smpl.py (customers/payments/mrr_waterfall)."
        ),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print()
    print(f"Wrote summary: {OUT_PATH}")
    print(f"Sample data present: {sample_data_present}")
    print(f"Overall success: {summary['success']}")
    if not summary["success"]:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)
