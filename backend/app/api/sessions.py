from flask import Blueprint, jsonify

from ..schemas.response import ApiResponse
from ..services.session.session_service import get_session_transcript
from ..services.summarization.transcript_processor import (
    TranscriptProcessor,
    TranscriptNotFoundError,
    EmptyTranscriptError,
    TranscriptProcessorError,
)
from ..services.persistence.summaries import save_summary, get_summary
from ..services.persistence.actions import save_action_items

sessions_bp = Blueprint("sessions", __name__)


def _parse_action_items_text(raw: str) -> list[str]:
    """Parse the raw action items text into a list of individual items."""
    if not raw or raw.strip().lower() == "no action items identified.":
        return []
    items = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if line.startswith("- "):
            line = line[2:].strip()
        elif line.startswith("* "):
            line = line[2:].strip()
        if line.lower() == "no action items identified.":
            continue
        if line and line.lower() not in ("action items", "action items:"):
            items.append(line)
    return items


@sessions_bp.get("/")
def list_sessions():
    # TODO: return recent sessions for history view.
    return jsonify(ApiResponse.fail("not implemented").to_dict()), 501


@sessions_bp.get("/<session_id>")
def get_session(session_id: str):
    # TODO: load session, transcript, and summaries from persistence layer.
    return (
        jsonify(ApiResponse.fail("not implemented").to_dict()),
        501,
    )


@sessions_bp.get("/<session_id>/transcript")
def get_session_transcript_endpoint(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    payload = get_session_transcript(session_id_int)
    if payload is None:
        return jsonify(ApiResponse.fail("session not found").to_dict()), 404

    return jsonify(ApiResponse.ok(payload).to_dict()), 200


@sessions_bp.post("/<session_id>/process")
def process_session(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    processor = TranscriptProcessor()

    try:
        result = processor.process_session(session_id_int)
    except TranscriptNotFoundError as e:
        return jsonify(ApiResponse.fail(str(e)).to_dict()), 404
    except EmptyTranscriptError as e:
        return jsonify(ApiResponse.fail(str(e)).to_dict()), 400
    except TranscriptProcessorError as e:
        return jsonify(ApiResponse.fail(str(e)).to_dict()), 500

    # Persist outputs
    try:
        save_summary(session_id_int, result["summary"], result.get("mom"))
        raw_actions = result.get("action_items") or ""
        parsed_items = _parse_action_items_text(raw_actions)
        save_action_items(session_id_int, parsed_items)
    except Exception as e:
        return jsonify(
            ApiResponse.fail(
                f"failed to persist generated outputs: {e}"
            ).to_dict()
        ), 500
    return jsonify(ApiResponse.ok(result).to_dict()), 200


@sessions_bp.get("/<session_id>/summary")
def get_session_summary(session_id: str):
    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify(ApiResponse.fail("invalid session id").to_dict()), 400

    data = get_summary(session_id_int)
    if data is None:
        return jsonify(ApiResponse.fail("no summary found").to_dict()), 404

    return jsonify(ApiResponse.ok(data).to_dict()), 200
