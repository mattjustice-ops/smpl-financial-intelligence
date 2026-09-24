"""Shared helpers for Quick Demo Co Stripe connector seed/export.

Customer master is the spine for both QBO enrichment and Stripe test data.
Do not ingest into SMPL Demo Co from these scripts.
"""
from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parent.parent
SECRETS_PATH = BACKEND / "secrets.env"
ENV_PATH = BACKEND / ".env"
QUICK_DEMO_DIR = BACKEND / "tmp" / "quick_demo_co"
STRIPE_EXPORT_DIR = BACKEND / "tmp" / "stripe_export"
QBO_EXPORT_DIR = BACKEND / "tmp" / "qbo_export"

SEED_MARKER = "quick_demo_co"
ARCHETYPE = "Quick Demo Co"
SOURCE_SYSTEM = "stripe"

# Exact compact demo_csv headers (detector EXPECTED)
CUSTOMERS_HEADERS = [
    "customer_id",
    "customer_name",
    "segment",
    "industry",
    "status",
    "start_date",
    "billing_cadence",
    "payment_terms",
    "source_crm",
    "netsuite_customer_id",
    "stripe_customer_id",
]
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
PAYMENTS_HEADERS = [
    "payment_id",
    "invoice_id",
    "customer_id",
    "payment_date",
    "payment_amount",
    "payment_method",
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
MASTER_HEADERS = [
    "smpl_customer_id",
    "customer_name",
    "segment",
    "industry",
    "status",
    "start_date",
    "billing_cadence",
    "payment_terms",
    "qbo_customer_ref_id",
    "qbo_sandbox_display_name",
    "plan_tier",
    "platform_mrr",
    "addon_mrr",
    "notes",
]

# QBO Intuit sample names are not SaaS-shaped; we keep them for join/trace only.
# Spine names are Quick Demo Co SaaS customers mapped to invoice-bearing QBO IDs.
CUSTOMER_MASTER: list[dict[str, Any]] = [
    {
        "smpl_customer_id": "QDC-001",
        "customer_name": "Northstar Analytics",
        "segment": "Enterprise",
        "industry": "Software",
        "status": "active",
        "start_date": "2026-01-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "1",
        "qbo_sandbox_display_name": "Amy's Bird Sanctuary",
        "plan_tier": "ent",
        "platform_mrr": "2500",
        "addon_mrr": "300",
        "notes": "stable + addon",
    },
    {
        "smpl_customer_id": "QDC-002",
        "customer_name": "Harbor Logistics",
        "segment": "Mid-Market",
        "industry": "Logistics",
        "status": "active",
        "start_date": "2026-01-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "2",
        "qbo_sandbox_display_name": "Bill's Windsurf Shop",
        "plan_tier": "mm",
        "platform_mrr": "1000",
        "addon_mrr": "0",
        "notes": "stable",
    },
    {
        "smpl_customer_id": "QDC-003",
        "customer_name": "Apex Retail Systems",
        "segment": "Mid-Market",
        "industry": "Retail",
        "status": "active",
        "start_date": "2026-02-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "3",
        "qbo_sandbox_display_name": "Cool Cars",
        "plan_tier": "mm",
        "platform_mrr": "1200",
        "addon_mrr": "0",
        "notes": "new Feb",
    },
    {
        "smpl_customer_id": "QDC-004",
        "customer_name": "Cascade Health Tech",
        "segment": "Enterprise",
        "industry": "Healthcare",
        "status": "active",
        "start_date": "2026-01-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "5",
        "qbo_sandbox_display_name": "Dukes Basketball Camp",
        "plan_tier": "ent",
        "platform_mrr": "2800",
        "addon_mrr": "300",
        "notes": "expanded May (platform bump seeded as current)",
    },
    {
        "smpl_customer_id": "QDC-005",
        "customer_name": "Blue Ridge Media",
        "segment": "SMB",
        "industry": "Media",
        "status": "active",
        "start_date": "2026-03-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 15",
        "qbo_customer_ref_id": "8",
        "qbo_sandbox_display_name": "0969 Ocean View Road",
        "plan_tier": "smb",
        "platform_mrr": "400",
        "addon_mrr": "0",
        "notes": "new Mar",
    },
    {
        "smpl_customer_id": "QDC-006",
        "customer_name": "Summit FinOps",
        "segment": "Mid-Market",
        "industry": "Finance",
        "status": "active",
        "start_date": "2026-01-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "9",
        "qbo_sandbox_display_name": "55 Twin Lane",
        "plan_tier": "mm",
        "platform_mrr": "900",
        "addon_mrr": "0",
        "notes": "stable",
    },
    {
        "smpl_customer_id": "QDC-007",
        "customer_name": "Lattice Data Co",
        "segment": "Enterprise",
        "industry": "Software",
        "status": "active",
        "start_date": "2026-01-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "10",
        "qbo_sandbox_display_name": "Geeta Kalapatapu",
        "plan_tier": "ent",
        "platform_mrr": "2500",
        "addon_mrr": "0",
        "notes": "stable",
    },
    {
        "smpl_customer_id": "QDC-008",
        "customer_name": "Pinnacle Ops",
        "segment": "SMB",
        "industry": "Services",
        "status": "active",
        "start_date": "2026-04-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 15",
        "qbo_customer_ref_id": "12",
        "qbo_sandbox_display_name": "Jeff's Jalopies",
        "plan_tier": "smb",
        "platform_mrr": "350",
        "addon_mrr": "0",
        "notes": "new Apr",
    },
    {
        "smpl_customer_id": "QDC-009",
        "customer_name": "Verdant Energy",
        "segment": "Mid-Market",
        "industry": "Energy",
        "status": "active",
        "start_date": "2026-01-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "13",
        "qbo_sandbox_display_name": "John Melton",
        "plan_tier": "mm",
        "platform_mrr": "1500",
        "addon_mrr": "300",
        "notes": "stable + addon",
    },
    {
        "smpl_customer_id": "QDC-010",
        "customer_name": "Cobalt Security",
        "segment": "SMB",
        "industry": "Security",
        "status": "active",
        "start_date": "2026-02-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 15",
        "qbo_customer_ref_id": "16",
        "qbo_sandbox_display_name": "Kookies by Kathy",
        "plan_tier": "smb",
        "platform_mrr": "600",
        "addon_mrr": "0",
        "notes": "new Feb",
    },
    {
        "smpl_customer_id": "QDC-011",
        "customer_name": "Meridian SaaS",
        "segment": "Mid-Market",
        "industry": "Software",
        "status": "active",
        "start_date": "2026-01-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "17",
        "qbo_sandbox_display_name": "Mark Cho",
        "plan_tier": "mm",
        "platform_mrr": "1100",
        "addon_mrr": "0",
        "notes": "contracted from 1400 (current=1100)",
    },
    {
        "smpl_customer_id": "QDC-012",
        "customer_name": "Helix Biotech",
        "segment": "Enterprise",
        "industry": "Healthcare",
        "status": "active",
        "start_date": "2026-01-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "18",
        "qbo_sandbox_display_name": "Paulsen Medical Supplies",
        "plan_tier": "ent",
        "platform_mrr": "4000",
        "addon_mrr": "300",
        "notes": "logo + addon",
    },
    {
        "smpl_customer_id": "QDC-013",
        "customer_name": "Redwood Commerce",
        "segment": "Mid-Market",
        "industry": "Retail",
        "status": "active",
        "start_date": "2026-01-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "20",
        "qbo_sandbox_display_name": "Red Rock Diner",
        "plan_tier": "mm",
        "platform_mrr": "800",
        "addon_mrr": "0",
        "notes": "stable",
    },
    {
        "smpl_customer_id": "QDC-014",
        "customer_name": "Orbit Mobility",
        "segment": "SMB",
        "industry": "Transportation",
        "status": "active",
        "start_date": "2026-05-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 15",
        "qbo_customer_ref_id": "21",
        "qbo_sandbox_display_name": "Rondonuwu Fruit and Vegi",
        "plan_tier": "smb",
        "platform_mrr": "400",
        "addon_mrr": "0",
        "notes": "new May",
    },
    {
        "smpl_customer_id": "QDC-015",
        "customer_name": "Copperline Design",
        "segment": "SMB",
        "industry": "Design",
        "status": "active",
        "start_date": "2026-03-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 15",
        "qbo_customer_ref_id": "23",
        "qbo_sandbox_display_name": "Barnett Design",
        "plan_tier": "smb",
        "platform_mrr": "550",
        "addon_mrr": "0",
        "notes": "new Mar",
    },
    {
        "smpl_customer_id": "QDC-016",
        "customer_name": "Atlas Workforce",
        "segment": "Mid-Market",
        "industry": "HR Tech",
        "status": "active",
        "start_date": "2026-01-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "24",
        "qbo_sandbox_display_name": "Sonnenschein Family Store",
        "plan_tier": "mm",
        "platform_mrr": "1400",
        "addon_mrr": "0",
        "notes": "stable",
    },
    {
        "smpl_customer_id": "QDC-017",
        "customer_name": "Neon Kitchen OS",
        "segment": "SMB",
        "industry": "Food Tech",
        "status": "churned",
        "start_date": "2026-01-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 15",
        "qbo_customer_ref_id": "25",
        "qbo_sandbox_display_name": "Sushi by Katsuyuki",
        "plan_tier": "smb",
        "platform_mrr": "300",
        "addon_mrr": "0",
        "notes": "churned Apr (seed cancels sub)",
    },
    {
        "smpl_customer_id": "QDC-018",
        "customer_name": "Flux Creative",
        "segment": "Mid-Market",
        "industry": "Media",
        "status": "active",
        "start_date": "2026-01-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "26",
        "qbo_sandbox_display_name": "Travis Waldron",
        "plan_tier": "mm",
        "platform_mrr": "950",
        "addon_mrr": "0",
        "notes": "stable",
    },
    {
        "smpl_customer_id": "QDC-019",
        "customer_name": "Weiskopf Advisory",
        "segment": "Enterprise",
        "industry": "Consulting",
        "status": "active",
        "start_date": "2026-01-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "29",
        "qbo_sandbox_display_name": "Weiskopf Consulting",
        "plan_tier": "ent",
        "platform_mrr": "2200",
        "addon_mrr": "0",
        "notes": "name aligned to QBO consulting sample",
    },
    # Stripe-only (no QBO invoice yet) — reserved for future QBO enrichment
    {
        "smpl_customer_id": "QDC-020",
        "customer_name": "Brightpath EdTech",
        "segment": "Mid-Market",
        "industry": "Education",
        "status": "active",
        "start_date": "2026-04-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "",
        "qbo_sandbox_display_name": "",
        "plan_tier": "mm",
        "platform_mrr": "1300",
        "addon_mrr": "0",
        "notes": "stripe_only; future QBO link",
    },
    {
        "smpl_customer_id": "QDC-021",
        "customer_name": "Quartz Payments",
        "segment": "Enterprise",
        "industry": "FinTech",
        "status": "active",
        "start_date": "2026-01-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "",
        "qbo_sandbox_display_name": "",
        "plan_tier": "ent",
        "platform_mrr": "3500",
        "addon_mrr": "300",
        "notes": "stripe_only",
    },
    {
        "smpl_customer_id": "QDC-022",
        "customer_name": "Softcap Labs",
        "segment": "SMB",
        "industry": "Software",
        "status": "active",
        "start_date": "2026-05-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 15",
        "qbo_customer_ref_id": "",
        "qbo_sandbox_display_name": "",
        "plan_tier": "smb",
        "platform_mrr": "250",
        "addon_mrr": "0",
        "notes": "stripe_only new May",
    },
    {
        "smpl_customer_id": "QDC-023",
        "customer_name": "Ironclad LegalTech",
        "segment": "Mid-Market",
        "industry": "Legal",
        "status": "active",
        "start_date": "2026-02-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "",
        "qbo_sandbox_display_name": "",
        "plan_tier": "mm",
        "platform_mrr": "1600",
        "addon_mrr": "0",
        "notes": "stripe_only",
    },
    {
        "smpl_customer_id": "QDC-024",
        "customer_name": "Daybreak Climate",
        "segment": "Enterprise",
        "industry": "Climate",
        "status": "active",
        "start_date": "2026-03-01",
        "billing_cadence": "monthly",
        "payment_terms": "Net 30",
        "qbo_customer_ref_id": "",
        "qbo_sandbox_display_name": "",
        "plan_tier": "ent",
        "platform_mrr": "2700",
        "addon_mrr": "0",
        "notes": "stripe_only; win-back style logo",
    },
]


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


def load_connector_stripe_key() -> str:
    """Load CONNECTOR_STRIPE_SECRET_KEY only (never STRIPE_SECRET_KEY)."""
    merged: dict[str, str] = {}
    for path in (ENV_PATH, SECRETS_PATH):
        merged.update(_parse_env_file(path))
    key = os.environ.get("CONNECTOR_STRIPE_SECRET_KEY") or merged.get("CONNECTOR_STRIPE_SECRET_KEY") or ""
    if not key:
        raise SystemExit(
            "Missing CONNECTOR_STRIPE_SECRET_KEY in backend/secrets.env "
            "(do not use STRIPE_SECRET_KEY — that is SMPL SaaS billing)."
        )
    if not key.startswith("sk_test_"):
        raise SystemExit(
            f"Refusing non-test key (prefix={key[:8]!r}). "
            "Quick Demo Co seed/export is TEST MODE ONLY."
        )
    # Guardrail: if someone accidentally put the same value in STRIPE_SECRET_KEY, still OK —
    # but we never *read* STRIPE_SECRET_KEY here.
    return key


def write_customer_master(path: Path | None = None) -> Path:
    out = path or (QUICK_DEMO_DIR / "customer_master.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MASTER_HEADERS)
        w.writeheader()
        for row in CUSTOMER_MASTER:
            w.writerow({k: row.get(k, "") for k in MASTER_HEADERS})
    return out


def read_customer_master(path: Path | None = None) -> list[dict[str, str]]:
    p = path or (QUICK_DEMO_DIR / "customer_master.csv")
    if not p.is_file():
        write_customer_master(p)
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({h: row.get(h, "") for h in headers})


def cents(dollars: str | int | float) -> int:
    return int(round(float(dollars) * 100))
