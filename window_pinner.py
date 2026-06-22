"""
Window Pinner V0.9 — Keep any window always on top

A lightweight replacement for DisplayFusion / SpecialK's "prevent window deactivation" feature.

Copyright (c) 2024 CrazyKat (www.meshcon.tech)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files, to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.

DISCLAIMER: This utility interacts with Windows focus and messaging systems. While designed
for productivity, using this tool with certain video games may technically violate their
Terms of Service (ToS). Use at your own discretion.

Changelog V0.8:
- FIX: Removed SetForegroundWindow and AttachThreadInput from _on_focus_change entirely.
  V0.7 called _inject_focus_once(game_hwnd) inside the WinEvent hook. This created an
  infinite re-entrant loop: user clicks Chrome → hook fires → SetForegroundWindow(Forza)
  → hook fires again with Forza as new foreground → SetForegroundWindow(Forza) → loop →
  focus permanently locked on the game, impossible to switch away.
- FIX: _on_focus_change now only re-asserts HWND_TOPMOST (visual layering) when a
  non-pinned window takes foreground. No focus injection of any kind happens here.
  Focus spoofing (WM_ACTIVATE, WM_SETFOCUS etc.) is handled exclusively by the 16 ms
  heartbeat, which already skips a pinned window when it IS the real foreground window.
- KEPT from V0.7: UWP/Xbox HWND resolution via EnumChildWindows, WM_ACTIVATE lParam=0
  fix, WM_KILLFOCUS→WM_SETFOCUS deny-and-reclaim cycle, 5 ms SendMessageTimeout,
  graceful Admin/non-Admin path split.
"""

import ctypes
import ctypes.wintypes as wintypes
import sys
import os
import webbrowser
import subprocess
import threading

MY_PID = os.getpid()

# ── Windows API setup ────────────────────────────────────────────────────────

user32   = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

HWND_TOPMOST   = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE     = 0x0002
SWP_NOSIZE     = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_FLAGS      = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE

EnumWindows              = user32.EnumWindows
EnumChildWindows         = user32.EnumChildWindows
GetWindowText            = user32.GetWindowTextW
GetWindowTextLen         = user32.GetWindowTextLengthW
GetClassName             = user32.GetClassNameW
IsWindowVisible          = user32.IsWindowVisible
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
SetWindowPos             = user32.SetWindowPos
SetWindowPos.restype     = wintypes.BOOL
IsIconic                 = user32.IsIconic
ShowWindow               = user32.ShowWindow
IsWindow                 = user32.IsWindow

try:
    GetWindowLongPtr         = user32.GetWindowLongPtrW
    GetWindowLongPtr.restype = ctypes.c_long
except AttributeError:
    GetWindowLongPtr         = user32.GetWindowLongW
    GetWindowLongPtr.restype = ctypes.c_long

GetForegroundWindow          = user32.GetForegroundWindow
GetForegroundWindow.restype  = wintypes.HWND

PostMessage                  = user32.PostMessageW
PostMessage.restype          = wintypes.BOOL

SendMessageTimeout           = user32.SendMessageTimeoutW
SendMessageTimeout.argtypes  = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
    wintypes.UINT, wintypes.UINT, ctypes.POINTER(wintypes.DWORD)
]
SendMessageTimeout.restype   = wintypes.LPARAM

FindWindowW                  = user32.FindWindowW
FindWindowW.argtypes         = [wintypes.LPCWSTR, wintypes.LPCWSTR]
FindWindowW.restype          = wintypes.HWND

SetForegroundWindow          = user32.SetForegroundWindow
SetForegroundWindow.argtypes = [wintypes.HWND]
SetForegroundWindow.restype  = wintypes.BOOL

# AttachThreadInput — used ONLY in the WinEvent callback, never in the heartbeat
AttachThreadInput            = user32.AttachThreadInput
AttachThreadInput.argtypes   = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
AttachThreadInput.restype    = wintypes.BOOL

GetCurrentThreadId           = kernel32.GetCurrentThreadId
GetCurrentThreadId.restype   = wintypes.DWORD

# WinEventHook
WINEVENT_OUTOFCONTEXT   = 0x0000
EVENT_SYSTEM_FOREGROUND = 0x0003

WINEVENTPROC = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE, wintypes.DWORD, wintypes.HWND,
    wintypes.LONG,   wintypes.LONG,  wintypes.DWORD, wintypes.DWORD
)

SetWinEventHook          = user32.SetWinEventHook
SetWinEventHook.restype  = wintypes.HANDLE
SetWinEventHook.argtypes = [
    wintypes.UINT, wintypes.UINT, wintypes.HANDLE,
    WINEVENTPROC,  wintypes.DWORD, wintypes.DWORD, wintypes.UINT
]
UnhookWinEvent = user32.UnhookWinEvent

# Power / process management
ES_CONTINUOUS       = 0x80000000
ES_DISPLAY_REQUIRED = 0x00000002
ES_SYSTEM_REQUIRED  = 0x00000001

SetThreadExecutionState = kernel32.SetThreadExecutionState
SetPriorityClass        = kernel32.SetPriorityClass
CreateMutexW            = kernel32.CreateMutexW
CreateMutexW.argtypes   = [wintypes.LPCVOID, wintypes.BOOL, wintypes.LPCWSTR]
CreateMutexW.restype    = wintypes.HANDLE
GetCurrentProcess       = kernel32.GetCurrentProcess
OpenProcess             = kernel32.OpenProcess
OpenProcess.restype     = wintypes.HANDLE
CloseHandle             = kernel32.CloseHandle

