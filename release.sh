#!/usr/bin/env bash
# Release automation script for Fit File Faker
# Usage: ./release.sh <version> [release-message]
# Example: ./release.sh 2.0.1 "Fix changelog generation and dependencies"

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
error() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

validate_changelog_commit_subjects() {
    local previous_tag
    previous_tag=$(git describe --tags --abbrev=0 --match 'v[0-9]*.[0-9]*.[0-9]*' 2>/dev/null || true)

    if [ -z "$previous_tag" ]; then
        warn "No previous release tag found; skipping git-cliff commit subject validation."
        return 0
    fi

    local invalid_commits=""
    while IFS=$'\t' read -r commit_hash subject; do
        if [[ "$subject" =~ ^docs:\ update\ changelog ]] ||
           [[ "$subject" =~ ^chore:\ bump\ version ]] ||
           [[ "$subject" =~ ^chore\(release\):\ prepare\ for ]] ||
           [[ "$subject" =~ ^chore\(deps\) ]] ||
           [[ "$subject" =~ ^chore\(pr\) ]] ||
           [[ "$subject" =~ ^chore\(pull\) ]]; then
            continue
        fi

        if [[ "$subject" =~ ^(feat|fix|minor-feat|docs|perf|refactor|style|test|chore|ci|build|revert)(\([A-Za-z0-9._-]+\))?(!)?:\ .+ ]]; then
            continue
        fi

        invalid_commits+="${commit_hash} ${subject}"$'\n'
    done < <(git log --format='%h%x09%s' "${previous_tag}..HEAD")

    if [ -n "$invalid_commits" ]; then
        echo -e "${RED}Error: The following commits do not match git-cliff commit parser requirements:${NC}" >&2
        echo >&2
        echo "$invalid_commits" >&2
        echo "Use Conventional Commits subjects so release notes include every relevant change." >&2
        echo "Example: fix: preserve .fit suffix for monitor mode uploads" >&2
        exit 1
    fi

    success "All commits since ${previous_tag} match git-cliff commit parser requirements"
}

show_help() {
    echo -e "${GREEN}FIT File Faker Release Script${NC}"
    echo
    echo -e "${BLUE}USAGE:${NC}"
    echo "    ./release.sh <version> [release-message]"
    echo "    ./release.sh -h | --help"
    echo
    echo -e "${BLUE}ARGUMENTS:${NC}"
    echo -e "    ${GREEN}<version>${NC}          Version number in X.Y.Z format (e.g., 2.0.1)"
    echo -e "    ${GREEN}[release-message]${NC}  Optional release message (default: \"Release vX.Y.Z\")"
    echo
    echo -e "${BLUE}OPTIONS:${NC}"
    echo -e "    ${GREEN}-h, --help${NC}         Show this help message"
    echo
    echo -e "${BLUE}DESCRIPTION:${NC}"
    echo "    Automates the release process for Fit File Faker by:"
    echo "      1. Updating version in pyproject.toml"
    echo "      2. Updating release date in __init__.py"
    echo "      3. Committing the version change"
    echo "      4. Creating an annotated Git tag"
    echo "      5. Pushing commits and tag to origin"
    echo
    echo -e "${BLUE}EXAMPLES:${NC}"
    echo -e "    ${YELLOW}# Release with default message${NC}"
    echo "    ./release.sh 2.0.1"
    echo
    echo -e "    ${YELLOW}# Release with custom message${NC}"
    echo "    ./release.sh 2.0.1 \"Fix changelog generation and dependencies\""
    echo
    echo -e "    ${YELLOW}# Show help${NC}"
    echo "    ./release.sh --help"
    echo
    echo -e "${BLUE}REQUIREMENTS:${NC}"
    echo "    - Git repository on main branch (recommended)"
    echo "    - Clean working directory (recommended)"
    echo
    echo -e "${BLUE}NOTES:${NC}"
    echo "    - The script will prompt for confirmation at each step"
    echo "    - Pushing the tag triggers automated PyPI publication and GitHub release"
    echo "    - Documentation is automatically rebuilt after release"
    echo
}

