# pyrefly: ignore [missing-import]
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="eventlet")
warnings.filterwarnings("ignore", message=".*Eventlet is deprecated.*")

# pyrefly: ignore [missing-import]
import eventlet
eventlet.monkey_patch()

import threading
import signal
import sys
import time
from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

from .api import register_blueprints
from .config.logging import configure_logging
from .config.settings import settings
from .websocket import register_socketio_events
from .config.extensions import limiter

from .db.base import Base
from .db.session import engine, SessionLocal
from .db.migrations import run_migrations

from .workers.realtime import realtime_worker_loop

from .config.logging import get_logger

configure_logging()
logger = get_logger(__name__)

cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")] if settings.CORS_ORIGINS and settings.CORS_ORIGINS != "*" else "*"
if not settings.DEBUG and cors_origins == "*":
    raise RuntimeError("CORS_ORIGINS must be configured to an explicit whitelist in production.")

socketio = SocketIO(
    cors_allowed_origins=cors_origins,
    async_mode="eventlet",
)

_PROCESS_INITIALIZED = False

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    # Only use secure cookies in production/non-testing environments
    app.config["SESSION_COOKIE_SECURE"] = False if app.config.get("TESTING") or settings.DATABASE_URL.startswith("sqlite") else True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.DATABASE_URL
    app.config["UPLOAD_DIR"] = settings.UPLOAD_DIR
    app.config["EXPORT_DIR"] = settings.EXPORT_DIR
    app.config["MODEL_DIR"] = settings.MODEL_DIR
    app.config["MAX_CONTENT_LENGTH"] = settings.MAX_CONTENT_LENGTH
    app.config["ALLOWED_EXTENSIONS"] = settings.ALLOWED_EXTENSIONS

    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    
    CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": cors_origins, "expose_headers": ["Content-Range", "Accept-Ranges", "Content-Length"]}})

    register_blueprints(app)
    register_socketio_events(socketio)
    socketio.init_app(app)
    limiter.init_app(app)



    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    # IMPORTANT: Gunicorn / Multi-Worker Deployment
    # Because this app uses Flask-SocketIO with eventlet and DOES NOT use a message queue
    # (like Redis) for pub/sub, it MUST be run with exactly 1 worker process (-w 1).
    # If run with multiple workers, Socket.IO sessions will drop and background 
    # tasks (like pyannote warmup and periodic recovery) will run redundantly across processes.
    import os
    is_reloader_process = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    is_flask_debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    
    # Only initialize background tasks once per process.
    # If running with Flask debug reloader, only initialize in the actual worker process.
    global _PROCESS_INITIALIZED
    should_initialize = not _PROCESS_INITIALIZED
    if is_flask_debug and not is_reloader_process:
        should_initialize = False

    if should_initialize:
        _PROCESS_INITIALIZED = True

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

        # Whisper and Pyannote models are intentionally lazy-loaded.
        # Warming them up via threading.Thread under Eventlet blocks the event loop
        # and hangs the application (including login) for 10-15s during startup.

        def periodic_recovery_loop():
            while True:
                time.sleep(600)  # 10 minutes
                logger.info("Running periodic stale session recovery...")
                db = None
                try:
                    from .services.persistence.session_repository import recover_stale_sessions
                    from .db.session import SessionLocal
                    db = SessionLocal()
                    recovered = recover_stale_sessions(db, include_recording=False)
                    if recovered > 0:
                        logger.info(f"Periodic recovery completed. Recovered={recovered}")
                except Exception as e:
                    logger.error(f"Periodic recovery failed: {e}")
                finally:
                    if db is not None:
                        db.close()

        threading.Thread(
            target=periodic_recovery_loop,
            daemon=True,
        ).start()

        def handle_shutdown(signum, frame):
            logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
            from .services.transcription.streaming import session_manager
            for sid, session in list(session_manager.active_sessions.items()):
                session.is_ending = True
            
            # Wait up to 10 seconds for worker loop to drain active sessions
            wait_seconds = 0
            while session_manager.active_sessions and wait_seconds < 10:
                time.sleep(1.0)
                wait_seconds += 1
                
            logger.info("Active sessions drained. Shutting down thread pool...")
            from .workers.realtime.worker_state import inference_executor
            inference_executor.shutdown(wait=True)
            
            logger.info("Shutdown complete.")
            sys.exit(0)

        # only register signal handler in main thread
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGTERM, handle_shutdown)
            signal.signal(signal.SIGINT, handle_shutdown)

    return app


if __name__ == "__main__":
    app = create_app()
    import os
    is_debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    socketio.run(app, host="0.0.0.0", port=5000, debug=is_debug)