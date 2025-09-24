import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Allow overriding DB location via env so webhook resets do not affect data
DB_PATH = os.environ.get("PPLUS_DB_PATH") or os.path.join(BASE_DIR, "pplus.sqlite3")


def get_db_connection() -> sqlite3.Connection:
    """Get a database connection with optimized settings."""
    # Ensure target directory exists when using external DB paths
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    except Exception:
        pass
    
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    
    # Optimize SQLite settings for better performance
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=10000")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=268435456")  # 256MB
    
    return conn


@contextmanager
def get_db_context():
    """Context manager for database connections with automatic cleanup."""
    conn = None
    try:
        conn = get_db_connection()
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


def ensure_db() -> None:
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS purchases (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			created_at TEXT NOT NULL,
			amount_btc REAL NOT NULL,
			price_usd_per_btc REAL NOT NULL,
			wallet_id INTEGER DEFAULT 1,
			notes TEXT,
			FOREIGN KEY (wallet_id) REFERENCES wallets (id)
		)
		"""
	)
	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS withdrawals (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			created_at TEXT NOT NULL,
			amount_btc REAL NOT NULL,
			price_usd_per_btc REAL NOT NULL,
			wallet_id INTEGER DEFAULT 1,
			notes TEXT,
			FOREIGN KEY (wallet_id) REFERENCES wallets (id)
		)
		"""
	)
	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS usd_deposits (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			created_at TEXT NOT NULL,
			amount_usd REAL NOT NULL,
			price_toman_per_usd REAL NOT NULL,
			amount_toman REAL NOT NULL
		)
		"""
	)
	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS wallets (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT NOT NULL,
			description TEXT,
			wallet_type TEXT NOT NULL,
			color TEXT DEFAULT '#3b82f6',
			is_active BOOLEAN DEFAULT 1,
			created_at TEXT NOT NULL
		)
		"""
	)
	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS portfolio_goals (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			wallet_id INTEGER,
			goal_name TEXT NOT NULL,
			goal_type TEXT NOT NULL,
			target_value REAL NOT NULL,
			current_value REAL DEFAULT 0,
			target_date TEXT,
			is_achieved BOOLEAN DEFAULT 0,
			created_at TEXT NOT NULL,
			FOREIGN KEY (wallet_id) REFERENCES wallets (id)
		)
		"""
	)
	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS risk_limits (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			wallet_id INTEGER,
			limit_type TEXT NOT NULL,
			limit_value REAL NOT NULL,
			alert_threshold REAL DEFAULT 0.8,
			is_active BOOLEAN DEFAULT 1,
			created_at TEXT NOT NULL,
			FOREIGN KEY (wallet_id) REFERENCES wallets (id)
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
	# USD to Toman rate is now automatically fetched from Wallex API
	# No need to store in database
	
	# اضافه کردن آدرس کیف پول‌ها
	cur.execute("SELECT value FROM settings WHERE key='btc_wallet_address'")
	row = cur.fetchone()
	if row is None:
		cur.execute(
			"INSERT INTO settings(key, value) VALUES('btc_wallet_address', ?)",
			("",),
		)
	
	cur.execute("SELECT value FROM settings WHERE key='usdt_wallet_address'")
	row = cur.fetchone()
	if row is None:
		cur.execute(
			"INSERT INTO settings(key, value) VALUES('usdt_wallet_address', ?)",
			("",),
		)
	
	# ایجاد کیف پول پیش‌فرض
	cur.execute("SELECT COUNT(*) FROM wallets")
	wallet_count = cur.fetchone()[0]
	if wallet_count == 0:
		cur.execute(
			"INSERT INTO wallets(name, description, wallet_type, color, created_at) VALUES(?, ?, ?, ?, ?)",
			("کیف پول اصلی", "کیف پول اصلی برای معاملات", "main", "#3b82f6", datetime.utcnow().isoformat(timespec="seconds"))
		)
	
	conn.commit()
	conn.close()


