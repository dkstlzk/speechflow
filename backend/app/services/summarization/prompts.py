"""Prompt templates for transcript intelligence generation."""

def get_base_schema() -> str:
    return """{
  "title": "A short, descriptive title for the transcript",
  "overview": "A 2-4 sentence high-level overview of the transcript.",
  "languages_detected": [
    {
      "language": "Language name (e.g. Hindi, English)",
      "usage": "Primary or Secondary"
    }
  ],
  "overall_context": {
    "purpose": "What was the transcript trying to achieve",
    "summary": "What was the actual result or key takeaway",
    "status": "planned|in-progress|completed|blocked"
  },
  "topics": [
    {
      "title": "Topic Name (only if explicitly discussed)",
      "overview": "1-2 sentence summary of this topic.",
      "key_points": ["Key point 1"]
    }
  ],
  "decisions": ["Only output if an explicit decision was made"],
  "action_items": [
    {
      "owner": "Name or Unassigned",
      "task": "Only output if a task was explicitly agreed upon",
      "priority": "medium"
    }
  ],
  "future_enhancements": ["Only if explicitly mentioned"],
  "risks": ["Only if explicitly mentioned"],
  "next_steps": ["Only if explicitly mentioned"]
}"""


def get_base_rules() -> str:
    return """CRITICAL RULES:
1. NEVER invent owners. If an owner is not explicitly mentioned, set owner to "Unassigned".
2. NEVER generate placeholder text such as "Owner Name", "Actionable Task", "TBD", or "Unknown".
3. Only use information supported by the transcript.
4. Do not invent facts, features, decisions, people, timelines, or commitments that are not supported by the transcript.
5. If a field is not applicable to this transcript type, return an empty array [] or empty object {}. The absence of information is preferable to invented information. Never fabricate goals, tasks, deadlines, projects, owners, meetings, follow-ups, or future work. If uncertain, return an empty array.
6. Never output SPEAKER_XX identifiers; if a speaker's name isn't known, use their generic label (e.g., Participant A).
7. If the transcript contains only: greetings, testing audio, introductions, filler conversation, acknowledgements, laughter, or incomplete speech, then treat it as a low-information transcript. Generate Overview: "The transcript contains only a brief casual interaction and does not contain enough meaningful information for detailed analysis." Return empty arrays for topics, action_items, decisions, future_enhancements, risks, next_steps. Do NOT infer any meeting context.
8. DO NOT OVER-INDEX ON SINGLE WORDS. If the transcript is extremely short (e.g., under 50 words) and someone says a random word (like "disease" or "health" due to a mic check misrecognition), DO NOT invent a "health-related meeting". You MUST return empty arrays for topics, decisions, action_items, risks, and next_steps in this case. Never hallucinate "communication strategies" or "future meetings" unless explicitly discussed at length.
9. ONLY populate the JSON arrays if the information is EXPLICITLY discussed. Otherwise, return `[]`. Default to empty arrays for sparse transcripts."""


TYPE_SPECIFIC_POLICIES = {
    "meeting": """Transcript Type: meeting
Allowed assumptions:
✓ Decisions
✓ Tasks
✓ Risks
Behavior:
- summarize discussions
- identify decisions
- identify action items
- identify risks
- identify next steps
""",
    "conversation": """Transcript Type: conversation
Allowed assumptions:
✗ Decisions unless explicit
✗ Action items unless explicit
✗ Future roadmap
Behavior:
- summarize the conversation naturally
- identify important discussion points
- do NOT invent decisions
- do NOT invent action items
- do NOT invent project plans
""",
    "interview": """Transcript Type: interview
Allowed assumptions:
✓ Questions
✓ Answers
✗ Action items
Behavior:
- summarize questions and answers
- identify candidate strengths
- identify interviewer concerns
""",
    "lecture": """Transcript Type: lecture
Allowed assumptions:
✗ Owners
✗ Decisions
✓ Concepts
✓ Topics
Behavior:
- summarize concepts
- identify learning points
- identify examples
- do NOT generate action items unless explicitly stated
""",
    "podcast": """Transcript Type: podcast
Allowed assumptions:
✓ Themes
✓ Opinions
Behavior:
- summarize themes
- identify key opinions
""",
    "voice_note": """Transcript Type: voice_note
Allowed assumptions:
✓ Message
✗ Meeting minutes
Behavior:
- summarize the message
""",
    "presentation": """Transcript Type: presentation
Allowed assumptions:
✗ Owners
✗ Decisions unless explicit
✓ Key points
✓ Themes
✓ Topics
Behavior:
- summarize the key points and themes presented
- identify slides or sections if discernible
- identify examples and demonstrations
- identify conclusions only if explicitly stated
- do NOT generate action items unless explicitly stated
- do NOT invent decisions or follow-ups
"""
}

def get_prompts(transcript_type: str) -> tuple[str, str]:
    """Returns (INTELLIGENCE_PROMPT, INTELLIGENCE_MERGE_PROMPT) for a given type."""
    
    # Fallback to conversation if type is unknown
    policy = TYPE_SPECIFIC_POLICIES.get(transcript_type, TYPE_SPECIFIC_POLICIES["conversation"])
    
    base_prompt = f"""You are an expert transcript analyst.
Your task is to analyze a transcript exactly as it is.
The transcript has already been classified as: {{transcript_type}}
This classification is authoritative. DO NOT reinterpret or change the transcript type.
Tailor your analysis to this transcript type. Do NOT assume it is a meeting unless transcript_type == "meeting".

Different transcript types require different analysis.
{policy}

The transcript may contain Hindi, English, or Hinglish (code-switched speech).
When generating summaries, action items, topics and decisions:
- Preserve original meaning.
- Do not treat Hindi words as transcription errors.
- Do not rewrite Hinglish into unnatural formal English.
- Use natural business English while preserving important Hindi terms when they carry context.

Return STRICT JSON and ONLY JSON. Do not output markdown code blocks like ```json ... ```, just output the raw JSON object.
The JSON MUST match this exact schema:

{get_base_schema()}

{get_base_rules()}
"""

    intelligence_prompt = base_prompt + """
Here is the transcript:
{transcript}
"""

    intelligence_merge_prompt = base_prompt + """
You have been given several JSON intelligence reports from different segments of the same {transcript_type}.
Merge them into a single, comprehensive JSON report that EXACTLY matches the schema.

ADDITIONAL MERGE RULES:
1. Combine topics, decisions, and action items from all segments. NEVER drop or omit any unique items. You must include ALL unique decisions, action items, and topics from the partial reports.
2. Only use information supported by the provided reports. You may consolidate related statements into higher-level themes, goals, objectives, discussion topics, and conclusions.
3. Be EXHAUSTIVE. An intelligence report is useless if it loses data. Merge the arrays by combining them, do not truncate them.

Here are the partial JSON reports:
{partial_outputs}
"""

    return intelligence_prompt, intelligence_merge_prompt

