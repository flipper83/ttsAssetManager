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

    # ------------------------------------------------------------------
    # Remote sync helpers
    # ------------------------------------------------------------------

    def export_remote(self, assets_root: Path) -> dict:
        """Export state with paths relative to assets_root for remote sync."""
        files = {}
        for abs_path, entry in self._data.get("files", {}).items():
            try:
                rel = str(Path(abs_path).relative_to(assets_root))
            except ValueError:
                continue  # skip files outside assets_root (e.g. the save JSON)
            files[rel] = entry
        return {"files": files, "save_hash": self._data.get("uploaded_save_hash")}

    def merge_remote(self, data: dict, assets_root: Path) -> None:
        """Merge remote state into local, only for files whose local hash matches."""
        for rel_path, entry in data.get("files", {}).items():
            abs_path = assets_root / rel_path
            if abs_path.exists() and self._hash(abs_path) == entry.get("hash"):
                self._data.setdefault("files", {})[str(abs_path)] = entry

    def uploaded_save_hash(self) -> str | None:
        return self._data.get("uploaded_save_hash")

    def set_uploaded_save_hash(self, h: str | None) -> None:
        if h is not None:
            self._data["uploaded_save_hash"] = h
        else:
            self._data.pop("uploaded_save_hash", None)

    def _load(self) -> dict:
        if self._state_file.exists():
            with self._state_file.open(encoding="utf-8") as f:
                return json.load(f)
        return {"files": {}, "decks": {}}
