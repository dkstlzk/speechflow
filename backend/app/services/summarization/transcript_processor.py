"""Transcript processing service for summarization outputs."""

from typing import List, Optional

from ...config.logging import get_logger
from ...services.session.session_service import get_session_transcript
from .classify import classify_transcript
from .ollama import OllamaClient, OllamaClientError
from .prompts import (
    ACTION_ITEMS_PROMPT,
    MOM_PROMPT,
    SUMMARY_PROMPT,
    SUMMARY_MERGE_PROMPT,
    MOM_MERGE_PROMPT,
    ACTION_ITEMS_MERGE_PROMPT,
)

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
        model: str = "qwen2.5:3b",
    ) -> None:
        self._client = ollama_client or OllamaClient()
        self._model = model

    def _normalize_speaker(
        self,
        speaker: str,
        speaker_map: dict[str, str],
    ) -> str:
        if speaker not in speaker_map:
            speaker_map[speaker] = f"Participant {chr(65 + len(speaker_map))}"
        return speaker_map[speaker]

    def assemble_chunks(self, session_id: int, max_chars: int = 8000) -> List[str]:
        payload = get_session_transcript(session_id)
        if payload is None:
            raise TranscriptNotFoundError(f"Session {session_id} not found")

        entries = payload.get("transcript") or []
        if not entries:
            raise EmptyTranscriptError(f"Session {session_id} has no transcript chunks")

        chunks: List[str] = []
        current_chunk_lines: List[str] = []
        current_length = 0
        speaker_map: dict[str, str] = {}

        for entry in entries:
            text = (entry.get("text") or "").strip()
            if not text:
                continue
            speaker = (entry.get("speaker") or "UNKNOWN").strip() or "UNKNOWN"

            normalized_speaker = self._normalize_speaker(
                speaker,
                speaker_map,
            )

            if speaker == "UNKNOWN":
                line = text
            else:
                line = f"{normalized_speaker}: {text}"
            line_len = len(line) + 1

            if current_chunk_lines and current_length + line_len > max_chars:
                chunks.append("\n".join(current_chunk_lines))
                current_chunk_lines = []
                current_length = 0

            current_chunk_lines.append(line)
            current_length += line_len

        if current_chunk_lines:
            chunks.append("\n".join(current_chunk_lines))

        if not chunks:
            raise EmptyTranscriptError(f"Session {session_id} has no usable transcript text")

        logger.info(
            "Assembled transcript chunks",
            extra={
                "session_id": session_id,
                "chunk_count": len(chunks),
                "total_chars": sum(len(c) for c in chunks),
            },
        )
        return chunks

    def assemble_transcript(self, session_id: int) -> str:
        return "\n".join(self.assemble_chunks(session_id))

    def generate_summary(self, session_id: int) -> str:
        return self._generate(session_id, SUMMARY_PROMPT, SUMMARY_MERGE_PROMPT, "summary")

    def generate_mom(self, session_id: int) -> str:
        return self._generate(session_id, MOM_PROMPT, MOM_MERGE_PROMPT, "mom")

    def generate_action_items(self, session_id: int) -> str:
        return self._generate(session_id, ACTION_ITEMS_PROMPT, ACTION_ITEMS_MERGE_PROMPT, "action_items")

    def classify(self, session_id: int) -> str:
        transcript = self.assemble_transcript(session_id)

        if len(transcript.strip()) < 100:
            return "conversation"

        return classify_transcript(
            transcript,
            self._client,
            model=self._model,
        )

    def process_session(self, session_id: int) -> dict:

        transcript_type = self.classify(session_id)

        logger.info(
            "Transcript classified",
            extra={
                "session_id": session_id,
                "type": transcript_type,
            },
        )

        summary = self.generate_summary(session_id)

        summary = (
            summary
            .replace("SPEAKER_", "Participant ")
            .replace("Speaker ", "Participant ")
        )

        mom = None
        action_items = None

        # SpeechFlow currently treats MoM and Action Items
        # as meeting-specific intelligence artifacts.
        if transcript_type == "meeting":
            mom = self.generate_mom(session_id)
            action_items = self.generate_action_items(session_id)

        return {
            "session_id": session_id,
            "transcript_type": transcript_type,
            "summary": summary,
            "mom": mom,
            "action_items": action_items,
        }

    def _generate(self, session_id: int, template: str, merge_template: str, output_type: str) -> str:
        chunks = self.assemble_chunks(session_id)
        
        partial_outputs = []
        for i, chunk in enumerate(chunks):

            prompt = template.format(transcript=chunk)

            try:
                out = self._client.generate(prompt, model=self._model)
                partial_outputs.append(out)
            except OllamaClientError as exc:
                logger.exception(
                    "Ollama chunk generation failed",
                    extra={
                        "session_id": session_id,
                        "model": self._model,
                        "output_type": output_type,
                        "chunk_index": i,
                    },
                )
                raise TranscriptGenerationError(
                    f"Ollama generation failed for {output_type} (chunk {i})"
                ) from exc

        if len(partial_outputs) == 1:
            return partial_outputs[0]

        merged_text = "\n\n".join(f"--- PART {i+1} ---\n{text}" for i, text in enumerate(partial_outputs))
        merge_prompt = merge_template.format(partial_outputs=merged_text)
        
        try:
            return self._client.generate(merge_prompt, model=self._model)
        except OllamaClientError as exc:
            logger.exception(
                "Ollama merge generation failed",
                extra={
                    "session_id": session_id,
                    "model": self._model,
                    "output_type": output_type,
                },
            )
            raise TranscriptGenerationError(f"Ollama merge generation failed for {output_type}") from exc
