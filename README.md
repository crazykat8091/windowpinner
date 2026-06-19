# 📌 Window Pinner

**Version 0.5** — A lightweight Windows utility to keep any window always on top and prevent background apps or games from pausing when they lose focus.

> **Author:** CrazyKat | **License:** MIT | [GitHub](https://github.com/crazykat8091/windowpinner)

---

## 🖼️ Overview

Window Pinner gives you fine-grained control over window layering and focus behavior on Windows 10/11. Whether you want a calculator floating above your game, a stream overlay staying visible, or a background app that thinks it's still active — Window Pinner handles it in a single lightweight Python script with a clean dark GUI.

It is a **free, open-source alternative** to paid tools like DisplayFusion or SpecialK for the specific use case of "always on top + focus spoofing."

---

## ✨ Features

| Feature | Description |
|---|---|
| 📍 **Always on Top** | Force any visible window to stay above all others using the Win32 `SetWindowPos` API |
| 🔒 **Focus Lock** | Spoofs a full Windows activation message sequence so games/apps believe they are still the focused window — prevents pause-on-minimize logic |
| ⚡ **Instant Hook** | Uses `SetWinEventHook` (`EVENT_SYSTEM_FOREGROUND`) for zero-latency response when you switch tasks |
| ☕ **Sleep Prevention** | Calls `SetThreadExecutionState` to keep the display and system awake |
| 🔍 **Live Search** | Filter the window list in real time by title |
| 🔄 **Auto Refresh** | Configurable interval (5–100 s) keeps the window list up to date automatically |
| 🛡️ **Admin Awareness** | Detects and displays whether the app is running elevated — required for some games |
| 🔁 **Single Instance** | Named Win32 mutex prevents duplicate instances; re-focuses the existing window instead |
| 📥 **System Tray** | Minimizes to system tray on close (X button); double-click or use tray menu to restore, unpin all, or exit cleanly |
| 🧹 **Clean Exit** | Automatically unpins all windows and resets sleep/execution state on close |

---

## 📋 Requirements

- **OS:** Windows 10 or 11 (64-bit recommended)
- **Python:** 3.8 or higher
- **Dependencies:** `customtkinter`, `pystray`, `Pillow` (auto-installed on first run if missing)

> ⚠️ **Admin rights are recommended** for pinning games and protected processes. Run as Administrator when the header shows *"User Mode (Limited)"*.

---

## 🚀 Quick Start

### 1. Clone or Download

```bash
git clone https://github.com/crazykat8091/windowpinner.git
cd windowpinner
```

Or download the ZIP and extract it.

### 2. Install Dependencies

```bash
pip install customtkinter pystray Pillow
```

> The app will attempt to auto-install `customtkinter`, `pystray`, and `Pillow` if any are missing when you launch it.

### 3. Run

```bash
python window_pinner.py
```

Or double-click `window_pinner.py` in File Explorer (requires Python to be associated with `.py` files).

**To run as Administrator:**
Right-click `window_pinner.py` → *Run as administrator*

---

## 🖥️ Interface Guide

```
┌──────────────────────────────────────────────────┐
│ 📌 Window Pinner            ✕ minimizes to tray  │
│    V0.5 — ADMIN MODE                    2 pinned │
├──────────────────────────────────────────────────┤
│ 🔍 Search windows…      [↻ Refresh] [✕ Unpin All] │
├──────────────────────────────────────────────────┤
│ ☑ Auto Refresh  ☑ Focus Lock  Interval: 15s  ☐ Sleep Prevention │
├──────────────────────────────────────────────────┤
│ ●  Status Dot │ Window Title         │ Handle │ [Pin] │
│ ●  Notepad                0x000A1234   [☑ Pin] │
│ ○  Chrome - Google        0x000B5678   [☐ Pin] │
├──────────────────────────────────────────────────┤
│ Status: Pinned: Notepad  ● Auto-refresh on  ● Focus Lock on │
└──────────────────────────────────────────────────┘
```

- **Green dot (●)** — window is currently pinned (always on top)
- **Dim dot (○)** — window is not pinned
- **Pin checkbox** — click to toggle pinned state
- **Header badge** — shows count of currently pinned windows; turns amber/red in User Mode
- **Tray Hint** — close button (✕) minimizes the app to the system tray instead of exiting

---

## ⚙️ Settings Explained

### Auto Refresh
Automatically re-scans open windows at the configured interval. Keeps the list current if you open/close apps while Window Pinner is running. Interval is configurable from 5 to 100 seconds.

### Focus Lock
Sends a spoofed Windows activation message sequence (`WM_ACTIVATE`, `WM_SETFOCUS`, `WM_NCACTIVATE`, `WM_ACTIVATEAPP`, and more) to each pinned window at ~60 Hz (every 16 ms). This prevents games and media players from detecting that they have lost focus and triggering their pause/minimize logic.

**When to enable:** Use when a pinned game or app pauses or minimizes after you click elsewhere.

**When to leave off:** If you only need the visual overlay (always on top) without focus behavior changes.

### Sleep Prevention
Calls `SetThreadExecutionState(ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED)` to prevent the display and system from sleeping. Resets automatically when disabled or when the app exits.

---

## 🔧 How It Works (Technical)

Window Pinner is a single-file Python application using:

- **`ctypes` / Win32 API** for all window management
- **`customtkinter`** for the modern dark UI
- **`pystray` & `Pillow`** for system tray integration and programmatic tray icon generation
- **`EnumWindows`** to list all visible titled windows, filtered to exclude the app's own process
- **`SetWindowPos(HWND_TOPMOST)`** to set/clear the always-on-top flag
- **`SetWinEventHook(EVENT_SYSTEM_FOREGROUND)`** for immediate event-driven response when the active window changes
- **`SendMessageTimeout`** with `SMTO_ABORTIFHUNG` for safe, non-blocking message delivery to pinned windows
- **`SetThreadExecutionState`** for sleep prevention
- **Named mutex (`Local\WindowPinner_SingleInstance_Mutex`)** for single-instance enforcement
- **`HIGH_PRIORITY_CLASS`** on the process when Focus Lock is active to ensure the 16 ms loop is never delayed

---

## ⚠️ Known Limitations

- **Windows only** — the app exits immediately on non-Windows platforms
- **Admin required for some targets** — games with anti-cheat or UAC-elevated processes may be inaccessible in User Mode
- **Focus Lock and anti-cheat** — some competitive game anti-cheat systems (e.g., Easy Anti-Cheat, BattlEye) can detect window message spoofing. Use with caution and at your own risk
- **Window handles can change** — if a pinned app restarts or crashes, its handle becomes invalid. The app will automatically prune stale handles on the next refresh

---

## ⚖️ Disclaimer

This utility interacts with the Windows focus and messaging system. While designed for productivity, using the Focus Lock feature with certain video games may technically violate their **Terms of Service (ToS)**. Use at your own discretion.

---

## 📄 License

MIT License — see [LICENSE.md](LICENSE.md) for full text.

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

For the full detailed release notes, please see [CHANGELOG.md](CHANGELOG.md).

### v0.5 (Current)
- **NEW:** Minimize to system tray — clicking the "X" button hides the window to the system tray instead of quitting
- **NEW:** Tray icon shows pinned count dynamically as a tooltip (e.g. "Window Pinner • 2 pinned")
- **NEW:** Tray icon is generated programmatically (no external `.ico` file required)
- **NEW:** Right-click context menu in tray: *Show Window*, *Unpin All*, and *Exit*
- **NEW:** Double-click the tray icon to restore the main window
- **NEW:** Automatic installation of `pystray` and `Pillow` dependencies if missing
- **NEW:** "Exit" option in the tray menu performs a full clean shutdown (unpins all windows, resets sleep state, unhooks win events)

### v0.4
- Fixed `SetWindowPos` return checks and window-positioning flags
- Added Focus Lock access checks to prevent errors on protected processes
- Optimized window list refreshing to use handle-set comparisons for better performance
- Added font fallback mechanisms to support systems lacking default fonts
- Added null-HWND guard checks to prevent Win32 API errors
- Added TclError guard checks on clean-exit to avoid UI exceptions on shutdown
- Fixed `GetWindowLongPtr` restype definition for compatibility
- Added a dedicated "Run as Admin" button in the header for easier elevation
- Fixed anti-minimize logic to prevent pinned windows from staying minimized

### v0.3
- Added Focus Lock with full activation message sequence
- Added Sleep Prevention via `SetThreadExecutionState`
- Added `SetWinEventHook` for instant focus-change response
- Single-instance enforcement via named mutex
- Process elevated to `HIGH_PRIORITY_CLASS` when Focus Lock is active
- Admin mode detection and UI indicator
- Anti-minimize: restores windows that try to iconify while pinned
- UI: live search, configurable auto-refresh interval, HWND badge per row
