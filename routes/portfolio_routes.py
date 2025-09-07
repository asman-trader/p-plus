# -*- coding: utf-8 -*-
from flask import Blueprint, jsonify, request, render_template
from datetime import datetime
from ._utils import read_json, write_json
import uuid
import math

"""
فرض: فایل ._utils تو داری و مشابه settings ازش استفاده کرده‌ای.
اگر DATA_TRADES در _utils نیست، یا اضافه‌اش کن یا اینجا یک ثابت محلی بگذار.
"""

try:
    # اگر قبلاً در _utils تعریف کرده‌ای از همون استفاده کن
    from ._utils import DATA_TRADES
except Exception:
    # مسیر پیش‌فرض JSON ذخیره معاملات
    DATA_TRADES = "app/data/trades.json"

portfolio_bp = Blueprint("portfolio", __name__, url_prefix="/portfolio")

# اسکیمای ذخیره: لیستی از معاملات
# item = {
#   "id": str,                uuid
#   "symbol": str,            مثل BTCUSDT
#   "side": "BUY"|"SELL",
#   "qty": float,             مقدار
#   "price": float,           قیمت واحد
#   "fee": float,             کارمزد (اختیاری)
#   "ts": "YYYY-MM-DD HH:MM", زمان معامله
#   "note": str               توضیح (اختیاری)
# }

def _load_trades():
    data = read_json(DATA_TRADES, default=[])
    # تضمین لیست
    if not isinstance(data, list):
        data = []
    return data

def _save_trades(items):
    write_json(DATA_TRADES, items)

def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def _to_float(v, default=0.0):
    try:
        # اجازه ورودی رشته با ویرگول
        return float(str(v).replace(",", "").strip())
    except Exception:
        return float(default)

def _calc_positions(trades):
    """
    خروجی خلاصه پوزیشن برای هر نماد بر اساس معاملات ثبت‌شده.
    قیمت لحظه‌ای نداریم، پس PnL لحظه‌ای محاسبه نمی‌شود (بعداً می‌توانی وصل کنی).
    """
    by_symbol = {}
    for t in trades:
        sym = t.get("symbol", "").upper().strip()
        side = (t.get("side") or "").upper()
        qty  = _to_float(t.get("qty"))
        prc  = _to_float(t.get("price"))
        fee  = _to_float(t.get("fee"))

        if sym == "" or qty <= 0 or prc <= 0:
            continue

        if sym not in by_symbol:
            by_symbol[sym] = {
                "symbol": sym,
                "total_buy_qty": 0.0,
                "total_sell_qty": 0.0,
                "gross_buy_value": 0.0,  # جمع مبلغ خریدها (qty*price)
                "gross_sell_value": 0.0, # جمع مبلغ فروش‌ها
                "fees": 0.0
            }

        if side == "BUY":
            by_symbol[sym]["total_buy_qty"] += qty
            by_symbol[sym]["gross_buy_value"] += qty * prc
        elif side == "SELL":
            by_symbol[sym]["total_sell_qty"] += qty
            by_symbol[sym]["gross_sell_value"] += qty * prc

        by_symbol[sym]["fees"] += fee

    # محاسبات نهایی
    positions = []
    for sym, row in by_symbol.items():
        net_qty = row["total_buy_qty"] - row["total_sell_qty"]
        avg_buy = (row["gross_buy_value"] / row["total_buy_qty"]) if row["total_buy_qty"] > 0 else 0.0
        realized_cashflow = row["gross_sell_value"] - row["gross_buy_value"] - row["fees"]
        positions.append({
            "symbol": sym,
            "net_qty": round(net_qty, 8),
            "avg_buy_price": round(avg_buy, 8),
            "invested": round(row["gross_buy_value"], 2),
            "realized_cashflow": round(realized_cashflow, 2),
            "fees": round(row["fees"], 2)
        })
    # می‌توانی مرتب‌سازی کنی: بیشترین سرمایه‌گذاری در بالا
    positions.sort(key=lambda x: x["invested"], reverse=True)
    return positions

@portfolio_bp.get("/")
def page():
    """
    صفحه وب لیست معاملات و خلاصه پوزیشن‌ها
    """
    return render_template("portfolio.html")

# --------- API ---------

@portfolio_bp.get("/api/trades")
def api_list_trades():
    trades = _load_trades()
    # مرتب‌سازی نزولی بر اساس زمان ثبت (ts) اگر وجود دارد
    def _key(t):
        try:
            return datetime.strptime(t.get("ts", ""), "%Y-%m-%d %H:%M")
        except Exception:
            return datetime.min
    trades.sort(key=_key, reverse=True)
    return jsonify({
        "ok": True,
        "items": trades,
        "positions": _calc_positions(trades)
    })

@portfolio_bp.post("/api/trades")
def api_add_trade():
    """
    ورودی JSON:
      symbol (str, required)
      side   ("BUY"|"SELL", required)
      qty    (float, required)
      price  (float, required)
      fee    (float, optional)
      ts     (str, optional "YYYY-MM-DD HH:MM")
      note   (str, optional)
    """
    payload = request.get_json(silent=True) or {}
    symbol = (payload.get("symbol") or "").upper().strip()
    side   = (payload.get("side") or "").upper().strip()
    qty    = _to_float(payload.get("qty"))
    price  = _to_float(payload.get("price"))
    fee    = _to_float(payload.get("fee"))
    ts     = payload.get("ts") or _now_str()
    note   = (payload.get("note") or "").strip()

    if symbol == "" or side not in ("BUY", "SELL") or qty <= 0 or price <= 0:
        return jsonify({"ok": False, "error": "bad input"}), 400

    items = _load_trades()
    new_item = {
        "id": str(uuid.uuid4()),
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": price,
        "fee": fee,
        "ts": ts,
        "note": note
    }
    items.append(new_item)
    _save_trades(items)
    return jsonify({"ok": True, "item": new_item, "positions": _calc_positions(items)})

@portfolio_bp.delete("/api/trades/<trade_id>")
def api_delete_trade(trade_id):
    items = _load_trades()
    before = len(items)
    items = [t for t in items if str(t.get("id")) != str(trade_id)]
    if len(items) == before:
        return jsonify({"ok": False, "error": "not found"}), 404
    _save_trades(items)
    return jsonify({"ok": True, "positions": _calc_positions(items)})
