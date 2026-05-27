"""CLI entry point — thin wrapper around AssetManager."""

import argparse
import sys
from pathlib import Path

from .config import Config, GameConfig
from .manager import AssetManager
from .progress import EventKind, ProgressEvent

ROOT = Path.cwd()


def _print_progress(event: ProgressEvent) -> None:
    prefix = {
        EventKind.WARNING: "WARNING: ",
        EventKind.UPLOAD: "  ",
        EventKind.SKIP: "  ",
        EventKind.DELETE: "  ",
        EventKind.COMPOSE: "  ",
        EventKind.INFO: "",
    }.get(event.kind, "")
    print(f"{prefix}{event.message}")


def _make_manager(config: Config, game: GameConfig, on_progress=_print_progress) -> AssetManager:
    processed_dir = ROOT / "processed" / game.github_subfolder
    return AssetManager(
        config=config,
        game=game,
        skeleton_path=ROOT / "skeleton" / "TS_Save_138.json",
        output_dir=ROOT / "output",
        processed_dir=processed_dir,
        state_file=processed_dir / "state.json",
        on_progress=on_progress,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tts-manager",
        description="TTS Asset Manager — prepare Tabletop Simulator saves without opening TTS",
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config file (default: config.json)",
    )
    parser.add_argument(
        "--game",
        default=None,
        help="Game name to process (default: first game in config)",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.add_parser("upload", help="Full upload of all assets (default)")
    sub.add_parser("update", help="Upload only changed or new assets")
    args = parser.parse_args()

    try:
        config = Config.load(Path(args.config))
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if not config.games:
        print("ERROR: No games configured. Use the GUI to create a game first.", file=sys.stderr)
        sys.exit(1)

    if args.game:
        matches = [g for g in config.games if g.name == args.game]
        if not matches:
            names = ", ".join(g.name for g in config.games)
            print(f"ERROR: Game '{args.game}' not found. Available: {names}", file=sys.stderr)
            sys.exit(1)
        game = matches[0]
    else:
        game = config.games[0]

    manager = _make_manager(config, game)

    try:
        if args.command == "update":
            manager.update()
        else:
            manager.upload()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
