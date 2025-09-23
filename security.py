import os
from flask import request, abort
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

USE_REPLIT_AUTH = os.getenv("USE_REPLIT_AUTH", "false").lower() == "true"
CORS_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,https://*.repl.co"
).split(",") if o.strip()]

def get_replit_user(req):
    """Only returns a user dict when USE_REPLIT_AUTH==true AND request came via Replit."""
    if not USE_REPLIT_AUTH:
        return None
    host = req.headers.get("X-Forwarded-Host", "") or req.headers.get("Host", "")
    if not (host.endswith(".repl.co") or host.endswith(".replit.dev")):
        return None
    uid = req.headers.get("X-Replit-User-Id")
    name = req.headers.get("X-Replit-User-Name")
    if not uid or not name:
        return None
    return {"id": uid, "name": name}

def harden_app(app):
    # Secrets / cookies
    app.config.setdefault("SECRET_KEY", os.getenv("SECRET_KEY", "change-me"))
    app.config.setdefault("WTF_CSRF_TIME_LIMIT", None)

    # CSRF for forms/cookie-based routes
    CSRFProtect(app)

    # CORS – credentials require explicit origins, not "*"
    CORS(app,
         resources={r"/api/*": {"origins": CORS_ORIGINS}},
         supports_credentials=True)

    # Security headers (+ optional HTTPS enforcement via env)
    Talisman(
        app,
        force_https=(os.getenv("FORCE_HTTPS", "0") == "1"),
        content_security_policy={
            "default-src": ["'self'"],
            "img-src": ["'self'", "data:"],
            "style-src": ["'self'", "'unsafe-inline'"],
            "script-src": ["'self'"],
        },
        frame_options="DENY",
        referrer_policy="no-referrer",
        session_cookie_secure=True,
        session_cookie_samesite="Lax",
        session_cookie_http_only=True
    )

    # Basic rate limiting
    Limiter(get_remote_address, app=app, default_limits=["200/day", "60/hour"])

    if USE_REPLIT_AUTH:
        @app.before_request
        def _replit_header_gate():
            # Block state-changing requests if not from Replit with valid headers
            if request.method in ("POST", "PUT", "PATCH", "DELETE"):
                if not get_replit_user(request):
                    abort(401)
