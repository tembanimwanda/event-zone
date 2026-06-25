from datetime import date as date_type
from flask import Blueprint, request
from db import db
from models import Booking, Event
from utils import api_error, api_success, jwt_required

bookings_bp = Blueprint("bookings", __name__)


def calculate_total_price(ticket_price, ticket_quantity):
    """Calculate total booking price."""
    return round(ticket_price * ticket_quantity, 2)


# ── POST /api/bookings ─────────────────────────────────────────────────────

@bookings_bp.route("", methods=["POST"])
@bookings_bp.route("/", methods=["POST"])
@jwt_required
def create_booking(current_user):
    """Authenticated: create a new event booking."""
    data = request.get_json(silent=True) or {}

    # Validate required fields
    for field in ("event_id", "ticket_quantity"):
        if data.get(field) is None:
            return api_error(f"Field '{field}' is required", 400)

    # Validate ticket_quantity
    try:
        ticket_quantity = int(data["ticket_quantity"])
        if ticket_quantity < 1:
            raise ValueError
    except (ValueError, TypeError):
        return api_error("ticket_quantity must be a positive integer", 400)

    # Validate event exists
    try:
        event_id = int(data["event_id"])
    except (ValueError, TypeError):
        return api_error("Invalid event_id", 400)

    event = Event.query.filter_by(id=event_id, is_active=True).first()
    if not event:
        return api_error("Event not found", 404)

    # Check ticket availability
    if (event.tickets_sold + ticket_quantity) > event.total_tickets:
        available = event.total_tickets - event.tickets_sold
        return api_error(
            f"Not enough tickets available. Only {available} tickets remaining.",
            409
        )

    # Calculate total price
    total_price = calculate_total_price(event.ticket_price, ticket_quantity)

    # Create booking
    booking = Booking(
        user_id=current_user.id,
        event_id=event_id,
        ticket_quantity=ticket_quantity,
        total_price=total_price,
        status="pending",
    )
    db.session.add(booking)

    # Increment tickets_sold
    event.tickets_sold += ticket_quantity
    db.session.commit()

    return api_success(
        {
            "booking_id":      booking.id,
            "event_title":     event.title,
            "event_date":      event.event_date.isoformat(),
            "event_time":      event.event_time,
            "venue":           event.venue,
            "ticket_quantity": ticket_quantity,
            "total_price":     total_price,
            "status":          booking.status,
        },
        message="Booking created",
        status_code=201,
    )


# ── GET /api/bookings/my ───────────────────────────────────────────────────

@bookings_bp.route("/my", methods=["GET"])
@jwt_required
def my_bookings(current_user):
    """Authenticated: return all bookings for the current user."""
    bookings = (
        Booking.query
        .filter_by(user_id=current_user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )
    return api_success([b.to_dict() for b in bookings])


# ── PUT /api/bookings/<id>/cancel ──────────────────────────────────────────

@bookings_bp.route("/<int:booking_id>/cancel", methods=["PUT"])
@jwt_required
def cancel_booking(booking_id, current_user):
    """Authenticated: cancel a booking if event is in the future."""
    booking = Booking.query.filter_by(
        id=booking_id, user_id=current_user.id
    ).first()

    if not booking:
        return api_error("Booking not found", 404)

    if booking.status == "cancelled":
        return api_error("Booking is already cancelled", 400)

    event = Event.query.get(booking.event_id)
    if not event:
        return api_error("Event not found", 404)

    today = date_type.today()
    if event.event_date <= today:
        return api_error("Cannot cancel a booking on or after event date", 400)

    # Decrement tickets_sold
    event.tickets_sold -= booking.ticket_quantity
    booking.status = "cancelled"
    db.session.commit()

    return api_success(
        {"booking_id": booking.id, "status": booking.status},
        message="Booking cancelled",
    )
