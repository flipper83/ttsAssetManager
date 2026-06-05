# TTS Asset Manager

Prepare [Tabletop Simulator](https://www.tabletopsimulator.com/) save files from local image assets — no need to open TTS during prototyping.

## What it does

1. Reads images from a local folder and classifies them by filename convention
2. Composes deck sprite sheets automatically
3. Uploads assets to GitHub Pages (content-addressed, cache-safe)
4. Generates a `.json` save file ready to load in TTS
5. Copies the save directly to your TTS saves folder
6. Syncs the save to GitHub so teammates can pull the latest version

## Asset naming conventions

| File | Type |
|------|------|
| `d_<deck>_<card>.png` | Card in a deck |
| `d_<deck>_back.png` | Back image for a deck |
| `c_<name>_a.png` / `c_<name>_b.png` | Standalone card (front / back) |
| `t_<name>_a.png` / `t_<name>_b.png` | Tile (front / back) |
| `to_<name>.png` | Token |

Cards within a deck are sorted alphabetically and composed into a sprite sheet automatically.

## Setup

**1. Clone and install**

```bash
git clone https://github.com/flipper83/ttsAssetManager.git
cd ttsAssetManager
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[gui]"
```

**2. Launch the GUI**

```bash
tts-manager-gui
```

**3. Configure GitHub (Settings dialog)**

Open **File → Settings** and fill in:

- **GitHub token** — [Personal access token](https://github.com/settings/tokens) with `repo` scope
- **GitHub owner** — your GitHub username
- **GitHub repo** — a public repo for your assets (e.g. `my-tts-assets`)
- **TTS saves folder** — auto-detected, or set manually

> `config.json` is gitignored — your token stays local.

**4. Create a game**

Click **+ New Game** and provide:

- **Game name** — display name (e.g. `My Game`)
- **Assets folder** — local folder containing your images
- **GitHub subfolder** — auto-derived from the name (e.g. `my-game`)

## Usage

### Upload & update

| Button | Action |
|--------|--------|
| **Upload All** | Full upload — uploads everything and generates the save |
| **Update** | Incremental — only uploads changed or new files |
| **Pull** | Download the latest save from GitHub to your TTS folder |

The asset tree shows the sync status of each asset at a glance:

| Icon | Color | Meaning |
|------|-------|---------|
| `+` | Green | New — never uploaded |
| `↑` | Orange | Modified — uploaded but changed locally |
| `✓` | Gray | Up to date |

### Team workflow

1. **Person A** creates the game, uploads assets, and shares the save URL  
   (shown in the log after upload, e.g. `https://owner.github.io/repo/saves/my-game.json`)
2. **Person B** *(Join — coming soon)* will be able to join via that URL and pull the latest save
3. Before uploading, the app warns if someone else has pushed changes since your last sync

## How updates work

Each uploaded asset gets a short content hash in its filename (`token_abc12345.png`). When a file changes, the hash changes and TTS downloads the new version automatically — no stale cache issues. Old versions are deleted from GitHub.

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src tests
ruff format src tests
```

## Requirements

- Python 3.11+
- A GitHub account with a public repo for assets
- Tabletop Simulator (to load the generated save)
