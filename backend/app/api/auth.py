from flask import Blueprint, request, jsonify, session
from ..config.settings import settings
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    password = data.get("password")
    
    if password == settings.ADMIN_PASSWORD:
        session["authenticated"] = True
        logger.info("Admin user logged in successfully.")
        return jsonify({"success": True, "message": "Logged in successfully"})
    else:
        logger.warning("Failed login attempt.")
        return jsonify({"success": False, "error": "Invalid password"}), 401

@auth_bp.post("/logout")
def logout():
    session.clear()
    logger.info("Admin user logged out.")
    try:
        from ..main import socketio
        socketio.emit("force_disconnect", to="admin")
        logger.info("Sent force_disconnect broadcast to admin room.")
    except Exception as e:
        logger.error(f"Failed to broadcast disconnect: {e}")
    return jsonify({"success": True, "message": "Logged out successfully"})

@auth_bp.get("/status")
def status():
    is_auth = session.get("authenticated", False)
    return jsonify({"success": True, "authenticated": is_auth})
