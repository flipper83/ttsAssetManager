import math
from pathlib import Path

from PIL import Image

from .models import DeckAsset
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

    output_dir.mkdir(parents=True, exist_ok=True)

    reference = Image.open(deck.cards[0].path)
    card_w, card_h = reference.size
    reference.close()

    n = len(deck.cards)
    num_cols = min(10, n)
    num_rows = math.ceil(n / num_cols)

    sheet = Image.new("RGBA", (card_w * num_cols, card_h * num_rows), (0, 0, 0, 0))

    for i, card in enumerate(deck.cards):
        img = Image.open(card.path).convert("RGBA")
        if img.size != (card_w, card_h):
            on_progress(ProgressEvent(
                EventKind.WARNING,
                f"Card '{card.card_name}' is {img.size}, expected {(card_w, card_h)} — resizing",
            ))
            img = img.resize((card_w, card_h), Image.LANCZOS)
        sheet.paste(img, (i % num_cols * card_w, i // num_cols * card_h))
        img.close()

    sheet_path = output_dir / f"deck_{deck.name}_sheet.png"
    sheet.save(sheet_path, "PNG")
    sheet.close()

    on_progress(ProgressEvent(EventKind.COMPOSE, f"Composed {n}-card sheet: {sheet_path.name}"))
    return sheet_path, num_cols, num_rows


def sheet_dims(n: int) -> tuple[int, int]:
    """Return (num_cols, num_rows) for a deck of n cards."""
    num_cols = min(10, n)
    return num_cols, math.ceil(n / num_cols)
