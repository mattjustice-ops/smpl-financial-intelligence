"""Upload manifest generated from the readiness registry.

Every file SMPL ingests supplies a canonical object (``registry.OBJECTS``). The manifest lists each
file, the table the loader writes it to, the load order, which modules need it, and the
questionnaire question that says whether the customer has it. ``check_files`` compares uploaded file
names with the manifest: files it does not declare are reported, never guessed at.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable

from app.services.readiness.registry import CONNECTOR_TYPES, MODULES, OBJECTS, VERSIONS

MANIFEST_COLUMNS: tuple[str, ...] = (
    "load_sequence",
    "file_name",
    "dataset_type",
    "object_id",
    "object",
    "source_system",
    "target_table",
    "requirement",
    "required_by",
    "question",
)

# Build logs, validation summaries, dictionaries and manifests: carried with a dataset, not customer data.
REFERENCE_BASES: frozenset[str] = frozenset(
    {
        "data_dictionary",
        "dataset_summary",
        "normalized_operating_model_summary",
        "opportunity_mix_summary",
        "pipeline_marketing_reconciliation",
        "version_split_modeling_guidance",
    }
)


def file_name(base: str, version: str | None) -> str:
    return f"{version}_{base}.csv" if version else f"{base}.csv"


_VERSION_PREFIXES = frozenset(v.lower() for v in VERSIONS)


def _versioned(name: str) -> bool:
    return Path(name).name.partition("_")[0].lower() in _VERSION_PREFIXES


def _base(name: str) -> str:
    stem = Path(name).name.rsplit(".", 1)[0]
    return (stem.partition("_")[2] if _versioned(name) else stem).lower()


def is_reference(name: str) -> bool:
    base = _base(name)
    return (
        base in REFERENCE_BASES
        or "validation" in base
        or base.endswith("_log")
        or base.endswith("_check")
        or base.endswith("_manifest")
        or base == "master_upload_order"
    )


def upload_target(name: str) -> str | None:
    """The table the loader writes this file to, or None when the loader has no route for it."""
    from app.services.demo_csv.loader import KIND_MODEL, _kind_from_filename, _physical_version_table_name

    if _versioned(name) and _base(name) == "gl_detail":
        return "gl_actuals"
    table = _physical_version_table_name(name)
    if table:
        return table
    kind = _kind_from_filename(name)
    if kind in KIND_MODEL:
        return KIND_MODEL[kind].__tablename__
    return None


def manifest_rows() -> list[dict[str, str]]:
    required_by = {oid: [m.name for m in MODULES if oid in m.required_objects] for oid in OBJECTS}
    connectors = list(CONNECTOR_TYPES)
    entries = []
    for order, obj in enumerate(OBJECTS.values()):
        for index, src in enumerate(obj.files):
            for version in src.versions or (None,):
                rank = VERSIONS.index(version) if version else -1
                entries.append(((obj.tier, connectors.index(obj.connector), order, index, rank), obj, src.base, version))
    entries.sort(key=lambda e: e[0])
    rows = []
    for seq, (_, obj, base, version) in enumerate(entries, start=1):
        name = file_name(base, version)
        modules = required_by[obj.id]
        rows.append(
            {
                "load_sequence": f"{seq:03d}",
                "file_name": name,
                "dataset_type": version or "Shared",
                "object_id": obj.id,
                "object": obj.name,
                "source_system": CONNECTOR_TYPES[obj.connector],
                "target_table": upload_target(name) or "",
                "requirement": "required" if modules else "optional",
                "required_by": "; ".join(modules),
                "question": obj.question or "",
            }
        )
    return rows


def classify(name: str) -> str | None:
    """Canonical object id for an upload file name (case-insensitive), or None if the manifest has no such file."""
    index = {r["file_name"].lower(): r["object_id"] for r in manifest_rows()}
    return index.get(Path(name).name.lower())


def check_files(names: Iterable[str]) -> dict[str, object]:
    """Compare uploaded file names with the manifest.

    mapped: file → object; reference: carried but not customer data; undeclared: no manifest entry
    (load it only after declaring it, or delete it); duplicates: same file name more than once;
    missing: manifest files not uploaded, by object.
    """
    rows = manifest_rows()
    index = {r["file_name"].lower(): r for r in rows}
    seen = [Path(n).name for n in names]
    counts = Counter(n.lower() for n in seen)
    mapped: dict[str, str] = {}
    reference: list[str] = []
    undeclared: list[str] = []
    for n in sorted(set(seen), key=str.lower):
        row = index.get(n.lower())
        if row:
            mapped[n] = row["object_id"]
        elif is_reference(n):
            reference.append(n)
        else:
            undeclared.append(n)
    present = {n.lower() for n in seen}
    missing: dict[str, list[str]] = {}
    for r in rows:
        if r["file_name"].lower() not in present:
            missing.setdefault(r["object_id"], []).append(r["file_name"])
    return {
        "mapped": mapped,
        "reference": reference,
        "undeclared": undeclared,
        "duplicates": sorted(n for n, c in counts.items() if c > 1),
        "missing": missing,
    }
