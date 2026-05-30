from backend.app.models.enums import SessionStatus
from backend.app.services.persistence.session_repository import create_session
from backend.app.services.persistence.speaker_repository import get_or_create_speaker


def test_get_or_create_speaker(db_session):
    session = create_session(db_session, session_type="upload", status=SessionStatus.PENDING)
    speaker = get_or_create_speaker(
        db_session, session_id=session.id, speaker_label="SPEAKER_00"
    )
    second = get_or_create_speaker(
        db_session, session_id=session.id, speaker_label="SPEAKER_00"
    )

    assert speaker.id == second.id


def test_get_or_create_speaker_normalizes_blank_labels(db_session):
    session = create_session(db_session, session_type="upload", status=SessionStatus.PENDING)
    speaker = get_or_create_speaker(db_session, session_id=session.id, speaker_label="  ")

    assert speaker.speaker_label == "UNKNOWN"
