"""Transcript repository for ORM access."""

from typing import Dict, List

from sqlalchemy.orm import Session

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
