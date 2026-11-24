"""Close flux-event grain: OpEx compile, upload guard, account-line placement."""

from __future__ import annotations

import uuid
from decimal import Decimal

from app.services.commentary.revenue_rollup import (
    RevenueSectionIn,
    _finalize_paragraph,
    attach_stored_events,
    build_revenue_evidence,
)
from app.services.warehouse.compile_flux_events import (
    BS_SECTION_LINES,
    MATERIALITY,
    _apply_materiality,
    _event_kind,
    _gl_bs_activity,
    brief_flux_for_rollup,
    compile_bs_flux_events,
    compile_close_flux_events,
    compile_cogs_flux_events,
    compile_opex_flux_events,
    money,
)


ORG = "8571e520-0687-4516-bdee-379f37c58c1f"


def test_event_kind_payroll_credit_and_vendor():
    assert _event_kind("6100 Salaries & Wages", Decimal("50000")) == "payroll_batch"
    assert _event_kind("6200 Software", Decimal("-12000")) == "credit_reversal"
    assert _event_kind("6200 Software", Decimal("12000")) == "vendor_spend"


def test_opex_brief_includes_prior_amounts_and_tx_counts():
    events = brief_flux_for_rollup(
        [
            {
                "account_number": "6200",
                "account_name": "Software",
                "event_kind": "vendor_spend",
                "counterparty": "AWS",
                "department": "Engineering",
                "amount": "45000",
                "prior_amount": "30000",
                "tx_count": "12",
                "prior_tx_count": "8",
            },
            {
                "account_number": "6200",
                "account_name": "Software",
                "event_kind": "vendor_spend",
                "counterparty": "Datadog",
                "department": "Engineering",
                "amount": "15000",
                "prior_amount": "14000",
                "tx_count": "2",
                "prior_tx_count": "2",
            },
        ]
    )
    assert len(events) == 1
    assert events[0]["customer"] == "AWS"
    assert events[0]["bucket"] == "Vendor"
    assert events[0]["amount"] == 45000.0
    assert events[0]["prior_amount"] == 30000.0
    assert events[0]["tx_count"] == 12
    assert events[0]["prior_tx_count"] == 8
    assert events[0]["others"] == 1
    assert events[0]["account_number"] == "6200"
    assert "6200" in events[0]["account_label"]


def test_materiality_keeps_sole_under_threshold_driver():
    key = ("6400", "Travel", "United", "Sales", "")
    row = {
        "section": "opex",
        "account_number": "6400",
        "account_name": "Travel",
        "event_kind": "vendor_spend",
        "counterparty": "United",
        "counterparty_id": "",
        "department": "Sales",
        "tag": "",
        "amount": money(Decimal("2500")),
        "prior_amount": money(Decimal("0")),
        "tx_count": "1",
        "prior_tx_count": "0",
        "is_credit": "false",
        "_amount": Decimal("2500"),
        "_prior_amount": Decimal("0"),
    }
    kept = _apply_materiality([(key, row)])
    assert len(kept) == 1
    assert kept[0]["counterparty"] == "United"
    assert Decimal(kept[0]["amount"]) < MATERIALITY


def test_customer_upload_blocks_compiled_rewrite(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events.table_exists",
        lambda db, name: True,
    )
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events._customer_loaded",
        lambda db, org, period, section: True,
    )
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events._gl_activity",
        lambda *args, **kwargs: calls.append("gl") or [],
    )
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events._replace_compiled",
        lambda *args, **kwargs: calls.append("write") or True,
    )

    wrote = compile_opex_flux_events(object(), uuid.UUID(ORG), "2026-07")
    assert wrote is False
    assert calls == []


def test_opex_compile_writes_vendor_rows_with_priors(monkeypatch):
    written: list[dict] = []

    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events.table_exists",
        lambda db, name: True,
    )
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events._customer_loaded",
        lambda *args, **kwargs: False,
    )

    def fake_gl(db, org, period, *, lines):
        if period == "2026-07":
            return [
                {
                    "account_number": "6200",
                    "account_name": "Software",
                    "vendor_name": "AWS",
                    "vendor_id": "v1",
                    "department": "Engineering",
                    "amount": Decimal("45000"),
                    "tx_count": 10,
                }
            ]
        return [
            {
                "account_number": "6200",
                "account_name": "Software",
                "vendor_name": "AWS",
                "vendor_id": "v1",
                "department": "Engineering",
                "amount": Decimal("30000"),
                "tx_count": 7,
            }
        ]

    monkeypatch.setattr("app.services.warehouse.compile_flux_events._gl_activity", fake_gl)

    def capture_replace(db, org, period, section, rows, filename):
        written.extend(rows)
        assert section == "opex"
        assert filename == "compiled:flux:2026-07:opex"
        return True

    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events._replace_compiled",
        capture_replace,
    )

    assert compile_opex_flux_events(object(), uuid.UUID(ORG), "2026-07") is True
    assert len(written) == 1
    assert written[0]["counterparty"] == "AWS"
    assert written[0]["amount"] == "45000.00"
    assert written[0]["prior_amount"] == "30000.00"
    assert written[0]["tx_count"] == "10"
    assert written[0]["prior_tx_count"] == "7"
    assert written[0]["event_kind"] == "vendor_spend"


