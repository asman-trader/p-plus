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
	
	# محاسبه آمار کلی BTC
	cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM purchases")
	total_purchased_usd = float(cur.fetchone()[0] or 0)
	cur.execute("SELECT COALESCE(SUM(amount_btc), 0) FROM purchases")
	total_purchased_btc = float(cur.fetchone()[0] or 0)
	
	cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM withdrawals")
	total_withdrawn_usd = float(cur.fetchone()[0] or 0)
	cur.execute("SELECT COALESCE(SUM(amount_btc), 0) FROM withdrawals")
	total_withdrawn_btc = float(cur.fetchone()[0] or 0)
	
	# محاسبه آمار واریزهای دلاری
	cur.execute("SELECT COALESCE(SUM(amount_usd), 0) FROM usd_deposits")
	total_usd_deposits = float(cur.fetchone()[0] or 0)
	
	cur.execute("SELECT COALESCE(SUM(amount_toman), 0) FROM usd_deposits")
	total_usd_toman = float(cur.fetchone()[0] or 0)
	
	# محاسبه موجودی فعلی
	current_btc_balance = total_purchased_btc - total_withdrawn_btc
	net_invested_usd = total_purchased_usd - total_withdrawn_usd + total_usd_deposits
	
	# نرخ تبدیل از تنظیمات
	cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
	row = cur.fetchone()
	usd_to_toman = float(row[0]) if row else 60000.0
	
	# محاسبه ROI دقیق با در نظر گیری معاملات بسته و باز
	roi_percentage = 0
	profit_loss_usd = 0
	
	# دریافت قیمت فعلی BTC از API
	current_btc_price = 50000  # Default
	try:
		response = requests.post('https://api.nobitex.ir/market/stats', json={"srcCurrency": "btc", "dstCurrency": "usdt"}, timeout=3)
		if response.status_code == 200:
			data = response.json()["stats"]["btc-usdt"]
			current_btc_price = float(data["latest"])
	except Exception:
		pass
	
	# محاسبه سود/زیان از معاملات بسته (FIFO)
	closed_trades_profit = 0
	purchases_list = []
	withdrawals_list = []
	
	# دریافت تمام خریدها و برداشت‌ها
	cur.execute("SELECT id, created_at, amount_btc, price_usd_per_btc FROM purchases ORDER BY created_at ASC")
	purchases_list = cur.fetchall()
	cur.execute("SELECT id, created_at, amount_btc, price_usd_per_btc FROM withdrawals ORDER BY created_at ASC")
	withdrawals_list = cur.fetchall()
	
	# محاسبه معاملات بسته با FIFO
	purchase_queue = [(p[0], p[1], float(p[2]), float(p[3])) for p in purchases_list]
	withdrawal_queue = [(w[0], w[1], float(w[2]), float(w[3])) for w in withdrawals_list]
	
	for withdrawal in withdrawal_queue:
		remaining_withdrawal = withdrawal[2]
		withdrawal_price = withdrawal[3]
		
		while remaining_withdrawal > 1e-12 and purchase_queue:
			purchase = purchase_queue[0]
			purchase_amount = purchase[2]
			purchase_price = purchase[3]
			
			# مقدار معامله شده
			trade_amount = min(remaining_withdrawal, purchase_amount)
			
			# محاسبه سود/زیان این معامله
			buy_cost = trade_amount * purchase_price
			sell_value = trade_amount * withdrawal_price
			trade_profit = sell_value - buy_cost
			closed_trades_profit += trade_profit
			
			# کاهش از صف‌ها
			remaining_withdrawal -= trade_amount
			purchase_queue[0] = (purchase[0], purchase[1], purchase[2] - trade_amount, purchase[3])
			
			# اگر خرید تمام شد، از صف حذف کن
			if purchase_queue[0][2] <= 1e-12:
				purchase_queue.pop(0)
	
	# محاسبه ارزش معاملات باز (موجودی فعلی)
	open_trades_value = 0
	open_trades_cost = 0
	for purchase in purchase_queue:
		open_trades_cost += purchase[2] * purchase[3]
		open_trades_value += purchase[2] * current_btc_price
	
	open_trades_profit = open_trades_value - open_trades_cost
	
	# محاسبه کل سود/زیان
	total_profit_loss = closed_trades_profit + open_trades_profit
	
	# محاسبه ROI
	if net_invested_usd > 0:
		roi_percentage = (total_profit_loss / net_invested_usd) * 100
		profit_loss_usd = total_profit_loss
	
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
		total_usd_deposits=total_usd_deposits,
		total_usd_toman=total_usd_toman,
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
		wallet_id = int(request.form.get("wallet_id", 1))
		notes = request.form.get("notes", "").strip()
		
		if not (amount_btc == amount_btc and price_usd_per_btc == price_usd_per_btc):  # NaN check
			flash("مقادیر وارد شده نامعتبر است.", "error")
			return redirect(url_for("panel_bp.deposits_page"))

		if amount_btc <= 0 or price_usd_per_btc <= 0:
			flash("مقادیر باید بزرگ‌تر از صفر باشند.", "error")
			return redirect(url_for("panel_bp.deposits_page"))

		conn = get_db_connection()
		cur = conn.cursor()
		cur.execute("INSERT INTO purchases(created_at, amount_btc, price_usd_per_btc, wallet_id, notes) VALUES(?,?,?,?,?)", 
			(datetime.utcnow().isoformat(timespec="seconds"), amount_btc, price_usd_per_btc, wallet_id, notes))
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
		wallet_id = int(request.form.get("wallet_id", 1))
		notes = request.form.get("notes", "").strip()
		
		if not (amount_btc == amount_btc and price_usd_per_btc == price_usd_per_btc):
			flash("مقادیر وارد شده نامعتبر است.", "error")
			return redirect(url_for("panel_bp.withdrawals_page"))

		if amount_btc <= 0 or price_usd_per_btc <= 0:
			flash("مقادیر باید بزرگ‌تر از صفر باشند.", "error")
			return redirect(url_for("panel_bp.withdrawals_page"))

		conn = get_db_connection()
		cur = conn.cursor()
		cur.execute("INSERT INTO withdrawals(created_at, amount_btc, price_usd_per_btc, wallet_id, notes) VALUES(?,?,?,?,?)", 
			(datetime.utcnow().isoformat(timespec="seconds"), amount_btc, price_usd_per_btc, wallet_id, notes))
		conn.commit()
		conn.close()
		flash("برداشت با موفقیت ثبت شد.", "success")
		return redirect(url_for("panel_bp.withdrawals_page"))
	except Exception as e:
		print("[panel_withdraw] error:", e)
		flash("خطای داخلی هنگام ثبت برداشت.", "error")
		return redirect(url_for("panel_bp.withdrawals_page"))


