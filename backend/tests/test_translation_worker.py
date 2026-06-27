from unittest.mock import MagicMock, patch

from backend.app.models.translation import TranslatedChunk
from backend.app.services.summarization.ollama import OllamaClientError
from backend.app.workers.translation_worker import process_translation


@patch("backend.app.workers.translation_worker.SessionLocal")
@patch("backend.app.workers.translation_worker.TranslationService")
@patch("backend.app.workers.translation_worker.get_summary")
def test_translation_worker_exception(mock_get_summary, mock_translation_service, mock_session_local):
    """Test that translation worker gracefully handles and persists LLM exceptions."""
    mock_db = MagicMock()
    mock_get_summary.return_value = None
    mock_session_local.return_value = mock_db
    
    mock_translation = MagicMock(status="translating")
    
    # We need to distinguish between db.query(SessionTranslation) and db.query(TranscriptChunk)
    # The worker first calls db.query(SessionTranslation).filter().first()
    # Then db.query(TranscriptChunk).filter().order_by().all()
    
    def side_effect_query(model):
        query_mock = MagicMock()
        if model.__name__ == "Session":
            query_mock.filter.return_value.first.return_value = MagicMock(id=1, transcript_type="conversation")
        elif model.__name__ == "SessionTranslation":
            query_mock.filter.return_value.first.return_value = mock_translation
        elif model.__name__ == "TranscriptChunk":
            mock_chunk = MagicMock(id=1, text="Hello world")
            query_mock.filter.return_value.order_by.return_value.all.return_value = [mock_chunk]
        return query_mock
    
    mock_db.query.side_effect = side_effect_query
    
    # Force TranslationService to raise an error
    mock_translator = MagicMock()
    mock_translator.translate_chunks.side_effect = OllamaClientError("LLM unavailable")
    mock_translation_service.return_value = mock_translator
    
    # Must not raise the exception up to the worker process level
    process_translation(session_id=1, target_language="hi")
    
    assert mock_translation.status == "failed"
    assert "LLM unavailable" in mock_translation.error_message
    assert mock_db.commit.called


@patch("backend.app.workers.translation_worker.SessionLocal")
@patch("backend.app.workers.translation_worker.TranslationService")
def test_translation_malformed_json(mock_translation_service, mock_session_local):
    """Test translation worker handles malformed JSON chunk output by falling back correctly."""
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    mock_translation = MagicMock(status="translating", id=10)
    
    def side_effect_query(model):
        query_mock = MagicMock()
        if model.__name__ == "Session":
            query_mock.filter.return_value.first.return_value = MagicMock(id=1)
        elif model.__name__ == "SessionTranslation":
            query_mock.filter.return_value.first.return_value = mock_translation
        elif model.__name__ == "TranscriptChunk":
            mock_chunk = MagicMock(id=101, text="Hello world")
            query_mock.filter.return_value.order_by.return_value.all.return_value = [mock_chunk]
        return query_mock
        
    mock_db.query.side_effect = side_effect_query
    
    mock_translator = MagicMock()
    # Return empty list simulating failed JSON parse
    mock_translator.translate_chunks.return_value = []
    mock_translation_service.return_value = mock_translator
    
    process_translation(session_id=1, target_language="hi")
    
    # We should not insert any translated chunks
    added_objects = mock_db.add_all.call_args_list
    if added_objects:
        for call in added_objects:
            assert not any(isinstance(obj, TranslatedChunk) for obj in call[0][0])


@patch("backend.app.workers.translation_worker.SessionLocal")
@patch("backend.app.workers.translation_worker.TranslationService")
def test_translation_duplicate_request(mock_translation_service, mock_session_local):
    """Test translation worker exits early if status is already completed."""
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    mock_translation = MagicMock(status="completed")
    
    def side_effect_query(model):
        query_mock = MagicMock()
        if model.__name__ == "Session":
            query_mock.filter.return_value.first.return_value = MagicMock(id=1, transcript_type="conversation")
        elif model.__name__ == "SessionTranslation":
            query_mock.filter.return_value.first.return_value = mock_translation
        return query_mock
        
    mock_db.query.side_effect = side_effect_query
    
    process_translation(session_id=1, target_language="hi")
    
    # Should exit before doing translation
    assert not mock_translation_service.called
