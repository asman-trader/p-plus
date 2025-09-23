from flask import Blueprint, render_template, redirect, url_for, flash, request  # pyright: ignore[reportMissingImports]
from datetime import datetime
from db import get_db_connection
import requests

panel_bp = Blueprint("panel_bp", __name__)


def _to_float(txt: str) -> float:
	"""Parse user input numbers with Persian digits and separators to float."""
	if txt is None:
		return 0.0
	s = str(txt).strip()
	# Convert Persian digits to ASCII
	persian_digits = "۰۱۲۳۴۵۶۷۸۹"
	for i, d in enumerate(persian_digits):
		s = s.replace(d, str(i))
	# normalize separators and spaces
	s = s.replace("،", ",").replace("٬", ",").replace("٫", ".")
	s = s.replace(" ", "")
	# remove thousand separators / unify decimal
	if s.count(",") > 0 and "." in s:
		s = s.replace(",", "")
	elif s.count(",") == 1 and "." not in s:
		s = s.replace(",", ".")
	else:
		s = s.replace(",", "")
	try:
		return float(s)
	except Exception:
		return float("nan")

@panel_bp.get("/panel")
def panel_index():
	conn = get_db_connection()
	cur = conn.cursor()
	
	# دریافت آخرین تراکنش‌ها
	cur.execute("SELECT id, created_at, amount_btc, price_usd_per_btc FROM purchases ORDER BY id DESC LIMIT 5")
	purchases = cur.fetchall()
	cur.execute("SELECT id, created_at, amount_btc, price_usd_per_btc FROM withdrawals ORDER BY id DESC LIMIT 5")
	withdrawals = cur.fetchall()
	
	# محاسبه آمار کلی
	cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM purchases")
	total_purchased_usd = float(cur.fetchone()[0] or 0)
	cur.execute("SELECT COALESCE(SUM(amount_btc), 0) FROM purchases")
	total_purchased_btc = float(cur.fetchone()[0] or 0)
	
	cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM withdrawals")
	total_withdrawn_usd = float(cur.fetchone()[0] or 0)
	cur.execute("SELECT COALESCE(SUM(amount_btc), 0) FROM withdrawals")
	total_withdrawn_btc = float(cur.fetchone()[0] or 0)
	
	# محاسبه موجودی فعلی
	current_btc_balance = total_purchased_btc - total_withdrawn_btc
	net_invested_usd = total_purchased_usd - total_withdrawn_usd
	
	# نرخ تبدیل
	# cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
	# usd_to_toman = float(cur.fetchone()[0])
	usd_to_toman = 60000  # Default
	try:
		response = requests.post('https://api.nobitex.ir/market/stats', json={"srcCurrency": "usdt", "dstCurrency": "rls"}, timeout=3)
		if response.status_code == 200:
			data = response.json()["stats"]["usdt-rls"]
			usd_to_toman = float(data["latest"])
	except Exception:
		pass
	
	# محاسبه ROI (درصد سود/زیان)
	roi_percentage = 0
	if net_invested_usd > 0:
		# اینجا باید قیمت فعلی BTC را از API دریافت کنیم
		# برای حالا از یک قیمت ثابت استفاده می‌کنیم
		current_btc_price = 50000  # این باید از API دریافت شود
		current_value_usd = current_btc_balance * current_btc_price
		roi_percentage = ((current_value_usd - net_invested_usd) / net_invested_usd) * 100
	
	# تاریخ شروع سرمایه‌گذاری
	cur.execute("SELECT MIN(created_at) FROM purchases")
	row_first = cur.fetchone()
	inception_days = 0
	try:
		first_str = row_first[0] if row_first and row_first[0] else None
		if first_str:
			dt0 = datetime.fromisoformat(first_str)
			inception_days = max(0, (datetime.utcnow() - dt0).days)
	except Exception:
		inception_days = 0
	
	conn.close()

	return render_template(
		"panel.html",
		purchases=purchases,
		withdrawals=withdrawals,
		total_purchased_usd=total_purchased_usd,
		total_purchased_btc=total_purchased_btc,
		total_withdrawn_usd=total_withdrawn_usd,
		total_withdrawn_btc=total_withdrawn_btc,
		current_btc_balance=current_btc_balance,
		net_invested_usd=net_invested_usd,
		usd_to_toman=usd_to_toman,
		roi_percentage=roi_percentage,
		inception_days=inception_days,
	)


@panel_bp.post("/panel/add")
def panel_add():
	try:
		amount_btc = _to_float(request.form.get("amount_btc", "0"))
		price_usd_per_btc = _to_float(request.form.get("price_usd_per_btc", "0"))
		if not (amount_btc == amount_btc and price_usd_per_btc == price_usd_per_btc):  # NaN check
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
	except Exception as e:
		print("[panel_add] error:", e)
		flash("خطای داخلی هنگام ثبت واریزی.", "error")
		return redirect(url_for("panel_bp.deposits_page"))


