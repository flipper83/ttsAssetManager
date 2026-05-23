# TTS Asset Manager

Prepare [Tabletop Simulator](https://www.tabletopsimulator.com/) save files from local image assets — no need to open TTS during prototyping.

## What it does

1. Reads images from `input/` and classifies them by filename convention
2. Composes deck sprite sheets automatically
3. Uploads assets to GitHub Pages (content-addressed, cache-safe)
4. Generates a `.json` save file ready to load in TTS
5. Copies the save directly to your TTS saves folder

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
pip install -e ".[dev]"
```

**2. Create a GitHub repo for your assets**

Create a public repo (e.g. `my-tts-assets`) and enable GitHub Pages:
> Settings → Pages → Source: `gh-pages` branch → root

**3. Generate a GitHub token**

> GitHub → Settings → Developer settings → Personal access tokens → Classic
> Scope: `public_repo`

**4. Configure**

```bash
cp config.example.json config.json
```

Edit `config.json`:

```json
{
  "github_token": "your_token_here",
  "github_owner": "your_username",
  "github_repo": "my-tts-assets",
  "github_branch": "gh-pages",
  "tts_saves_path": "~/Library/Tabletop Simulator/Saves",
  "save_name": "MyGame"
}
```

> `config.json` is gitignored — your token stays local.

**5. Add your assets**

Drop your images into `input/` following the naming conventions above.

## Usage

```bash
# Full upload — uploads everything and generates the save
./tts.sh upload

# Incremental update — only uploads changed or new files
./tts.sh update
```

The save file is written to `output/TTS_Save.json` and copied to your TTS saves folder automatically. Open TTS and load it from the Games menu.

## How updates work

Each uploaded file gets a short content hash in its name (`token_abc12345.png`). When a file changes, the hash changes and TTS downloads the new version — no stale cache issues. Old versions are deleted from GitHub automatically.

## Development

```bash
# Run tests
pytest

# Lint
ruff check src tests
```

## Requirements

- Python 3.11+
- A GitHub account with a public repo for assets
- Tabletop Simulator (to load the generated save)
