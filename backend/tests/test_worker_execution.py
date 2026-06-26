from dataclasses import dataclass
from pathlib import Path

from backend.app.models.enums import SessionStatus
from backend.app.models.session import Session
from backend.app.models.transcript_chunk import TranscriptChunk
from backend.app.services.persistence.session_repository import create_session
from backend.app.services.persistence.session_repository import (
    update_session_status as update_session_status_record,
)
from backend.app.workers import transcription_worker as worker_module
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
                ],
                "language": "en"
            },
        )()


class DummyDiarizer:
    def diarize(self, _audio_path):
        return [
            {"speaker": "SPEAKER_00", "start": 0.0, "end": 1.2},
            {"speaker": "SPEAKER_01", "start": 1.2, "end": 2.2},
        ]


class FailingTranscriber:
    def transcribe(self, _audio_path):
        raise RuntimeError("transcription crashed")


class SequentialTranscriber:
    def __init__(self):
        self.calls = 0

    def transcribe(self, _audio_path):
        self.calls += 1
        text = f"pass-{self.calls}"
        return type(
            "Result",
            (),
            {
                "segments": [
                    {"start": 0.0, "end": 1.0, "text": text, "order": 0},
                ],
                "language": "en"
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
        diarizer=DummyDiarizer(),
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
    assert chunks[0].speaker is not None


def test_worker_failure_sets_failed_status_and_cleans_files(db_session, tmp_path):
    session = create_session(db_session, session_type="upload", status=SessionStatus.PENDING)
    temp_file = Path(tmp_path / "broken.wav")
    temp_file.write_bytes(b"dummy")

    process_upload_session(
        session_id=session.id,
        file_path=str(temp_file),
        preprocessor=DummyPreprocessor(),
        transcriber=FailingTranscriber(),
        diarizer=DummyDiarizer(),
        db_session=db_session,
    )

    refreshed = db_session.get(Session, session.id)
    assert refreshed.status == SessionStatus.FAILED
    assert "transcription crashed" in (refreshed.processing_error or "")
    assert not temp_file.exists()


def test_worker_lifecycle_transitions_are_consistent(db_session, tmp_path, monkeypatch):
    transitions = []

    def tracking_update_status(db, session_id, status, error=None):
        transitions.append(status.value)
        return update_session_status_record(db, session_id, status, error=error)

    monkeypatch.setattr(worker_module, "update_session_status", tracking_update_status)

    session = create_session(db_session, session_type="upload", status=SessionStatus.PENDING)
    temp_file = Path(tmp_path / "lifecycle.wav")
    temp_file.write_bytes(b"dummy")

    process_upload_session(
        session_id=session.id,
        file_path=str(temp_file),
        preprocessor=DummyPreprocessor(),
        transcriber=DummyTranscriber(),
        diarizer=DummyDiarizer(),
        db_session=db_session,
    )

    assert transitions == [
        SessionStatus.PREPROCESSING.value,
        SessionStatus.TRANSCRIBING.value,
        SessionStatus.DIARIZING.value,
        SessionStatus.PROCESSING.value,
        SessionStatus.COMPLETED.value,
    ]


def test_worker_rerun_replaces_existing_chunks(db_session, tmp_path):
    session = create_session(db_session, session_type="upload", status=SessionStatus.PENDING)
    transcriber = SequentialTranscriber()

    for idx in range(2):
        temp_file = Path(tmp_path / f"rerun-{idx}.wav")
        temp_file.write_bytes(b"dummy")
        process_upload_session(
            session_id=session.id,
            file_path=str(temp_file),
            preprocessor=DummyPreprocessor(),
            transcriber=transcriber,
            diarizer=DummyDiarizer(),
            db_session=db_session,
        )

    chunks = (
        db_session.query(TranscriptChunk)
        .filter(TranscriptChunk.session_id == session.id)
        .order_by(TranscriptChunk.chunk_index)
        .all()
    )

    assert len(chunks) == 1
    assert chunks[0].text == "pass-2"
