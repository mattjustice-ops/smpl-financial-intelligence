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
