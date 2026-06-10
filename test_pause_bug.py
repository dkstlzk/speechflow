import socketio
import time
import requests

sio = socketio.Client()
sio.connect('http://localhost:5000')

print("Starting session...")
res = requests.post("http://localhost:5000/api/realtime/session")
session_id = res.json()["data"]["session_id"]
print(f"Session created: {session_id}")

sio.emit("stream_start", {"session_id": str(session_id)})
time.sleep(0.5)

print("Sending 10 'speech' chunks...")
for i in range(10):
    sio.emit("audio_chunk", b'\x01\x02' * 16000) # 1 sec of audio
    time.sleep(0.1)

print("Pausing session...")
sio.emit("stream_pause", {})
time.sleep(0.5)

print("Sending 30 'paused' chunks...")
for i in range(30):
    sio.emit("audio_chunk", b'\x00\x00' * 16000) # 1 sec of audio
    time.sleep(0.1)

print("Stopping session...")
sio.emit("stream_end", {})
time.sleep(2)

# API Finalize
requests.post(f"http://localhost:5000/api/realtime/session/{session_id}/finalize")
print("Done!")
