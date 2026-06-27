from typing import Any, Dict, List, Optional


def format_mom(intel_data: Dict[str, Any]) -> Optional[str]:
    """Formats raw intelligence JSON data into a Markdown Minutes of Meeting (MoM)."""
    mom_parts = []

    overall_context = intel_data.get("overall_context", {})
    if not overall_context:
        # Fallback for old data
        overall_context = intel_data.get("meeting_outcome", {})

    if overall_context:
        mom_parts.append("## Overall Context\n")
        purpose = overall_context.get("purpose") or overall_context.get("objective")
        if purpose:
            mom_parts.append(f"**Purpose:** {purpose}")
        summary = overall_context.get("summary") or overall_context.get("result")
        if summary:
            mom_parts.append(f"**Summary:** {summary}")
        if overall_context.get("status"):
            mom_parts.append(
                f"**Status:** {str(overall_context.get('status')).title()}"
            )
        mom_parts.append("")

    languages_detected = intel_data.get("languages_detected", [])
    if languages_detected:
        mom_parts.append("## Languages Detected\n")
        for lang in languages_detected:
            l_name = lang.get("language", "Unknown")
            l_use = lang.get("usage", "Unknown")
            mom_parts.append(f"- {l_name} ({l_use})")
        mom_parts.append("")

    topics = intel_data.get("topics", [])
    if topics:
        mom_parts.append("## Discussion Topics\n")
        for topic in topics:
            mom_parts.append(f"### {topic.get('title', 'Topic')}")
            if topic.get("overview"):
                mom_parts.append(f"{topic.get('overview', '')}\n")
            for pt in topic.get("key_points", []):
                mom_parts.append(f"- {pt}")
            mom_parts.append("")

    def _format_list_item(item) -> str:
        if isinstance(item, dict):
            title = item.get("title", "")
            desc = item.get("description", item.get("overview", ""))
            if title and desc:
                return f"**{title}**\n  _{desc}_"
            elif title:
                return f"**{title}**"
            elif desc:
                return desc
            return str(item)
        return str(item)

    decisions = intel_data.get("decisions", [])
    if decisions:
        mom_parts.append("## Decisions\n")
        for d in decisions:
            mom_parts.append(f"- {_format_list_item(d)}")
        mom_parts.append("")

    risks = intel_data.get("risks", [])
    if risks:
        mom_parts.append("## Risks\n")
        for r in risks:
            mom_parts.append(f"- {_format_list_item(r)}")
        mom_parts.append("")

    next_steps = intel_data.get("next_steps", [])
    if next_steps:
        mom_parts.append("## Next Steps\n")
        for ns in next_steps:
            mom_parts.append(f"- {_format_list_item(ns)}")
        mom_parts.append("")

    future_enhancements = intel_data.get("future_enhancements", [])
    if future_enhancements:
        mom_parts.append("## Future Enhancements\n")
        for fe in future_enhancements:
            mom_parts.append(f"- {_format_list_item(fe)}")
        mom_parts.append("")

    return "\n".join(mom_parts) if mom_parts else None


def format_action_items(raw_actions: List[Dict[str, Any]]) -> List[str]:
    """Formats raw action item JSON array into a normalized list of strings."""
    parsed_items = []
    for act in raw_actions:
        owner = act.get("owner", "Unassigned")
        task = act.get("task", "")
        priority = act.get("priority", "").title()
        if task:
            task_str = f"[{priority}] {task}" if priority else task
            parsed_items.append(f"[{owner}] {task_str}")
    return parsed_items
