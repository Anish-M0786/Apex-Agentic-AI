from pathlib import Path
import re
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "outputs"
def output_path(filename: str, suffix: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._ -]", "_", Path(filename).name).strip(" .") or "output"
    if not safe.lower().endswith(suffix): safe += suffix
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = (OUTPUT_DIR / safe).resolve()
    if path.parent != OUTPUT_DIR.resolve(): raise ValueError("Invalid output filename")
    return path
