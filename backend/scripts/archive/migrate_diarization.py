import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.db.session import engine
from sqlalchemy import text

def migrate():
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE sessions ADD COLUMN diarization_mode VARCHAR(32);"))
            print("Added diarization_mode")
        except Exception as e:
            print(f"Skipped diarization_mode: {e}")
            
        try:
            conn.execute(text("ALTER TABLE sessions ADD COLUMN diarized_at TIMESTAMP;"))
            print("Added diarized_at")
        except Exception as e:
            print(f"Skipped diarized_at: {e}")

if __name__ == "__main__":
    migrate()
