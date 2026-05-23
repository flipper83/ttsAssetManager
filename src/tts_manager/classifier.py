from pathlib import Path

from .models import AssetCollection, CardAsset, DeckAsset, DeckCard, TileAsset, TokenAsset
from .progress import EventKind, ProgressCallback, ProgressEvent, noop

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def classify_assets(
    input_dir: Path,
    on_progress: ProgressCallback = noop,
) -> AssetCollection:
    """Parse filenames in input_dir and return a classified AssetCollection.

    Naming conventions:
      d_<deck>_<card>  — deck card (back if card == "back")
      c_<name>_a/b    — standalone card front/back
      t_<name>_a/b    — tile front/back
      to_<name>        — token (front only)
    """
    collection = AssetCollection()

    files = sorted(
        p for p in input_dir.iterdir()
        if not p.name.startswith(".")
        and p.is_file()
        and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    for path in files:
        parts = path.stem.split("_")
        if len(parts) < 2:
            on_progress(ProgressEvent(EventKind.WARNING, f"Skipping unrecognized file: {path.name}"))
            continue

        prefix = parts[0]

        if prefix == "to":
            _parse_token(parts, path, collection, on_progress)
        elif prefix == "d":
            _parse_deck_card(parts, path, collection, on_progress)
        elif prefix == "c":
            _parse_card(parts, path, collection, on_progress)
        elif prefix == "t":
            _parse_tile(parts, path, collection, on_progress)
        else:
            on_progress(ProgressEvent(EventKind.WARNING, f"Skipping unknown prefix '{prefix}': {path.name}"))

    for deck in collection.decks.values():
        deck.cards.sort(key=lambda c: c.card_name)

    return collection


def _parse_token(parts: list[str], path: Path, col: AssetCollection, cb: ProgressCallback) -> None:
    name = "_".join(parts[1:])
    col.tokens[name] = TokenAsset(name=name, front_path=path)


def _parse_deck_card(parts: list[str], path: Path, col: AssetCollection, cb: ProgressCallback) -> None:
    if len(parts) < 3:
        cb(ProgressEvent(EventKind.WARNING, f"Malformed deck filename: {path.name}"))
        return
    deck_name = parts[1]
    card_name = "_".join(parts[2:])
    if deck_name not in col.decks:
        col.decks[deck_name] = DeckAsset(name=deck_name)
    if card_name == "back":
        col.decks[deck_name].back_path = path
    else:
        col.decks[deck_name].cards.append(DeckCard(deck_name=deck_name, card_name=card_name, path=path))


def _parse_card(parts: list[str], path: Path, col: AssetCollection, cb: ProgressCallback) -> None:
    if len(parts) < 3:
        cb(ProgressEvent(EventKind.WARNING, f"Malformed card filename: {path.name}"))
        return
    side = parts[-1]
    name = "_".join(parts[1:-1])
    if name not in col.cards:
        col.cards[name] = CardAsset(name=name, front_path=path)
    if side == "a":
        col.cards[name].front_path = path
    elif side == "b":
        col.cards[name].back_path = path


def _parse_tile(parts: list[str], path: Path, col: AssetCollection, cb: ProgressCallback) -> None:
    if len(parts) < 3:
        cb(ProgressEvent(EventKind.WARNING, f"Malformed tile filename: {path.name}"))
        return
    side = parts[-1]
    name = "_".join(parts[1:-1])
    if name not in col.tiles:
        col.tiles[name] = TileAsset(name=name, front_path=path)
    if side == "a":
        col.tiles[name].front_path = path
    elif side == "b":
        col.tiles[name].back_path = path
