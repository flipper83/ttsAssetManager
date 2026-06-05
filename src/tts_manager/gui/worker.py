"""Background worker — runs AssetManager operations off the main thread."""

from PyQt6.QtCore import QThread, pyqtSignal

from ..manager import AssetManager
from ..progress import ProgressEvent


class AssetWorker(QThread):
    progress = pyqtSignal(object)   # emits ProgressEvent
    finished = pyqtSignal(bool, str)  # (success, message)

    def __init__(self, manager: AssetManager, incremental: bool = False, pull: bool = False) -> None:
        super().__init__()
        self._manager = manager
        self._incremental = incremental
        self._pull = pull

    def run(self) -> None:
        self._manager._on_progress = lambda e: self.progress.emit(e)
        try:
            if self._pull:
                self._manager.pull()
            elif self._incremental:
                self._manager.update()
            else:
                self._manager.upload()
            self.finished.emit(True, "Done")
        except Exception as exc:  # noqa: BLE001
            self.finished.emit(False, str(exc))
