# 📋 Changelog — Window Pinner

All notable changes to this project are documented in this file.

---

## [0.8] — 2026-06-21

### Fixed

- **Infinite focus-trap loop removed** — V0.7 called `SetForegroundWindow(game)` inside `_on_focus_change`. This created a re-entrant loop: clicking any other window caused the hook to fire, which called `SetForegroundWindow(game)`, which caused Windows to make the game the foreground window, which fired the hook again, which called `SetForegroundWindow(game)` again — repeating infinitely. The result was that focus was permanently locked on the pinned game and it was impossible to switch to any other application.

- **`SetForegroundWindow` and `AttachThreadInput` removed from `_on_focus_change` entirely** — the hook callback is now responsible only for re-asserting `HWND_TOPMOST` (visual layering) when a non-pinned window takes the foreground. It no longer calls any focus-injection function.

- **Focus Lock correctly isolated to the 16 ms heartbeat** — the heartbeat (`_maintain_active_state`) already contains the correct guard: `if target == fg_hwnd: skip`. This means it only sends `WM_ACTIVATE` / `WM_SETFOCUS` messages when the game is NOT the real foreground window — which is exactly the right condition. No changes needed to the heartbeat itself.

---

## [0.7] — 2026-06-21

### Fixed

- Removed `AttachThreadInput` from the 16 ms heartbeat loop. Calling it 60x/sec merged Window Pinner's input queue with the game's on every tick, blocking macro keys and preventing program switching.
- Added UWP/Xbox game HWND resolution via `EnumChildWindows`. Forza Horizon 6 runs inside `ApplicationFrameHost` — the visible title-bar HWND is a shell frame, not the game. `_resolve_game_hwnd()` walks child windows to find the real `CoreWindow` HWND and pins that instead.
- Removed `SetForegroundWindow` from the heartbeat loop (it was stealing real keyboard focus from the user every 16 ms).

### Known issue (fixed in V0.8)

- `_inject_focus_once` (AttachThreadInput + SetForegroundWindow) was placed inside `_on_focus_change`, creating a re-entrant focus-trap loop. Fixed in V0.8.

---

## [0.6] — 2026-06-20

### Fixed

- `AttachThreadInput`-based focus injection introduced. Temporarily attaches our input queue to the target process's thread before calling `SetForegroundWindow`, mirroring the technique used by SpecialK. Restores compatibility with games (e.g. Forza Horizon 6) that hardened their focus detection.
- `WM_ACTIVATE` lParam corrected from `fg_hwnd` to `0` — prevents games from detecting a foreign HWND in the activation message.
- `WM_KILLFOCUS` → `WM_SETFOCUS` deny-and-reclaim cycle added to the heartbeat loop.
- `SendMessageTimeout` reduced from 25 ms to 5 ms.

### Known issue (fixed in V0.7)

- `AttachThreadInput` was called inside the 16 ms heartbeat loop (60x/sec), causing input queue merging that blocked macro keys and program switching.

---

## [0.5] — 2026-06-18

### New

- Minimize to system tray on close (X button)
- Tray icon with dynamic pinned-count badge and tooltip
- Programmatic tray icon (no external `.ico` required)
- Right-click tray menu: Show Window, Unpin All, Exit
- Auto-installs `pystray` and `Pillow` on first run
- Clean shutdown from tray: unpin all, reset sleep state, unhook win events

---

## [0.4]

### Fixed

- `SetWindowPos` return value checked; added `SWP_SHOWWINDOW` fallback on failure
- Focus Lock process-accessibility check before `SendMessageTimeout`
- Window list refresh optimized to diff by handle-set
- Font fallback for non-English systems
- Null-HWND guard before all Win32 calls in heartbeat
- `TclError` guard on clean exit
- `GetWindowLongPtr` restype fixed to `ctypes.c_long`
- Anti-minimize: pinned windows that become iconic are restored automatically

### New

- "Run as Admin" button in header with UAC elevation
- Process raised to `HIGH_PRIORITY_CLASS` when Focus Lock is active

---

## [0.3]

### New

- Focus Lock: full Win32 activation message sequence at ~60 Hz
- Sleep Prevention via `SetThreadExecutionState`
- `SetWinEventHook(EVENT_SYSTEM_FOREGROUND)` for instant topmost re-assertion
- Single-instance mutex (`Local\WindowPinner_SingleInstance_Mutex`)
- Admin mode detection and UI indicator
- Anti-minimize for pinned windows
- Live search, configurable auto-refresh interval, HWND per row

---

## [0.2]

- Configurable auto-refresh interval
- Pinned windows sorted to top of list
- Status bar with per-action feedback
- Window count badge in header

---

## [0.1]

- Initial release
- `EnumWindows`-based window list
- `SetWindowPos(HWND_TOPMOST)` pin/unpin toggle
- Dark UI with `customtkinter`
- Auto-install of `customtkinter` on first run
