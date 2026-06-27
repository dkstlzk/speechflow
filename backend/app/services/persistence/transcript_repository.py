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
    if chunks:
        from sqlalchemy import insert

        db.execute(insert(TranscriptChunk), chunks)
    db.commit()


def replace_session_chunks(db: Session, session_id: int, chunks: List[Dict]) -> None:
    """Replace all transcript chunks for a session in one transaction."""
    (
        db.query(TranscriptChunk)
        .filter(TranscriptChunk.session_id == session_id)
        .delete(synchronize_session=False)
    )
    if chunks:
        from sqlalchemy import insert

        db.execute(insert(TranscriptChunk), chunks)

        # Cleanup any orphaned speakers for this session that no longer have chunks
        # (e.g., if a speaker was renamed during a previous diarization run)
        from ...models.speaker import Speaker

        db.query(Speaker).filter(
            Speaker.session_id == session_id,
            ~Speaker.id.in_(
                db.query(TranscriptChunk.speaker_id).filter(
                    TranscriptChunk.session_id == session_id,
                    TranscriptChunk.speaker_id.isnot(None),
                )
            ),
        ).delete(synchronize_session=False)

    # Invalidate existing translations since the chunks have changed
    from ...models.translation import SessionTranslation, TranslatedChunk

    translations = db.query(SessionTranslation).filter(SessionTranslation.session_id == session_id).all()
    for t in translations:
        t.status = "invalidated"
        t.translated_summary = None
        t.translated_mom = None
        t.error_message = "This translation is outdated because the transcript changed."
        
        # Delete old translated chunks since they no longer align with the new transcript
        db.query(TranslatedChunk).filter(
            TranslatedChunk.translation_id == t.id
        ).delete(synchronize_session=False)

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


def update_chunk_speakers(db: Session, session_id: int, updates: List[Dict]) -> None:
    """Update speaker_id and speaker_source for existing chunks."""
    # We use bulk_update_mappings if we have the primary key (id) in the updates dict.
    # The updates dict should have: 'id', 'speaker_id', 'speaker_source'
    db.bulk_update_mappings(TranscriptChunk, updates)
    db.commit()