HIGH_PRIORITY_CLASS               = 0x00000080
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
ERROR_ALREADY_EXISTS              = 183

GWL_EXSTYLE       = -20
WS_EX_TOPMOST     = 0x00000008
SW_RESTORE        = 9
SW_HIDE           = 0
SW_SHOWNOACTIVATE = 4

SMTO_ABORTIFHUNG = 0x0002

WM_ACTIVATE          = 0x0006
WA_ACTIVE            = 1
WA_CLICKACTIVE       = 2
WM_SETFOCUS          = 0x0007
WM_KILLFOCUS         = 0x0008
WM_NCACTIVATE        = 0x0086
WM_MOUSEACTIVATE     = 0x0021
MA_ACTIVATE          = 1
WM_LBUTTONDOWN       = 0x0201
WM_ACTIVATEAPP       = 0x001C
WM_SETCURSOR         = 0x0020
WM_QUERYNEWPALETTE   = 0x0017
WM_IME_SETCONTEXT    = 0x0281
WM_ENABLE            = 0x000A
WM_WINDOWPOSCHANGING = 0x0046
WM_MDIACTIVATE       = 0x0222
WM_INPUTLANGCHANGE   = 0x0051
WM_IME_NOTIFY        = 0x0282
IMN_SETOPENSTATUS    = 0x0008
WM_SYSCOMMAND        = 0x0112   # V0.9
SC_RESTORE           = 0xF120   # V0.9

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

# ── Dependency bootstrap ─────────────────────────────────────────────────────

def _pip_install(*packages):
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", *packages],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True
    except Exception:
        return False

def _bootstrap_deps():
    missing = []
    for pkg, imp in [("customtkinter", "customtkinter"), ("pystray", "pystray"), ("Pillow", "PIL")]:
        try:
            __import__(imp)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[Window Pinner] Installing: {', '.join(missing)} ...")
        if not _pip_install(*missing):
            import tkinter as tk
            from tkinter import messagebox
            _r = tk.Tk(); _r.withdraw()
            messagebox.showerror(
                "Missing Dependencies",
                f"Failed to auto-install: {', '.join(missing)}\n\n"
                f"Please run:\n  pip install {' '.join(missing)}\n\nthen restart."
            )
            sys.exit(1)
        print("[Window Pinner] Dependencies installed.")

_bootstrap_deps()

import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Palette ──────────────────────────────────────────────────────────────────

BG      = "#000000"
CARD    = "#0b0b0b"
BORDER  = "#1f1f1f"
ACCENT  = "#3b82f6"
ACCENT2 = "#d946ef"
PINNED  = "#10b981"
MUTED   = "#4b5563"
TEXT    = "#f9fafb"
SUBTEXT = "#9ca3af"
WARN    = "#f59e0b"

_DEFAULT_FONT = "Segoe UI" if sys.platform == "win32" else "TkDefaultFont"

FONT_DISPLAY   = (_DEFAULT_FONT, 18, "bold")
FONT_BODY      = (_DEFAULT_FONT, 12)
FONT_BODY_BOLD = (_DEFAULT_FONT, 12, "bold")
FONT_SMALL     = (_DEFAULT_FONT, 10)
FONT_MONO      = ("Consolas", 11)

# ── Helpers ──────────────────────────────────────────────────────────────────

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def restart_as_admin():
    script = os.path.abspath(sys.argv[0])
    params = " ".join(f'"{a}"' for a in sys.argv[1:])
    ret = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{script}" {params}', None, 1
    )
    return ret > 32

def _can_access_process(pid: int) -> bool:
    if pid == 0:
        return False
    h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return False
    CloseHandle(h)
    return True

def _get_class_name(hwnd) -> str:
    buf = ctypes.create_unicode_buffer(256)
    GetClassName(hwnd, buf, 256)
    return buf.value

# ── UWP/Xbox game HWND resolution ────────────────────────────────────────────
#
# Forza Horizon 6 (and other Xbox/UWP titles) run inside ApplicationFrameHost.
# The HWND that appears in EnumWindows is the shell frame window — it has the
# title bar but is NOT the game's render window. SetWindowPos on the frame works
# for always-on-top, but focus messages must go to the inner CoreWindow HWND.
#
# We walk child windows looking for "Windows.UI.Core.CoreWindow" or
# "ApplicationFrameInputSinkWindow", which are the real game surfaces.
#
# UWP_FRAME_CLASS  — the outer ApplicationFrameHost shell
# UWP_CORE_CLASSES — candidate inner-game window class names

UWP_FRAME_CLASS  = "ApplicationFrameWindow"
UWP_CORE_CLASSES = {
    "Windows.UI.Core.CoreWindow",
    "ApplicationFrameInputSinkWindow",
    "GAME_WINDOW",          # some Win32 games hosted in GameBar
}

def _resolve_game_hwnd(hwnd: int) -> int:
    """
    If hwnd belongs to an ApplicationFrameHost UWP shell, return the real
    inner game HWND. Otherwise return hwnd unchanged.
    """
    if _get_class_name(hwnd) != UWP_FRAME_CLASS:
        return hwnd

    found = [hwnd]  # fallback to the frame if no inner HWND found

    def _child_cb(child_hwnd, _lParam):
        cls = _get_class_name(child_hwnd)
        if cls in UWP_CORE_CLASSES:
            found[0] = child_hwnd
            return False  # stop enumeration
        return True

    cb = EnumWindowsProc(_child_cb)
    EnumChildWindows(hwnd, cb, 0)
    return found[0]


