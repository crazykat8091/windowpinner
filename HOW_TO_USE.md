# 📖 How to Use Window Pinner

> This guide covers everything from first launch to advanced Focus Lock usage, including the UWP support and isolated Enhanced mode introduced in V0.7.

---

## Table of Contents

1. [First Launch](#1-first-launch)
2. [Understanding the Interface](#2-understanding-the-interface)
3. [Pinning a Window (Always on Top)](#3-pinning-a-window-always-on-top)
4. [Using Focus Lock](#4-using-focus-lock)
5. [Using Sleep Prevention](#5-using-sleep-prevention)
6. [Search & Filter](#6-search--filter)
7. [Auto Refresh](#7-auto-refresh)
8. [Running as Administrator](#8-running-as-administrator)
9. [Minimize to System Tray](#9-minimize-to-system-tray)
10. [Exiting Cleanly](#10-exiting-cleanly)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. First Launch

```
python window_pinner.py
```

**On first run**, if `customtkinter`, `pystray`, or `Pillow` are not installed, the app will automatically install them via `pip` and then start. You only need to wait for this once.

You will see the main window appear with a list of all currently open, visible windows on your system.

> **Recommended:** Right-click `window_pinner.py` and choose **Run as administrator** to enable Enhanced Focus Lock mode.

---

## 2. Understanding the Interface

### Header Bar

- **Window Pinner** title with version number (V0.7)
- **Admin Mode / User Mode (Limited)** indicator — green means elevated, red means not
- **Pinned count badge** — shows how many windows are currently pinned
- **Tray hint** — shows "✕ minimizes to tray" as a reminder

### Toolbar

| Control | Function |
|---|---|
| 🔍 Search box | Filter the window list live by title text |
| ↻ Refresh | Immediately re-scan all open windows |
| ✕ Unpin All | Remove always-on-top from every pinned window at once |

### Settings Bar

| Setting | Default | Function |
|---|---|---|
| Auto Refresh | ✅ ON | Periodically re-scans window list |
| Focus Lock | ✅ ON | Keeps pinned apps "active" — Enhanced or Basic depending on Admin status |
| Interval (s) | 15 | How often Auto Refresh runs (5–100 seconds) |
| Sleep Prevention | ☐ OFF | Prevents display and system from going to sleep |

### Window List

Each row shows:

- **Colored dot** — green (●) = pinned, dim (○) = not pinned, amber = inaccessible
- **Window title** (truncated at 45 characters; 🔒 prefix means process is inaccessible without Admin)
- **Handle** — the Win32 HWND value in hex (useful for debugging)
- **Pin checkbox** — click to toggle pinned state

> Pinned windows always float to the top of the list.

### Status Bar (bottom)

Displays the last action taken and live indicators for Auto Refresh, Focus Lock, and Sleep Prevention. The Focus Lock indicator shows **(Enhanced)** when `AttachThreadInput` is active or **(Basic)** when in message-only mode.

---

## 3. Pinning a Window (Always on Top)

**To pin a window:**

1. Find the window in the list (use the Search box if needed)
2. Check the **Pin** checkbox on the right side of its row
3. The dot turns **green**, the row floats to the top of the list, and the status bar confirms

The target window is now set to always-on-top. It will stay above all other windows — including fullscreen apps — until you unpin it.

**To unpin:**

- Uncheck the **Pin** checkbox on the same row, or
- Click **✕ Unpin All** to release every pinned window at once

> **Note:** Pinned state is maintained only while Window Pinner is running. All windows are automatically unpinned when the app exits.

---

## 4. Using Focus Lock

Focus Lock is Window Pinner's most powerful feature. It prevents games and applications from detecting that they've lost focus — stopping pause-on-minimize and FPS-drop behavior when you Alt+Tab.

V0.7 supports two modes:

### Enhanced Mode (Admin required — recommended for games)

Uses `AttachThreadInput` to temporarily bind Window Pinner's input queue to the target window's thread, then calls `SetForegroundWindow`. This makes Windows issue a genuine foreground token to the game process at the OS level. The game's own internal calls to `GetForegroundWindow()` return itself as the foreground window — it cannot tell it has been unfocused.

This is the same user-mode technique used by SpecialK and is significantly more reliable than message flooding for modern DirectX 12 and DXGI-based games.

**The status bar shows: `● Focus Lock on (Enhanced)`**

### Basic Mode (no Admin)

Sends a spoofed Windows activation message sequence to each pinned window at approximately 60 times per second:

```
WM_KILLFOCUS → WM_SETFOCUS (deny-and-reclaim cycle)
WM_ENABLE → WM_MDIACTIVATE → WM_NCACTIVATE →
WM_ACTIVATEAPP → WM_ACTIVATE (Active, lParam=0) →
WM_ACTIVATE (ClickActive, lParam=0) → WM_SETFOCUS →
WM_MOUSEACTIVATE → WM_SETCURSOR → WM_MOUSEMOVE →
WM_QUERYNEWPALETTE → WM_IME_SETCONTEXT → WM_IME_NOTIFY →
WM_INPUTLANGCHANGE → WM_WINDOWPOSCHANGING → WM_PAINT
```

Effective for most non-hardened applications and older games.

**The status bar shows: `● Focus Lock on (Basic)`**

### When to use Focus Lock

- A game pauses, minimizes, or drops to low FPS when you click another window
- You want a browser or overlay on top while gaming without interrupting the game
- A media player stops playback when you switch focus

### How to enable

Focus Lock is **on by default**. The **Focus Lock** checkbox in the Settings Bar toggles it. Mode (Enhanced or Basic) is determined automatically based on whether the app is running as Administrator.

> ⚠️ **Important:** Focus Lock interacts with how games handle window messages. Some competitive multiplayer games use anti-cheat systems that can detect focus manipulation. Using Focus Lock with those games **may violate their Terms of Service**. Always check the rules for your specific game.

---

## 5. Using Sleep Prevention

When enabled, Sleep Prevention tells Windows to keep both the **display** and **system** awake indefinitely — equivalent to moving the mouse continuously.

**To enable:** Check **Sleep Prevention** in the Settings Bar.

- Status bar shows **● Sleep Prev. on** in green
- Windows `SetThreadExecutionState` is called with `ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED`

**On exit or when unchecked**, the execution state resets to the system default, restoring normal sleep behavior.

---

## 6. Search & Filter

Type in the **Search box** to filter the window list in real time. The filter is **case-insensitive** and matches anywhere in the title.

**Example:** Typing `forza` will show only windows with "forza" in their title.

Pinned windows remain at the top of filtered results. If no windows match, the list shows *"No windows match your search."*

---

## 7. Auto Refresh

Auto Refresh periodically re-scans all open windows so the list stays current.

- **Default interval:** 15 seconds
- **Range:** 5–100 seconds (values outside this range are clamped automatically)
- Stale handles (windows that have been closed) are automatically removed from the pinned set on refresh

**To change the interval:** Edit the number in the **Interval (s)** field in the Settings Bar.

**To disable:** Uncheck **Auto Refresh**. You can still refresh manually with the **↻ Refresh** button.

---

## 8. Running as Administrator

Running as Administrator is required for **Enhanced Focus Lock** mode. Without it, Focus Lock falls back to Basic (message-flood) mode, which may not work with hardened modern games.

**Signs you need Admin Mode:**

- The header shows **User Mode (Limited)** in red
- The status bar shows `● Focus Lock on (Basic)` instead of `(Enhanced)`
- A game continues to pause or drop FPS when you Alt+Tab

**How to run as Administrator:**

**Option A — In-app button:**

Click the **🔑 Run as Admin** button in the header bar. The app will prompt for UAC confirmation and restart elevated automatically.

**Option B — Right-click:**

1. Right-click `window_pinner.py` in File Explorer
2. Select **Run as administrator**

**Option C — Terminal:**

1. Open Command Prompt or PowerShell as Administrator
2. Navigate to the folder
3. Run `python window_pinner.py`

When elevated, the header shows **ADMIN MODE** in green and Focus Lock shows **(Enhanced)**.

---

## 9. Minimize to System Tray

Clicking the close (**✕**) button on the main window **minimizes the application to the system tray** instead of quitting. Your pinned windows and Focus Lock remain active in the background.

- **System Tray Icon:** A custom pushpin icon appears in the Windows notification area
  - A **green dot badge** with pinned count appears when windows are pinned
  - Hovering shows a tooltip: `Window Pinner • 2 pinned`
- **Restoring the Window:** Double-click the tray icon, or right-click → **Show Window**
- **Tray Context Menu:**
  - **Show Window** — restore the GUI
  - **Unpin All** — immediately release all pinned windows
  - **Exit** — full clean shutdown

---

## 10. Exiting Cleanly

To fully close Window Pinner:

1. Right-click the system tray icon
2. Select **Exit**

Upon exit, Window Pinner will:

1. **Unpin all windows** — removes always-on-top from every pinned target
2. **Reset sleep state** — if Sleep Prevention was active, restores the system default
3. **Unhook the event hook** — releases the `SetWinEventHook` callback
4. **Stop the background tray service** and destroy the tray icon
5. **Exit cleanly** — no background processes or threads remain

> **Note:** Windows will not stay pinned after Window Pinner closes.

---

## 11. Troubleshooting

### Window Pinner won't start

- Ensure Python 3.8+ is installed and in your PATH
- Run `pip install customtkinter pystray Pillow` manually if auto-install fails

### A window won't pin / pinning has no effect

- Run Window Pinner as Administrator (see Section 8)
- Some UWP/Store apps and certain system windows cannot be modified by any process

### Focus Lock doesn't stop the game from pausing (Enhanced Mode)

This is the V0.6/V0.7 fix scenario. If Enhanced Mode is shown but the game still pauses:

1. Confirm you are running as Administrator (header shows **ADMIN MODE**)
2. The game's process must be visible in the window list and pinned
3. If the game uses a kernel-level anti-cheat (EasyAntiCheat, BattlEye, Riot Vanguard), it may block all user-mode focus manipulation — there is no user-space workaround for those

### Focus Lock doesn't stop the game from pausing (Basic Mode)

- Run as Administrator to enable Enhanced Mode, which is significantly more effective
- Some games with DX12/DXGI focus polling respond only to Enhanced Mode

### The window list doesn't update when I open a new app

- Click **↻ Refresh** to force an immediate scan, or
- Lower the **Interval** value in the Settings Bar

### Window Pinner opens a second instance instead of focusing the existing one

- Should not happen — the app uses a named mutex to prevent this
- If it occurs, check Task Manager for orphaned `python.exe` processes

### The app shows duplicate windows or ghost entries

- Click **↻ Refresh** — stale handles are pruned automatically on any refresh

### The status bar says "Basic" even though I'm running as Admin

- Check that the pinned game's process is accessible: a 🔒 icon on its row means it's protected
- Try clicking **↻ Refresh** after launching the game and before pinning it

---

*For bugs, feature requests, or contributions, visit the [GitHub repository](https://github.com/crazykat8091/windowpinner).*
