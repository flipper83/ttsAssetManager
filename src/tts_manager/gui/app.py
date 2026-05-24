"""GUI entry point."""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox

from ..config import Config
from .main_window import MainWindow

ROOT = Path.cwd()


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("TTS Asset Manager")

    try:
        config = Config.load(ROOT / "config.json")
    except (FileNotFoundError, ValueError) as exc:
        QMessageBox.critical(None, "Configuration Error", str(exc))
        sys.exit(1)

    window = MainWindow(config, ROOT)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
