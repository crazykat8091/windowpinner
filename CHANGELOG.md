# Changelog

All notable changes to **Window Pinner** will be documented in this file.

---

## [0.5.0] - 2026-06-18
### Added
- **Minimize to system tray**: Clicking the window's close button (✕) minimizes the application to the system tray instead of exiting, keeping always-on-top and Focus Lock active in the background.
- **Dynamic tray icon badge**: A programmatically drawn tray icon shows a green dot badge with the current number of pinned windows.
- **Tray tooltip**: Hovering over the tray icon displays status information (e.g., `Window Pinner • 2 pinned`).
- **Tray context menu**: Right-click menu options for *Show Window*, *Unpin All*, and *Exit*.
- **Tray restore action**: Double-clicking the tray icon restores the main GUI window.
- **Auto-dependency bootstrapping**: Added automatic pip installation of missing `pystray` and `Pillow` dependencies alongside `customtkinter`.
- **Programmatic icon generation**: System tray icon is created dynamically at runtime, removing the need for external `.ico` assets.

### Fixed
- Dedicated "Exit" option in the tray menu triggers a clean shutdown sequence, releasing all resources.

---

## [0.4.0]
### Added
- Dedicated **🔑 Run as Admin** elevation button directly in the main header for quick privilege elevation.

### Fixed
- Added return checks for `SetWindowPos` to ensure windows are correctly repositioned/layered.
- Added Access Checks on processes within the Focus Lock message loop to prevent errors on protected applications.
- Refactored list refresh mechanism to compare handle sets instead of rebuilding the widget array, reducing CPU usage.
- Added font fallback mechanisms to handle Windows configurations lacking "Segoe UI".
- Added safety null-HWND guard checks across Win32 API interactions.
- Added TclError try/catch guards on shutdown to avoid UI-thread crashes.
- Fixed `GetWindowLongPtr` ctypes restype definition to support 64-bit memory addresses correctly.
- Fixed anti-minimize logic to prevent pinned windows from staying minimized when backgrounded.

---

## [0.3.0]
### Added
- **Focus Lock**: Spoofs window activation messages (`WM_ACTIVATE`, `WM_SETFOCUS`, `WM_NCACTIVATE`, etc.) at ~60 Hz (16 ms) to prevent background games/apps from pausing.
- **Sleep Prevention**: Keeps the system and screen awake via `SetThreadExecutionState`.
- **Instant Hook**: Uses `SetWinEventHook` to handle active foreground changes instantly.
- **Single-instance Enforcement**: Uses a named Win32 mutex (`Local\WindowPinner_SingleInstance_Mutex`) to prevent duplicate processes.
- **High Process Priority**: Automatically raises process priority class to `HIGH_PRIORITY_CLASS` when Focus Lock is running to guarantee timing accuracy.
- **Admin Indicator**: Header color badges to show current privileges.
- **User Interface**: Integrated a customtkinter search, scrollable list, and manual refresh controls.
