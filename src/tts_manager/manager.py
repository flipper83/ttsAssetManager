"""AssetManager — public API consumed by both CLI and GUI."""

import json
import shutil
from pathlib import Path

from .builder import build_card, build_deck, build_save, build_tile, build_token, merge_into_save
from .classifier import classify_assets
from .composer import compose_deck_back_sheet, compose_deck_sheet, sheet_dims
from .config import Config, GameConfig
from .optimizer import optimize_image
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
        game: GameConfig,
        skeleton_path: Path,
        output_dir: Path,
        processed_dir: Path,
        state_file: Path,
        on_progress: ProgressCallback = noop,
    ) -> None:
        self._config = game.resolved_config(config)
        self._game = game
        self._input_dir = game.assets_path()
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

    def pull(self) -> Path:
        """Download the latest TTS save from remote and sync state."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._processed_dir.mkdir(parents=True, exist_ok=True)

        uploader = GitHubUploader(self._config, self._on_progress)

        save_remote = f"saves/{self._game.github_subfolder}.json"
        save_bytes = uploader.fetch_bytes(save_remote)
        if save_bytes is None:
            raise RuntimeError(f"No remote save found at {save_remote}. Upload first.")

        output_path = self._output_dir / f"{self._game.name}.json"
        output_path.write_bytes(save_bytes)
        self._on_progress(ProgressEvent(EventKind.INFO, f"Save downloaded: {output_path}"))

        tts_dir = self._config.tts_saves_dir
        if tts_dir and tts_dir.is_dir():
            dest = tts_dir / f"{self._game.name}.json"
            shutil.copy2(output_path, dest)
            self._on_progress(ProgressEvent(EventKind.INFO, f"Copied to TTS: {dest}", {"dest": str(dest)}))
        elif tts_dir:
            self._on_progress(ProgressEvent(EventKind.WARNING, f"TTS saves folder not found: {tts_dir}"))

        state = StateManager(self._state_file)
        remote_state = uploader.fetch_json(f"saves/{self._game.github_subfolder}.state.json")
        if remote_state:
            state.merge_remote(remote_state, self._input_dir)
            state.set_uploaded_save_hash(remote_state.get("save_hash"))
            state.mark_file(output_path, save_remote)
            state.save()
            self._on_progress(ProgressEvent(EventKind.INFO, "State synced from remote"))

        return output_path

    def _existing_save(self) -> dict | None:
        """Load the current TTS save for this game, if one exists on disk."""
        tts_dir = self._config.tts_saves_dir
        if not tts_dir:
            return None
        existing_path = tts_dir / f"{self._game.name}.json"
        if not existing_path.exists():
            return None
        try:
            with existing_path.open(encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def delete_game(self, delete_remote: bool) -> None:
        """Remove local processed files and optionally all remote assets."""
        if delete_remote:
            uploader = GitHubUploader(self._config, self._on_progress)
            paths = (
                uploader.list_remote_paths(f"{self._game.github_subfolder}/")
                + uploader.list_remote_paths(f"saves/{self._game.github_subfolder}")
            )
            if paths:
                uploader.delete_many(paths)
            else:
                self._on_progress(ProgressEvent(EventKind.INFO, "No remote files found"))

        if self._processed_dir.exists():
            shutil.rmtree(self._processed_dir)
        output_path = self._output_dir / f"{self._game.name}.json"
        if output_path.exists():
            output_path.unlink()
        tts_dir = self._config.tts_saves_dir
        if tts_dir:
            tts_save = tts_dir / f"{self._game.name}.json"
            if tts_save.exists():
                tts_save.unlink()
                self._on_progress(ProgressEvent(EventKind.DELETE, f"Deleted TTS save: {tts_save}"))
        self._on_progress(ProgressEvent(EventKind.INFO, "Local files cleaned up"))

    @staticmethod
    def remote_save_hash(config: Config, game: GameConfig) -> str | None:
        """Fetch the remote save_hash without full uploader initialization."""
        data = GitHubUploader.fetch_remote_state(
            game.resolved_config(config), f"saves/{game.github_subfolder}.state.json"
        )
        return data.get("save_hash") if data else None

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

        prefix = self._game.github_subfolder

        def _upload(local: Path, folder: str, force: bool = False) -> str:
            if incremental and not force and not state.changed(local):
                remote = state.remote_path(local)
                url = f"{self._config.base_url}/{remote}"
                self._on_progress(ProgressEvent(EventKind.SKIP, f"(unchanged) {url}", {"url": url}))
                return url
            old_remote = state.remote_path(local)
            dest = self._processed_dir / local.name
            optimized = optimize_image(local, dest, on_progress=self._on_progress)
            versioned = StateManager.versioned_name(optimized)
            remote = f"{prefix}/{folder}/{versioned}"
            url = uploader.upload(optimized, remote)
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
            unique_back = any(c.back_path for c in deck.cards)
            back_paths = [c.back_path for c in deck.cards if c.back_path]
            if unique_back and deck.back_path:
                back_paths.append(deck.back_path)

            info = state.deck_info(name)
            was_unique = bool(info and info.get("back_remote"))
            mode_switched = info is not None and unique_back != was_unique
            deck_is_changed = (
                not incremental
                or info is None
                or mode_switched
                or state.deck_changed(card_paths + back_paths)
            )

            self._on_progress(ProgressEvent(
                EventKind.INFO,
                f"Deck '{name}' ({len(deck.cards)} cards){'...' if deck_is_changed else ' (unchanged)'}",
            ))

            back_url = ""
            if deck_is_changed:
                sheet_path, cols, rows = compose_deck_sheet(deck, self._processed_dir, self._on_progress)
                old_remote = info and info.get("remote")
                versioned = StateManager.versioned_name(sheet_path)
                remote = f"{prefix}/decks/{versioned}"
                sheet_url = uploader.upload(sheet_path, remote)
                if old_remote and old_remote != remote:
                    uploader.delete(old_remote)

                back_remote = None
                if unique_back:
                    # The shared back (if any) is baked into the back sheet; drop its standalone copy.
                    old_back_remote = info and info.get("back_remote")
                    if not old_back_remote and deck.back_path:
                        old_back_remote = state.remote_path(deck.back_path)
                    back_sheet_path = compose_deck_back_sheet(deck, self._processed_dir, self._on_progress)
                    back_remote = f"{prefix}/decks/{StateManager.versioned_name(back_sheet_path)}"
                    back_url = uploader.upload(back_sheet_path, back_remote)
                    if old_back_remote and old_back_remote != back_remote:
                        uploader.delete(old_back_remote)
                elif was_unique and not deck.back_path:
                    # With a shared back, the forced re-upload below replaces (and deletes) the back sheet.
                    uploader.delete(info["back_remote"])  # type: ignore[index]
                state.mark_deck(name, card_paths, remote, cols, rows, back_paths, back_remote)
            else:
                sheet_url = f"{self._config.base_url}/{info['remote']}"  # type: ignore[index]
                cols, rows = info["cols"], info["rows"]  # type: ignore[index]
                self._on_progress(ProgressEvent(EventKind.SKIP, f"(unchanged) {sheet_url}", {"url": sheet_url}))
                if unique_back:
                    back_url = f"{self._config.base_url}/{info['back_remote']}"  # type: ignore[index]

            if not unique_back and deck.back_path:
                # After leaving unique-back mode the shared back's state points at the deleted back sheet.
                back_url = _upload(deck.back_path, "decks", force=mode_switched)
            tts_objects.append(build_deck(
                name, deck_key, sheet_url, back_url, cols, rows, len(deck.cards), unique_back=unique_back,
            ))
            deck_key += 1

        existing_save = self._existing_save()
        if existing_save is not None:
            save_data = merge_into_save(existing_save, tts_objects)
            self._on_progress(ProgressEvent(
                EventKind.INFO,
                "Merged into existing save — hand-placed objects and layout preserved",
            ))
        else:
            save_data = build_save(self._skeleton_path, tts_objects)
        save_data["SaveName"] = self._game.name
        output_path = self._output_dir / f"{self._game.name}.json"
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)

        self._on_progress(ProgressEvent(EventKind.INFO, f"Save written: {output_path}"))

        save_remote = f"saves/{self._game.github_subfolder}.json"
        if state.changed(output_path):
            save_url = uploader.upload(output_path, save_remote)
            state.mark_file(output_path, save_remote)
            state.set_uploaded_save_hash(StateManager._hash(output_path))
            self._on_progress(ProgressEvent(EventKind.INFO, f"Save synced → {save_url}", {"url": save_url}))
        else:
            self._on_progress(ProgressEvent(EventKind.SKIP, f"(unchanged) {save_remote}"))

        uploader.upload_json(state.export_remote(self._input_dir), f"saves/{self._game.github_subfolder}.state.json")
        state.save()

        tts_dir = self._config.tts_saves_dir
        if tts_dir and tts_dir.is_dir():
            dest = tts_dir / f"{self._game.name}.json"
            shutil.copy2(output_path, dest)
            self._on_progress(ProgressEvent(EventKind.INFO, f"Copied to TTS: {dest}", {"dest": str(dest)}))
        elif tts_dir:
            self._on_progress(ProgressEvent(EventKind.WARNING, f"TTS saves folder not found: {tts_dir}"))

        return output_path
