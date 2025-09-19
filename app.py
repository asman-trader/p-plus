# -*- coding: utf-8 -*-
from flask import Flask, request
import logging
import os
from datetime import datetime

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


def setup_logging(app):
    """
    تنظیم سیستم لاگ‌گیری
    """
    # ایجاد پوشه لاگ‌ها
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # تنظیم فرمت لاگ
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # لاگ فایل اصلی
    log_file = os.path.join(log_dir, 'app.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # لاگ فایل خطاها
    error_log_file = os.path.join(log_dir, 'errors.log')
    error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format))
    
    # لاگ کنسول
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # تنظیم لاگر اصلی
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    app.logger.addHandler(console_handler)
    
    # لاگ شروع اپلیکیشن
    app.logger.info('Application started successfully')
    
    return app

def create_app():
    """
    Flask application factory.
    """
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates"
    )
    
    # تنظیم لاگ‌گیری
    app = setup_logging(app)

    # --- رجیستر کردن بلوپرینت‌ها ---
    try:
        app.register_blueprint(main_bp)        # /
        app.register_blueprint(prefs_bp)       # /prefs
        app.register_blueprint(coins_bp)       # /price, /prices
        app.register_blueprint(analysis_bp)    # /analysis/<symbol>
        app.register_blueprint(signals_bp)     # /signals/<symbol>
        app.register_blueprint(settings_bp)    # /settings
        app.register_blueprint(portfolio_bp)   # /portfolio
        # app.register_blueprint(webhook_bp)   # برای وبهوک GitHub (اختیاری)
        app.logger.info('All blueprints registered successfully')
    except Exception as e:
        app.logger.error(f'Error registering blueprints: {str(e)}')
        raise

    # --- هندلرهای خطا ---
    @app.errorhandler(404)
    def not_found(error):
        app.logger.warning(f'404 error: {request.url}')
        return {'error': 'Not found'}, 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'500 error: {str(error)}')
        return {'error': 'Internal server error'}, 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f'Unhandled exception: {str(e)}', exc_info=True)
        return {'error': 'Internal server error'}, 500

    return app


# --- اجرای مستقیم (لوکال) ---
if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)
