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
	# Total deposits in USD and BTC
	cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM purchases")
	total_usd = cur.fetchone()[0] or 0
	cur.execute("SELECT COALESCE(SUM(amount_btc), 0) FROM purchases")
	total_btc = float(cur.fetchone()[0] or 0)
	cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
	usd_to_toman = float(cur.fetchone()[0])
	total_toman = total_usd * usd_to_toman
	conn.close()
	return render_template(
		"panel.html",
		purchases=purchases,
		total_usd=total_usd,
		usd_to_toman=usd_to_toman,
		total_toman=total_toman,
		total_btc=total_btc,
	)


@panel_bp.post("/panel/add")
def panel_add():
	try:
		amount_btc = float(request.form.get("amount_btc", "0").strip())
		price_usd_per_btc = float(request.form.get("price_usd_per_btc", "0").strip())
	except ValueError:
		flash("مقادیر وارد شده نامعتبر است.", "error")
		return redirect(url_for("panel_index"))

	if amount_btc <= 0 or price_usd_per_btc <= 0:
		flash("مقادیر باید بزرگ‌تر از صفر باشند.", "error")
		return redirect(url_for("panel_index"))

	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute("INSERT INTO purchases(created_at, amount_btc, price_usd_per_btc) VALUES(?,?,?)", (datetime.utcnow().isoformat(timespec="seconds"), amount_btc, price_usd_per_btc))
	conn.commit()
	conn.close()
	flash("خرید با موفقیت ثبت شد.", "success")
	return redirect(url_for("panel_index"))


@panel_bp.post("/panel/rate")
def panel_update_rate():
	try:
		new_rate = float(request.form.get("usd_to_toman", "0").strip())
	except ValueError:
		flash("نرخ نامعتبر است.", "error")
		return redirect(url_for("panel_index"))

	if new_rate <= 0:
		flash("نرخ باید بزرگ‌تر از صفر باشد.", "error")
		return redirect(url_for("panel_index"))

	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute("INSERT INTO settings(key, value) VALUES('usd_to_toman', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(new_rate),))
	conn.commit()
	conn.close()
	flash("نرخ با موفقیت به‌روزرسانی شد.", "success")
	return redirect(url_for("panel_index"))


@panel_bp.get("/")
def home():
	return redirect(url_for("panel_index"))


@panel_bp.get("/healthz")
def healthz():
	return "ok", 200


