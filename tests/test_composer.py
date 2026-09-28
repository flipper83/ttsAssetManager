from pathlib import Path

import pytest
from PIL import Image

from tts_manager.composer import compose_deck_back_sheet, compose_deck_sheet, sheet_dims
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


def make_colored(directory: Path, name: str, color: tuple, size: tuple[int, int] = (10, 10)) -> Path:
    path = directory / name
    Image.new("RGBA", size, color).save(path)
    return path


def test_compose_back_sheet_matches_front_grid(tmp_path: Path) -> None:
    red, blue, gray = (255, 0, 0, 255), (0, 0, 255, 255), (50, 50, 50, 255)
    cards = [
        DeckCard("test", "a", make_card(tmp_path, "d_test_a.png", size=(10, 10)),
                 back_path=make_colored(tmp_path, "db_test_a.png", red)),
        DeckCard("test", "b", make_card(tmp_path, "d_test_b.png", size=(10, 10)),
                 back_path=make_colored(tmp_path, "db_test_b.png", blue)),
        DeckCard("test", "c", make_card(tmp_path, "d_test_c.png", size=(10, 10))),
    ]
    deck = DeckAsset(name="test", cards=cards, back_path=make_colored(tmp_path, "d_test_back.png", gray))

    back_path = compose_deck_back_sheet(deck, tmp_path / "processed")
    img = Image.open(back_path).convert("RGBA")
    assert img.size == (30, 10)
    assert img.getpixel((5, 5)) == red
    assert img.getpixel((15, 5)) == blue
    assert img.getpixel((25, 5)) == gray  # falls back to the deck's shared back


def test_compose_back_sheet_leaves_missing_backs_blank(tmp_path: Path) -> None:
    cards = [
        DeckCard("test", "a", make_card(tmp_path, "d_test_a.png", size=(10, 10)),
                 back_path=make_colored(tmp_path, "db_test_a.png", (255, 0, 0, 255))),
        DeckCard("test", "b", make_card(tmp_path, "d_test_b.png", size=(10, 10))),
    ]
    deck = DeckAsset(name="test", cards=cards)

    warnings = []
    back_path = compose_deck_back_sheet(deck, tmp_path / "processed", on_progress=warnings.append)
    img = Image.open(back_path).convert("RGBA")
    assert img.getpixel((15, 5))[3] == 0
    assert any("'b'" in w.message and "no back" in w.message for w in warnings)


def test_compose_back_sheet_resizes_to_front_size(tmp_path: Path) -> None:
    cards = [
        DeckCard("test", "a", make_card(tmp_path, "d_test_a.png", size=(10, 15)),
                 back_path=make_colored(tmp_path, "db_test_a.png", (255, 0, 0, 255), size=(20, 30))),
    ]
    back_path = compose_deck_back_sheet(DeckAsset(name="test", cards=cards), tmp_path / "processed")
    assert Image.open(back_path).size == (10, 15)
