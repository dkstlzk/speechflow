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

def build_translation_prompt(text: str, target_language: str, transcript_type: str, is_chunk: bool = False, is_summary: bool = False) -> str:
    """Builds a context-aware translation prompt."""
    
    base_prompt = f"""You are an expert professional translator.
Your task is to translate the following text.

Transcript Type:
{transcript_type}

The transcript originates from automatic speech recognition.
It may contain:
- recognition errors
- incomplete sentences
- false starts
- repeated words
- filler words
Do NOT "correct" the transcript.
Translate what was actually transcribed.
Do not guess what the speaker intended beyond what is reasonably inferable from the text.

The transcript may contain English, Hindi, Hinglish, Code-switched speech, colloquial expressions, incomplete sentences, and spoken language.
Your goal is to preserve the speaker's intended meaning, tone and style.

CRITICAL RULES:
1. Translate faithfully. Never summarize. Never explain. Never omit.
2. Preserve timestamps, speaker labels, paragraph breaks, and punctuation.
3. Keep proper nouns unchanged. Keep product names unchanged. Keep technical terms when they are commonly used in the target language. Examples: WhatsApp, Email, API, GitHub, Meeting ID, Transcript, Workflow, Server, Database, Deployment.
4. Do NOT translate names.
5. If speakers switch languages naturally, preserve that intent. Do NOT over-normalize.
6. Use language that sounds like a native person actually speaking. Avoid textbook translations. Avoid government-style wording. Avoid archaic vocabulary. Prefer contemporary spoken language.
7. If the transcript is casual, produce casual translation. If professional, produce professional translation. If interview, preserve interview tone. If lecture, preserve educational tone. If podcast, preserve conversational tone. Never convert every transcript into formal meeting language.
8. Never: summarize, paraphrase, rewrite, improve grammar, remove repetitions, infer missing words, or complete unfinished sentences. Translate exactly what exists. If the source contains mistakes, translate those mistakes faithfully.
"""

    if target_language.lower() in ("hindi", "hi"):
        base_prompt += """
When translating into Hindi:
- Prefer modern spoken Hindi.
- Use the type of Hindi commonly spoken in India today.
- Avoid overly Sanskritized vocabulary.
- Keep commonly used English technical words when they are naturally used by native speakers.
Examples: ✓ मीटिंग, ✓ प्रोजेक्ट, ✓ ईमेल, ✓ WhatsApp, ✓ API, ✓ Workflow, ✓ अपडेट
✗ बैठक (unless formal), ✗ कार्यप्रवाह, ✗ विद्युतीय डाक
Do not force unnatural Hindi replacements.
"""
    elif target_language.lower() in ("english", "en"):
        base_prompt += """
When translating into English:
- Do not translate every Hindi phrase literally.
- Produce natural fluent English.
- Preserve cultural meaning.
- Avoid robotic sentence structures.
- Prefer spoken business English over literal translations.
"""

    base_prompt += f"\nReturn ONLY translated text in {target_language}.\n"

    if is_chunk:
        base_prompt += f"""
Translate the values of the JSON object. The keys of the JSON object are the chunk IDs.
You MUST preserve the EXACT same keys from the Input JSON. Do not change the keys.
Never reorder. Never merge. Never split.
Return EXACTLY one key-value pair for every input key-value pair.
If one chunk cannot be translated, return the original text instead of removing it.

You must return STRICT JSON and ONLY JSON. Do not use markdown blocks.
The output must be a JSON object mapping the chunk ID to the translated text.

Input JSON:
{text}
"""
    elif is_summary:
        base_prompt += f"""
Translate the following meeting summary strictly to {target_language}.
- Preserve bullet points, headings, and formatting structure.
- Do NOT add any commentary, notes, or explanations.
- Output ONLY the translated text.

Text to translate:
{text}
"""
    else:
        base_prompt += f"""
Output ONLY the translated text.

Text to translate:
{text}
"""

    return base_prompt


class TranslationService:
    """Translates text using Ollama LLM."""

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        model: Optional[str] = None,
    ) -> None:
        from ...config.settings import settings
        self._client = ollama_client or OllamaClient()
        self._model = model or settings.OLLAMA_MODEL

    def translate_text(
        self,
        text: str,
        target_language: str,
        transcript_type: str = "conversation",
        is_summary: bool = False,
    ) -> str:
        """Translate text to the target language.

        Args:
            text: The text to translate.
            target_language: Target language key (e.g., 'hi', 'ta').
            transcript_type: Type of the transcript to inform translation tone.
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
        prompt = build_translation_prompt(
            text=text, 
            target_language=language_display, 
            transcript_type=transcript_type, 
            is_chunk=False, 
            is_summary=is_summary
        )

        logger.info(
            "Starting translation",
            extra={
                "target_language": lang_key,
                "text_length": len(text),
                "is_summary": is_summary,
                "transcript_type": transcript_type,
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
        transcript_type: str = "conversation",
    ) -> list[dict]:
        import json

        lang_key = target_language.lower().strip()
        if lang_key not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {target_language}")

        if not chunks:
            return []

        chunk_map = {}
        for c in chunks:
            c_id = str(c.get("id", ""))
            c_text = c.get("text", "")
            if c_id:
                chunk_map[c_id] = c_text

        language_display = SUPPORTED_LANGUAGES[lang_key]
        prompt = build_translation_prompt(
            text=json.dumps(chunk_map, ensure_ascii=False),
            target_language=language_display,
            transcript_type=transcript_type,
            is_chunk=True,
            is_summary=False
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

                # Layer 2: Extract raw object brackets
                if parsed is None:
                    obj_match = re.search(
                        r"\{\s*.*?\s*\}", translated_json, re.DOTALL
                    )
                    if obj_match:
                        try:
                            parsed = json.loads(obj_match.group(0))
                        except json.JSONDecodeError:
                            pass

                if parsed is None:
                    logger.warning(
                        f"Failed to parse chunk translation JSON using layered methods: {e}"
                    )
                    return []

            def _extract_dict(data: any) -> dict:
                res = {}
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, str):
                            res[k] = v
                        elif isinstance(v, dict):
                            if "text" in v:
                                res[k] = v["text"]
                            else:
                                res.update(_extract_dict(v))
                elif isinstance(data, list):
                    for item in data:
                        res.update(_extract_dict(item))
                return res

            extracted_dict = _extract_dict(parsed)
            if extracted_dict:
                result_chunks = []
                for k, v in extracted_dict.items():
                    if str(k).isdigit():
                        result_chunks.append({"id": int(k), "text": str(v)})
                    else:
                        result_chunks.append({"id": k, "text": str(v)})
                return result_chunks
            else:
                logger.error(
                    f"Unexpected JSON format from chunk translation: {type(parsed)} - {str(parsed)[:200]}"
                )
                return []
        except Exception as e:
            logger.error(f"Chunk translation failed: {e}")
            raise

    @staticmethod
    def get_supported_languages() -> dict[str, str]:
        """Return dict of supported language keys to display names."""
        return dict(SUPPORTED_LANGUAGES)
