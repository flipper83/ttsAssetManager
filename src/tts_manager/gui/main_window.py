"""Main application window."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor, QFont, QKeySequence, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..classifier import classify_assets
from ..config import Config
from ..manager import AssetManager
from ..progress import EventKind, ProgressEvent
from .settings_dialog import SettingsDialog
from .worker import AssetWorker

# Log colours per event kind
_LOG_COLOURS = {
    EventKind.UPLOAD: "#4ec94e",
    EventKind.SKIP:   "#888888",
    EventKind.DELETE: "#e0a030",
    EventKind.WARNING:"#e0c030",
    EventKind.COMPOSE:"#6ab0e0",
    EventKind.INFO:   "#cccccc",
}

_STYLESHEET = """
QMainWindow, QWidget { background: #1e1e2e; color: #cdd6f4; font-family: 'SF Pro Text', 'Segoe UI', sans-serif; font-size: 13px; }
QPushButton { background: #313244; border: 1px solid #45475a; border-radius: 6px; padding: 6px 18px; color: #cdd6f4; }
QPushButton:hover { background: #45475a; }
QPushButton:pressed { background: #585b70; }
QPushButton:disabled { color: #585b70; border-color: #313244; }
QPushButton#upload_btn { background: #1e66f5; border-color: #1e66f5; color: #ffffff; }
QPushButton#upload_btn:hover { background: #3d7ef7; }
QPushButton#upload_btn:disabled { background: #313244; border-color: #313244; color: #585b70; }
QPushButton#update_btn { background: #40a02b; border-color: #40a02b; color: #ffffff; }
QPushButton#update_btn:hover { background: #5abf3f; }
QPushButton#update_btn:disabled { background: #313244; border-color: #313244; color: #585b70; }
QLineEdit { background: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 4px 8px; color: #cdd6f4; }
QTreeWidget { background: #181825; border: 1px solid #313244; border-radius: 4px; alternate-background-color: #1e1e2e; }
QTreeWidget::item { padding: 2px 4px; }
QTreeWidget::item:selected { background: #313244; }
QTextEdit { background: #181825; border: 1px solid #313244; border-radius: 4px; font-family: 'SF Mono', 'Menlo', 'Consolas', monospace; font-size: 12px; }
QSplitter::handle { background: #313244; }
QStatusBar { background: #181825; border-top: 1px solid #313244; color: #888; }
QLabel#section_label { color: #7f849c; font-size: 11px; font-weight: bold; letter-spacing: 0.5px; }
"""


class MainWindow(QMainWindow):
    def __init__(self, config: Config, config_path: Path, project_root: Path) -> None:
        super().__init__()
        self._config = config
        self._config_path = config_path
        self._root = project_root
        self._worker: AssetWorker | None = None

        self.setWindowTitle("TTS Asset Manager")
        self.setMinimumSize(860, 580)
        self.resize(960, 660)
        self.setStyleSheet(_STYLESHEET)

        self._build_menu_bar()
        self._build_ui()
        self._scan()

    # ------------------------------------------------------------------
    # Menu bar (native on macOS)
    # ------------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        mb = self.menuBar()

        # TTS Manager / File menu — Settings with Cmd+, (standard macOS shortcut)
        file_menu = mb.addMenu("File")
        settings_action = QAction("Settings…", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)
        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(QApplication.quit)
        file_menu.addAction(quit_action)

        # Assets menu
        assets_menu = mb.addMenu("Assets")
        scan_action = QAction("Scan Input Folder", self)
        scan_action.setShortcut(QKeySequence("Ctrl+R"))
        scan_action.triggered.connect(self._scan)
        assets_menu.addAction(scan_action)
        assets_menu.addSeparator()
        upload_action = QAction("Upload All", self)
        upload_action.setShortcut(QKeySequence("Ctrl+U"))
        upload_action.triggered.connect(self._on_upload)
        assets_menu.addAction(upload_action)
        update_action = QAction("Update Changed", self)
        update_action.setShortcut(QKeySequence("Ctrl+Shift+U"))
        update_action.triggered.connect(self._on_update)
        assets_menu.addAction(update_action)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 8)
        root_layout.setSpacing(8)

        root_layout.addLayout(self._build_input_bar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_asset_panel())
        splitter.addWidget(self._build_log_panel())
        splitter.setSizes([280, 620])
        root_layout.addWidget(splitter, stretch=1)

        root_layout.addLayout(self._build_action_bar())

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._set_status("Ready", "●")

    def _build_input_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(6)

        lbl = QLabel("Input folder:")
        lbl.setFixedWidth(90)
        layout.addWidget(lbl)

        self._input_edit = QLineEdit(str(self._root / "input"))
        layout.addWidget(self._input_edit, stretch=1)

        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_input)
        layout.addWidget(browse_btn)

        scan_btn = QPushButton("Scan")
        scan_btn.setFixedWidth(70)
        scan_btn.clicked.connect(self._scan)
        layout.addWidget(scan_btn)

        return layout

    def _build_asset_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(4)

        lbl = QLabel("ASSETS")
        lbl.setObjectName("section_label")
        layout.addWidget(lbl)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setAlternatingRowColors(True)
        layout.addWidget(self._tree)

        return panel

    def _build_log_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 0, 0, 0)
        layout.setSpacing(4)

        lbl = QLabel("LOG")
        lbl.setObjectName("section_label")
        layout.addWidget(lbl)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        layout.addWidget(self._log)

        return panel

    def _build_action_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(8)

        self._upload_btn = QPushButton("Upload All")
        self._upload_btn.setObjectName("upload_btn")
        self._upload_btn.setFixedHeight(34)
        self._upload_btn.clicked.connect(self._on_upload)
        layout.addWidget(self._upload_btn)

        self._update_btn = QPushButton("Update")
        self._update_btn.setObjectName("update_btn")
        self._update_btn.setFixedHeight(34)
        self._update_btn.clicked.connect(self._on_update)
        layout.addWidget(self._update_btn)

        layout.addStretch()

        clear_btn = QPushButton("Clear log")
        clear_btn.clicked.connect(self._log.clear)
        layout.addWidget(clear_btn)

        return layout

    # ------------------------------------------------------------------
    # Asset tree
    # ------------------------------------------------------------------

    def _scan(self) -> None:
        input_dir = Path(self._input_edit.text())
        if not input_dir.is_dir():
            self._set_status("Input folder not found", "⚠", "#e0c030")
            return

        warnings: list[str] = []
        collection = classify_assets(
            input_dir,
            on_progress=lambda e: warnings.append(e.message) if e.kind == EventKind.WARNING else None,
        )

        self._tree.clear()
        categories = [
            ("Decks",  collection.decks,  lambda d: [c.card_name for c in d.cards]),
            ("Cards",  collection.cards,  lambda c: ["front" + (" + back" if c.back_path else "")]),
            ("Tiles",  collection.tiles,  lambda t: ["front" + (" + back" if t.back_path else "")]),
            ("Tokens", collection.tokens, lambda t: [t.front_path.name]),
        ]

        total = 0
        for cat_name, assets, children_fn in categories:
            if not assets:
                continue
            cat_item = QTreeWidgetItem(self._tree, [f"{cat_name}  ({len(assets)})"])
            font = QFont()
            font.setBold(True)
            cat_item.setFont(0, font)
            cat_item.setForeground(0, QColor("#89b4fa"))
            for name, asset in sorted(assets.items()):
                asset_item = QTreeWidgetItem(cat_item, [name])
                for child_label in children_fn(asset):
                    QTreeWidgetItem(asset_item, [f"  {child_label}"]).setForeground(0, QColor("#7f849c"))
            cat_item.setExpanded(True)
            total += len(assets)

        status = f"Scanned: {total} assets"
        if warnings:
            status += f"  ⚠ {len(warnings)} warning(s)"
        self._set_status(status, "●")
        self._upload_btn.setEnabled(True)
        self._update_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_upload(self) -> None:
        self._run(incremental=False)

    def _on_update(self) -> None:
        self._run(incremental=True)

    def _run(self, incremental: bool) -> None:
        manager = AssetManager(
            config=self._config,
            input_dir=Path(self._input_edit.text()),
            skeleton_path=self._root / "skeleton" / "TS_Save_138.json",
            output_dir=self._root / "output",
            processed_dir=self._root / "processed",
            state_file=self._root / "processed" / "state.json",
        )

        self._worker = AssetWorker(manager, incremental=incremental)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

        self._upload_btn.setEnabled(False)
        self._update_btn.setEnabled(False)
        label = "Updating..." if incremental else "Uploading..."
        self._set_status(label, "⟳", "#6ab0e0")
        self._log_line(f"{'Update' if incremental else 'Upload'} started", "#89b4fa")

    # ------------------------------------------------------------------
    # Progress & completion
    # ------------------------------------------------------------------

    def _on_progress(self, event: ProgressEvent) -> None:
        colour = _LOG_COLOURS.get(event.kind, "#cccccc")
        self._log_line(event.message, colour)

    def _on_finished(self, success: bool, message: str) -> None:
        if success:
            self._log_line("✓ " + message, "#4ec94e")
            self._set_status("Done", "✓", "#4ec94e")
            self._scan()
        else:
            self._log_line("✗ " + message, "#f38ba8")
            self._set_status("Error — see log", "✗", "#f38ba8")
            QMessageBox.critical(self, "Error", message)

        self._upload_btn.setEnabled(True)
        self._update_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._config, self._config_path, self)
        if dlg.exec():
            self._set_status("Settings saved", "✓", "#4ec94e")

    def _browse_input(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select input folder", self._input_edit.text())
        if path:
            self._input_edit.setText(path)
            self._scan()

    def _log_line(self, text: str, colour: str = "#cccccc") -> None:
        self._log.moveCursor(QTextCursor.MoveOperation.End)
        self._log.insertHtml(f'<span style="color:{colour};">{text}</span><br>')
        self._log.moveCursor(QTextCursor.MoveOperation.End)

    def _set_status(self, text: str, icon: str = "●", colour: str = "#888888") -> None:
        self._status.showMessage(f"  {icon}  {text}")
        self._status.setStyleSheet(f"QStatusBar {{ color: {colour}; }}")
