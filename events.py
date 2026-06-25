from datetime import date as date_type
from flask import Blueprint, request
from db import db
from models import Event
from utils import api_error, api_success, admin_required

events_bp = Blueprint("events", __name__)


def _parse_date(value, field_name):
    """Parse an ISO date string; return (date, None) or (None, error_response)."""
    try:
        return date_type.fromisoformat(value), None
    except (ValueError, TypeError):
        return None, api_error(f"Invalid date format for '{field_name}'. Use YYYY-MM-DD.", 400)


def has_tickets_available(event_id, requested_quantity):
    """Return True if the event has enough tickets for the requested quantity."""
    event = Event.query.get(event_id)
    if not event:
        return False
    return (event.tickets_sold + requested_quantity) <= event.total_tickets


# ── GET /api/events ────────────────────────────────────────────────────────

@events_bp.route("", methods=["GET"])
@events_bp.route("/", methods=["GET"])
def list_events():
    """Return all active events, optionally filtered by category or upcoming only."""
    category = request.args.get("category")
    upcoming = request.args.get("upcoming", "false").lower() == "true"

    query = Event.query.filter_by(is_active=True)

    if category and category.lower() != "all":
        query = query.filter_by(category=category.lower())

    if upcoming:
        today = date_type.today()
        query = query.filter(Event.event_date >= today)

    events = query.order_by(Event.event_date.asc()).all()
    return api_success([e.to_dict() for e in events])


# ── GET /api/events/<id> ───────────────────────────────────────────────────

@events_bp.route("/<int:event_id>", methods=["GET"])
def get_event(event_id):
    """Return a single active event by id."""
    event = Event.query.filter_by(id=event_id, is_active=True).first()
    if not event:
        return api_error("Event not found", 404)
    return api_success(event.to_dict())


# ── POST /api/events ───────────────────────────────────────────────────────

@events_bp.route("", methods=["POST"])
@events_bp.route("/", methods=["POST"])
@admin_required
def create_event(current_user):
    """Admin only: create a new event."""
    data = request.get_json(silent=True) or {}

    for field in ("title", "category", "venue", "event_date", "event_time",
                  "ticket_price", "total_tickets"):
        if data.get(field) is None or str(data.get(field, "")).strip() == "":
            return api_error(f"Field '{field}' is required", 400)

    event_date, err = _parse_date(str(data["event_date"]), "event_date")
    if err:
        return err

    try:
        ticket_price  = float(data["ticket_price"])
        total_tickets = int(data["total_tickets"])
    except (ValueError, TypeError):
        return api_error("ticket_price and total_tickets must be numbers", 400)

    if ticket_price <= 0:
        return api_error("ticket_price must be greater than 0", 400)
    if total_tickets <= 0:
        return api_error("total_tickets must be greater than 0", 400)

    valid_categories = ("concert", "show", "sport")
    if data["category"].lower() not in valid_categories:
        return api_error(f"category must be one of: {', '.join(valid_categories)}", 400)

    event = Event(
        title=data["title"].strip(),
        category=data["category"].lower().strip(),
        description=data.get("description", ""),
        venue=data["venue"].strip(),
        event_date=event_date,
        event_time=data["event_time"].strip(),
        ticket_price=ticket_price,
        total_tickets=total_tickets,
        tickets_sold=0,
        image_url=data.get("image_url", ""),
        is_active=True,
    )
    db.session.add(event)
    db.session.commit()

    return api_success(event.to_dict(), message="Event created", status_code=201)


# ── PUT /api/events/<id> ───────────────────────────────────────────────────

@events_bp.route("/<int:event_id>", methods=["PUT"])
@admin_required
def update_event(event_id, current_user):
    """Admin only: update an existing event."""
    event = Event.query.get(event_id)
    if not event:
        return api_error("Event not found", 404)

    data = request.get_json(silent=True) or {}

    if "title" in data:
        event.title = data["title"].strip()
    if "category" in data:
        event.category = data["category"].lower().strip()
    if "description" in data:
        event.description = data["description"]
    if "venue" in data:
        event.venue = data["venue"].strip()
    if "event_date" in data:
        parsed, err = _parse_date(str(data["event_date"]), "event_date")
        if err:
            return err
        event.event_date = parsed
    if "event_time" in data:
        event.event_time = data["event_time"].strip()
    if "ticket_price" in data:
        try:
            event.ticket_price = float(data["ticket_price"])
        except (ValueError, TypeError):
            return api_error("ticket_price must be a number", 400)
    if "total_tickets" in data:
        try:
            event.total_tickets = int(data["total_tickets"])
        except (ValueError, TypeError):
            return api_error("total_tickets must be a number", 400)
    if "image_url" in data:
        event.image_url = data["image_url"]
    if "is_active" in data:
        event.is_active = bool(data["is_active"])

    db.session.commit()
    return api_success(event.to_dict(), message="Event updated")


# ── DELETE /api/events/<id> ────────────────────────────────────────────────

@events_bp.route("/<int:event_id>", methods=["DELETE"])
@admin_required
def deactivate_event(event_id, current_user):
    """Admin only: soft-delete an event by setting is_active = False."""
    event = Event.query.get(event_id)
    if not event:
        return api_error("Event not found", 404)

    event.is_active = False
    db.session.commit()
    return api_success({"id": event.id}, message="Event deactivated")
