# 📋 Changelog — Window Pinner

All notable changes to this project are documented in this file.

---

## [0.7] — 2026-06-20

### Fixed

- **UWP / Xbox App Pinning (Forza Horizon 6)** — Sandboxed UWP applications running under `ApplicationFrameHost.exe` are now fully supported. Window Pinner resolves the top-level parent frame to its child game rendering window (`Windows.UI.Core.CoreWindow`) and targets the child directly for all topmost assertions (`SetWindowPos`) and focus messaging operations.

- **Input Queue & Program Switching Lockups** — Removed `AttachThreadInput` from the high-frequency 16ms heartbeat loop. Focus lock messages are sent via message flood only. `AttachThreadInput` focus injection is isolated to run exactly once inside the `EVENT_SYSTEM_FOREGROUND` event callback hook when focus changes. This eliminates program switching lockups (Alt-Tab) and avoids merging the input queue during the heartbeat loop.

- **Macro Key Conflicts** — By isolating `AttachThreadInput` from the heartbeat loop, input queues are no longer continuously merged, fixing mapping conflicts where macro key presses were incorrectly routed to the game process.

---

## [0.6] — 2026-06-20

### Fixed

- **`AttachThreadInput` focus injection** — the primary fix for games that hardened their focus detection (including Forza Horizon 6 post-update). Window Pinner now temporarily attaches its input queue to the target process's thread using `AttachThreadInput`, then calls `SetForegroundWindow`. This causes Windows to commit a genuine foreground token to the game at the OS level. The game's own `GetForegroundWindow()` calls return itself — it cannot detect it has been unfocused. This mirrors the technique used internally by SpecialK and is the most reliable user-mode focus spoof available without a kernel driver.

- **`WM_ACTIVATE` lParam corrected** — previously passed `fg_hwnd` (the real foreground window handle) as the lParam of `WM_ACTIVATE`. Games can read this value and detect that the activating HWND is a foreign process, identifying it as spoofed. Now passes `0`, which matches the value Windows sends during a natural focus transition.

- **`WM_KILLFOCUS` → `WM_SETFOCUS` deny-and-reclaim cycle** — added to the heartbeat loop for both Enhanced and Basic modes. DirectX 12 and DXGI-based games often track focus state by watching for `WM_KILLFOCUS` rather than polling `WM_ACTIVATE`. Sending `WM_KILLFOCUS` immediately followed by `WM_SETFOCUS` suppresses focus-loss detection at the message level.

- **`SendMessageTimeout` timeout reduced from 25 ms to 5 ms** — the 16 ms heartbeat loop was at risk of stalling when `SendMessageTimeout` blocked for up to 25 ms on a busy or hung game thread. The tighter 5 ms timeout ensures the loop completes within its 16 ms budget even under load.

### New

- **Enhanced vs Basic Focus Lock indicator** — the status bar Focus Lock label now shows `(Enhanced)` when `AttachThreadInput` is active (Admin + accessible process) or `(Basic)` when falling back to the message-flood path. This makes it immediately clear which mode is in effect without opening any menus.

- **Graceful degradation in User Mode** — `AttachThreadInput` requires the ability to open a handle to the target thread. When running without Admin rights or when the target process is protected, the new Enhanced path is skipped cleanly and the Basic message-flood path is used instead. No crash, no error dialog.

- **Immediate `AttachThreadInput` injection on foreground change** — the `SetWinEventHook` callback (`_on_focus_change`) now also calls `_inject_focus_via_attach` immediately when the foreground changes away from a pinned window, in addition to the existing 16 ms heartbeat. This closes the window of time between the focus-loss event and the next heartbeat tick.

---

## [0.5] — 2026-06-18

### New

- Minimize to system tray — clicking the X button hides the window to the system tray instead of quitting
- Tray icon shows pinned count dynamically as a badge and tooltip (e.g. "Window Pinner • 2 pinned")
- Tray icon generated programmatically using Pillow — no external `.ico` file required
- Right-click tray context menu: Show Window, Unpin All, Exit
- Double-click tray icon to restore the main window
- Auto-installs `pystray` and `Pillow` dependencies if missing (same pattern as `customtkinter`)
- "Exit" in the tray menu performs a full clean shutdown: unpin all, reset sleep state, unhook win events, stop tray thread

### Carries all V0.4 fixes

---

## [0.4]

### Fixed

- `SetWindowPos` return value checked; added `SWP_SHOWWINDOW` fallback flag on failure
- Focus Lock now checks process accessibility before attempting `SendMessageTimeout` to protected processes
- Window list refresh optimized to diff by handle-set rather than rebuilding the full list on every tick
- Font fallback added for systems where Segoe UI is unavailable
- Added null-HWND guard before all Win32 API calls in the heartbeat loop
- Added `TclError` guard on clean exit to suppress Tk exception when the window is destroyed mid-redraw
- Fixed `GetWindowLongPtr` restype — was `ctypes.c_int`, now correctly `ctypes.c_long`
- Anti-minimize fix: pinned windows that become iconic (minimized) are now restored automatically

### New

- "Run as Admin" button in the header bar — triggers UAC elevation and restarts the app
- Process priority raised to `HIGH_PRIORITY_CLASS` when Focus Lock is enabled

---

## [0.3]

### New

- Focus Lock: full Win32 activation message sequence sent at ~60 Hz to pinned windows
- Sleep Prevention via `SetThreadExecutionState`
- `SetWinEventHook(EVENT_SYSTEM_FOREGROUND)` for immediate event-driven topmost re-assertion
- Single-instance enforcement via named mutex (`Local\WindowPinner_SingleInstance_Mutex`)
- Process elevated to `HIGH_PRIORITY_CLASS` when Focus Lock is active
- Admin mode detection with visual indicator in the header
- Anti-minimize: restores windows that attempt to iconify while pinned
- Live search: filter window list in real time by title
- Configurable auto-refresh interval (5–100 seconds)
- HWND displayed per row in monospace hex format

---

## [0.2]

- Added configurable auto-refresh interval
- Pinned windows sorted to the top of the list
- Status bar with per-action feedback messages
- Window count shown in the header badge

---

## [0.1]

- Initial release
- `EnumWindows`-based window list
- `SetWindowPos(HWND_TOPMOST)` pin/unpin toggle
- Basic dark UI with `customtkinter`
- Auto-install of `customtkinter` dependency on first run
