"""Main application window."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor, QFont, QKeySequence, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
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
from ..config import Config, GameConfig
from ..manager import AssetManager
from ..progress import EventKind, ProgressEvent
from .new_game_dialog import NewGameDialog
from .settings_dialog import SettingsDialog
from .worker import AssetWorker

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
QPushButton#new_game_btn { background: #313244; border: 1px dashed #585b70; border-radius: 6px; padding: 5px 10px; color: #7f849c; font-size: 12px; }
QPushButton#new_game_btn:hover { background: #45475a; color: #cdd6f4; }
QLineEdit { background: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 4px 8px; color: #cdd6f4; }
QListWidget { background: #181825; border: 1px solid #313244; border-radius: 4px; }
QListWidget::item { padding: 6px 8px; border-radius: 3px; }
QListWidget::item:selected { background: #313244; color: #89b4fa; }
QListWidget::item:hover { background: #1e1e2e; }
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
        self._selected_game: GameConfig | None = None

        self.setWindowTitle("TTS Asset Manager")
        self.setMinimumSize(900, 580)
        self.resize(1020, 680)
        self.setStyleSheet(_STYLESHEET)

        self._build_menu_bar()
        self._build_ui()
        self._populate_game_list()

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        mb = self.menuBar()

        file_menu = mb.addMenu("File")
        settings_action = QAction("Settings…", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)
        file_menu.addSeparator()
        new_game_action = QAction("New Game…", self)
        new_game_action.setShortcut(QKeySequence("Ctrl+N"))
        new_game_action.triggered.connect(self._new_game)
        file_menu.addAction(new_game_action)
        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(QApplication.quit)
        file_menu.addAction(quit_action)

        assets_menu = mb.addMenu("Assets")
        scan_action = QAction("Scan Assets", self)
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

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_log_panel())
        splitter.setSizes([300, 680])
        root_layout.addWidget(splitter, stretch=1)

        root_layout.addLayout(self._build_action_bar())

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._set_status("Select or create a game", "●")

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(4)

        # Games section
        games_lbl = QLabel("GAMES")
        games_lbl.setObjectName("section_label")
        layout.addWidget(games_lbl)

        self._game_list = QListWidget()
        self._game_list.setMaximumHeight(130)
        self._game_list.currentRowChanged.connect(self._on_game_selected)
        layout.addWidget(self._game_list)

        new_game_btn = QPushButton("+ New Game")
        new_game_btn.setObjectName("new_game_btn")
        new_game_btn.setFixedHeight(28)
        new_game_btn.clicked.connect(self._new_game)
        layout.addWidget(new_game_btn)

        # Assets section
        assets_lbl = QLabel("ASSETS")
        assets_lbl.setObjectName("section_label")
        layout.addWidget(assets_lbl)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setAlternatingRowColors(True)
        layout.addWidget(self._tree, stretch=1)

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
        self._upload_btn.setEnabled(False)
        self._upload_btn.clicked.connect(self._on_upload)
        layout.addWidget(self._upload_btn)

        self._update_btn = QPushButton("Update")
        self._update_btn.setObjectName("update_btn")
        self._update_btn.setFixedHeight(34)
        self._update_btn.setEnabled(False)
        self._update_btn.clicked.connect(self._on_update)
        layout.addWidget(self._update_btn)

        layout.addStretch()

        clear_btn = QPushButton("Clear log")
        clear_btn.clicked.connect(self._log.clear)
        layout.addWidget(clear_btn)

        return layout

    # ------------------------------------------------------------------
    # Game list
    # ------------------------------------------------------------------

    def _populate_game_list(self) -> None:
        self._game_list.blockSignals(True)
        self._game_list.clear()
        for game in self._config.games:
            item = QListWidgetItem(game.name)
            item.setData(Qt.ItemDataRole.UserRole, game)
            self._game_list.addItem(item)
        self._game_list.blockSignals(False)

        if self._config.games:
            self._game_list.setCurrentRow(0)

    def _on_game_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._config.games):
            self._selected_game = None
            self._upload_btn.setEnabled(False)
            self._update_btn.setEnabled(False)
            return
        self._selected_game = self._config.games[row]
        self._scan()

    def _new_game(self) -> None:
        dlg = NewGameDialog(self)
        if dlg.exec():
            game = dlg.game_config()
            self._config.games.append(game)
            self._config.save(self._config_path)
            self._populate_game_list()
            # Select the newly created game
            self._game_list.setCurrentRow(len(self._config.games) - 1)
            self._log_line(f"Game '{game.name}' created", "#89b4fa")

    # ------------------------------------------------------------------
    # Asset tree
    # ------------------------------------------------------------------

    def _scan(self) -> None:
        self._tree.clear()
        game = self._selected_game
        if not game:
            return

        input_dir = game.assets_path()
        if not input_dir.is_dir():
            self._set_status(f"Assets folder not found: {input_dir}", "⚠", "#e0c030")
            return

        warnings: list[str] = []
        collection = classify_assets(
            input_dir,
            on_progress=lambda e: warnings.append(e.message) if e.kind == EventKind.WARNING else None,
        )

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

        status = f"{game.name} — {total} assets"
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
        game = self._selected_game
        if not game:
            return

        processed_dir = self._root / "processed" / game.github_subfolder
        manager = AssetManager(
            config=self._config,
            game=game,
            skeleton_path=self._root / "skeleton" / "TS_Save_138.json",
            output_dir=self._root / "output",
            processed_dir=processed_dir,
            state_file=processed_dir / "state.json",
        )

        self._worker = AssetWorker(manager, incremental=incremental)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

        self._upload_btn.setEnabled(False)
        self._update_btn.setEnabled(False)
        label = "Updating..." if incremental else "Uploading..."
        self._set_status(label, "⟳", "#6ab0e0")
        self._log_line(f"{'Update' if incremental else 'Upload'} — {game.name}", "#89b4fa")

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

    def _log_line(self, text: str, colour: str = "#cccccc") -> None:
        self._log.moveCursor(QTextCursor.MoveOperation.End)
        self._log.insertHtml(f'<span style="color:{colour};">{text}</span><br>')
        self._log.moveCursor(QTextCursor.MoveOperation.End)

    def _set_status(self, text: str, icon: str = "●", colour: str = "#888888") -> None:
        self._status.showMessage(f"  {icon}  {text}")
        self._status.setStyleSheet(f"QStatusBar {{ color: {colour}; }}")
