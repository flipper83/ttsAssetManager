import json
from pathlib import Path

from tts_manager.builder import (
    build_card,
    build_deck,
    build_save,
    build_tile,
    build_token,
    merge_into_save,
)


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


def test_build_deck_shared_back_by_default() -> None:
    obj = build_deck("spells", 1, "https://example.com/sheet.png", "https://example.com/back.png", 2, 1, 2)
    assert obj["CustomDeck"]["1"]["UniqueBack"] is False


def test_build_deck_unique_back() -> None:
    obj = build_deck("heroes", 2, "https://example.com/sheet.png", "https://example.com/back_sheet.png",
                     2, 1, 2, unique_back=True)
    entry = obj["CustomDeck"]["2"]
    assert entry["UniqueBack"] is True
    assert entry["BackURL"] == "https://example.com/back_sheet.png"
    assert all(c["CustomDeck"]["2"]["UniqueBack"] is True for c in obj["ContainedObjects"])


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


def test_merge_into_save_preserves_hand_placed_objects() -> None:
    base = {
        "SaveName": "test",
        "ObjectStates": [
            {"Name": "Custom_Model", "GUID": "board1", "Transform": {"posX": 5.0}},
            {"Name": "Infinite_Bag", "GUID": "bag1", "Transform": {"posX": -3.0}},
        ],
    }
    new_obj = build_token("gem", "https://example.com/gem.png")
    save = merge_into_save(base, [new_obj])

    guids = {o["GUID"] for o in save["ObjectStates"]}
    assert "board1" in guids
    assert "bag1" in guids
    assert new_obj["GUID"] in guids
    assert len(save["ObjectStates"]) == 3


def test_merge_into_save_keeps_old_transform_on_replace() -> None:
    new_obj = build_token("gem", "https://example.com/gem-v2.png")
    base = {
        "ObjectStates": [
            {
                "Name": "Custom_Token",
                "GUID": new_obj["GUID"],
                "Transform": {"posX": 7.5, "posY": 2.0, "posZ": -1.0, "scaleX": 2.0},
                "CustomImage": {"ImageURL": "https://example.com/gem-v1.png"},
            },
        ],
    }
    save = merge_into_save(base, [new_obj])

    assert len(save["ObjectStates"]) == 1
    merged = save["ObjectStates"][0]
    assert merged["CustomImage"]["ImageURL"] == "https://example.com/gem-v2.png"
    assert merged["Transform"] == {"posX": 7.5, "posY": 2.0, "posZ": -1.0, "scaleX": 2.0}


def test_merge_into_save_appends_new_managed_objects() -> None:
    base = {"ObjectStates": [{"Name": "Custom_Model", "GUID": "board1", "Transform": {}}]}
    new_obj = build_token("gem", "https://example.com/gem.png")
    save = merge_into_save(base, [new_obj])

    assert len(save["ObjectStates"]) == 2
    assert save["ObjectStates"][-1]["GUID"] == new_obj["GUID"]


def test_merge_into_save_spreads_new_objects_so_they_dont_stack() -> None:
    base = {"ObjectStates": []}
    new_decks = [
        build_deck(f"deck{i}", i, f"https://example.com/{i}.png", "", 1, 1, 1) for i in range(1, 4)
    ]
    save = merge_into_save(base, new_decks)

    positions = [(o["Transform"]["posX"], o["Transform"]["posZ"]) for o in save["ObjectStates"]]
    assert len(set(positions)) == len(positions)
