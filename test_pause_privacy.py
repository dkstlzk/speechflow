import socketio
import time
import requests

sio = socketio.Client()

def run_test():
    # 1. Create a session
    resp = requests.post("http://localhost:5000/api/realtime/start")
    data = resp.json()["data"]
    session_id = data["session_id"]
    print(f"Started session {session_id}")

    # 2. Connect
    sio.connect("http://localhost:5000")
    
    # 3. Stream Start
    sio.emit("stream_start", {"session_id": session_id})
    time.sleep(1)

    # 4. Send 10 chunks (active)
    print("Sending active audio...")
    for _ in range(10):
        sio.emit("audio_chunk", b'\x00' * 16000) # 0.5s of 16kHz 16-bit audio
        time.sleep(0.1)

    # 5. Pause
    print("Pausing stream...")
    sio.emit("stream_pause", {})
    time.sleep(1)

    # 6. Send 10 chunks (paused) - simulating frontend still capturing
    print("Sending paused audio...")
    for _ in range(10):
        sio.emit("audio_chunk", b'\xff' * 16000)
        time.sleep(0.1)

    # 7. Stop
    print("Stopping stream...")
    sio.emit("stream_end", {})
    time.sleep(2)
    sio.disconnect()
    
    # 8. Check DB duration
    import sqlite3
    # Wait, the DB uses SQLAlchemy, let's just query the DB directly.
    
run_test()
