import bcrypt
import jwt as pyjwt
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, current_app
from db import db
from models import User
from utils import api_error, api_success

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    """POST /api/auth/register — create a new guest account."""
    data = request.get_json(silent=True) or {}

    # ── Validate required fields ───────────────────────────────────────────
    for field in ("full_name", "email", "password"):
        if not data.get(field):
            return api_error(f"Field '{field}' is required", 400)

    full_name = data["full_name"].strip()
    email     = data["email"].strip().lower()
    password  = data["password"]

    if len(full_name) == 0:
        return api_error("Field 'full_name' is required", 400)

    if len(password) < 8:
        return api_error("Password must be at least 8 characters", 400)

    # ── Check email uniqueness ─────────────────────────────────────────────
    if User.query.filter_by(email=email).first():
        return api_error("Email already registered", 409)

    # ── Hash password and persist ──────────────────────────────────────────
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    user = User(
        full_name=full_name,
        email=email,
        password_hash=hashed.decode("utf-8"),
        role="guest",
    )
    db.session.add(user)
    db.session.commit()

    return api_success(
        {"user_id": user.id, "email": user.email, "role": user.role},
        message="Account created successfully",
        status_code=201,
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    """POST /api/auth/login — authenticate and return a JWT."""
    data = request.get_json(silent=True) or {}

    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return api_error("Email and password are required", 400)

    user = User.query.filter_by(email=email).first()

    # Use constant-time comparison to prevent timing attacks
    if user is None or not bcrypt.checkpw(
        password.encode("utf-8"), user.password_hash.encode("utf-8")
    ):
        return api_error("Invalid email or password", 401)

    # ── Issue JWT ──────────────────────────────────────────────────────────
    payload = {
        "user_id":   user.id,
        "full_name": user.full_name,
        "role":      user.role,
        "exp":       datetime.now(timezone.utc) + timedelta(hours=24),
    }
    token = pyjwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm="HS256",
    )

    return api_success(
        {
            "token":     token,
            "user_id":   user.id,
            "full_name": user.full_name,
            "role":      user.role,
        },
        message="Login successful",
    )
