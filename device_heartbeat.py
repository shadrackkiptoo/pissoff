import hashlib
import json
import os
import platform
import socket
import time
from urllib.request import Request, urlopen

SITE_URL = os.getenv("KEY_FEED_URL", "https://your-app.onrender.com").rstrip("/")
API_KEY = os.getenv("KEY_FEED_API_KEY", "")
device_name = platform.node() or socket.gethostname() or "Unknown device"
device_id = hashlib.sha256(device_name.encode("utf-8")).hexdigest()[:12]


def send_heartbeat():
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    request = Request(
        f"{SITE_URL}/api/devices/heartbeat",
        data=json.dumps({"device_id": device_id, "device_name": device_name}).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urlopen(request, timeout=10):
        pass


print(f"Device heartbeat active: {device_name}")
while True:
    try:
        send_heartbeat()
    except OSError as error:
        print(f"Heartbeat failed: {error}")
    time.sleep(60)