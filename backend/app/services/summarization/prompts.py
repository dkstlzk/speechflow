"""Prompt templates for transcript intelligence generation."""

SUMMARY_PROMPT = """
Generate a compressed summary of the transcript.
If the transcript contains test phrases,
microphone checks,
audio checks,
or very little meaningful content:

Return a short factual summary.

Do not invent context.
Do not infer topics.
Do not fabricate technical subjects.

Internal guidance:

- Use only information present in the transcript.
- Do not add external knowledge.
- Do not repeat information.
- Output should be substantially shorter than the transcript.
- Every bullet should represent multiple related statements when possible.
- Do not narrate the conversation.
- Identify the main topics first.
- Group related information under the same topic.
- Create a new topic only when the subject meaningfully changes.
- Prefer fewer high-quality topics over many small topics.
- Prefer information compression over explanation.
- Omit topics with no meaningful content.
- Do not explain why something happened.
- Do not infer motivations, causes, intentions, emotions, or outcomes.
- Report information only.

Do not output prompt instructions.
Do not output rule names.
Do not output explanation of formatting decisions.
Output only the final summary.

Do NOT write phrases such as:
- "Participants discussed..."
- "During the meeting..."
- "The discussion focused on..."
- "The meeting covered..."

Single-Speaker Handling:

- If the transcript contains only one speaker,
  do not describe a discussion, meeting,
  conversation, debate, or exchange.

- Treat the transcript as a monologue,
  narration, recording, lecture, reading,
  or statement when appropriate.

Do not use plural nouns unless multiple people
are explicitly present.
Avoid:
- participants
- attendees
- speakers
- they
when only one speaker exists.

If the transcript contains only one meaningful idea:
Return a single sentence.

Transcript Type Handling:
- Conversations may contain opinions, preferences, stories, or casual discussion.
- Do not force every conversation into a meeting structure.
- For conversations, summarize the topics discussed naturally.
- For recordings with a single subject, prefer a short summary over multiple topics.

If the transcript does not contain a coherent discussion,
still summarize the content that is present.

Return:
Overview
<one sentence>

Key Topics
...

Otherwise return:

Overview
<one sentence>

Key Topics

<Topic Name>
- point
- point

<Topic Name>
- point

Name Handling:
- Never output SPEAKER_XX identifiers.
- Prefer real names if mentioned.
- Prefer real roles if mentioned.

If no names or roles are explicitly available:
- Avoid referring to people whenever possible.
- Focus on the information rather than the speaker.

Transcript:
{transcript}
"""


MOM_PROMPT = """
Generate meeting minutes.

Internal guidance:

- Extract only information explicitly stated.
- Do not infer attendees.
- Do not infer decisions.
- Do not infer next steps.
- Do not infer ownership.
- Do not infer deadlines.
- Prefer omission over guessing.
- Omit empty sections entirely.

Attendees section is OPTIONAL.

If attendees are not explicitly named,
omit the Attendees section completely.

Never create participant roles.
Never infer titles.
Never infer occupations.

Only include attendees if explicitly identified by name,
role, or self-introduction in the transcript.
Speaker labels alone do not identify attendees.
If attendee identity is unknown:
omit the Attendees section entirely.

Do NOT:
- derive attendees from speaker labels
- derive attendees from diarization speakers
- create placeholder attendees

Name Handling:
- Never output SPEAKER_XX identifiers.
- Prefer real names if mentioned.
- Prefer real roles if mentioned.

If no names or roles are explicitly available:
- Avoid referring to people whenever possible.

If no explicit decisions exist:
omit the Decisions section.

If no explicit next steps exist:
omit the Next Steps section.

If no sections contain information:
return exactly:

No meeting minutes identified.

Output format:

Attendees
- attendee

Decisions
- decision

Next Steps
- next step

Transcript:
{transcript}
"""


ACTION_ITEMS_PROMPT = """
Extract action items.

Internal guidance:

- Include only actions that were:
  - assigned
  - agreed upon
  - committed to
  - accepted

If no explicitly assigned or agreed actions exist,
return exactly:

No action items identified.

Do not convert suggestions into actions.
Do not assume group agreement.
Do not assume commitment.

Do NOT extract:
- suggestions
- recommendations
- possibilities
- ideas under discussion
- hypothetical actions

Do not infer:
- tasks
- owners
- deadlines

If an action lacks an explicit owner,
commitment, assignment, or agreement,
do NOT include it.

When uncertain:
exclude the action item.

Examples that are NOT action items:
- "We could..."
- "Maybe we should..."
- "Someone suggested..."
- "It might help to..."

Examples that ARE action items:
- "Rahul will..."
- "Priya agreed to..."
- "The team decided to..."
- "Action: ..."

Keep items concise.

If no valid action items exist:
Return exactly:
No action items identified.

Name Handling:
- Never output SPEAKER_XX identifiers.
- Prefer real names if mentioned.
- Prefer real roles if mentioned.
- Otherwise use participant labels already present.

Output format:

Action Items
- action
- action

Transcript:
{transcript}
"""


SUMMARY_MERGE_PROMPT = """
Merge partial summaries.

Internal guidance:

- Merge duplicate topics.
- Remove repetition.
- Remove filler.
- Keep only unique information.
- Do not add information.
- Do not narrate the conversation.
- Preserve topic structure.
- Final output must be shorter than the combined inputs.

Output format:

Overview
<one sentence>

Key Topics

<Topic Name>
- point
- point

Partial Summaries:
{partial_outputs}
"""


MOM_MERGE_PROMPT = """
Merge partial meeting minutes.

Internal guidance:

- Deduplicate attendees.
- Deduplicate decisions.
- Deduplicate next steps.
- Omit empty sections.
- Do not add information.
- Prefer omission over guessing.

Partial MoMs:
{partial_outputs}
"""


ACTION_ITEMS_MERGE_PROMPT = """
Merge partial action-item lists.

Internal guidance:

- Remove duplicates.
- Merge equivalent actions.
- Keep wording concise.
- Do not invent actions.
- Preserve only agreed or assigned actions.

If no actions remain:
Return exactly:
No action items identified.

Output format:

Action Items
- action
- action

Partial Action Items:
{partial_outputs}
"""