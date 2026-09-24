"""Thin Maxio Advanced Billing → SMPL billing CSV export stub.

Wraps maxio_sandbox_probe.write_export_stub after a live read, or documents
the expected output layout when credentials are missing.

Full customers/payments/mrr_waterfall bridge lives here later (clone
stripe_export_to_smpl.py). For now this is a thin entrypoint so Day-1
docs can point at one script name.

Usage (from repo root):
  python backend/scripts/maxio_export_to_smpl.py

Requires CONNECTOR_MAXIO_SITE + CONNECTOR_MAXIO_API_KEY (same as probe).
Export-only — no org ingest.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from maxio_sandbox_probe import (  # noqa: E402
    EXPORT_DIR,
    INVOICES_HEADERS,
    MRR_WATERFALL_HEADERS,
    SUBSCRIPTIONS_HEADERS,
    list_all,
    load_maxio_config,
    maxio_get,
    write_export_stub,
)

BACKEND = Path(__file__).resolve().parent.parent
OUT_PATH = BACKEND / "tmp" / "maxio_export_to_smpl_summary.json"


def main() -> None:
    cfg = load_maxio_config()
    site = (cfg.get("CONNECTOR_MAXIO_SITE") or "").strip()
    api_key = (cfg.get("CONNECTOR_MAXIO_API_KEY") or "").strip()

    if not site or not api_key:
        raise SystemExit(
            "set credentials: CONNECTOR_MAXIO_SITE and CONNECTOR_MAXIO_API_KEY "
            "in backend/secrets.env (gitignored) or the environment, then re-run.\n"
            "Expected outputs under backend/tmp/maxio_export/: "
            "subscriptions.csv, invoices.csv, mrr_waterfall.csv, export_manifest.json\n"
            f"Headers (subscriptions): {SUBSCRIPTIONS_HEADERS}\n"
            f"Headers (invoices): {INVOICES_HEADERS}\n"
            f"Headers (mrr_waterfall): {MRR_WATERFALL_HEADERS}"
        )

    if "." in site or "/" in site or "chargify" in site.lower():
        raise SystemExit(
            "CONNECTOR_MAXIO_SITE must be the subdomain only (e.g. acme-sandbox)."
        )

    subscriptions, _ = list_all(site, api_key, "subscription", path="subscriptions.json")
    invoices, _ = list_all(site, api_key, "invoice", path="invoices.json")

    mrr_movements: list = []
    try:
        payload = maxio_get(
            site, api_key, "mrr_movements.json", {"page": "1", "per_page": "50"}
        )
        mrr_block = payload.get("mrr") if isinstance(payload, dict) else None
        if isinstance(mrr_block, dict):
            mrr_movements = [
                m for m in (mrr_block.get("movements") or []) if isinstance(m, dict)
            ]
    except Exception as exc:  # noqa: BLE001
        print(f"  mrr_movements skipped: {exc}")

    export_info = write_export_stub(
        site=site,
        subscriptions=subscriptions,
        invoices=invoices,
        mrr_movements=mrr_movements,
    )

    summary = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source_system": "maxio_advanced_billing",
        "site": site,
        "read_only": True,
        "ingest": False,
        "export": export_info,
        "dir": str(EXPORT_DIR),
        "note": (
            "Stub export — customers.csv / payments.csv not yet; "
            "MRR from list fields is approximate; prefer Insights/Core for ARR."
        ),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote export under {EXPORT_DIR}")
    print(f"Wrote summary: {OUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)
