from flask import Blueprint, request, jsonify  # pyright: ignore[reportMissingImports]
from datetime import datetime
from db import get_db_connection
import json
import urllib.request
import requests
from price_fetcher import get_price_info

api_bp = Blueprint("api_bp", __name__, url_prefix="/api")


@api_bp.get("/wallet_balance")
def get_wallet_balance():
	try:
		conn = get_db_connection()
		cur = conn.cursor()
		
		# دریافت آدرس کیف پول‌ها
		cur.execute("SELECT value FROM settings WHERE key='btc_wallet_address'")
		btc_row = cur.fetchone()
		btc_address = btc_row[0] if btc_row and btc_row[0] else None
		
		cur.execute("SELECT value FROM settings WHERE key='usdt_wallet_address'")
		usdt_row = cur.fetchone()
		usdt_address = usdt_row[0] if usdt_row and usdt_row[0] else None
		
		conn.close()
		
		# اگر آدرس‌ها تنظیم نشده باشند
		if not btc_address and not usdt_address:
			return jsonify({
				"btc_balance": 0,
				"usdt_balance": 0,
				"error": "آدرس کیف پول‌ها تنظیم نشده است"
			})
		
		# دریافت موجودی بیت‌کوین
		btc_balance = 0
		if btc_address:
			try:
				# استفاده از BlockCypher API برای بیت‌کوین
				response = requests.get(f'https://api.blockcypher.com/v1/btc/main/addrs/{btc_address}/balance', timeout=10)
				if response.status_code == 200:
					data = response.json()
					btc_balance = data.get('balance', 0) / 100000000  # تبدیل از satoshi به BTC
			except Exception as e:
				print(f"Error fetching BTC balance: {e}")
		
		# دریافت موجودی تتر (USDT)
		usdt_balance = 0
		if usdt_address:
			try:
				# استفاده از Covalent API برای USDT (ERC-20) - رایگان
				# این API نیازی به API key ندارد
				response = requests.get(f'https://api.covalenthq.com/v1/1/address/{usdt_address}/balances_v2/?key=ckey_demo', timeout=10)
				if response.status_code == 200:
					data = response.json()
					if data.get('data') and data['data'].get('items'):
						for item in data['data']['items']:
							if item.get('contract_ticker_symbol') == 'USDT':
								usdt_balance = float(item.get('balance', 0)) / (10 ** int(item.get('contract_decimals', 6)))
								break
			except Exception as e:
				print(f"Error fetching USDT balance from Covalent: {e}")
				# Fallback: استفاده از Etherscan API (نیاز به API key)
				try:
					api_key = "YourApiKeyToken"  # باید از etherscan.io دریافت شود
					response = requests.get(f'https://api.etherscan.io/api?module=account&action=tokenbalance&contractaddress=0xdAC17F958D2ee523a2206206994597C13D831ec7&address={usdt_address}&tag=latest&apikey={api_key}', timeout=10)
					if response.status_code == 200:
						data = response.json()
						if data.get('status') == '1':
							usdt_balance = int(data.get('result', 0)) / 1000000  # USDT has 6 decimals
				except Exception as e2:
					print(f"Error fetching USDT balance from Etherscan: {e2}")
		
		return jsonify({
			"btc_balance": btc_balance,
			"usdt_balance": usdt_balance,
			"btc_address": btc_address,
			"usdt_address": usdt_address,
			"timestamp": datetime.utcnow().isoformat()
		})
		
	except Exception as e:
		return jsonify({
			"btc_balance": 0,
			"usdt_balance": 0,
			"error": str(e),
			"timestamp": datetime.utcnow().isoformat()
		})


@api_bp.get("/price")
def get_prices():
	try:
		# دریافت قیمت از والکس
		response = requests.get('https://api.wallex.ir/v1/currencies/stats', timeout=5)
		if response.status_code == 200:
			result = response.json()['result']
			btc_irt = next((float(item['price']) for item in result if item['key'] == 'BTC'), 0)
			usdt_irt = next((float(item['price']) for item in result if item['key'] == 'USDT'), 0)
			btc_usdt = btc_irt / usdt_irt if usdt_irt > 0 else 0

			# دریافت قیمت تتر به تومان از async fetcher
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
			raise Exception(f"API returned status {response.status_code}")
	except Exception as e:
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
def get_usdt_price():
	"""دریافت قیمت تتر به تومان از async fetcher"""
	price_info = get_price_info()
	if price_info.get("usdt_price"):
		return jsonify({
			"symbol": "USDTTMN",
			"price_toman": price_info["usdt_price"],
			"formatted": price_info["usdt_formatted"],
			"updated_at": price_info["updated_at"],
			"timestamp": datetime.utcnow().isoformat()
		})
	else:
		return jsonify({"error": "قیمت در دسترس نیست"}), 500



def _get_usd_to_toman(conn) -> float:
	"""Get USD to Toman rate from async fetcher, fallback to settings"""
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
def list_purchases():
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute("SELECT id, created_at, amount_btc, price_usd_per_btc FROM purchases ORDER BY id DESC")
	rows = cur.fetchall()
	conn.close()
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
def create_purchase():
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
		"INSERT INTO purchases(created_at, amount_btc, price_usd_per_btc) VALUES(?,?,?)",
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

