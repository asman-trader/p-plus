# app.py
from flask import Flask
from routes.main_routes import main_bp
# ... سایر ایمپورت‌هایی که داری ...
from routes.prefs_routes import prefs_bp  # اگر اضافه کرده‌ای

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.register_blueprint(main_bp)
    # ... سایر بلواپرینت‌ها ...
    app.register_blueprint(prefs_bp)
    return app

# --- این بخش را اضافه کن ---
if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)  # یا 127.0.0.1
