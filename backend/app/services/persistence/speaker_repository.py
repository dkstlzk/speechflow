"""Speaker repository for ORM access."""

from sqlalchemy.orm import Session

from ...models.speaker import Speaker


def get_or_create_speaker(db: Session, session_id: int, speaker_label: str) -> Speaker:
    normalized_label = (speaker_label or "UNKNOWN").strip() or "UNKNOWN"
    speaker = (
        db.query(Speaker)
        .filter(
            Speaker.session_id == session_id,
            Speaker.speaker_label == normalized_label,
        )
        .first()
    )
    if speaker:
        return speaker

    speaker = Speaker(session_id=session_id, speaker_label=normalized_label)
    db.add(speaker)
    db.commit()
    db.refresh(speaker)
    return speaker


def update_speaker_display_name(
    db: Session, session_id: int, speaker_label: str, display_name: str
) -> Speaker:
    normalized_label = (speaker_label or "UNKNOWN").strip() or "UNKNOWN"
    speaker = (
        db.query(Speaker)
        .filter(
            Speaker.session_id == session_id,
            Speaker.speaker_label == normalized_label,
        )
        .first()
    )
    if not speaker:
        speaker = Speaker(session_id=session_id, speaker_label=normalized_label)
        db.add(speaker)

    speaker.display_name = display_name.strip() if display_name else None
    db.commit()
    db.refresh(speaker)
    return speaker
