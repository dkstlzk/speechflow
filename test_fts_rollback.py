from backend.app.db.session import SessionLocal
from backend.app.models.session import Session as SessionModel
from backend.app.models.transcript_chunk import TranscriptChunk
from sqlalchemy import func, literal_column, or_

db = SessionLocal()
q = db.query(SessionModel).outerjoin(TranscriptChunk, SessionModel.id == TranscriptChunk.session_id)

try:
    print("Testing intentional failure (bad column)...")
    q_fts = q.filter(literal_column("nonexistent_column").op("@@")(func.plainto_tsquery("english", "test"))).distinct()
    q_fts.all()
except Exception as e:
    print(f"Caught: {type(e).__name__}")
    db.rollback()
    print("Rollback complete.")
    
try:
    print("Testing fallback query...")
    q_ilike = q.filter(SessionModel.title.ilike("%test%")).distinct()
    res = q_ilike.all()
    print(f"Success! Found {len(res)} results.")
except Exception as e:
    print(f"Fallback failed: {type(e).__name__} - {e}")
