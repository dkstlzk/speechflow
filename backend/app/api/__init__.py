from flask import Flask, request, session, jsonify

from .realtime import realtime_bp
from .actions import actions_bp
from .sessions import sessions_bp
from .upload import upload_bp
from .auth import auth_bp

def register_blueprints(app: Flask) -> None:
    @app.before_request
    def require_auth():
        # Exempt CORS preflight requests
        if request.method == "OPTIONS":
            return
            
        # Exempt specific paths
        if request.path.startswith("/api/auth/") or request.path == "/health":
            return
            
        # Protect all other /api/ routes
        if request.path.startswith("/api/"):
            if not session.get("authenticated"):
                return jsonify({"success": False, "error": "Unauthorized"}), 401

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(upload_bp, url_prefix="/api/upload")
    app.register_blueprint(sessions_bp, url_prefix="/api/sessions")
    app.register_blueprint(actions_bp, url_prefix="/api/actions")
    app.register_blueprint(realtime_bp, url_prefix="/api/realtime")