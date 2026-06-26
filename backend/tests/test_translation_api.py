from backend.app.services.persistence.session_repository import create_session
from backend.app.models.translation import SessionTranslation

def test_translation_create(client, db_session, mock_auth, monkeypatch):
    session = create_session(db_session, "test_file.wav", "test_file.wav")
    db_session.commit()
    
    # Mock multiprocessing to avoid actually spawning a worker in tests
    class MockProcess:
        def __init__(self, target, args):
            pass
        def start(self):
            pass
    monkeypatch.setattr("multiprocessing.context.SpawnContext.Process", MockProcess)

    response = client.post(
        f"/api/sessions/{session.id}/translate",
        json={"target_language": "hindi"}
    )
    assert response.status_code == 202
    assert response.json["data"]["message"] == "Translation started"
    
    translation = db_session.query(SessionTranslation).filter_by(session_id=session.id).first()
    assert translation is not None
    assert translation.status == "translating"
    assert translation.target_language == "hindi"

def test_translation_already_running(client, db_session, mock_auth, monkeypatch):
    session = create_session(db_session, "test_file.wav", "test_file.wav")
    db_session.commit()
    
    translation = SessionTranslation(
        session_id=session.id,
        target_language="hindi",
        status="translating"
    )
    db_session.add(translation)
    db_session.commit()

    response = client.post(
        f"/api/sessions/{session.id}/translate",
        json={"target_language": "hindi"}
    )
    assert response.status_code == 202
    assert response.json["data"]["message"] == "Translation already in progress"

def test_translation_retry(client, db_session, mock_auth, monkeypatch):
    session = create_session(db_session, "test_file.wav", "test_file.wav")
    db_session.commit()
    
    translation = SessionTranslation(
        session_id=session.id,
        target_language="hindi",
        status="failed",
        error_message="Connection lost"
    )
    db_session.add(translation)
    db_session.commit()
    
    class MockProcess:
        def __init__(self, target, args):
            pass
        def start(self):
            pass
    monkeypatch.setattr("multiprocessing.context.SpawnContext.Process", MockProcess)

    response = client.post(
        f"/api/sessions/{session.id}/translate",
        json={"target_language": "hindi"}
    )
    assert response.status_code == 202
    assert response.json["data"]["message"] == "Translation started"
    
    # Verify status changed to translating and error cleared
    db_session.refresh(translation)
    assert translation.status == "translating"
    assert translation.error_message is None
