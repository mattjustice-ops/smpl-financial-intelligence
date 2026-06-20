import shutil
from pathlib import Path

src = Path(r"C:\Users\mattj\Downloads\us_emea_basemap.svg")
dst = Path(__file__).resolve().parents[1] / "frontend" / "public" / "board" / "us_emea_basemap.svg"
dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(src, dst)
print(f"copied {src.stat().st_size} bytes -> {dst}")
