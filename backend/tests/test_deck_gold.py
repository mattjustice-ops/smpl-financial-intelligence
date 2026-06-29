"""Tests for gold deck reference and timestamped archiving."""

from pathlib import Path

from app.services.reporting.export.deck_gold import (
    archive_timestamp,
    extract_layout_fingerprint,
    gold_period_dir,
    write_timestamped_archive,
)


def test_archive_timestamp_format():
    ts = archive_timestamp()
    assert "T" in ts and ts.endswith("Z")


def test_write_timestamped_archive_creates_immutable_copy(tmp_path, monkeypatch):
    import app.services.reporting.export.deck_gold as mod

    monkeypatch.setattr(mod, "ARCHIVE_DIR", tmp_path)
    js_path = write_timestamped_archive("2026-06", "const x=1;", b"pptx")
    assert js_path.name.startswith("generate_deck_2026-06_")
    assert (tmp_path / "2026-06" / "generate_deck_2026-06.js").read_text() == "const x=1;"
    assert len(list((tmp_path / "2026-06").glob("generate_deck_2026-06_*.js"))) == 1


def test_resolve_reference_script_prefers_gold(tmp_path, monkeypatch):
    import app.services.reporting.export.deck_gold as mod

    period = "2026-06"
    gold_dir = tmp_path / "gold" / period
    arch_dir = tmp_path / period
    gold_dir.mkdir(parents=True)
    arch_dir.mkdir(parents=True)
    (gold_dir / "generate_deck_reference.js").write_text("x" * 2000, encoding="utf-8")
    (arch_dir / "generate_deck_2026-06.js").write_text("y" * 2000, encoding="utf-8")
    monkeypatch.setattr(mod, "GOLD_DIR", tmp_path / "gold")
    monkeypatch.setattr(mod, "ARCHIVE_DIR", tmp_path)
    path, kind = mod.resolve_reference_script(period)
    assert kind == "gold"
    assert path.name == "generate_deck_reference.js"


def test_resolve_reference_script_falls_back_to_archive(tmp_path, monkeypatch):
    import app.services.reporting.export.deck_gold as mod

    period = "2026-06"
    arch_dir = tmp_path / period
    arch_dir.mkdir(parents=True)
    (arch_dir / "generate_deck_2026-06.js").write_text("z" * 2000, encoding="utf-8")
    monkeypatch.setattr(mod, "GOLD_DIR", tmp_path / "gold")
    monkeypatch.setattr(mod, "ARCHIVE_DIR", tmp_path)
    path, kind = mod.resolve_reference_script(period)
    assert kind == "archive"
    assert path.name == "generate_deck_2026-06.js"


def test_extract_layout_fingerprint_from_v3_reference():
    v3 = Path(__file__).resolve().parents[1] / "tmp" / "mda_deck_2026-06 v3.pptx"
    if not v3.is_file():
        return
    fp = extract_layout_fingerprint(v3)
    assert fp["slide_count"] == 11
    slide3 = fp["slides"][2]
    assert slide3["charts"]
    assert slide3["charts"][0]["series"] == ["Actual ($M)", "Budget ($M)"]
