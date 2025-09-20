# -*- coding: utf-8 -*-
from flask import Blueprint, request, abort  # pyright: ignore[reportMissingImports]
import subprocess
import hmac
import hashlib
import os

# --------------------------
# Blueprint وبهوک GitHub
# --------------------------
webhook_bp = Blueprint("webhook_bp", __name__)

# توکن امنیتی از ENV یا مقدار پیش‌فرض
SECRET = (os.environ.get("WEBHOOK_SECRET") or "my-secret-token").encode()

# مسیر پروژه روی هاست از ENV یا مقدار پیش‌فرض
PROJECT_DIR = os.environ.get("PROJECT_DIR", "/home/bztypmws/myapp")

# فایل برای ریستارت خودکار (مثلاً توسط touch tmp/restart.txt)
RESTART_FILE = os.path.join(PROJECT_DIR, "tmp", "restart.txt")


# --------------------------
# بررسی صحت امضای GitHub
# --------------------------
def verify_signature(data: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    mac = hmac.new(SECRET, data, hashlib.sha256)
    return hmac.compare_digest("sha256=" + mac.hexdigest(), signature)


# --------------------------
# مسیر اصلی وبهوک: Pull اتوماتیک
# --------------------------
def perform_update():
    try:
        subprocess.run(["git", "fetch", "origin"], cwd=PROJECT_DIR, check=True)
        subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=PROJECT_DIR, check=True)
        subprocess.run(["git", "clean", "-fd"], cwd=PROJECT_DIR, check=True)

        # ایجاد فایل restart برای سیستم‌های WSGI مانند Gunicorn یا uWSGI
        os.makedirs(os.path.dirname(RESTART_FILE), exist_ok=True)
        with open(RESTART_FILE, "w") as f:
            f.write("restart")

        return "✅ پروژه با موفقیت آپدیت و ریستارت شد.", 200
    except subprocess.CalledProcessError as e:
        return f"❌ خطا هنگام آپدیت پروژه: {e}", 500


@webhook_bp.route("/update", methods=["POST"])
def update():
    # Debug headers/body size
    ua = request.headers.get("User-Agent")
    evt = request.headers.get("X-GitHub-Event")
    delivery = request.headers.get("X-GitHub-Delivery")
    print("[webhook] UA=", ua)
    print("[webhook] event=", evt, "delivery=", delivery)
    print("[webhook] PROJECT_DIR=", PROJECT_DIR)
    print("[webhook] payload_length=", len(request.data or b""))

    signature = request.headers.get("X-Hub-Signature-256")
    print("[webhook] signature=", signature)
    if not verify_signature(request.data, signature):
        try:
            expected = "sha256=" + hmac.new(SECRET, request.data, hashlib.sha256).hexdigest()
            print("[webhook] expected_sig_prefix=", expected[:12])
        except Exception:
            pass
        abort(403)
    return perform_update()


# --------------------------
# Alias برای مسیر /webhook
# --------------------------
@webhook_bp.route("/webhook", methods=["POST"])
def webhook_alias():
    return update()


# --------------------------
# Health check برای GET /webhook
# --------------------------
@webhook_bp.get("/webhook")
def webhook_health():
    return "ok", 200
