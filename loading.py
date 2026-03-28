import tkinter as tk
import threading
import time
import os

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
LOGO_PATH  = "logo.png"
LOGO_SIZE  = (80, 80)
WINDOW_W   = 480
WINDOW_H   = 280
BG_COLOR   = "#1a1a1a"
ACCENT     = "#3a7bd5"
BAR_BG     = "#2e2e2e"
BAR_FG     = "#3a7bd5"
TEXT_COLOR = "#cccccc"

class SplashScreen(tk.Toplevel):
    def __init__(self, master, flags_file: str, mods_cfg: dict, on_done=None, auth_ticket: str = ""):
        super().__init__(master)
        self.flags_file  = flags_file
        self.mods_cfg    = mods_cfg
        self.on_done     = on_done
        self.auth_ticket = auth_ticket

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=BG_COLOR)
        self.resizable(False, False)

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - WINDOW_W) // 2
        y  = (sh - WINDOW_H) // 2
        self.geometry(f"{WINDOW_W}x{WINDOW_H}+{x}+{y}")

        border = tk.Frame(self, bg="#2a2a2a")
        border.place(x=0, y=0, width=WINDOW_W, height=WINDOW_H)
        inner = tk.Frame(border, bg=BG_COLOR)
        inner.place(x=1, y=1, width=WINDOW_W - 2, height=WINDOW_H - 2)

        tk.Label(inner, text="", bg=BG_COLOR, fg="#555",
                 font=("Courier New", 7)).place(x=10, y=8)
        tk.Label(inner, text="Version: 1.1.0", bg=BG_COLOR, fg="#555",
                 font=("Courier New", 7)).place(x=WINDOW_W - 90, y=8)

        self.logo_label = tk.Label(inner, bg=BG_COLOR)
        self.logo_label.place(relx=0.5, rely=0.35, anchor="center")
        self._load_logo()

        tk.Label(inner, text="Turtlestrap", bg=BG_COLOR, fg="#ffffff",
                 font=("Courier New", 13, "bold")).place(
                     relx=0.5, rely=0.60, anchor="center")

        self.status_var = tk.StringVar(value="starting...")
        tk.Label(inner, textvariable=self.status_var,
                 bg=BG_COLOR, fg=TEXT_COLOR,
                 font=("Courier New", 9)).place(
                     relx=0.5, rely=0.69, anchor="center")

        bar_frame = tk.Frame(inner, bg=BAR_BG)
        bar_frame.place(relx=0.5, rely=0.80, anchor="center",
                        width=WINDOW_W - 80, height=6)
        self.fill = tk.Frame(bar_frame, bg=BAR_FG)
        self.fill.place(x=0, y=0, width=0, height=6)
        self.bar_track = bar_frame

        self.pct_var = tk.StringVar(value="0%")
        tk.Label(inner, textvariable=self.pct_var,
                 bg=BG_COLOR, fg="#666",
                 font=("Courier New", 7)).place(
                     relx=0.5, rely=0.87, anchor="center")

        self._cur_pct = 0
        self.after(50, self._start)
    def _load_logo(self):
        if PIL_AVAILABLE and os.path.exists(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH).convert("RGBA")
                img = img.resize(LOGO_SIZE, Image.LANCZOS)
                self._photo = ImageTk.PhotoImage(img)
                self.logo_label.configure(image=self._photo)
                return
            except Exception:
                pass
        size = LOGO_SIZE[0]
        c = tk.Canvas(self.logo_label, width=size, height=size,
                      bg=BG_COLOR, highlightthickness=0)
        c.pack()
        p = size // 6
        c.create_polygon([size//2, p, size-p, size//2,
                           size//2, size-p, p, size//2],
                         fill=ACCENT, outline="#5599ff", width=2)
        ip = size // 3
        c.create_polygon([size//2, ip, size-ip, size//2,
                           size//2, size-ip, ip, size//2],
                         fill="#1a2a4a", outline="")
    def _start(self):
        self.update_idletasks()
        self._bar_w = self.bar_track.winfo_width()
        threading.Thread(target=self._run, daemon=True).start()
    def _run(self):
        from fastflags import apply_fastflags
        from mods import apply_mods
        from roblox import launch_roblox
        steps = [
            (20,  "Applying FastFlags...",   lambda: apply_fastflags(self.flags_file)),
            (55,  "Applying mods...",        lambda: apply_mods(
                                                 self.mods_cfg,
                                                 status_cb=lambda m: self._set_status(m))),
            (75,  "Preparing environment...", None),
            (90,  "Almost ready...",          None),
            (100, "Launching Roblox...",      lambda: launch_roblox(
                                                 self.auth_ticket,
                                                 multi_instance=self.mods_cfg.get("multi_instance", False)
                                             )),
        ]

        for target_pct, label, fn in steps:
            self._set_status(label)
            if fn:
                try:
                    fn()
                except Exception as e:
                    self._set_status(f"Warning: {e}")
                    time.sleep(1.5)
            self._animate_to(target_pct)

        self._set_status("Done!")
        self.after(800, self._finish)
    def _animate_to(self, target: int):
        while self._cur_pct < target:
            self._cur_pct += 1
            w = int(self._cur_pct / 100 * self._bar_w)
            self.after(0, lambda ww=w, p=self._cur_pct: self._upd_bar(ww, p))
            time.sleep(0.013)

    def _set_status(self, msg: str):
        self.after(0, lambda m=msg: self.status_var.set(m))

    def _upd_bar(self, w: int, p: int):
        try:
            self.fill.place_configure(width=w)
            self.pct_var.set(f"{p}%")
        except tk.TclError:
            pass

    def _finish(self):
        self.destroy()
        if self.on_done:
            self.on_done()