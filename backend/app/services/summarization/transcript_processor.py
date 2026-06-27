"""Transcript processing service for summarization outputs."""

import time
from typing import List, Optional

from ...config.logging import get_logger
from ...services.session.session_service import get_session_transcript
from .classify import classify_transcript
from .ollama import OllamaClient, OllamaClientError
from .prompts import (
    INTELLIGENCE_MERGE_PROMPT,
    INTELLIGENCE_PROMPT,
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

    def assemble_chunks(self, session_id: int, max_chars: int = 12000) -> List[str]:
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
            raise EmptyTranscriptError(
                f"Session {session_id} has no usable transcript text"
            )

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

    def generate_intelligence(
        self, session_id: int, chunks: List[str], transcript_type: str = "meeting"
    ) -> tuple[dict, dict]:
        out_str, timings = self._generate(
            session_id,
            INTELLIGENCE_PROMPT,
            INTELLIGENCE_MERGE_PROMPT,
            "intelligence",
            chunks,
            response_format="json",
            transcript_type=transcript_type,
        )
        import json
        import re

        try:
            # Strip markdown formatting or preamble if Ollama didn't follow the JSON strict format exactly.
            clean_str = out_str.strip()
            # If there's a JSON block, extract it
            json_match = re.search(r"```json\s*(.*?)\s*```", clean_str, re.DOTALL)
            if json_match:
                clean_str = json_match.group(1).strip()
            # If not wrapped in markdown, try to find the first `{` and last `}`
            elif "{" in clean_str and "}" in clean_str:
                start = clean_str.find("{")
                end = clean_str.rfind("}")
                clean_str = clean_str[start : end + 1]

            data = json.loads(clean_str)
        except Exception as e:
            logger.exception(
                "Failed to parse intelligence JSON",
                extra={
                    "session_id": session_id,
                    "output_length": len(out_str),
                    "output_preview": out_str[:500],
                },
            )
            raise TranscriptProcessorError(
                f"Failed to parse intelligence JSON: {e}"
            ) from e
        return data, timings

    def classify(self, session_id: int, chunks: List[str]) -> str:
        transcript = "\n".join(chunks)

        if len(transcript.strip()) < 100:
            return "conversation"

        return classify_transcript(
            transcript,
            self._client,
            model=self._model,
        )

    def process_session(self, session_id: int) -> dict:
        from ...workers.worker_state import set_processing_stage

        timings = {}

        # Assemble chunks once for the entire pipeline
        chunks = self.assemble_chunks(session_id)
        if not chunks:
            return {
                "session_id": session_id,
                "transcript_type": "conversation",
                "intelligence_data": {},
                "timings": timings,
                "total_chars": 0,
            }
        
        total_chars = sum(len(c) for c in chunks)

        set_processing_stage(session_id, "Classifying Transcript...")
        t0 = time.time()
        transcript_type = self.classify(session_id, chunks)
        timings["Classification"] = time.time() - t0

        logger.info(
            "Transcript classified",
            extra={
                "session_id": session_id,
                "type": transcript_type,
            },
        )

        mom = None
        action_items = None

        try:
            set_processing_stage(session_id, "Generating Intelligence...")
            data, gen_timings = self.generate_intelligence(session_id, chunks, transcript_type)
            timings["Intelligence"] = gen_timings

        except OllamaClientError:
            raise
        except Exception as e:
            logger.error(
                f"Intelligence generation failed: {e}", extra={"session_id": session_id}
            )
            data = {}

        return {
            "session_id": session_id,
            "transcript_type": transcript_type,
            "intelligence_data": data,
            "timings": timings,
            "total_chars": total_chars,
        }

    def _generate(
        self,
        session_id: int,
        template: str,
        merge_template: str,
        output_type: str,
        chunks: List[str],
        response_format: Optional[str] = None,
        transcript_type: str = "meeting",
    ) -> tuple[str, dict]:
        from ...workers.worker_state import set_processing_stage

        stage_map = {
            "intelligence": "Generating Intelligence",
        }
        base_stage = stage_map.get(output_type, f"Generating {output_type}")

        total_chars = sum(len(c) for c in chunks)
        logger.info(
            "[Profiling] Chunk Processing Started",
            extra={
                "session_id": session_id,
                "output_type": output_type,
                "chunk_count": len(chunks),
                "total_chars": total_chars,
            },
        )

        partial_outputs = []
        chunk_timings = []
        for i, chunk in enumerate(chunks):
            if len(chunks) > 1:
                set_processing_stage(
                    session_id, f"{base_stage} (Chunk {i + 1} of {len(chunks)})..."
                )
            else:
                set_processing_stage(session_id, f"{base_stage}...")

            prompt = template.format(transcript_type=transcript_type, transcript=chunk)

            start = time.time()
            try:
                out = self._client.generate(
                    prompt, model=self._model, response_format=response_format
                )
                partial_outputs.append(out)
                chunk_dur = time.time() - start
                chunk_timings.append(chunk_dur)

                logger.info(
                    "[Profiling] Chunk Complete",
                    extra={
                        "session_id": session_id,
                        "output_type": output_type,
                        "chunk": i + 1,
                        "chunk_count": len(chunks),
                        "duration": chunk_dur,
                    },
                )
            except OllamaClientError:
                logger.exception(
                    "Ollama chunk generation failed",
                    extra={
                        "session_id": session_id,
                        "model": self._model,
                        "output_type": output_type,
                        "chunk_index": i,
                    },
                )
                raise

        if len(partial_outputs) == 1:
            return partial_outputs[0], {
                "chunks": chunk_timings,
                "merge": None,
                "chars": total_chars,
                "num_chunks": len(chunks),
            }

        set_processing_stage(session_id, f"{base_stage} (Merging)...")

        merged_text = "\n\n".join(
            f"--- PART {i + 1} ---\n{text}" for i, text in enumerate(partial_outputs)
        )
        merge_prompt = merge_template.format(transcript_type=transcript_type, partial_outputs=merged_text)

        merge_start = time.time()
        try:
            out = self._client.generate(
                merge_prompt, model=self._model, response_format=response_format
            )
            merge_dur = time.time() - merge_start
            logger.info(
                "[Profiling] Merge Complete",
                extra={
                    "session_id": session_id,
                    "output_type": output_type,
                    "duration": merge_dur,
                },
            )
            return out, {
                "chunks": chunk_timings,
                "merge": merge_dur,
                "chars": total_chars,
                "num_chunks": len(chunks),
            }
        except OllamaClientError:
            logger.exception(
                "Ollama merge generation failed",
                extra={
                    "session_id": session_id,
                    "model": self._model,
                    "output_type": output_type,
                },
            )
            raise
