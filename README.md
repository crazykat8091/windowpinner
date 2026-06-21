# 📌 Window Pinner

**Version 0.7** — A lightweight Windows utility to keep any window always on top and prevent background apps or games from pausing when they lose focus.

> **Author:** CrazyKat | **License:** MIT | [GitHub](https://github.com/crazykat8091/windowpinner) | [meshcon.tech](http://www.meshcon.tech)

---

## 🖼️ Overview

Window Pinner gives you fine-grained control over window layering and focus behavior on Windows 10/11. Whether you want a calculator floating above your game, a stream overlay staying visible, or a background app that thinks it's still active — Window Pinner handles it in a single lightweight Python script with a clean dark GUI.

It is a **free, open-source alternative** to paid tools like DisplayFusion or SpecialK for the specific use case of "always on top + focus spoofing."

**V0.7 introduces UWP / Xbox App support and Input Hook Safety.** It adds automatic child window resolution for UWP containers (`ApplicationFrameWindow` -> `Windows.UI.Core.CoreWindow`), enabling pinning of games like Forza Horizon 6. It also isolates `AttachThreadInput` to run strictly on focus change events to eliminate program switching (Alt-Tab) lockups and macro key conflicts.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📍 **Always on Top** | Force any visible window to stay above all others using the Win32 `SetWindowPos` API |
| 🔒 **Focus Lock (Enhanced)** | Uses `AttachThreadInput` to inject a genuine focus token into the target process thread. Games cannot distinguish this from a real focus event. Requires Admin. |
| 🔒 **Focus Lock (Basic)** | Falls back to Win32 message-flood (`WM_ACTIVATE`, `WM_SETFOCUS`, etc.) when not running as Administrator |
| ⚡ **Instant Hook** | Uses `SetWinEventHook` (`EVENT_SYSTEM_FOREGROUND`) for zero-latency response when you switch tasks |
| ☕ **Sleep Prevention** | Calls `SetThreadExecutionState` to keep the display and system awake |
| 🔍 **Live Search** | Filter the window list in real time by title |
| 🔄 **Auto Refresh** | Configurable interval (5–100 s) keeps the window list up to date automatically |
| 🛡️ **Admin Awareness** | Detects and displays whether the app is running elevated — required for Enhanced Focus Lock |
| 🔁 **Single Instance** | Named Win32 mutex prevents duplicate instances; re-focuses the existing window instead |
| 📥 **System Tray** | Minimizes to system tray on close (X button); double-click or use tray menu to restore, unpin all, or exit cleanly |
| 🧹 **Clean Exit** | Automatically unpins all windows and resets sleep/execution state on close |

---

## 📋 Requirements

- **OS:** Windows 10 or 11 (64-bit recommended)
- **Python:** 3.8 or higher
- **Dependencies:** `customtkinter`, `pystray`, `Pillow` (auto-installed on first run if missing)

> ⚠️ **Admin rights are strongly recommended.** Enhanced Focus Lock (the `AttachThreadInput` path) only activates when running as Administrator. Without it, Focus Lock falls back to Basic (message-flood) mode, which may not work with hardened games.

---

## 🚀 Quick Start

### 1. Clone or Download

```
git clone https://github.com/crazykat8091/windowpinner.git
cd windowpinner
```

Or download the ZIP and extract it.

### 2. Install Dependencies

```
pip install customtkinter pystray Pillow
```

> The app will attempt to auto-install `customtkinter`, `pystray`, and `Pillow` if any are missing when you launch it.

### 3. Run

```
python window_pinner.py
```

Or double-click `window_pinner.py` in File Explorer (requires Python to be associated with `.py` files).

**To run as Administrator (recommended):** Right-click `window_pinner.py` → *Run as administrator*

---

## 🖥️ Interface Guide

```
┌──────────────────────────────────────────────────────────────┐
│ 📌 Window Pinner              ✕ minimizes to tray            │
│    V0.7 — ADMIN MODE                              2 pinned   │
├──────────────────────────────────────────────────────────────┤
│ 🔍 Search windows…         [↻ Refresh]  [✕ Unpin All]       │
├──────────────────────────────────────────────────────────────┤
│ ☑ Auto Refresh  ☑ Focus Lock  Interval: 15s  ☐ Sleep Prev.  │
├──────────────────────────────────────────────────────────────┤
│  ●  Window Title                    Handle    [Pin]          │
│  ●  Forza Horizon 6             0x000A1234    [☑ Pin]        │
│  ○  Chrome - Google             0x000B5678    [☐ Pin]        │
├──────────────────────────────────────────────────────────────┤
│ Status: Pinned: Forza  ● Auto-refresh on  ● Focus Lock (Enhanced) │
└──────────────────────────────────────────────────────────────┘
```

- **Green dot (●)** — window is currently pinned (always on top)
- **Dim dot (○)** — window is not pinned
- **Pin checkbox** — click to toggle pinned state
- **Header badge** — shows count of currently pinned windows
- **Focus Lock label** — shows `(Enhanced)` when `AttachThreadInput` is active, `(Basic)` otherwise

---

## ⚙️ Settings Explained

### Auto Refresh

Automatically re-scans open windows at the configured interval. Keeps the list current if you open or close apps while Window Pinner is running. Interval is configurable from 5 to 100 seconds.

### Focus Lock

Prevents games and applications from detecting that they've lost focus. Two modes:

**Enhanced Mode (Admin required):**
Temporarily attaches Window Pinner's input queue to the target process's thread using `AttachThreadInput` strictly on focus transition events, then calls `SetForegroundWindow`. This makes Windows commit a genuine focus token to the game at the OS level — the game's own `GetForegroundWindow()` calls return itself as the foreground window. This is the same technique used by SpecialK and is the most reliable user-mode approach available. Isolated from the heartbeat loop to prevent program-switching lockups and macro key conflicts.

**Basic Mode (no Admin):**
Sends a spoofed Windows activation message sequence (`WM_ACTIVATE`, `WM_SETFOCUS`, `WM_NCACTIVATE`, `WM_ACTIVATEAPP`, `WM_KILLFOCUS` + `WM_SETFOCUS` cycle, and more) to each pinned window at ~60 Hz. Effective for most non-hardened games and applications.

**When to enable:** Use when a pinned game or app pauses or minimizes after you click elsewhere.

**When to leave off:** If you only need the visual overlay (always on top) without focus behavior changes.

### Sleep Prevention

Calls `SetThreadExecutionState(ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED)` to prevent the display and system from sleeping. Resets automatically when disabled or when the app exits.

---

## 🔧 How It Works (Technical)

Window Pinner is a single-file Python application using:

- **`ctypes` / Win32 API** for all window management — no C extensions
- **`customtkinter`** for the modern dark UI
- **`pystray` & `Pillow`** for system tray integration and programmatic tray icon generation
- **`EnumWindows`** to list all visible titled windows, filtered to exclude the app's own process
- **`SetWindowPos(HWND_TOPMOST)`** to set/clear the always-on-top flag
- **`AttachThreadInput`** (V0.7) — temporarily merges our thread's input queue with the target's on focus changes, allowing `SetForegroundWindow` to commit a genuine foreground token even against games with hardened focus detection
- **`SetWinEventHook(EVENT_SYSTEM_FOREGROUND)`** for immediate event-driven response when the active window changes
- **`SendMessageTimeout`** with `SMTO_ABORTIFHUNG` and a tight 5 ms timeout for safe, non-blocking message delivery
- **`SetThreadExecutionState`** for sleep prevention
- **Named mutex (`Local\WindowPinner_SingleInstance_Mutex`)** for single-instance enforcement
- **`HIGH_PRIORITY_CLASS`** on the process when Focus Lock is active to ensure the 16 ms loop is never delayed by Windows scheduling

### Why DisplayFusion Still Works Without Updates

DisplayFusion uses a **kernel-mode driver** (`dfmirage.sys` / `dfdisplay.sys`) that hooks at the driver level — below the Win32 message layer entirely. It intercepts focus-loss events *before* they reach the game, rather than reacting to them after. No game update can patch a kernel driver from user space. Window Pinner operates in user mode only (no driver), so V0.7's `AttachThreadInput` approach is the closest equivalent available without a kernel component.

---

## ⚠️ Known Limitations

- **Windows only** — the app exits immediately on non-Windows platforms
- **Admin required for Enhanced Focus Lock** — `AttachThreadInput` requires the ability to open a handle to the target thread, which games with elevated privileges block in User Mode
- **Kernel-level anti-cheat** — systems like EasyAntiCheat and BattlEye operate below the Win32 layer and may detect or block any user-mode focus manipulation. Use with caution and at your own risk
- **Window handles can change** — if a pinned app restarts or crashes, its handle becomes invalid. The app will automatically prune stale handles on the next refresh

---

## ⚖️ Disclaimer

This utility interacts with the Windows focus and messaging system. While designed for productivity, using the Focus Lock feature with certain video games may technically violate their **Terms of Service (ToS)**. Use at your own discretion.

---

## 📄 License

MIT License — see [LICENSE.md](https://github.com/crazykat8091/windowpinner/blob/main/LICENSE.md) for full text.

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss the proposed change.

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📌 Changelog

For the full detailed release notes, see [CHANGELOG.md](https://github.com/crazykat8091/windowpinner/blob/main/CHANGELOG.md).

### v0.7 (Current)

- **FIX:** Added UWP / Xbox App Pinning support (e.g. Forza Horizon 6). Automatically resolves the top-level parent frame (`ApplicationFrameWindow`) to the child game window (`Windows.UI.Core.CoreWindow`) to apply topmost styles and send focus messages correctly.
- **FIX:** Isolated `AttachThreadInput` to run only on foreground change events (inside the focus change event callback hook) instead of the 16 ms heartbeat loop. This fixes program switching lockups (Alt-Tab) and avoids input queue congestion.
- **FIX:** Fixed macro key conflicts by preventing continuous input queue merging.

### v0.6

- **FIX:** `AttachThreadInput`-based focus injection restores compatibility with games that hardened their focus detection (e.g. Forza Horizon 6 post-update). Temporarily merges Window Pinner's input queue with the target thread before calling `SetForegroundWindow` — the same technique used by SpecialK
- **FIX:** `WM_ACTIVATE` lParam corrected from `fg_hwnd` to `0` — prevents games from detecting a foreign HWND in the activation message
- **FIX:** `WM_KILLFOCUS` → `WM_SETFOCUS` deny-and-reclaim cycle added; suppresses focus-loss at the message level for DX12/DXGI-based games
- **FIX:** `SendMessageTimeout` reduced from 25 ms to 5 ms — prevents the 16 ms heartbeat from stalling when a game thread is under high load
- **NEW:** Focus Lock status indicator now shows `(Enhanced)` when `AttachThreadInput` is active or `(Basic)` when falling back to message-only mode
- **NEW:** `AttachThreadInput` degrades gracefully in User Mode — no crash, automatically uses Basic path instead

### v0.5

- Minimize to system tray — clicking X hides the window to tray instead of quitting
- Tray icon shows pinned count dynamically as a tooltip
- Tray icon generated programmatically (no external `.ico` file required)
- Right-click tray context menu: Show Window, Unpin All, Exit
- Double-click tray icon to restore main window
- Auto-installs `pystray` and `Pillow` if missing
- "Exit" in tray menu performs full clean shutdown

### v0.4

- Fixed `SetWindowPos` return checks and window-positioning flags
- Added Focus Lock access checks to prevent errors on protected processes
- Optimized window list refreshing to use handle-set comparisons
- Added font fallback mechanisms
- Added null-HWND guard checks
- Added TclError guard on clean-exit
- Fixed `GetWindowLongPtr` restype definition
- Added "Run as Admin" button in the header
- Fixed anti-minimize logic

### v0.3

- Added Focus Lock with full activation message sequence
- Added Sleep Prevention via `SetThreadExecutionState`
- Added `SetWinEventHook` for instant focus-change response
- Single-instance enforcement via named mutex
- Process elevated to `HIGH_PRIORITY_CLASS` when Focus Lock is active
- Admin mode detection and UI indicator
- Anti-minimize: restores windows that try to iconify while pinned
- Live search, configurable auto-refresh interval, HWND badge per row
