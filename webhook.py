from flask import Flask, request, abort, render_template, redirect, url_for, flash, jsonify  # pyright: ignore[reportMissingImports]
import subprocess
import hmac
import hashlib
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET_KEY", "dev-secret-key")

# ============================================================================
# Simple SQLite storage for a personal BTC purchase panel
# ============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "pplus.sqlite3")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            amount_btc REAL NOT NULL,
            price_usd_per_btc REAL NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    # Default USD→Toman rate if not set
    cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO settings(key, value) VALUES('usd_to_toman', ?)",
            ("60000",),
        )
    conn.commit()
    conn.close()

ensure_db()

# توکن امنیتی ساده
SECRET = b"my-secret-token"

# مسیر پروژه روی هاست
PROJECT_DIR = "/home/bztypmws/myapp"

def verify_signature(data, signature):
    mac = hmac.new(SECRET, data, hashlib.sha256)
    return hmac.compare_digest("sha256=" + mac.hexdigest(), signature)

@app.route("/update", methods=["POST"])
def update():
    # بررسی header GitHub
    signature = request.headers.get("X-Hub-Signature-256")
    if signature is None or not verify_signature(request.data, signature):
        abort(403)

    # اجرای دستورات pull
    try:
        subprocess.run(["git", "fetch", "origin"], cwd=PROJECT_DIR, check=True)
        subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=PROJECT_DIR, check=True)
        subprocess.run(["git", "clean", "-fd"], cwd=PROJECT_DIR, check=True)
        return "✅ پروژه با موفقیت آپدیت شد.", 200
    except subprocess.CalledProcessError as e:
        return f"❌ خطا هنگام آپدیت: {e}", 500

# ============================================================================
# Panel routes
# ============================================================================
@app.get("/panel")
def panel_index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, created_at, amount_btc, price_usd_per_btc FROM purchases ORDER BY id DESC")
    purchases = cur.fetchall()

    cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM purchases")
    total_usd = cur.fetchone()[0] or 0

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
    )

@app.post("/panel/add")
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
    cur.execute(
        "INSERT INTO purchases(created_at, amount_btc, price_usd_per_btc) VALUES(?,?,?)",
        (datetime.utcnow().isoformat(timespec="seconds"), amount_btc, price_usd_per_btc),
    )
    conn.commit()
    conn.close()
    flash("خرید با موفقیت ثبت شد.", "success")
    return redirect(url_for("panel_index"))

@app.post("/panel/rate")
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
    cur.execute(
        "INSERT INTO settings(key, value) VALUES('usd_to_toman', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (str(new_rate),),
    )
    conn.commit()
    conn.close()
    flash("نرخ با موفقیت به‌روزرسانی شد.", "success")
    return redirect(url_for("panel_index"))

# صفحه اصلی → انتقال به پنل
@app.get("/")
def home():
    return redirect(url_for("panel_index"))

# سلامت ساده
@app.get("/healthz")
def healthz():
    return "ok", 200

# ============================================================================
# JSON API routes
# ============================================================================
def _get_usd_to_toman(conn):
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
    row = cur.fetchone()
    return float(row[0]) if row else 0.0

@app.get("/api/purchases")
def api_list_purchases():
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

@app.post("/api/purchases")
def api_create_purchase():
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

@app.delete("/api/purchases/<int:purchase_id>")
def api_delete_purchase(purchase_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM purchases WHERE id = ?", (purchase_id,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    if deleted == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})

@app.get("/api/totals")
def api_totals():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(amount_btc * price_usd_per_btc), 0) FROM purchases")
    total_usd = float(cur.fetchone()[0] or 0)
    usd_to_toman = _get_usd_to_toman(conn)
    total_toman = total_usd * usd_to_toman
    conn.close()
    return jsonify({
        "total_usd": total_usd,
        "usd_to_toman": usd_to_toman,
        "total_toman": total_toman,
    })

@app.get("/api/rate")
def api_get_rate():
    conn = get_db_connection()
    rate = _get_usd_to_toman(conn)
    conn.close()
    return jsonify({"usd_to_toman": rate})

@app.put("/api/rate")
def api_set_rate():
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
