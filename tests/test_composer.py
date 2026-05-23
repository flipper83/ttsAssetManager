from pathlib import Path

import pytest
from PIL import Image

from tts_manager.composer import compose_deck_sheet, sheet_dims
from tts_manager.models import DeckAsset, DeckCard


def make_card(directory: Path, name: str, size: tuple[int, int] = (10, 15)) -> Path:
    path = directory / name
    Image.new("RGBA", size, (255, 0, 0, 255)).save(path)
    return path


def test_sheet_dims_single_card() -> None:
    assert sheet_dims(1) == (1, 1)


def test_sheet_dims_fits_in_one_row() -> None:
    assert sheet_dims(5) == (5, 1)


def test_sheet_dims_max_10_cols() -> None:
    cols, rows = sheet_dims(15)
    assert cols == 10
    assert rows == 2


def test_compose_single_card(tmp_path: Path) -> None:
    card_path = make_card(tmp_path, "d_test_card1.png", size=(20, 30))
    deck = DeckAsset(name="test", cards=[DeckCard("test", "card1", card_path)])
    sheet_path, cols, rows = compose_deck_sheet(deck, tmp_path / "processed")
    assert sheet_path.exists()
    assert cols == 1 and rows == 1
    img = Image.open(sheet_path)
    assert img.size == (20, 30)


def test_compose_multiple_cards_layout(tmp_path: Path) -> None:
    cards = []
    for i in range(3):
        p = make_card(tmp_path, f"d_test_c{i}.png", size=(10, 10))
        cards.append(DeckCard("test", f"c{i}", p))
    deck = DeckAsset(name="test", cards=cards)
    sheet_path, cols, rows = compose_deck_sheet(deck, tmp_path / "processed")
    assert cols == 3 and rows == 1
    img = Image.open(sheet_path)
    assert img.size == (30, 10)


def test_compose_raises_on_empty_deck(tmp_path: Path) -> None:
    deck = DeckAsset(name="empty", cards=[])
    with pytest.raises(ValueError, match="no cards"):
        compose_deck_sheet(deck, tmp_path)
