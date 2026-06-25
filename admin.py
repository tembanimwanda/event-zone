from datetime import date as date_type
from flask import Blueprint, request
from sqlalchemy import func
from db import db
from models import Booking, User, Event, Payment
from utils import api_error, api_success, admin_required

admin_bp = Blueprint("admin", __name__)

PAGE_SIZE = 20


# ── PUT /api/admin/bookings/<id>/status ───────────────────────────────────

@admin_bp.route("/bookings/<int:booking_id>/status", methods=["PUT"])
@admin_required
def update_booking_status(booking_id, current_user):
    """Admin only: update a booking status (confirmed / cancelled)."""
    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "").lower()

    if new_status not in ("confirmed", "cancelled"):
        return api_error("Status must be 'confirmed' or 'cancelled'", 400)

    booking = Booking.query.get(booking_id)
    if not booking:
        return api_error("Booking not found", 404)

    if booking.status == "cancelled":
        return api_error("Cannot update a cancelled booking", 400)

    booking.status = new_status
    db.session.commit()

    return api_success(
        {"booking_id": booking.id, "status": booking.status},
        message=f"Booking {booking_id} marked as {new_status}."
    )


# ── GET /api/admin/bookings ────────────────────────────────────────────────

@admin_bp.route("/bookings", methods=["GET"])
@admin_required
def admin_bookings(current_user):
    """Admin only: paginated list of all bookings with optional status filter."""
    status_filter = request.args.get("status", "all")
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    query = Booking.query
    if status_filter != "all":
        query = query.filter_by(status=status_filter)

    total    = query.count()
    bookings = (
        query
        .order_by(Booking.created_at.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )

    results = []
    for b in bookings:
        row = b.to_dict()
        row["guest_name"] = b.user.full_name if b.user else "Unknown"
        results.append(row)

    return api_success({
        "bookings":    results,
        "total":       total,
        "page":        page,
        "page_size":   PAGE_SIZE,
        "total_pages": max(1, -(-total // PAGE_SIZE)),  # ceiling division
    })


# ── GET /api/admin/users ───────────────────────────────────────────────────

@admin_bp.route("/users", methods=["GET"])
@admin_required
def admin_users(current_user):
    """Admin only: all users with booking counts."""
    booking_counts = (
        db.session.query(
            Booking.user_id,
            func.count(Booking.id).label("booking_count")
        )
        .group_by(Booking.user_id)
        .subquery()
    )

    users = (
        db.session.query(User, booking_counts.c.booking_count)
        .outerjoin(booking_counts, User.id == booking_counts.c.user_id)
        .order_by(User.created_at.desc())
        .all()
    )

    results = []
    for user, count in users:
        row = user.to_dict()
        row["booking_count"] = count or 0
        results.append(row)

    return api_success(results)


# ── GET /api/admin/stats ───────────────────────────────────────────────────

@admin_bp.route("/events", methods=["GET"])
@admin_required
def admin_events(current_user):
    """Admin only: list all events including inactive."""
    events = Event.query.order_by(Event.event_date.asc()).all()
    return api_success([e.to_dict() for e in events])


@admin_bp.route("/stats", methods=["GET"])
@admin_required
def admin_stats(current_user):
    """Admin only: aggregate statistics."""
    total_bookings   = Booking.query.count()
    active_events    = Event.query.filter_by(is_active=True).count()
    registered_users = User.query.count()

    # Total revenue = sum of confirmed payment amounts
    total_revenue = (
        db.session.query(func.sum(Payment.amount))
        .join(Booking, Payment.booking_id == Booking.id)
        .filter(Booking.status == "confirmed")
        .scalar()
    ) or 0.0

    # Tickets sold today
    today = date_type.today()
    tickets_sold_today = (
        db.session.query(func.sum(Booking.ticket_quantity))
        .filter(
            func.date(Booking.created_at) == today,
            Booking.status.in_(["pending", "confirmed"]),
        )
        .scalar()
    ) or 0

    return api_success({
        "total_bookings":    total_bookings,
        "total_revenue":     round(float(total_revenue), 2),
        "active_events":     active_events,
        "registered_users":  registered_users,
        "tickets_sold_today": int(tickets_sold_today),
    })
