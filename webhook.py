# -*- coding: utf-8 -*-
"""
Webhook handler for GitHub → auto-deploy.
- Verifies HMAC SHA-256 signature (X-Hub-Signature-256)
- Filters repository and branch
- Triggers a deploy script asynchronously

Env vars:
  GITHUB_WEBHOOK_SECRET   (required)  e.g. "super-strong-secret"
  REPO_FULL_NAME          (optional)  default: "asman-trader/p_plus-dashboard"
  BRANCH                  (optional)  default: "main"
  DEPLOY_CMD              (optional)  default: "/var/www/app/deploy.sh"
  ENABLE_IP_CHECK         (optional)  default: "0"  (set "1" to enable)
"""
from __future__ import annotations
import os, hmac, hashlib, subprocess, ipaddress, json
from flask import Blueprint, request, abort, jsonify

webhook_bp = Blueprint("webhook", __name__)

# --- Config ---
SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
REPO_FULL_NAME = os.getenv("REPO_FULL_NAME", "asman-trader/p_plus-dashboard")
BRANCH = os.getenv("BRANCH", "main")
DEPLOY_CMD = os.getenv("DEPLOY_CMD", "/var/www/app/deploy.sh")
ENABLE_IP_CHECK = os.getenv("ENABLE_IP_CHECK", "0") == "1"

# GitHub hook IPs (optional hardening). Keep short list; prefer putting this behind a reverse proxy allowlist.
GITHUB_HOOK_CIDRS = [
    "192.30.252.0/22",
    "185.199.108.0/22",
    "140.82.112.0/20",
    "143.55.64.0/20",
]

def _json():
    # Silent parse: return {} if body isn't JSON
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}

def _verify_signature(secret: str, body: bytes, signature_hdr: str) -> bool:
    if not signature_hdr or not signature_hdr.startswith("sha256="):
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    received = signature_hdr.split("=", 1)[1].strip()
    # constant-time compare
    return hmac.compare_digest(digest, received)

def _client_ip_allowed() -> bool:
    if not ENABLE_IP_CHECK:
        return True
    try:
        peer = ipaddress.ip_address(request.remote_addr)
        for cidr in GITHUB_HOOK_CIDRS:
            if peer in ipaddress.ip_network(cidr):
                return True
        return False
    except Exception:
        return False

@webhook_bp.route("/webhook/github", methods=["POST"])
def github_webhook():
    # --- Basic guards ---
    if not SECRET:
        # Misconfiguration; better to return 500 than accept unsigned webhooks.
        return jsonify(error="server_not_configured: missing GITHUB_WEBHOOK_SECRET"), 500

    if not _client_ip_allowed():
        abort(403)

    # --- Signature check ---
    raw = request.get_data()  # exact bytes as GitHub signed
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not _verify_signature(SECRET, raw, sig):
        abort(401)

    event = request.headers.get("X-GitHub-Event", "")

    # Respond to GitHub's "ping" event quickly
    if event == "ping":
        return jsonify(ok=True, msg="pong")

    # We only act on pushes to the configured branch
    if event != "push":
        return jsonify(ignored=True, reason=f"event:{event}")

    payload = _json()
    repo_name = (payload.get("repository") or {}).get("full_name")
    if REPO_FULL_NAME and repo_name != REPO_FULL_NAME:
        return jsonify(ignored=True, reason=f"repo_mismatch:{repo_name}")

    ref = payload.get("ref", "")
    expected_ref = f"refs/heads/{BRANCH}"
    if ref != expected_ref:
        return jsonify(ignored=True, reason=f"ref:{ref} != {expected_ref}")

    # --- Queue deploy (async) ---
    try:
        # Prefer absolute path; no shell for safety
        proc = subprocess.Popen([DEPLOY_CMD], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return jsonify(queued=True, pid=proc.pid, branch=BRANCH, repo=repo_name)
    except FileNotFoundError:
        return jsonify(error="deploy_script_not_found", path=DEPLOY_CMD), 500
    except Exception as e:
        return jsonify(error="deploy_failed", detail=str(e)), 500
