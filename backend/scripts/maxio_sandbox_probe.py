"""Read-only Maxio Advanced Billing (Chargify) sandbox probe.

Loads CONNECTOR_MAXIO_SITE + CONNECTOR_MAXIO_API_KEY from backend/secrets.env
(or .env / process env), lists customers / subscriptions / invoices / products,
optionally probes Insights MRR movements, writes a summary JSON under
backend/tmp/, and a thin CSV stub under backend/tmp/maxio_export/ mapped toward
SMPL billing CSV headers. Export-only — no org ingest (especially not Demo Co).

Auth (public Maxio docs): HTTP Basic with API key as username and literal `x`
as password against https://{site}.chargify.com

Usage (from repo root):
  python backend/scripts/maxio_sandbox_probe.py

Without credentials the script exits clearly — it does not invent API responses.
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
OUT_PATH = BACKEND / "tmp" / "maxio_sandbox_probe_summary.json"
EXPORT_DIR = BACKEND / "tmp" / "maxio_export"

# Compact demo_csv headers (same spine as Stripe / Chargebee export) — stub only
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
MRR_WATERFALL_HEADERS = [
    "period",
    "customer_id",
    "beginning_mrr",
    "new_mrr",
    "expansion_mrr",
    "contraction_mrr",
    "churn_mrr",
    "reactivation_mrr",
    "ending_mrr",
    "movement_type",
]

MAX_PAGES = 50
PAGE_LIMIT = 200  # Advanced Billing max per_page for most list endpoints


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


def load_maxio_config() -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in (ENV_PATH, SECRETS_PATH):
        merged.update(_parse_env_file(path))
    for key in ("CONNECTOR_MAXIO_SITE", "CONNECTOR_MAXIO_API_KEY"):
        if os.environ.get(key):
            merged[key] = os.environ[key]
    return merged


def _mask(value: str, keep: int = 4) -> str:
    if not value:
        return "(empty)"
    if len(value) <= keep * 2:
        return "***"
    return f"{value[:keep]}...{value[-keep:]} (len={len(value)})"


def maxio_get(
    site: str,
    api_key: str,
    path: str,
    params: dict[str, str] | None = None,
) -> Any:
    qs = f"?{urllib.parse.urlencode(params)}" if params else ""
    url = f"https://{site}.chargify.com/{path.lstrip('/')}{qs}"
    # Advanced Billing: Basic api_key:x  (Chargebee uses api_key: empty password)
    basic = base64.b64encode(f"{api_key}:x".encode("utf-8")).decode("ascii")
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Basic {basic}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Maxio GET /{path} failed ({exc.code}): {detail[:500]}") from exc


def _unwrap_list(payload: Any, resource: str) -> list[dict[str, Any]]:
    """Unwrap Chargify-style [{resource: {...}}, ...] or {resource_plural: [...]}."""
    rows: list[dict[str, Any]] = []
    if isinstance(payload, list):
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            obj = entry.get(resource)
            if isinstance(obj, dict):
                rows.append(obj)
            elif "id" in entry or "uid" in entry:
                rows.append(entry)
        return rows
    if isinstance(payload, dict):
        plural = f"{resource}s"
        nested = payload.get(plural) or payload.get(resource)
        if isinstance(nested, list):
            for entry in nested:
                if not isinstance(entry, dict):
                    continue
                obj = entry.get(resource) if resource in entry else entry
                if isinstance(obj, dict):
                    rows.append(obj)
            return rows
        # Single object wrap
        obj = payload.get(resource)
        if isinstance(obj, dict):
            return [obj]
    return rows


def list_all(
    site: str,
    api_key: str,
    resource: str,
    *,
    path: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Paginate an Advanced Billing list endpoint (page / per_page)."""
    rows: list[dict[str, Any]] = []
    pages = 0
    truncated = False
    page = 1
    while pages < MAX_PAGES:
        params = {"page": str(page), "per_page": str(PAGE_LIMIT)}
        payload = maxio_get(site, api_key, path, params)
        batch = _unwrap_list(payload, resource)
        rows.extend(batch)
        pages += 1
        if len(batch) < PAGE_LIMIT:
            break
        page += 1
    else:
        truncated = True
    meta = {
        "ok": True,
        "count": len(rows),
        "pages": pages,
        "truncated": truncated,
        "path": path,
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
        rid = row.get("id") or row.get("uid")
        if rid is not None:
            out.append(str(rid))
    return out


def _iso_date(value: Any) -> str:
    if value is None or value == "":
        return ""
    s = str(value)
    # ISO timestamps: 2016-11-14T14:48:12-05:00 or date-only
    if "T" in s:
        return s.split("T", 1)[0]
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return ""


def _cents_to_money(cents: Any) -> str:
    if cents is None or cents == "":
        return ""
    try:
        return f"{int(cents) / 100:.2f}"
    except (TypeError, ValueError):
        return ""


def _money_str(value: Any) -> str:
    """Invoice amounts are already decimal strings in Relationship Invoicing."""
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _billing_cadence(sub: dict[str, Any]) -> str:
    product = sub.get("product") if isinstance(sub.get("product"), dict) else {}
    unit = str(product.get("interval_unit") or "").lower()
    period = product.get("interval")
    if unit == "month" and period == 1:
        return "monthly"
    if unit == "month" and period == 3:
        return "quarterly"
    if unit == "month" and period == 12:
        return "annual"
    if unit == "year" and period in (None, 1):
        return "annual"
    if unit:
        return f"{period or 1}_{unit}"
    return ""


def _product_label(sub: dict[str, Any]) -> str:
    product = sub.get("product") if isinstance(sub.get("product"), dict) else {}
    return str(product.get("handle") or product.get("name") or product.get("id") or "")


def _customer_id(sub: dict[str, Any]) -> str:
    cust = sub.get("customer") if isinstance(sub.get("customer"), dict) else {}
    cid = cust.get("id") or sub.get("customer_id")
    return str(cid) if cid is not None else ""


def _normalize_mrr_cents(sub: dict[str, Any]) -> int | None:
    """Approximate monthly recurring from product price + interval (stub).

    Prefer Insights /mrr.json or per-subscription MRR when available; this is a
    first-pass mapping from list-subscription fields only.
    """
    product = sub.get("product") if isinstance(sub.get("product"), dict) else {}
    price = product.get("price_in_cents")
    if price is None:
        price = sub.get("product_price_in_cents")
    if price is None:
        # current_billing_amount_in_cents is period amount, not always monthly
        price = sub.get("current_billing_amount_in_cents")
        if price is None:
            return None
        unit = str(product.get("interval_unit") or "").lower()
        period = product.get("interval") or 1
        try:
            amount = int(price)
        except (TypeError, ValueError):
            return None
        if unit == "year" or (unit == "month" and int(period) == 12):
            return amount // 12
        if unit == "month" and int(period) > 1:
            return amount // int(period)
        return amount
    try:
        amount = int(price)
    except (TypeError, ValueError):
        return None
    unit = str(product.get("interval_unit") or "").lower()
    period = product.get("interval") or 1
    try:
        period_i = int(period)
    except (TypeError, ValueError):
        period_i = 1
    if unit == "year" or (unit == "month" and period_i == 12):
        return amount // 12
    if unit == "month" and period_i > 1:
        return amount // period_i
    return amount


def _category_to_waterfall(category: str) -> str:
    c = (category or "").lower()
    if c in ("new_business", "signup", "new"):
        return "new_mrr"
    if c in ("expansion", "upgrade"):
        return "expansion_mrr"
    if c in ("contraction", "downgrade"):
        return "contraction_mrr"
    if c in ("churn", "cancellation", "cancel"):
        return "churn_mrr"
    if c in ("reactivation", "re-activation", "reactivate"):
        return "reactivation_mrr"
    return "movement_type"


def write_export_stub(
    *,
    site: str,
    subscriptions: list[dict[str, Any]],
    invoices: list[dict[str, Any]],
    mrr_movements: list[dict[str, Any]],
) -> dict[str, Any]:
    """Header + lightly mapped rows toward SMPL billing shapes (not full export)."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    sub_rows: list[dict[str, str]] = []
    for sub in subscriptions:
        mrr_cents = _normalize_mrr_cents(sub)
        mrr = _cents_to_money(mrr_cents) if mrr_cents is not None else ""
        arr = ""
        if mrr:
            try:
                arr = f"{float(mrr) * 12:.2f}"
            except ValueError:
                arr = ""
        currency = ""
        product = sub.get("product") if isinstance(sub.get("product"), dict) else {}
        currency = str(sub.get("currency") or product.get("currency") or "")
        sub_rows.append(
            {
                "subscription_id": str(sub.get("id") or ""),
                "customer_id": _customer_id(sub),
                "product": _product_label(sub),
                "billing_cadence": _billing_cadence(sub),
                "start_date": _iso_date(sub.get("activated_at") or sub.get("created_at")),
                "end_date": _iso_date(sub.get("canceled_at") or sub.get("expires_at")),
                "current_mrr": mrr,
                "current_arr": arr,
                "status": str(sub.get("state") or ""),
                "currency": currency,
            }
        )

    inv_rows: list[dict[str, str]] = []
    for inv in invoices:
        issue = _iso_date(inv.get("issue_date") or inv.get("created_at"))
        inv_rows.append(
            {
                "invoice_id": str(inv.get("uid") or inv.get("id") or ""),
                "customer_id": str(inv.get("customer_id") or ""),
                "invoice_period": issue[:7] if issue else "",
                "invoice_date": issue,
                "due_date": _iso_date(inv.get("due_date")),
                "invoice_amount": _money_str(inv.get("total_amount") or inv.get("total_in_cents")),
                "payment_status": str(inv.get("status") or ""),
                "billing_cadence": "",
                "currency": str(inv.get("currency") or ""),
            }
        )

    # Sparse waterfall stub from Insights movements (category → column); not a full bridge
    wf_rows: list[dict[str, str]] = []
    for mov in mrr_movements:
        ts = _iso_date(mov.get("timestamp"))
        period = ts[:7] if ts else ""
        category = str(mov.get("category") or "")
        col = _category_to_waterfall(category)
        amount = _cents_to_money(mov.get("amount_in_cents"))
        row = {h: "" for h in MRR_WATERFALL_HEADERS}
        row["period"] = period
        row["customer_id"] = ""  # movements carry subscription_id / subscriber_name
        row["movement_type"] = category
        if col in row and col != "movement_type":
            row[col] = amount
        elif amount:
            row["new_mrr"] = amount  # fallback bucket
        # stash subscription id in notes-like field via movement_type already
        if mov.get("subscription_id") is not None:
            row["customer_id"] = f"sub:{mov.get('subscription_id')}"
        wf_rows.append(row)

    sub_path = EXPORT_DIR / "subscriptions.csv"
    inv_path = EXPORT_DIR / "invoices.csv"
    wf_path = EXPORT_DIR / "mrr_waterfall.csv"
    with sub_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SUBSCRIPTIONS_HEADERS)
        writer.writeheader()
        writer.writerows(sub_rows)
    with inv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=INVOICES_HEADERS)
        writer.writeheader()
        writer.writerows(inv_rows)
    with wf_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=MRR_WATERFALL_HEADERS)
        writer.writeheader()
        writer.writerows(wf_rows)

    next_step = (
        "Align Maxio sample customers/subscriptions to Net Demo Co naming "
        "(shared customer_master spine like Stripe Quick Demo Co), then flesh out "
        "customers/payments export. Prefer Insights MRR (or Core) for accurate ARR; "
        "list-subscription price→MRR is a stub. Do not ingest into SMPL Demo Co."
    )
    files: dict[str, Any] = {
        "subscriptions.csv": {"rows": len(sub_rows), "headers": SUBSCRIPTIONS_HEADERS},
        "invoices.csv": {"rows": len(inv_rows), "headers": INVOICES_HEADERS},
        "mrr_waterfall.csv": {"rows": len(wf_rows), "headers": MRR_WATERFALL_HEADERS},
    }
    manifest = {
        "written_at": datetime.now(timezone.utc).isoformat(),
        "site": site,
        "source_system": "maxio_advanced_billing",
        "read_only": True,
        "ingest": False,
        "files": files,
        "mapping_notes": [
            "subscription.product.handle → product; state → status",
            "product.price_in_cents + interval → current_mrr (approx); ARR = MRR*12",
            "invoice.uid → invoice_id; total_amount (decimal) → invoice_amount; status → payment_status",
            "mrr_movements.category → waterfall column (sparse stub); customer_id may be sub:{id}",
            "Insights /mrr_movements.json is deprecated upstream — still useful for Day-1 shape",
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
        "mrr_waterfall_rows": len(wf_rows),
        "next_step": next_step,
    }


def main() -> None:
    cfg = load_maxio_config()
    site = (cfg.get("CONNECTOR_MAXIO_SITE") or "").strip()
    api_key = (cfg.get("CONNECTOR_MAXIO_API_KEY") or "").strip()

    if not site and not api_key:
        raise SystemExit(
            "Missing Maxio credentials. Set CONNECTOR_MAXIO_SITE and "
            "CONNECTOR_MAXIO_API_KEY in backend/secrets.env (gitignored) or the environment.\n"
            "  SITE = Advanced Billing subdomain only (e.g. acme-sandbox), not a full URL.\n"
            "  API_KEY = site API key from Config > Integrations > API Keys.\n"
            "Auth: Basic {API_KEY}:x against https://{SITE}.chargify.com\n"
            "Ask Nick for partner sandbox site+key, or self-serve signup at "
            "https://app.chargify.com/signup/maxio-billing-sandbox"
        )
    if not site:
        raise SystemExit(
            "Missing CONNECTOR_MAXIO_SITE (hostname only, e.g. acme-sandbox). "
            "Do not include .chargify.com."
        )
    if not api_key:
        raise SystemExit(
            "Missing CONNECTOR_MAXIO_API_KEY (Advanced Billing site API key). "
            "Password for Basic Auth is the literal character x — do not put x in this env var."
        )
    if "." in site or "/" in site or "chargify" in site.lower() or "maxio" in site.lower():
        raise SystemExit(
            "CONNECTOR_MAXIO_SITE must be the subdomain only "
            "(e.g. acme-sandbox), not a full URL."
        )

    api_base = f"https://{site}.chargify.com/"
    print("Maxio Advanced Billing probe (read-only)")
    print(f"  site:     {site}")
    print(f"  api_key:  {_mask(api_key)}")
    print(f"  base:     {api_base}")
    print(f"  auth:     Basic {{api_key}}:x")
    print()

    entities: dict[str, Any] = {}
    errors: list[dict[str, str]] = []
    customers: list[dict[str, Any]] = []
    subscriptions: list[dict[str, Any]] = []
    invoices: list[dict[str, Any]] = []
    mrr_movements: list[dict[str, Any]] = []

    list_targets = (
        ("customer", "customers.json"),
        ("subscription", "subscriptions.json"),
        ("invoice", "invoices.json"),
        ("product", "products.json"),
    )
    for resource, path in list_targets:
        plural = f"{resource}s"
        try:
            rows, meta = list_all(site, api_key, resource, path=path)
            meta["field_names_sample"] = _sample_fields(rows)
            meta["id_samples"] = _id_samples(rows)
            if resource in ("subscription", "invoice"):
                key = "state" if resource == "subscription" else "status"
                meta["status_samples"] = sorted(
                    {str(r.get(key)) for r in rows if r.get(key)}
                )[:10]
            entities[plural] = meta
            print(f"  {plural}: {meta['count']} (pages={meta['pages']})")
            if resource == "customer":
                customers = rows
            elif resource == "subscription":
                subscriptions = rows
            elif resource == "invoice":
                invoices = rows
        except Exception as exc:  # noqa: BLE001
            entities[plural] = {"ok": False, "count": 0, "path": path}
            errors.append({"entity": plural, "error": str(exc)[:300]})
            print(f"  {plural}: FAIL — {exc}")

    # Optional Insights (deprecated but still documented) — non-fatal
    try:
        stats = maxio_get(site, api_key, "stats.json")
        entities["stats"] = {"ok": True, "sample_keys": list(stats.keys())[:20] if isinstance(stats, dict) else []}
        print("  stats.json: ok")
    except Exception as exc:  # noqa: BLE001
        entities["stats"] = {"ok": False, "path": "stats.json"}
        errors.append({"entity": "stats", "error": str(exc)[:300]})
        print(f"  stats.json: FAIL — {exc}")

    try:
        # First page only for movements (per_page max 50 on this endpoint)
        payload = maxio_get(
            site,
            api_key,
            "mrr_movements.json",
            {"page": "1", "per_page": "50"},
        )
        mrr_block = payload.get("mrr") if isinstance(payload, dict) else None
        if isinstance(mrr_block, dict):
            mrr_movements = [
                m for m in (mrr_block.get("movements") or []) if isinstance(m, dict)
            ]
            entities["mrr_movements"] = {
                "ok": True,
                "count": len(mrr_movements),
                "path": "mrr_movements.json",
                "deprecated": True,
                "total_entries": mrr_block.get("total_entries"),
                "field_names_sample": _sample_fields(mrr_movements),
                "category_samples": sorted(
                    {str(m.get("category")) for m in mrr_movements if m.get("category")}
                )[:15],
            }
        else:
            entities["mrr_movements"] = {
                "ok": True,
                "count": 0,
                "path": "mrr_movements.json",
                "deprecated": True,
                "note": "unexpected payload shape",
            }
        print(f"  mrr_movements: {len(mrr_movements)} (page 1, deprecated endpoint)")
    except Exception as exc:  # noqa: BLE001
        entities["mrr_movements"] = {"ok": False, "count": 0, "path": "mrr_movements.json", "deprecated": True}
        errors.append({"entity": "mrr_movements", "error": str(exc)[:300]})
        print(f"  mrr_movements: FAIL — {exc}")

    sample_data_present = any(
        (entities.get(k) or {}).get("ok") and (entities.get(k) or {}).get("count", 0) > 0
        for k in ("customers", "subscriptions", "invoices")
    )

    export_info: dict[str, Any]
    if sample_data_present and (subscriptions or invoices or mrr_movements):
        export_info = write_export_stub(
            site=site,
            subscriptions=subscriptions,
            invoices=invoices,
            mrr_movements=mrr_movements,
        )
        print(
            f"  export stub: {export_info['subscription_rows']} subs / "
            f"{export_info['invoice_rows']} invoices / "
            f"{export_info['mrr_waterfall_rows']} mrr rows -> {EXPORT_DIR}"
        )
    else:
        export_info = {
            "written": False,
            "reason": "no customers/subscriptions/invoices to map",
            "next_step": (
                "Confirm sample data in Advanced Billing UI or seed a Net Demo Co–aligned "
                "catalog, then re-run this probe / maxio_export_to_smpl.py."
            ),
        }
        print("  export stub: skipped (no sample billing rows)")

    summary = {
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "environment": "sandbox_or_site",
        "product_surface": "advanced_billing",
        "site": site,
        "api_base": api_base,
        "api_key_masked": _mask(api_key),
        "auth": "basic_api_key_x",
        "read_only": True,
        "ingest": False,
        "sample_data_present": sample_data_present,
        "billing_arr_targets": [
            "customers",
            "subscriptions",
            "invoices",
            "mrr_waterfall",
        ],
        "counts": {
            "customers": len(customers),
            "subscriptions": len(subscriptions),
            "invoices": len(invoices),
            "products": (entities.get("products") or {}).get("count", 0)
            if (entities.get("products") or {}).get("ok")
            else 0,
            "mrr_movements_page1": len(mrr_movements),
        },
        "entities": entities,
        "export_stub": export_info,
        "errors": errors,
        "success": bool(entities.get("customers", {}).get("ok")) and not any(
            e.get("entity") == "customers" for e in errors
        ),
        "next_step": export_info.get("next_step")
        or (
            "Map Maxio sample billing to Net Demo Co customer_master and "
            "expand maxio_export_to_smpl.py (customers/payments/full mrr_waterfall)."
        ),
        "blocked_surfaces": [
            "maxio_core_api — docs inside Core Admin; need partner access",
            "maxio_mcp — reporting demo only; ask Nick/Kevin for URL+token",
        ],
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
