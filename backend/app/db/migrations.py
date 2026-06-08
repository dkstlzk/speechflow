"""Lightweight schema migration helpers.

Handles additive changes that SQLAlchemy's create_all() cannot manage,
such as adding new values to an existing PostgreSQL ENUM type or adding
new columns to existing tables.
"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from ..config.logging import get_logger
from ..models.enums import SessionStatus

logger = get_logger("migrations")

# Values that may be missing from the session_status enum in older DBs
_REQUIRED_ENUM_VALUES = list(set([s.name for s in SessionStatus] + [s.value for s in SessionStatus]))


def ensure_enum_values(engine: Engine) -> None:
    """Add any missing values to the session_status PostgreSQL enum type."""
    with engine.connect() as conn:
        # Check if it's PostgreSQL (skip for SQLite, etc.)
        if engine.dialect.name != "postgresql":
            return

        result = conn.execute(
            text("SELECT unnest(enum_range(NULL::session_status))::text")
        )
        existing = {row[0] for row in result}

        for value in _REQUIRED_ENUM_VALUES:
            if value not in existing:
                conn.execute(
                    text(f"ALTER TYPE session_status ADD VALUE IF NOT EXISTS '{value}'")
                )
                logger.info(f"Added enum value '{value}' to session_status")

        conn.commit()


def ensure_columns(engine: Engine) -> None:
    """Add any missing columns to existing tables."""
    inspector = inspect(engine)

    if engine.dialect.name != "postgresql":
        return

    # Check for sessions.title column
    if inspector.has_table("sessions"):
        columns = {col["name"] for col in inspector.get_columns("sessions")}
        if "title" not in columns:
            with engine.connect() as conn:
                conn.execute(
                    text("ALTER TABLE sessions ADD COLUMN title VARCHAR(255)")
                )
                conn.commit()
                logger.info("Added 'title' column to sessions table")


def run_migrations(engine: Engine) -> None:
    """Run all additive migrations. Safe to call on every startup."""
    try:
        ensure_enum_values(engine)
        ensure_columns(engine)
    except Exception as e:
        logger.warning(f"Migration helper encountered an error (non-fatal): {e}")
