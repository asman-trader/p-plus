from flask import Flask, render_template, redirect, url_for, flash, request, jsonify  # pyright: ignore[reportMissingImports]
import os
import sqlite3
from datetime import datetime
from db import get_db_connection, ensure_db
from routes.panel import panel_bp
from routes.api import api_bp
from routes.webhook import webhook_bp

# ----------------------------------------------------------------------------
# App factory and config
# ----------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET_KEY", "dev-secret-key")

ensure_db()

# Register blueprints
app.register_blueprint(webhook_bp)
app.register_blueprint(api_bp)
app.register_blueprint(panel_bp)
# WSGI entrypoint for Passenger and Flask CLI
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


