from backend.app.models.enums import SessionStatus
from backend.app.services.persistence.speaker_repository import get_or_create_speaker
from backend.app.services.persistence.session_repository import create_session
from backend.app.services.persistence.transcript_repository import bulk_insert_chunks
from backend.app.services.session.session_service import get_session_transcript


def test_transcript_retrieval_service_orders_chunks(db_session):
    session = create_session(db_session, session_type="upload", status=SessionStatus.PENDING)
    speaker = get_or_create_speaker(db_session, session.id, "SPEAKER_00")

    chunks = [
        {
            "session_id": session.id,
            "speaker_id": speaker.id,
            "start_time": 1.0,
            "end_time": 2.0,
            "text": "world",
            "chunk_index": 1,
            "is_partial": False,
        },
        {
            "session_id": session.id,
            "speaker_id": speaker.id,
            "start_time": 0.0,
            "end_time": 1.0,
            "text": "hello",
            "chunk_index": 0,
            "is_partial": False,
        },
    ]

    bulk_insert_chunks(db_session, chunks)

    payload = get_session_transcript(session.id)

    assert payload["session_id"] == str(session.id)
    assert payload["transcript"][0]["text"] == "hello"
    assert payload["transcript"][1]["text"] == "world"
    assert payload["transcript"][0]["speaker"] == "SPEAKER_00"


def test_transcript_retrieval_endpoint_returns_ordered_transcript(client, db_session):
    session = create_session(db_session, session_type="upload", status=SessionStatus.COMPLETED)
    speaker_a = get_or_create_speaker(db_session, session.id, "SPEAKER_00")
    speaker_b = get_or_create_speaker(db_session, session.id, "SPEAKER_01")

    bulk_insert_chunks(
        db_session,
        [
            {
                "session_id": session.id,
                "speaker_id": speaker_b.id,
                "start_time": 1.0,
                "end_time": 2.0,
                "text": "second",
                "chunk_index": 1,
                "is_partial": False,
            },
            {
                "session_id": session.id,
                "speaker_id": speaker_a.id,
                "start_time": 0.0,
                "end_time": 1.0,
                "text": "first",
                "chunk_index": 0,
                "is_partial": False,
            },
        ],
    )

    response = client.get(f"/api/sessions/{session.id}/transcript")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["session_id"] == str(session.id)
    assert payload["data"]["status"] == SessionStatus.COMPLETED.value
    assert [chunk["text"] for chunk in payload["data"]["transcript"]] == ["first", "second"]
    assert [chunk["speaker"] for chunk in payload["data"]["transcript"]] == [
        "SPEAKER_00",
        "SPEAKER_01",
    ]


def test_transcript_retrieval_endpoint_invalid_session_id(client):
    response = client.get("/api/sessions/abc/transcript")
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False


def test_transcript_retrieval_endpoint_not_found(client):
    response = client.get("/api/sessions/999999/transcript")
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["success"] is False
