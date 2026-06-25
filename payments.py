import re
import random
import string
from datetime import date as date_type
from flask import Blueprint, request, send_file
from db import db
from models import Booking, Payment
from utils import api_error, api_success, jwt_required
from tickets import generate_ticket_buffer

payments_bp = Blueprint("payments", __name__)

# In-memory store for pending MTN MoMo transactions
# { transaction_id: { "booking_id": int, "user_id": int } }
_pending_momo = {}


def _validate_card(card_number, card_expiry, card_cvv):
    """
    Validate card fields.
    Returns (True, None) on success or (False, error_message) on failure.
    """
    # Card number: exactly 16 digits
    if not re.fullmatch(r"\d{16}", str(card_number or "").replace(" ", "")):
        return False, "Invalid card number"

    # CVV: exactly 3 digits
    if not re.fullmatch(r"\d{3}", str(card_cvv or "")):
        return False, "Invalid CVV"

    # Expiry: MM/YY format and not in the past
    expiry_str = str(card_expiry or "")
    if not re.fullmatch(r"\d{2}/\d{2}", expiry_str):
        return False, "Card has expired"

    month_str, year_str = expiry_str.split("/")
    try:
        month = int(month_str)
        year  = 2000 + int(year_str)
    except ValueError:
        return False, "Card has expired"

    if month < 1 or month > 12:
        return False, "Card has expired"

    today = date_type.today()
    if year < today.year or (year == today.year and month < today.month):
        return False, "Card has expired"

    return True, None


def _validate_momo_phone(phone_number):
    """
    Validate MTN MoMo phone number.
    Must match ^(096|076|077)\\d{7}$ — 10 digits starting with 096, 076, or 077.
    """
    if not re.fullmatch(r"(096|076|077)\d{7}", str(phone_number or "")):
        return False, "Invalid MTN MoMo number. Must be 10 digits starting with 096, 076, or 077."
    return True, None


