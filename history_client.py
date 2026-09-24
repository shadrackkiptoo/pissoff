import os
import time

import client


CHECK_INTERVAL_SECONDS = int(os.getenv("HISTORY_CHECK_INTERVAL_SECONDS", "30").strip() or "30")


def run_history_watch(interval_seconds: int = CHECK_INTERVAL_SECONDS):
    print(f"History watcher started. Site: {client.SITE_URL}")
    while True:
        try:
            before = len(client.browser_history_seen)
            client.sync_browser_history()
            after = len(client.browser_history_seen)
            if before != after:
                print(f"History sync complete. New entries tracked: {after - before}")
            else:
                print("History sync complete. No new entries.")
        except Exception as error:
            print(f"History watcher error: {type(error).__name__}: {error}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_history_watch()
