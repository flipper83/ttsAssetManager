import math
from pathlib import Path

from PIL import Image

from .models import DeckAsset
from .optimizer import MAX_SHEET_DIMENSION, resize_to_fit
from .progress import EventKind, ProgressCallback, ProgressEvent, noop


def compose_deck_sheet(
    deck: DeckAsset,
    output_dir: Path,
    on_progress: ProgressCallback = noop,
) -> tuple[Path, int, int]:
    """Compose card images into a TTS sprite sheet.

    Cards are arranged left-to-right, top-to-bottom, sorted alphabetically.
    Returns (sheet_path, num_cols, num_rows).
    """
    if not deck.cards:
        raise ValueError(f"Deck '{deck.name}' has no cards")

    cells = [(card.card_name, card.path) for card in deck.cards]
    sheet_path = output_dir / f"deck_{deck.name}_sheet.png"
    num_cols, num_rows = _compose_sheet(cells, _card_size(deck), sheet_path, on_progress)

    on_progress(ProgressEvent(EventKind.COMPOSE, f"Composed {len(cells)}-card sheet: {sheet_path.name}"))
    return sheet_path, num_cols, num_rows


def compose_deck_back_sheet(
    deck: DeckAsset,
    output_dir: Path,
    on_progress: ProgressCallback = noop,
) -> Path:
    """Compose per-card back images into a sprite sheet matching the front sheet grid.

    Each cell uses the card's own back, falling back to the deck's shared back,
    or a blank cell if neither exists. Returns the sheet path.
    """
    if not deck.cards:
        raise ValueError(f"Deck '{deck.name}' has no cards")

    cells: list[tuple[str, Path | None]] = []
    for card in deck.cards:
        back = card.back_path or deck.back_path
        if back is None:
            on_progress(ProgressEvent(
                EventKind.WARNING,
                f"Card '{card.card_name}' in deck '{deck.name}' has no back — leaving it blank",
            ))
        cells.append((card.card_name, back))

    sheet_path = output_dir / f"deck_{deck.name}_back_sheet.png"
    _compose_sheet(cells, _card_size(deck), sheet_path, on_progress)

    on_progress(ProgressEvent(EventKind.COMPOSE, f"Composed {len(cells)}-card back sheet: {sheet_path.name}"))
    return sheet_path


def _card_size(deck: DeckAsset) -> tuple[int, int]:
    """Cell size for the deck, taken from the first card front."""
    with Image.open(deck.cards[0].path) as reference:
        return reference.size


def _compose_sheet(
    cells: list[tuple[str, Path | None]],
    card_size: tuple[int, int],
    sheet_path: Path,
    on_progress: ProgressCallback,
) -> tuple[int, int]:
    """Paste (label, image) cells into a grid sheet and save it. None cells stay transparent."""
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    card_w, card_h = card_size
    num_cols, num_rows = sheet_dims(len(cells))

    sheet = Image.new("RGBA", (card_w * num_cols, card_h * num_rows), (0, 0, 0, 0))

    for i, (label, path) in enumerate(cells):
        if path is None:
            continue
        img = Image.open(path).convert("RGBA")
        if img.size != (card_w, card_h):
            on_progress(ProgressEvent(
                EventKind.WARNING,
                f"Card '{label}' is {img.size}, expected {(card_w, card_h)} — resizing",
            ))
            img = img.resize((card_w, card_h), Image.LANCZOS)
        sheet.paste(img, (i % num_cols * card_w, i // num_cols * card_h))
        img.close()

    sheet = resize_to_fit(sheet, MAX_SHEET_DIMENSION)
    sheet.save(sheet_path, "PNG", optimize=True)
    sheet.close()
    return num_cols, num_rows


def sheet_dims(n: int) -> tuple[int, int]:
    """Return (num_cols, num_rows) for a deck of n cards."""
    num_cols = min(10, n)
    return num_cols, math.ceil(n / num_cols)
