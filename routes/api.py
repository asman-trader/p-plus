from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import Dict, Any, Optional, List
import json
import urllib.request
import requests
from functools import wraps
import time

from db import get_db_connection, get_db_context
from price_fetcher import get_price_info, get_current_usd_rate, get_api_health, get_best_api, force_price_update

api_bp = Blueprint("api_bp", __name__, url_prefix="/api")

# Simple in-memory cache for API responses
_api_cache: Dict[str, Dict[str, Any]] = {}
CACHE_DURATION = 30  # seconds

def cached_response(cache_key: str, duration: int = CACHE_DURATION):
    """Decorator for caching API responses."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            if cache_key in _api_cache:
                cached_data, timestamp = _api_cache[cache_key]
                if now - timestamp < duration:
                    return jsonify(cached_data)
            
            result = func(*args, **kwargs)
            if hasattr(result, 'get_json'):
                _api_cache[cache_key] = (result.get_json(), now)
            return result
        return wrapper
    return decorator

def handle_api_errors(func):
    """Decorator for consistent API error handling."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return jsonify({
                "error": "Internal server error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500
    return wrapper


@api_bp.get("/wallet_balance")
@cached_response("wallet_balance", 60)  # Cache for 1 minute
@handle_api_errors
def get_wallet_balance():
    """Get wallet balances for BTC and USDT addresses."""
    with get_db_context() as conn:
        cur = conn.cursor()
        
        # Get wallet addresses in a single query
        cur.execute("""
            SELECT key, value FROM settings 
            WHERE key IN ('btc_wallet_address', 'usdt_wallet_address')
        """)
        settings = {row[0]: row[1] for row in cur.fetchall()}
        
        btc_address = settings.get('btc_wallet_address')
        usdt_address = settings.get('usdt_wallet_address')
        
        # If no addresses are configured
        if not btc_address and not usdt_address:
            return jsonify({
                "btc_balance": 0,
                "usdt_balance": 0,
                "error": "آدرس کیف پول‌ها تنظیم نشده است"
            })
        
        # Fetch balances concurrently
        btc_balance = _fetch_btc_balance(btc_address) if btc_address else 0
        usdt_balance = _fetch_usdt_balance(usdt_address) if usdt_address else 0
        
        return jsonify({
            "btc_balance": btc_balance,
            "usdt_balance": usdt_balance,
            "btc_address": btc_address,
            "usdt_address": usdt_address,
            "timestamp": datetime.utcnow().isoformat()
        })

