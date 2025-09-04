from pathlib import Path
import json, time

BASE_DIR = Path(__file__).resolve().parents[1]  # پوشه ریشه پروژه
DATA_SETTINGS = BASE_DIR / "settings.json"
DATA_SIGNALS  = BASE_DIR / "signals.json"

def _atomic_write(path: Path, data: dict):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)

def read_json(path: Path, default: dict):
    if not path.exists():
        _atomic_write(path, default)
        return default
    # retry ساده در صورت رقابت نوشتن
    for _ in range(3):
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            time.sleep(0.05)
    return default

def write_json(path: Path, data: dict):
    _atomic_write(path, data)
