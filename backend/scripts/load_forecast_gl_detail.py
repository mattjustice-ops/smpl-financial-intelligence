"""Load all Forecast_*.csv files (including Forecast_gl_detail.csv).

Legacy name kept for existing scripts. Prefer:
  python scripts/load_forecast_csvs.py <org_id> [csv_folder]
  python scripts/load_versioned_csvs.py <org_id> [csv_folder] Forecast
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPTS_DIR.parent
sys.path.insert(0, str(_BACKEND_DIR))
sys.path.insert(0, str(_SCRIPTS_DIR))

from load_forecast_csvs import main

if __name__ == "__main__":
    main()
