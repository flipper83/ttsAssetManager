# TTS Asset Manager — Project Guide

## Conventions

- All code, comments, docstrings, PR titles, descriptions, commit messages, and documentation must be written in English.
- Before opening a PR, check that README.md is aligned with any new features or workflow changes.

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
├── config.py      # Config dataclass + validation (multi-game)
├── manager.py     # AssetManager — orchestrates everything (public API)
├── cli.py         # Thin CLI wrapper around AssetManager
└── gui/           # PyQt6 desktop app (thin UI wrapper around AssetManager)
    ├── app.py                 # Entry point — loads Config, opens MainWindow
    ├── main_window.py         # Main window: game list, asset tree, log, actions
    ├── worker.py              # AssetWorker — runs AssetManager calls off the UI thread
    ├── new_game_dialog.py     # Create a new game (name, assets folder)
    ├── join_game_dialog.py    # Join an existing game from a shared save URL
    ├── delete_game_dialog.py  # Remove a game (optionally delete remote assets)
    └── settings_dialog.py     # GitHub credentials + TTS saves folder
```

**Key design rule**: `manager.py` is the single public API. CLI and GUI both consume `AssetManager`
and nothing else. Library modules never call `print()` — all output goes through `ProgressCallback`.

## CLI vs GUI

The project ships both a CLI and a graphical UI; both are thin wrappers around `AssetManager`.

- **CLI** (`cli.py`): calls `AssetManager`, prints `ProgressEvent` messages. One game per run
  (`--game`, defaults to the first game in config).
- **GUI** (`gui/`, PyQt6): the primary day-to-day tool. `MainWindow` lists games from
  `config.json`, scans the selected game's assets folder every 5s, and shows sync status
  (new / modified / up to date) in a tree. `AssetWorker` runs `AssetManager.upload()` /
  `.update()` / `.pull()` / `.delete_game()` on a background `QThread`; progress reaches the UI
  via Qt signals fed by the `ProgressCallback`.
  - Launch: `tts-manager-gui` (or `python -m tts_manager.gui.app`) — requires the `gui` extra
    (`pip install -e ".[gui]"`).
  - Supports multiple games at once (see Config below): **New Game**, **Join Game** (from a
    shared save URL), **Delete Game**.
  - **Upload All** / **Update** / **Pull** buttons drive the same operations as the CLI.
  - Warns before upload if the remote save hash has changed since the last local sync
    (someone else pushed in the meantime).

Never add `print()` to library code (`models`, `classifier`, `composer`, `builder`, `state`,
`uploader`, `manager`). Always emit a `ProgressEvent` instead — this is what lets the GUI show
live progress without any library code knowing about Qt.

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

`config.json` (gitignored) holds global GitHub credentials plus a list of games. Each `GameConfig`
can override `github_owner` / `github_repo` / `github_branch` individually (e.g. to keep one
game's assets in a different repo); unset fields fall back to the globals via
`GameConfig.resolved_config()`.

```json
{
  "github_token": "...",
  "github_owner": "flipper83",
  "github_repo": "tts-assets",
  "github_branch": "gh-pages",
  "tts_saves_path": "~/Library/Tabletop Simulator/Saves",
  "games": [
    {
      "name": "My Game",
      "assets_folder": "~/tts-assets/my-game",
      "github_subfolder": "my-game"
    }
  ]
}
```

`github_subfolder` is auto-derived from `name` (slugified) if omitted. The GUI's **New Game** /
**Join Game** dialogs write to this `games` list; the CLI's `--game` flag selects one by name.
