"""GUI entry point."""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox

from ..config import Config
from .main_window import MainWindow
from .settings_dialog import SettingsDialog

ROOT = Path.cwd()
CONFIG_PATH = ROOT / "config.json"


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("TTS Asset Manager")

    # Load or bootstrap config
    try:
        config = Config.load(CONFIG_PATH)
    except (FileNotFoundError, ValueError):
        # First run or bad config — open Settings before the main window
        config = Config.empty()
        dlg = SettingsDialog(config, CONFIG_PATH)
        if dlg.exec() == 0 or not config.is_valid():
            QMessageBox.warning(
                None,
                "Setup required",
                "GitHub credentials are required to use TTS Asset Manager.\n"
                "You can open Settings later from the status bar.",
            )

    window = MainWindow(config, CONFIG_PATH, ROOT)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
