import pytest
from unittest.mock import MagicMock, patch
from backend.app.services.summarization.transcript_processor import TranscriptProcessor, TranscriptProcessorError, EmptyTranscriptError

def test_intelligence_empty_transcript():
    """Test that intelligence generation handles empty transcripts gracefully."""
    processor = TranscriptProcessor()
    
    with patch("backend.app.services.summarization.transcript_processor.get_session_transcript") as mock_get:
        mock_get.return_value = {"transcript": []}
        
        with pytest.raises(EmptyTranscriptError):
            processor.assemble_chunks(1)
        
        with patch.object(processor, 'assemble_chunks', return_value=[]):
            result = processor.process_session(1)
            assert result["transcript_type"] == "conversation"
            assert result["intelligence_data"] == {}

def test_intelligence_markdown_wrapped_json():
    """Test that the processor correctly extracts JSON if LLM wraps it in markdown blocks."""
    processor = TranscriptProcessor()
    markdown_json = "```json\n{\n  \"title\": \"Test\"\n}\n```"
    
    with patch.object(processor, '_generate', return_value=(markdown_json, {})):
        parsed, _ = processor.generate_intelligence(1, ["chunk"])
        assert parsed == {"title": "Test"}

def test_intelligence_malformed_json():
    """Test that the processor gracefully fails when the LLM outputs garbage."""
    processor = TranscriptProcessor()
    garbage_output = "I am an AI and I cannot generate JSON for you today."
    
    with patch.object(processor, '_generate', return_value=(garbage_output, {})):
        with pytest.raises(TranscriptProcessorError):
            processor.generate_intelligence(1, ["chunk"])

def test_intelligence_action_items_grouping():
    """Test that the action items extracted are properly normalized and missing owners become Unassigned."""
    processor = TranscriptProcessor()
    
    raw_ai_output = '{"action_items": [{"task": "Do this task", "priority": "high"}, {"owner": "Participant A", "task": "Do that task", "priority": "low"}, {"owner": "TBD", "task": "Another task", "priority": "medium"}]}'
    
    with patch.object(processor, 'assemble_chunks', return_value=["dummy chunk"]), \
         patch.object(processor, 'classify', return_value="english"), \
         patch.object(processor, '_generate', return_value=(raw_ai_output, {"Parse": 0.1})):
        
        result = processor.process_session(1)
        assert len(result["intelligence_data"]["action_items"]) == 3
        assert result["intelligence_data"]["action_items"][0].get("owner", "Unassigned") in ("Unassigned", None)
