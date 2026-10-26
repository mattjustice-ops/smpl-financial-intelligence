"""The Board usage meter is the warehouse rows, totaled onto a month."""

from app.services.reporting.vendor_usage import vendor_usage_from_rows


def test_meter_groups_the_loaded_rows_by_month():
    payload = vendor_usage_from_rows({
        "Actual": [
            {
                "period": "2026-06-01", "vendor_name": "Twilio", "account_number": "5030",
                "service": "Notification messaging", "driver": "active customers",
                "units": "499", "unit_cost": "24.85", "amount": "12398.59", "billing": "monthly usage",
            },
            {
                "period": "2026-06-01", "vendor_name": "Amazon Web Services", "account_number": "5000",
                "service": "Production compute and storage", "driver": "ending ARR ($K)",
                "units": "75000", "unit_cost": "3.05", "amount": "228750.00", "billing": "monthly usage",
            },
        ],
        "Budget": [],
        "Forecast": [],
    })
    june = payload["scenarios"]["Actual"]["2026-06"]
    assert [row["vendor"] for row in june] == ["Amazon Web Services", "Twilio"]
    assert june[0]["account"] == "5000"
    assert june[0]["amount"] == 228750.0
    assert payload["accounts"]["5000"] == "Hosting"
    assert "fitted" in payload["note"]


def test_a_meter_fitted_to_the_ledger_is_not_commentary():
    from app.services.reporting.vendor_usage import attach_usage_measures

    tree = {"lines": [{"account_number": "5000", "label": "Hosting", "children": []}]}
    attach_usage_measures(tree, [{
        "account": "5000",
        "service": "Production compute and storage",
        "driver": "ending ARR ($K)",
        "units": 75000,
        "unit_cost": 3.05,
        "unit_cost_basis": "Actual source GL 2026-01 to 2026-06: 1.00 x 100% = 1.00 over 1 units",
    }])
    assert "measures" not in tree["lines"][0]


def test_usage_the_customer_entered_is_a_measure():
    from app.services.reporting.vendor_usage import attach_usage_measures

    tree = {"lines": [{"account_number": "6410", "label": "Development cloud", "children": []}]}
    attach_usage_measures(tree, [{
        "account": "6410",
        "service": "Build compute",
        "driver": "compute hours",
        "units": 1200,
        "unit_cost": 0.12,
        "unit_cost_basis": "customer usage export",
    }])
    labels = {measure["label"] for measure in tree["lines"][0]["measures"]}
    assert labels == {"Build compute — compute hours", "Build compute — compute hours unit cost"}
