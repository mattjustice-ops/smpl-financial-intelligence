"""Demo CSV: exact-header detection and PostgreSQL upsert loaders."""

from app.services.demo_csv.detector import detect_csv_kind, header_mismatch_report, normalize_headers
from app.services.demo_csv.loader import (
    SEED_FILES_IN_ORDER,
    load_demo_csv,
    load_demo_csv_core,
    parse_csv,
    seed_demo_csv_folder,
)

__all__ = [
    "SEED_FILES_IN_ORDER",
    "detect_csv_kind",
    "header_mismatch_report",
    "load_demo_csv",
    "load_demo_csv_core",
    "normalize_headers",
    "parse_csv",
    "seed_demo_csv_folder",
]