@panel_bp.post("/panel/usd_deposit")
def panel_usd_deposit():
	try:
		amount_usd = _to_float(request.form.get("amount_usd", "0"))
		price_toman_per_usd = _to_float(request.form.get("price_toman_per_usd", "0"))
		if not (amount_usd == amount_usd and price_toman_per_usd == price_toman_per_usd):
			flash("مقادیر وارد شده نامعتبر است.", "error")
			return redirect(url_for("panel_bp.deposits_page"))

		if amount_usd <= 0 or price_toman_per_usd <= 0:
			flash("مقادیر باید بزرگ‌تر از صفر باشند.", "error")
			return redirect(url_for("panel_bp.deposits_page"))

		# محاسبه مقدار تومان
		amount_toman = amount_usd * price_toman_per_usd

		conn = get_db_connection()
		cur = conn.cursor()
		cur.execute("INSERT INTO usd_deposits(created_at, amount_usd, price_toman_per_usd, amount_toman) VALUES(?,?,?,?)", 
			(datetime.utcnow().isoformat(timespec="seconds"), amount_usd, price_toman_per_usd, amount_toman))
		conn.commit()
		conn.close()
		flash(f"واریز دلاری {amount_usd:,.0f} دلار ({amount_toman:,.0f} تومان) با موفقیت ثبت شد.", "success")
		return redirect(url_for("panel_bp.deposits_page"))
	except Exception as e:
		print("[panel_usd_deposit] error:", e)
		flash("خطای داخلی هنگام ثبت واریز دلاری.", "error")
		return redirect(url_for("panel_bp.deposits_page"))


@panel_bp.post("/panel/create_wallet")
def panel_create_wallet():
	try:
		name = request.form.get("name", "").strip()
		description = request.form.get("description", "").strip()
		wallet_type = request.form.get("wallet_type", "main")
		color = request.form.get("color", "#3b82f6")
		
		if not name:
			flash("نام کیف پول الزامی است.", "error")
			return redirect(url_for("panel_bp.portfolio_page"))
		
		conn = get_db_connection()
		cur = conn.cursor()
		cur.execute(
			"INSERT INTO wallets(name, description, wallet_type, color, created_at) VALUES(?, ?, ?, ?, ?)",
			(name, description, wallet_type, color, datetime.utcnow().isoformat(timespec="seconds"))
		)
		conn.commit()
		conn.close()
		flash(f"کیف پول '{name}' با موفقیت ایجاد شد.", "success")
		return redirect(url_for("panel_bp.portfolio_page"))
	except Exception as e:
		print("[panel_create_wallet] error:", e)
		flash("خطای داخلی هنگام ایجاد کیف پول.", "error")
		return redirect(url_for("panel_bp.portfolio_page"))


