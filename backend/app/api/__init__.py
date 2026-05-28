from flask import Flask

from .actions import actions_bp
from .sessions import sessions_bp
from .upload import upload_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(upload_bp, url_prefix="/api/upload")
    app.register_blueprint(sessions_bp, url_prefix="/api/sessions")
    app.register_blueprint(actions_bp, url_prefix="/api/actions")
