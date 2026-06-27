"""Translation service using Ollama for transcript translation."""

from typing import Optional

from ...config.logging import get_logger
from ..summarization.ollama import OllamaClient, OllamaClientError

logger = get_logger("translation")

SUPPORTED_LANGUAGES = {
    "hi": "Hindi",
    "en": "English",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "or": "Odia",
    "es": "Spanish",
    "nl": "Dutch",
    "gu": "Gujarati",
    "ru": "Russian",
}

TRANSLATION_PROMPT = """Translate the following text to {language}.

Rules:
- Translate ALL text faithfully and completely.
- Use natural, modern, and conversational {language}. Prefer commonly spoken words over overly formal terms.
- Do NOT translate technical terms unnecessarily. Keep terms like Meeting ID, WhatsApp, Email, Transcript, Summary, Action Items, Workflow, and Translation as-is when appropriate.
- Preserve the speaker labels exactly as they appear (e.g. "Participant A:", "Participant B:").
- Preserve timestamps if present.
- Preserve paragraph structure and line breaks.
- Do NOT add any commentary, notes, or explanations.
- Do NOT omit any content.
- CRITICAL: Output ONLY in {language}. Do NOT output any other languages like Japanese, Chinese, or English unless it's a technical term kept as-is.
- The output should sound like a professional meeting note written by a native speaker.
- Output ONLY the translated text.

Text to translate:
{text}
"""

CHUNK_TRANSLATION_PROMPT = """You are an expert translator. 
Translate the following JSON array of transcript chunks into {language}.

Rules:
- You must return STRICT JSON and ONLY JSON. Do not use markdown blocks.
- The output must be a JSON array of objects, with the exact same "id" values as the input.
- Translate the "text" field to {language}.
- Preserve context across chunks. Return exact same ids. Do not merge chunks. Do not reorder chunks.
- Use natural, modern, and conversational {language}. Prefer commonly spoken words over overly formal terms.
- Do NOT translate technical terms unnecessarily. Keep terms like Meeting ID, WhatsApp, Email, Transcript, Summary, Action Items, Workflow, and Translation as-is when appropriate.
- The translation should sound like a professional meeting transcript written by a native speaker.

Input JSON:
{text}

Output JSON format:
[
  {{"id": 1, "text": "translated text here"}},
  {{"id": 2, "text": "translated text here"}}
]
"""

SUMMARY_TRANSLATION_PROMPT = """Translate the following meeting summary strictly to {language}.

Rules:
- Translate ALL text faithfully and completely.
- Preserve bullet points, headings, and formatting structure.
- Do NOT add any commentary, notes, or explanations.
- Do NOT omit any content.
- Use natural, contemporary language suitable for native speakers of the target language.
- CRITICAL: Output ONLY in {language}. Do NOT output any other languages like Japanese, Chinese, or English.
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
            target_language: Target language key (e.g., 'hi', 'ta').
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

    def translate_chunks(
        self,
        chunks: list[dict],
        target_language: str,
    ) -> list[dict]:
        import json

        lang_key = target_language.lower().strip()
        if lang_key not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {target_language}")

        if not chunks:
            return []

        language_display = SUPPORTED_LANGUAGES[lang_key]
        prompt = CHUNK_TRANSLATION_PROMPT.format(
            language=language_display, text=json.dumps(chunks, ensure_ascii=False)
        )

        logger.info(
            f"Sending Ollama chunk translation request for {len(chunks)} chunks"
        )
        try:
            translated_json = self._client.generate(
                prompt, model=self._model, response_format="json"
            )
            parsed = None
            try:
                parsed = json.loads(translated_json)
            except json.JSONDecodeError as e:
                import re

                # Layer 1: Extract from markdown block
                md_match = re.search(
                    r"```(?:json)?\s*(.*?)\s*```",
                    translated_json,
                    re.DOTALL | re.IGNORECASE,
                )
                if md_match:
                    try:
                        parsed = json.loads(md_match.group(1))
                    except json.JSONDecodeError:
                        pass

                # Layer 2: Extract raw array brackets
                if parsed is None:
                    array_match = re.search(
                        r"\[\s*{.*}\s*\]", translated_json, re.DOTALL
                    )
                    if array_match:
                        try:
                            parsed = json.loads(array_match.group(0))
                        except json.JSONDecodeError:
                            pass

                if parsed is None:
                    logger.warning(
                        f"Failed to parse chunk translation JSON using layered methods: {e}"
                    )
                    return []

            if isinstance(parsed, dict):
                # If LLM wrapped the array in an object, find the array
                for v in parsed.values():
                    if isinstance(v, list):
                        return v
                return [parsed]  # fallback
            elif isinstance(parsed, list):
                return parsed
            else:
                logger.error(
                    f"Unexpected JSON format from chunk translation: {type(parsed)}"
                )
                return []
        except Exception as e:
            logger.error(f"Chunk translation failed: {e}")
            raise

    @staticmethod
    def get_supported_languages() -> dict[str, str]:
        """Return dict of supported language keys to display names."""
        return dict(SUPPORTED_LANGUAGES)
