"""Localhost Radar v0.3 entry point."""
from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from src.main_window import APP_VERSION, BUILD_ID, LocalhostRadarWindow
from src.settings_manager import SettingsManager


def configure_logging(settings: SettingsManager) -> None:
    logging.basicConfig(
        filename=settings.log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        encoding="utf-8",
    )


def main() -> int:
    settings = SettingsManager()
    configure_logging(settings)
    app = QApplication(sys.argv)
    app.setApplicationName(f"Localhost Radar v{APP_VERSION}")
    app.setOrganizationName("Localhost Radar")
    app.setQuitOnLastWindowClosed(True)
    try:
        window = LocalhostRadarWindow(settings)
        window.show()
        return app.exec()
    except Exception as exc:
        logging.exception("Fatal startup error")
        QMessageBox.critical(None, "Localhost Radar", f"Startup failed:\n{exc}\n\nBuild: {BUILD_ID}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
