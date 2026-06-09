# pyrefly: ignore [missing-import]
import eventlet
eventlet.monkey_patch()

import threading
from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

from .api import register_blueprints
from .config.logging import configure_logging
from .config.settings import Settings
from .websocket import register_socketio_events

from .db.base import Base
from .db.session import engine, SessionLocal
from .db.migrations import run_migrations

from .workers.realtime_worker import realtime_worker_loop

from .config.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)
settings = Settings()
socketio = SocketIO(
    cors_allowed_origins=settings.CORS_ORIGINS,
    async_mode="eventlet",
)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.DATABASE_URL
    app.config["UPLOAD_DIR"] = settings.UPLOAD_DIR
    app.config["EXPORT_DIR"] = settings.EXPORT_DIR
    app.config["TRANSCRIPTS_DIR"] = settings.TRANSCRIPTS_DIR
    app.config["MODEL_DIR"] = settings.MODEL_DIR
    app.config["MAX_CONTENT_LENGTH"] = settings.MAX_CONTENT_LENGTH
    app.config["ALLOWED_EXTENSIONS"] = settings.ALLOWED_EXTENSIONS

    CORS(app, resources={r"/api/*": {"origins": settings.CORS_ORIGINS}})

    register_blueprints(app)
    register_socketio_events(socketio)
    socketio.init_app(app)

    Base.metadata.create_all(bind=engine)
    run_migrations(engine)

    # Recover stale sessions
    try:
        from .services.persistence.session_repository import recover_stale_sessions
        db = SessionLocal()
        recovered = recover_stale_sessions(db)
        logger.info(
            f"Stale session recovery completed. Recovered={recovered}"
        )
    except Exception as e:
        logger.error(f"Failed to recover stale sessions: {e}")
    finally:
        db.close()

    threading.Thread(
        target=realtime_worker_loop,
        args=(socketio,),
        daemon=True,
    ).start()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


if __name__ == "__main__":
    app = create_app()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)