from pathlib import Path

from tts_manager.state import StateManager


def test_new_file_is_considered_changed(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state = StateManager(state_file)
    f = tmp_path / "img.png"
    f.write_bytes(b"hello")
    assert state.changed(f) is True


def test_marked_file_is_unchanged(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state = StateManager(state_file)
    f = tmp_path / "img.png"
    f.write_bytes(b"hello")
    state.mark_file(f, "tokens/img_abc.png")
    assert state.changed(f) is False


def test_modified_file_is_changed(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state = StateManager(state_file)
    f = tmp_path / "img.png"
    f.write_bytes(b"hello")
    state.mark_file(f, "tokens/img_abc.png")
    f.write_bytes(b"world")
    assert state.changed(f) is True


def test_remote_path_returned_after_mark(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state = StateManager(state_file)
    f = tmp_path / "img.png"
    f.write_bytes(b"hello")
    state.mark_file(f, "tokens/img_abc123.png")
    assert state.remote_path(f) == "tokens/img_abc123.png"


def test_state_persists_across_instances(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    f = tmp_path / "img.png"
    f.write_bytes(b"hello")

    s1 = StateManager(state_file)
    s1.mark_file(f, "tokens/img_abc.png")
    s1.save()

    s2 = StateManager(state_file)
    assert s2.changed(f) is False
    assert s2.remote_path(f) == "tokens/img_abc.png"


def test_clear_resets_state(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    f = tmp_path / "img.png"
    f.write_bytes(b"hello")

    state = StateManager(state_file)
    state.mark_file(f, "tokens/img_abc.png")
    state.clear()
    assert state.changed(f) is True


def test_versioned_name_includes_hash(tmp_path: Path) -> None:
    f = tmp_path / "my_token.png"
    f.write_bytes(b"content_a")
    name_a = StateManager.versioned_name(f)

    f.write_bytes(b"content_b")
    name_b = StateManager.versioned_name(f)

    assert name_a != name_b
    assert name_a.startswith("my_token_")
    assert name_a.endswith(".png")


def test_deck_state_roundtrip(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state = StateManager(state_file)
    cards = []
    for i in range(3):
        f = tmp_path / f"card_{i}.png"
        f.write_bytes(f"card{i}".encode())
        cards.append(f)

    state.mark_deck("spells", cards, "decks/sheet_abc.png", cols=3, rows=1)
    assert state.deck_info("spells") == {"remote": "decks/sheet_abc.png", "cols": 3, "rows": 1}
    assert state.deck_changed(cards) is False


def test_deck_state_records_unique_back_sheet(tmp_path: Path) -> None:
    front = tmp_path / "d_heroes_knight.png"
    front.write_bytes(b"front")
    back = tmp_path / "db_heroes_knight.png"
    back.write_bytes(b"back")

    state = StateManager(tmp_path / "state.json")
    state.mark_deck("heroes", [front], "g/decks/sheet.png", 1, 1, [back], "g/decks/back_sheet.png")

    assert state.deck_info("heroes")["back_remote"] == "g/decks/back_sheet.png"
    assert state.remote_path(back) == "g/decks/back_sheet.png"
    assert state.deck_changed([front, back]) is False
    back.write_bytes(b"new back")
    assert state.deck_changed([front, back]) is True


def test_deck_state_without_unique_back_has_no_back_remote(tmp_path: Path) -> None:
    front = tmp_path / "d_spells_fireball.png"
    front.write_bytes(b"front")

    state = StateManager(tmp_path / "state.json")
    state.mark_deck("spells", [front], "g/decks/sheet.png", 1, 1)
    assert "back_remote" not in state.deck_info("spells")
