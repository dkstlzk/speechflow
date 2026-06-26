from backend.app.services.transcription.streaming import session_manager
from backend.app.models.enums import SessionStatus
from backend.app.services.persistence.session_repository import create_session

def test_finalize_race_guard(client, db_session, mock_auth):
    # Set up a fake streaming session
    db_sess = create_session(db_session, "realtime", None, SessionStatus.RECORDING)
    session_manager.create_session("fake_sid", str(db_sess.id))
    
    response1 = client.post(f"/api/realtime/session/{db_sess.id}/finalize")
    assert response1.status_code == 200
    
    response2 = client.post(f"/api/realtime/session/{db_sess.id}/finalize")
    assert response2.status_code == 200
    assert response2.json["data"]["status"] in ["finalizing", "completed"]
