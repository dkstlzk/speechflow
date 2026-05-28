from typing import Optional


def create_session(session_type: str, original_filename: Optional[str] = None) -> int:
    # TODO: persist session row and return session id.
    # TODO: set status to pending or transcribing based on pipeline.
    return 0


def update_session_status(
    session_id: int, status: str, error: Optional[str] = None
) -> None:
    # TODO: update session lifecycle state and error details.
    return None
