"""Transcript repository for ORM access."""

from typing import Dict, List

from sqlalchemy.orm import Session, joinedload

from ...models.transcript_chunk import TranscriptChunk


def create_transcript_chunk(db: Session, payload: Dict) -> TranscriptChunk:
    """Persist a single transcript chunk."""
    chunk = TranscriptChunk(**payload)
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def bulk_insert_chunks(db: Session, chunks: List[Dict]) -> None:
    """Bulk insert transcript chunks."""
    db.bulk_insert_mappings(TranscriptChunk, chunks)
    db.commit()


def replace_session_chunks(db: Session, session_id: int, chunks: List[Dict]) -> None:
    """Replace all transcript chunks for a session in one transaction."""
    (
        db.query(TranscriptChunk)
        .filter(TranscriptChunk.session_id == session_id)
        .delete(synchronize_session=False)
    )
    if chunks:
        db.bulk_insert_mappings(TranscriptChunk, chunks)
    db.commit()


def list_transcript_chunks(db: Session, session_id: int) -> List[TranscriptChunk]:
    """Return transcript chunks with deterministic ordering for reconstruction."""
    return (
        db.query(TranscriptChunk)
        .options(joinedload(TranscriptChunk.speaker))
        .filter(TranscriptChunk.session_id == session_id)
        .order_by(
            TranscriptChunk.chunk_index,
            TranscriptChunk.start_time,
            TranscriptChunk.end_time,
            TranscriptChunk.id,
        )
        .all()
    )
