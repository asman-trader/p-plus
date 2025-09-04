# routes/prefs_routes.py
from flask import Blueprint, jsonify, request
from pathlib import Path
from ._utils import read_json, write_json, BASE_DIR

prefs_bp = Blueprint("prefs", __name__)

PREFS_PATH = BASE_DIR / "prefs.json"
DEFAULTS = {
    "selected_coins": ["BTC", "ETH", "BNB"],
    "notif_sound": True
}

@prefs_bp.get("/prefs")
def get_prefs():
    data = read_json(PREFS_PATH, DEFAULTS.copy())
    # تضمین کلیدها
    data = {**DEFAULTS, **data}
    # پاکسازی ورودی‌های نامعتبر
    data["selected_coins"] = [c.upper() for c in data.get("selected_coins", []) if isinstance(c, str)]
    data["notif_sound"] = bool(data.get("notif_sound", True))
    return jsonify(data)

@prefs_bp.post("/prefs")
def save_prefs():
    payload = request.get_json(silent=True) or {}
    coins = payload.get("selected_coins")
    sound = payload.get("notif_sound")

    data = read_json(PREFS_PATH, DEFAULTS.copy())

    if isinstance(coins, list):
        data["selected_coins"] = [str(c).upper() for c in coins if isinstance(c, str)]
    if isinstance(sound, (bool, int)):
        data["notif_sound"] = bool(sound)

    write_json(PREFS_PATH, data)
    return jsonify({"ok": True, **data})
