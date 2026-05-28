from pathlib import Path


def preprocess_to_wav(input_path: str, output_path: str) -> str:
    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise FileNotFoundError(f"Audio file not found: {input_file}")

    # TODO: invoke FFmpeg CLI to normalize to 16kHz mono WAV.
    return str(output_file)
