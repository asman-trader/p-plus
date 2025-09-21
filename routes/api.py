from flask import Blueprint, request, jsonify  # pyright: ignore[reportMissingImports]
from datetime import datetime
from db import get_db_connection
import json
import urllib.request

api_bp = Blueprint("api_bp", __name__, url_prefix="/api")


def _get_usd_to_toman(conn) -> float:
	cur = conn.cursor()
	cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
	row = cur.fetchone()
	return float(row[0]) if row else 0.0


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


@api_bp.get("/price/btcusd")
def price_btcusd():
	# Try multiple free sources, first successful wins
	sources = [
		("coindesk", "https://api.coindesk.com/v1/bpi/currentprice/USD.json", lambda data: float(data["bpi"]["USD"]["rate_float"])) ,
		("binance", "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", lambda data: float(data["price"])) ,
		("bitstamp", "https://www.bitstamp.net/api/v2/ticker/btcusd/", lambda data: float(data["last"])) ,
	]
	for name, url, picker in sources:
		try:
			with urllib.request.urlopen(url, timeout=5) as resp:
				payload = json.loads(resp.read().decode("utf-8"))
				price = picker(payload)
				return jsonify({"source": name, "price_usd": price})
		except Exception:
			continue
	return jsonify({"error": "failed to fetch"}), 502


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

