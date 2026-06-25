# ── Create the Flask application (required by Vercel) ─────────────────────

app = create_app()

# ── Entry point for local development ──────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
    import os
import bcrypt
from datetime import date as date_type
from flask import Flask, send_from_directory
from flask_cors import CORS
from db import db
from utils import api_error


def create_app(test_config=None):
    """Flask application factory."""
    root_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__, static_folder=root_dir, static_url_path="")

    # ── Configuration ──────────────────────────────────────────────────────
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lodge.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.environ.get(
        "JWT_SECRET_KEY", "eventzone-secret-key-change-in-production"
    )

    if test_config:
        app.config.update(test_config)

    # ── Extensions ─────────────────────────────────────────────────────────
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    app.url_map.strict_slashes = False

    # ── Blueprints ─────────────────────────────────────────────────────────
    from auth import auth_bp
    from events import events_bp
    from bookings import bookings_bp
    from payments import payments_bp
    from admin import admin_bp

    app.register_blueprint(auth_bp,     url_prefix="/api/auth")
    app.register_blueprint(events_bp,   url_prefix="/api/events")
    app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
    app.register_blueprint(payments_bp, url_prefix="/api/payments")
    app.register_blueprint(admin_bp,    url_prefix="/api/admin")

    # ── Database init & seed ───────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        seed_data()

    # ── Serve frontend HTML files ──────────────────────────────────────────
    @app.route("/")
    def serve_index():
        return send_from_directory(root_dir, "index.html")

    @app.route("/admin")
    @app.route("/admin.html")
    def serve_admin():
        return send_from_directory(root_dir, "admin.html")

    # ── Global error handlers ──────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return api_error("Resource not found", 404)

    @app.errorhandler(405)
    def method_not_allowed(e):
        return api_error("Method not allowed", 405)

    @app.errorhandler(500)
    def server_error(e):
        return api_error("Internal server error", 500)

    return app


# ── Seed data ──────────────────────────────────────────────────────────────

SEED_EVENTS = [
    {
        "title": "Afrobeats Night Live",
        "category": "concert",
        "venue": "Lusaka Arena",
        "event_date": "2026-08-15",
        "event_time": "19:00",
        "ticket_price": 50.0,
        "total_tickets": 500,
        "description": "The biggest Afrobeats concert of the year.",
        "image_url": "/static/AfroBeat.jpg",
    },
    {
        "title": "Comedy Gala 2026",
        "category": "show",
        "venue": "Levy Mall Theatre",
        "event_date": "2026-09-20",
        "event_time": "20:00",
        "ticket_price": 35.0,
        "total_tickets": 300,
        "description": "A night of non-stop laughter with top comedians.",
        "image_url": "/static/comedy.jpg",
    },
    {
        "title": "Zambia vs Tanzania — AFCON Qualifier",
        "category": "sport",
        "venue": "National Heroes Stadium",
        "event_date": "2026-10-10",
        "event_time": "15:00",
        "ticket_price": 25.0,
        "total_tickets": 1000,
        "description": "Cheer the Chipolopolo in this crucial qualifier.",
        "image_url": "/static/football.jpg",
    },
    {
        "title": "Jazz & Wine Evening",
        "category": "concert",
        "venue": "Radisson Blu Rooftop",
        "event_date": "2026-11-05",
        "event_time": "18:30",
        "ticket_price": 80.0,
        "total_tickets": 150,
        "description": "An intimate evening of jazz under the stars.",
        "image_url": "/static/GALA.webp",
    },
    {
        "title": "Magic Show Spectacular",
        "category": "show",
        "venue": "Arcades Entertainment",
        "event_date": "2026-12-01",
        "event_time": "17:00",
        "ticket_price": 20.0,
        "total_tickets": 200,
        "description": "Mind-blowing illusions for the whole family.",
        "image_url": "/static/joze.webp",
    },
]

SEED_ADMIN = {
    "full_name": "System Admin",
    "email": "admin@eventzone.com",
    "password": "Admin1234",
    "role": "admin",
}


def seed_data():
    """Insert seed events and admin account only when tables are empty."""
    from models import Event, User

    if Event.query.count() == 0:
        for e in SEED_EVENTS:
            event = Event(
                title=e["title"],
                category=e["category"],
                venue=e["venue"],
                event_date=date_type.fromisoformat(e["event_date"]),
                event_time=e["event_time"],
                ticket_price=e["ticket_price"],
                total_tickets=e["total_tickets"],
                tickets_sold=0,
                description=e.get("description", ""),
                image_url=e.get("image_url", ""),
                is_active=True,
            )
            db.session.add(event)

    if User.query.filter_by(role="admin").count() == 0:
        hashed = bcrypt.hashpw(
            SEED_ADMIN["password"].encode("utf-8"), bcrypt.gensalt()
        )
        admin = User(
            full_name=SEED_ADMIN["full_name"],
            email=SEED_ADMIN["email"],
            password_hash=hashed.decode("utf-8"),
            role=SEED_ADMIN["role"],
        )
        db.session.add(admin)

    db.session.commit()


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    application = create_app()
    application.run(debug=True, port=5000)
