from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

from .api import register_blueprints
from .config.settings import Settings
from .websocket import register_socketio_events

settings = Settings()
socketio = SocketIO(
    cors_allowed_origins=settings.CORS_ORIGINS,
    async_mode=settings.SOCKETIO_ASYNC_MODE,
)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.DATABASE_URL
    app.config["UPLOAD_DIR"] = settings.UPLOAD_DIR
    app.config["EXPORT_DIR"] = settings.EXPORT_DIR
    app.config["TRANSCRIPTS_DIR"] = settings.TRANSCRIPTS_DIR
    app.config["MODEL_DIR"] = settings.MODEL_DIR

    CORS(app, resources={r"/api/*": {"origins": settings.CORS_ORIGINS}})

    register_blueprints(app)
    register_socketio_events(socketio)
    socketio.init_app(app)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


if __name__ == "__main__":
    app = create_app()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)