import jwt as pyjwt
from functools import wraps
from flask import request, jsonify, current_app
from db import db

# ─────────────────────────────────────────────
# Standard JSON response helpers
# ─────────────────────────────────────────────

def api_error(message, status_code=400):
    """Return a standard error envelope."""
    return jsonify({"success": False, "data": None, "message": message}), status_code


def api_success(data, message="OK", status_code=200):
    """Return a standard success envelope."""
    return jsonify({"success": True, "data": data, "message": message}), status_code


# ─────────────────────────────────────────────
# JWT decorators
# ─────────────────────────────────────────────

def jwt_required(f):
    """
    Decorator that validates the Bearer JWT in the Authorization header.
    Injects `current_user` (a User model instance) into the wrapped function
    as a keyword argument.
    Returns 401 if the token is missing, malformed, or expired.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return api_error("Authentication required", 401)

        token = auth_header.split(" ", 1)[1]
        try:
            payload = pyjwt.decode(
                token,
                current_app.config["JWT_SECRET_KEY"],
                algorithms=["HS256"]
            )
        except pyjwt.ExpiredSignatureError:
            return api_error("Token has expired", 401)
        except pyjwt.InvalidTokenError:
            return api_error("Invalid token", 401)

        # Import here to avoid circular imports
        from models import User
        user = db.session.get(User, payload.get("user_id"))
        if user is None:
            return api_error("User not found", 401)

        kwargs["current_user"] = user
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """
    Decorator that enforces admin role.
    Wraps jwt_required — returns 403 if the authenticated user is not an admin.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return api_error("Authentication required", 401)

        token = auth_header.split(" ", 1)[1]
        try:
            payload = pyjwt.decode(
                token,
                current_app.config["JWT_SECRET_KEY"],
                algorithms=["HS256"]
            )
        except pyjwt.ExpiredSignatureError:
            return api_error("Token has expired", 401)
        except pyjwt.InvalidTokenError:
            return api_error("Invalid token", 401)

        from models import User
        user = db.session.get(User, payload.get("user_id"))
        if user is None:
            return api_error("User not found", 401)
        if user.role != "admin":
            return api_error("Admin access required", 403)

        kwargs["current_user"] = user
        return f(*args, **kwargs)

    return decorated
