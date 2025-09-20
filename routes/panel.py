from flask import Blueprint, render_template, redirect, url_for, flash, request  # pyright: ignore[reportMissingImports]
from datetime import datetime
from db import get_db_connection

panel_bp = Blueprint("panel_bp", __name__)


@panel_bp.get("/panel")
def panel_index():
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute("SELECT id, created_at, amount_btc, price_usd_per_btc FROM purchases ORDER BY id DESC")
	purchases = cur.fetchall()
	cur.execute("SELECT id, created_at, amount_btc, price_usd_per_btc FROM withdrawals ORDER BY id DESC")
	withdrawals = cur.fetchall()
	# Total deposits in USD and BTC
	cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM purchases")
	total_usd = cur.fetchone()[0] or 0
	cur.execute("SELECT COALESCE(SUM(amount_btc), 0) FROM purchases")
	total_btc = float(cur.fetchone()[0] or 0)
	cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM withdrawals")
	total_withdraw_usd = cur.fetchone()[0] or 0
	cur.execute("SELECT COALESCE(SUM(amount_btc), 0) FROM withdrawals")
	total_withdraw_btc = float(cur.fetchone()[0] or 0)
	cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
	usd_to_toman = float(cur.fetchone()[0])
	total_toman = total_usd * usd_to_toman
	conn.close()
	return render_template(
		"panel.html",
		purchases=purchases,
		withdrawals=withdrawals,
		total_usd=total_usd,
		usd_to_toman=usd_to_toman,
		total_toman=total_toman,
		total_btc=total_btc,
		total_withdraw_usd=total_withdraw_usd,
		total_withdraw_toman=total_withdraw_usd * usd_to_toman,
		total_withdraw_btc=total_withdraw_btc,
	)


@panel_bp.post("/panel/add")
def panel_add():
	try:
		amount_btc = float(request.form.get("amount_btc", "0").strip())
		price_usd_per_btc = float(request.form.get("price_usd_per_btc", "0").strip())
	except ValueError:
		flash("مقادیر وارد شده نامعتبر است.", "error")
		return redirect(url_for("panel_bp.deposits_page"))

	if amount_btc <= 0 or price_usd_per_btc <= 0:
		flash("مقادیر باید بزرگ‌تر از صفر باشند.", "error")
		return redirect(url_for("panel_bp.deposits_page"))

	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute("INSERT INTO purchases(created_at, amount_btc, price_usd_per_btc) VALUES(?,?,?)", (datetime.utcnow().isoformat(timespec="seconds"), amount_btc, price_usd_per_btc))
	conn.commit()
	conn.close()
	flash("خرید با موفقیت ثبت شد.", "success")
	return redirect(url_for("panel_bp.deposits_page"))


@panel_bp.post("/panel/withdraw")
def panel_withdraw():
	try:
		amount_btc = float(request.form.get("amount_btc", "0").strip())
		price_usd_per_btc = float(request.form.get("price_usd_per_btc", "0").strip())
	except ValueError:
		flash("مقادیر وارد شده نامعتبر است.", "error")
		return redirect(url_for("panel_bp.withdrawals_page"))

	if amount_btc <= 0 or price_usd_per_btc <= 0:
		flash("مقادیر باید بزرگ‌تر از صفر باشند.", "error")
		return redirect(url_for("panel_bp.withdrawals_page"))

	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute("INSERT INTO withdrawals(created_at, amount_btc, price_usd_per_btc) VALUES(?,?,?)", (datetime.utcnow().isoformat(timespec="seconds"), amount_btc, price_usd_per_btc))
	conn.commit()
	conn.close()
	flash("برداشت با موفقیت ثبت شد.", "success")
	return redirect(url_for("panel_bp.withdrawals_page"))


@panel_bp.post("/panel/rate")
def panel_update_rate():
	try:
		new_rate = float(request.form.get("usd_to_toman", "0").strip())
	except ValueError:
		flash("نرخ نامعتبر است.", "error")
		return redirect(url_for("panel_bp.panel_index"))

	if new_rate <= 0:
		flash("نرخ باید بزرگ‌تر از صفر باشد.", "error")
		return redirect(url_for("panel_bp.panel_index"))

	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute("INSERT INTO settings(key, value) VALUES('usd_to_toman', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(new_rate),))
	conn.commit()
	conn.close()
	flash("نرخ با موفقیت به‌روزرسانی شد.", "success")
	return redirect(url_for("panel_bp.settings_page"))


@panel_bp.get("/")
def home():
	return redirect(url_for("panel_bp.panel_index"))


@panel_bp.get("/healthz")
def healthz():
	return "ok", 200
@panel_bp.get("/settings")
def settings_page():
	# Load current rate
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
	row = cur.fetchone()
	usd_to_toman = float(row[0]) if row else 60000.0
	conn.close()
	return render_template("settings.html", usd_to_toman=usd_to_toman)



@panel_bp.get("/deposits")
def deposits_page():
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM purchases")
	total_usd = cur.fetchone()[0] or 0
	cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
	usd_to_toman = float(cur.fetchone()[0])
	total_toman = total_usd * usd_to_toman
	conn.close()
	return render_template("deposits.html", total_usd=total_usd, usd_to_toman=usd_to_toman, total_toman=total_toman)


@panel_bp.get("/withdrawals")
def withdrawals_page():
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute("SELECT id, created_at, amount_btc, price_usd_per_btc FROM withdrawals ORDER BY id DESC")
	withdrawals = cur.fetchall()
	cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM withdrawals")
	total_withdraw_usd = cur.fetchone()[0] or 0
	cur.execute("SELECT COALESCE(SUM(amount_btc), 0) FROM withdrawals")
	total_withdraw_btc = float(cur.fetchone()[0] or 0)
	cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
	usd_to_toman = float(cur.fetchone()[0])
	conn.close()
	return render_template("withdrawals.html", withdrawals=withdrawals, total_withdraw_usd=total_withdraw_usd, total_withdraw_btc=total_withdraw_btc, total_withdraw_toman=total_withdraw_usd * usd_to_toman, usd_to_toman=usd_to_toman)


@panel_bp.get("/balance")
def balance_page():
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute("SELECT COALESCE(SUM(amount_btc), 0) FROM purchases")
	total_btc = float(cur.fetchone()[0] or 0)
	cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
	usd_to_toman = float(cur.fetchone()[0])
	conn.close()
	return render_template("balance.html", total_btc=total_btc, usd_to_toman=usd_to_toman)


@panel_bp.get("/purchases")
def purchases_page():
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute("SELECT id, created_at, amount_btc, price_usd_per_btc FROM purchases ORDER BY id DESC")
	rows_p = cur.fetchall()
	cur.execute("SELECT id, created_at, amount_btc, price_usd_per_btc FROM withdrawals ORDER BY id ASC")
	rows_w = cur.fetchall()
	cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
	usd_to_toman = float(cur.fetchone()[0])
	conn.close()
	# Convert sqlite3.Row to plain dicts for JSON serialization in template
	purchases = [
		{
			"id": int(r["id"]),
			"created_at": r["created_at"],
			"amount_btc": float(r["amount_btc"]),
			"price_usd_per_btc": float(r["price_usd_per_btc"]),
		}
		for r in rows_p
	]
	withdrawals = [
		{
			"id": int(r["id"]),
			"created_at": r["created_at"],
			"amount_btc": float(r["amount_btc"]),
			"price_usd_per_btc": float(r["price_usd_per_btc"]),
		}
		for r in rows_w
	]
	return render_template("purchases.html", purchases=purchases, withdrawals=withdrawals, usd_to_toman=usd_to_toman)


