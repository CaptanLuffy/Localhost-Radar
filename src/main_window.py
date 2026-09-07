"""Localhost Radar v0.3 user interface.

Design goals for this build:
- obvious, testable Scan / Full refresh buttons (not toolbar actions)
- compact non-overlapping detail panel
- no background service or secondary worker process
- clear build identification so an old copy cannot be mistaken for this one
"""
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, QThread, QTimer, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .models import GREEN_LISTENING, YELLOW_WARNING, PortInfo, is_system_process
from .port_scanner import PortScanner
from .process_manager import ProcessManager
from .settings_manager import SettingsManager

APP_VERSION = "0.3.0"
BUILD_ID = "2026-08-30-B"

BG = "#0F1720"
PANEL = "#17212B"
PANEL_2 = "#1D2A36"
FIELD = "#111A23"
BORDER = "#304252"
TEXT = "#E7EEF5"
MUTED = "#91A3B3"
ACCENT = "#2F9BDB"
ACCENT_HOVER = "#41A9E8"
DANGER = "#7A3340"
DANGER_HOVER = "#93404E"


class ScanWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, scanner: PortScanner, favorites: list[int], collapse_duplicates: bool):
        super().__init__()
        self.scanner = scanner
        self.favorites = list(favorites)
        self.collapse_duplicates = collapse_duplicates

    @Slot()
    def run(self) -> None:
        try:
            result = self.scanner.scan(
                self.favorites,
                collapse_duplicate_bindings=self.collapse_duplicates,
            )
            self.finished.emit(result)
        except Exception as exc:  # surfaced visibly to user
            self.failed.emit(str(exc))


