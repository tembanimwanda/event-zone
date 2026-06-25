from datetime import date as date_type
from flask import Blueprint, request
from db import db
from models import Room, Booking
from utils import api_error, api_success, admin_required

rooms_bp = Blueprint("rooms", __name__)


def _parse_date(value, field_name):
    """Parse an ISO date string; return (date, None) or (None, error_response)."""
    try:
        return date_type.fromisoformat(value), None
    except (ValueError, TypeError):
        return None, api_error(f"Invalid date format for '{field_name}'. Use YYYY-MM-DD.", 400)


def has_overlap(room_id, check_in, check_out):
    """Return True if the room has a pending/confirmed booking overlapping [check_in, check_out)."""
    return Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status.in_(["pending", "confirmed"]),
        Booking.check_in_date  < check_out,
        Booking.check_out_date > check_in,
    ).first() is not None


# ── GET /api/rooms ─────────────────────────────────────────────────────────

@rooms_bp.route("", methods=["GET"])
@rooms_bp.route("/", methods=["GET"])
def list_rooms():
    """Return all active rooms, optionally filtered by date availability."""
    check_in_str  = request.args.get("check_in")
    check_out_str = request.args.get("check_out")

    query = Room.query.filter_by(is_active=True)

    if check_in_str and check_out_str:
        check_in, err = _parse_date(check_in_str, "check_in")
        if err:
            return err
        check_out, err = _parse_date(check_out_str, "check_out")
        if err:
            return err

        if check_out <= check_in:
            return api_error("Check-out date must be after check-in date", 400)

        # Exclude rooms that have an overlapping booking
        rooms = [r for r in query.all() if not has_overlap(r.id, check_in, check_out)]
    else:
        rooms = query.all()

    return api_success([r.to_dict() for r in rooms])


# ── GET /api/rooms/<id> ────────────────────────────────────────────────────

@rooms_bp.route("/<int:room_id>", methods=["GET"])
def get_room(room_id):
    """Return a single active room by id."""
    room = Room.query.filter_by(id=room_id, is_active=True).first()
    if not room:
        return api_error("Room not found", 404)
    return api_success(room.to_dict())


# ── POST /api/rooms ────────────────────────────────────────────────────────

@rooms_bp.route("", methods=["POST"])
@rooms_bp.route("/", methods=["POST"])
@admin_required
def create_room(current_user):
    """Admin only: create a new room."""
    data = request.get_json(silent=True) or {}

    for field in ("name", "type", "price_per_night", "capacity"):
        if data.get(field) is None or str(data.get(field, "")).strip() == "":
            return api_error(f"Field '{field}' is required", 400)

    try:
        price    = float(data["price_per_night"])
        capacity = int(data["capacity"])
    except (ValueError, TypeError):
        return api_error("price_per_night and capacity must be numbers", 400)

    if price <= 0:
        return api_error("price_per_night must be greater than 0", 400)
    if capacity <= 0:
        return api_error("capacity must be greater than 0", 400)

    room = Room(
        name=data["name"].strip(),
        type=data["type"].strip(),
        description=data.get("description", ""),
        price_per_night=price,
        capacity=capacity,
        image_url=data.get("image_url", ""),
        is_active=True,
    )
    db.session.add(room)
    db.session.commit()

    return api_success(room.to_dict(), message="Room created", status_code=201)


# ── PUT /api/rooms/<id> ────────────────────────────────────────────────────

@rooms_bp.route("/<int:room_id>", methods=["PUT"])
@admin_required
def update_room(room_id, current_user):
    """Admin only: update an existing room."""
    room = Room.query.get(room_id)
    if not room:
        return api_error("Room not found", 404)

    data = request.get_json(silent=True) or {}

    if "name" in data:
        room.name = data["name"].strip()
    if "type" in data:
        room.type = data["type"].strip()
    if "description" in data:
        room.description = data["description"]
    if "price_per_night" in data:
        try:
            room.price_per_night = float(data["price_per_night"])
        except (ValueError, TypeError):
            return api_error("price_per_night must be a number", 400)
    if "capacity" in data:
        try:
            room.capacity = int(data["capacity"])
        except (ValueError, TypeError):
            return api_error("capacity must be a number", 400)
    if "image_url" in data:
        room.image_url = data["image_url"]
    if "is_active" in data:
        room.is_active = bool(data["is_active"])

    db.session.commit()
    return api_success(room.to_dict(), message="Room updated")


# ── DELETE /api/rooms/<id> ─────────────────────────────────────────────────

@rooms_bp.route("/<int:room_id>", methods=["DELETE"])
@admin_required
def deactivate_room(room_id, current_user):
    """Admin only: soft-delete a room by setting is_active = False."""
    room = Room.query.get(room_id)
    if not room:
        return api_error("Room not found", 404)

    room.is_active = False
    db.session.commit()
    return api_success({"id": room.id}, message="Room deactivated")
