import pytest
from unittest.mock import MagicMock, patch
from backend.app.services.persistence.session_repository import recover_stale_sessions
from backend.app.models.enums import SessionStatus

@patch("backend.app.services.persistence.session_repository.get_logger")
def test_session_recovery_after_exception(mock_get_logger):
    """Test that stale sessions are properly marked as FAILED."""
    mock_db = MagicMock()
    
    # Mock a session that is stuck
    mock_session = MagicMock()
    mock_session.id = 443
    mock_session.status = SessionStatus.FINALIZING
    mock_session.error_message = None
    
    # Setup query to return the stuck session
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_session]
    
    # We will call recover_stale_sessions directly
    recovered = recover_stale_sessions(mock_db, include_recording=True)
    
    # Assert the session was marked as FAILED with an appropriate error
    assert mock_session.status == SessionStatus.FAILED
    assert mock_session.error_message is not None
    assert "recovery" in mock_session.error_message.lower() or "missing" in mock_session.error_message.lower()
    assert mock_db.commit.called
