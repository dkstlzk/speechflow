# pyrefly: ignore [missing-import]
import eventlet
eventlet.monkey_patch()

import threading
from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

from .api import register_blueprints
from .config.logging import configure_logging
from .config.settings import settings
from .websocket import register_socketio_events

from .db.base import Base
from .db.session import engine, SessionLocal
from .db.migrations import run_migrations

from .workers.realtime import realtime_worker_loop

from .config.logging import get_logger

configure_logging()
logger = get_logger(__name__)

cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")] if settings.CORS_ORIGINS and settings.CORS_ORIGINS != "*" else "*"

socketio = SocketIO(
    cors_allowed_origins=cors_origins,
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

    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    
    CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": cors_origins, "expose_headers": ["Content-Range", "Accept-Ranges", "Content-Length"]}})

    register_blueprints(app)
    register_socketio_events(socketio)
    socketio.init_app(app)



    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


if __name__ == "__main__":
    app = create_app()

    Base.metadata.create_all(bind=engine)
    run_migrations(engine)

    # Recover stale sessions
    db = None
    try:
        from .services.persistence.session_repository import recover_stale_sessions
        from .db.session import SessionLocal
        db = SessionLocal()
        recovered = recover_stale_sessions(db)
        logger.info(
            f"Stale session recovery completed. Recovered={recovered}"
        )
    except Exception as e:
        logger.error(f"Failed to recover stale sessions: {e}")
    finally:
        if db is not None:
            db.close()

    threading.Thread(
        target=realtime_worker_loop,
        args=(socketio,),
        daemon=True,
    ).start()

    from .workers.realtime.worker_state import transcriber
    threading.Thread(
        target=transcriber._get_model,
        daemon=True,
    ).start()

    from .services.diarization.pyannote import _get_pipeline
    def _warm_pyannote():
        try:
            _get_pipeline()
            logger.info("Pyannote warmup completed successfully")
        except Exception as e:
            logger.error(f"Pyannote warmup failed: {e}")

    threading.Thread(
        target=_warm_pyannote,
        daemon=True,
    ).start()

    import os
    is_debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    socketio.run(app, host="0.0.0.0", port=5000, debug=is_debug)