import base64
import json
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
            self._ensure_nojekyll()
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
        self._ensure_nojekyll()
        self._enable_pages()

    def _ensure_nojekyll(self) -> None:
        """Add .nojekyll to the gh-pages branch if missing (prevents Jekyll from filtering assets)."""
        r = requests.get(
            f"{self._base_url}/contents/.nojekyll",
            headers=self._headers,
            params={"ref": self._config.github_branch},
        )
        if r.status_code == 200:
            return
        blob_sha = requests.post(
            f"{self._base_url}/git/blobs",
            headers=self._headers,
            json={"content": "", "encoding": "utf-8"},
        ).json()["sha"]
        head = self._head_sha()
        new_tree = self._create_tree(self._tree_sha(head), [{
            "path": ".nojekyll",
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha,
        }])
        self._update_ref(self._create_commit("Add .nojekyll to disable Jekyll", new_tree, head))
        self._on_progress(ProgressEvent(EventKind.INFO, "Added .nojekyll to gh-pages branch"))

    def _enable_pages(self) -> None:
        """Enable GitHub Pages via API (best-effort; requires pages write permission)."""
        r = requests.post(
            f"{self._base_url}/pages",
            headers=self._headers,
            json={"source": {"branch": self._config.github_branch, "path": "/"}},
        )
        if r.status_code in (201, 409):
            self._on_progress(ProgressEvent(EventKind.INFO, f"GitHub Pages enabled → {self._config.base_url}"))
        else:
            self._on_progress(ProgressEvent(
                EventKind.WARNING,
                f"Enable GitHub Pages manually at "
                f"https://github.com/{self._config.github_owner}/{self._config.github_repo}/settings/pages "
                f"(Source: {self._config.github_branch} branch, root)",
            ))

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

    def _commit_blob(self, content: bytes, remote_path: str) -> str:
        blob_sha = self._create_blob(content)
        head = self._head_sha()
        new_tree = self._create_tree(self._tree_sha(head), [{
            "path": remote_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha,
        }])
        self._update_ref(self._create_commit(f"Upload {remote_path}", new_tree, head))
        return f"{self._config.base_url}/{remote_path}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload(self, local_path: Path, remote_path: str) -> str:
        """Upload a file and return its GitHub Pages URL."""
        url = self._commit_blob(local_path.read_bytes(), remote_path)
        self._on_progress(ProgressEvent(EventKind.UPLOAD, f"→ {url}", {"url": url, "path": remote_path}))
        return url

    def upload_json(self, data: dict, remote_path: str) -> None:
        """Upload a dict as JSON (no progress event — internal bookkeeping file)."""
        self._commit_blob(json.dumps(data, indent=2, ensure_ascii=False).encode(), remote_path)

    def fetch_json(self, remote_path: str) -> dict | None:
        """Download and parse a JSON file from the branch. Returns None if not found."""
        r = requests.get(
            f"{self._base_url}/contents/{remote_path}",
            headers=self._headers,
            params={"ref": self._config.github_branch},
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return json.loads(base64.b64decode(r.json()["content"]))

    def fetch_bytes(self, remote_path: str) -> bytes | None:
        """Download raw bytes of a file from the branch. Returns None if not found."""
        r = requests.get(
            f"{self._base_url}/contents/{remote_path}",
            headers=self._headers,
            params={"ref": self._config.github_branch},
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return base64.b64decode(r.json()["content"])

    @classmethod
    def fetch_remote_state(cls, config, remote_path: str) -> dict | None:
        """Fetch and parse a JSON file without full uploader initialization."""
        r = requests.get(
            f"https://api.github.com/repos/{config.github_owner}/{config.github_repo}/contents/{remote_path}",
            headers={
                "Authorization": f"Bearer {config.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            params={"ref": config.github_branch},
            timeout=5,
        )
        if r.status_code != 200:
            return None
        try:
            return json.loads(base64.b64decode(r.json()["content"]))
        except Exception:
            return None

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
