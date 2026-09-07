<div align="center">

# Localhost Radar

**A lightweight Windows desktop tool for seeing what is listening on your local machine.**

`v0.3.0` · `BUILD 2026-08-30-B`

[Türkçe README](README_TR.md)

</div>

Localhost Radar scans listening TCP ports, maps them to the owning process, and presents the result in a compact desktop interface. It is designed for local development and troubleshooting: finding forgotten dev servers, checking which process owns a port, opening detected web services, and safely ending ordinary processes when needed.

## Highlights

- Real **Scan now** and **Full refresh** actions with visible scan state and scan counter
- Process mapping: PID, process name, executable path, command line, user and start time
- Conservative web-service detection before enabling **Open in browser**
- IPv4 / IPv6 duplicate listener collapsing
- Favorites and filtering
- Possible leftover development-server warning
- Protected Windows processes cannot be ended from the app
- Settings are persisted under the user's application-data directory
- Silent `.pyw` launcher: no console window, no service, no tray agent and no second long-running backend process
- Background scanning runs in a `QThread` inside the same GUI process

## Requirements

- Windows 10 / 11
- Python 3.10+ recommended
- PySide6
- psutil

## Quick start

1. Download or clone the repository.
2. Run `KUR.bat` once to install Python dependencies.
3. Double-click `RUN_THIS_Localhost_Radar_v0.3.pyw` for normal use.

For debug output, run `BASLAT_DEBUG.bat`.

The application title and header should show:

```text
v0.3.0 • BUILD 2026-08-30-B
```

If that text is not visible, an older copy is probably being launched.

## What the buttons do

### Scan now

Performs a fresh `psutil.net_connections()` scan. Process metadata may come from the short-lived process cache.

### Full refresh

Clears the process cache first, then rescans all listening TCP endpoints.

### Settings

Applies and persists options such as auto refresh, refresh interval, duplicate-binding collapse, system-process visibility and confirmation before process termination.

## Core smoke test

Run:

```bash
python core_test.py
```

The test creates a temporary localhost TCP listener, scans for it, and verifies that Localhost Radar can map the listener back to the Python process.

Expected output starts with:

```text
PASS
```

## Project structure

```text
.
├── RUN_THIS_Localhost_Radar_v0.3.pyw  # silent Windows launcher
├── main.py                             # application entry point
├── core_test.py                        # localhost detection smoke test
├── requirements.txt
├── src/
│   ├── main_window.py                  # PySide6 UI and scan workflow
│   ├── models.py                       # port/process models and classification
│   ├── port_scanner.py                 # listening TCP discovery
│   ├── process_manager.py              # process metadata and safe termination
│   └── settings_manager.py             # persistent settings
└── *.bat                               # install, debug and test helpers
```

## Privacy and behavior

Localhost Radar is a local desktop utility. It does not require a cloud backend, background service or tray agent. The scanner reads local listening TCP connections and local process metadata through `psutil`.

Some process details can require elevated permissions on Windows. If listener enumeration or process metadata is denied, try running the application as Administrator.

## Version

Current release: **v0.3.0 — BUILD 2026-08-30-B**

See [CHANGELOG.md](CHANGELOG.md) for release notes.

## License

No license has been selected yet. Until a license is added, the source remains under the repository owner's default copyright rights.
