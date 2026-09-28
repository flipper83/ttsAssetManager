from pathlib import Path

from tests.conftest import make_png
from tts_manager.classifier import classify_assets
from tts_manager.progress import EventKind


def test_classifies_token(input_dir: Path) -> None:
    col = classify_assets(input_dir)
    assert "gem" in col.tokens
    assert col.tokens["gem"].front_path.name == "to_gem.png"


def test_classifies_card_front_and_back(input_dir: Path) -> None:
    col = classify_assets(input_dir)
    assert "hero" in col.cards
    assert col.cards["hero"].front_path.name == "c_hero_a.png"
    assert col.cards["hero"].back_path.name == "c_hero_b.png"


def test_classifies_tile_front_and_back(input_dir: Path) -> None:
    col = classify_assets(input_dir)
    assert "forest" in col.tiles
    assert col.tiles["forest"].front_path.name == "t_forest_a.png"
    assert col.tiles["forest"].back_path.name == "t_forest_b.png"


def test_classifies_deck_cards_sorted(input_dir: Path) -> None:
    col = classify_assets(input_dir)
    assert "spells" in col.decks
    deck = col.decks["spells"]
    card_names = [c.card_name for c in deck.cards]
    assert card_names == sorted(card_names)
    assert "fireball" in card_names
    assert "icebolt" in card_names


def test_classifies_deck_back(input_dir: Path) -> None:
    col = classify_assets(input_dir)
    assert col.decks["spells"].back_path is not None
    assert col.decks["spells"].back_path.name == "d_spells_back.png"


def test_warns_on_unrecognized_file(tmp_path: Path) -> None:
    d = tmp_path / "input"
    d.mkdir()
    (d / "unknown_file.png").write_bytes(b"")

    warnings = []
    classify_assets(d, on_progress=lambda e: warnings.append(e) if e.kind == EventKind.WARNING else None)
    assert any("unknown" in w.message.lower() or "unrecognized" in w.message.lower() for w in warnings)


def test_ignores_dotfiles(tmp_path: Path) -> None:
    d = tmp_path / "input"
    d.mkdir()
    (d / ".DS_Store").write_bytes(b"")

    col = classify_assets(d)
    assert not col.tokens and not col.cards and not col.tiles and not col.decks


def test_deck_cards_have_no_unique_back_by_default(input_dir: Path) -> None:
    col = classify_assets(input_dir)
    assert all(c.back_path is None for c in col.decks["spells"].cards)


def test_classifies_deck_card_unique_back(tmp_path: Path) -> None:
    d = tmp_path / "input"
    d.mkdir()
    make_png(d, "d_heroes_knight.png")
    make_png(d, "d_heroes_rogue.png")
    make_png(d, "db_heroes_knight.png")

    col = classify_assets(d)
    cards = {c.card_name: c for c in col.decks["heroes"].cards}
    assert cards["knight"].back_path.name == "db_heroes_knight.png"
    assert cards["rogue"].back_path is None


def test_deck_card_unique_back_supports_underscores(tmp_path: Path) -> None:
    d = tmp_path / "input"
    d.mkdir()
    make_png(d, "d_heroes_dark_knight.png")
    make_png(d, "db_heroes_dark_knight.png")

    col = classify_assets(d)
    card = col.decks["heroes"].cards[0]
    assert card.card_name == "dark_knight"
    assert card.back_path.name == "db_heroes_dark_knight.png"


def test_warns_on_deck_back_without_matching_card(tmp_path: Path) -> None:
    d = tmp_path / "input"
    d.mkdir()
    make_png(d, "d_heroes_knight.png")
    make_png(d, "db_heroes_wizard.png")

    warnings = []
    col = classify_assets(d, on_progress=lambda e: warnings.append(e) if e.kind == EventKind.WARNING else None)
    assert col.decks["heroes"].cards[0].back_path is None
    assert any("db_heroes_wizard.png" in w.message for w in warnings)
