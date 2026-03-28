import os
import subprocess
import ctypes
import ctypes.wintypes
import threading
import time

ROBLOX_VERSIONS = os.path.expandvars(r"%LOCALAPPDATA%\Roblox\Versions")

MUTEX_NAME           = "ROBLOX_singletonMutex"
INSTALLER_MUTEX_NAME = "RobloxPlayerInstaller"

MUTEX_ALL_ACCESS     = 0x001F0001
ERROR_ALREADY_EXISTS = 183


def get_latest_version():
    versions = []
    for v in os.listdir(ROBLOX_VERSIONS):
        if v.startswith("version-"):
            full_path = os.path.join(ROBLOX_VERSIONS, v)
            exe_path = os.path.join(full_path, "RobloxPlayerBeta.exe")
            if os.path.exists(exe_path):
                versions.append(full_path)
    if not versions:
        raise RuntimeError("No valid Roblox Player installation found")
    return max(versions, key=os.path.getmtime)


def _mutex_holder_thread(stop_event: threading.Event):
    kernel32 = ctypes.windll.kernel32

    while not stop_event.is_set():
        handle = kernel32.CreateMutexW(None, True, MUTEX_NAME)
        if not handle:
            time.sleep(0.05)
            continue

        err = kernel32.GetLastError()

        if err != ERROR_ALREADY_EXISTS:
            stop_event.wait()
            kernel32.ReleaseMutex(handle)
            kernel32.CloseHandle(handle)
            return

        kernel32.CloseHandle(handle)
        steal = kernel32.OpenMutexW(MUTEX_ALL_ACCESS, False, MUTEX_NAME)
        if steal:
            kernel32.ReleaseMutex(steal)
            kernel32.CloseHandle(steal)

        time.sleep(0.02)


_mutex_stop_event: threading.Event  | None = None
_mutex_thread:     threading.Thread | None = None


def enable_multi_instance():
    global _mutex_stop_event, _mutex_thread

    if _mutex_thread and _mutex_thread.is_alive():
        return

    _mutex_stop_event = threading.Event()
    _mutex_thread = threading.Thread(
        target=_mutex_holder_thread,
        args=(_mutex_stop_event,),
        daemon=True,
        name="RobloxMutexHolder",
    )
    _mutex_thread.start()


def disable_multi_instance():
    global _mutex_stop_event
    if _mutex_stop_event:
        _mutex_stop_event.set()


def _kill_installer_processes():
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "RobloxPlayerInstaller.exe"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def _hold_installer_mutex(stop_event: threading.Event):
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, True, INSTALLER_MUTEX_NAME)
    if not handle:
        return
    stop_event.wait()
    kernel32.ReleaseMutex(handle)
    kernel32.CloseHandle(handle)


_installer_mutex_stop:   threading.Event  | None = None
_installer_mutex_thread: threading.Thread | None = None


def _start_installer_block():
    global _installer_mutex_stop, _installer_mutex_thread
    if _installer_mutex_thread and _installer_mutex_thread.is_alive():
        return
    _installer_mutex_stop = threading.Event()
    _installer_mutex_thread = threading.Thread(
        target=_hold_installer_mutex,
        args=(_installer_mutex_stop,),
        daemon=True,
        name="RobloxInstallerBlock",
    )
    _installer_mutex_thread.start()


def stop_installer_block():
    global _installer_mutex_stop
    if _installer_mutex_stop:
        _installer_mutex_stop.set()


def launch_roblox(ticket: str = "", multi_instance: bool = False):
    version = get_latest_version()
    exe = os.path.join(version, "RobloxPlayerBeta.exe")

    _kill_installer_processes()
    _start_installer_block()

    if multi_instance:
        enable_multi_instance()

    time.sleep(0.25)

    if ticket:
        args = [
            exe,
            "--app",
            "--authenticationUrl", "https://auth.roblox.com/v1/authentication-ticket/redeem",
            "--authenticationTicket", ticket,
            "--launchtime", str(int(time.time() * 1000)),
        ]
        subprocess.Popen(args)
    else:
        subprocess.Popen([exe, "--app"])