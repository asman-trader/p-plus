# -*- coding: utf-8 -*-
from flask import Blueprint, jsonify, request
from ._utils import read_json, write_json, DATA_SETTINGS

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")

# مقادیر پیش‌فرض
DEFAULTS = {
    "first_buy_threshold": 1.0,  # درصد کاهش برای خرید اول
    "next_buy_threshold": 1.0,   # درصد کاهش خریدهای بعدی از آخرین خرید
    "sell_threshold": 1.5        # درصد سود برای فروش
}

@settings_bp.get("/")
def get_settings():
    """
    دریافت تنظیمات فعلی.
    اگر فایل وجود نداشته باشد یا ناقص باشد، مقادیر پیش‌فرض اعمال می‌شود.
    """
    data = read_json(DATA_SETTINGS, DEFAULTS.copy())
    # ادغام با مقادیر پیش‌فرض
    data = {**DEFAULTS, **data}
    return jsonify(data)


@settings_bp.post("/")
def save_settings():
    """
    ذخیره‌سازی تنظیمات جدید.
    ورودی JSON شامل:
      - first_buy_threshold
      - next_buy_threshold
      - sell_threshold
    """
    payload = request.get_json(silent=True) or {}
    try:
        first_buy = float(payload.get("first_buy_threshold", DEFAULTS["first_buy_threshold"]))
        next_buy = float(payload.get("next_buy_threshold", DEFAULTS["next_buy_threshold"]))
        sell = float(payload.get("sell_threshold", DEFAULTS["sell_threshold"]))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "bad input"}), 400

    data = {
        "first_buy_threshold": first_buy,
        "next_buy_threshold": next_buy,
        "sell_threshold": sell
    }
    write_json(DATA_SETTINGS, data)
    return jsonify({"ok": True, **data})
