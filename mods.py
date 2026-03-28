import os
import shutil
import json
import ctypes
import time

ROBLOX_VERSIONS   = os.path.expandvars(r"%LOCALAPPDATA%\Roblox\Versions")
MODS_CONFIG       = "mods_config.json"
CURSORS_ASSET_DIR = os.path.join("assets", "cursors")
SOUNDS_ASSET_DIR  = os.path.join("assets", "sounds")
CURSOR_FOLDER_MAP = {
    "Default": "default",
    "2016":    "2016",
    "2008":    "2008",
}

SOUNDS_FOLDER_MAP = {
    "Default": "default",
    "Old":     "old",
}

FONTS_ASSET_DEFAULT = os.path.join("assets", "fonts", "default")

FONT_SKIP_KEYWORDS = [
    "emoji", "Emoji", "icon", "Icon", "seguiemj", "color", "Symbol"
]

DEFAULT_CONFIG = {
    "mouse_cursor":         "Default",
    "old_character_sounds": "Default",
    "vr_enabled":           False,
    "fps_unlock":           False,
    "ram_optimizer":        False,
    "custom_font":          False,
    "custom_font_path":     "",
    "multi_instance":       False,
}

def load_mods_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(MODS_CONFIG):
        try:
            with open(MODS_CONFIG, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg

def save_mods_config(cfg: dict):
    with open(MODS_CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def _get_latest_version() -> str:
    versions = []
    for v in os.listdir(ROBLOX_VERSIONS):
        if not v.startswith("version-"):
            continue
        full = os.path.join(ROBLOX_VERSIONS, v)
        exe  = os.path.join(full, "RobloxPlayerBeta.exe")
        if os.path.exists(exe):
            versions.append(full)
    if not versions:
        raise RuntimeError("Roblox installation not found.")
    return max(versions, key=os.path.getmtime)

def _safe_copy(src: str, dest: str, status_cb=None):
    if not os.path.exists(src):
        if status_cb:
            status_cb(f"  [skip] source not found: {os.path.basename(src)}")
        return
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src, dest)
    except Exception as e:
        if status_cb:
            status_cb(f"  [error] {e}")

def _copy_folder_contents(src_dir: str, dest_dir: str, status_cb=None):
    if not os.path.isdir(src_dir):
        if status_cb:
            status_cb(f"  [skip] folder not found: {src_dir}")
        return
    os.makedirs(dest_dir, exist_ok=True)
    for fn in os.listdir(src_dir):
        src  = os.path.join(src_dir, fn)
        dest = os.path.join(dest_dir, fn)
        if os.path.isfile(src):
            _safe_copy(src, dest, status_cb)

def apply_mods(cfg: dict | None = None, status_cb=None):
    if cfg is None:
        cfg = load_mods_config()

    try:
        version_dir = _get_latest_version()
    except RuntimeError as e:
        if status_cb:
            status_cb(f"⚠  {e}")
        return

    content = os.path.join(version_dir, "content")
    cursor_choice = cfg.get("mouse_cursor", "Default")
    cursor_folder = CURSOR_FOLDER_MAP.get(cursor_choice)
    if cursor_folder is not None:
        if status_cb:
            status_cb(f"Applying cursor mod ({cursor_choice})…")
        src_dir  = os.path.join(CURSORS_ASSET_DIR, cursor_folder)
        dest_dir = os.path.join(content, "textures", "Cursors", "KeyboardMouse")
        _copy_folder_contents(src_dir, dest_dir, status_cb)
        if status_cb:
            status_cb("Cursor mod applied ✓")
    sounds_choice = cfg.get("old_character_sounds", "Default")
    sounds_folder = SOUNDS_FOLDER_MAP.get(sounds_choice)
    if sounds_folder is not None:
        if status_cb:
            status_cb(f"Applying character sounds ({sounds_choice})…")
        src_dir  = os.path.join(SOUNDS_ASSET_DIR, sounds_folder)
        dest_dir = os.path.join(content, "sounds")
        _copy_folder_contents(src_dir, dest_dir, status_cb)
        if status_cb:
            status_cb("Character sounds applied ✓")
    vr_enabled = cfg.get("vr_enabled", False)
    if status_cb:
        status_cb(f"Setting VR {'enabled' if vr_enabled else 'disabled'}…")

    try:
        version_dir = _get_latest_version()
        settings_file = os.path.join(version_dir, "ClientSettings", "ClientAppSettings.json")
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                app_settings = json.load(f)
        except Exception:
            app_settings = {}

        if vr_enabled:
            app_settings.pop("FFlagDebugVRDisable", None)
        else:
            app_settings["FFlagDebugVRDisable"] = True

        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(app_settings, f, indent=2)
    except Exception as e:
        if status_cb:
            status_cb(f"  [vr error] {e}")
    fonts_dest = os.path.join(version_dir, "content", "fonts")
    custom_font_on  = cfg.get("custom_font", False)
    custom_font_src = cfg.get("custom_font_path", "").strip()

    if custom_font_on and custom_font_src and os.path.exists(custom_font_src):
        if status_cb:
            status_cb(f"Applying custom font: {os.path.basename(custom_font_src)}…")
        if os.path.isdir(fonts_dest):
            for fn in os.listdir(fonts_dest):
                if not fn.lower().endswith((".ttf", ".otf", ".woff", ".woff2")):
                    continue
                if any(kw in fn for kw in FONT_SKIP_KEYWORDS):
                    continue
                dest = os.path.join(fonts_dest, fn)
                try:
                    shutil.copy2(custom_font_src, dest)
                except Exception as e:
                    if status_cb:
                        status_cb(f"  [error] {fn}: {e}")
        if status_cb:
            status_cb("Custom font applied ✓")

    else:
        if status_cb:
            status_cb("Restoring default fonts…")
        if os.path.isdir(FONTS_ASSET_DEFAULT):
            _copy_folder_contents(FONTS_ASSET_DEFAULT, fonts_dest, status_cb)
            if status_cb:
                status_cb("Default fonts restored ✓")
        else:
            if status_cb:
                status_cb("  [skip] assets/fonts/default/ not found")
    fps_unlock = cfg.get("fps_unlock", False)
    if status_cb:
        status_cb(f"{'Unlocking' if fps_unlock else 'Resetting'} FPS cap…")
    try:
        settings_file = os.path.join(version_dir, "ClientSettings", "ClientAppSettings.json")
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                app_settings = json.load(f)
        except Exception:
            app_settings = {}

        if fps_unlock:
            app_settings["FFlagTaskSchedulerLimitTargetFps"] = False
            app_settings["FIntTaskSchedulerTargetFps"]       = 9999
            app_settings["DFIntTaskSchedulerTargetFps"]      = 9999
        else:
            app_settings.pop("FFlagTaskSchedulerLimitTargetFps", None)
            app_settings.pop("FIntTaskSchedulerTargetFps", None)
            app_settings.pop("DFIntTaskSchedulerTargetFps", None)

        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(app_settings, f, indent=2)
        xml_path = os.path.expandvars(r"%LOCALAPPDATA%\Roblox\GlobalBasicSettings_13.xml")
        if os.path.exists(xml_path):
            with open(xml_path, "r", encoding="utf-8") as f:
                xml_content = f.read()

            target_value = "9999" if fps_unlock else "-1"

            import re
            xml_content = re.sub(
                r'(<int name="FramerateCap">)(-?\d+)(</int>)',
                rf'\g<1>{target_value}\g<3>',
                xml_content
            )

            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(xml_content)
            if status_cb:
                status_cb(f"  GlobalBasicSettings_13.xml → FramerateCap={target_value} ✓")
        else:
            if status_cb:
                status_cb("  [skip] GlobalBasicSettings_13.xml not found")

    except Exception as e:
        if status_cb:
            status_cb(f"  [fps error] {e}")
    if cfg.get("ram_optimizer", False):
        if status_cb:
            status_cb("Optimizing RAM…")
        try:
            import psutil
            current = psutil.Process()
            current.nice(psutil.HIGH_PRIORITY_CLASS)
            for proc in psutil.process_iter(["name", "pid"]):
                if proc.info["name"] and "Roblox" in proc.info["name"]:
                    try:
                        handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, proc.info["pid"])
                        if handle:
                            ctypes.windll.psapi.EmptyWorkingSet(handle)
                            ctypes.windll.kernel32.CloseHandle(handle)
                    except Exception:
                        pass
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.psapi.EmptyWorkingSet(handle)

            if status_cb:
                status_cb("RAM optimized ✓")
        except ImportError:
            if status_cb:
                status_cb("  [skip] psutil not installed — run install_dependencies.py")
        except Exception as e:
            if status_cb:
                status_cb(f"  [ram error] {e}")

    if status_cb:
        status_cb("Mods applied ✓")