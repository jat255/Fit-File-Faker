---
name: fit-file-faker-release
description: Use when preparing or publishing a Fit File Faker release, version bump, or release tag.
---

# Fit File Faker releases

Use the repository's current `release.sh`, `AGENTS.md`, and `.github/workflows/publish_and_release.yml` as the source of truth. A pushed release tag publishes to PyPI, creates a draft GitHub release, and triggers changelog and documentation updates; publishing is a separate action from preparing a release.

1. Determine the requested scope and version. Inspect the latest release tag, `pyproject.toml`, and commits since the tag; recommend a version from the changes if one was not specified. Ask for the version if it cannot be determined. Do not publish when asked only to prepare or review a release.
2. Check the current branch, working tree, remote `main`, and existing local and remote tags. Preserve unrelated changes. Release from an up-to-date `main` unless the user explicitly directs otherwise. Stop and explain conflicts, duplicate tags, or unexpected repository state rather than bypassing checks.
3. Inspect every subject with `git log --format='%h %s' <previous-tag>..HEAD`. Check both the repository's conventional-commit policy and the current git-cliff parser in `pyproject.toml`; report subjects that are invalid or would be omitted. The script has exceptions for some subjects, so its validation alone is not sufficient. Do not rewrite published history without authorization.
4. Run the relevant local tests, lint, and package build; resolve failures before release. Review release notes and the version/date/lockfile changes. For preparation only, make the requested reviewable changes without creating or pushing a release tag.
5. For an explicitly requested release, use `./release.sh <version> [release-message]` after reviewing its current behavior. It updates `pyproject.toml`, `fit_file_faker/__init__.py`, and `uv.lock`, then prompts to commit, create an annotated tag, and push the branch and tag. Respond to prompts only within the user's authorized scope. Do not silently accept warnings about a dirty tree or unexpected branch. If interrupted, inspect the commit, tag, and remote state before retrying; avoid duplicate publication.
6. Report the version, commit, tag, local verification, and which publication steps completed. The workflow creates a **draft** GitHub release; do not claim it is published or that PyPI succeeded without evidence. Do not monitor GitHub Actions unless the user explicitly asks. If a draft release needs editing or publishing, follow the user's requested scope.
