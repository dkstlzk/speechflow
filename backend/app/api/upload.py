from flask import Blueprint, jsonify

upload_bp = Blueprint("upload", __name__)


@upload_bp.post("/")
def upload_audio():
    # TODO: accept multipart upload and create session.
    # TODO: save temp file, run FFmpeg normalization.
    # TODO: run faster-whisper and pyannote diarization.
    # TODO: persist transcript chunks and finalize session.
    return jsonify({"status": "not_implemented"}), 501
