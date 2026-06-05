"""Confirmation dialog for deleting a game."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


class DeleteGameDialog(QDialog):
    def __init__(self, game_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._game_name = game_name
        self.setWindowTitle("Delete Game")
        self.setMinimumWidth(420)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(f'Delete <b>"{game_name}"</b>?')
        title.setStyleSheet("font-size: 14px;")
        layout.addWidget(title)

        self._remote_check = QCheckBox("Also delete all remote assets from GitHub Pages")
        layout.addWidget(self._remote_check)

        remote_warn = QLabel("This will permanently remove all uploaded images and the save file.")
        remote_warn.setStyleSheet("color: #f38ba8; font-size: 11px; padding-left: 22px;")
        remote_warn.setWordWrap(True)
        layout.addWidget(remote_warn)

        confirm_label = QLabel("Type the game name to confirm:")
        confirm_label.setStyleSheet("color: #7f849c; font-size: 12px; margin-top: 4px;")
        layout.addWidget(confirm_label)

        self._confirm = QLineEdit()
        self._confirm.setPlaceholderText(game_name)
        self._confirm.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._confirm)

        layout.addWidget(self._build_buttons())

    def _build_buttons(self) -> QWidget:
        box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        self._delete_btn = box.button(QDialogButtonBox.StandardButton.Ok)
        self._delete_btn.setText("Delete Game")
        self._delete_btn.setEnabled(False)
        self._delete_btn.setStyleSheet(
            "background: #d20f39; border-color: #d20f39; color: #fff; padding: 6px 20px;"
        )
        return box

    def _on_text_changed(self, text: str) -> None:
        self._delete_btn.setEnabled(text == self._game_name)

    def delete_remote(self) -> bool:
        return self._remote_check.isChecked()
