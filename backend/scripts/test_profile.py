import sys
import os
import logging

# Make sure we can import backend.app regardless of where script is run
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from backend.app.db.session import SessionLocal
from backend.app.models.session import Session
from backend.app.workers.intelligence_worker import run_intelligence_pipeline

# Configure basic logging to catch our profiling output
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] [%(name)s] %(message)s'
)

def main():
    db = SessionLocal()
    
    # Grab the most recent session
    session = db.query(Session).order_by(Session.id.desc()).first()
    
    if not session:
        print("No sessions found in database.")
        return
        
    print(f"Triggering intelligence pipeline for Session {session.id} ({session.title})")
    
    try:
        run_intelligence_pipeline(session.id)
    except Exception as e:
        print(f"Failed: {e}")
        
if __name__ == "__main__":
    main()
