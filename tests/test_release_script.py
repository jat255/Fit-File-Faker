"""Tests for release automation script preflight checks."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path


def run_git(repo: Path, *args: str) -> None:
    """Run a git command in the temporary release repository."""
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def create_release_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo that can run release.sh."""
    repo = tmp_path / "release-repo"
    repo.mkdir()

    source_root = Path(__file__).resolve().parents[1]
    shutil.copy(source_root / "release.sh", repo / "release.sh")
    pyproject_text = (source_root / "pyproject.toml").read_text()
    (repo / "pyproject.toml").write_text(
        re.sub(
            r'^version = "[^"]+"',
            'version = "2.1.5"',
            pyproject_text,
            count=1,
            flags=re.MULTILINE,
        )
    )
    shutil.copy(source_root / "uv.lock", repo / "uv.lock")

    package_dir = repo / "fit_file_faker"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        '__version_date__ = "2026-01-01"  # Updated automatically by release.sh\n'
    )

    run_git(repo, "init", "-b", "main")
    run_git(repo, "config", "user.name", "Release Test")
    run_git(repo, "config", "user.email", "release-test@example.com")
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", "chore: initial release fixture")
    run_git(repo, "tag", "v2.1.5")
    return repo


def test_release_script_rejects_commit_subjects_git_cliff_will_not_render(
    tmp_path: Path,
) -> None:
    """Abort before release mutation when a commit subject cannot appear in git-cliff."""
    repo = create_release_repo(tmp_path)
    (repo / "change.txt").write_text("change\n")
    run_git(repo, "add", "change.txt")
    run_git(repo, "commit", "-m", "Support Garmin MFA login and add .fit suffix")

    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(tmp_path / "uv-cache")
    result = subprocess.run(
        ["./release.sh", "2.2.0"],
        cwd=repo,
        input="n\n",
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )

    assert result.returncode != 0
    assert "do not match git-cliff commit parser requirements" in result.stderr
    assert "Support Garmin MFA login and add .fit suffix" in result.stderr
    assert 'version = "2.1.5"' in (repo / "pyproject.toml").read_text()
