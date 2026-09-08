import asyncio
import json
import os
import time
from collections import deque
from pathlib import Path
from typing import Deque, Dict

from fastapi import FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

MAX_MESSAGES = 200
BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "text.txt"
HTML_PATH = BASE_DIR / "index.html"
messages: Deque[Dict[str, object]] = deque(maxlen=MAX_MESSAGES)
devices: Dict[str, Dict[str, object]] = {}


def load_text_messages():
    global messages
    try:
        with LOG_PATH.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.read().splitlines() if line.strip()]
    except FileNotFoundError:
        return

    parsed = []
    for line in lines:
        if "|" not in line:
            continue
        ts, text = line.split("|", 1)
        try:
            parsed.append({"id": int(ts), "text": text.strip(), "time": int(ts)})
        except ValueError:
            continue
    messages = deque(parsed[-MAX_MESSAGES:], maxlen=MAX_MESSAGES)


def write_text_log():
    line_text = "\n".join(
        f"{int(item['time'])}|{item['text']}" for item in list(messages)
    )
    with LOG_PATH.open("w", encoding="utf-8") as f:
        f.write(line_text)


class MessageInput(BaseModel):
    text: str


class DeviceHeartbeat(BaseModel):
    device_id: str
    device_name: str


app = FastAPI(title="Live Key Feed")
load_text_messages()


@app.get("/")
async def root():
    return FileResponse(HTML_PATH)


@app.get("/messages")
async def fetch_messages():
    return JSONResponse(list(messages))


@app.post("/api/devices/heartbeat")
async def device_heartbeat(payload: DeviceHeartbeat, x_api_key: str | None = Header(default=None)):
    expected_key = os.getenv("INGEST_API_KEY")
    if expected_key and x_api_key != expected_key:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)

    now = int(time.time() * 1000)
    devices[payload.device_id] = {
        "id": payload.device_id,
        "name": payload.device_name,
        "last_seen": now,
    }
    return {"ok": True, "device": devices[payload.device_id]}


@app.get("/api/devices")
async def fetch_devices():
    return JSONResponse(list(devices.values()))


@app.post("/api/messages")
async def add_message(payload: MessageInput, x_api_key: str | None = Header(default=None)):
    expected_key = os.getenv("INGEST_API_KEY")
    if expected_key and x_api_key != expected_key:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)

    text = payload.text.strip()
    if not text:
        return JSONResponse({"ok": False, "error": "empty message"})

    item = {"id": int(time.time() * 1000), "text": text, "time": int(time.time() * 1000)}
    messages.append(item)
    write_text_log()
    return JSONResponse({"ok": True, "message": item})


@app.get("/events")
async def events(request: Request):
    async def event_generator():
        last_seen = max((int(item["id"]) for item in messages), default=0)
        while True:
            for msg in list(messages):
                msg_id = int(msg["id"])
                if msg_id > last_seen:
                    yield f"data: {json.dumps(msg)}\n\n"
                    last_seen = msg_id
            if await request.is_disconnected():
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"ok": True, "count": len(messages)}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
