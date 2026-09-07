# Contributing

Thanks for your interest in Localhost Radar.

## Development setup

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

## Before opening a pull request

Run the core smoke test:

```bash
python core_test.py
```

Also run a syntax check:

```bash
python -m compileall -q .
```

Please keep changes focused. Localhost Radar intentionally avoids a background service, tray agent, separate backend process or unnecessary network dependency.

When changing scan behavior, verify both `Scan now` and `Full refresh`. When changing process termination, preserve protection for critical Windows processes.
