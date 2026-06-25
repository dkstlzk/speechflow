"""Translation service using Ollama for transcript translation."""

from typing import Optional

from ...config.logging import get_logger
from ..summarization.ollama import OllamaClient, OllamaClientError

logger = get_logger("translation")

SUPPORTED_LANGUAGES = {
    "hindi": "Hindi",
    "tamil": "Tamil",
    "telugu": "Telugu",
    "marathi": "Marathi",
    "odia": "Odia",
    "english": "English",
    "spanish": "Spanish",
    "dutch": "Dutch",
}

TRANSLATION_PROMPT = """Translate the following text to {language}.

Rules:
- Translate ALL text faithfully and completely.
- Preserve the speaker labels exactly as they appear (e.g. "Participant A:", "Participant B:").
- Preserve timestamps if present.
- Preserve paragraph structure and line breaks.
- Do NOT add any commentary, notes, or explanations.
- Do NOT omit any content.
- If a word or name has no direct translation, keep it in its original form.
- Output ONLY the translated text.

Text to translate:
{text}
"""

SUMMARY_TRANSLATION_PROMPT = """Translate the following meeting summary to {language}.

Rules:
- Translate ALL text faithfully and completely.
- Preserve bullet points, headings, and formatting structure.
- Do NOT add any commentary, notes, or explanations.
- Do NOT omit any content.
- Output ONLY the translated text.

Text to translate:
{text}
"""


class TranslationService:
    """Translates text using Ollama LLM."""

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        model: str = "qwen2.5:3b",
    ) -> None:
        self._client = ollama_client or OllamaClient()
        self._model = model

    def translate_text(
        self,
        text: str,
        target_language: str,
        is_summary: bool = False,
    ) -> str:
        """Translate text to the target language.

        Args:
            text: The text to translate.
            target_language: Target language key (e.g., 'hindi', 'tamil').
            is_summary: If True, uses summary-optimized prompt.

        Returns:
            Translated text string.

        Raises:
            ValueError: If target language is not supported.
            OllamaClientError: If Ollama fails.
        """
        lang_key = target_language.lower().strip()
        if lang_key not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language: {target_language}. "
                f"Supported: {', '.join(SUPPORTED_LANGUAGES.keys())}"
            )

        if not text or not text.strip():
            return ""

        language_display = SUPPORTED_LANGUAGES[lang_key]
        template = SUMMARY_TRANSLATION_PROMPT if is_summary else TRANSLATION_PROMPT
        prompt = template.format(language=language_display, text=text)

        logger.info(
            "Starting translation",
            extra={
                "target_language": lang_key,
                "text_length": len(text),
                "is_summary": is_summary,
            },
        )

        import time
        start = time.time()

        try:
            result = self._client.generate(prompt, model=self._model)
        except OllamaClientError:
            logger.exception(
                "Translation failed",
                extra={"target_language": lang_key},
            )
            raise

        duration = time.time() - start
        logger.info(
            "Translation completed",
            extra={
                "target_language": lang_key,
                "duration": f"{duration:.1f}s",
                "input_chars": len(text),
                "output_chars": len(result),
            },
        )

        return result.strip()

    def translate_transcript_chunks(
        self,
        chunks: list[dict],
        target_language: str,
    ) -> list[dict]:
        """Translate transcript chunks while preserving structure.

        Args:
            chunks: List of transcript segment dicts with 'text', 'speaker', etc.
            target_language: Target language key.

        Returns:
            List of translated segment dicts (same structure, translated text).
        """
        # Build a single block of text with speaker labels for context
        lines = []
        for chunk in chunks:
            speaker = chunk.get("speaker", "")
            display_name = chunk.get("display_name")
            text = chunk.get("text", "")
            label = display_name or speaker or "Speaker"
            lines.append(f"{label}: {text}")

        combined = "\n".join(lines)
        translated = self.translate_text(combined, target_language)

        # Parse translated lines back into chunks
        translated_lines = translated.strip().split("\n")
        result = []

        for i, chunk in enumerate(chunks):
            translated_chunk = dict(chunk)  # shallow copy
            if i < len(translated_lines):
                line = translated_lines[i]
                # Try to strip the speaker label prefix if present
                if ": " in line:
                    parts = line.split(": ", 1)
                    translated_chunk["text"] = parts[1]
                else:
                    translated_chunk["text"] = line
            result.append(translated_chunk)

        return result

    @staticmethod
    def get_supported_languages() -> dict[str, str]:
        """Return dict of supported language keys to display names."""
        return dict(SUPPORTED_LANGUAGES)
