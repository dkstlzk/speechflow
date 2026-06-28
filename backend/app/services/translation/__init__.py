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
Your task is to translate the following text naturally as a native professional translator.

Transcript Type: {transcript_type}
Target Language: {target_language}

CRITICAL INSTRUCTIONS:
1. Do NOT translate word-by-word. Translate the meaning, not the individual words.
2. If a literal translation sounds unnatural, rewrite it into fluent, everyday {target_language} while preserving meaning.
3. Domain-specific terms should be translated using commonly accepted terminology.
4. Never invent words or produce transliterated nonsense.
5. If an English technical term is more commonly used than its {target_language} equivalent, keep the English term.
"""

    LANGUAGE_SPECIFIC_INSTRUCTIONS = {
        "Hindi": "6. Use natural, conversational Hindi. Avoid overly formal Sanskritized words.\nExamples:\nguidance counselor -> काउंसलर\nflu season -> फ्लू का मौसम\npancake breakfast -> पैनकेक नाश्ता\nmeeting -> बैठक",
        "Tamil": "6. CRITICAL: Use modern, conversational, everyday Tamil. DO NOT use archaic, formal, or textbook Tamil (Senthamil).\n7. If a Tamil word sounds unnatural, use the common English loanword instead.\nExamples:\nguidance counselor -> வழிகாட்டி\nflu season -> காய்ச்சல் காலம்\npancake breakfast -> பான்கேக்\nmeeting -> மீட்டிங்\nattendance -> வருகை",
        "Telugu": "6. CRITICAL: Use modern, conversational Telugu. DO NOT use archaic or formal Telugu (Grandhikam).\n7. If a Telugu word sounds unnatural, use the common English loanword instead.\nExamples:\nguidance counselor -> గైడెన్స్ కౌన్సిలర్\nflu season -> ఫ్లూ సీజన్\npancake breakfast -> పాన్‌కేక్ బ్రేక్‌ఫాస్ట్\nmeeting -> మీటింగ్\nattendance -> అటెండెన్స్",
        "Marathi": "6. CRITICAL: Use modern, conversational Marathi. DO NOT use overly formal or archaic Marathi.\n7. If a Marathi word sounds unnatural, use the common English loanword instead.\nExamples:\nguidance counselor -> समुपदेशक\nflu season -> फ्लूचा हंगाम\npancake breakfast -> पॅनकेक नाश्ता\nmeeting -> मीटिंग\nattendance -> उपस्थिती",
        "Gujarati": "6. CRITICAL: Use modern, conversational Gujarati. DO NOT use overly formal Gujarati.\n7. If a Gujarati word sounds unnatural, use the common English loanword instead.\nExamples:\nguidance counselor -> માર્ગદર્શક\nflu season -> ફ્લૂની સિઝન\npancake breakfast -> પેનકેક નાસ્તો\nmeeting -> મીટિંગ\nattendance -> હાજરી",
        "Odia": "6. CRITICAL: Use modern, conversational Odia. DO NOT use overly formal Odia.\n7. If an Odia word sounds unnatural, use the common English loanword instead.\nExamples:\nguidance counselor -> ପରାମର୍ଶଦାତା (or Counselor)\nflu season -> ଫ୍ଲୁ ସିଜିନ୍\npancake breakfast -> ପ୍ୟାନକେକ୍ ବ୍ରେକଫାଷ୍ଟ\nmeeting -> ମିଟିଂ\nattendance -> ଉପସ୍ଥାନ",
        "Spanish": "6. CRITICAL: Use modern, conversational Spanish. DO NOT use overly formal vocabulary.\nExamples:\nguidance counselor -> consejero\nflu season -> temporada de gripe\npancake breakfast -> desayuno de panqueques\nmeeting -> reunión\nattendance -> asistencia",
        "Dutch": "6. CRITICAL: Use modern, conversational Dutch. Avoid archaic or overly formal phrasing.\nExamples:\nguidance counselor -> decaan\nflu season -> griepseizoen\npancake breakfast -> pannenkoekenontbijt\nmeeting -> vergadering\nattendance -> aanwezigheid",
        "Russian": "6. CRITICAL: Use modern, conversational Russian. Avoid overly formal or archaic vocabulary.\nExamples:\nguidance counselor -> школьный психолог\nflu season -> сезон гриппа\npancake breakfast -> завтрак с блинами\nmeeting -> собрание\nattendance -> посещаемость",
    }

    if target_language in LANGUAGE_SPECIFIC_INSTRUCTIONS:
        base_prompt += LANGUAGE_SPECIFIC_INSTRUCTIONS[target_language] + "\n"
    else:
        base_prompt += f"6. Use modern, conversational {target_language}. Avoid overly formal or archaic vocabulary.\n"

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
        self._model = model or settings.TRANSLATION_MODEL

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
                prompt, model=self._model
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

                # Layer 3: Attempt to repair truncated JSON (Unterminated strings or missing brackets)
                if parsed is None:
                    fixed_json = translated_json.strip()
                    # If there's an odd number of quotes, close the last string
                    if fixed_json.count('"') % 2 != 0:
                        fixed_json += '"'
                    # If it doesn't end with a bracket, close the object
                    if not fixed_json.endswith('}'):
                        fixed_json += '}'
                    
                    try:
                        parsed = json.loads(fixed_json)
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
