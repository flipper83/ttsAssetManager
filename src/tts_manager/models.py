from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DeckCard:
    deck_name: str
    card_name: str
    path: Path


@dataclass
class DeckAsset:
    name: str
    cards: list[DeckCard] = field(default_factory=list)
    back_path: Path | None = None


@dataclass
class CardAsset:
    name: str
    front_path: Path
    back_path: Path | None = None


@dataclass
class TileAsset:
    name: str
    front_path: Path
    back_path: Path | None = None


@dataclass
class TokenAsset:
    name: str
    front_path: Path


@dataclass
class AssetCollection:
    decks: dict[str, DeckAsset] = field(default_factory=dict)
    cards: dict[str, CardAsset] = field(default_factory=dict)
    tiles: dict[str, TileAsset] = field(default_factory=dict)
    tokens: dict[str, TokenAsset] = field(default_factory=dict)