@panel_bp.post("/panel/create_goal")
def panel_create_goal():
	try:
		wallet_id = int(request.form.get("wallet_id", 0))
		goal_name = request.form.get("goal_name", "").strip()
		goal_type = request.form.get("goal_type", "value")
		target_value = _to_float(request.form.get("target_value", "0"))
		target_date = request.form.get("target_date", "")
		
		if not goal_name or target_value <= 0:
			flash("نام هدف و مقدار هدف الزامی است.", "error")
			return redirect(url_for("panel_bp.portfolio_page"))
		
		conn = get_db_connection()
		cur = conn.cursor()
		cur.execute(
			"INSERT INTO portfolio_goals(wallet_id, goal_name, goal_type, target_value, target_date, created_at) VALUES(?, ?, ?, ?, ?, ?)",
			(wallet_id, goal_name, goal_type, target_value, target_date, datetime.utcnow().isoformat(timespec="seconds"))
		)
		conn.commit()
		conn.close()
		flash(f"هدف '{goal_name}' با موفقیت ایجاد شد.", "success")
		return redirect(url_for("panel_bp.portfolio_page"))
	except Exception as e:
		print("[panel_create_goal] error:", e)
		flash("خطای داخلی هنگام ایجاد هدف.", "error")
		return redirect(url_for("panel_bp.portfolio_page"))


@panel_bp.post("/panel/create_risk_limit")
def panel_create_risk_limit():
	try:
		wallet_id = int(request.form.get("wallet_id", 0))
		limit_type = request.form.get("limit_type", "max_loss")
		limit_value = _to_float(request.form.get("limit_value", "0"))
		alert_threshold = _to_float(request.form.get("alert_threshold", "0.8"))
		
		if limit_value <= 0:
			flash("مقدار محدودیت باید بزرگ‌تر از صفر باشد.", "error")
			return redirect(url_for("panel_bp.portfolio_page"))
		
		conn = get_db_connection()
		cur = conn.cursor()
		cur.execute(
			"INSERT INTO risk_limits(wallet_id, limit_type, limit_value, alert_threshold, created_at) VALUES(?, ?, ?, ?, ?)",
			(wallet_id, limit_type, limit_value, alert_threshold, datetime.utcnow().isoformat(timespec="seconds"))
		)
		conn.commit()
		conn.close()
		flash("محدودیت ریسک با موفقیت ایجاد شد.", "success")
		return redirect(url_for("panel_bp.portfolio_page"))
	except Exception as e:
		print("[panel_create_risk_limit] error:", e)
		flash("خطای داخلی هنگام ایجاد محدودیت ریسک.", "error")
		return redirect(url_for("panel_bp.portfolio_page"))


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


