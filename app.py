# -*- coding: utf-8 -*-
from flask import Flask

# --- ایمپورت بلوپرینت‌ها ---
from routes.main_routes import main_bp
from routes.prefs_routes import prefs_bp
from routes.coins_routes import coins_bp
from routes.analysis_routes import analysis_bp
from routes.signals_routes import signals_bp
from routes.settings_routes import settings_bp
from routes.portfolio_routes import portfolio_bp   # 🔹 لیست دارایی‌ها

# از وبهوک فعلاً صرف‌نظر می‌کنیم؛ هر وقت خواستی فعال می‌کنیم
# from webhook import webhook_bp


def create_app():
    """
    Flask application factory.
    """
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates"
    )

    # --- رجیستر کردن بلوپرینت‌ها ---
    app.register_blueprint(main_bp)        # /
    app.register_blueprint(prefs_bp)       # /prefs
    app.register_blueprint(coins_bp)       # /price, /prices
    app.register_blueprint(analysis_bp)    # /analysis/<symbol>
    app.register_blueprint(signals_bp)     # /signals/<symbol>
    app.register_blueprint(settings_bp)    # /settings
    app.register_blueprint(portfolio_bp)   # /portfolio
    # app.register_blueprint(webhook_bp)   # برای وبهوک GitHub (اختیاری)

    return app


# --- اجرای مستقیم (لوکال) ---
if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)
