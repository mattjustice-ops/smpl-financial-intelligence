"""One general ledger per month.

A close file stamped for a later month can also carry earlier months. Those
earlier months are already on the book. Summing both copies doubles the
statements and the cash flow. Keep the earlier book. Keep a stamped file's
own month. Keep an earlier month from a later file only when nothing older
has that month.
"""

from __future__ import annotations

# True for a row the statement should keep. A null load_name stays: `NOT` of a
# null comparison would drop the original book.
ONE_BOOK_SQL = """
(
  load_name is null
  or load_name !~ ' · [0-9]{4}-[0-9]{2}$'
  or to_char(period, 'YYYY-MM') = right(load_name, 7)
  or not exists (
    select 1
    from gl_actuals kept
    where kept.organization_id = gl_actuals.organization_id
      and lower(kept.version) = lower(gl_actuals.version)
      and kept.period = gl_actuals.period
      and (
        kept.load_name is null
        or (
          kept.load_name ~ ' · [0-9]{4}-[0-9]{2}$'
          and right(kept.load_name, 7) < right(gl_actuals.load_name, 7)
        )
      )
  )
)
""".strip()
