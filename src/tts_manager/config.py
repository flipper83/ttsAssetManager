import json
import os
from dataclasses import dataclass
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

    @property
    def base_url(self) -> str:
        return f"https://{self.github_owner}.github.io/{self.github_repo}"

    @property
    def tts_saves_dir(self) -> Path | None:
        if not self.tts_saves_path:
            return None
        return Path(os.path.expanduser(self.tts_saves_path))
