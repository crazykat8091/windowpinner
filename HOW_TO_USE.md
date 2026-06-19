# 📖 How to Use Window Pinner

> This guide walks you through everything from first launch to advanced Focus Lock usage.

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
9. [Exiting Cleanly](#9-exiting-cleanly)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. First Launch

```bash
python window_pinner.py
```

**On first run**, if `customtkinter` is not installed, the app will automatically install it via `pip` and then start. You only need to wait for this once.

You will see the main window appear with a list of all currently open, visible windows on your system.

---

## 2. Understanding the Interface

### Header Bar
- **Window Pinner** title with version number
- **Admin Mode / User Mode (Limited)** indicator — green means elevated, red means not
- **Pinned count badge** — shows how many windows are currently pinned

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
| Focus Lock | ✅ ON | Spoofs focus messages to keep pinned apps "active" |
| Interval (s) | 15 | How often Auto Refresh runs (5–100 seconds) |
| Sleep Prevention | ☐ OFF | Prevents display and system from going to sleep |

### Window List
Each row shows:
- **Colored dot** — green (●) = pinned, dim (○) = not pinned
- **Window title** (truncated at 45 characters)
- **Handle** — the Win32 HWND value in hex (useful for debugging)
- **Pin checkbox** — click to toggle pinned state

> Pinned windows always float to the top of the list.

### Status Bar (bottom)
Displays the last action taken and shows live status indicators for Auto Refresh, Focus Lock, and Sleep Prevention.

---

## 3. Pinning a Window (Always on Top)

**To pin a window:**

1. Find the window in the list (use the Search box if needed)
2. Check the **Pin** checkbox on the right side of its row
3. The dot turns **green**, the row floats to the top of the list, and the status bar confirms the action

The target window is now set to always-on-top using the Windows API. It will stay above all other windows — including fullscreen apps — until you unpin it.

**To unpin:**
- Uncheck the **Pin** checkbox on the same row, or
- Click **✕ Unpin All** to release every pinned window at once

> **Note:** Pinned state is maintained only while Window Pinner is running. All windows are automatically unpinned when the app exits.

---

## 4. Using Focus Lock

Focus Lock is Window Pinner's most powerful feature. It sends a series of Windows activation messages to pinned windows at approximately 60 times per second, making games and applications believe they are still the active, focused window — even when you have clicked elsewhere.

### When to use Focus Lock

- You are gaming and want a calculator, browser, or overlay to stay on top
- A game pauses, minimizes, or drops to low FPS when you click another window
- A media player stops playback when you switch focus

### How to enable

Focus Lock is **on by default**. Check the **Focus Lock** checkbox in the Settings Bar to toggle it.

When enabled:
- The status bar shows **● Focus Lock on** in green
- The process priority is raised to **High** automatically to ensure the 16 ms message loop is never delayed by Windows scheduling

### What it does technically

For each pinned window, on every tick (~16 ms), the app sends:

```
WM_ENABLE → WM_MDIACTIVATE → WM_NCACTIVATE →
WM_ACTIVATEAPP → WM_ACTIVATE (Active) → WM_ACTIVATE (ClickActive) →
WM_SETFOCUS → WM_MOUSEACTIVATE → WM_SETCURSOR → WM_MOUSEMOVE →
WM_QUERYNEWPALETTE → WM_IME_SETCONTEXT → WM_IME_NOTIFY →
WM_INPUTLANGCHANGE → WM_WINDOWPOSCHANGING → WM_PAINT
```

Additionally, a `SetWinEventHook` callback fires instantly the moment you switch to another window, re-asserting topmost and sending an immediate restore + paint signal.

### Focus Lock and games

> ⚠️ **Important:** Focus Lock interacts with how games handle window messages. Some competitive multiplayer games use anti-cheat systems that can detect or block spoofed focus messages. Using Focus Lock with those games **may violate their Terms of Service**. Always check the rules for your specific game before using this feature.

---

## 5. Using Sleep Prevention

When enabled, Sleep Prevention tells Windows to keep both the **display** and **system** awake indefinitely — equivalent to moving the mouse continuously. This is useful for long renders, downloads, or monitoring tasks.

**To enable:** Check **Sleep Prevention** in the Settings Bar.

- Status bar shows **● Sleep Prev. on** in green
- Windows `SetThreadExecutionState` is called with `ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED`

**On exit or when unchecked**, the execution state is reset to the system default, restoring normal sleep behavior.

---

## 6. Search & Filter

Type in the **Search box** to filter the window list in real time. The filter is **case-insensitive** and matches anywhere in the title.

**Example:** Typing `chrome` will show only windows with "chrome" in their title.

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

Some windows — especially games, UAC-prompted apps, and processes running under a different user — cannot be modified without administrator privileges.

**Signs you need Admin Mode:**
- The header shows **User Mode (Limited)** in red
- Pinning a window appears to succeed but has no effect
- Focus Lock messages are silently ignored by the target

**How to run as Administrator:**

**Option A — Right-click:**
1. Right-click `window_pinner.py` in File Explorer
2. Select **Run as administrator**

**Option B — Terminal:**
1. Open Command Prompt or PowerShell as Administrator
2. Navigate to the folder
3. Run `python window_pinner.py`

When elevated, the header will show **ADMIN MODE** in green.

---

## 9. Exiting Cleanly

Close the window normally (click X or Alt+F4). Window Pinner will:

1. **Unpin all windows** — removes always-on-top from every pinned target
2. **Reset sleep state** — if Sleep Prevention was active, restores the system default
3. **Unhook the event hook** — releases the `WinEventHook` callback
4. **Exit cleanly** — no background processes remain

> Windows will not stay pinned after Window Pinner closes.

---

## 10. Troubleshooting

### Window Pinner won't start
- Ensure Python 3.8+ is installed and in your PATH
- Run `pip install customtkinter` manually if auto-install fails

### A window won't pin / pinning has no effect
- Run Window Pinner as Administrator (see Section 8)
- Some UWP/Store apps and certain system windows cannot be modified by any process

### Focus Lock doesn't stop the game from pausing
- Try running as Administrator — some games require elevated access for message delivery
- Certain games with kernel-level anti-cheat may block Win32 messages entirely — focus spoofing will not work in those cases

### The window list doesn't update when I open a new app
- Click **↻ Refresh** to force an immediate scan, or
- Lower the **Interval** value in the Settings Bar for more frequent auto-updates

### Window Pinner opens a second time instead of focusing the existing one
- This should not happen — the app uses a named mutex to prevent this
- If it occurs, check that no orphaned `python.exe` processes are running in Task Manager

### The app shows duplicate windows or ghost entries
- Click **↻ Refresh** — stale handles are pruned automatically on any refresh

---

*For bugs, feature requests, or contributions, visit the [GitHub repository](https://github.com/crazykat8091/windowpinner).*
