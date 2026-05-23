# TTS Asset Manager — Project Guide

## What this project does

Prepares Tabletop Simulator save files from local image assets without opening TTS.
It classifies images by filename convention, uploads them to GitHub Pages, and generates
a `.json` save file that TTS can load directly.

## Architecture

```
src/tts_manager/
├── models.py      # Domain dataclasses — no logic, no I/O
├── classifier.py  # Filename → model mapping (pure logic)
├── composer.py    # Deck sprite sheet composition (Pillow)
├── builder.py     # TTS JSON object construction (pure logic)
├── state.py       # StateManager — upload hash tracking
├── uploader.py    # GitHubUploader — GitHub API via Git Data API
├── config.py      # Config dataclass + validation
├── manager.py     # AssetManager — orchestrates everything (public API)
└── cli.py         # Thin CLI wrapper around AssetManager
```

**Key design rule**: `manager.py` is the single public API. CLI and GUI both consume `AssetManager`
and nothing else. Library modules never call `print()` — all output goes through `ProgressCallback`.

## CLI vs GUI

The project is designed to support both a CLI and a graphical UI.

- **CLI** (`cli.py`): calls `AssetManager`, prints `ProgressEvent` messages.
- **GUI** (future): creates `AssetManager` with a callback that updates UI widgets.
  Run `AssetManager.upload()` / `AssetManager.update()` in a background thread; GUI thread
  receives progress via the callback.

Never add `print()` to library code (`models`, `classifier`, `composer`, `builder`, `state`,
`uploader`, `manager`). Always emit a `ProgressEvent` instead.

## Asset naming conventions

| Prefix | Example | Meaning |
|--------|---------|---------|
| `d_<deck>_<card>` | `d_spells_fireball.png` | Card in deck "spells" |
| `d_<deck>_back` | `d_spells_back.png` | Back image for deck "spells" |
| `c_<name>_a` | `c_hero_a.png` | Standalone card front |
| `c_<name>_b` | `c_hero_b.png` | Standalone card back |
| `t_<name>_a` | `t_forest_a.png` | Tile front |
| `t_<name>_b` | `t_forest_b.png` | Tile back |
| `to_<name>` | `to_gem.png` | Token (front only) |

Cards within a deck are sorted alphabetically by card_name. The sheet is composed left-to-right,
top-to-bottom, max 10 columns.

## TTS JSON details

- `CardID = deck_key * 100 + card_index` (0-based index in the sheet)
- Each asset type that needs a `CustomDeck` entry gets a unique `deck_key` (auto-incremented)
- Deck sprite sheets use the Git Data API (no size limit)
- Versioned filenames (`name_<sha8>.ext`) bust TTS's local image cache on update

## Running

```bash
./tts.sh upload   # full upload of all assets
./tts.sh update   # incremental — only changed files
```

Or after `pip install -e ".[dev]"`:
```bash
tts-manager upload
tts-manager update
```

## Development

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src tests
ruff format src tests
```

## Testing

- Tests live in `tests/`, using `pytest`.
- `conftest.py` provides `input_dir` fixture with minimal PNG files (no real assets needed).
- No network calls in tests — uploader is not tested directly (requires real GitHub token).
- Add tests for any new classifier rule, builder function, or state logic.
- Do not use `unittest.mock` to mock the filesystem — use `tmp_path` fixtures instead.

## Adding a new asset type

1. Add a dataclass to `models.py`
2. Add a `_parse_<type>` function in `classifier.py` and wire it in `classify_assets`
3. Add a `build_<type>` function in `builder.py`
4. Handle the new type in `manager.py` (upload + build TTS object)
5. Add tests in `tests/test_classifier.py` and `tests/test_builder.py`

## Config

`config.json` (gitignored):
```json
{
  "github_token": "...",
  "github_owner": "flipper83",
  "github_repo": "tts-assets",
  "github_branch": "gh-pages",
  "tts_saves_path": "~/Library/Tabletop Simulator/Saves",
  "save_name": "MyGame"
}
```
