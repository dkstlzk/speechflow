from flask import Blueprint, jsonify

from ..schemas.response import ApiResponse
from ..services.session.session_service import get_session_transcript
from ..services.summarization.transcript_processor import (
    TranscriptProcessor,
    TranscriptNotFoundError,
    EmptyTranscriptError,
    TranscriptProcessorError,
)

sessions_bp = Blueprint("sessions", __name__)


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
        summary = processor.generate_summary(session_id_int)
        mom = processor.generate_mom(session_id_int)
        action_items = processor.generate_action_items(session_id_int)
    except TranscriptNotFoundError as e:
        return jsonify(ApiResponse.fail(str(e)).to_dict()), 404
    except EmptyTranscriptError as e:
        return jsonify(ApiResponse.fail(str(e)).to_dict()), 400
    except TranscriptProcessorError as e:
        return jsonify(ApiResponse.fail(str(e)).to_dict()), 500

    data = {
        "session_id": session_id_int,
        "summary": summary,
        "mom": mom,
        "action_items": action_items,
    }
    return jsonify(ApiResponse.ok(data).to_dict()), 200
