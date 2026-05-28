import re
import time
from pathlib import Path
from typing import Iterable
from uuid import uuid4


def sanitize_filename(filename: str) -> str:
    base_name = Path(filename).name
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", base_name)
    return sanitized or "upload.bin"


def is_allowed_extension(filename: str, allowed_extensions: Iterable[str]) -> bool:
    extension = Path(filename).suffix.lower().lstrip(".")
    return extension in {ext.lower() for ext in allowed_extensions}


def build_temp_filename(filename: str) -> str:
    path = Path(filename)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    token = uuid4().hex[:8]
    return f"{path.stem}_{timestamp}_{token}{path.suffix.lower()}"


def create_temp_path(temp_dir: str, filename: str) -> Path:
    Path(temp_dir).mkdir(parents=True, exist_ok=True)
    temp_name = build_temp_filename(filename)
    return Path(temp_dir) / temp_name


def cleanup_file(path: str) -> None:
    file_path = Path(path)
    if file_path.exists():
        file_path.unlink()
