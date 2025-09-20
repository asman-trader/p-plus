from pathlib import Path
import json, time

BASE_DIR = Path(__file__).resolve().parents[1]  # پوشه ریشه پروژه
DATA_SETTINGS = BASE_DIR / "settings.json"
DATA_SIGNALS  = BASE_DIR / "signals.json"
DATA_TRADES   = BASE_DIR / "trades.json"

def _atomic_write(path: Path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)

def read_json(path: Path, default):
    if not path.exists():
        _atomic_write(path, default)
        return default
    # retry ساده در صورت رقابت نوشتن
    for _ in range(3):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                # بررسی نوع داده بر اساس نوع default (dict یا list)
                expected_type = type(default)
                if expected_type in (dict, list) and not isinstance(data, expected_type):
                    print(f"Warning: {path} contains invalid data type, resetting to default")
                    _atomic_write(path, default)
                    return default
                return data
        except json.JSONDecodeError as e:
            print(f"Warning: {path} contains invalid JSON, resetting to default: {e}")
            _atomic_write(path, default)
            return default
        except Exception as e:
            print(f"Warning: Error reading {path}, resetting to default: {e}")
            _atomic_write(path, default)
            return default
    return default

def write_json(path: Path, data):
    _atomic_write(path, data)
