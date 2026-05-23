"""AssetManager — public API consumed by both CLI and GUI."""

import json
import shutil
from pathlib import Path

from .builder import build_card, build_deck, build_save, build_tile, build_token
from .classifier import classify_assets
from .composer import compose_deck_sheet, sheet_dims
from .config import Config
from .progress import EventKind, ProgressCallback, ProgressEvent, noop
from .state import StateManager
from .uploader import GitHubUploader


class AssetManager:
    """Orchestrates asset classification, upload, and TTS save generation.

    Designed to be consumed by both CLI and GUI. All progress is reported via
    the on_progress callback so the consumer controls how it's displayed.
    """

    def __init__(
        self,
        config: Config,
        input_dir: Path,
        skeleton_path: Path,
        output_dir: Path,
        processed_dir: Path,
        state_file: Path,
        on_progress: ProgressCallback = noop,
    ) -> None:
        self._config = config
        self._input_dir = input_dir
        self._skeleton_path = skeleton_path
        self._output_dir = output_dir
        self._processed_dir = processed_dir
        self._state_file = state_file
        self._on_progress = on_progress

    def upload(self) -> Path:
        """Full upload of all assets. Ignores existing state."""
        return self._run(incremental=False)

    def update(self) -> Path:
        """Incremental upload — only changed or new assets."""
        return self._run(incremental=True)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run(self, incremental: bool) -> Path:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._processed_dir.mkdir(parents=True, exist_ok=True)

        state = StateManager(self._state_file)
        if not incremental:
            state.clear()

        uploader = GitHubUploader(self._config, self._on_progress)
        collection = classify_assets(self._input_dir, self._on_progress)

        self._on_progress(ProgressEvent(
            EventKind.INFO,
            f"Assets — decks:{len(collection.decks)} cards:{len(collection.cards)} "
            f"tiles:{len(collection.tiles)} tokens:{len(collection.tokens)}",
            {"collection": {
                "decks": sorted(collection.decks),
                "cards": sorted(collection.cards),
                "tiles": sorted(collection.tiles),
                "tokens": sorted(collection.tokens),
            }},
        ))

        tts_objects: list[dict] = []
        deck_key = 1

        def _upload(local: Path, folder: str) -> str:
            if incremental and not state.changed(local):
                remote = state.remote_path(local)
                url = f"{self._config.base_url}/{remote}"
                self._on_progress(ProgressEvent(EventKind.SKIP, f"(unchanged) {url}", {"url": url}))
                return url
            old_remote = state.remote_path(local)
            versioned = StateManager.versioned_name(local)
            remote = f"{folder}/{versioned}"
            url = uploader.upload(local, remote)
            if old_remote and old_remote != remote:
                uploader.delete(old_remote)
            state.mark_file(local, remote)
            return url

        for name in sorted(collection.tokens):
            token = collection.tokens[name]
            self._on_progress(ProgressEvent(EventKind.INFO, f"Token '{name}'"))
            url = _upload(token.front_path, "tokens")
            tts_objects.append(build_token(name, url))

        for name in sorted(collection.tiles):
            tile = collection.tiles[name]
            self._on_progress(ProgressEvent(EventKind.INFO, f"Tile '{name}'"))
            front_url = _upload(tile.front_path, "tiles")
            back_url = _upload(tile.back_path, "tiles") if tile.back_path else ""
            tts_objects.append(build_tile(name, front_url, back_url))

        for name in sorted(collection.cards):
            card = collection.cards[name]
            if not card.front_path:
                self._on_progress(ProgressEvent(EventKind.WARNING, f"Card '{name}' has no front image, skipping"))
                continue
            self._on_progress(ProgressEvent(EventKind.INFO, f"Card '{name}'"))
            front_url = _upload(card.front_path, "cards")
            back_url = _upload(card.back_path, "cards") if card.back_path else ""
            tts_objects.append(build_card(name, deck_key, front_url, back_url))
            deck_key += 1

        for name in sorted(collection.decks):
            deck = collection.decks[name]
            if not deck.cards:
                self._on_progress(ProgressEvent(EventKind.WARNING, f"Deck '{name}' has no cards, skipping"))
                continue

            card_paths = [c.path for c in deck.cards]
            deck_is_changed = not incremental or state.deck_changed(card_paths)

            self._on_progress(ProgressEvent(
                EventKind.INFO,
                f"Deck '{name}' ({len(deck.cards)} cards){'...' if deck_is_changed else ' (unchanged)'}",
            ))

            if deck_is_changed:
                sheet_path, cols, rows = compose_deck_sheet(deck, self._processed_dir, self._on_progress)
                old_remote = state.deck_info(name) and state.deck_info(name).get("remote")  # type: ignore[union-attr]
                versioned = StateManager.versioned_name(sheet_path)
                remote = f"decks/{versioned}"
                sheet_url = uploader.upload(sheet_path, remote)
                if old_remote and old_remote != remote:
                    uploader.delete(old_remote)
                state.mark_deck(name, card_paths, remote, cols, rows)
            else:
                info = state.deck_info(name)
                sheet_url = f"{self._config.base_url}/{info['remote']}"
                cols, rows = info["cols"], info["rows"]
                self._on_progress(ProgressEvent(EventKind.SKIP, f"(unchanged) {sheet_url}", {"url": sheet_url}))

            back_url = _upload(deck.back_path, "decks") if deck.back_path else ""
            tts_objects.append(build_deck(name, deck_key, sheet_url, back_url, cols, rows, len(deck.cards)))
            deck_key += 1

        save_data = build_save(self._skeleton_path, tts_objects)
        output_path = self._output_dir / "TTS_Save.json"
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)

        state.save()

        self._on_progress(ProgressEvent(EventKind.INFO, f"Save written: {output_path}"))

        tts_dir = self._config.tts_saves_dir
        if tts_dir and tts_dir.is_dir():
            dest = tts_dir / f"{self._config.save_name}.json"
            shutil.copy2(output_path, dest)
            self._on_progress(ProgressEvent(EventKind.INFO, f"Copied to TTS: {dest}", {"dest": str(dest)}))
        elif tts_dir:
            self._on_progress(ProgressEvent(EventKind.WARNING, f"TTS saves folder not found: {tts_dir}"))

        return output_path
