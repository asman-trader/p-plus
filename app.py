# -*- coding: utf-8 -*-
from flask import Flask

# --- ایمپورت بلوپرینت‌ها ---
from routes.main_routes import main_bp
from routes.prefs_routes import prefs_bp
# اگر روت‌های دیگه داری، اینجا اضافه کن:
# from routes.analysis_routes import analysis_bp
# from routes.signals_routes import signals_bp
# from webhook import webhook_bp   # برای وبهوک GitHub

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
    app.register_blueprint(main_bp)
    app.register_blueprint(prefs_bp)
    # app.register_blueprint(analysis_bp)
    # app.register_blueprint(signals_bp)
    # app.register_blueprint(webhook_bp)

    return app


# --- اجرای مستقیم (لوکال) ---
if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)
