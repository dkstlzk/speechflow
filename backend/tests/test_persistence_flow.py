from backend.app.models.enums import SessionStatus
from backend.app.models.transcript_chunk import TranscriptChunk
from backend.app.services.persistence.session_repository import create_session
from backend.app.services.persistence.transcript_repository import bulk_insert_chunks


def test_transcript_persistence_ordering(db_session):
    session = create_session(db_session, session_type="upload", status=SessionStatus.PENDING)

    chunks = [
        {
            "session_id": session.id,
            "speaker_id": None,
            "start_time": 1.0,
            "end_time": 2.0,
            "text": "second",
            "chunk_index": 1,
            "is_partial": False,
        },
        {
            "session_id": session.id,
            "speaker_id": None,
            "start_time": 0.0,
            "end_time": 1.0,
            "text": "first",
            "chunk_index": 0,
            "is_partial": False,
        },
    ]

    bulk_insert_chunks(db_session, chunks)

    ordered = (
        db_session.query(TranscriptChunk)
        .filter(TranscriptChunk.session_id == session.id)
        .order_by(TranscriptChunk.chunk_index)
        .all()
    )

    assert [chunk.text for chunk in ordered] == ["first", "second"]
