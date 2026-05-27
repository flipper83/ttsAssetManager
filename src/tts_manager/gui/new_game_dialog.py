"""Dialog to create a new game entry."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..config import GameConfig, _name_to_subfolder


class NewGameDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Game")
        self.setMinimumWidth(460)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._prev_name = ""
        self._name = QLineEdit()
        self._name.setPlaceholderText("My Game")
        self._name.textChanged.connect(self._on_name_changed)
        form.addRow("Game name:", self._name)

        folder_row = QHBoxLayout()
        self._folder = QLineEdit()
        self._folder.setPlaceholderText("/path/to/assets folder")
        folder_row.addWidget(self._folder)
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(70)
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(browse_btn)
        form.addRow("Assets folder:", folder_row)

        self._subfolder = QLineEdit()
        self._subfolder.setPlaceholderText("auto-derived from name")
        hint = QLabel("Subfolder in GitHub Pages (e.g. my-game). Auto-filled from name.")
        hint.setStyleSheet("color: #7f849c; font-size: 11px;")
        form.addRow("GitHub subfolder:", self._subfolder)
        form.addRow("", hint)

        layout.addLayout(form)
        layout.addWidget(self._build_buttons())

    def _build_buttons(self) -> QWidget:
        box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        box.accepted.connect(self._accept)
        box.rejected.connect(self.reject)
        ok_btn = box.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("Create Game")
        ok_btn.setStyleSheet(
            "background: #1e66f5; border-color: #1e66f5; color: #fff; padding: 6px 20px;"
        )
        return box

    def _on_name_changed(self, text: str) -> None:
        if not self._subfolder.text() or self._subfolder.text() == _name_to_subfolder(self._prev_name):
            self._subfolder.setText(_name_to_subfolder(text))
        self._prev_name = text

    def _browse_folder(self) -> None:
        current = self._folder.text() or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, "Select assets folder", current)
        if path:
            self._folder.setText(path)

    def _accept(self) -> None:
        name = self._name.text().strip()
        folder = self._folder.text().strip()
        if not name:
            self._name.setFocus()
            return
        if not folder:
            self._folder.setFocus()
            return
        self.accept()

    def game_config(self) -> GameConfig:
        name = self._name.text().strip()
        folder = self._folder.text().strip()
        subfolder = self._subfolder.text().strip() or _name_to_subfolder(name)
        return GameConfig(name=name, assets_folder=folder, github_subfolder=subfolder)
