import base64
from pathlib import Path

import requests

from .config import Config
from .progress import EventKind, ProgressCallback, ProgressEvent, noop


class GitHubUploader:
    """Uploads files to a GitHub Pages branch using the Git Data API."""

    def __init__(self, config: Config, on_progress: ProgressCallback = noop) -> None:
        self._config = config
        self._on_progress = on_progress
        self._headers = {
            "Authorization": f"Bearer {config.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._base_url = f"https://api.github.com/repos/{config.github_owner}/{config.github_repo}"
        self._ensure_repo()
        self._ensure_branch()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _ensure_repo(self) -> None:
        r = requests.get(self._base_url, headers=self._headers)
        if r.status_code == 404:
            self._on_progress(ProgressEvent(EventKind.INFO, f"Creating repo '{self._config.github_repo}'..."))
            r = requests.post(
                "https://api.github.com/user/repos",
                headers=self._headers,
                json={"name": self._config.github_repo, "private": False, "auto_init": True},
            )
            r.raise_for_status()
            self._on_progress(ProgressEvent(
                EventKind.WARNING,
                f"Repo created. Enable GitHub Pages at "
                f"https://github.com/{self._config.github_owner}/{self._config.github_repo}/settings/pages "
                f"(Source: gh-pages branch, root)",
            ))
        elif r.status_code != 200:
            r.raise_for_status()

    def _branch_sha(self, branch: str) -> str | None:
        r = requests.get(f"{self._base_url}/git/ref/heads/{branch}", headers=self._headers)
        return r.json()["object"]["sha"] if r.status_code == 200 else None

    def _ensure_branch(self) -> None:
        if self._branch_sha(self._config.github_branch):
            return
        source_sha = next(
            (
                requests.get(f"{self._base_url}/git/ref/heads/{ref}", headers=self._headers).json()["object"]["sha"]
                for ref in ("main", "master")
                if requests.get(f"{self._base_url}/git/ref/heads/{ref}", headers=self._headers).status_code == 200
            ),
            None,
        )
        if not source_sha:
            raise RuntimeError("Cannot find main or master branch to base gh-pages on")
        requests.post(
            f"{self._base_url}/git/refs",
            headers=self._headers,
            json={"ref": f"refs/heads/{self._config.github_branch}", "sha": source_sha},
        ).raise_for_status()
        self._on_progress(ProgressEvent(EventKind.INFO, f"Created branch '{self._config.github_branch}'"))

    # ------------------------------------------------------------------
    # Git Data API
    # ------------------------------------------------------------------

    def _create_blob(self, data: bytes) -> str:
        r = requests.post(
            f"{self._base_url}/git/blobs",
            headers=self._headers,
            json={"content": base64.b64encode(data).decode(), "encoding": "base64"},
        )
        r.raise_for_status()
        return r.json()["sha"]

    def _head_sha(self) -> str:
        return self._branch_sha(self._config.github_branch)  # type: ignore[return-value]

    def _tree_sha(self, commit_sha: str) -> str:
        r = requests.get(f"{self._base_url}/git/commits/{commit_sha}", headers=self._headers)
        r.raise_for_status()
        return r.json()["tree"]["sha"]

    def _create_tree(self, base_tree: str, entries: list[dict]) -> str:
        r = requests.post(
            f"{self._base_url}/git/trees",
            headers=self._headers,
            json={"base_tree": base_tree, "tree": entries},
        )
        r.raise_for_status()
        return r.json()["sha"]

    def _create_commit(self, message: str, tree: str, parent: str) -> str:
        r = requests.post(
            f"{self._base_url}/git/commits",
            headers=self._headers,
            json={"message": message, "tree": tree, "parents": [parent]},
        )
        r.raise_for_status()
        return r.json()["sha"]

    def _update_ref(self, commit_sha: str) -> None:
        requests.patch(
            f"{self._base_url}/git/refs/heads/{self._config.github_branch}",
            headers=self._headers,
            json={"sha": commit_sha},
        ).raise_for_status()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload(self, local_path: Path, remote_path: str) -> str:
        """Upload a file and return its GitHub Pages URL."""
        blob_sha = self._create_blob(local_path.read_bytes())
        head = self._head_sha()
        new_tree = self._create_tree(self._tree_sha(head), [{
            "path": remote_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha,
        }])
        self._update_ref(self._create_commit(f"Upload {remote_path}", new_tree, head))
        url = f"{self._config.base_url}/{remote_path}"
        self._on_progress(ProgressEvent(EventKind.UPLOAD, f"→ {url}", {"url": url, "path": remote_path}))
        return url

    def delete(self, remote_path: str) -> None:
        """Delete a file from the repo (no-op if not found)."""
        r = requests.get(
            f"{self._base_url}/contents/{remote_path}",
            headers=self._headers,
            params={"ref": self._config.github_branch},
        )
        if r.status_code == 404:
            return
        r.raise_for_status()
        requests.delete(
            f"{self._base_url}/contents/{remote_path}",
            headers=self._headers,
            json={
                "message": f"Remove {remote_path}",
                "sha": r.json()["sha"],
                "branch": self._config.github_branch,
            },
        ).raise_for_status()
        self._on_progress(ProgressEvent(EventKind.DELETE, f"Deleted old: {remote_path}"))
