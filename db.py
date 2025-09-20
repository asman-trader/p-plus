import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "pplus.sqlite3")


def get_db_connection() -> sqlite3.Connection:
	conn = sqlite3.connect(DB_PATH)
	conn.row_factory = sqlite3.Row
	return conn


def ensure_db() -> None:
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
	cur.execute("SELECT value FROM settings WHERE key='usd_to_toman'")
	row = cur.fetchone()
	if row is None:
		cur.execute(
			"INSERT INTO settings(key, value) VALUES('usd_to_toman', ?)",
			("60000",),
		)
	conn.commit()
	conn.close()


