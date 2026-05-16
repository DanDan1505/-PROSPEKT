"""Application factory for the PROSPEKT dashboard."""

from flask import Flask


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    from prospekt_dashboard.main.routes import main_bp

    app.register_blueprint(main_bp)

    return app
