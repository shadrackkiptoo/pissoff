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


if __name__ == "__main__":
    unittest.main()
