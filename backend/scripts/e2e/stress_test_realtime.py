import asyncio
import socketio
import requests
import wave
import time
import sys

BACKEND_URL = "http://localhost:5000"
API_URL = f"{BACKEND_URL}/api"
ADMIN_PASSWORD = "testpassword" # wait, we need to check .env

def login():
    res = requests.post(f"{API_URL}/auth/login", json={"password": "password123"})
    if res.status_code == 200:
        return res.cookies
    return None

async def test_silent_recording(cookies):
    print("--- Testing Silent Recording ---")
    sio = socketio.AsyncClient()
    
    # We must pass cookies to socketio
    headers = {"Cookie": f"session={cookies.get('session')}"} if cookies else {}
    await sio.connect(BACKEND_URL, headers=headers)
    
    events = []
    
    @sio.on("stream_ack")
    async def on_stream_ack(data):
        events.append("stream_ack")
        print("Silent: stream started")
        
    @sio.on("stream_complete")
    async def on_stream_complete(data):
        events.append("stream_complete")
        print("Silent: stream complete")
        
    @sio.on("stream_finalized")
    async def on_stream_finalized(data):
        events.append("stream_finalized")
        print("Silent: stream finalized")
        
    await sio.emit("stream_start", {"session_id": "test_silent", "sample_rate": 16000})
    await asyncio.sleep(1.0)
    
    # send silence (10 chunks of 0s)
    silence = b'\x00' * 16000 * 2 # 1 sec
    await sio.emit("audio_chunk", silence)
    
    await sio.emit("stream_end", {})
    await asyncio.sleep(2.0)
    
    await sio.disconnect()
    
    if "stream_finalized" in events:
        print("Silent recording test PASS: Session was finalized.")
    else:
        print("Silent recording test FAIL: Session stuck.")

async def test_concurrency(cookies):
    print("\n--- Testing Concurrency ---")
    sio1 = socketio.AsyncClient()
    sio2 = socketio.AsyncClient()
    
    cookies2 = login()
    headers1 = {"Cookie": f"session={cookies.get('session')}"} if cookies else {}
    headers2 = {"Cookie": f"session={cookies2.get('session')}"} if cookies2 else {}
    
    await sio1.connect(BACKEND_URL, headers=headers1)
    await sio2.connect(BACKEND_URL, headers=headers2)
    
    logs = []
    
    @sio1.on("caption_update")
    async def on_cap1(data):
        logs.append((time.time(), "Client 1 Caption", data["text"]))
        
    @sio2.on("caption_update")
    async def on_cap2(data):
        logs.append((time.time(), "Client 2 Caption", data["text"]))
        
    await sio1.emit("stream_start", {"session_id": "test_c1", "sample_rate": 16000})
    await sio2.emit("stream_start", {"session_id": "test_c2", "sample_rate": 16000})
    await asyncio.sleep(0.5)
    
    # Read harvard.wav
    with wave.open("test_audio/harvard.wav", "rb") as w:
        frames = w.readframes(w.getnframes())
        
    chunk_size = 16000 * 2 // 4 # 250ms chunks
    
    for i in range(0, len(frames), chunk_size):
        chunk = frames[i:i+chunk_size]
        await sio1.emit("audio_chunk", chunk)
        await sio2.emit("audio_chunk", chunk)
        await asyncio.sleep(0.25) # realtime
        
    await sio1.emit("stream_end", {})
    await sio2.emit("stream_end", {})
    await asyncio.sleep(5.0)
    
    await sio1.disconnect()
    await sio2.disconnect()
    
    print("\nLogs timeline:")
    t0 = logs[0][0] if logs else 0
    for t, src, txt in logs:
        print(f"[{t-t0:.2f}s] {src}: {txt[:30]}...")

async def main():
    cookies = login()
    if not cookies:
        print("Failed to login")
        return
        
    await test_silent_recording(cookies)
    await test_concurrency(cookies)

if __name__ == "__main__":
    asyncio.run(main())