def test_cogs_compile_writes_vendor_rows_with_usage_tag(monkeypatch):
    written: list[dict] = []

    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events.table_exists",
        lambda db, name: True,
    )
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events._customer_loaded",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events._usage_tags_by_account_vendor",
        lambda db, org, period: {("5000", "aws"): "Hosting — compute units; commit 100000"},
    )

    def fake_gl(db, org, period, *, lines):
        assert lines == frozenset({"cogs"})
        if period == "2026-07":
            return [
                {
                    "account_number": "5000",
                    "account_name": "Hosting",
                    "vendor_name": "AWS",
                    "vendor_id": "v-aws",
                    "department": "Infrastructure",
                    "amount": Decimal("120000"),
                    "tx_count": 6,
                }
            ]
        return [
            {
                "account_number": "5000",
                "account_name": "Hosting",
                "vendor_name": "AWS",
                "vendor_id": "v-aws",
                "department": "Infrastructure",
                "amount": Decimal("90000"),
                "tx_count": 5,
            }
        ]

    monkeypatch.setattr("app.services.warehouse.compile_flux_events._gl_activity", fake_gl)

    def capture_replace(db, org, period, section, rows, filename):
        written.extend(rows)
        assert section == "cogs"
        assert filename == "compiled:flux:2026-07:cogs"
        return True

    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events._replace_compiled",
        capture_replace,
    )

    assert compile_cogs_flux_events(object(), uuid.UUID(ORG), "2026-07") is True
    assert len(written) == 1
    assert written[0]["section"] == "cogs"
    assert written[0]["counterparty"] == "AWS"
    assert written[0]["amount"] == "120000.00"
    assert written[0]["prior_amount"] == "90000.00"
    assert written[0]["tag"] == "Hosting — compute units; commit 100000"


def test_cogs_customer_upload_blocks_compiled_rewrite(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events.table_exists",
        lambda db, name: True,
    )
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events._customer_loaded",
        lambda db, org, period, section: section == "cogs",
    )
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events._gl_activity",
        lambda *args, **kwargs: calls.append("gl") or [],
    )
    assert compile_cogs_flux_events(object(), uuid.UUID(ORG), "2026-07") is False
    assert calls == []


def test_bs_customer_upload_blocks_compiled_rewrite(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events.table_exists",
        lambda db, name: True,
    )
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events._customer_loaded",
        lambda db, org, period, section: section in BS_SECTION_LINES,
    )
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events._gl_bs_activity",
        lambda *args, **kwargs: calls.append("gl") or [],
    )
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events._replace_compiled",
        lambda *args, **kwargs: calls.append("write") or True,
    )
    assert compile_bs_flux_events(object(), uuid.UUID(ORG), "2026-07") is False
    assert calls == []


def test_bs_opening_balance_rows_skipped(monkeypatch):
    class _Mappings:
        def __init__(self, rows):
            self._rows = rows

        def mappings(self):
            return self._rows

    class _Db:
        def execute(self, *args, **kwargs):
            return _Mappings(
                [
                    {
                        "period": "2026-07",
                        "statement": "Balance Sheet",
                        "statement_category": "",
                        "category": "",
                        "account_group": "Cash",
                        "expense_type": "Cash",
                        "account_number": "1000",
                        "account_name": "Operating Cash",
                        "department": "",
                        "vendor_name": "",
                        "vendor_id": "",
                        "notes": "",
                        "source_system": "Opening Balance",
                        "amount": Decimal("500000"),
                        "tx_count": 1,
                    },
                    {
                        "period": "2026-07",
                        "statement": "Balance Sheet",
                        "statement_category": "",
                        "category": "",
                        "account_group": "Cash",
                        "expense_type": "Cash",
                        "account_number": "1000",
                        "account_name": "Operating Cash",
                        "department": "",
                        "vendor_name": "Bank",
                        "vendor_id": "b1",
                        "notes": "",
                        "source_system": "Campfire",
                        "amount": Decimal("25000"),
                        "tx_count": 3,
                    },
                ]
            )

    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events._table_columns",
        lambda db, table: {
            "period",
            "amount",
            "vendor_name",
            "vendor_id",
            "notes",
            "source_system",
            "account_number",
            "account_name",
            "department",
            "statement",
            "statement_category",
            "category",
            "account_group",
            "expense_type",
            "version",
            "organization_id",
        },
    )
    monkeypatch.setattr(
        "app.services.reporting.account_maps.load_account_maps",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(
        "app.services.reporting.account_maps.stamp_account_maps",
        lambda rows, maps: None,
    )

    out = _gl_bs_activity(_Db(), ORG, "2026-07", lines=frozenset({"cash"}))
    assert len(out) == 1
    assert out[0]["amount"] == Decimal("25000")
    assert out[0]["source_system"] == "Campfire"


def test_compile_close_includes_bs_writer(monkeypatch):
    called: list[str] = []
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events.compile_opex_flux_events",
        lambda *args, **kwargs: called.append("opex") or False,
    )
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events.compile_cogs_flux_events",
        lambda *args, **kwargs: called.append("cogs") or False,
    )
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events.compile_bs_flux_events",
        lambda *args, **kwargs: called.append("bs") or True,
    )
    assert compile_close_flux_events(object(), uuid.UUID(ORG), "2026-07") is True
    assert called == ["opex", "cogs", "bs"]


