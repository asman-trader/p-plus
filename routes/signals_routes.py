# routes/signals_routes.py
from flask import Blueprint, jsonify, request, Response
from datetime import datetime
from ._utils import read_json, write_json, DATA_SIGNALS

signals_bp = Blueprint("signals", __name__)

# ساختار فایل signals.json:
# {
#   "open_trades": {"BTC": 50000.0, ...},   # آخرین خرید باز هر نماد
#   "history": {"BTC": [{"type":"buy","price":50000,"time":"...","profit":0}, ...]},
#   "total_profit": {"BTC": 12.34, ...}
# }

DEFAULT = {"open_trades": {}, "history": {}, "total_profit": {}}


# ---------- کمکـی ----------
def _ensure_symbol(data: dict, sym: str) -> None:
    """وجود کلیدهای لازم برای نماد را تضمین می‌کند."""
    data["history"].setdefault(sym, [])
    data["total_profit"].setdefault(sym, 0.0)


def _to_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return float(default)


# ---------- خواندن سیگنال‌های یک نماد ----------
@signals_bp.get("/<symbol>")
def get_symbol_signals(symbol):
    """
    پاسخ:
      {
        "symbol": "BTC",
        "signals": [ ... آخرین n رکورد ... ],
        "total_profit": 0.0,
        "last_open_buy": 50000.0 | null
      }

    پارامترها:
      limit (اختیاری، پیش‌فرض 200) - تعداد رکوردهای بازگشتی
      order (اختیاری: 'desc' | 'asc'، پیش‌فرض 'desc')
    """
    symbol = symbol.upper()
    limit = request.args.get("limit", default=200, type=int)
    order = (request.args.get("order") or "desc").lower()
    if limit is None or limit <= 0:
        limit = 200
    if order not in ("asc", "desc"):
        order = "desc"

    data = read_json(DATA_SIGNALS, DEFAULT.copy())
    _ensure_symbol(data, symbol)

    rows = data["history"][symbol]
    # ترتیب
    rows_iter = rows if order == "asc" else list(reversed(rows))
    # محدودیت
    rows_out = list(rows_iter)[:limit]

    return jsonify({
        "symbol": symbol,
        "signals": rows_out,
        "total_profit": float(data["total_profit"].get(symbol, 0.0)),
        "last_open_buy": float(data["open_trades"][symbol]) if symbol in data["open_trades"] else None
    })


# ---------- افزودن سیگنال (خرید/فروش) ----------
@signals_bp.post("/<symbol>")
def add_signal(symbol):
    """
    بدنه:
      { "type": "buy" | "sell", "price": number, "time": "YYYY-MM-DD HH:MM:SS"(اختیاری) }

    منطق:
      - buy: مقدار خریدِ باز برای نماد ثبت می‌شود.
      - sell: اگر خریدِ باز موجود باشد، profit = sell - buy محاسبه و به total_profit اضافه می‌شود،
              سپس وضعیت خریدِ باز پاک می‌شود.
    """
    symbol = symbol.upper()
    payload = request.get_json(silent=True) or {}
    s_type = str(payload.get("type", "")).lower().strip()   # buy | sell
    price = _to_float(payload.get("price"), 0)

    if s_type not in ("buy", "sell") or price <= 0:
        return jsonify({"ok": False, "error": "bad input"}), 400

    data = read_json(DATA_SIGNALS, DEFAULT.copy())
    _ensure_symbol(data, symbol)

    # زمان: اگر فرستادی استفاده می‌کنیم، وگرنه الان
    try:
        time_str = str(payload.get("time")) if payload.get("time") else None
        if time_str:
            # اعتبارسنجی فرمت
            datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        else:
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    profit = 0.0

    if s_type == "buy":
        # ثبت خرید باز
        data["open_trades"][symbol] = round(price, 8)

    else:  # sell
        last_buy = data["open_trades"].get(symbol)
        if last_buy is not None:
            last_buy = _to_float(last_buy, 0)
            profit = round(price - last_buy, 8)
            # جمع سود/زیان
            data["total_profit"][symbol] = round(
                _to_float(data["total_profit"].get(symbol), 0) + profit, 8
            )
            # بستن پوزیشن باز
            data["open_trades"].pop(symbol, None)

    # ثبت در تاریخچه
    data["history"][symbol].append({
        "type": s_type,
        "price": round(price, 8),
        "time": time_str,
        "profit": profit if s_type == "sell" else 0
    })

    write_json(DATA_SIGNALS, data)

    return jsonify({
        "ok": True,
        "saved": {"type": s_type, "price": round(price, 8), "time": time_str, "profit": profit},
        "last_open_buy": float(data["open_trades"][symbol]) if symbol in data["open_trades"] else None,
        "total_profit": float(data["total_profit"].get(symbol, 0.0))
    })


# ---------- خروجی CSV ----------
@signals_bp.get("/<symbol>/csv")
def export_csv(symbol):
    """
    خروجی CSV با هدر:
      type,price,time,profit

    پارامترها:
      limit (اختیاری، پیش‌فرض همه)
      order ('desc' | 'asc'، پیش‌فرض 'asc' برای CSV تا از قدیم به جدید باشد)
    """
    symbol = symbol.upper()
    data = read_json(DATA_SIGNALS, DEFAULT.copy())
    _ensure_symbol(data, symbol)
    rows = data["history"][symbol]

    limit = request.args.get("limit", type=int)
    order = (request.args.get("order") or "asc").lower()
    if order not in ("asc", "desc"):
        order = "asc"

    rows_iter = rows if order == "asc" else list(reversed(rows))
    rows_iter = list(rows_iter)
    if isinstance(limit, int) and limit > 0:
        rows_iter = rows_iter[:limit]

    def generate():
        yield "type,price,time,profit\n"
        for r in rows_iter:
            t = r.get("type", "")
            p = r.get("price", "")
            tm = r.get("time", "")
            pr = r.get("profit", 0)
            yield f"{t},{p},{tm},{pr}\n"

    filename = f"{symbol}_signals.csv"
    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
