"""CLI entry point — thin wrapper around AssetManager."""

import argparse
import sys
from pathlib import Path

from .config import Config
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


def _make_manager(config: Config, on_progress=_print_progress) -> AssetManager:
    return AssetManager(
        config=config,
        input_dir=ROOT / "input",
        skeleton_path=ROOT / "skeleton" / "TS_Save_138.json",
        output_dir=ROOT / "output",
        processed_dir=ROOT / "processed",
        state_file=ROOT / "processed" / "state.json",
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
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.add_parser("upload", help="Full upload of all assets (default)")
    sub.add_parser("update", help="Upload only changed or new assets")
    args = parser.parse_args()

    try:
        config = Config.load(Path(args.config))
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    manager = _make_manager(config)

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
