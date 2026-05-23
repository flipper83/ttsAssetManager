import json
from pathlib import Path

from tts_manager.builder import build_card, build_deck, build_save, build_tile, build_token


def test_build_token() -> None:
    obj = build_token("gem", "https://example.com/gem.png")
    assert obj["Name"] == "Custom_Token"
    assert obj["CustomImage"]["ImageURL"] == "https://example.com/gem.png"
    assert obj["CustomImage"]["ImageSecondaryURL"] == ""
    assert obj["Nickname"] == "gem"
    assert len(obj["GUID"]) == 6


def test_build_tile_with_back() -> None:
    obj = build_tile("forest", "https://example.com/front.png", "https://example.com/back.png")
    assert obj["Name"] == "Custom_Tile"
    assert obj["CustomImage"]["ImageURL"] == "https://example.com/front.png"
    assert obj["CustomImage"]["ImageSecondaryURL"] == "https://example.com/back.png"


def test_build_tile_without_back() -> None:
    obj = build_tile("desert", "https://example.com/front.png")
    assert obj["CustomImage"]["ImageSecondaryURL"] == ""


def test_build_card_id() -> None:
    obj = build_card("hero", deck_key=3, front_url="https://example.com/f.png", back_url="https://example.com/b.png")
    assert obj["Name"] == "CardCustom"
    assert obj["CardID"] == 300
    assert "3" in obj["CustomDeck"]
    assert obj["CustomDeck"]["3"]["NumWidth"] == 1
    assert obj["CustomDeck"]["3"]["NumHeight"] == 1


def test_build_deck_structure() -> None:
    obj = build_deck("spells", deck_key=1, sheet_url="https://example.com/sheet.png",
                     back_url="https://example.com/back.png", num_width=2, num_height=1, num_cards=2)
    assert obj["Name"] == "Deck"
    assert obj["DeckIDs"] == [100, 101]
    assert len(obj["ContainedObjects"]) == 2
    assert obj["ContainedObjects"][0]["CardID"] == 100
    assert obj["ContainedObjects"][1]["CardID"] == 101
    assert obj["CustomDeck"]["1"]["NumWidth"] == 2
    assert obj["CustomDeck"]["1"]["NumHeight"] == 1


def test_build_save_preserves_hand_triggers(tmp_path: Path) -> None:
    skeleton = {
        "SaveName": "test",
        "ObjectStates": [
            {"Name": "HandTrigger", "GUID": "aaa"},
            {"Name": "Deck", "GUID": "bbb"},
        ],
    }
    skeleton_path = tmp_path / "skeleton.json"
    skeleton_path.write_text(json.dumps(skeleton), encoding="utf-8")

    new_obj = build_token("gem", "https://example.com/gem.png")
    save = build_save(skeleton_path, [new_obj])

    names = [o["Name"] for o in save["ObjectStates"]]
    assert "HandTrigger" in names
    assert "Deck" not in names
    assert "Custom_Token" in names


def test_build_save_all_objects_at_center(tmp_path: Path) -> None:
    skeleton = {"SaveName": "test", "ObjectStates": []}
    skeleton_path = tmp_path / "skeleton.json"
    skeleton_path.write_text(json.dumps(skeleton), encoding="utf-8")

    obj = build_token("gem", "https://example.com/gem.png")
    save = build_save(skeleton_path, [obj])

    t = save["ObjectStates"][0]["Transform"]
    assert t["posX"] == 0.0
    assert t["posZ"] == 0.0
