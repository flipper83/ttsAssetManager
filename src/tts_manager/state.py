import hashlib
import json
from pathlib import Path


class StateManager:
    """Tracks uploaded file hashes and remote paths to enable incremental uploads."""

    def __init__(self, state_file: Path) -> None:
        self._state_file = state_file
        self._data: dict = self._load()

    # ------------------------------------------------------------------
    # File-level state
    # ------------------------------------------------------------------

    def changed(self, path: Path) -> bool:
        entry = self._data.get("files", {}).get(str(path))
        if not entry:
            return True
        return entry.get("hash") != self._hash(path)

    def remote_path(self, path: Path) -> str | None:
        entry = self._data.get("files", {}).get(str(path))
        return entry.get("remote") if entry else None

    def mark_file(self, path: Path, remote: str) -> None:
        self._data.setdefault("files", {})[str(path)] = {
            "hash": self._hash(path),
            "remote": remote,
        }

    # ------------------------------------------------------------------
    # Deck-level state (sheet dimensions + remote path)
    # ------------------------------------------------------------------

    def deck_changed(self, card_paths: list[Path]) -> bool:
        return any(self.changed(p) for p in card_paths)

    def deck_info(self, deck_name: str) -> dict | None:
        return self._data.get("decks", {}).get(deck_name)

    def mark_deck(self, deck_name: str, card_paths: list[Path], remote: str, cols: int, rows: int) -> None:
        for p in card_paths:
            self._data.setdefault("files", {})[str(p)] = {
                "hash": self._hash(p),
                "remote": remote,
            }
        self._data.setdefault("decks", {})[deck_name] = {
            "remote": remote,
            "cols": cols,
            "rows": rows,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        with self._state_file.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def clear(self) -> None:
        self._data = {"files": {}, "decks": {}}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def versioned_name(path: Path) -> str:
        """Return filename with 8-char content hash: image_ab12cd34.png"""
        h = StateManager._hash(path)[:8]
        return f"{path.stem}_{h}{path.suffix}"

    @staticmethod
    def _hash(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _load(self) -> dict:
        if self._state_file.exists():
            with self._state_file.open(encoding="utf-8") as f:
                return json.load(f)
        return {"files": {}, "decks": {}}
