# pyrefly: ignore [missing-import]
from flask import Blueprint, jsonify, request

from ..config.constants import MAX_FIELD_LENGTH
from ..config.extensions import limiter
from ..config.logging import get_logger
from ..config.settings import settings
from ..schemas.response import ApiResponse, UploadResponseSchema
from ..services.session import create_upload_session
from ..utils.file_manager import (
    cleanup_file,
    create_temp_path,
    is_allowed_extension,
    sanitize_filename,
)
from ..workers.upload_pipeline import start_upload_pipeline

upload_bp = Blueprint("upload", __name__)
logger = get_logger("upload")


@upload_bp.post("/")
@limiter.limit("20 per minute")
def upload_audio():
    from ..workers.job_manager import get_active_job_count

    if get_active_job_count() >= settings.MAX_BACKGROUND_WORKERS:
        return jsonify(
            ApiResponse.fail("Server overloaded. Too many active jobs.").to_dict()
        ), 503

    if "file" not in request.files:
        return jsonify(ApiResponse.fail("file is required").to_dict()), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify(ApiResponse.fail("filename is required").to_dict()), 400

    filename = sanitize_filename(file.filename)
    if not is_allowed_extension(filename, settings.ALLOWED_EXTENSIONS):
        return jsonify(ApiResponse.fail("unsupported file type").to_dict()), 400

    temp_path = create_temp_path(settings.TEMP_DIR, filename)

    title = request.form.get("title")
    host_name = request.form.get("host_name")
    participants = request.form.get("participants")

    for field_name, field_val in [
        ("Title", title),
        ("Host name", host_name),
        ("Participants", participants),
    ]:
        if field_val and len(field_val) > MAX_FIELD_LENGTH:
            return jsonify(
                ApiResponse.fail(
                    f"{field_name} cannot exceed {MAX_FIELD_LENGTH} characters"
                ).to_dict()
            ), 400

    try:
        file.save(temp_path)
        session_context = create_upload_session(
            original_filename=filename,
            title=title,
            host_name=host_name,
            participants=participants,
        )
    except Exception:
        cleanup_file(str(temp_path))
        raise
    logger.info(
        "Upload received",
        extra={"session_id": session_context.session_id, "upload_filename": filename},
    )

    start_upload_pipeline(session_context.session_id, str(temp_path))

    payload = UploadResponseSchema(
        session_id=session_context.session_id,
        status=session_context.status.value,
        filename=filename,
    ).to_dict()

    return jsonify(ApiResponse.ok(payload).to_dict()), 202
