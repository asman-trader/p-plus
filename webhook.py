from flask import Blueprint, request, abort  # pyright: ignore[reportMissingImports]
import subprocess
import hmac
import hashlib

webhook_bp = Blueprint("webhook_bp", __name__)

# توکن امنیتی ساده
SECRET = b"my-secret-token"

# مسیر پروژه روی هاست
PROJECT_DIR = "/home/bztypmws/myapp"


def verify_signature(data: bytes, signature: str | None) -> bool:
	if not signature:
		return False
	mac = hmac.new(SECRET, data, hashlib.sha256)
	return hmac.compare_digest("sha256=" + mac.hexdigest(), signature)


@webhook_bp.route("/update", methods=["POST"])
def update():
	# بررسی header GitHub
	signature = request.headers.get("X-Hub-Signature-256")
	if not verify_signature(request.data, signature):
		abort(403)

	# اجرای دستورات pull
	try:
		subprocess.run(["git", "fetch", "origin"], cwd=PROJECT_DIR, check=True)
		subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=PROJECT_DIR, check=True)
		subprocess.run(["git", "clean", "-fd"], cwd=PROJECT_DIR, check=True)
		return "✅ پروژه با موفقیت آپدیت شد.", 200
	except subprocess.CalledProcessError as e:
		return f"❌ خطا هنگام آپدیت: {e}", 500
