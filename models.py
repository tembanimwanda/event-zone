from datetime import datetime
from db import db


class User(db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    full_name     = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default="guest")
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship("Booking", backref="user", lazy=True)

    def to_dict(self):
        return {
            "id":         self.id,
            "full_name":  self.full_name,
            "email":      self.email,
            "role":       self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Event(db.Model):
    __tablename__ = "events"

    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(200), nullable=False)
    category      = db.Column(db.String(50), nullable=False)   # concert/show/sport
    description   = db.Column(db.Text)
    venue         = db.Column(db.String(200), nullable=False)
    event_date    = db.Column(db.Date, nullable=False)
    event_time    = db.Column(db.String(10), nullable=False)   # e.g. "19:00"
    ticket_price  = db.Column(db.Float, nullable=False)
    total_tickets = db.Column(db.Integer, nullable=False)
    tickets_sold  = db.Column(db.Integer, default=0, nullable=False)
    is_active     = db.Column(db.Boolean, default=True, nullable=False)
    image_url     = db.Column(db.String(500), default="")

    bookings = db.relationship("Booking", backref="event", lazy=True)

    def to_dict(self):
        return {
            "id":               self.id,
            "title":            self.title,
            "category":         self.category,
            "description":      self.description,
            "venue":            self.venue,
            "event_date":       self.event_date.isoformat() if self.event_date else None,
            "event_time":       self.event_time,
            "ticket_price":     self.ticket_price,
            "total_tickets":    self.total_tickets,
            "tickets_sold":     self.tickets_sold,
            "tickets_available": self.total_tickets - self.tickets_sold,
            "is_active":        self.is_active,
            "image_url":        self.image_url or "",
        }


class Booking(db.Model):
    __tablename__ = "bookings"

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id        = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    ticket_quantity = db.Column(db.Integer, nullable=False)
    total_price     = db.Column(db.Float, nullable=False)
    status          = db.Column(db.String(20), nullable=False, default="pending")
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    payment = db.relationship("Payment", backref="booking", uselist=False, lazy=True)

    def to_dict(self):
        return {
            "id":              self.id,
            "user_id":         self.user_id,
            "event_id":        self.event_id,
            "event_title":     self.event.title if self.event else None,
            "event_date":      self.event.event_date.isoformat() if self.event else None,
            "ticket_quantity": self.ticket_quantity,
            "total_price":     self.total_price,
            "status":          self.status,
            "created_at":      self.created_at.isoformat() if self.created_at else None,
        }


class Payment(db.Model):
    __tablename__ = "payments"

    id             = db.Column(db.Integer, primary_key=True)
    booking_id     = db.Column(
        db.Integer, db.ForeignKey("bookings.id"), nullable=False, unique=True
    )
    amount         = db.Column(db.Float, nullable=False)
    card_last_four = db.Column(db.String(4), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False, default="card")  # card/mtn_momo
    status         = db.Column(db.String(20), nullable=False, default="completed")
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":             self.id,
            "booking_id":     self.booking_id,
            "amount":         self.amount,
            "card_last_four": self.card_last_four,
            "payment_method": self.payment_method,
            "status":         self.status,
            "created_at":     self.created_at.isoformat() if self.created_at else None,
        }