def test_attach_flux_events_for_cogs(monkeypatch):
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events.load_flux_events",
        lambda *args, **kwargs: [
            {
                "account_number": "5000",
                "account_name": "Hosting",
                "event_kind": "vendor_spend",
                "counterparty": "AWS",
                "department": "Infrastructure",
                "tag": "Hosting — compute units",
                "amount": "120000",
                "prior_amount": "90000",
                "tx_count": "6",
                "prior_tx_count": "5",
            }
        ],
    )
    section = RevenueSectionIn.model_validate(
        {
            "comparison": "Jul 2026 vs Jun 2026",
            "comparison_kind": "mom",
            "section_id": "cogs",
            "period": "2026-07",
            "organization_id": ORG,
            "materiality": 10000,
            "parent": {"label": "Cost of Revenue", "current": 200000, "comparison_amount": 150000, "variance": 50000},
            "lines": [
                {
                    "label": "5000 Hosting",
                    "current": 120000,
                    "comparison_amount": 90000,
                    "variance": 30000,
                }
            ],
        }
    )
    attached = attach_stored_events(section, object())
    assert [event.customer for event in attached.events] == ["AWS"]
    assert attached.events[0].account_number == "5000"
    assert attached.events[0].tag == "Hosting — compute units"


def test_attach_flux_events_for_sm(monkeypatch):
    monkeypatch.setattr(
        "app.services.warehouse.compile_flux_events.load_flux_events",
        lambda *args, **kwargs: [
            {
                "account_number": "6100",
                "account_name": "Marketing Programs",
                "event_kind": "vendor_spend",
                "counterparty": "Google Ads",
                "department": "Demand Gen",
                "amount": "80000",
                "prior_amount": "50000",
                "tx_count": "4",
                "prior_tx_count": "3",
            }
        ],
    )
    section = RevenueSectionIn.model_validate(
        {
            "comparison": "Jul 2026 vs Jun 2026",
            "comparison_kind": "mom",
            "section_id": "sm",
            "period": "2026-07",
            "organization_id": ORG,
            "materiality": 10000,
            "parent": {"label": "Sales & Marketing", "current": 200000, "comparison_amount": 150000, "variance": 50000},
            "lines": [
                {
                    "label": "6100 Marketing Programs",
                    "current": 200000,
                    "comparison_amount": 150000,
                    "variance": 50000,
                }
            ],
        }
    )
    attached = attach_stored_events(section, object())
    assert [event.customer for event in attached.events] == ["Google Ads"]
    assert attached.events[0].bucket == "Vendor"
    assert attached.events[0].account_number == "6100"


def test_orphan_flux_event_lands_on_matching_account_line():
    section = RevenueSectionIn.model_validate(
        {
            "comparison": "Jul 2026 vs Jun 2026",
            "comparison_kind": "mom",
            "section_id": "sm",
            "period": "2026-07",
            "organization_id": ORG,
            "parent": {"label": "Sales & Marketing", "current": 300000, "comparison_amount": 200000, "variance": 100000},
            "lines": [
                {
                    "label": "6100 Marketing Programs",
                    "current": 200000,
                    "comparison_amount": 120000,
                    "variance": 80000,
                },
                {
                    "label": "6200 Software",
                    "current": 100000,
                    "comparison_amount": 80000,
                    "variance": 20000,
                },
            ],
            "events": [
                {
                    "bucket": "Vendor",
                    "customer": "Google Ads",
                    "amount": 80000,
                    "outcome": "occurred",
                    "account_number": "6100",
                    "account_label": "6100 Marketing Programs",
                }
            ],
        }
    )
    evidence = build_revenue_evidence(section)
    text = (
        "6100 Marketing Programs increased $80.00k to $200.00k.\n"
        "6200 Software increased $20.00k to $100.00k.\n"
        "Vendor included Google Ads at $80.00k."
    )
    fixed = _finalize_paragraph(text, evidence)
    programs = next(block for block in fixed.split("\n") if block.startswith("6100"))
    software = next(block for block in fixed.split("\n") if block.startswith("6200"))
    assert "Google Ads" in programs
    assert "Google Ads" not in software
    assert "Vendor included" not in software
