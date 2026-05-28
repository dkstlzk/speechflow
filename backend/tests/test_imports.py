import importlib


def test_core_imports():
	modules = [
		"torch",
		"faster_whisper",
		"flask",
		"flask_socketio",
		"silero_vad",
		"pyannote.audio",
		"pydub",
		"ollama",
		"sqlalchemy",
		"psycopg2",
	]

	for module in modules:
		importlib.import_module(module)