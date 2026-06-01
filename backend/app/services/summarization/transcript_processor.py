"""Transcript processing service for summarization outputs."""

from typing import List, Optional

from ...config.logging import get_logger
from ...services.session.session_service import get_session_transcript
from .ollama import OllamaClient, OllamaClientError
from .prompts import ACTION_ITEMS_PROMPT, MOM_PROMPT, SUMMARY_PROMPT

logger = get_logger("summarization")


class TranscriptProcessorError(RuntimeError):
    """Base error for transcript processing failures."""


class TranscriptNotFoundError(TranscriptProcessorError):
    """Raised when the session transcript cannot be found."""


class EmptyTranscriptError(TranscriptProcessorError):
    """Raised when the transcript has no usable content."""


class TranscriptGenerationError(TranscriptProcessorError):
    """Raised when generation fails for a transcript output."""


class TranscriptProcessor:
    """Assemble transcripts and request LLM outputs."""

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        model: str = "phi3:mini",
    ) -> None:
        self._client = ollama_client or OllamaClient()
        self._model = model

    def assemble_transcript(self, session_id: int) -> str:
        payload = get_session_transcript(session_id)
        if payload is None:
            raise TranscriptNotFoundError(f"Session {session_id} not found")

        entries = payload.get("transcript") or []
        if not entries:
            raise EmptyTranscriptError(
                f"Session {session_id} has no transcript chunks"
            )

        lines: List[str] = []
        for entry in entries:
            text = (entry.get("text") or "").strip()
            if not text:
                continue
            speaker = (entry.get("speaker") or "UNKNOWN").strip() or "UNKNOWN"
            lines.append(f"{speaker}: {text}")

        if not lines:
            raise EmptyTranscriptError(
                f"Session {session_id} has no usable transcript text"
            )

        assembled = "\n".join(lines)
        logger.info(
            "Assembled transcript",
            extra={
                "session_id": session_id,
                "line_count": len(lines),
                "char_count": len(assembled),
            },
        )
        return assembled

    def generate_summary(self, session_id: int) -> str:
        return self._generate(session_id, SUMMARY_PROMPT, "summary")

    def generate_mom(self, session_id: int) -> str:
        return self._generate(session_id, MOM_PROMPT, "mom")

    def generate_action_items(self, session_id: int) -> str:
        return self._generate(session_id, ACTION_ITEMS_PROMPT, "action_items")

    def _generate(self, session_id: int, template: str, output_type: str) -> str:
        transcript = self.assemble_transcript(session_id)
        prompt = template.format(transcript=transcript)
        try:
            return self._client.generate(prompt, model=self._model)
        except OllamaClientError as exc:
            logger.exception(
                "Ollama generation failed",
                extra={
                    "session_id": session_id,
                    "model": self._model,
                    "output_type": output_type,
                },
            )
            raise TranscriptGenerationError(
                f"Ollama generation failed for {output_type}"
            ) from exc
