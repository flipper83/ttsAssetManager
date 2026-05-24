"""Settings dialog — configure GitHub credentials and TTS saves folder."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..config import Config, detect_tts_saves_paths


class SettingsDialog(QDialog):
    def __init__(self, config: Config, config_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._config_path = config_path

        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(self._build_github_group())
        layout.addWidget(self._build_tts_group())
        layout.addWidget(self._build_buttons())

        self._populate(config)

    # ------------------------------------------------------------------
    # Build sections
    # ------------------------------------------------------------------

    def _build_github_group(self) -> QGroupBox:
        group = QGroupBox("GitHub")
        form = QFormLayout(group)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Token with show/hide toggle
        token_row = QHBoxLayout()
        self._token = QLineEdit()
        self._token.setEchoMode(QLineEdit.EchoMode.Password)
        self._token.setPlaceholderText("ghp_…")
        token_row.addWidget(self._token)
        show_btn = QToolButton()
        show_btn.setText("Show")
        show_btn.setCheckable(True)
        show_btn.toggled.connect(
            lambda on: self._token.setEchoMode(
                QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password
            )
        )
        token_row.addWidget(show_btn)
        form.addRow("Token:", token_row)

        help_lbl = QLabel(
            '<a href="https://github.com/settings/tokens" style="color:#89b4fa;">'
            "Generate a token</a> with <b>public_repo</b> scope."
        )
        help_lbl.setOpenExternalLinks(True)
        help_lbl.setStyleSheet("color: #7f849c; font-size: 11px;")
        form.addRow("", help_lbl)

        self._owner = QLineEdit()
        self._owner.setPlaceholderText("your-github-username")
        form.addRow("Owner:", self._owner)

        self._repo = QLineEdit()
        self._repo.setPlaceholderText("tts-assets")
        form.addRow("Repo:", self._repo)

        self._branch = QLineEdit()
        self._branch.setPlaceholderText("gh-pages")
        form.addRow("Branch:", self._branch)

        return group

    def _build_tts_group(self) -> QGroupBox:
        group = QGroupBox("Tabletop Simulator")
        form = QFormLayout(group)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        saves_row = QHBoxLayout()
        self._saves_path = QLineEdit()
        self._saves_path.setPlaceholderText("Path to TTS Saves folder")
        saves_row.addWidget(self._saves_path)

        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(70)
        browse_btn.clicked.connect(self._browse_saves)
        saves_row.addWidget(browse_btn)

        # Suggest button with detected paths
        suggestions = detect_tts_saves_paths()
        if suggestions:
            suggest_btn = QToolButton()
            suggest_btn.setText("Suggest ▾")
            suggest_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            menu = QMenu(suggest_btn)
            for label, path in suggestions:
                exists = path.is_dir()
                action = menu.addAction(f"{'✓ ' if exists else ''}{label}")
                action.setToolTip(str(path))
                action.triggered.connect(lambda _checked, p=path: self._saves_path.setText(str(p)))
                if not exists:
                    action.setEnabled(False)
            # If none exist, enable them anyway so user can pick
            if not any(p.is_dir() for _, p in suggestions):
                for action in menu.actions():
                    action.setEnabled(True)
            suggest_btn.setMenu(menu)
            saves_row.addWidget(suggest_btn)

        form.addRow("Saves folder:", saves_row)

        self._save_name = QLineEdit()
        self._save_name.setPlaceholderText("MyGame")
        form.addRow("Save name:", self._save_name)

        return group

    def _build_buttons(self) -> QWidget:
        box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        box.accepted.connect(self._save)
        box.rejected.connect(self.reject)
        # Style the Save button
        save_btn = box.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setStyleSheet(
            "background: #1e66f5; border-color: #1e66f5; color: #fff; padding: 6px 20px;"
        )
        return box

    # ------------------------------------------------------------------
    # Logic
    # ------------------------------------------------------------------

    def _populate(self, config: Config) -> None:
        self._token.setText(config.github_token)
        self._owner.setText(config.github_owner)
        self._repo.setText(config.github_repo)
        self._branch.setText(config.github_branch)
        self._saves_path.setText(config.tts_saves_path or "")
        self._save_name.setText(config.save_name)

        # Auto-suggest if saves path is empty
        if not config.tts_saves_path:
            for _, path in detect_tts_saves_paths():
                if path.is_dir():
                    self._saves_path.setText(str(path))
                    break

    def _browse_saves(self) -> None:
        current = self._saves_path.text() or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, "Select TTS Saves folder", current)
        if path:
            self._saves_path.setText(path)

    def _save(self) -> None:
        self._config.github_token = self._token.text().strip()
        self._config.github_owner = self._owner.text().strip()
        self._config.github_repo = self._repo.text().strip()
        self._config.github_branch = self._branch.text().strip() or "gh-pages"
        self._config.tts_saves_path = self._saves_path.text().strip() or None
        self._config.save_name = self._save_name.text().strip() or "MyGame"
        self._config.save(self._config_path)
        self.accept()
