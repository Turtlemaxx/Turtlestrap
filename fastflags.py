import json
import os
import shutil

ROBLOX_VERSIONS = os.path.expandvars(r"%LOCALAPPDATA%\Roblox\Versions")

def load_flags(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_flags(path, flags):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(flags, f, indent=2)

def get_latest_version():
    versions = []
    for v in os.listdir(ROBLOX_VERSIONS):
        if not v.startswith("version-"):
            continue
        full = os.path.join(ROBLOX_VERSIONS, v)
        exe  = os.path.join(full, "RobloxPlayerBeta.exe")
        if os.path.exists(exe):
            versions.append(full)
    if not versions:
        raise RuntimeError("No valid Roblox Player installation found")
    return max(versions, key=os.path.getmtime)

def apply_fastflags(flags_file):
    version = get_latest_version()
    settings = os.path.join(version, "ClientSettings")
    os.makedirs(settings, exist_ok=True)

    dest = os.path.join(settings, "ClientAppSettings.json")
    if not os.path.exists(flags_file):
        with open(dest, "w", encoding="utf-8") as f:
            f.write("{}")
        return

    shutil.copyfile(flags_file, dest)