@panel_bp.get("/portfolio")
def portfolio_page():
	try:
		conn = get_db_connection()
		cur = conn.cursor()
		
		# دریافت کیف پول‌ها
		cur.execute("SELECT id, name, description, wallet_type, color, is_active FROM wallets ORDER BY id")
		wallets_rows = cur.fetchall()
		wallets = [
			{
				"id": r["id"],
				"name": r["name"],
				"description": r["description"],
				"wallet_type": r["wallet_type"],
				"color": r["color"],
				"is_active": bool(r["is_active"])
			}
			for r in wallets_rows
		]
	
		# محاسبه موجودی هر کیف پول
		wallet_balances = {}
		for wallet in wallets:
			wallet_id = wallet["id"]
			
			# محاسبه موجودی BTC
			cur.execute("SELECT COALESCE(SUM(amount_btc), 0) FROM purchases WHERE wallet_id = ?", (wallet_id,))
			total_btc = float(cur.fetchone()[0] or 0)
			cur.execute("SELECT COALESCE(SUM(amount_btc), 0) FROM withdrawals WHERE wallet_id = ?", (wallet_id,))
			withdrawn_btc = float(cur.fetchone()[0] or 0)
			current_btc = total_btc - withdrawn_btc
			
			# محاسبه ارزش USD
			cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM purchases WHERE wallet_id = ?", (wallet_id,))
			total_invested_usd = float(cur.fetchone()[0] or 0)
			cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM withdrawals WHERE wallet_id = ?", (wallet_id,))
			total_withdrawn_usd = float(cur.fetchone()[0] or 0)
			net_invested_usd = total_invested_usd - total_withdrawn_usd
			
			wallet_balances[wallet_id] = {
				"btc_balance": current_btc,
				"invested_usd": net_invested_usd,
				"total_purchased_usd": total_invested_usd,
				"total_withdrawn_usd": total_withdrawn_usd
			}
	
		# دریافت اهداف پورتفولیو
		cur.execute("""
			SELECT pg.id, pg.wallet_id, pg.goal_name, pg.goal_type, pg.target_value, 
			       pg.current_value, pg.target_date, pg.is_achieved, w.name as wallet_name
			FROM portfolio_goals pg
			LEFT JOIN wallets w ON pg.wallet_id = w.id
			ORDER BY pg.created_at DESC
		""")
		goals_rows = cur.fetchall()
		goals = [
			{
				"id": r["id"],
				"wallet_id": r["wallet_id"],
				"goal_name": r["goal_name"],
				"goal_type": r["goal_type"],
				"target_value": float(r["target_value"]),
				"current_value": float(r["current_value"]),
				"target_date": r["target_date"],
				"is_achieved": bool(r["is_achieved"]),
				"wallet_name": r["wallet_name"]
			}
			for r in goals_rows
		]
		
		# دریافت محدودیت‌های ریسک
		cur.execute("""
			SELECT rl.id, rl.wallet_id, rl.limit_type, rl.limit_value, 
			       rl.alert_threshold, rl.is_active, w.name as wallet_name
			FROM risk_limits rl
			LEFT JOIN wallets w ON rl.wallet_id = w.id
			WHERE rl.is_active = 1
			ORDER BY rl.created_at DESC
		""")
		limits_rows = cur.fetchall()
		risk_limits = [
			{
				"id": r["id"],
				"wallet_id": r["wallet_id"],
				"limit_type": r["limit_type"],
				"limit_value": float(r["limit_value"]),
				"alert_threshold": float(r["alert_threshold"]),
				"is_active": bool(r["is_active"]),
				"wallet_name": r["wallet_name"]
			}
			for r in limits_rows
		]
		
		# نرخ تبدیل
		cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
		row = cur.fetchone()
		usd_to_toman = float(row[0]) if row else 60000.0
		
		conn.close()
		return render_template("portfolio.html", 
			wallets=wallets, 
			wallet_balances=wallet_balances,
			goals=goals,
			risk_limits=risk_limits,
			usd_to_toman=usd_to_toman)
	except Exception as e:
		print(f"[portfolio_page] error: {e}")
		flash("خطا در بارگذاری صفحه پورتفولیو", "error")
		return redirect(url_for("panel_bp.panel_index"))



