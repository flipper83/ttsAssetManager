import json
import os
import platform
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Config:
    github_token: str
    github_owner: str
    github_repo: str
    github_branch: str = "gh-pages"
    tts_saves_path: str | None = None
    save_name: str = "MyGame"

    @classmethod
    def load(cls, path: Path) -> "Config":
        if not path.exists():
            raise FileNotFoundError(
                f"Config file '{path}' not found. "
                "Copy 'config.example.json' and fill in your values."
            )
        with path.open(encoding="utf-8") as f:
            data = json.load(f)

        token = data.get("github_token", "")
        if not token or token == "YOUR_GITHUB_TOKEN_HERE":
            raise ValueError("Set a real github_token in config.json")

        return cls(
            github_token=token,
            github_owner=data["github_owner"],
            github_repo=data["github_repo"],
            github_branch=data.get("github_branch", "gh-pages"),
            tts_saves_path=data.get("tts_saves_path"),
            save_name=data.get("save_name", "MyGame"),
        )

    @classmethod
    def empty(cls) -> "Config":
        return cls(github_token="", github_owner="", github_repo="")

    def save(self, path: Path) -> None:
        data = {
            "github_token": self.github_token,
            "github_owner": self.github_owner,
            "github_repo": self.github_repo,
            "github_branch": self.github_branch,
            "tts_saves_path": self.tts_saves_path,
            "save_name": self.save_name,
        }
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def is_valid(self) -> bool:
        return bool(
            self.github_token
            and self.github_token != "YOUR_GITHUB_TOKEN_HERE"
            and self.github_owner
            and self.github_repo
        )

    @property
    def base_url(self) -> str:
        return f"https://{self.github_owner}.github.io/{self.github_repo}"

    @property
    def tts_saves_dir(self) -> Path | None:
        if not self.tts_saves_path:
            return None
        return Path(os.path.expanduser(self.tts_saves_path))


def detect_tts_saves_paths() -> list[tuple[str, Path]]:
    """Return (label, path) suggestions for the TTS saves folder per platform."""
    system = platform.system()
    home = Path.home()
    candidates = []

    if system == "Darwin":
        candidates = [
            ("macOS (default)", home / "Library" / "Tabletop Simulator" / "Saves"),
            ("macOS (Steam)", home / "Library" / "Application Support" / "Steam" /
             "steamapps" / "common" / "Tabletop Simulator" / "Saves"),
        ]
    elif system == "Windows":
        candidates = [
            ("Windows (default)", home / "Documents" / "My Games" / "Tabletop Simulator" / "Saves"),
        ]
    elif system == "Linux":
        candidates = [
            ("Linux / Steam (default)", home / ".local" / "share" / "Tabletop Simulator" / "Saves"),
            ("Linux / Steam (Proton)", home / ".steam" / "steam" / "steamapps" / "compatdata" /
             "286160" / "pfx" / "drive_c" / "users" / "steamuser" / "Documents" /
             "My Games" / "Tabletop Simulator" / "Saves"),
        ]

    return [(label, path) for label, path in candidates]
