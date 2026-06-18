"""
Window Pinner V0.3 — Keep any window always on top
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
"""

import ctypes
import ctypes.wintypes as wintypes
import time
import sys
import os
import webbrowser

MY_PID = os.getpid()

# ── Windows API setup ────────────────────────────────────────────────────────
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32 # Added for power management
HWND_TOPMOST    = -1
HWND_NOTOPMOST  = -2
SWP_NOMOVE      = 0x0002
SWP_NOSIZE      = 0x0001
SWP_NOACTIVATE  = 0x0010
SWP_FLAGS       = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
SWP_SHOWWINDOW  = 0x0040

EnumWindows         = user32.EnumWindows
GetWindowText       = user32.GetWindowTextW
GetWindowTextLen    = user32.GetWindowTextLengthW
IsWindowVisible     = user32.IsWindowVisible
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
SetWindowPos        = user32.SetWindowPos
IsIconic            = user32.IsIconic

# Use GetWindowLongPtrW for 64-bit compatibility
try:
    GetWindowLongPtr = user32.GetWindowLongPtrW
    GetWindowLongPtr.restype = wintypes.LONG
except AttributeError:
    GetWindowLongPtr = user32.GetWindowLongW

GetForegroundWindow = user32.GetForegroundWindow
GetForegroundWindow.restype = wintypes.HWND
PostMessage         = user32.PostMessageW

SendMessageTimeout = user32.SendMessageTimeoutW
SendMessageTimeout.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM, wintypes.UINT, wintypes.UINT, ctypes.POINTER(wintypes.DWORD)]
SendMessageTimeout.restype = wintypes.LPARAM

ShowWindow          = user32.ShowWindow
IsWindow            = user32.IsWindow

# WinEventHook for immediate focus detection
WINEVENT_OUTOFCONTEXT = 0x0000
EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENTPROC = ctypes.WINFUNCTYPE(None, wintypes.HANDLE, wintypes.DWORD, wintypes.HWND, wintypes.LONG, wintypes.LONG, wintypes.DWORD, wintypes.DWORD)
SetWinEventHook = user32.SetWinEventHook
SetWinEventHook.restype = wintypes.HANDLE
SetWinEventHook.argtypes = [wintypes.UINT, wintypes.UINT, wintypes.HANDLE, WINEVENTPROC, wintypes.DWORD, wintypes.DWORD, wintypes.UINT]
UnhookWinEvent = user32.UnhookWinEvent

FindWindowW         = user32.FindWindowW
FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
FindWindowW.restype = wintypes.HWND

SetForegroundWindow = user32.SetForegroundWindow
SetForegroundWindow.argtypes = [wintypes.HWND]
SetForegroundWindow.restype = wintypes.BOOL

# Power management constants
ES_CONTINUOUS        = 0x80000000
ES_DISPLAY_REQUIRED  = 0x00000002
ES_SYSTEM_REQUIRED   = 0x00000001
SetThreadExecutionState = kernel32.SetThreadExecutionState
SetPriorityClass     = kernel32.SetPriorityClass
CreateMutexW         = kernel32.CreateMutexW
CreateMutexW.argtypes = [wintypes.LPCVOID, wintypes.BOOL, wintypes.LPCWSTR]
CreateMutexW.restype = wintypes.HANDLE

GetCurrentProcess    = kernel32.GetCurrentProcess
GWL_EXSTYLE  = -20
GWL_STYLE    = -16
WS_EX_TOPMOST = 0x00000008

SW_SHOWNOACTIVATE = 4

# SendMessageTimeout constants
SMTO_ABORTIFHUNG = 0x0002
HIGH_PRIORITY_CLASS = 0x00000080

# Focus maintenance constants
WM_ACTIVATE      = 0x0006
WA_ACTIVE        = 1
WA_CLICKACTIVE   = 2
WM_SETFOCUS      = 0x0007
WM_NCACTIVATE    = 0x0086
WM_MOUSEACTIVATE = 0x0021
MA_ACTIVATE      = 1
WM_LBUTTONDOWN   = 0x0201
WM_ACTIVATEAPP   = 0x001C
WM_SETCURSOR     = 0x0020
WM_QUERYNEWPALETTE = 0x0017
WM_IME_SETCONTEXT = 0x0281
WM_ENABLE        = 0x000A
WM_WINDOWPOSCHANGING = 0x0046
WM_MDIACTIVATE   = 0x0222
WM_INPUTLANGCHANGE = 0x0051
WM_IME_NOTIFY    = 0x0282
IMN_SETOPENSTATUS = 0x0008

