from flask import Blueprint, render_template, redirect, url_for, request, session, flash, current_app  # type: ignore


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
    expected_user = current_app.config.get("LOGIN_USERNAME")
    expected_pass = current_app.config.get("LOGIN_PASSWORD")
    if username == expected_user and password == expected_pass:
        session["logged_in"] = True
        # Redirect to next or dashboard
        next_url = session.pop("next_url", None)
        try:
            if next_url:
                return redirect(next_url)
        except Exception:
            pass
        return redirect(url_for("panel_bp.panel_index"))
    flash("نام کاربری یا رمز عبور نادرست است.", "error")
    return redirect(url_for("auth_bp.login"))


@auth_bp.post("/logout")
def logout():
    session.clear()
    flash("با موفقیت خارج شدید.", "success")
    return redirect(url_for("auth_bp.login"))


