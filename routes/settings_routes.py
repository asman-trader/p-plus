from flask import Blueprint, jsonify, request
from ._utils import read_json, write_json, DATA_SETTINGS

settings_bp = Blueprint("settings", __name__)

DEFAULTS = {"buy_threshold": 1.0, "sell_threshold": 1.5}

@settings_bp.get("")
def get_settings():
    data = read_json(DATA_SETTINGS, DEFAULTS.copy())
    # تضمین وجود کلیدها
    data = {**DEFAULTS, **data}
    return jsonify(data)

@settings_bp.post("")
def save_settings():
    payload = request.get_json(silent=True) or {}
    try:
        buy  = float(payload.get("buy_threshold", DEFAULTS["buy_threshold"]))
        sell = float(payload.get("sell_threshold", DEFAULTS["sell_threshold"]))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "bad input"}), 400

    data = {"buy_threshold": buy, "sell_threshold": sell}
    write_json(DATA_SETTINGS, data)
    return jsonify({"ok": True, **data})
