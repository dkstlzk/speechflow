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
_REQUIRED_ENUM_VALUES = list(
    set([s.name for s in SessionStatus] + [s.value for s in SessionStatus])
)


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

    if inspector.has_table("sessions"):
        columns = {col["name"] for col in inspector.get_columns("sessions")}
        if "title" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE sessions ADD COLUMN title VARCHAR(255)"))
                conn.commit()
                logger.info("Added 'title' column to sessions table")

        if "audio_path" not in columns:
            with engine.connect() as conn:
                conn.execute(
                    text("ALTER TABLE sessions ADD COLUMN audio_path VARCHAR(512)")
                )
                conn.commit()
                logger.info("Added 'audio_path' column to sessions table")

        if "diarization_mode" not in columns:
            with engine.connect() as conn:
                conn.execute(
                    text("ALTER TABLE sessions ADD COLUMN diarization_mode VARCHAR(32)")
                )
                conn.commit()
                logger.info("Added 'diarization_mode' column to sessions table")

        if "diarized_at" not in columns:
            with engine.connect() as conn:
                conn.execute(
                    text("ALTER TABLE sessions ADD COLUMN diarized_at TIMESTAMP")
                )
                conn.commit()
                logger.info("Added 'diarized_at' column to sessions table")

        if "detected_language" not in columns:
            with engine.connect() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE sessions ADD COLUMN detected_language VARCHAR(10)"
                    )
                )
                conn.commit()
                logger.info("Added 'detected_language' column to sessions table")

        if "host_name" not in columns:
            with engine.connect() as conn:
                conn.execute(
                    text("ALTER TABLE sessions ADD COLUMN host_name VARCHAR(255)")
                )
                conn.commit()
                logger.info("Added 'host_name' column to sessions table")

        if "sample_rate" not in columns:
            with engine.connect() as conn:
                conn.execute(
                    text("ALTER TABLE sessions ADD COLUMN sample_rate INTEGER")
                )
                conn.commit()
                logger.info("Added 'sample_rate' column to sessions table")

        if "participants" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE sessions ADD COLUMN participants TEXT"))
                conn.commit()
                logger.info("Added 'participants' column to sessions table")

    if inspector.has_table("transcript_chunks"):
        chunk_cols = {col["name"] for col in inspector.get_columns("transcript_chunks")}
        if "speaker_source" not in chunk_cols:
            with engine.connect() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE transcript_chunks ADD COLUMN speaker_source VARCHAR(20)"
                    )
                )
                conn.commit()
                logger.info("Added 'speaker_source' column to transcript_chunks table")


def ensure_foreign_key_cascades(engine: Engine) -> None:
    """Ensure foreign keys on child tables have ON DELETE CASCADE/SET NULL."""
    if engine.dialect.name != "postgresql":
        return

    expected_rules = {
        "transcript_chunks_session_id_fkey": "c",  # CASCADE
        "transcript_chunks_speaker_id_fkey": "n",  # SET NULL
        "action_items_session_id_fkey": "c",
        "session_summaries_session_id_fkey": "c",
        "speakers_session_id_fkey": "c",
    }

    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT conname, confdeltype FROM pg_constraint WHERE conname = ANY(:names)"
            ),
            {"names": list(expected_rules.keys())},
        )
        existing_rules = {row[0]: row[1] for row in result}

        queries = []

        # transcript_chunks
        if existing_rules.get("transcript_chunks_session_id_fkey") != "c":
            queries.extend(
                [
                    "ALTER TABLE transcript_chunks DROP CONSTRAINT IF EXISTS transcript_chunks_session_id_fkey;",
                    "ALTER TABLE transcript_chunks ADD CONSTRAINT transcript_chunks_session_id_fkey FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE;",
                ]
            )
        if existing_rules.get("transcript_chunks_speaker_id_fkey") != "n":
            queries.extend(
                [
                    "ALTER TABLE transcript_chunks DROP CONSTRAINT IF EXISTS transcript_chunks_speaker_id_fkey;",
                    "ALTER TABLE transcript_chunks ADD CONSTRAINT transcript_chunks_speaker_id_fkey FOREIGN KEY (speaker_id) REFERENCES speakers (id) ON DELETE SET NULL;",
                ]
            )

        # action_items
        if existing_rules.get("action_items_session_id_fkey") != "c":
            queries.extend(
                [
                    "ALTER TABLE action_items DROP CONSTRAINT IF EXISTS action_items_session_id_fkey;",
                    "ALTER TABLE action_items ADD CONSTRAINT action_items_session_id_fkey FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE;",
                ]
            )

        # session_summaries
        if existing_rules.get("session_summaries_session_id_fkey") != "c":
            queries.extend(
                [
                    "ALTER TABLE session_summaries DROP CONSTRAINT IF EXISTS session_summaries_session_id_fkey;",
                    "ALTER TABLE session_summaries ADD CONSTRAINT session_summaries_session_id_fkey FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE;",
                ]
            )

        # speakers
        if existing_rules.get("speakers_session_id_fkey") != "c":
            queries.extend(
                [
                    "ALTER TABLE speakers DROP CONSTRAINT IF EXISTS speakers_session_id_fkey;",
                    "ALTER TABLE speakers ADD CONSTRAINT speakers_session_id_fkey FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE;",
                ]
            )

        if queries:
            for q in queries:
                conn.execute(text(q))
            conn.commit()
            logger.info("Ensured ON DELETE CASCADE for all session child tables")