def _fetch_btc_balance(address: str) -> float:
    """Fetch BTC balance from BlockCypher API."""
    try:
        response = requests.get(
            f'https://api.blockcypher.com/v1/btc/main/addrs/{address}/balance',
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('balance', 0) / 100000000  # Convert satoshi to BTC
    except Exception as e:
        print(f"Error fetching BTC balance: {e}")
    return 0.0

def _fetch_usdt_balance(address: str) -> float:
    """Fetch USDT balance from Covalent API."""
    try:
        response = requests.get(
            f'https://api.covalenthq.com/v1/1/address/{address}/balances_v2/?key=ckey_demo',
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('data') and data['data'].get('items'):
                for item in data['data']['items']:
                    if item.get('contract_ticker_symbol') == 'USDT':
                        return float(item.get('balance', 0)) / (10 ** int(item.get('contract_decimals', 6)))
    except Exception as e:
        print(f"Error fetching USDT balance: {e}")
    return 0.0


@api_bp.get("/price")
@cached_response("price_data", 30)  # Cache for 30 seconds
@handle_api_errors
def get_prices():
    """Get current cryptocurrency prices from multiple sources."""
    try:
        # Get prices from Wallex
        response = requests.get('https://api.wallex.ir/v1/currencies/stats', timeout=5)
        if response.status_code == 200:
            result = response.json()['result']
            btc_irt = next((float(item['price']) for item in result if item['key'] == 'BTC'), 0)
            usdt_irt = next((float(item['price']) for item in result if item['key'] == 'USDT'), 0)
            btc_usdt = btc_irt / usdt_irt if usdt_irt > 0 else 0

            # Get USDT to Toman price from async fetcher
            usdt_price_info = get_price_info()
            usdt_toman = usdt_price_info.get("usdt_price", 60000)

            return jsonify({
                "btc_irt": btc_irt,
                "usdt_irt": usdt_irt,
                "btc_usdt": btc_usdt,
                "usdt_toman": usdt_toman,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "wallex_async"
            })
        else:
            raise Exception(f"Wallex API returned status {response.status_code}")
    except Exception as e:
        # Fallback prices
        return jsonify({
            "btc_irt": 3000000000,
            "usdt_irt": 60000,
            "btc_usdt": 50000,
            "usdt_toman": 60000,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "fallback",
            "error": str(e)
        })

@api_bp.get("/usdt-price")
@cached_response("usdt_price", 15)  # Cache for 15 seconds
@handle_api_errors
def get_usdt_price():
	"""دریافت قیمت تتر به تومان از async fetcher"""
	price_info = get_price_info()
	if price_info.get("usdt_price"):
		return jsonify({
			"symbol": "USDTTMN",
			"price_toman": price_info["usdt_price"],
			"formatted": price_info["usdt_formatted"],
			"updated_at": price_info["updated_at"],
			"source": price_info.get("source", "unknown"),
			"cache_valid": price_info.get("cache_valid", False),
			"timestamp": datetime.utcnow().isoformat()
		})
	else:
		return jsonify({"error": "قیمت در دسترس نیست"}), 500

@api_bp.get("/api-health")
@cached_response("api_health", 30)  # Cache for 30 seconds
@handle_api_errors
def get_api_health_status():
	"""Get health status of all price APIs."""
	health = get_api_health()
	best_api = get_best_api()
	
	return jsonify({
		"apis": health,
		"best_api": best_api,
		"timestamp": datetime.utcnow().isoformat()
	})

@api_bp.post("/force-update")
@handle_api_errors
def force_update_prices():
	"""Force an immediate price update."""
	success = force_price_update()
	
	if success:
		# Clear relevant caches
		_api_cache.pop("price_data", None)
		_api_cache.pop("usdt_price", None)
		_api_cache.pop("wallet_balance", None)
		
		return jsonify({
			"success": True,
			"message": "Price update initiated successfully",
			"timestamp": datetime.utcnow().isoformat()
		})
	else:
		return jsonify({
			"success": False,
			"message": "Failed to update prices",
			"timestamp": datetime.utcnow().isoformat()
		}), 500



def _get_usd_to_toman(conn) -> float:
    """Get USD to Toman rate from async fetcher, fallback to settings."""
    # First try to get from async fetcher
    usd_rate = get_current_usd_rate()
    if usd_rate and usd_rate > 0:
        return usd_rate
    
    # Fallback to database settings
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
    row = cur.fetchone()
    return float(row[0]) if row else 60000.0


@api_bp.get("/purchases")
@cached_response("purchases_list", 10)  # Cache for 10 seconds
@handle_api_errors
def list_purchases():
    """Get list of all purchases."""
    with get_db_context() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, created_at, amount_btc, price_usd_per_btc 
            FROM purchases 
            ORDER BY id DESC
        """)
        rows = cur.fetchall()
        
        purchases = []
        for r in rows:
            amount_usd = float(r["amount_btc"]) * float(r["price_usd_per_btc"])
            purchases.append({
                "id": r["id"],
                "created_at": r["created_at"],
                "amount_btc": float(r["amount_btc"]),
                "price_usd_per_btc": float(r["price_usd_per_btc"]),
                "amount_usd": amount_usd,
            })
        return jsonify(purchases)


@api_bp.post("/purchases")
@handle_api_errors
def create_purchase():
    """Create a new purchase record."""
    payload = request.get_json(silent=True) or {}
    
    try:
        amount_btc = float(payload.get("amount_btc", 0))
        price_usd_per_btc = float(payload.get("price_usd_per_btc", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid payload"}), 400

    if amount_btc <= 0 or price_usd_per_btc <= 0:
        return jsonify({"error": "amount_btc and price_usd_per_btc must be > 0"}), 400

    with get_db_context() as conn:
        cur = conn.cursor()
        created_at = datetime.utcnow().isoformat(timespec="seconds")
        cur.execute(
            "INSERT INTO purchases(created_at, amount_btc, price_usd_per_btc) VALUES(?,?,?)",
            (created_at, amount_btc, price_usd_per_btc),
        )
        new_id = cur.lastrowid
        conn.commit()
        
        # Clear cache
        _api_cache.pop("purchases_list", None)
        
        return jsonify({
            "id": new_id,
            "created_at": created_at,
            "amount_btc": amount_btc,
            "price_usd_per_btc": price_usd_per_btc,
            "amount_usd": amount_btc * price_usd_per_btc,
        }), 201


@api_bp.delete("/purchases/<int:purchase_id>")
def delete_purchase(purchase_id: int):
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute("DELETE FROM purchases WHERE id = ?", (purchase_id,))
	deleted = cur.rowcount
	conn.commit()
	conn.close()
	if deleted == 0:
		return jsonify({"error": "not found"}), 404
	return jsonify({"ok": True})


@api_bp.get("/totals")
def totals():
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM purchases")
	total_usd = float(cur.fetchone()[0] or 0)
	usd_to_toman = _get_usd_to_toman(conn)
	total_toman = total_usd * usd_to_toman
	conn.close()
	return jsonify({"total_usd": total_usd, "usd_to_toman": usd_to_toman, "total_toman": total_toman})


@api_bp.get("/rate")
def get_rate():
	conn = get_db_connection()
	rate = _get_usd_to_toman(conn)
	conn.close()
	return jsonify({"usd_to_toman": rate})


@api_bp.put("/rate")
def set_rate():
	payload = request.get_json(silent=True) or {}
	try:
		new_rate = float(payload.get("usd_to_toman", 0))
	except (TypeError, ValueError):
		return jsonify({"error": "invalid usd_to_toman"}), 400
	if new_rate <= 0:
		return jsonify({"error": "usd_to_toman must be > 0"}), 400
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute(
		"INSERT INTO settings(key, value) VALUES('usd_to_toman', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
		(str(new_rate),),
	)
	conn.commit()
	conn.close()
	return jsonify({"usd_to_toman": new_rate})


def _get_setting(key: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cur.fetchone()
    conn.close()
    return None if not row else row[0]


def _set_setting(key: str, value: str) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()


def _fetch_json(url: str):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=6) as resp:
        return json.loads(resp.read().decode("utf-8"))


@api_bp.get("/price/btcusd")
def price_btcusd():
    # Try multiple free sources, first successful wins
    sources = [
        ("coindesk", "https://api.coindesk.com/v1/bpi/currentprice/USD.json", lambda data: float(data["bpi"]["USD"]["rate_float"])),
        ("binance", "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", lambda data: float(data["price"])),
        ("bitstamp", "https://www.bitstamp.net/api/v2/ticker/btcusd/", lambda data: float(data["last"])),
        ("coingecko", "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", lambda data: float(data["bitcoin"]["usd"]))
    ]
    for name, url, picker in sources:
        try:
            payload = _fetch_json(url)
            price = picker(payload)
            if not (price and price > 0):
                continue
            try:
                _set_setting("last_price_usd", str(price))
            except Exception:
                pass
            return jsonify({"source": name, "price_usd": price})
        except Exception:
            continue

    # Fallback to cached price if available
    try:
        cached = _get_setting("last_price_usd")
        if cached:
            price = float(cached)
            if price > 0:
                return jsonify({"source": "cache", "price_usd": price, "stale": True})
    except Exception:
        pass

    return jsonify({"error": "unavailable"})


@api_bp.get("/price/btcusd2")
def price_btcusd2():
    try:
        cached = _get_setting("last_price_usd")
        if cached:
            price = float(cached)
            if price > 0:
                return jsonify({"source": "cache", "price_usd": price, "stale": True})
    except Exception:
        pass
    return jsonify({"error": "unavailable"})


@api_bp.after_request
def add_cors_headers(resp):
    resp.headers.setdefault("Access-Control-Allow-Origin", "*")
    resp.headers.setdefault("Access-Control-Allow-Headers", "Content-Type, Authorization")
    resp.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    return resp


@api_bp.get("/withdrawals")
def list_withdrawals():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, created_at, amount_btc, price_usd_per_btc FROM withdrawals ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    withdrawals = []
    for r in rows:
        amount_usd = float(r["amount_btc"]) * float(r["price_usd_per_btc"])
        withdrawals.append({
            "id": r["id"],
            "created_at": r["created_at"],
            "amount_btc": float(r["amount_btc"]),
            "price_usd_per_btc": float(r["price_usd_per_btc"]),
            "amount_usd": amount_usd,
        })
    return jsonify(withdrawals)


@api_bp.post("/withdrawals")
def create_withdrawal():
    payload = request.get_json(silent=True) or {}
    try:
        amount_btc = float(payload.get("amount_btc", 0))
        price_usd_per_btc = float(payload.get("price_usd_per_btc", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid payload"}), 400

    if amount_btc <= 0 or price_usd_per_btc <= 0:
        return jsonify({"error": "amount_btc and price_usd_per_btc must be > 0"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    created_at = datetime.utcnow().isoformat(timespec="seconds")
    cur.execute(
        "INSERT INTO withdrawals(created_at, amount_btc, price_usd_per_btc) VALUES(?,?,?)",
        (created_at, amount_btc, price_usd_per_btc),
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return jsonify({
        "id": new_id,
        "created_at": created_at,
        "amount_btc": amount_btc,
        "price_usd_per_btc": price_usd_per_btc,
        "amount_usd": amount_btc * price_usd_per_btc,
    }), 201


@api_bp.delete("/withdrawals/<int:withdrawal_id>")
def delete_withdrawal(withdrawal_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM withdrawals WHERE id = ?", (withdrawal_id,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    if deleted == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


@api_bp.get("/summary")
def summary():
    conn = get_db_connection()
    cur = conn.cursor()
    # Purchases totals
    cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0), COALESCE(SUM(amount_btc), 0) FROM purchases")
    row_p = cur.fetchone()
    total_usd = float(row_p[0] or 0)
    total_btc = float(row_p[1] or 0)
    # Withdrawals totals
    cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0), COALESCE(SUM(amount_btc), 0) FROM withdrawals")
    row_w = cur.fetchone()
    total_withdraw_usd = float(row_w[0] or 0)
    total_withdraw_btc = float(row_w[1] or 0)
    # Settings
    usd_to_toman = _get_usd_to_toman(conn)
    conn.close()
    return jsonify({
        "total_deposit_usd": total_usd,
        "total_deposit_btc": total_btc,
        "total_withdraw_usd": total_withdraw_usd,
        "total_withdraw_btc": total_withdraw_btc,
        "usd_to_toman": usd_to_toman,
        "total_deposit_toman": total_usd * usd_to_toman,
        "total_withdraw_toman": total_withdraw_usd * usd_to_toman,
        "net_invested_usd": max(0.0, total_usd - total_withdraw_usd),
    })