@panel_bp.post("/panel/withdraw")
def panel_withdraw():
	try:
		amount_btc = _to_float(request.form.get("amount_btc", "0"))
		price_usd_per_btc = _to_float(request.form.get("price_usd_per_btc", "0"))
		if not (amount_btc == amount_btc and price_usd_per_btc == price_usd_per_btc):
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
	except Exception as e:
		print("[panel_withdraw] error:", e)
		flash("خطای داخلی هنگام ثبت برداشت.", "error")
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
    return redirect(url_for("auth_bp.login"))


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
	rows = cur.fetchall()
	cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM withdrawals")
	total_withdraw_usd = cur.fetchone()[0] or 0
	cur.execute("SELECT COALESCE(SUM(amount_btc), 0) FROM withdrawals")
	total_withdraw_btc = float(cur.fetchone()[0] or 0)
	cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
	usd_to_toman = float(cur.fetchone()[0])
	conn.close()
	
	# Convert sqlite3.Row to plain dicts for JSON serialization
	withdrawals = [
		{
			"id": int(r["id"]),
			"created_at": r["created_at"],
			"amount_btc": float(r["amount_btc"]),
			"price_usd_per_btc": float(r["price_usd_per_btc"]),
		}
		for r in rows
	]
	
	return render_template("withdrawals.html", withdrawals=withdrawals, total_withdraw_usd=total_withdraw_usd, total_withdraw_btc=total_withdraw_btc, total_withdraw_toman=total_withdraw_usd * usd_to_toman, usd_to_toman=usd_to_toman)


@panel_bp.get("/balance")
def balance_page():
	conn = get_db_connection()
	cur = conn.cursor()
	
	# محاسبه موجودی واقعی (خرید - برداشت)
	cur.execute("SELECT COALESCE(SUM(amount_btc), 0) FROM purchases")
	total_purchased_btc = float(cur.fetchone()[0] or 0)
	cur.execute("SELECT COALESCE(SUM(amount_btc), 0) FROM withdrawals")
	total_withdrawn_btc = float(cur.fetchone()[0] or 0)
	current_btc_balance = total_purchased_btc - total_withdrawn_btc
	
	# محاسبه ارزش سرمایه‌گذاری شده
	cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM purchases")
	total_invested_usd = float(cur.fetchone()[0] or 0)
	cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM withdrawals")
	total_withdrawn_usd = float(cur.fetchone()[0] or 0)
	net_invested_usd = total_invested_usd - total_withdrawn_usd
	
	# نرخ تبدیل
	# cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
	# usd_to_toman = float(cur.fetchone()[0])
	usd_to_toman = 60000  # Default
	try:
		response = requests.post('https://api.nobitex.ir/market/stats', json={"srcCurrency": "usdt", "dstCurrency": "rls"}, timeout=3)
		if response.status_code == 200:
			data = response.json()["stats"]["usdt-rls"]
			usd_to_toman = float(data["latest"])
	except Exception:
		pass
	
	# تاریخ آخرین تراکنش
	cur.execute("SELECT MAX(created_at) FROM (SELECT created_at FROM purchases UNION ALL SELECT created_at FROM withdrawals)")
	last_transaction_date = cur.fetchone()[0]
	
	# تعداد تراکنش‌ها
	cur.execute("SELECT COUNT(*) FROM purchases")
	total_purchases_count = cur.fetchone()[0]
	cur.execute("SELECT COUNT(*) FROM withdrawals")
	total_withdrawals_count = cur.fetchone()[0]
	
	# Fetch all transactions
	cur.execute("""
		SELECT id, created_at, amount_btc, price_usd_per_btc, 'purchase' as type 
		FROM purchases 
		UNION ALL 
		SELECT id, created_at, amount_btc, price_usd_per_btc, 'withdrawal' as type 
		FROM withdrawals 
		ORDER BY created_at DESC
	""")
	transactions = [
		{
			"id": r[0],
			"created_at": r[1],
			"amount_btc": r[2],
			"price_usd_per_btc": r[3],
			"type": r[4]
		} for r in cur.fetchall()
	]
	
	# محاسبه ROI (با قیمت فعلی تقریبی)
	current_btc_price = 50000  # این باید از API دریافت شود
	current_value_usd = current_btc_balance * current_btc_price
	roi_percentage = 0
	profit_loss_usd = 0
	if net_invested_usd > 0:
		roi_percentage = ((current_value_usd - net_invested_usd) / net_invested_usd) * 100
		profit_loss_usd = current_value_usd - net_invested_usd
	
	# تاریخ شروع سرمایه‌گذاری
	cur.execute("SELECT MIN(created_at) FROM purchases")
	row_first = cur.fetchone()
	inception_days = 0
	try:
		first_str = row_first[0] if row_first and row_first[0] else None
		if first_str:
			dt0 = datetime.fromisoformat(first_str)
			inception_days = max(0, (datetime.utcnow() - dt0).days)
	except Exception:
		inception_days = 0
	
	conn.close()
	
	return render_template("balance.html", 
		current_btc_balance=current_btc_balance,
		total_purchased_btc=total_purchased_btc,
		total_withdrawn_btc=total_withdrawn_btc,
		net_invested_usd=net_invested_usd,
		total_invested_usd=total_invested_usd,
		total_withdrawn_usd=total_withdrawn_usd,
		usd_to_toman=usd_to_toman,
		last_transaction_date=last_transaction_date,
		total_purchases_count=total_purchases_count,
		total_withdrawals_count=total_withdrawals_count,
		roi_percentage=roi_percentage,
		profit_loss_usd=profit_loss_usd,
		inception_days=inception_days,
		transactions=transactions)


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
