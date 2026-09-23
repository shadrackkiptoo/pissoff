import os
import subprocess
import sys

import winreg

STARTUP_ENTRY_NAME = "KeyboardService"


def get_target_executable():
    if getattr(sys, "frozen", False):
        return os.path.abspath(sys.executable)

    repo_root = os.path.dirname(os.path.abspath(__file__))
    dist_exe = os.path.join(repo_root, "dist", "KeyboardService.exe")
    if os.path.exists(dist_exe):
        return dist_exe

    return os.path.abspath(sys.executable)


def register_startup_launch():
    exe_path = get_target_executable()
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    ) as startup_key:
        winreg.SetValueEx(startup_key, STARTUP_ENTRY_NAME, 0, winreg.REG_SZ, exe_path)
    print(f"Startup entry registered: {exe_path}")


def remove_startup_launch():
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_ALL_ACCESS,
        ) as startup_key:
            try:
                winreg.DeleteValue(startup_key, STARTUP_ENTRY_NAME)
                print(f"Removed startup entry: {STARTUP_ENTRY_NAME}")
            except FileNotFoundError:
                print(f"Startup entry not found: {STARTUP_ENTRY_NAME}")
    except FileNotFoundError:
        print(f"Run key not found: {STARTUP_ENTRY_NAME}")


def start_hidden_instance():
    exe_path = get_target_executable()
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    subprocess.Popen([exe_path], close_fds=True, startupinfo=startupinfo)
    print(f"Started hidden instance: {exe_path}")


def main():
    if len(sys.argv) > 1 and sys.argv[1].lower() == "install":
        register_startup_launch()
        return

    if len(sys.argv) > 1 and sys.argv[1].lower() == "remove":
        remove_startup_launch()
        return

    if len(sys.argv) > 1 and sys.argv[1].lower() == "start":
        start_hidden_instance()
        return

    print("Usage: service_client.py [install|remove|start]")


if __name__ == "__main__":
    main()
