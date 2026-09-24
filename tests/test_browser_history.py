import sqlite3
import threading
import types
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


if __name__ == "__main__":
    unittest.main()
