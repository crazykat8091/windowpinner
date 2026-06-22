# 📌 Window Pinner

**Version 0.9** — A lightweight Windows utility to keep any window always on top and prevent background apps or games from pausing when they lose focus.

> **Author:** CrazyKat | **License:** MIT | [GitHub](https://github.com/crazykat8091/windowpinner) | [meshcon.tech](http://www.meshcon.tech)

---

## 🖼️ Overview

Window Pinner gives you fine-grained control over window layering and focus behavior on Windows 10/11. Whether you want a calculator floating above your game, a stream overlay staying visible, or a background game that thinks it's still active — Window Pinner handles it in a single lightweight Python script with a clean dark GUI.

It is a **free, open-source alternative** to paid tools like DisplayFusion or SpecialK for the specific use case of "always on top + focus spoofing."

**V0.9 is the first version with full macro key app compatibility.** All mouse messages, input-language messages, and IME messages have been removed from the focus-spoof sequence — the exact messages that caused conflicts with AutoHotkey, Logitech GHUB, Razer Synapse, and similar tools. Focus Lock now uses a clean 6-message activation-only sequence that does not touch the global input hook chain.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📍 **Always on Top** | Force any visible window to stay above all others using the Win32 `SetWindowPos` API |
| 🔒 **Focus Lock (Enhanced)** | Sends a clean Win32 activation sequence at 120 Hz to keep games active. Enhanced path uses full `SendMessageTimeout` for hardened processes. Requires Admin. |
| 🔒 **Focus Lock (Basic)** | Same activation sequence without process-access checks. Works without Admin for non-protected windows. |
| 🎮 **UWP / Xbox Game Support** | Resolves the real inner game HWND for titles running inside `ApplicationFrameHost` (e.g. Forza Horizon 6) via `EnumChildWindows` |
| 🎹 **Macro App Safe** | No mouse messages, no `WM_INPUTLANGCHANGE`, no IME messages in the heartbeat — zero conflict with AutoHotkey, Logitech GHUB, Razer Synapse, or any low-level input hook app |
| ⚡ **Instant Hook** | Uses `SetWinEventHook` (`EVENT_SYSTEM_FOREGROUND`) for zero-latency topmost re-assertion when any window changes foreground |
| ☕ **Sleep Prevention** | Calls `SetThreadExecutionState` to keep the display and system awake |
| 🔍 **Live Search** | Filter the window list in real time by title |
| 🔄 **Auto Refresh** | Configurable interval (5–100 s) keeps the window list up to date automatically |
| 🛡️ **Admin Awareness** | Detects and displays whether the app is running elevated; shows Enhanced vs Basic mode |
| 🔁 **Single Instance** | Named Win32 mutex prevents duplicate instances; re-focuses the existing window instead |
| 📥 **System Tray** | Minimizes to system tray on close (X button); double-click or use tray menu to restore, unpin all, or exit cleanly |
| 🧹 **Clean Exit** | Automatically unpins all windows and resets sleep/execution state on close |

---

## 📋 Requirements

- **OS:** Windows 10 or 11 (64-bit recommended)
- **Python:** 3.8 or higher
- **Dependencies:** `customtkinter`, `pystray`, `Pillow` (auto-installed on first run if missing)

> ⚠️ **Admin rights are strongly recommended.** Enhanced Focus Lock only activates when running as Administrator. Without it, Focus Lock falls back to Basic mode, which may not work with hardened games like Forza Horizon 6.

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

> Dependencies are auto-installed on first launch if missing.

### 3. Run

```
python window_pinner.py
```

Or double-click `window_pinner.py` in File Explorer (requires Python associated with `.py` files).

**Recommended:** Right-click → *Run as administrator* for full Focus Lock.

---

## 🖥️ Interface Guide

```
┌──────────────────────────────────────────────────────────────┐
│ 📌 Window Pinner              ✕ minimizes to tray            │
│    V0.9 — ADMIN MODE                              2 pinned   │
├──────────────────────────────────────────────────────────────┤
│ 🔍 Search windows…         [↻ Refresh]  [✕ Unpin All]       │
├──────────────────────────────────────────────────────────────┤
│ ☑ Auto Refresh  ☑ Focus Lock  Interval: 15s  ☐ Sleep Prev.  │
├──────────────────────────────────────────────────────────────┤
│  ●  Window Title                    Handle    [Pin]          │
│  ●  Forza Horizon 6             0x000A1234    [☑ Pin]        │
│  ○  Chrome - Google             0x000B5678    [☐ Pin]        │
├──────────────────────────────────────────────────────────────┤
│ Pinned: Forza  ● Auto-refresh on  ● Focus Lock (Enhanced)    │
└──────────────────────────────────────────────────────────────┘
```

- **Green dot (●)** — window is pinned (always on top + Focus Lock active)
- **Dim dot (○)** — window is not pinned
- **Amber dot (●)** — window is inaccessible without Admin (🔒 prefix on title)
- **Pin checkbox** — click to toggle pinned state
- **Header badge** — live count of pinned windows
- **Focus Lock label** — shows `(Enhanced)` when Admin + accessible, `(Basic)` otherwise

---

## ⚙️ Settings Explained

### Auto Refresh

Automatically re-scans open windows at the configured interval. Keeps the list current as you open or close apps. Configurable from 5 to 100 seconds. Stale handles (closed windows) are pruned automatically on each refresh.

### Focus Lock

Prevents games and applications from detecting that they've lost focus — stopping the pause, FPS drop, or audio mute that happens when you Alt+Tab.

Window Pinner runs a **120 Hz heartbeat** that sends a clean Win32 activation sequence to each pinned window whenever it is not the real foreground:

```
WM_KILLFOCUS → WM_SETFOCUS         (deny-and-reclaim cycle)
WM_NCACTIVATE(1)                   (non-client area draws as active)
WM_ACTIVATEAPP(1)                  (process is active)
WM_ACTIVATE(WA_ACTIVE, lParam=0)   (standard focus grant, no foreign HWND leak)
WM_SETFOCUS                        (keyboard focus grant)
WM_SYSCOMMAND(SC_RESTORE)          (resumes audio/physics in UE4/UE5 and Unity)
```

**Enhanced Mode (Admin):** Uses `SendMessageTimeout` with `SMTO_ABORTIFHUNG` for reliable delivery to hardened game processes. Status bar shows `(Enhanced)`.

**Basic Mode (no Admin):** Same sequence, skips the process-access check. Works for most non-hardened apps. Status bar shows `(Basic)`.

**Macro app safety:** The sequence contains **no mouse messages, no `WM_INPUTLANGCHANGE`, no IME messages.** These were removed in V0.9 because low-level input hooks in macro apps (AutoHotkey, Logitech GHUB, Razer Synapse) intercept them globally, causing unintended macro triggers and profile switches.

**When to enable:** Game pauses, mutes audio, or drops FPS when you click another window.

**When to leave off:** You only need the visual overlay (always on top) without any focus behavior changes.

### Sleep Prevention

Calls `SetThreadExecutionState(ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED)` to prevent display and system sleep. Resets automatically when disabled or when the app exits.

---

## 🔧 How It Works (Technical)

Window Pinner is a single-file Python application using only the standard library + three pip packages:

- **`ctypes` / Win32 API** — all window management, no C extensions
- **`customtkinter`** — modern dark UI
- **`pystray` & `Pillow`** — system tray integration with a programmatically generated icon
- **`EnumWindows`** — lists all visible titled windows, filtered to exclude Window Pinner's own process
- **`EnumChildWindows`** — resolves the real inner game HWND for UWP/Xbox titles running inside `ApplicationFrameHost`
- **`SetWindowPos(HWND_TOPMOST)`** — sets/clears always-on-top flag on both the frame and the inner game HWND
- **`SetWinEventHook(EVENT_SYSTEM_FOREGROUND)`** — event-driven callback that re-asserts topmost instantly when any window changes foreground. Does **not** call `SetForegroundWindow` (which caused an infinite re-entrant loop in earlier versions)
- **`SendMessageTimeout`** with `SMTO_ABORTIFHUNG` and 5 ms timeout — safe, non-blocking delivery of activation messages to game threads under load
- **`SetThreadExecutionState`** — sleep prevention
- **Named mutex (`Local\WindowPinner_SingleInstance_Mutex`)** — single-instance enforcement
- **`HIGH_PRIORITY_CLASS`** — process priority raised when Focus Lock is active so the 8 ms loop is never starved by Windows scheduling

### Why DisplayFusion Still Works Without Updates

DisplayFusion ships a **kernel-mode driver** (`dfmirage.sys` / `dfdisplay.sys`) that hooks at the driver level — below the Win32 message layer. It intercepts focus-loss events *before* they reach the game. No game update can patch that from user space. Window Pinner is pure user mode (no driver), so it reacts to focus changes rather than intercepting them. That gap is why DisplayFusion achieves closer to 100% effectiveness on hardened games.

---

## ⚠️ Known Limitations

- **Windows only** — exits immediately on non-Windows platforms
- **Admin recommended** — Enhanced Focus Lock requires process handle access; games running elevated block this in User Mode
- **Kernel-level anti-cheat** — EasyAntiCheat, BattlEye, and Riot Vanguard operate below Win32 and may detect or block user-mode focus manipulation. Use at your own discretion and check your game's ToS
- **`GetForegroundWindow()` polling** — some game engine systems poll this API directly. No user-mode tool can fake its return value; only a kernel driver can intercept it. This is the source of the remaining ~5–10% gap versus DisplayFusion
- **Stale handles** — if a pinned app restarts or crashes, its HWND becomes invalid. Window Pinner prunes these automatically on the next refresh

---

## ⚖️ Disclaimer

This utility interacts with the Windows focus and messaging system. While designed for productivity, using the Focus Lock feature with certain video games may technically violate their **Terms of Service (ToS)**. Use at your own discretion.

---

## 📄 License

MIT License — see [LICENSE.md](https://github.com/crazykat8091/windowpinner/blob/main/LICENSE.md) for full text.

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first.

1. Fork the repository
2. Create your branch: `git checkout -b feature/my-feature`
3. Commit: `git commit -m 'Add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📌 Changelog

Full release notes: [CHANGELOG.md](https://github.com/crazykat8091/windowpinner/blob/main/CHANGELOG.md)

### v0.9 (Current)

- **FIX:** All mouse messages removed from heartbeat (`WM_MOUSEACTIVATE`, `WM_SETCURSOR`, `WM_MOUSEMOVE`, `WM_LBUTTONDOWN`) — these were triggering macros in AutoHotkey, GHUB, and Synapse via global low-level input hooks
- **FIX:** `WM_INPUTLANGCHANGE` removed — was randomly flipping macro app hotkey profiles mid-game
- **FIX:** `WM_IME_SETCONTEXT` / `WM_IME_NOTIFY` removed — was causing spurious input-mode switches in IME-aware macro tools
- **FIX:** `WM_ENABLE`, `WM_MDIACTIVATE`, `WM_WINDOWPOSCHANGING`, `WM_QUERYNEWPALETTE` removed — no effect on modern games, pure noise
- **NEW:** `WM_SYSCOMMAND SC_RESTORE` added — UE4/UE5 and Unity IL2CPP games resume audio/physics on this, not on `WM_ACTIVATE` alone
- **NEW:** Heartbeat increased from 60 Hz to 120 Hz (`after(16)` → `after(8)`)

### v0.8

- **FIX:** Removed `SetForegroundWindow` + `AttachThreadInput` from `_on_focus_change`. V0.7 called these inside the WinEvent hook, creating an infinite re-entrant loop that permanently trapped focus on the pinned game
- **FIX:** `_on_focus_change` now only re-asserts `HWND_TOPMOST` (visual layering) — no focus injection in the hook
- **FIX:** UWP/Xbox HWND resolution via `EnumChildWindows` — correctly pins Forza Horizon 6 inside `ApplicationFrameHost`

### v0.7

- **FIX:** `AttachThreadInput` moved out of the 16 ms heartbeat loop — calling it 60×/sec was blocking macro keys
- **FIX:** `SetForegroundWindow` removed from heartbeat — was stealing real focus every 16 ms
- **NEW:** UWP/Xbox inner HWND discovery via `EnumChildWindows`

### v0.6

- **FIX:** `WM_ACTIVATE` lParam corrected from `fg_hwnd` to `0`
- **FIX:** `WM_KILLFOCUS` → `WM_SETFOCUS` deny-and-reclaim cycle added
- **FIX:** `SendMessageTimeout` reduced from 25 ms to 5 ms

### v0.5

- Minimize to system tray (X button hides, double-click tray to restore)
- Programmatic tray icon with live pinned-count badge
- Right-click tray menu: Show Window, Unpin All, Exit

### v0.4

- `SetWindowPos` return value checked with `SWP_SHOWWINDOW` fallback
- `GetWindowLongPtr` restype fixed to `ctypes.c_long`
- Anti-minimize for pinned windows
- "Run as Admin" button with UAC elevation

### v0.3

- Focus Lock with Win32 activation message sequence
- Sleep Prevention via `SetThreadExecutionState`
- `SetWinEventHook` for instant focus-change response
- Single-instance mutex, admin mode indicator, live search
