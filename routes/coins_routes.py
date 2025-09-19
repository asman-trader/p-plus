# routes/coins_routes.py
from flask import Blueprint, jsonify, request, current_app
import os, time, random
import requests

coins_bp = Blueprint("coins", __name__)

# =========================
# تنظیمات و کش
# =========================
CMC_API_KEY = os.getenv("CMC_API_KEY", "29475099-1a72-4895-89da-51dabc3cbf9e")
CMC_ENDPOINT = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
CACHE_TTL = 10  # ثانیه

_cache = {}  # {"BTC": {"price": 12345.67, "t": 1712345678.9}}
_base_prices = {  # برای fallback خیلی کوتاه
    "BTC": 65000.0, "ETH": 3000.0, "BNB": 550.0, "SOL": 150.0, "XRP": 0.52,
    "ADA": 0.45, "DOGE": 0.12, "TON": 7.2, "AVAX": 30.0, "DOT": 6.5
}

def _from_cache(symbol: str):
    s = symbol.upper()
    ent = _cache.get(s)
    if ent and (time.time() - ent["t"] <= CACHE_TTL):
        return ent["price"]
    return None

def _save_cache(symbol: str, price: float):
    _cache[symbol.upper()] = {"price": float(price), "t": time.time()}

def _fallback_price(symbol: str):
    """در صورت قطعی API: آخرین کش + نویز کوچک؛ و اگر نبود، پایه با نوسان خیلی کم."""
    s = symbol.upper()
    ent = _cache.get(s)
    if ent:
        p = ent["price"] * (1 + random.uniform(-0.0015, 0.0015))
        _save_cache(s, p)
        return p
    base = _base_prices.get(s, 10.0)
    p = base * (1 + random.uniform(-0.002, 0.002))
    _save_cache(s, p)
    return p

def _fetch_cmc_price(symbol: str) -> float:
    """گرفتن قیمت لحظه‌ای از CoinMarketCap (بر حسب USD)."""
    sym = symbol.upper()
    headers = {
        "Accept": "application/json",
        "X-CMC_PRO_API_KEY": CMC_API_KEY,
        "Accept-Encoding": "deflate, gzip"
    }
    params = {"symbol": sym, "convert": "USD"}
    resp = requests.get(CMC_ENDPOINT, headers=headers, params=params, timeout=6)
    resp.raise_for_status()
    data = resp.json()
    # ساختار: data['data'][SYM]['quote']['USD']['price']
    price = data["data"][sym]["quote"]["USD"]["price"]
    return float(price)

# =========================
# روت‌ها
# =========================
@coins_bp.get("/price/<symbol>")
def price(symbol):
    sym = symbol.upper()
    current_app.logger.info(f'Price request for symbol: {sym}')
    
    # 1) کش
    p = _from_cache(sym)
    if p is not None:
        current_app.logger.debug(f'Price from cache for {sym}: {p}')
        return jsonify({"symbol": sym, "price": p, "source": "cache"})

    # 2) API واقعی
    try:
        current_app.logger.info(f'Fetching price from CMC for {sym}')
        p = _fetch_cmc_price(sym)
        _save_cache(sym, p)
        current_app.logger.info(f'Successfully fetched price for {sym}: {p}')
        return jsonify({"symbol": sym, "price": p, "source": "coinmarketcap"})
    except Exception as e:
        # 3) fallback امن
        current_app.logger.warning(f'CMC API failed for {sym}: {str(e)}. Using fallback.')
        p = _fallback_price(sym)
        return jsonify({"symbol": sym, "price": p, "source": "fallback", "error": str(e)[:120]}), 200

@coins_bp.get("/prices")
def prices_bulk():
    """
    گرفتن چند نماد باهم:
    /prices?symbols=BTC,ETH,BNB
    """
    symbols = request.args.get("symbols", "")
    symbols = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbols:
        return jsonify({"ok": False, "error": "symbols param required"}), 400

    out = {}
    # ابتدا تلاش از کش
    remaining = []
    for s in symbols:
        p = _from_cache(s)
        if p is None:
            remaining.append(s)
        else:
            out[s] = {"price": p, "source": "cache"}

    # سپس یک‌به‌یک از API (بهینه: می‌توان با join هم زد، ولی CMC با 'symbol=BTC,ETH' هم کار می‌کند)
    try:
        if remaining:
            headers = {
                "Accept": "application/json",
                "X-CMC_PRO_API_KEY": CMC_API_KEY,
                "Accept-Encoding": "deflate, gzip"
            }
            params = {"symbol": ",".join(remaining), "convert": "USD"}
            resp = requests.get(CMC_ENDPOINT, headers=headers, params=params, timeout=7)
            resp.raise_for_status()
            data = resp.json()["data"]
            for s in remaining:
                if s in data:
                    p = float(data[s]["quote"]["USD"]["price"])
                    _save_cache(s, p)
                    out[s] = {"price": p, "source": "coinmarketcap"}
                else:
                    # اگر CMC برنگرداند
                    p = _fallback_price(s)
                    out[s] = {"price": p, "source": "fallback"}
    except Exception:
        for s in remaining:
            p = _fallback_price(s)
            out[s] = {"price": p, "source": "fallback"}

    return jsonify(out)
