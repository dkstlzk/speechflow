from typing import Dict, List

from ...db.session import SessionLocal
from .transcript_repository import bulk_insert_chunks


def save_transcript_chunks(session_id: int, chunks: List[Dict]) -> None:
    """Persist transcript chunks with chunk_index ordering."""
    db = SessionLocal()
    try:
        bulk_insert_chunks(db, chunks)
    finally:
        db.close()
