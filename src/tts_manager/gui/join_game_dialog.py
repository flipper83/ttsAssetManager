"""Dialog to join an existing remote game via its save URL."""

from pathlib import Path
from urllib.parse import urlparse

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

from ..config import GameConfig


def parse_save_url(url: str) -> tuple[str, str, str] | None:
    """Parse (owner, repo, subfolder) from a GitHub Pages save URL.

    Expected format: https://{owner}.github.io/{repo}/saves/{subfolder}.json
    Returns None if the URL doesn't match the expected pattern.
    """
    try:
        parsed = urlparse(url.strip())
        host = parsed.hostname or ""
        if not host.endswith(".github.io"):
            return None
        owner = host[: -len(".github.io")]
        parts = [p for p in parsed.path.split("/") if p]
        # parts must be: [repo, "saves", "subfolder.json"]
        if len(parts) != 3 or parts[1] != "saves" or not parts[2].endswith(".json"):
            return None
        repo = parts[0]
        subfolder = parts[2][: -len(".json")]
        if not owner or not repo or not subfolder:
            return None
        return owner, repo, subfolder
    except Exception:
        return None


def _subfolder_to_name(subfolder: str) -> str:
    return subfolder.replace("-", " ").replace("_", " ").title()


class JoinGameDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Join Game")
        self.setMinimumWidth(500)
        self.setModal(True)

        self._parsed: tuple[str, str, str] | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._url = QLineEdit()
        self._url.setPlaceholderText("https://owner.github.io/repo/saves/my-game.json")
        self._url.textChanged.connect(self._on_url_changed)
        form.addRow("Save URL:", self._url)

        self._url_hint = QLabel("")
        self._url_hint.setStyleSheet("font-size: 11px;")
        form.addRow("", self._url_hint)

        self._name = QLineEdit()
        self._name.setPlaceholderText("My Game")
        form.addRow("Game name:", self._name)

        folder_row = QHBoxLayout()
        self._folder = QLineEdit()
        self._folder.setPlaceholderText("/path/to/local/assets folder")
        folder_row.addWidget(self._folder)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(browse_btn)
        form.addRow("Assets folder:", folder_row)

        layout.addLayout(form)
        layout.addWidget(self._build_buttons())

    def _build_buttons(self) -> QWidget:
        box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        box.accepted.connect(self._accept)
        box.rejected.connect(self.reject)
        ok_btn = box.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("Join & Pull")
        ok_btn.setEnabled(False)
        ok_btn.setStyleSheet(
            "background: #04a5e5; border-color: #04a5e5; color: #fff; padding: 6px 20px;"
        )
        self._ok_btn = ok_btn
        return box

    def _on_url_changed(self, text: str) -> None:
        self._parsed = parse_save_url(text)
        if self._parsed:
            owner, repo, subfolder = self._parsed
            self._url_hint.setStyleSheet("font-size: 11px; color: #a6e3a1;")
            self._url_hint.setText(f"✓  {owner}/{repo}  ·  subfolder: {subfolder}")
            if not self._name.text():
                self._name.setText(_subfolder_to_name(subfolder))
        elif text.strip():
            self._url_hint.setStyleSheet("font-size: 11px; color: #f38ba8;")
            self._url_hint.setText("✗  Expected: https://owner.github.io/repo/saves/name.json")
        else:
            self._url_hint.setText("")
        self._ok_btn.setEnabled(self._parsed is not None)

    def _browse_folder(self) -> None:
        current = self._folder.text() or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, "Select assets folder", current)
        if path:
            self._folder.setText(path)

    def _accept(self) -> None:
        if not self._parsed:
            self._url.setFocus()
            return
        if not self._name.text().strip():
            self._name.setFocus()
            return
        if not self._folder.text().strip():
            self._folder.setFocus()
            return
        self.accept()

    def game_config(self) -> GameConfig:
        assert self._parsed is not None
        owner, repo, subfolder = self._parsed
        return GameConfig(
            name=self._name.text().strip(),
            assets_folder=self._folder.text().strip(),
            github_subfolder=subfolder,
            github_owner=owner,
            github_repo=repo,
        )