def _enum_windows_callback(hwnd, lParam):
    if not IsWindowVisible(hwnd):
        return True
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == MY_PID:
        return True
    length = GetWindowTextLen(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowText(hwnd, buf, length + 1)
        title = buf.value.strip()
        if title and title != "Window Pinner V0.9":
            ctypes.cast(lParam, ctypes.py_object).value.append((hwnd, title, pid.value))
    return True

ENUM_WINDOWS_FUNC = EnumWindowsProc(_enum_windows_callback)

def get_windows() -> list[tuple[int, str, int]]:
    windows: list[tuple[int, str, int]] = []
    EnumWindows(ENUM_WINDOWS_FUNC, ctypes.py_object(windows))
    return windows

def is_topmost(hwnd) -> bool:
    return bool(GetWindowLongPtr(hwnd, GWL_EXSTYLE) & WS_EX_TOPMOST)

def set_topmost(hwnd, enable: bool) -> bool:
    flag = HWND_TOPMOST if enable else HWND_NOTOPMOST
    ok   = SetWindowPos(hwnd, flag, 0, 0, 0, 0, SWP_FLAGS)
    if not ok and enable:
        ok = SetWindowPos(hwnd, flag, 0, 0, 0, 0, SWP_FLAGS | SWP_SHOWWINDOW)
    return bool(ok)

# ── AttachThreadInput focus injection (event-only, NOT in heartbeat) ──────────

def _inject_focus_once(hwnd: int) -> bool:
    """
    Called ONLY from _on_focus_change (the WinEvent callback) — fires once per
    actual foreground-change event, NOT from the 16 ms heartbeat loop.

    Temporarily attaches our input queue to the target thread, then calls
    SetForegroundWindow to commit a genuine focus token. The game's own
    GetForegroundWindow() will return itself.

    Safe because:
    - Called at most once per real focus-change (not 60x/sec)
    - AttachThreadInput is immediately undone after SetForegroundWindow
    - No keyboard/macro input is in flight during the brief attachment
    """
    try:
        my_tid     = GetCurrentThreadId()
        target_tid = GetWindowThreadProcessId(hwnd, None)
        if target_tid == 0 or target_tid == my_tid:
            return False
        AttachThreadInput(my_tid, target_tid, True)
        try:
            ok = bool(SetForegroundWindow(hwnd))
        finally:
            AttachThreadInput(my_tid, target_tid, False)
        return ok
    except Exception:
        return False

# ── Tray icon ─────────────────────────────────────────────────────────────────

def _make_tray_icon(pinned_count: int = 0) -> Image.Image:
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill=(15, 15, 15, 255), outline=(59, 130, 246, 255), width=3)
    draw.rectangle([30, 38, 34, 58], fill=(249, 250, 251, 220))
    draw.ellipse([20, 12, 44, 36], fill=(59, 130, 246, 255))
    if pinned_count > 0:
        draw.ellipse([42, 2, 62, 22], fill=(16, 185, 129, 255))
        label = str(pinned_count) if pinned_count < 10 else "+"
        try:
            from PIL import ImageFont
            font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((52 - tw // 2, 12 - th // 2), label, fill=(0, 0, 0, 255), font=font)
        except Exception:
            pass
    return img

# ── WindowRow widget ──────────────────────────────────────────────────────────

class WindowRow(ctk.CTkFrame):
    def __init__(self, master, hwnd, title, pid, pinned, accessible, toggle_cb, **kwargs):
        super().__init__(master, fg_color=CARD, corner_radius=10, **kwargs)
        self.hwnd        = hwnd
        self.title       = title
        self.pid         = pid
        self._pinned     = pinned
        self._accessible = accessible
        self.toggle_cb   = toggle_cb

        self.columnconfigure(0, weight=1)

        dot_color = PINNED if pinned else (WARN if not accessible else BORDER)
        self.dot  = ctk.CTkLabel(self, text="●", font=(_DEFAULT_FONT, 14),
                                  text_color=dot_color, width=24)
        self.dot.grid(row=0, column=0, padx=(12, 4), pady=6, sticky="w")

        display = title if len(title) <= 45 else title[:42] + "…"
        if not accessible:
            display = "🔒 " + display

        self.lbl = ctk.CTkLabel(self, text=display, font=FONT_BODY_BOLD,
                                 text_color=TEXT if accessible else SUBTEXT, anchor="w")
        self.lbl.grid(row=0, column=1, padx=(0, 20), pady=6, sticky="ew")
        self.columnconfigure(1, weight=1)

        self.hwnd_lbl = ctk.CTkLabel(self, text=f"0x{hwnd:08X}", font=FONT_MONO,
                                      text_color=MUTED, width=90)
        self.hwnd_lbl.grid(row=0, column=2, padx=8, pady=6, sticky="we")

        self._pinned_var = ctk.BooleanVar(value=pinned)
        self._pinned_var.trace_add("write", self._on_checkbox_toggle)

        self.pin_checkbox = ctk.CTkCheckBox(
            self, text="Pin", font=FONT_SMALL,
            variable=self._pinned_var,
            checkbox_width=18, checkbox_height=18,
            onvalue=True, offvalue=False,
            fg_color=PINNED, hover_color="#059669",
            border_color=BORDER, text_color=TEXT,
            state="normal" if accessible else "disabled",
        )
        self.pin_checkbox.grid(row=0, column=3, padx=(0, 12), pady=6, sticky="we")

    def _on_checkbox_toggle(self, *args):
        new_state = self._pinned_var.get()
        if new_state != self._pinned:
            self._pinned = new_state
            self.toggle_cb(self.hwnd, self.title)

    def update_state(self, pinned):
        self._pinned = pinned
        self._pinned_var.set(pinned)
        self.dot.configure(
            text_color=PINNED if pinned else (WARN if not self._accessible else BORDER)
        )

# ── Main App ──────────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Window Pinner V0.9")
        self.geometry("640x520")
        self.minsize(520, 380)
        self.configure(fg_color=BG)
        self.protocol("WM_DELETE_WINDOW", self._hide_to_tray)

        try:
            SetPriorityClass(GetCurrentProcess(), HIGH_PRIORITY_CLASS)
        except Exception:
            pass

        self._all_windows: list[tuple[int, str, int]] = []
        self._pinned: set[int]         = set()
        # Maps frame_hwnd → real_game_hwnd for UWP games
        self._hwnd_map: dict[int, int] = {}
        self._last_displayed_hwnds: list[int] = []
        self._rows: dict[int, WindowRow]       = {}
        self._tray_icon: pystray.Icon | None   = None
        self._tray_thread: threading.Thread | None = None
        self._hidden = False

        self._search_var            = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        self._auto_refresh_enabled  = ctk.BooleanVar(value=True)
        self._refresh_interval_var  = ctk.StringVar(value="15")
        self._focus_lock_enabled    = ctk.BooleanVar(value=True)
        self._prevent_sleep_enabled = ctk.BooleanVar(value=False)
        self._current_execution_state = ES_CONTINUOUS

        self._hook_callback = WINEVENTPROC(self._on_focus_change)
        self._hook = SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND,
            None, self._hook_callback, 0, 0, WINEVENT_OUTOFCONTEXT
        )

        self._build_ui()

        self._auto_refresh_enabled.trace_add("write",  self._update_auto_refresh_ui)
        self._focus_lock_enabled.trace_add("write",    self._update_focus_lock_ui)
        self._prevent_sleep_enabled.trace_add("write", self._toggle_prevent_sleep)

        self._update_auto_refresh_ui()
        self._update_focus_lock_ui()
        self._toggle_prevent_sleep()

        self._schedule_refresh()
        self._maintain_active_state()
        self._start_tray()

    # ── Tray ─────────────────────────────────────────────────────────────────

    def _build_tray_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("📌 Window Pinner V0.9", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Show Window", self._show_from_tray, default=True),
            pystray.MenuItem("Unpin All",   self._tray_unpin_all),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit",        self._tray_exit),
        )

    def _start_tray(self):
        self._tray_icon = pystray.Icon(
            name  = "WindowPinner",
            icon  = _make_tray_icon(len(self._pinned)),
            title = self._tray_tooltip(),
            menu  = self._build_tray_menu(),
        )
        self._tray_icon.on_activate = lambda icon: self._show_from_tray(icon)
        self._tray_thread = threading.Thread(
            target=self._tray_icon.run, daemon=True, name="TrayThread"
        )
        self._tray_thread.start()

    def _tray_tooltip(self) -> str:
        n = len(self._pinned)
        return f"Window Pinner • {n} pinned" if n else "Window Pinner"

    def _update_tray(self):
        if self._tray_icon and self._tray_icon.visible:
            self._tray_icon.icon  = _make_tray_icon(len(self._pinned))
            self._tray_icon.title = self._tray_tooltip()

    def _hide_to_tray(self):
        self._hidden = True
        self.withdraw()
        if hasattr(self, "_first_tray_hide"):
            return
        self._first_tray_hide = True
        try:
            self._tray_icon.notify(
                "Window Pinner is still running.\nDouble-click the tray icon to restore.",
                "Minimized to Tray"
            )
        except Exception:
            pass

    def _show_from_tray(self, icon=None):
        self.after(0, self._do_show)

    def _do_show(self):
        self._hidden = False
        self.deiconify()
        self.lift()
        self.focus_force()

    def _tray_unpin_all(self, icon=None):
        self.after(0, self._unpin_all)

    def _tray_exit(self, icon=None):
        self.after(0, self._full_exit)

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_rowconfigure(4, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text="📌", font=(_DEFAULT_FONT, 22)).grid(
            row=0, column=0, padx=(20, 8), pady=12)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(title_frame, text="Window Pinner",
                     font=FONT_DISPLAY, text_color=TEXT).pack(anchor="w")
        admin_status = "ADMIN MODE" if is_admin() else "User Mode (Limited)"
        status_color = PINNED if is_admin() else "#ef4444"
        ctk.CTkLabel(title_frame, text=f"V0.8 — {admin_status}",
                     font=FONT_SMALL, text_color=status_color).pack(anchor="w")

        self.pinned_badge = ctk.CTkLabel(
            header, text="0 pinned", font=(_DEFAULT_FONT, 11, "bold"),
            text_color=ACCENT, fg_color="#1e2a4a", corner_radius=12, padx=10, pady=4
        )
        if not is_admin():
            self.pinned_badge.configure(text="⚠ Limited Mode",
                                        text_color="#f87171", fg_color="#3a1a1a")
        self.pinned_badge.grid(row=0, column=2, padx=4)

        ctk.CTkLabel(header, text="✕ minimizes to tray",
                     font=(_DEFAULT_FONT, 9), text_color=MUTED).grid(row=0, column=3, padx=4)

        if not is_admin():
            ctk.CTkButton(
                header, text="🔑 Run as Admin",
                font=FONT_SMALL, width=110, height=28, corner_radius=8,
                fg_color="#7f1d1d", hover_color="#991b1b", text_color="#fca5a5",
                command=self._request_elevation
            ).grid(row=0, column=4, padx=(4, 16))

        # Toolbar
        toolbar = ctk.CTkFrame(self, fg_color="transparent", height=44)
        toolbar.grid(row=1, column=0, sticky="ew", padx=16, pady=(8, 0))
        toolbar.grid_columnconfigure(0, weight=1)

        self.search = ctk.CTkEntry(
            toolbar, textvariable=self._search_var,
            placeholder_text="🔍 Search windows…",
            font=FONT_BODY, height=38, corner_radius=10,
            fg_color=CARD, border_color=BORDER, text_color=TEXT
        )
        self.search.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        ctk.CTkButton(
            toolbar, text="↻ Refresh", font=(_DEFAULT_FONT, 12, "bold"),
            width=100, height=38, corner_radius=10,
            fg_color=CARD, hover_color="#2a2d3a", border_width=1,
            border_color=ACCENT, text_color=TEXT,
            command=lambda: self._refresh_list(force=True)
        ).grid(row=0, column=1, padx=(0, 10))

        ctk.CTkButton(
            toolbar, text="✕ Unpin All", font=(_DEFAULT_FONT, 12, "bold"),
            width=100, height=38, corner_radius=10,
            fg_color="#450a0a", hover_color="#7f1d1d", border_width=0,
            text_color="#f87171", command=self._unpin_all
        ).grid(row=0, column=2, padx=(0, 10))

        # Settings bar
        settings_bar = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10, height=38)
        settings_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=8)

        for text, var in [
            ("Auto Refresh", self._auto_refresh_enabled),
            ("Focus Lock",   self._focus_lock_enabled),
        ]:
            ctk.CTkCheckBox(
                settings_bar, text=text, font=FONT_SMALL, text_color=TEXT,
                variable=var, checkbox_width=18, checkbox_height=18,
                onvalue=True, offvalue=False
            ).pack(side="left", padx=15)

        ctk.CTkLabel(settings_bar, text="Interval (s):",
                     font=FONT_SMALL, text_color=SUBTEXT).pack(side="left", padx=(10, 2))
        ctk.CTkEntry(
            settings_bar, textvariable=self._refresh_interval_var,
            width=40, height=24, font=FONT_SMALL, fg_color=BG, border_color=BORDER
        ).pack(side="left", padx=8)

        ctk.CTkCheckBox(
            settings_bar, text="Sleep Prevention", font=FONT_SMALL, text_color=TEXT,
            variable=self._prevent_sleep_enabled,
            checkbox_width=18, checkbox_height=18, onvalue=True, offvalue=False
        ).pack(side="right", padx=15)

        # Column headers
        col_hdr = ctk.CTkFrame(self, fg_color="transparent", height=24)
        col_hdr.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 4))
        col_hdr.grid_columnconfigure(0, minsize=40)
        col_hdr.grid_columnconfigure(1, weight=1)
        col_hdr.grid_columnconfigure(2, minsize=106)
        col_hdr.grid_columnconfigure(3, minsize=112)

        ctk.CTkLabel(col_hdr, text="", width=24).grid(
            row=0, column=0, padx=(12, 4), sticky="w")
        ctk.CTkLabel(col_hdr, text="Window Title",
                     font=FONT_SMALL, text_color=MUTED).grid(
            row=0, column=1, padx=(0, 20), sticky="w")
        ctk.CTkLabel(col_hdr, text="Handle", font=FONT_SMALL, text_color=MUTED,
                     width=90, anchor="center").grid(row=0, column=2, padx=8, sticky="we")
        ctk.CTkLabel(col_hdr, text="Action", font=FONT_SMALL, text_color=MUTED,
                     width=100, anchor="e").grid(row=0, column=3, padx=(0, 12), sticky="we")

        # Scrollable list
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=ACCENT
        )
        self.scroll.grid(row=4, column=0, sticky="nsew", padx=16, pady=0)
        self.scroll.grid_columnconfigure(0, weight=1)

        # Status bar
        status = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=34)
        status.grid(row=5, column=0, sticky="ew")
        status.grid_columnconfigure(0, weight=1)

        self.status_lbl = ctk.CTkLabel(status, text="Ready", font=FONT_SMALL,
                                        text_color=SUBTEXT, anchor="w")
        self.status_lbl.grid(row=0, column=0, padx=16, pady=6, sticky="w")

        self.auto_lbl = ctk.CTkLabel(status, text="● Auto-refresh on",
                                      font=FONT_SMALL, text_color=PINNED, anchor="e")
        self.auto_lbl.grid(row=0, column=1, padx=(16, 8), pady=6, sticky="e")

        self.focus_status_lbl = ctk.CTkLabel(status, text="○ Focus Lock off",
                                              font=FONT_SMALL, text_color=MUTED, anchor="e")
        self.focus_status_lbl.grid(row=0, column=2, padx=8, pady=6, sticky="e")

        self.sleep_status_lbl = ctk.CTkLabel(status, text="○ Sleep Prev. off",
                                              font=FONT_SMALL, text_color=MUTED, anchor="e")
        self.sleep_status_lbl.grid(row=0, column=3, padx=8, pady=6, sticky="e")

        gh = ctk.CTkLabel(status, text="GitHub", font=FONT_SMALL,
                           text_color=ACCENT2, anchor="e", cursor="hand2")
        gh.grid(row=0, column=4, padx=8, pady=6, sticky="e")
        gh.bind("<Button-1>", lambda e: webbrowser.open(
            "https://github.com/crazykat8091/windowpinner"))

        cr = ctk.CTkLabel(status, text="By CrazyKat", font=FONT_SMALL,
                           text_color=ACCENT, anchor="e", cursor="hand2")
        cr.grid(row=0, column=5, padx=(8, 16), pady=6, sticky="e")
        cr.bind("<Button-1>", lambda e: webbrowser.open("http://www.meshcon.tech"))

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _request_elevation(self):
        from tkinter import messagebox
        if messagebox.askyesno(
            "Restart as Administrator",
            "Window Pinner needs Administrator privileges to pin games\n"
            "and protected applications.\n\nRestart now with elevated permissions?"
        ):
            if restart_as_admin():
                self._full_exit()
            else:
                messagebox.showerror(
                    "Error",
                    "Could not restart as Administrator.\n"
                    "Please right-click the script and choose 'Run as administrator'."
                )

    def _update_auto_refresh_ui(self, *args):
        enabled = self._auto_refresh_enabled.get()
        self.auto_lbl.configure(
            text_color=PINNED if enabled else MUTED,
            text="● Auto-refresh on" if enabled else "○ Auto-refresh off"
        )
        self.status_lbl.configure(
            text="Auto-refresh enabled" if enabled else "Auto-refresh disabled")
        if enabled:
            self._refresh_list()

    def _update_focus_lock_ui(self, *args):
        enabled = self._focus_lock_enabled.get()
        if enabled:
            mode  = "Enhanced" if is_admin() else "Basic"
            label = f"● Focus Lock on ({mode})"
            desc  = f"Focus Lock active — {mode} mode"
        else:
            label = "○ Focus Lock off"
            desc  = "Focus Lock disabled"
        self.focus_status_lbl.configure(
            text_color=PINNED if enabled else MUTED, text=label)
        self.status_lbl.configure(text=desc)
        if enabled:
            try:
                SetPriorityClass(GetCurrentProcess(), HIGH_PRIORITY_CLASS)
            except Exception:
                pass

    def _refresh_list(self, force=False):
        new_wins      = get_windows()
        new_hwnd_set  = {h for h, _, _ in new_wins}
        prev_hwnd_set = {h for h, _, _ in self._all_windows}

        if not force and new_hwnd_set == prev_hwnd_set:
            title_map = {h: t for h, t, _ in new_wins}
            for hwnd, row in self._rows.items():
                new_title = title_map.get(hwnd, row.title)
                if new_title != row.title:
                    row.title  = new_title
                    display    = new_title if len(new_title) <= 45 else new_title[:42] + "…"
                    if not row._accessible:
                        display = "🔒 " + display
                    row.lbl.configure(text=display)
            self._all_windows = new_wins
            return

        self._all_windows = new_wins
        existing          = {h for h, _, _ in self._all_windows}
        self._pinned     -= (self._pinned - existing)
        # Clean stale hwnd_map entries
        self._hwnd_map    = {k: v for k, v in self._hwnd_map.items() if k in existing}
        self._apply_filter()
        self._update_badge()
        self.status_lbl.configure(
            text=f"Found {len(self._all_windows)} windows • last refreshed just now"
        )

    def _apply_filter(self):
        query       = self._search_var.get().lower()
        filtered    = [(h, t, p) for h, t, p in self._all_windows if query in t.lower()]
        pinned_wins = [(h, t, p) for h, t, p in filtered if h in self._pinned]
        rest_wins   = [(h, t, p) for h, t, p in filtered if h not in self._pinned]
        final_list  = pinned_wins + rest_wins

        current_hwnds = [h for h, _, _ in final_list]
        if current_hwnds == self._last_displayed_hwnds:
            return
        self._last_displayed_hwnds = current_hwnds

        for w in self.scroll.winfo_children():
            w.destroy()
        self._rows.clear()

        _admin = is_admin()
        for idx, (hwnd, title, pid) in enumerate(final_list):
            accessible = _admin or _can_access_process(pid)
            row = WindowRow(
                self.scroll, hwnd, title, pid,
                pinned=(hwnd in self._pinned),
                accessible=accessible,
                toggle_cb=self._toggle,
            )
            row.grid(row=idx, column=0, sticky="ew", padx=0, pady=3)
            self._rows[hwnd] = row

        if not filtered:
            ctk.CTkLabel(self.scroll, text="No windows match your search.",
                         font=FONT_BODY, text_color=MUTED).grid(row=0, column=0, pady=40)

    def _toggle(self, hwnd, title):
        pinned = hwnd not in self._pinned

        if pinned:
            # Resolve the real game HWND for UWP/Xbox titles
            real_hwnd = _resolve_game_hwnd(hwnd)
            self._hwnd_map[hwnd] = real_hwnd

            # Pin both the frame (for visual always-on-top) and the inner HWND
            ok = set_topmost(hwnd, True)
            if real_hwnd != hwnd:
                set_topmost(real_hwnd, True)
            self._pinned.add(hwnd)
        else:
            real_hwnd = self._hwnd_map.pop(hwnd, hwnd)
            set_topmost(hwnd, False)
            if real_hwnd != hwnd:
                set_topmost(real_hwnd, False)
            ok = True
            self._pinned.discard(hwnd)

        if hwnd in self._rows:
            self._rows[hwnd].update_state(pinned)
        self._update_badge()

        short = title[:40] + "…" if len(title) > 40 else title
        if not ok and pinned:
            self.status_lbl.configure(
                text=f"⚠ Could not pin '{short}' — try running as Administrator",
                text_color=WARN
            )
        else:
            verb = "Pinned" if pinned else "Unpinned"
            suffix = " (UWP inner HWND)" if (pinned and self._hwnd_map.get(hwnd) != hwnd) else ""
            self.status_lbl.configure(
                text=f"{verb}: {short}{suffix}", text_color=SUBTEXT)
        self._apply_filter()

    def _unpin_all(self):
        for hwnd in list(self._pinned):
            real_hwnd = self._hwnd_map.pop(hwnd, hwnd)
            set_topmost(hwnd, False)
            if real_hwnd != hwnd:
                set_topmost(real_hwnd, False)
        self._pinned.clear()
        self._apply_filter()
        self._update_badge()
        self.status_lbl.configure(text="All windows unpinned.", text_color=SUBTEXT)

    def _update_badge(self):
        n = len(self._pinned)
        self.pinned_badge.configure(text=f"{n} pinned")
        self._update_tray()

    # ── Heartbeat (120 Hz) ────────────────────────────────────────────────────
    #
    # Rules to avoid macro key conflicts:
    #   - NO mouse messages (WM_MOUSEACTIVATE, WM_SETCURSOR, WM_MOUSEMOVE,
    #     WM_LBUTTONDOWN). Macro apps (AHK, GHUB, Synapse) intercept these
    #     globally. Fake mouse messages trigger macros unintentionally.
    #   - NO WM_INPUTLANGCHANGE. Macro apps watch this to switch hotkey profiles.
    #     Sending it randomly can flip the active profile mid-game.
    #   - NO WM_IME_SETCONTEXT / WM_IME_NOTIFY. IME-aware macro apps react to
    #     these for CJK input-mode switching.
    #   - NO AttachThreadInput / SetForegroundWindow in the loop. Merging input
    #     queues even briefly from the Tk main thread delays the pystray and
    #     keyboard hook callbacks that macro apps rely on.
    #
    # What we DO send: pure window-activation messages only. These go directly
    # to the game's message queue and are not intercepted by input hook chains.
    #
    # Added: WM_SYSCOMMAND SC_RESTORE — some game engines (UE4/UE5, Unity
    # IL2CPP) resume audio/physics on this, not on WM_ACTIVATE alone.

    def _maintain_active_state(self):
        if self._pinned:
            fg_hwnd    = GetForegroundWindow()
            focus_lock = self._focus_lock_enabled.get()

            for hwnd in list(self._pinned):
                if not IsWindow(hwnd):
                    continue

                # Resolve real HWND for UWP games
                real_hwnd = self._hwnd_map.get(hwnd, hwnd)

                # Re-assert topmost on frame + inner HWND
                if IsIconic(hwnd) and hwnd != fg_hwnd:
                    ShowWindow(hwnd, SW_SHOWNOACTIVATE)
                if not is_topmost(hwnd):
                    SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS | SWP_SHOWWINDOW)
                if real_hwnd != hwnd and not is_topmost(real_hwnd):
                    SetWindowPos(real_hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS | SWP_SHOWWINDOW)

                target = real_hwnd

                # Skip focus spoofing if game already IS the foreground
                if not focus_lock or target == fg_hwnd:
                    continue

                pid = wintypes.DWORD()
                GetWindowThreadProcessId(target, ctypes.byref(pid))
                accessible = is_admin() and _can_access_process(pid.value)

                t = 5  # ms — tight timeout; never stalls the 8 ms loop

                # ── Pure activation sequence (no mouse, no IME, no input-lang) ──
                #
                # 1. KILLFOCUS → SETFOCUS: deny-and-reclaim.
                #    Games watching for absence of KILLFOCUS see it arrive and
                #    immediately see SETFOCUS — net: "I never lost focus."
                PostMessage(target, WM_KILLFOCUS, 0, 0)
                PostMessage(target, WM_SETFOCUS,  0, 0)

                if accessible:
                    # 2. NCACTIVATE(1): non-client area draws as active
                    SendMessageTimeout(target, WM_NCACTIVATE,  1, 0, SMTO_ABORTIFHUNG, t, None)
                    # 3. ACTIVATEAPP(1): process is active
                    SendMessageTimeout(target, WM_ACTIVATEAPP, 1, 0, SMTO_ABORTIFHUNG, t, None)
                    # 4. ACTIVATE(WA_ACTIVE, lParam=0): standard focus grant.
                    #    lParam=0 is critical — passing fg_hwnd lets games detect
                    #    the foreign HWND and flag the message as spoofed.
                    SendMessageTimeout(target, WM_ACTIVATE, WA_ACTIVE, 0, SMTO_ABORTIFHUNG, t, None)
                    # 5. SETFOCUS: explicit keyboard focus grant
                    SendMessageTimeout(target, WM_SETFOCUS,  0, 0, SMTO_ABORTIFHUNG, t, None)
                    # 6. SC_RESTORE: UE4/UE5 and Unity IL2CPP resume audio/physics
                    #    on this syscommand, not on WM_ACTIVATE alone.
                    PostMessage(target, WM_SYSCOMMAND, SC_RESTORE, 0)
                else:
                    # Basic path (User Mode / inaccessible process)
                    SendMessageTimeout(target, WM_NCACTIVATE,  1, 0, SMTO_ABORTIFHUNG, t, None)
                    SendMessageTimeout(target, WM_ACTIVATEAPP, 1, 0, SMTO_ABORTIFHUNG, t, None)
                    SendMessageTimeout(target, WM_ACTIVATE, WA_ACTIVE, 0, SMTO_ABORTIFHUNG, t, None)
                    SendMessageTimeout(target, WM_SETFOCUS,  0, 0, SMTO_ABORTIFHUNG, t, None)
                    PostMessage(target, WM_SYSCOMMAND, SC_RESTORE, 0)

        self.after(8, self._maintain_active_state)  # 120 Hz

    def _toggle_prevent_sleep(self, *args):
        enabled   = self._prevent_sleep_enabled.get()
        new_state = (ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED) if enabled else ES_CONTINUOUS
        self.sleep_status_lbl.configure(
            text_color=PINNED if enabled else MUTED,
            text="● Sleep Prev. on" if enabled else "○ Sleep Prev. off"
        )
        self.status_lbl.configure(
            text="Sleep prevention active" if enabled else "Sleep prevention disabled")
        if new_state != self._current_execution_state:
            SetThreadExecutionState(new_state)
            self._current_execution_state = new_state

    def _schedule_refresh(self):
        if self._auto_refresh_enabled.get():
            self._refresh_list()
        try:
            val = max(5, min(100, int(self._refresh_interval_var.get())))
        except ValueError:
            val = 5
        self.after(val * 1000, self._schedule_refresh)

    def _on_focus_change(self, hWinEventHook, event, hwnd, idObject, idChild,
                         dwEventThread, dwmsEventTime):
        """
        Fires when any window becomes foreground.

        We use this ONLY to re-assert HWND_TOPMOST on pinned windows when something
        else takes the foreground — e.g. a dialog or a new window that pops up above
        a pinned window.

        We do NOT call SetForegroundWindow or AttachThreadInput here.
        Doing so would create an infinite re-entrant loop:
          user clicks X → hook fires → SetForegroundWindow(game) → hook fires again
          → SetForegroundWindow(game) → ... → focus locked on game forever.

        Focus spoofing (WM_ACTIVATE etc.) is handled entirely by the 16 ms heartbeat.
        That loop already checks `if target == fg_hwnd: skip`, so it only sends
        messages when the game is NOT the real foreground — which is exactly right.
        """
        if not hwnd:
            return

        # hwnd is the window that just became foreground.
        # If it IS one of our pinned windows (or its inner real HWND), nothing to do —
        # topmost is already set and we must not call SetForegroundWindow (re-entrancy).
        for frame_hwnd in self._pinned:
            real_hwnd = self._hwnd_map.get(frame_hwnd, frame_hwnd)
            if hwnd == frame_hwnd or hwnd == real_hwnd:
                return  # the pinned window itself just got focus — leave it alone

        # A non-pinned window just took foreground. Re-assert topmost on all pinned
        # windows so they stay visually above it. No focus calls — just layering.
        for frame_hwnd in self._pinned:
            if not IsWindow(frame_hwnd):
                continue
            real_hwnd = self._hwnd_map.get(frame_hwnd, frame_hwnd)
            if IsIconic(frame_hwnd):
                ShowWindow(frame_hwnd, SW_SHOWNOACTIVATE)
            SetWindowPos(frame_hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS)
            if real_hwnd != frame_hwnd:
                SetWindowPos(real_hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS)

    def _full_exit(self):
        for hwnd in list(self._pinned):
            real_hwnd = self._hwnd_map.get(hwnd, hwnd)
            set_topmost(hwnd, False)
            if real_hwnd != hwnd:
                set_topmost(real_hwnd, False)
        if self._current_execution_state != ES_CONTINUOUS:
            SetThreadExecutionState(ES_CONTINUOUS)
        if hasattr(self, "_hook") and self._hook:
            UnhookWinEvent(self._hook)
        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass
        sys.exit(0)

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if sys.platform != "win32":
        print("Window Pinner only works on Windows.")
        sys.exit(1)

    _instance_mutex = CreateMutexW(None, False, "Local\\WindowPinner_SingleInstance_Mutex")
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        hwnd = FindWindowW(None, "Window Pinner V0.9")
        if hwnd:
            if IsIconic(hwnd):
                ShowWindow(hwnd, SW_RESTORE)
            SetForegroundWindow(hwnd)
        sys.exit(0)

    app = App()
    app.mainloop()
