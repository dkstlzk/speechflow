"""Ollama client utilities for local LLM generation."""

from dataclasses import dataclass
import os
from typing import Dict, Optional

import requests

from ...config.logging import get_logger

DEFAULT_OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
DEFAULT_TIMEOUT_SECONDS = 300.0

logger = get_logger("summarization")


class OllamaClientError(RuntimeError):
    """Raised when the Ollama client cannot produce a response."""


@dataclass(frozen=True)
class OllamaConfig:
    endpoint: str
    timeout_seconds: float


def _resolve_timeout(value: Optional[str]) -> float:
    if not value:
        return DEFAULT_TIMEOUT_SECONDS

    try:
        parsed = float(value)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS

    return parsed if parsed > 0 else DEFAULT_TIMEOUT_SECONDS


def _build_config(
    endpoint: Optional[str],
    timeout_seconds: Optional[float],
) -> OllamaConfig:
    resolved_endpoint = (endpoint or os.getenv("OLLAMA_ENDPOINT") or "").strip()
    if not resolved_endpoint:
        resolved_endpoint = DEFAULT_OLLAMA_ENDPOINT

    resolved_timeout = (
        timeout_seconds
        if timeout_seconds is not None
        else _resolve_timeout(os.getenv("OLLAMA_TIMEOUT_SECONDS"))
    )

    return OllamaConfig(
        endpoint=resolved_endpoint,
        timeout_seconds=resolved_timeout,
    )


class OllamaClient:
    """Requests-based client for Ollama text generation."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        config = _build_config(endpoint, timeout_seconds)
        self.endpoint = config.endpoint
        self.timeout_seconds = config.timeout_seconds
        self._session = session or requests.Session()

    def generate(self, prompt: str, model: str = "qwen2.5:3b") -> str:
        if not prompt or not prompt.strip():
            raise OllamaClientError("Prompt must not be empty")

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        import time
        logger.info(
            "Sending Ollama request",
            extra={
                "endpoint": self.endpoint,
                "model": model,
                "prompt_chars": len(prompt),
                "timeout": self.timeout_seconds,
            },
        )
        start_time = time.time()

        try:
            response = self._session.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout_seconds,
            )
            duration = time.time() - start_time
            logger.info("Ollama request completed", extra={"duration": duration, "type": "success"})
        except requests.Timeout as exc:
            duration = time.time() - start_time
            logger.warning(
                "Ollama request timed out",
                extra={
                    "endpoint": self.endpoint,
                    "model": model,
                    "timeout_seconds": self.timeout_seconds,
                    "duration": duration,
                },
            )
            raise OllamaClientError(f"Ollama request timed out after {duration:.2f}s") from exc
        except requests.RequestException as exc:
            duration = time.time() - start_time
            logger.exception(
                "Ollama request failed",
                extra={"endpoint": self.endpoint, "model": model, "duration": duration},
            )
            raise OllamaClientError("Ollama request failed") from exc

        if response.status_code != 200:
            logger.error(
                "Ollama returned non-200 response",
                extra={
                    "endpoint": self.endpoint,
                    "model": model,
                    "status_code": response.status_code,
                },
            )
            raise OllamaClientError(
                f"Ollama returned status {response.status_code}: "
                f"{response.text[:200]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            logger.exception(
                "Ollama returned invalid JSON",
                extra={"endpoint": self.endpoint, "model": model},
            )
            raise OllamaClientError("Ollama returned invalid JSON") from exc

        if data.get("error"):
            logger.error(
                "Ollama returned error",
                extra={
                    "endpoint": self.endpoint,
                    "model": model,
                    "error": data.get("error"),
                },
            )
            raise OllamaClientError(f"Ollama error: {data['error']}")

        generated = data.get("response")
        if not generated:
            logger.error(
                "Ollama response missing text",
                extra={"endpoint": self.endpoint, "model": model},
            )
            raise OllamaClientError("Ollama response missing text")

        return str(generated).strip()


def summarize_transcript(transcript_text: str) -> Dict:
    # TODO: call Ollama to produce summary, mom, action items.
    return {"summary": "", "mom": {}, "action_items": []}
