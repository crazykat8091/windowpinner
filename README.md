# Window Pinner V0.3

A lightweight, modern Windows utility designed to keep any window **Always on Top** and prevent background applications or games from pausing when they lose focus.

## ✨ Key Features

- **📍 Always-on-Top:** Force any window to stay above others.
- **🔒 Focus Lock:** Spoofs Windows messages to trick games and apps into thinking they are still the active window. Ideal for multi-tasking while gaming or streaming.
- **☕ Sleep Prevention:** Toggle system and display sleep on/off to keep your PC awake during long tasks.
- **⚡ Instant Response:** Uses Windows Event Hooks to immediately re-assert priority when you switch tasks.
- **🖥️ Compact UI:** A clean, dark-themed interface built with `CustomTkinter`.
- **🛡️ Admin Awareness:** Indicates if running with administrative privileges (often required for pinning games).

---

## 🚀 Quick Start

### Requirements
- **OS:** Windows 10 or 11 (64-bit recommended)
- **Python:** 3.8 or higher

### Installation
1. Download or clone this repository.
2. Install the required GUI library:
   ```bash
   pip install customtkinter
   ```
   *(Note: The app will attempt to auto-install this if missing when run).*

### Running the App
Double-click `window_pinner.py` or run via terminal:
```bash
python window_pinner.py
```

---

## ⚖️ Disclaimer
This utility interacts with Windows focus and messaging systems. While designed for productivity, using this tool with certain video games may technically violate their Terms of Service (ToS) due to the focus spoofing nature. Use at your own discretion.

**License:** MIT