def ensure_unique_constraints(engine: Engine) -> None:
    """Ensure unique constraints exist."""
    if engine.dialect.name != "postgresql":
        return

    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT conname FROM pg_constraint WHERE conname = 'uix_session_chunk'"
            )
        )
        if result.fetchone() is None:
            conn.execute(
                text(
                    "ALTER TABLE transcript_chunks ADD CONSTRAINT uix_session_chunk UNIQUE (session_id, chunk_index)"
                )
            )
            conn.commit()
            logger.info(
                "Added unique constraint uix_session_chunk to transcript_chunks"
            )


def ensure_fts_indexes(engine: Engine) -> None:
    """Add Full Text Search generated columns and GIN indexes for PostgreSQL."""
    if engine.dialect.name != "postgresql":
        return

    inspector = inspect(engine)
    with engine.connect() as conn:
        # Transcript chunks FTS
        if inspector.has_table("transcript_chunks"):
            chunk_cols = {c["name"] for c in inspector.get_columns("transcript_chunks")}
            if "search_vector" not in chunk_cols:
                conn.execute(
                    text(
                        "ALTER TABLE transcript_chunks ADD COLUMN search_vector tsvector GENERATED ALWAYS AS (to_tsvector('simple', text)) STORED"
                    )
                )
                logger.info("Added FTS column to transcript_chunks")

            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS transcript_chunks_search_idx ON transcript_chunks USING GIN(search_vector)"
                )
            )

        # Sessions FTS
        if inspector.has_table("sessions"):
            session_cols = {c["name"] for c in inspector.get_columns("sessions")}
            if "search_vector" not in session_cols:
                conn.execute(
                    text(
                        "ALTER TABLE sessions ADD COLUMN search_vector tsvector GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(original_filename, ''))) STORED"
                    )
                )
                logger.info("Added FTS column to sessions")

            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS sessions_search_idx ON sessions USING GIN(search_vector)"
                )
            )

        conn.commit()


def ensure_translation_table(engine: Engine) -> None:
    """Ensure the session_translations table exists."""
    inspector = inspect(engine)
    if not inspector.has_table("session_translations"):
        with engine.connect() as conn:
            conn.execute(
                text("""
                CREATE TABLE session_translations (
                    id SERIAL PRIMARY KEY,
                    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    target_language VARCHAR(10) NOT NULL,
                    translated_transcript TEXT,
                    translated_summary TEXT,
                    translated_mom TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'translating',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uix_session_translation_language UNIQUE (session_id, target_language)
                )
            """)
            )
            conn.commit()
            logger.info("Created session_translations table")


def run_migrations(engine: Engine) -> None:
    """Run all additive migrations. Safe to call on every startup."""
    try:
        ensure_enum_values(engine)
    except Exception as e:
        logger.warning(f"ensure_enum_values failed (non-fatal): {e}")

    try:
        ensure_columns(engine)
    except Exception as e:
        logger.warning(f"ensure_columns failed (non-fatal): {e}")

    try:
        ensure_foreign_key_cascades(engine)
    except Exception as e:
        logger.warning(f"ensure_foreign_key_cascades failed (non-fatal): {e}")

    try:
        ensure_unique_constraints(engine)
    except Exception as e:
        logger.warning(f"ensure_unique_constraints failed (non-fatal): {e}")

    try:
        ensure_fts_indexes(engine)
    except Exception as e:
        logger.warning(f"ensure_fts_indexes failed (non-fatal): {e}")

    try:
        ensure_translation_table(engine)
    except Exception as e:
        logger.warning(f"ensure_translation_table failed (non-fatal): {e}")
