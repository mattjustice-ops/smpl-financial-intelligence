import traceback
import uuid
from pathlib import Path

from app.db.session import SessionLocal
from app.services.demo_csv.loader import load_demo_csv

org = uuid.UUID("8571e520-0687-4516-bdee-379f37c58c1f")
content = Path(r"C:\Users\mattj\OneDrive\Documents\simple CSVS\invoices.csv").read_bytes()
db = SessionLocal()
try:
    res = load_demo_csv(db, org, content)
    print("kind", res.csv_kind)
    print("rows", res.rows_upserted)
    print("dup", res.duplicate_key_error)
    print("integrity", res.integrity_error)
    print("header", res.header_error)
    print("val errs", len(res.validation_errors))
except Exception:
    traceback.print_exc()
finally:
    db.close()