class PortTable(QTableWidget):
    HEADERS = ["★", "Port", "Endpoint", "Process", "PID", "Type", "Age", "Status"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(len(self.HEADERS))
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setAlternatingRowColors(False)
        self.setSortingEnabled(True)
        self.setFont(QFont("Segoe UI", 9))

        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        for col in (0, 1, 4, 5, 6, 7):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self.setStyleSheet(f"""
            QTableWidget {{
                background:{PANEL}; color:{TEXT}; border:1px solid {BORDER};
                border-radius:7px; selection-background-color:#245E82;
            }}
            QTableWidget::item {{ padding:8px 7px; border-bottom:1px solid #243440; }}
            QTableWidget::item:selected {{ background:#245E82; color:white; }}
            QHeaderView::section {{
                background:#223344; color:#DCE7EF; padding:9px 7px;
                border:none; border-right:1px solid #314657; font-weight:600;
            }}
        """)


class ReadOnlyValue(QLineEdit):
    def __init__(self, text: str = "—", parent=None):
        super().__init__(text, parent)
        self.setReadOnly(True)
        self.setMinimumHeight(30)
        self.setStyleSheet(f"""
            QLineEdit {{
                background:{FIELD}; color:{TEXT}; border:1px solid {BORDER};
                border-radius:5px; padding:5px 8px;
            }}
        """)


class DetailPanel(QWidget):
    open_browser_requested = Signal(str)
    copy_endpoint_requested = Signal(str)
    open_folder_requested = Signal(str)
    terminate_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.info: Optional[PortInfo] = None
        self.setMinimumWidth(390)
        self.setMaximumWidth(520)
        self.setStyleSheet(f"background:{PANEL}; color:{TEXT};")

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        top = QHBoxLayout()
        title = QLabel("Port details")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.identity = QLabel("No selection")
        self.identity.setStyleSheet(f"color:{MUTED};")
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(self.identity)
        root.addLayout(top)

        self.hero = QLabel("Select a listener")
        self.hero.setMinimumHeight(58)
        self.hero.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.hero.setStyleSheet(
            f"background:{PANEL_2}; border:1px solid {BORDER}; border-radius:7px; "
            f"padding:10px 12px; color:{TEXT}; font-size:12pt; font-weight:600;"
        )
        root.addWidget(self.hero)

        # Scroll only the data portion; action buttons remain fixed and never overlap.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea{{background:{PANEL};border:none;}}")
        content = QWidget()
        grid = QGridLayout(content)
        grid.setContentsMargins(0, 0, 4, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(7)
        grid.setColumnStretch(1, 1)

        self.values: dict[str, ReadOnlyValue] = {}
        rows = [
            ("Port", "port"),
            ("Endpoint", "endpoint"),
            ("Bind address", "address"),
            ("Protocol", "protocol"),
            ("Status", "status"),
            ("Process", "process"),
            ("PID", "pid"),
            ("Type", "category"),
            ("User", "user"),
            ("Started", "started"),
            ("Browser URL", "url"),
        ]
        for row_index, (caption, key) in enumerate(rows):
            lab = QLabel(caption)
            lab.setStyleSheet(f"color:{MUTED};")
            val = ReadOnlyValue()
            grid.addWidget(lab, row_index, 0, Qt.AlignmentFlag.AlignTop)
            grid.addWidget(val, row_index, 1)
            self.values[key] = val

        r = len(rows)
        exe_label = QLabel("Executable")
        exe_label.setStyleSheet(f"color:{MUTED};")
        self.executable = QTextEdit()
        self.executable.setReadOnly(True)
        self.executable.setFixedHeight(62)
        self.executable.setStyleSheet(
            f"QTextEdit{{background:{FIELD};color:{TEXT};border:1px solid {BORDER};"
            "border-radius:5px;padding:5px;}}"
        )
        grid.addWidget(exe_label, r, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(self.executable, r, 1)

        command_label = QLabel("Command line")
        command_label.setStyleSheet(f"color:{MUTED};")
        self.command = QTextEdit()
        self.command.setReadOnly(True)
        self.command.setFixedHeight(82)
        self.command.setStyleSheet(
            f"QTextEdit{{background:{FIELD};color:{TEXT};border:1px solid {BORDER};"
            "border-radius:5px;padding:5px;}}"
        )
        grid.addWidget(command_label, r + 1, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(self.command, r + 1, 1)

        self.warning = QLabel("")
        self.warning.setWordWrap(True)
        self.warning.setStyleSheet(
            f"color:{YELLOW_WARNING}; background:#392F1B; border:1px solid #665225;"
            "border-radius:5px;padding:7px;"
        )
        self.warning.hide()
        grid.addWidget(self.warning, r + 2, 0, 1, 2)
        grid.setRowStretch(r + 3, 1)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        actions1 = QHBoxLayout()
        self.open_btn = self._button("Open in browser", primary=True)
        self.copy_btn = self._button("Copy endpoint")
        actions1.addWidget(self.open_btn)
        actions1.addWidget(self.copy_btn)
        root.addLayout(actions1)

        actions2 = QHBoxLayout()
        self.folder_btn = self._button("Open folder")
        self.end_btn = self._button("End process", danger=True)
        actions2.addWidget(self.folder_btn)
        actions2.addWidget(self.end_btn)
        root.addLayout(actions2)

        self.open_btn.clicked.connect(self._open)
        self.copy_btn.clicked.connect(self._copy)
        self.folder_btn.clicked.connect(self._folder)
        self.end_btn.clicked.connect(self._terminate)
        self.clear()

    @staticmethod
    def _button(text: str, primary: bool = False, danger: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setMinimumHeight(36)
        if danger:
            base, hover = DANGER, DANGER_HOVER
        elif primary:
            base, hover = ACCENT, ACCENT_HOVER
        else:
            base, hover = "#263B4B", "#304A5E"
        button.setStyleSheet(f"""
            QPushButton {{ background:{base}; color:white; border:1px solid #3A5366;
                border-radius:5px; padding:7px 10px; font-weight:600; }}
            QPushButton:hover {{ background:{hover}; }}
            QPushButton:disabled {{ background:#202C35; color:#637381; border-color:#2A3944; }}
        """)
        return button

    def set_port(self, info: PortInfo) -> None:
        self.info = info
        self.identity.setText(f"PID {info.pid or '—'}")
        self.hero.setText(f"{info.process_name or 'Unknown'}   •   {info.endpoint}")
        data = {
            "port": str(info.port),
            "endpoint": info.endpoint,
            "address": info.display_address,
            "protocol": info.protocol,
            "status": "Possible ghost" if info.is_ghost else info.status,
            "process": info.process_name or "Unknown",
            "pid": str(info.pid) if info.pid else "Unknown",
            "category": info.category,
            "user": info.username or "Unknown",
            "started": info.age_text,
            "url": info.browser_url or "Not detected as a web service",
        }
        for key, value in data.items():
            self.values[key].setText(value)
        self.executable.setPlainText(info.executable_path or "N/A")
        self.command.setPlainText(info.command_line or "N/A")
        self.warning.setText(info.ghost_reason)
        self.warning.setVisible(bool(info.ghost_reason))
        self.open_btn.setEnabled(bool(info.browser_url))
        self.copy_btn.setEnabled(bool(info.endpoint))
        self.folder_btn.setEnabled(bool(info.executable_path))
        self.end_btn.setEnabled(bool(info.pid) and not is_system_process(info.process_name))

    def clear(self) -> None:
        self.info = None
        self.identity.setText("No selection")
        self.hero.setText("Select a listener")
        for value in self.values.values():
            value.setText("—")
        self.executable.setPlainText("—")
        self.command.setPlainText("—")
        self.warning.hide()
        for btn in (self.open_btn, self.copy_btn, self.folder_btn, self.end_btn):
            btn.setEnabled(False)

    def _open(self) -> None:
        if self.info and self.info.browser_url:
            self.open_browser_requested.emit(self.info.browser_url)

    def _copy(self) -> None:
        if self.info:
            self.copy_endpoint_requested.emit(self.info.endpoint)

    def _folder(self) -> None:
        if self.info and self.info.executable_path:
            self.open_folder_requested.emit(self.info.executable_path)

    def _terminate(self) -> None:
        if self.info:
            self.terminate_requested.emit(self.info)


class SettingsDialog(QDialog):
    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(f"Localhost Radar v{APP_VERSION} — Settings")
        self.setMinimumWidth(500)
        self.setStyleSheet(f"""
            QDialog{{background:{BG};color:{TEXT};}}
            QLabel,QCheckBox{{color:{TEXT};}}
            QSpinBox{{background:{FIELD};color:{TEXT};border:1px solid {BORDER};padding:6px;border-radius:4px;}}
            QPushButton{{padding:7px 12px;}}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        title = QLabel("Scanning settings")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        root.addWidget(title)

        hint = QLabel("These options are applied immediately after Save.")
        hint.setStyleSheet(f"color:{MUTED};")
        root.addWidget(hint)

        self.auto = QCheckBox("Enable automatic refresh")
        self.auto.setChecked(bool(settings.get("auto_refresh_enabled", True)))
        root.addWidget(self.auto)

        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("Refresh interval"))
        interval_row.addStretch(1)
        self.interval = QSpinBox()
        self.interval.setRange(3, 300)
        self.interval.setSuffix(" sec")
        self.interval.setValue(max(3, int(settings.get("auto_refresh_interval", 10000)) // 1000))
        interval_row.addWidget(self.interval)
        root.addLayout(interval_row)

        self.collapse = QCheckBox("Merge duplicate IPv4 / IPv6 bindings")
        self.collapse.setChecked(bool(settings.get("collapse_duplicate_bindings", True)))
        root.addWidget(self.collapse)

        self.show_system = QCheckBox("Show Windows / system listeners")
        self.show_system.setChecked(bool(settings.get("show_system_processes", True)))
        root.addWidget(self.show_system)

        self.confirm = QCheckBox("Ask before ending a process")
        self.confirm.setChecked(bool(settings.get("confirm_termination", True)))
        root.addWidget(self.confirm)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"color:{BORDER};")
        root.addWidget(divider)

        note = QLabel(
            "Silent mode uses pythonw.exe. Localhost Radar does not install a service, "
            "tray agent or second worker process. The scanner thread lives inside this GUI process."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{MUTED};")
        root.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.auto.toggled.connect(self.interval.setEnabled)
        self.interval.setEnabled(self.auto.isChecked())

    def save_values(self) -> None:
        self.settings.set("auto_refresh_enabled", self.auto.isChecked())
        self.settings.set("auto_refresh_interval", self.interval.value() * 1000)
        self.settings.set("collapse_duplicate_bindings", self.collapse.isChecked())
        self.settings.set("show_system_processes", self.show_system.isChecked())
        self.settings.set("confirm_termination", self.confirm.isChecked())


class LocalhostRadarWindow(QMainWindow):
    def __init__(self, settings_manager: SettingsManager):
        super().__init__()
        self.settings = settings_manager
        self.process_manager = ProcessManager()
        self.scanner = PortScanner(self.process_manager)
        self.favorite_ports = self.settings.get_favorite_ports()
        self.all_ports: List[PortInfo] = []
        self.scan_thread: Optional[QThread] = None
        self.scan_worker: Optional[ScanWorker] = None
        self.scan_count = 0
        self._closing = False
        self._pending_auto_scan = False

        self.setWindowTitle(f"Localhost Radar v{APP_VERSION} — BUILD {BUILD_ID}")
        self.resize(1440, 820)
        self.setMinimumSize(1050, 650)
        self._build_ui()
        self._build_statusbar()
        self._setup_timer()
        QTimer.singleShot(150, lambda: self.request_scan(full_refresh=True, source="startup"))

    def _build_ui(self) -> None:
        central = QWidget()
        central.setStyleSheet(f"background:{BG};color:{TEXT};")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(9)

        # Build identity: deliberately impossible to confuse with the old toolbar build.
        header = QHBoxLayout()
        brand = QLabel("LOCALHOST RADAR")
        brand.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        build = QLabel(f"v{APP_VERSION}  •  BUILD {BUILD_ID}")
        build.setStyleSheet(
            "background:#13364A;color:#72C7F6;border:1px solid #245A76;"
            "border-radius:10px;padding:4px 9px;font-weight:600;"
        )
        header.addWidget(brand)
        header.addWidget(build)
        header.addStretch(1)
        self.scan_state = QLabel("READY")
        self.scan_state.setStyleSheet(
            "background:#153626;color:#7DE2A5;border:1px solid #285A40;"
            "border-radius:10px;padding:4px 9px;font-weight:700;"
        )
        header.addWidget(self.scan_state)
        root.addLayout(header)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.scan_btn = QPushButton("Scan now   F5")
        self.full_btn = QPushButton("Full refresh   Ctrl+F5")
        self.settings_btn = QPushButton("Settings")
        for button in (self.scan_btn, self.full_btn, self.settings_btn):
            button.setMinimumHeight(38)
        self.scan_btn.setStyleSheet(self._button_css(ACCENT, ACCENT_HOVER))
        self.full_btn.setStyleSheet(self._button_css("#315267", "#3B637C"))
        self.settings_btn.setStyleSheet(self._button_css("#2A3B48", "#344B5B"))
        self.scan_btn.clicked.connect(lambda: self.request_scan(False, "manual"))
        self.full_btn.clicked.connect(lambda: self.request_scan(True, "manual"))
        self.settings_btn.clicked.connect(self.open_settings)
        controls.addWidget(self.scan_btn)
        controls.addWidget(self.full_btn)
        controls.addWidget(self.settings_btn)

        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.setPlaceholderText("Search port, endpoint, process, PID or type…")
        self.search.setMinimumHeight(38)
        self.search.setStyleSheet(
            f"QLineEdit{{background:{PANEL_2};color:{TEXT};border:1px solid {BORDER};"
            "border-radius:6px;padding:7px 10px;}}"
        )
        self.search.textChanged.connect(self.apply_filter)
        controls.addWidget(self.search, 1)

        self.only_favorites = QCheckBox("Favorites only")
        self.only_favorites.setStyleSheet(f"color:{TEXT};padding:6px;")
        self.only_favorites.toggled.connect(self.apply_filter)
        controls.addWidget(self.only_favorites)
        root.addLayout(controls)

        self.progress = QFrame()
        self.progress.setFixedHeight(3)
        self.progress.setStyleSheet("background:#214A63;border-radius:1px;")
        self.progress.hide()
        root.addWidget(self.progress)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        splitter.setStyleSheet("QSplitter::handle{background:#21303B;}")

        self.table = PortTable()
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.cellDoubleClicked.connect(self._double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        splitter.addWidget(self.table)

        self.details = DetailPanel()
        self.details.open_browser_requested.connect(self.open_browser)
        self.details.copy_endpoint_requested.connect(self.copy_text)
        self.details.open_folder_requested.connect(self.open_folder)
        self.details.terminate_requested.connect(self.terminate_process)
        splitter.addWidget(self.details)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([980, 420])
        root.addWidget(splitter, 1)

        # Real keyboard shortcuts attached to buttons instead of invisible toolbar actions.
        self.scan_btn.setShortcut("F5")
        self.full_btn.setShortcut("Ctrl+F5")

    @staticmethod
    def _button_css(base: str, hover: str) -> str:
        return f"""
            QPushButton{{background:{base};color:white;border:1px solid #466174;
                border-radius:6px;padding:7px 12px;font-weight:600;}}
            QPushButton:hover{{background:{hover};}}
            QPushButton:disabled{{background:#202D36;color:#6A7984;border-color:#2B3B46;}}
        """

    def _build_statusbar(self) -> None:
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")
        self.last_scan = QLabel("Last scan: —")
        self.scan_number = QLabel("Scan #0")
        self.count_label = QLabel("0 shown / 0 total")
        for label in (self.last_scan, self.scan_number, self.count_label):
            label.setStyleSheet("padding:0 7px;")
            self.status.addPermanentWidget(label)

    def _setup_timer(self) -> None:
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(lambda: self.request_scan(False, "auto"))
        self._apply_timer_settings()

    def _apply_timer_settings(self) -> None:
        interval = max(3000, int(self.settings.get("auto_refresh_interval", 10000)))
        self.refresh_timer.setInterval(interval)
        if bool(self.settings.get("auto_refresh_enabled", True)):
            self.refresh_timer.start()
        else:
            self.refresh_timer.stop()

    def _set_scanning_ui(self, active: bool, full_refresh: bool = False) -> None:
        self.scan_btn.setEnabled(not active)
        self.full_btn.setEnabled(not active)
        self.settings_btn.setEnabled(not active)
        self.progress.setVisible(active)
        if active:
            self.scan_state.setText("FULL REFRESH…" if full_refresh else "SCANNING…")
            self.scan_state.setStyleSheet(
                "background:#4A3512;color:#FFD784;border:1px solid #72541E;"
                "border-radius:10px;padding:4px 9px;font-weight:700;"
            )
            self.scan_btn.setText("Scanning…")
        else:
            self.scan_state.setText("READY")
            self.scan_state.setStyleSheet(
                "background:#153626;color:#7DE2A5;border:1px solid #285A40;"
                "border-radius:10px;padding:4px 9px;font-weight:700;"
            )
            self.scan_btn.setText("Scan now   F5")

    def request_scan(self, full_refresh: bool = False, source: str = "manual") -> None:
        if self._closing:
            return
        if self.scan_thread and self.scan_thread.isRunning():
            if source == "auto":
                self._pending_auto_scan = True
            else:
                self.status.showMessage("A scan is already running", 1500)
            return

        if full_refresh:
            self.process_manager.refresh_process_cache()
        self._set_scanning_ui(True, full_refresh)
        self.status.showMessage("Refreshing everything…" if full_refresh else "Scanning listening TCP ports…")

        collapse = bool(self.settings.get("collapse_duplicate_bindings", True))
        self.scan_thread = QThread(self)
        self.scan_worker = ScanWorker(self.scanner, self.favorite_ports, collapse)
        self.scan_worker.moveToThread(self.scan_thread)
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self._scan_finished)
        self.scan_worker.failed.connect(self._scan_failed)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.failed.connect(self.scan_thread.quit)
        self.scan_worker.finished.connect(self.scan_worker.deleteLater)
        self.scan_worker.failed.connect(self.scan_worker.deleteLater)
        self.scan_thread.finished.connect(self._thread_finished)
        self.scan_thread.start()

    @Slot(list)
    def _scan_finished(self, rows: list) -> None:
        self.all_ports = rows
        self.scan_count += 1
        now = datetime.now().strftime("%H:%M:%S")
        self.last_scan.setText(f"Last scan: {now}")
        self.scan_number.setText(f"Scan #{self.scan_count}")
        self.apply_filter()
        self.status.showMessage(f"Scan complete — {len(rows)} listening endpoint(s)", 2500)

    @Slot(str)
    def _scan_failed(self, message: str) -> None:
        self.status.showMessage("Scan failed")
        QMessageBox.warning(self, "Scan failed", message)

    @Slot()
    def _thread_finished(self) -> None:
        thread = self.scan_thread
        self.scan_thread = None
        self.scan_worker = None
        if thread:
            thread.deleteLater()
        self._set_scanning_ui(False)
        if self._closing:
            return
        if self._pending_auto_scan:
            self._pending_auto_scan = False
            QTimer.singleShot(100, lambda: self.request_scan(False, "auto"))

    @Slot()
    def apply_filter(self) -> None:
        query = self.search.text().strip().lower()
        favorites_only = self.only_favorites.isChecked()
        show_system = bool(self.settings.get("show_system_processes", True))
        rows: list[PortInfo] = []
        for info in self.all_ports:
            if favorites_only and not info.is_favorite:
                continue
            if not show_system and is_system_process(info.process_name) and not info.is_favorite:
                continue
            text = " ".join([
                str(info.port), info.endpoint, info.display_address, info.process_name,
                str(info.pid), info.category, info.status, info.executable_path,
                info.command_line,
            ]).lower()
            if query and query not in text:
                continue
            rows.append(info)
        self._populate_table(rows)
        self.count_label.setText(f"{len(rows)} shown / {len(self.all_ports)} total")

    def _populate_table(self, rows: List[PortInfo]) -> None:
        old = self._selected_info()
        selected_key = (old.port, old.pid, old.endpoint) if old else None
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        selected_row = -1
        for row, info in enumerate(rows):
            values = [
                "★" if info.is_favorite else "☆",
                str(info.port), info.endpoint, info.process_name,
                str(info.pid) if info.pid else "—", info.category,
                info.age_text, "Possible ghost" if info.is_ghost else info.status,
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, info)
                if col == 1:
                    item.setData(Qt.ItemDataRole.DisplayRole, info.port)
                elif col == 4 and info.pid:
                    item.setData(Qt.ItemDataRole.DisplayRole, info.pid)
                if col == 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if info.is_ghost:
                    item.setBackground(QColor("#41331E"))
                elif col == 7:
                    item.setForeground(QColor(GREEN_LISTENING))
                self.table.setItem(row, col, item)
            if selected_key == (info.port, info.pid, info.endpoint):
                selected_row = row
        self.table.setSortingEnabled(True)
        if rows:
            self.table.selectRow(selected_row if selected_row >= 0 else 0)
        else:
            self.details.clear()

    def _selected_info(self) -> Optional[PortInfo]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    @Slot()
    def _selection_changed(self) -> None:
        info = self._selected_info()
        self.details.set_port(info) if info else self.details.clear()

    @Slot(int, int)
    def _double_click(self, _row: int, _column: int) -> None:
        info = self._selected_info()
        if not info:
            return
        if info.browser_url:
            self.open_browser(info.browser_url)
        else:
            self.copy_text(info.endpoint)
            self.status.showMessage("Not a detected web service — endpoint copied instead", 2200)

    @Slot(object)
    def _show_context_menu(self, pos) -> None:
        info = self._selected_info()
        if not info:
            return
        menu = QMenu(self)
        open_action = menu.addAction("Open in browser")
        copy_endpoint = menu.addAction("Copy endpoint")
        copy_pid = menu.addAction("Copy PID")
        menu.addSeparator()
        favorite = menu.addAction("Remove favorite" if info.is_favorite else "Add favorite")
        folder = menu.addAction("Open executable folder")
        menu.addSeparator()
        end_action = menu.addAction("End process")
        open_action.setEnabled(bool(info.browser_url))
        folder.setEnabled(bool(info.executable_path))
        end_action.setEnabled(bool(info.pid) and not is_system_process(info.process_name))
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen == open_action:
            self.open_browser(info.browser_url)
        elif chosen == copy_endpoint:
            self.copy_text(info.endpoint)
        elif chosen == copy_pid:
            self.copy_text(str(info.pid))
        elif chosen == favorite:
            self.toggle_favorite(info.port)
        elif chosen == folder:
            self.open_folder(info.executable_path)
        elif chosen == end_action:
            self.terminate_process(info)

    def toggle_favorite(self, port: int) -> None:
        if port in self.favorite_ports:
            self.settings.remove_favorite_port(port)
        else:
            self.settings.add_favorite_port(port)
        self.favorite_ports = self.settings.get_favorite_ports()
        for info in self.all_ports:
            info.is_favorite = info.port in self.favorite_ports
        self.all_ports.sort(key=lambda x: (not x.is_favorite, x.port, x.endpoint, x.pid))
        self.apply_filter()

    @Slot(str)
    def open_browser(self, url: str) -> None:
        if not url:
            return
        ok = QDesktopServices.openUrl(QUrl(url))
        self.status.showMessage("Opened in default browser" if ok else "Browser could not be opened", 1800)

    @Slot(str)
    def copy_text(self, text: str) -> None:
        QApplication.clipboard().setText(text or "")
        self.status.showMessage("Copied to clipboard", 1500)

    @Slot(str)
    def open_folder(self, executable_path: str) -> None:
        if not executable_path:
            return
        path = Path(executable_path)
        folder = path.parent
        try:
            if os.name == "nt":
                os.startfile(str(folder))  # type: ignore[attr-defined]
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
            self.status.showMessage("Executable folder opened", 1800)
        except Exception as exc:
            QMessageBox.warning(self, "Open folder", str(exc))

    @Slot(object)
    def terminate_process(self, info: PortInfo) -> None:
        if not info.pid:
            return
        if is_system_process(info.process_name):
            QMessageBox.warning(self, "Protected process", "This Windows/system process is protected.")
            return
        if bool(self.settings.get("confirm_termination", True)):
            answer = QMessageBox.question(
                self,
                "End process?",
                f"End {info.process_name} (PID {info.pid})?\n\nAll listeners owned by it will close.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        ok, message = self.process_manager.terminate_process(info.pid, force=False)
        if not ok and "3 seconds" in message:
            answer = QMessageBox.question(
                self,
                "Force kill?",
                message + "\n\nForce kill it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                ok, message = self.process_manager.terminate_process(info.pid, force=True)
        (QMessageBox.information if ok else QMessageBox.warning)(self, "Process", message)
        self.request_scan(True, "manual")

    def open_settings(self) -> None:
        before = bool(self.settings.get("collapse_duplicate_bindings", True))
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        dialog.save_values()
        after = bool(self.settings.get("collapse_duplicate_bindings", True))
        self._apply_timer_settings()
        self.apply_filter()
        self.status.showMessage("Settings saved and applied", 1800)
        if before != after:
            self.request_scan(True, "manual")

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        self._closing = True
        self.refresh_timer.stop()
        if self.scan_thread and self.scan_thread.isRunning():
            # The worker is a QThread in THIS process, not a separate background process.
            self.scan_thread.quit()
            self.scan_thread.wait(5000)
        super().closeEvent(event)