ERROR_ALREADY_EXISTS = 183
SW_RESTORE       = 9
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

def _enum_windows_callback(hwnd, lParam):
    """Internal callback for EnumWindows to collect window data."""
    if IsWindowVisible(hwnd):
        # Exclude windows belonging to this process to prevent "Self-Pinning" loops
        pid = wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == MY_PID:
            return True

        length = GetWindowTextLen(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            GetWindowText(hwnd, buf, length + 1)
            title = buf.value.strip()
            if title and title != "Window Pinner V0.3":
                # Extract the list from lParam
                window_list = ctypes.cast(lParam, ctypes.py_object).value
                window_list.append((hwnd, title))
    return True

ENUM_WINDOWS_FUNC = EnumWindowsProc(_enum_windows_callback)

def get_windows():
    """Return list of (hwnd, title) for all visible, titled windows."""
    windows = []
    EnumWindows(ENUM_WINDOWS_FUNC, ctypes.py_object(windows))
    return windows


def is_topmost(hwnd):
    ex_style = GetWindowLongPtr(hwnd, GWL_EXSTYLE)
    return bool(ex_style & WS_EX_TOPMOST)


def set_topmost(hwnd, enable: bool):
    """Toggle topmost state for a window."""
    flag = HWND_TOPMOST if enable else HWND_NOTOPMOST
    SetWindowPos(hwnd, flag, 0, 0, 0, 0, SWP_FLAGS)


def is_admin():
    """Check if the script is running with administrative privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return False

# ── GUI ──────────────────────────────────────────────────────────────────────
try:
    import customtkinter as ctk
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])
    import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Palette
BG       = "#000000"  # Pure Black for OLED
CARD     = "#0b0b0b"  # Very dark gray for subtle depth
BORDER   = "#1f1f1f"
ACCENT   = "#3b82f6"  # Electric Blue
ACCENT2  = "#d946ef"  # Fuchsia/Pink
PINNED   = "#10b981"  # Emerald Green
MUTED    = "#4b5563"
TEXT     = "#f9fafb"  # High contrast white
SUBTEXT  = "#9ca3af"

FONT_DISPLAY = ("Segoe UI", 18, "bold")
FONT_TITLE   = ("Segoe UI", 12, "bold")
FONT_BODY    = ("Segoe UI", 12)
FONT_BODY_BOLD = ("Segoe UI", 12, "bold")
FONT_SMALL   = ("Segoe UI", 10)
FONT_MONO    = ("Consolas", 11)


class WindowRow(ctk.CTkFrame):
    """A single row in the window list."""

    def __init__(self, master, hwnd, title, pinned, toggle_cb, **kwargs):
        super().__init__(master, fg_color=CARD, corner_radius=10, **kwargs)
        self.hwnd = hwnd
        self.title = title
        self._pinned = pinned
        self.toggle_cb = toggle_cb

        self.columnconfigure(0, weight=1)

        # Status dot
        dot_color = PINNED if pinned else BORDER
        self.dot = ctk.CTkLabel(self, text="●", font=("Segoe UI", 14),
                                text_color=dot_color, width=24)
        self.dot.grid(row=0, column=0, padx=(12, 4), pady=6, sticky="w")

        # Title
        display = title if len(title) <= 45 else title[:42] + "…"
        self.lbl = ctk.CTkLabel(self, text=display, font=FONT_BODY_BOLD,
                                text_color=TEXT, anchor="w")
        self.lbl.grid(row=0, column=1, padx=(0, 20), pady=6, sticky="ew")
        self.columnconfigure(1, weight=1)

        # HWND badge
        self.hwnd_lbl = ctk.CTkLabel(self, text=f"0x{hwnd:08X}", font=FONT_MONO,
                                     text_color=MUTED, width=90)
        self.hwnd_lbl.grid(row=0, column=2, padx=8, pady=6, sticky="we")

        # Toggle Checkbox
        self._pinned_var = ctk.BooleanVar(value=pinned) # New BooleanVar for the checkbox
        self._pinned_var.trace_add("write", self._on_checkbox_toggle) # Bind to its own toggle

        self.pin_checkbox = ctk.CTkCheckBox(
            self,
            text="Pin", # Text will always be "Pin", the state is visual
            font=FONT_SMALL,
            variable=self._pinned_var,
            checkbox_width=18, checkbox_height=18,
            onvalue=True, offvalue=False,
            fg_color=PINNED, # Color when checked
            hover_color="#059669", # Hover color when checked
            border_color=BORDER, # Border color when unchecked
            text_color=TEXT,
        )
        self.pin_checkbox.grid(row=0, column=3, padx=(0, 12), pady=6, sticky="we")

    def _on_checkbox_toggle(self, *args):
        # This is called when the checkbox state changes
        new_pinned_state = self._pinned_var.get()
        if new_pinned_state != self._pinned: # Only call toggle_cb if state actually changed
            self._pinned = new_pinned_state # Update internal state
            self.toggle_cb(self.hwnd, self.title) # Notify parent

    def update_state(self, pinned):
        self._pinned = pinned
        self._pinned_var.set(pinned) # Update checkbox variable
        self.dot.configure(text_color=PINNED if pinned else BORDER) # Update dot color


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Window Pinner V0.3")
        self.geometry("620x500")
        self.minsize(520, 380)
        self.configure(fg_color=BG)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Elevate process priority to ensure the 16ms Focus Lock loop is never delayed
        try:
            SetPriorityClass(GetCurrentProcess(), HIGH_PRIORITY_CLASS)
        except Exception:
            pass

        # State
        self._all_windows: list[tuple[int, str]] = []
        self._pinned: set[int] = set()
        self._last_displayed_hwnds: list[int] = [] # Cache to prevent UI flickering
        self._rows: dict[int, WindowRow] = {}
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        self._auto_refresh_enabled = ctk.BooleanVar(value=True)
        self._refresh_interval_var = ctk.StringVar(value="15")
        self._focus_lock_enabled = ctk.BooleanVar(value=True)
        self._prevent_sleep_enabled = ctk.BooleanVar(value=False)
        self._current_execution_state = ES_CONTINUOUS # To track current power state

        # Setup Event Hook for immediate focus transition handling
        self._hook_callback = WINEVENTPROC(self._on_focus_change)
        self._hook = SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND,
            None, self._hook_callback, 0, 0, WINEVENT_OUTOFCONTEXT
        )

        self._build_ui()
        
        # Initialize live status traces after UI is built
        self._auto_refresh_enabled.trace_add("write", self._update_auto_refresh_ui)
        self._focus_lock_enabled.trace_add("write", self._update_focus_lock_ui)
        self._prevent_sleep_enabled.trace_add("write", self._toggle_prevent_sleep)
        
        # Set initial status bar states
        self._update_auto_refresh_ui()
        self._update_focus_lock_ui()
        self._toggle_prevent_sleep()
        
        self._schedule_refresh()
        self._maintain_active_state()

    # ── Build UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_rowconfigure(4, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Header ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        icon = ctk.CTkLabel(header, text="📌", font=("Segoe UI", 22))
        icon.grid(row=0, column=0, padx=(20, 8), pady=12)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(title_frame, text="Window Pinner", font=FONT_DISPLAY,
                     text_color=TEXT).pack(anchor="w")
        
        # Admin/Status indicator
        admin_status = "ADMIN MODE" if is_admin() else "User Mode (Limited)"
        status_color = PINNED if is_admin() else "#ef4444"
        ctk.CTkLabel(title_frame, text=f"V0.3 — {admin_status}",
                     font=FONT_SMALL, text_color=status_color).pack(anchor="w")

        self.pinned_badge = ctk.CTkLabel(
            header, text="0 pinned", font=("Segoe UI", 11, "bold"),
            text_color=ACCENT, fg_color="#1e2a4a", corner_radius=12,
            padx=10, pady=4
        )
        if not is_admin():
            self.pinned_badge.configure(
                text="⚠ Limited Mode",
                text_color="#f87171", fg_color="#3a1a1a"
            )
        self.pinned_badge.grid(row=0, column=2, padx=16)

        # ── Toolbar ─────────────────────────────────────────────────────────
        toolbar = ctk.CTkFrame(self, fg_color="transparent", height=44)
        toolbar.grid(row=1, column=0, sticky="ew", padx=16, pady=(8, 0))
        toolbar.grid_columnconfigure(0, weight=1)

        self.search = ctk.CTkEntry(
            toolbar, textvariable=self._search_var,
            placeholder_text="🔍  Search windows…",
            font=FONT_BODY, height=38, corner_radius=10,
            fg_color=CARD, border_color=BORDER, text_color=TEXT
        )
        self.search.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.refresh_btn = ctk.CTkButton(
            toolbar, text="↻ Refresh", font=("Segoe UI", 12, "bold"),
            width=100, height=38, corner_radius=10,
            fg_color=CARD, hover_color="#2a2d3a", border_width=1,
            border_color=ACCENT, text_color=TEXT,
            command=lambda: self._refresh_list(force=True)
        )
        self.refresh_btn.grid(row=0, column=1, padx=(0, 10))

        self.unpin_all_btn = ctk.CTkButton(
            toolbar, text="✕ Unpin All", font=("Segoe UI", 12, "bold"),
            width=100, height=38, corner_radius=10,
            fg_color="#450a0a", hover_color="#7f1d1d", border_width=0,
            text_color="#f87171",
            command=self._unpin_all
        )
        self.unpin_all_btn.grid(row=0, column=2, padx=(0, 10))

        # ── Settings Bar ────────────────────────────────────────────────────
        settings_bar = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10, height=38)
        settings_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=8)
        
        # Auto Refresh Toggle
        self.auto_refresh_cb = ctk.CTkCheckBox(
            settings_bar, text="Auto Refresh",
            font=FONT_SMALL, text_color=TEXT,
            variable=self._auto_refresh_enabled,
            checkbox_width=18, checkbox_height=18,
            onvalue=True, offvalue=False
        )
        self.auto_refresh_cb.pack(side="left", padx=15)

        # Focus Lock Toggle
        self.focus_lock_cb = ctk.CTkCheckBox(
            settings_bar, text="Focus Lock",
            font=FONT_SMALL, text_color=TEXT,
            variable=self._focus_lock_enabled,
            checkbox_width=18, checkbox_height=18,
            onvalue=True, offvalue=False
        )
        self.focus_lock_cb.pack(side="left", padx=15)

        # Interval Setting
        ctk.CTkLabel(settings_bar, text="Interval (s):", font=FONT_SMALL, text_color=SUBTEXT).pack(side="left", padx=(10, 2))
        self.interval_entry = ctk.CTkEntry(
            settings_bar, textvariable=self._refresh_interval_var,
            width=40, height=24, font=FONT_SMALL, 
            fg_color=BG, border_color=BORDER
        )
        self.interval_entry.pack(side="left", padx=8)

        # Sleep Prevention Toggle
        self.sleep_cb = ctk.CTkCheckBox(
            settings_bar, text="Sleep Prevention",
            font=FONT_SMALL, text_color=TEXT,
            variable=self._prevent_sleep_enabled,
            checkbox_width=18, checkbox_height=18,
            onvalue=True, offvalue=False
        )
        self.sleep_cb.pack(side="right", padx=15)

        # ── Column headers ───────────────────────────────────────────────────
        col_hdr = ctk.CTkFrame(self, fg_color="transparent", height=24)
        col_hdr.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 4))
        col_hdr.grid_columnconfigure(0, minsize=40) 
        col_hdr.grid_columnconfigure(1, weight=1)
        col_hdr.grid_columnconfigure(2, minsize=106) # Matches HWND (90) + padx (8)
        col_hdr.grid_columnconfigure(3, minsize=112) # Matches Button (100) + padx (0,12)

        ctk.CTkLabel(col_hdr, text="", width=24).grid(row=0, column=0, padx=(12, 4), sticky="w")
        ctk.CTkLabel(col_hdr, text="Window Title", font=FONT_SMALL,
                     text_color=MUTED).grid(row=0, column=1, padx=(0, 20), sticky="w")
        ctk.CTkLabel(col_hdr, text="Handle", font=FONT_SMALL,
                     text_color=MUTED, width=90, anchor="center").grid(row=0, column=2, padx=8, sticky="we")
        ctk.CTkLabel(col_hdr, text="Action", font=FONT_SMALL,
                     text_color=MUTED, width=100, anchor="e").grid(row=0, column=3, padx=(0, 12), sticky="we")

        # ── Scrollable window list ───────────────────────────────────────────
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=ACCENT
        )
        self.scroll.grid(row=4, column=0, sticky="nsew", padx=16, pady=0)
        self.scroll.grid_columnconfigure(0, weight=1)

        # ── Status bar ──────────────────────────────────────────────────────
        status = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=34)
        status.grid(row=5, column=0, sticky="ew")
        status.grid_columnconfigure(0, weight=1)

        self.status_lbl = ctk.CTkLabel(
            status, text="Ready", font=FONT_SMALL, text_color=SUBTEXT, anchor="w"
        )
        self.status_lbl.grid(row=0, column=0, padx=16, pady=6, sticky="w")

        self.auto_lbl = ctk.CTkLabel(
            status, text="● Auto-refresh on", font=FONT_SMALL,
            text_color=PINNED, anchor="e"
        )
        self.auto_lbl.grid(row=0, column=1, padx=(16, 8), pady=6, sticky="e")

        self.focus_status_lbl = ctk.CTkLabel(
            status, text="○ Focus Lock off", font=FONT_SMALL,
            text_color=MUTED, anchor="e"
        )
        self.focus_status_lbl.grid(row=0, column=2, padx=8, pady=6, sticky="e")

        self.sleep_status_lbl = ctk.CTkLabel(
            status, text="○ Sleep Prev. off", font=FONT_SMALL,
            text_color=MUTED, anchor="e"
        )
        self.sleep_status_lbl.grid(row=0, column=3, padx=8, pady=6, sticky="e")

        # GitHub Link
        self.github_lbl = ctk.CTkLabel(
            status, text="GitHub", font=FONT_SMALL,
            text_color=ACCENT2, anchor="e", cursor="hand2"
        )
        self.github_lbl.grid(row=0, column=4, padx=8, pady=6, sticky="e")
        self.github_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/crazykat8091/windowpinner"))

        # Credits
        self.credits_lbl = ctk.CTkLabel(
            status, text="By CrazyKat",
            font=FONT_SMALL, text_color=ACCENT, anchor="e", cursor="hand2"
        )
        self.credits_lbl.grid(row=0, column=5, padx=(8, 16), pady=6, sticky="e")
        self.credits_lbl.bind("<Button-1>", lambda e: webbrowser.open("http://www.meshcon.tech"))

    # ── Logic ────────────────────────────────────────────────────────────────

    def _update_auto_refresh_ui(self, *args):
        """Update the status label for auto-refresh immediately when toggled."""
        enabled = self._auto_refresh_enabled.get()
        self.auto_lbl.configure(
            text_color=PINNED if enabled else MUTED,
            text="● Auto-refresh on" if enabled else "○ Auto-refresh off"
        )
        status_text = "Auto-refresh enabled" if enabled else "Auto-refresh disabled"
        self.status_lbl.configure(text=status_text)
        if enabled:
            self._refresh_list()

    def _update_focus_lock_ui(self, *args):
        """Update the status bar when Focus Lock is toggled."""
        enabled = self._focus_lock_enabled.get()
        self.focus_status_lbl.configure(
            text_color=PINNED if enabled else MUTED,
            text="● Focus Lock on" if enabled else "○ Focus Lock off"
        )
        status_text = "Focus Lock heartbeat active" if enabled else "Focus Lock disabled"
        self.status_lbl.configure(text=status_text)
        if enabled:
            # Elevate process priority to ensure the 16ms loop is reliable on Win10/11
            try: SetPriorityClass(GetCurrentProcess(), HIGH_PRIORITY_CLASS)
            except: pass

    def _refresh_list(self, force=False):
        new_wins = get_windows()
        if not force and new_wins == self._all_windows:
            return # Don't rebuild if nothing changed (prevents flicker)
        
        self._all_windows = new_wins

        # sync pinned set — remove hwnds that no longer exist
        existing = {h for h, _ in self._all_windows}
        gone = self._pinned - existing
        self._pinned -= gone
        self._apply_filter()
        self._update_badge()
        self.status_lbl.configure(
            text=f"Found {len(self._all_windows)} windows  •  last refreshed just now"
        )

    def _apply_filter(self):
        query = self._search_var.get().lower()
        filtered = [
            (h, t) for h, t in self._all_windows
            if query in t.lower()
        ]

        # Pinned first, then rest
        pinned_wins  = [(h, t) for h, t in filtered if h in self._pinned]
        rest_wins    = [(h, t) for h, t in filtered if h not in self._pinned]
        final_list = pinned_wins + rest_wins
        
        # Optimization: Only rebuild widgets if the window handles or order changed
        current_hwnds = [h for h, t in final_list]
        if current_hwnds == self._last_displayed_hwnds:
            return

        self._last_displayed_hwnds = current_hwnds

        # Clear scroll frame
        for w in self.scroll.winfo_children():
            w.destroy()
        self._rows.clear()

        idx = 0
        for hwnd, title in final_list:
            row = WindowRow(
                self.scroll, hwnd, title,
                pinned=(hwnd in self._pinned),
                toggle_cb=self._toggle,
            )
            row.grid(row=idx, column=0, sticky="ew", padx=0, pady=3)
            self._rows[hwnd] = row
            idx += 1

        if not filtered:
            ctk.CTkLabel(
                self.scroll,
                text="No windows match your search.",
                font=FONT_BODY, text_color=MUTED
            ).grid(row=0, column=0, pady=40)

    def _toggle(self, hwnd, title):
        pinned = hwnd not in self._pinned
        set_topmost(hwnd, pinned)
        if pinned:
            self._pinned.add(hwnd)
        else:
            self._pinned.discard(hwnd)
        if hwnd in self._rows:
            self._rows[hwnd].update_state(pinned)
        self._update_badge()
        verb = "Pinned" if pinned else "Unpinned"
        short = title[:40] + "…" if len(title) > 40 else title
        self.status_lbl.configure(text=f"{verb}: {short}")
        # Re-sort list (pinned floats to top)
        self._apply_filter()

    def _unpin_all(self):
        for hwnd in list(self._pinned):
            set_topmost(hwnd, False)
        self._pinned.clear()
        self._apply_filter()
        self._update_badge()
        self.status_lbl.configure(text="All windows unpinned.")

    def _update_badge(self):
        n = len(self._pinned)
        self.pinned_badge.configure(text=f"{n} pinned")

    def _maintain_active_state(self):
        """Maintain topmost state and optionally spoof focus to prevent games from pausing."""
        if self._pinned:
            # Track the actual foreground window to avoid spamming the game if you are playing it
            fg_hwnd = GetForegroundWindow()
            
            # Iterate over a copy to avoid mutation issues
            for hwnd in list(self._pinned):
                if not IsWindow(hwnd):
                    continue

                # 1. Anti-Minimize: Force the window back if it tries to hide (common on Alt+Tab)
                if IsIconic(hwnd):
                    ShowWindow(hwnd, SW_RESTORE)
                
                # 2. Maintain Topmost and visibility state. 
                # Re-asserting this prevents the DWM from deprioritizing the window.
                if not is_topmost(hwnd):
                    SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS | SWP_SHOWWINDOW)

                # Skip spoofing if focus lock is off OR window is already in foreground
                if not self._focus_lock_enabled.get() or hwnd == fg_hwnd:
                    # Basic repaint keep-alive
                    PostMessage(hwnd, 0x000F, 0, 0)
                    continue

                # 3. Enhanced Asynchronous Spoofing (Focus Lock)
                try:
                    # Increased timeout to handle thread contention during app-switching
                    timeout = 25  # ms

                    # Authoritative Activation Sequence
                    SendMessageTimeout(hwnd, WM_ENABLE, 1, 0, SMTO_ABORTIFHUNG, timeout, None)
                    SendMessageTimeout(hwnd, WM_MDIACTIVATE, hwnd, 0, SMTO_ABORTIFHUNG, timeout, None) 
                    SendMessageTimeout(hwnd, WM_NCACTIVATE, 1, 0, SMTO_ABORTIFHUNG, timeout, None)
                    SendMessageTimeout(hwnd, WM_ACTIVATEAPP, 1, 0, SMTO_ABORTIFHUNG, timeout, None)
                    
                    # Mimic standard transition: Standard Active -> Click Active (The "100%" fix)
                    SendMessageTimeout(hwnd, WM_ACTIVATE, WA_ACTIVE, fg_hwnd if fg_hwnd else 0, SMTO_ABORTIFHUNG, timeout, None)
                    SendMessageTimeout(hwnd, WM_ACTIVATE, WA_CLICKACTIVE, fg_hwnd if fg_hwnd else 0, SMTO_ABORTIFHUNG, timeout, None)
                    SendMessageTimeout(hwnd, WM_SETFOCUS, 0, 0, SMTO_ABORTIFHUNG, timeout, None)

                    PostMessage(hwnd, WM_MOUSEACTIVATE, hwnd, (MA_ACTIVATE << 16) | WM_LBUTTONDOWN)
                    PostMessage(hwnd, WM_SETCURSOR, hwnd, 1)
                    # Send a tiny mouse move pulse to the top-left of the window
                    PostMessage(hwnd, 0x0200, 0, 0) # WM_MOUSEMOVE
                    
                    # 3. Enhanced Engine-specific keep-alives
                    PostMessage(hwnd, WM_QUERYNEWPALETTE, 0, 0)
                    PostMessage(hwnd, WM_IME_SETCONTEXT, 1, 0xC000000F)
                    PostMessage(hwnd, WM_IME_NOTIFY, IMN_SETOPENSTATUS, 0)
                    PostMessage(hwnd, WM_INPUTLANGCHANGE, 0, 0)
                    # Inform the engine that its window position is NOT changing (prevents auto-minimize)
                    PostMessage(hwnd, WM_WINDOWPOSCHANGING, 0, 0)
                except Exception:
                    pass

                # 4. Keep-alive signal: Request a repaint
                PostMessage(hwnd, 0x000F, 0, 0) # WM_PAINT

        # 16ms matches a 60Hz refresh rate. This ensures our "Stay Active" messages 
        # hit the game's message pump nearly every frame, preventing auto-pause logic.
        self.after(16, self._maintain_active_state)

    def _toggle_prevent_sleep(self, *args):
        """Toggle system sleep prevention."""
        enabled = self._prevent_sleep_enabled.get()
        self.sleep_status_lbl.configure(
            text_color=PINNED if enabled else MUTED,
            text="● Sleep Prev. on" if enabled else "○ Sleep Prev. off"
        )
        
        if enabled:
            # Request to keep system and display awake
            new_state = ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED
            self.status_lbl.configure(text="Sleep prevention active (Display & System)")
        else:
            # Restore default system execution state
            new_state = ES_CONTINUOUS
            self.status_lbl.configure(text="Sleep prevention disabled")

        # Only call SetThreadExecutionState if the state actually changes
        if new_state != self._current_execution_state:
            SetThreadExecutionState(new_state)
            self._current_execution_state = new_state

    def _schedule_refresh(self):
        if self._auto_refresh_enabled.get():
            self._refresh_list()
        
        # Parse and clamp interval
        try:
            val = int(self._refresh_interval_var.get())
            val = max(5, min(100, val))
        except ValueError:
            val = 5
            
        self.after(val * 1000, self._schedule_refresh)

    def _on_focus_change(self, hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
        """Triggered immediately by Windows when the foreground window changes."""
        if hwnd in self._pinned:
            # If the user just switched back to a pinned game, 
            # ensure it's restored and topmost instantly.
            if IsIconic(hwnd):
                ShowWindow(hwnd, SW_RESTORE)
            SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS | SWP_SHOWWINDOW)
            # Kick the engine with a paint message
            PostMessage(hwnd, 0x000F, 0, 0)

    def on_close(self):
        # Unpin everything on exit so windows don't stay pinned
        for hwnd in list(self._pinned):
            set_topmost(hwnd, False)
        
        # Reset system execution state if it was modified
        if self._current_execution_state != ES_CONTINUOUS:
            SetThreadExecutionState(ES_CONTINUOUS)
            print("System execution state reset to default.")
            
        if hasattr(self, '_hook') and self._hook:
            UnhookWinEvent(self._hook)
            
        self.destroy()
        sys.exit(0)


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Require Windows
    if sys.platform != "win32":
        print("Window Pinner only works on Windows.")
        sys.exit(1)
        
    # Single instance check using a named mutex
    # Using "Local\" ensures it works without special admin privileges
    _instance_mutex = CreateMutexW(None, False, "Local\\WindowPinner_SingleInstance_Mutex")
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        # Attempt to focus the existing instance before exiting
        hwnd = FindWindowW(None, "Window Pinner V0.3")
        if hwnd:
            if IsIconic(hwnd):
                ShowWindow(hwnd, SW_RESTORE)
            SetForegroundWindow(hwnd)
        sys.exit(0)

    app = App()
    app.mainloop()
