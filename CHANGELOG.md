# Changelog

All notable changes to Localhost Radar are documented here.

## [0.3.0] - 2026-08-30

Build: `2026-08-30-B`

### Added

- Large, explicit `Scan now`, `Full refresh` and `Settings` controls
- Visible scanning state, scan counter and last-scan timestamp
- Separate executable-path and command-line fields
- Favorites filtering
- Conservative browser-opening logic for HTTP-like services
- Possible leftover development-server indicator
- IPv4 / IPv6 duplicate-listener collapse
- Persistent settings integration
- Safe process-termination guard for critical Windows processes
- Silent `.pyw` launcher with no separate long-running backend process
- Core smoke test that opens a real localhost listener and verifies process mapping

### Changed

- Reworked right-side details layout for better spacing and readability
- `Full refresh` now clears process metadata cache before rescanning
- Non-web services such as PostgreSQL and MySQL no longer receive misleading `http://localhost:<port>` URLs

### Verified

Core test result:

```text
PASS
```
