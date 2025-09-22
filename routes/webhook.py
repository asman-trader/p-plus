# -*- coding: utf-8 -*-
"""
وبهوک GitHub برای آپدیت خودکار پروژه روی سرور
- بررسی امضای GitHub (X-Hub-Signature-256)
- pull آخرین تغییرات از برنچ مشخص‌شده
- ریستارت پروژه با touch یا دستور سفارشی
"""

from flask import Blueprint, request, abort
import subprocess
import hmac
import hashlib
import os

# --------------------------
# Blueprint وبهوک GitHub
# --------------------------
webhook_bp = Blueprint("webhook_bp", __name__)

# --- سکرت از ENV خوانده می‌شود؛ اگر نبود، لاگ هشدار می‌دهیم اما برنامه را متوقف نمی‌کنیم ---
SECRET_ENV = os.environ.get("WEBHOOK_SECRET")
if not SECRET_ENV:
    print("[webhook] ⚠️ WEBHOOK_SECRET تنظیم نشده است؛ درخواست‌های وبهوک رد خواهند شد (403)")
SECRET = (SECRET_ENV or "").encode()

# مسیر پروژه و برنچ
PROJECT_DIR = os.environ.get("PROJECT_DIR", "/home/bztypmws/myapp")
TARGET_BRANCH = os.environ.get("WEBHOOK_BRANCH", "main")

# فایل ریستارت (برای uWSGI/Gunicorn)
RESTART_FILE = os.path.join(PROJECT_DIR, "tmp", "restart.txt")

# دستور ریستارت دلخواه (اختیاری: مثلاً systemctl restart myapp)
RESTART_CMD = os.environ.get("RESTART_CMD")


# --------------------------
# بررسی صحت امضای GitHub
# --------------------------
def verify_signature(data: bytes, signature: str | None) -> bool:
    """تطبیق امضای ارسال‌شده توسط GitHub با محاسبه محلی"""
    if not signature or not SECRET:
        return False
    mac = hmac.new(SECRET, data, hashlib.sha256)
    return hmac.compare_digest("sha256=" + mac.hexdigest(), signature)


# --------------------------
# Pull و ریستارت پروژه
# --------------------------
def perform_update():
    """اجرای git fetch/reset و سپس ریستارت پروژه"""
    try:
        subprocess.run(["git", "fetch", "origin"], cwd=PROJECT_DIR, check=True)
        subprocess.run(
            ["git", "reset", "--hard", f"origin/{TARGET_BRANCH}"],
            cwd=PROJECT_DIR,
            check=True,
        )

        if os.environ.get("WEBHOOK_ALLOW_FULL_CLEAN") == "1":
            subprocess.run(["git", "clean", "-fd"], cwd=PROJECT_DIR, check=True)

        # اجرای دستور ریستارت در صورت وجود
        if RESTART_CMD:
            subprocess.run(RESTART_CMD.split(), check=True)
        else:
            os.makedirs(os.path.dirname(RESTART_FILE), exist_ok=True)
            with open(RESTART_FILE, "w") as f:
                f.write("restart")

        return "✅ پروژه با موفقیت آپدیت و ریستارت شد.", 200

    except subprocess.CalledProcessError as e:
        return f"❌ خطا هنگام آپدیت پروژه: {e}", 500
    except Exception as e:
        return f"❌ خطای غیرمنتظره: {e}", 500


# --------------------------
# مسیر وبهوک: POST
# --------------------------
@webhook_bp.route("/webhook", methods=["POST"])
@webhook_bp.route("/update", methods=["POST"])
def webhook_update():
    """مسیر اصلی برای دریافت درخواست از GitHub"""
    ua = request.headers.get("User-Agent")
    evt = request.headers.get("X-GitHub-Event")
    delivery = request.headers.get("X-GitHub-Delivery")
    sig = request.headers.get("X-Hub-Signature-256")

    print(f"[webhook] UA={ua} event={evt} delivery={delivery}")
    print(f"[webhook] PROJECT_DIR={PROJECT_DIR} branch={TARGET_BRANCH}")
    print(f"[webhook] signature={sig}")
    print(f"[webhook] payload_length={len(request.data or b'')}")

    if not verify_signature(request.data, sig):
        expected = "sha256=" + hmac.new(SECRET, request.data, hashlib.sha256).hexdigest()
        print("[webhook] ❌ invalid signature! expected prefix:", expected[:12])
        abort(403)

    return perform_update()


# --------------------------
# Health check
# --------------------------
@webhook_bp.get("/webhook")
def webhook_health():
    """چک وضعیت سرور"""
    return "ok", 200
