import uuid
from app.db.session import SessionLocal
from app.services.reporting.three_statement_payload import (
    BS_FIELD_SPECS,
    IS_FIELD_SPECS,
    _enrich_is,
    _normalize_bs_display,
    _period_dict_from_field_specs,
    _read_statement_table,
    build_cfs_from_statements,
)

ORG = uuid.UUID("8571e520-0687-4516-bdee-379f37c58c1f")
db = SessionLocal()
actual_bs = _period_dict_from_field_specs(
    _read_statement_table(db, ORG, "actual_balance_sheet"), BS_FIELD_SPECS
)
for r in actual_bs.values():
    _normalize_bs_display(r)

for prefix, periods in [
    ("budget", [f"2026-{m:02d}" for m in range(1, 13)]),
    ("forecast", [f"2026-{m:02d}" for m in range(7, 13)]),
    ("actual", [f"2026-{m:02d}" for m in range(1, 7)]),
]:
    is_data = _period_dict_from_field_specs(
        _read_statement_table(db, ORG, f"{prefix}_income_statement"), IS_FIELD_SPECS
    )
    bs_data = _period_dict_from_field_specs(
        _read_statement_table(db, ORG, f"{prefix}_balance_sheet"), BS_FIELD_SPECS
    )
    for r in is_data.values():
        _enrich_is(r)
    for r in bs_data.values():
        _normalize_bs_display(r)
    cross = actual_bs if prefix in ("budget", "forecast") else None
    cfs = build_cfs_from_statements(periods, is_data, bs_data, cross_scenario_bs=cross)
    print(f"=== {prefix} platform-computed CFS ===")
    bad = 0
    for p in periods:
        r = cfs.get(p, {})
        v = r.get("cash_tie_variance")
        if v is not None and abs(v) > 1:
            bad += 1
            print(
                f"  {p}: variance={v:,.0f} "
                f"net_change={r.get('net_change'):,.0f} "
                f"computed={r.get('net_change_computed'):,.0f}"
            )
    if bad == 0:
        print("  all periods tie within $1")
    dec = periods[-1]
    r = cfs[dec]
    print(f"  {dec} ending_cash={r.get('ending_cash'):,.0f}")
db.close()
