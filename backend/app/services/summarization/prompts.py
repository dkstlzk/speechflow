"""Prompt templates for transcript intelligence generation."""

INTELLIGENCE_PROMPT = """
Write the report for a manager or stakeholder who did not attend this {transcript_type}.
The report should allow them to understand:
1. What was discussed
2. Why it matters
3. What decisions were made (if any)
4. What actions are required (if any)
5. What happens next
without reading the transcript.

You are an expert enterprise analyst.
Your task is to analyze the provided transcript and generate a comprehensive intelligence report for this {transcript_type}.

The transcript may contain Hindi, English, or Hinglish (code-switched speech).
When generating summaries, action items, topics and decisions:
- Preserve original meaning.
- Do not treat Hindi words as transcription errors.
- Do not rewrite Hinglish into unnatural formal English.
- Use natural business English while preserving important Hindi terms when they carry context.

Return STRICT JSON and ONLY JSON. Do not output markdown code blocks like ```json ... ```, just output the raw JSON object.

The JSON MUST match this exact schema:

{{
  "meeting_title": "A short, descriptive title for the {transcript_type}",
  "overview": "A 2-4 sentence high-level overview of the {transcript_type}.",
  "languages_detected": [
    {{
      "language": "Language name (e.g. Hindi, English)",
      "usage": "Primary or Secondary"
    }}
  ],
  "meeting_outcome": {{
    "objective": "What was the {transcript_type} trying to achieve",
    "result": "What was the actual result or key takeaway",
    "status": "planned|in-progress|completed|blocked"
  }},
  "topics": [
    {{
      "title": "Topic Name",
      "overview": "1-2 sentence summary of this topic.",
      "key_points": ["Point 1", "Point 2"]
    }}
  ],
  "decisions": ["Decision 1", "Decision 2"],
  "action_items": [
    {{
      "owner": "Name of the person assigned or Unassigned",
      "task": "Description of the task",
      "priority": "high|medium|low"
    }}
  ],
  "future_enhancements": ["Feature 1", "Feature 2"],
  "risks": ["Risk 1", "Risk 2"],
  "next_steps": ["Next Step 1"]
}}

CRITICAL RULES:
1. NEVER invent owners. If an owner is not explicitly mentioned, set owner to "Unassigned".
2. NEVER generate placeholder text such as "Owner Name", "Actionable Task", "TBD", or "Unknown".
3. Only use information supported by the transcript. You may consolidate related statements into higher-level themes, but do NOT omit important decisions, action items, or risks. Be highly detailed and exhaustive.
4. Do not invent facts, features, decisions, people, timelines, or commitments that are not supported by the transcript.
5. If there are no decisions, action items, or future work, return empty arrays [].
6. Never output SPEAKER_XX identifiers; if a speaker's name isn't known, use their generic label (e.g., Participant A).
7. If the transcript is extremely short (e.g., just greetings or a few meaningless sentences), DO NOT hallucinate a meeting. Provide a brief overview stating the transcript lacks meaningful content, and return empty arrays for topics, action items, decisions, etc.

Here is the transcript:
{transcript}
"""

INTELLIGENCE_MERGE_PROMPT = """
Write the report for a manager or stakeholder who did not attend this {transcript_type}.
The report should allow them to understand:
1. What was discussed
2. Why it matters
3. What decisions were made (if any)
4. What actions are required (if any)
5. What happens next
without reading the transcript.

You are an expert enterprise analyst.
You have been given several JSON intelligence reports from different segments of the same {transcript_type}.
Merge them into a single, comprehensive JSON report that EXACTLY matches this schema:

{{
  "meeting_title": "A short, descriptive title for the {transcript_type}",
  "overview": "A 2-4 sentence high-level overview of the entire {transcript_type}.",
  "languages_detected": [
    {{
      "language": "Language name (e.g. Hindi, English)",
      "usage": "Primary or Secondary"
    }}
  ],
  "meeting_outcome": {{
    "objective": "What was the {transcript_type} trying to achieve",
    "result": "What was the actual result or key takeaway",
    "status": "planned|in-progress|completed|blocked"
  }},
  "topics": [
    {{
      "title": "Topic Name",
      "overview": "1-2 sentence summary of this topic.",
      "key_points": ["Point 1", "Point 2"]
    }}
  ],
  "decisions": ["Decision 1", "Decision 2"],
  "action_items": [
    {{
      "owner": "Name of the person assigned or Unassigned",
      "task": "Description of the task",
      "priority": "high|medium|low"
    }}
  ],
  "future_enhancements": ["Feature 1", "Feature 2"],
  "risks": ["Risk 1", "Risk 2"],
  "next_steps": ["Next Step 1"]
}}

CRITICAL RULES:
1. Combine topics, decisions, and action items from all segments. NEVER drop or omit any unique items. You must include ALL unique decisions, action items, and topics from the partial reports.
2. Only use information supported by the provided reports. You may consolidate related statements into higher-level themes, goals, objectives, discussion topics, and conclusions.
3. Be EXHAUSTIVE. A meeting intelligence report is useless if it loses data. Merge the arrays by combining them, do not truncate them.
4. Do not invent facts, features, decisions, people, timelines, or commitments.
5. Return STRICT JSON and ONLY JSON. Do not output markdown blocks.
6. If the partial reports lack meaningful content (e.g., just greetings), DO NOT hallucinate a meeting. Provide a brief overview stating the transcript lacks meaningful content, and return empty arrays.

Here are the partial JSON reports:
{partial_outputs}
"""
