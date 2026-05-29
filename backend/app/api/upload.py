from flask import Blueprint, jsonify, request

from ..config.logging import get_logger
from ..config.settings import Settings
from ..schemas.response import ApiResponse, UploadResponseSchema
from ..services.session import create_upload_session
from ..services.utils import create_temp_path, is_allowed_extension, sanitize_filename
from ..workers.upload_pipeline import start_upload_pipeline

upload_bp = Blueprint("upload", __name__)
logger = get_logger("upload")
settings = Settings()


@upload_bp.post("/")
def upload_audio():
    if "file" not in request.files:
        return jsonify(ApiResponse.fail("file is required").to_dict()), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify(ApiResponse.fail("filename is required").to_dict()), 400

    filename = sanitize_filename(file.filename)
    if not is_allowed_extension(filename, settings.ALLOWED_EXTENSIONS):
        return jsonify(ApiResponse.fail("unsupported file type").to_dict()), 400

    temp_path = create_temp_path(settings.TEMP_DIR, filename)
    file.save(temp_path)

    session_context = create_upload_session(filename)
    logger.info(
        "Upload received",
        extra={"session_id": session_context.session_id, "filename": filename},
    )

    start_upload_pipeline(session_context.session_id, str(temp_path))

    payload = UploadResponseSchema(
        session_id=session_context.session_id,
        status=session_context.status.value,
        filename=filename,
    ).to_dict()

    return jsonify(ApiResponse.ok(payload).to_dict()), 202