def _generate_transaction_id():
    """Generate a random MTN MoMo transaction ID."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"MTN-{suffix}"


# ── POST /api/payments ─────────────────────────────────────────────────────

@payments_bp.route("", methods=["POST"])
@payments_bp.route("/", methods=["POST"])
@jwt_required
def process_payment(current_user):
    """
    Authenticated: process a payment for a booking.
    Supports payment_method: 'card' or 'mtn_momo'.
    For mtn_momo, returns 202 with transaction_id on first call.
    """
    data = request.get_json(silent=True) or {}

    if data.get("booking_id") is None:
        return api_error("Field 'booking_id' is required", 400)

    payment_method = data.get("payment_method", "card").lower()
    if payment_method not in ("card", "mtn_momo"):
        return api_error("payment_method must be 'card' or 'mtn_momo'", 400)

    # Look up booking
    try:
        booking_id = int(data["booking_id"])
    except (ValueError, TypeError):
        return api_error("Invalid booking_id", 400)

    booking = Booking.query.filter_by(
        id=booking_id, user_id=current_user.id
    ).first()

    if not booking:
        return api_error("Booking not found", 404)

    if booking.status != "pending":
        return api_error(
            f"Booking cannot be paid — current status is '{booking.status}'", 400
        )

    # ── Card payment ───────────────────────────────────────────────────────
    if payment_method == "card":
        for field in ("card_number", "card_expiry", "card_cvv"):
            if data.get(field) is None:
                return api_error(f"Field '{field}' is required for card payment", 400)

        valid, error_msg = _validate_card(
            data["card_number"], data["card_expiry"], data["card_cvv"]
        )
        if not valid:
            return api_error(error_msg, 400)

        card_last_four = str(data["card_number"]).replace(" ", "")[-4:]
        payment = Payment(
            booking_id=booking.id,
            amount=booking.total_price,
            card_last_four=card_last_four,
            payment_method="card",
            status="completed",
        )
        db.session.add(payment)
        booking.status = "confirmed"
        db.session.commit()

        booking_ref = f"EZ-{booking.id:06d}"
        return api_success(
            {
                "booking_ref":  booking_ref,
                "booking_id":   booking.id,
                "payment_id":   payment.id,
                "amount":       payment.amount,
                "status":       booking.status,
                "payment_method": "card",
            },
            message="Payment successful. Booking confirmed.",
        )

    # ── MTN MoMo — Step 1: initiate ───────────────────────────────────────
    if data.get("phone_number") is None:
        return api_error("Field 'phone_number' is required for MTN MoMo payment", 400)

    valid, error_msg = _validate_momo_phone(data["phone_number"])
    if not valid:
        return api_error(error_msg, 400)

    transaction_id = _generate_transaction_id()
    _pending_momo[transaction_id] = {
        "booking_id": booking.id,
        "user_id":    current_user.id,
        "phone":      str(data["phone_number"]),
    }

    from flask import make_response
    resp = make_response(
        api_success(
            {
                "status":         "pending",
                "transaction_id": transaction_id,
                "message":        "Enter your MTN MoMo PIN to confirm",
            },
            message="Enter your MTN MoMo PIN to confirm",
        )[0],
        202,
    )
    return resp


# ── POST /api/payments/confirm ─────────────────────────────────────────────

@payments_bp.route("/confirm", methods=["POST"])
@jwt_required
def confirm_momo_payment(current_user):
    """
    Authenticated: confirm an MTN MoMo payment with transaction_id + PIN.
    Any 4-digit PIN is accepted in simulation.
    """
    data = request.get_json(silent=True) or {}

    transaction_id = data.get("transaction_id")
    pin            = str(data.get("pin", ""))

    if not transaction_id:
        return api_error("Field 'transaction_id' is required", 400)

    if not re.fullmatch(r"\d{4}", pin):
        return api_error("PIN must be exactly 4 digits", 400)

    pending = _pending_momo.get(transaction_id)
    if not pending:
        return api_error("Transaction not found or already processed", 404)

    if pending["user_id"] != current_user.id:
        return api_error("Transaction not found or already processed", 404)

    booking = Booking.query.filter_by(
        id=pending["booking_id"], user_id=current_user.id
    ).first()

    if not booking:
        del _pending_momo[transaction_id]
        return api_error("Booking not found", 404)

    if booking.status != "pending":
        del _pending_momo[transaction_id]
        return api_error(
            f"Booking cannot be paid — current status is '{booking.status}'", 400
        )

    # Use last 4 digits of phone number as card_last_four
    phone = pending["phone"]
    card_last_four = phone[-4:]

    payment = Payment(
        booking_id=booking.id,
        amount=booking.total_price,
        card_last_four=card_last_four,
        payment_method="mtn_momo",
        status="completed",
    )
    db.session.add(payment)
    booking.status = "confirmed"
    db.session.commit()

    del _pending_momo[transaction_id]

    booking_ref = f"EZ-{booking.id:06d}"
    return api_success(
        {
            "booking_ref":    booking_ref,
            "booking_id":     booking.id,
            "payment_id":     payment.id,
            "amount":         payment.amount,
            "status":         booking.status,
            "payment_method": "mtn_momo",
            "transaction_id": transaction_id,
        },
        message="MTN MoMo payment confirmed. Booking confirmed.",
    )


# ── GET /api/payments/ticket/<id> ─────────────────────────────────────────

@payments_bp.route("/ticket/<int:booking_id>", methods=["GET"])
@jwt_required
def download_ticket(booking_id, current_user):
    """
    Authenticated: download a confirmed booking's ticket as PDF.
    Only the booking owner can download their ticket.
    """
    booking = Booking.query.filter_by(
        id=booking_id, user_id=current_user.id
    ).first()

    if not booking:
        return api_error("Booking not found", 404)

    if booking.status != "confirmed":
        return api_error(
            f"Ticket is only available for confirmed bookings. Current status: {booking.status}", 400
        )

    try:
        # Generate PDF ticket
        pdf_buffer = generate_ticket_buffer(
            booking_id=booking.id,
            user_email=current_user.email,
            user_name=current_user.full_name
        )
        
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"EventZone_Ticket_{booking.id:06d}.pdf"
        )
    except Exception as err:
        return api_error(f"Failed to generate ticket: {str(err)}", 500)

