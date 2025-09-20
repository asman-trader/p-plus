import sys
import os
import io
from typing import Optional

APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure CWD is project root (needed for templates/static/db paths)
try:
    os.chdir(APP_DIR)
except Exception:
    pass

# Add project root to sys.path
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Prefer virtualenv site-packages if available
def _add_virtualenv_site_packages(venv_path: Optional[str]) -> None:
    if not venv_path:
        return
    try:
        py_ver = f"python{sys.version_info[0]}.{sys.version_info[1]}"
        site_dir = os.path.join(venv_path, "lib", py_ver, "site-packages")
        if os.path.isdir(site_dir) and site_dir not in sys.path:
            sys.path.insert(0, site_dir)
    except Exception:
        pass

_add_virtualenv_site_packages(os.environ.get("VIRTUAL_ENV"))
_add_virtualenv_site_packages(os.path.join(APP_DIR, ".venv"))

# Load simple .env if present (no external deps)
def _load_env_file(env_path: str) -> None:
    try:
        if not os.path.isfile(env_path):
            return
        with io.open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                os.environ.setdefault(k, v)
    except Exception:
        # Ignore .env parsing issues silently to avoid breaking WSGI load
        pass

_load_env_file(os.path.join(APP_DIR, ".env"))

# Import the Flask app object (must expose `application` for Passenger)
from app import app as application

