from typing import Dict, List

from ...db.session import SessionLocal
from .transcript_repository import bulk_insert_chunks


def save_transcript_chunks(session_id: int, chunks: List[Dict]) -> None:
    """Persist transcript chunks with chunk_index ordering."""
    payloads = []
    for chunk in chunks:
        payload = dict(chunk)
        payload.setdefault("session_id", session_id)
        if payload["session_id"] != session_id:
            raise ValueError("chunk session_id does not match save target session_id")
        payloads.append(payload)

    db = SessionLocal()
    try:
        bulk_insert_chunks(db, payloads)
    finally:
        db.close()


def save_transcript_segments(session_id: int, segments: List[Dict]) -> None:
    """Persist normalized transcript segments for a session."""
    payloads = [
        {
            "session_id": session_id,
            "speaker_id": None,
            "start_time": segment["start"],
            "end_time": segment["end"],
            "text": segment["text"],
            "chunk_index": segment["order"],
            "is_partial": False,
        }
        for segment in segments
    ]
    save_transcript_chunks(session_id, payloads)