@panel_bp.get("/deposits")
def deposits_page():
	conn = get_db_connection()
	cur = conn.cursor()
	
	# محاسبه واریزهای BTC
	cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM purchases")
	total_btc_usd = cur.fetchone()[0] or 0
	
	# محاسبه واریزهای دلاری
	cur.execute("SELECT COALESCE(SUM(amount_usd), 0) FROM usd_deposits")
	total_usd_deposits = cur.fetchone()[0] or 0
	
	cur.execute("SELECT COALESCE(SUM(amount_toman), 0) FROM usd_deposits")
	total_usd_toman = cur.fetchone()[0] or 0
	
	# کل واریزها
	total_usd = total_btc_usd + total_usd_deposits
	
	# نرخ تبدیل
	cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
	usd_to_toman = float(cur.fetchone()[0])
	total_toman = total_usd * usd_to_toman + total_usd_toman
	
	# لیست واریزهای دلاری
	cur.execute("SELECT id, created_at, amount_usd, price_toman_per_usd, amount_toman FROM usd_deposits ORDER BY id DESC")
	usd_deposits_rows = cur.fetchall()
	usd_deposits = [
		{
			"id": r["id"],
			"created_at": r["created_at"],
			"amount_usd": float(r["amount_usd"]),
			"price_toman_per_usd": float(r["price_toman_per_usd"]),
			"amount_toman": float(r["amount_toman"]),
		}
		for r in usd_deposits_rows
	]
	
	conn.close()
	return render_template("deposits.html", 
		total_usd=total_usd, 
		total_btc_usd=total_btc_usd,
		total_usd_deposits=total_usd_deposits,
		total_usd_toman=total_usd_toman,
		usd_to_toman=usd_to_toman, 
		total_toman=total_toman,
		usd_deposits=usd_deposits)


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
	
	# نرخ تبدیل از تنظیمات
	cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
	row = cur.fetchone()
	usd_to_toman = float(row[0]) if row else 60000.0
	
	# تاریخ آخرین تراکنش
	cur.execute("SELECT MAX(created_at) FROM (SELECT created_at FROM purchases UNION ALL SELECT created_at FROM withdrawals)")
	last_transaction_date = cur.fetchone()[0]
	
	# تعداد تراکنش‌ها
	cur.execute("SELECT COUNT(*) FROM purchases")
	total_purchases_count = cur.fetchone()[0]
	cur.execute("SELECT COUNT(*) FROM withdrawals")
	total_withdrawals_count = cur.fetchone()[0]
	
	# Fetch purchases and withdrawals for trades calculation
	cur.execute("SELECT id, created_at, amount_btc, price_usd_per_btc FROM purchases ORDER BY id DESC")
	purchases_rows = cur.fetchall()
	cur.execute("SELECT id, created_at, amount_btc, price_usd_per_btc FROM withdrawals ORDER BY id ASC")
	withdrawals_rows = cur.fetchall()
	
	# Convert to dicts for JSON serialization
	purchases = [
		{
			"id": int(r["id"]),
			"created_at": r["created_at"],
			"amount_btc": float(r["amount_btc"]),
			"price_usd_per_btc": float(r["price_usd_per_btc"]),
		}
		for r in purchases_rows
	]
	withdrawals = [
		{
			"id": int(r["id"]),
			"created_at": r["created_at"],
			"amount_btc": float(r["amount_btc"]),
			"price_usd_per_btc": float(r["price_usd_per_btc"]),
		}
		for r in withdrawals_rows
	]
	
	# Fetch all transactions for transaction list
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
	
	# محاسبه ROI دقیق با در نظر گیری معاملات بسته و باز
	roi_percentage = 0
	profit_loss_usd = 0
	
	# دریافت قیمت فعلی BTC از API
	current_btc_price = 50000  # Default
	try:
		response = requests.post('https://api.nobitex.ir/market/stats', json={"srcCurrency": "btc", "dstCurrency": "usdt"}, timeout=3)
		if response.status_code == 200:
			data = response.json()["stats"]["btc-usdt"]
			current_btc_price = float(data["latest"])
	except Exception:
		pass
	
	# محاسبه سود/زیان از معاملات بسته (FIFO)
	closed_trades_profit = 0
	purchases_list = []
	withdrawals_list = []
	
	# دریافت تمام خریدها و برداشت‌ها
	cur.execute("SELECT id, created_at, amount_btc, price_usd_per_btc FROM purchases ORDER BY created_at ASC")
	purchases_list = cur.fetchall()
	cur.execute("SELECT id, created_at, amount_btc, price_usd_per_btc FROM withdrawals ORDER BY created_at ASC")
	withdrawals_list = cur.fetchall()
	
	# محاسبه معاملات بسته با FIFO
	purchase_queue = [(p[0], p[1], float(p[2]), float(p[3])) for p in purchases_list]
	withdrawal_queue = [(w[0], w[1], float(w[2]), float(w[3])) for w in withdrawals_list]
	
	for withdrawal in withdrawal_queue:
		remaining_withdrawal = withdrawal[2]
		withdrawal_price = withdrawal[3]
		
		while remaining_withdrawal > 1e-12 and purchase_queue:
			purchase = purchase_queue[0]
			purchase_amount = purchase[2]
			purchase_price = purchase[3]
			
			# مقدار معامله شده
			trade_amount = min(remaining_withdrawal, purchase_amount)
			
			# محاسبه سود/زیان این معامله
			buy_cost = trade_amount * purchase_price
			sell_value = trade_amount * withdrawal_price
			trade_profit = sell_value - buy_cost
			closed_trades_profit += trade_profit
			
			# کاهش از صف‌ها
			remaining_withdrawal -= trade_amount
			purchase_queue[0] = (purchase[0], purchase[1], purchase[2] - trade_amount, purchase[3])
			
			# اگر خرید تمام شد، از صف حذف کن
			if purchase_queue[0][2] <= 1e-12:
				purchase_queue.pop(0)
	
	# محاسبه ارزش معاملات باز (موجودی فعلی)
	open_trades_value = 0
	open_trades_cost = 0
	for purchase in purchase_queue:
		open_trades_cost += purchase[2] * purchase[3]
		open_trades_value += purchase[2] * current_btc_price
	
	open_trades_profit = open_trades_value - open_trades_cost
	
	# محاسبه کل سود/زیان
	total_profit_loss = closed_trades_profit + open_trades_profit
	
	# محاسبه ROI
	if net_invested_usd > 0:
		roi_percentage = (total_profit_loss / net_invested_usd) * 100
		profit_loss_usd = total_profit_loss
	
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
		transactions=transactions,
		purchases=purchases,
		withdrawals=withdrawals)
