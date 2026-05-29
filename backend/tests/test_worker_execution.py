from dataclasses import dataclass
from pathlib import Path

from backend.app.models.enums import SessionStatus
from backend.app.models.session import Session
from backend.app.models.transcript_chunk import TranscriptChunk
from backend.app.services.persistence.session_repository import create_session
from backend.app.workers.transcription_worker import process_upload_session


@dataclass
class DummySegment:
    start: float
    end: float
    text: str
    order: int


class DummyPreprocessor:
    def preprocess(self, input_path: str) -> str:
        return input_path


class DummyTranscriber:
    def transcribe(self, _audio_path):
        return type(
            "Result",
            (),
            {
                "segments": [
                    {"start": 0.0, "end": 1.0, "text": "hello", "order": 0},
                    {"start": 1.0, "end": 2.0, "text": "world", "order": 1},
                ]
            },
        )()


def test_worker_processes_session(db_session, tmp_path):
    session = create_session(db_session, session_type="upload", status=SessionStatus.PENDING)
    temp_file = Path(tmp_path / "input.wav")
    temp_file.write_bytes(b"dummy")

    process_upload_session(
        session_id=session.id,
        file_path=str(temp_file),
        preprocessor=DummyPreprocessor(),
        transcriber=DummyTranscriber(),
        db_session=db_session,
    )

    refreshed = db_session.get(Session, session.id)
    assert refreshed.status == SessionStatus.COMPLETED

    chunks = (
        db_session.query(TranscriptChunk)
        .filter(TranscriptChunk.session_id == session.id)
        .order_by(TranscriptChunk.chunk_index)
        .all()
    )

    assert [chunk.text for chunk in chunks] == ["hello", "world"]
