from flask import Blueprint, render_template, redirect, url_for, request, session, flash, current_app, make_response  # type: ignore
from datetime import datetime, timedelta


auth_bp = Blueprint("auth_bp", __name__)


def _is_logged_in() -> bool:
    try:
        return bool(session.get("logged_in") is True)
    except Exception:
        return False


@auth_bp.before_app_request
def enforce_login():  # type: ignore[override]
    # Allow static, auth, and health routes without login
    if request.endpoint in ("auth_bp.login", "auth_bp.login_post", "auth_bp.logout", "panel_bp.healthz"):
        return None
    if request.endpoint and request.endpoint.startswith("static"):
        return None
    # Skip API/webhook to not break existing integrations
    if request.endpoint and (request.endpoint.startswith("api_bp.") or request.endpoint.startswith("webhook_bp.")):
        return None
    if not _is_logged_in():
        # Remember next
        next_url = request.full_path if request.query_string else request.path
        session["next_url"] = next_url
        return redirect(url_for("auth_bp.login"))
    return None


@auth_bp.get("/login")
def login():
    if _is_logged_in():
        return redirect(url_for("panel_bp.panel_index"))
    return render_template("login.html", hide_chrome=True)


@auth_bp.post("/login")
def login_post():
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()
    remember = request.form.get("remember") == "on"

    # Basic rate-limit per IP in session (volatile)
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    rl_key = f"rl_fail_{ip}"
    rl_data = session.get(rl_key)
    if isinstance(rl_data, dict):
        first_ts = rl_data.get("first_ts")
        fails = int(rl_data.get("fails", 0))
        if first_ts and (datetime.utcnow() - datetime.fromisoformat(first_ts)) < timedelta(minutes=10):
            if fails >= 5:
                flash("تلاش‌های زیاد؛ چند دقیقه بعد دوباره تلاش کنید.", "error")
                return redirect(url_for("auth_bp.login"))
        else:
            rl_data = None

    expected_user = current_app.config.get("LOGIN_USERNAME")
    expected_pass = current_app.config.get("LOGIN_PASSWORD")
    if username == expected_user and password == expected_pass:
        session["logged_in"] = True
        # reset rate-limit
        session.pop(rl_key, None)
        # set remember cookie if requested (1 month lifespan)
        resp = make_response(redirect(url_for("panel_bp.panel_index")))
        if remember:
            expires = datetime.utcnow() + timedelta(days=30)
            session.permanent = True
            current_app.permanent_session_lifetime = timedelta(days=30)
            resp.set_cookie("remember_me", "1", expires=expires, samesite="Lax", secure=False)
        return resp
        # Redirect to next if stored
        next_url = session.pop("next_url", None)
        if next_url:
            return redirect(next_url)
        return resp
    flash("نام کاربری یا رمز عبور نادرست است.", "error")
    # update rate-limit state
    now_iso = datetime.utcnow().isoformat()
    if not isinstance(rl_data, dict):
        session[rl_key] = {"first_ts": now_iso, "fails": 1}
    else:
        rl_data["fails"] = int(rl_data.get("fails", 0)) + 1
        session[rl_key] = rl_data
    return redirect(url_for("auth_bp.login"))


@auth_bp.post("/logout")
def logout():
    session.clear()
    flash("با موفقیت خارج شدید.", "success")
    return redirect(url_for("auth_bp.login"))