# Check for help flag
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
    exit 0
fi

# Check if version is provided
if [ -z "$1" ]; then
    error "Version number required. Usage: ./release.sh <version> [release-message]
       Run './release.sh --help' for more information."
fi

VERSION="$1"
RELEASE_MESSAGE="${2:-Release v${VERSION}}"

# Validate version format (should be X.Y.Z)
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    error "Invalid version format. Expected: X.Y.Z (e.g., 2.0.1)"
fi

# Check if git working directory is clean
if ! git diff-index --quiet HEAD --; then
    warn "Working directory has uncommitted changes."
    echo -e "${YELLOW}Uncommitted files:${NC}"
    git status --short
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    warn "You are on branch '$CURRENT_BRANCH', not 'main'."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if tag already exists
if git rev-parse "v${VERSION}" >/dev/null 2>&1; then
    error "Tag v${VERSION} already exists. Use a different version."
fi

validate_changelog_commit_subjects

info "Preparing release v${VERSION}..."
echo

# Step 1: Update version in pyproject.toml
info "Updating version in pyproject.toml..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/^version = \".*\"/version = \"${VERSION}\"/" pyproject.toml
else
    # Linux
    sed -i "s/^version = \".*\"/version = \"${VERSION}\"/" pyproject.toml
fi
success "Version updated to ${VERSION}"

# Step 1b: Update version date in __init__.py
RELEASE_DATE=$(date +%Y-%m-%d)
info "Updating release date in __init__.py to ${RELEASE_DATE}..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/^__version_date__ = \".*\"/__version_date__ = \"${RELEASE_DATE}\"/" fit_file_faker/__init__.py
else
    # Linux
    sed -i "s/^__version_date__ = \".*\"/__version_date__ = \"${RELEASE_DATE}\"/" fit_file_faker/__init__.py
fi
success "Release date updated to ${RELEASE_DATE}"

# Step 2: Update lockfile
info "Updating uv.lock..."
uv lock
success "Lockfile updated"

# Step 3: Show the diff
info "Changes:"
git diff pyproject.toml fit_file_faker/__init__.py uv.lock

# Step 4: Commit version change
echo
read -p "Commit these changes? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    git add pyproject.toml fit_file_faker/__init__.py uv.lock
    git commit -m "chore: bump version to ${VERSION}"
    success "Version change committed"
else
    error "Release cancelled by user"
fi

# Step 5: Create annotated tag
info "Creating annotated tag v${VERSION}..."
echo
echo -e "${BLUE}Release message:${NC}"
echo "  ${RELEASE_MESSAGE}"
echo
read -p "Create tag with this message? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    git tag -a "v${VERSION}" -m "${RELEASE_MESSAGE}"
    success "Tag v${VERSION} created"
else
    error "Release cancelled by user"
fi

# Step 6: Push to remote
echo
info "Ready to push to origin..."
echo "  - Commits on branch: ${CURRENT_BRANCH}"
echo "  - Tag: v${VERSION}"
echo
read -p "Push to origin? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    git push origin "$CURRENT_BRANCH"
    git push origin "v${VERSION}"
    success "Pushed to origin"
else
    warn "Changes committed locally but not pushed."
    warn "To push manually, run:"
    echo "  git push origin ${CURRENT_BRANCH}"
    echo "  git push origin v${VERSION}"
    exit 0
fi

# Done!
echo
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Release v${VERSION} completed successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
info "Next steps:"
echo "  1. Monitor GitHub Actions: https://github.com/jat255/Fit-File-Faker/actions"
echo "  2. Verify PyPI release: https://pypi.org/project/fit-file-faker/"
echo "  3. Check GitHub release: https://github.com/jat255/Fit-File-Faker/releases"
echo "  4. Review docs: https://jat255.github.io/Fit-File-Faker/"
echo
