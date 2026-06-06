import hashlib
import json
from pathlib import Path


def _guid(seed: str) -> str:
    return hashlib.md5(seed.encode()).hexdigest()[:6]


def _base_transform() -> dict:
    return {
        "posX": 0.0, "posY": 1.0, "posZ": 0.0,
        "rotX": 0.0, "rotY": 180.0, "rotZ": 0.0,
        "scaleX": 1.0, "scaleY": 1.0, "scaleZ": 1.0,
    }


def _base_object(name: str, guid_seed: str) -> dict:
    return {
        "GUID": _guid(guid_seed),
        "Name": name,
        "Transform": _base_transform(),
        "Nickname": "",
        "Description": "",
        "GMNotes": "",
        "AltLookAngle": {"x": 0.0, "y": 0.0, "z": 0.0},
        "ColorDiffuse": {"r": 1.0, "g": 1.0, "b": 1.0},
        "LayoutGroupSortIndex": 0,
        "Value": 0,
        "Locked": False,
        "Grid": True,
        "Snap": True,
        "IgnoreFoW": False,
        "MeasureMovement": False,
        "DragSelectable": True,
        "Autoraise": True,
        "Sticky": True,
        "Tooltip": True,
        "GridProjection": False,
        "HideWhenFaceDown": False,
        "Hands": False,
        "LuaScript": "",
        "LuaScriptState": "",
        "XmlUI": "",
    }


def build_token(name: str, image_url: str) -> dict:
    obj = _base_object("Custom_Token", f"token:{name}")
    obj["Nickname"] = name
    obj["CustomImage"] = {
        "ImageURL": image_url,
        "ImageSecondaryURL": "",
        "ImageScalar": 1.0,
        "WidthScale": 0.0,
        "CustomToken": {
            "Thickness": 0.2,
            "MergeDistancePixels": 15.0,
            "StandUp": False,
            "Stackable": False,
        },
    }
    return obj


def build_tile(name: str, front_url: str, back_url: str = "") -> dict:
    obj = _base_object("Custom_Tile", f"tile:{name}")
    obj["Nickname"] = name
    obj["CustomImage"] = {
        "ImageURL": front_url,
        "ImageSecondaryURL": back_url,
        "ImageScalar": 1.0,
        "WidthScale": 0.0,
        "CustomTile": {
            "Type": 0,
            "Thickness": 0.2,
            "Stackable": False,
            "Stretch": True,
        },
    }
    return obj


def build_card(name: str, deck_key: int, front_url: str, back_url: str = "") -> dict:
    obj = _base_object("CardCustom", f"card:{name}")
    obj["Nickname"] = name
    obj["ColorDiffuse"] = {"r": 0.713235259, "g": 0.713235259, "b": 0.713235259}
    obj["HideWhenFaceDown"] = True
    obj["Hands"] = True
    obj["CardID"] = deck_key * 100
    obj["SidewaysCard"] = False
    obj["CustomDeck"] = {
        str(deck_key): {
            "FaceURL": front_url,
            "BackURL": back_url,
            "NumWidth": 1,
            "NumHeight": 1,
            "BackIsHidden": True,
            "UniqueBack": False,
            "Type": 0,
        }
    }
    return obj


def build_deck(
    name: str,
    deck_key: int,
    sheet_url: str,
    back_url: str,
    num_width: int,
    num_height: int,
    num_cards: int,
) -> dict:
    entry = {
        "FaceURL": sheet_url,
        "BackURL": back_url,
        "NumWidth": num_width,
        "NumHeight": num_height,
        "BackIsHidden": False,
        "UniqueBack": False,
        "Type": 0,
    }
    deck_ids = [deck_key * 100 + i for i in range(num_cards)]
    contained = []
    for i in range(num_cards):
        card = _base_object("Card", f"deck_card:{name}:{i}")
        card["ColorDiffuse"] = {"r": 0.713235259, "g": 0.713235259, "b": 0.713235259}
        card["HideWhenFaceDown"] = True
        card["Hands"] = True
        card["CardID"] = deck_key * 100 + i
        card["SidewaysCard"] = False
        card["CustomDeck"] = {str(deck_key): entry}
        contained.append(card)

    obj = _base_object("Deck", f"deck:{name}")
    obj["Nickname"] = name
    obj["ColorDiffuse"] = {"r": 0.713235259, "g": 0.713235259, "b": 0.713235259}
    obj["HideWhenFaceDown"] = True
    obj["SidewaysCard"] = False
    obj["DeckIDs"] = deck_ids
    obj["CustomDeck"] = {str(deck_key): entry}
    obj["ContainedObjects"] = contained
    return obj


def build_save(skeleton_path: Path, objects: list[dict]) -> dict:
    """Load skeleton, replace game assets, preserve structural objects (HandTriggers)."""
    with skeleton_path.open(encoding="utf-8") as f:
        save = json.load(f)
    hand_triggers = [o for o in save.get("ObjectStates", []) if o.get("Name") == "HandTrigger"]
    save["ObjectStates"] = hand_triggers + objects
    return save
