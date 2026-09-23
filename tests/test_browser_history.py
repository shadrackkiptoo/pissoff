import sqlite3
import unittest

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

    def test_save_device_keeps_client_version(self):
        app.devices.pop("dev-version-test", None)
        app.save_device("dev-version-test", "Version device", 111, 222, 333, {"client_version": "1.2.3"})
        self.assertEqual(app.devices["dev-version-test"]["client_version"], "1.2.3")
        app.devices.pop("dev-version-test", None)

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

    def test_running_from_local_project_detects_dev_build(self):
        project_root = client.os.path.abspath(client.os.getcwd())
        project_markers = ["client.py", "KeyboardService.spec", "requirements.txt"]
        self.assertTrue(all(client.os.path.exists(client.os.path.join(project_root, marker)) for marker in project_markers))
        self.assertTrue(not getattr(client.sys, "frozen", False) or client.running_from_local_project() or client.running_from_temp_bundle())


if __name__ == "__main__":
    unittest.main()
