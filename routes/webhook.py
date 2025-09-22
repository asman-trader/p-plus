# -*- coding: utf-8 -*-
from flask import Blueprint, request, abort
import subprocess
import hmac
import hashlib
import os

# --------------------------
# Blueprint وبهوک GitHub
# --------------------------
webhook_bp = Blueprint("webhook_bp", __name__)

# --- سکرت باید از ENV ست شده باشه ---
SECRET_ENV = os.environ.get("WEBHOOK_SECRET")
if not SECRET_ENV:
    raise RuntimeError("❌ متغیر محیطی WEBHOOK_SECRET تنظیم نشده است.")
SECRET = SECRET_ENV.encode()

# مسیر پروژه و برنچ
PROJECT_DIR = os.environ.get("PROJECT_DIR", "/home/bztypmws/myapp")
TARGET_BRANCH = os.environ.get("WEBHOOK_BRANCH", "main")

# فایل ریستارت (برای uWSGI/Gunicorn)
RESTART_FILE = os.path.join(PROJECT_DIR, "tmp", "restart.txt")

# دستور ریستارت دلخواه (اختیاری)
RESTART_CMD = os.environ.get("RESTART_CMD")


# --------------------------
# بررسی صحت امضای GitHub
# --------------------------
def verify_signature(data: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    mac = hmac.new(SECRET, data, hashlib.sha256)
    return hmac.compare_digest("sha256=" + mac.hexdigest(), signature)


# --------------------------
# Pull و ریستارت پروژه
# --------------------------
def perform_update():
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


# --------------------------
# مسیر وبهوک: POST
# --------------------------
@webhook_bp.route("/webhook", methods=["POST"])
@webhook_bp.route("/update", methods=["POST"])
def webhook_update():
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
        print("[webhook] invalid signature! expected prefix:", expected[:12])
        abort(403)

    return perform_update()


# --------------------------
# Health check
# --------------------------
@webhook_bp.get("/webhook")
def webhook_health():
    return "ok", 200
