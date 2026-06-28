import subprocess
from pathlib import Path


def preprocess_to_wav(input_path: str, output_path: str) -> str:
    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise FileNotFoundError(f"Audio file not found: {input_file}")

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_file),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(output_file),
    ]

    result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "FFmpeg conversion failed")

    if not output_file.exists() or output_file.stat().st_size == 0:
        raise RuntimeError("FFmpeg produced empty output")

    return str(output_file)
