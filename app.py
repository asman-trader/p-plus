# -*- coding: utf-8 -*-
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify  # pyright: ignore[reportMissingImports]
import os
from db import get_db_connection, ensure_db
from routes.panel import panel_bp
from routes.api import api_bp
from routes.webhook import webhook_bp
from flask_wtf.csrf import CSRFProtect, generate_csrf  # type: ignore

# ----------------------------------------------------------------------------
# App factory and configuration
# ----------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET_KEY", "dev-secret-key")

# اطمینان از وجود دیتابیس و جداول
ensure_db()

# ----------------------------------------------------------------------------
# Register Blueprints
# ----------------------------------------------------------------------------
app.register_blueprint(webhook_bp)
app.register_blueprint(api_bp)
app.register_blueprint(panel_bp)

# ----------------------------------------------------------------------------
# CSRF protection
# ----------------------------------------------------------------------------
csrf = CSRFProtect(app)
csrf.exempt(api_bp)
csrf.exempt(webhook_bp)

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)

# ----------------------------------------------------------------------------
# Security headers
# ----------------------------------------------------------------------------
@app.after_request
def set_security_headers(response):  # type: ignore[override]
    """Add basic security headers with CSP compatible with current inline assets."""
    csp = " ".join([
        "default-src 'self';",
        "img-src 'self' data: https:;",
        "style-src 'self' 'unsafe-inline' https:;",
        "script-src 'self' 'unsafe-inline' https:;",
        "connect-src 'self' https:;",
        "font-src 'self' https: data:;",
        "base-uri 'self';",
        "form-action 'self';",
        "frame-ancestors 'none'",
    ])
    response.headers.setdefault("Content-Security-Policy", csp)
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")

    # Enable HSTS only when served over HTTPS or behind a proxy terminating TLS
    if request.is_secure or request.headers.get("X-Forwarded-Proto", "").startswith("https"):
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

    return response

# ----------------------------------------------------------------------------
# WSGI entrypoint for Passenger / Gunicorn / Flask CLI
# ----------------------------------------------------------------------------
application = app

# ----------------------------------------------------------------------------
# Run standalone Flask server (development)
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
