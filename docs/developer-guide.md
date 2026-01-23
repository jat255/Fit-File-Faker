# Developer Guide

This guide provides comprehensive information for developers contributing to Fit File Faker, including architecture, testing, and release processes.

## Getting Started with Development

### Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) (preferred) or pip
- Git

### Development Setup

Clone the repository and install dependencies:

=== "uv (Recommended)"

    ```bash
    git clone https://github.com/jat255/Fit-File-Faker.git
    cd Fit-File-Faker
    uv sync  # Installs all dependencies
    ```

=== "pip"

    ```bash
    git clone https://github.com/jat255/Fit-File-Faker.git
    cd Fit-File-Faker
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install .
    ```

### Pre-commit Hooks

The project uses [pre-commit](https://pre-commit.com/) to run code quality checks before committing. After setting up your development environment:

```bash
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

This automatically runs the following checks:

- **`ruff check`** and **`ruff format`**: Code linting and formatting on staged files
- **`gitlint`**: Validates commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) format

Run hooks manually on all files:

```bash
uv run pre-commit run --all-files
```

### Common Development Commands

```bash
# Show help
fit-file-faker -h

# Interactive profile management menu
fit-file-faker --config-menu

# Show directories used for configuration and cache
fit-file-faker --show-dirs

# Edit a single FIT file
fit-file-faker path/to/file.fit

# Edit and upload to Garmin Connect
fit-file-faker -u path/to/file.fit

# Upload all new files in configured directory
fit-file-faker -ua

# Monitor directory for new files
fit-file-faker -m

# Dry run (no changes or uploads)
fit-file-faker -d path/to/file.fit
```

### Linting

```bash
# Run ruff (configured in dev dependencies)
ruff check .
ruff format .
```

### Build and Distribution

```bash
# Build the package for testing
uv build

# Install locally for testing
pip install -e .
```

### Release strategy

Releases are done built and pushed to PyPI automatically by the GitHub
action in `.github/workflows/publish_and_release.yml`, which is triggered
whenever a tag is pushed to the repository.

## Architecture Overview

### Package Structure

The application is organized as a modular Python package (`fit_file_faker/`) with ~1,800 total lines across six files:

```
fit_file_faker/
├── __init__.py           # Package initialization
├── app.py                # Main application, CLI, uploads, monitoring (550 lines)
├── app_registry.py       # NEW: Trainer app detection system (305 lines)
├── config.py             # Configuration management (750 lines)
├── fit_editor.py         # FIT file editing core logic (313 lines)
└── utils.py              # Utility functions and monkey patches (103 lines)
```

**Entry Point**: `fit_file_faker.app:run` (defined in `pyproject.toml`)

!!! note "Design Philosophy"
    The modular structure improves maintainability while keeping the codebase compact:

    - **Separation of concerns**: config, editing, upload, utilities, app detection
    - **Easier testing**: Each module can be tested independently
    - **Extensible architecture**: New trainer apps can be added via `app_registry.py`
    - **Backward compatibility**: Legacy single-profile configs auto-migrate
    - Clear boundaries between functionality
    - Still simple to understand and contribute to

### Core Workflow

The tool follows a six-step process:

1. **Read FIT file**: Uses the `fit_tool` library to parse binary FIT files
2. **Apply fit_tool patch**: Applies monkey patch from `utils.py` to handle malformed FIT files (e.g., COROS)
3. **Identify device messages**: Locates `FileIdMessage`, `FileCreatorMessage`, and `DeviceInfoMessage` records
4. **Rewrite manufacturer/product IDs**: Changes manufacturer codes from:
    - `DEVELOPMENT` (255)
    - `ZWIFT`
    - `WAHOO_FITNESS`
    - `PEAKSWARE`
    - `HAMMERHEAD`
    - `COROS`
    - `MYWHOOSH` (331)

    to `GARMIN` (1) with Edge 830 product ID (3122)

5. **Rebuild FIT file**: Uses `FitFileBuilder` to reconstruct the file with modified messages
6. **Upload (optional)**: Authenticates to Garmin Connect via `garth` library and uploads the modified file

### Module Breakdown

#### `config.py` - Configuration Management (Multi-Profile Architecture)

**Core Data Structures**:

- `AppType` enum: `TP_VIRTUAL`, `ZWIFT`, `MYWHOOSH`, `CUSTOM` for trainer app types
- `Profile` dataclass: Individual profile configuration
    - `name`: Unique profile identifier
    - `app_type`: Trainer app type (AppType enum)
    - `garmin_username`: Garmin account username
    - `garmin_password`: Garmin account password
    - `fitfiles_path`: Path to FIT files directory
- `Config` dataclass: Multi-profile container
    - `profiles`: List of Profile objects
    - `default_profile`: Optional default profile name

**Configuration Management**:

- `ConfigManager` class: Handles config file I/O, validation, and auto-migration
    - `_load_config()`: Loads or creates configuration, auto-migrates legacy format
    - `save_config()`: Persists configuration to disk
    - `is_valid()`: Validates configuration completeness
    - `migrate_legacy_config()`: Converts v1.2.4 single-profile to multi-profile format
- `ProfileManager` class: CRUD operations for profile management
    - `create_profile()`: Create new profile with validation
    - `get_profile()`: Retrieve profile by name
    - `update_profile()`: Modify existing profile
    - `delete_profile()`: Remove profile with safety checks
    - `set_default_profile()`: Set default profile
    - `list_profiles()`: Get all profiles

**TUI Components**:

- `display_profiles_table()`: Rich table display of profiles
- `interactive_menu()`: Questionary-based menu system
- Profile creation wizard: App-first flow (select app → auto-detect → credentials → name)
- Profile edit wizard: Field-specific editing
- Profile deletion wizard: Confirmation with safety checks
- Set default profile wizard: Interactive selection

**Utilities**:

- `get_garth_dir(profile_name)`: Profile-specific credential isolation
- `PathEncoder`: Custom JSON encoder for Path and Enum objects
- Stored in platform-specific user config directory (via `platformdirs`) as `.config.json`
- Auto-detection via `app_registry.py` for TPV, Zwift, MyWhoosh directories

#### `fit_editor.py` - FIT File Editing

- `FitEditor` class: Main editor with logging filter for fit_tool warnings
    - `edit_fit()`: Main function that reads, modifies, and saves FIT files
    - `rewrite_file_id_message()`: Converts FileIdMessage to Garmin Edge 830 format
    - `strip_unknown_fields()`: Handles unknown field definitions to prevent file corruption
    - `_should_modify_manufacturer()`: Determines if manufacturer should be changed
    - `_should_modify_device_info()`: Determines if device info should be changed
    - `get_date_from_fit()`: Extracts creation date from FIT file
    - `print_message()`: Debug output for FIT messages
- `FitFileLogFilter`: Custom logging filter to suppress noisy fit_tool warnings
- Device info messages are rewritten to Garmin Edge 830
- *Activity data is always preserved* (records, laps, sessions) - only modifies device metadata
- Special handling for Activity messages (reordered to end for COROS compatibility)

#### `app_registry.py` - Trainer App Detection System

**AppDetector ABC**: Abstract base class defining the detector interface

- `get_display_name()`: Human-readable app name for UI
- `get_default_path()`: Platform-specific FIT files directory detection
- `validate_path()`: Path validation for the specific app

**Concrete Detectors**:

- `TPVDetector`: TrainingPeaks Virtual directory detection
    - macOS: `~/TPVirtual/<user_id>/FITFiles`
    - Windows: `~/Documents/TPVirtual/<user_id>/FITFiles`
    - Linux: User prompt (no standard path)
    - Uses `TPV_DATA_PATH` environment variable override
- `ZwiftDetector`: Zwift activities directory detection
    - macOS: `~/Documents/Zwift/Activities/`
    - Windows: `%USERPROFILE%\Documents\Zwift\Activities\`
    - Linux: Wine/Proton path detection
- `MyWhooshDetector`: MyWhoosh data directory detection
    - macOS: Epic container path scanning
    - Windows: AppData package directory scanning
    - Linux: User prompt (not officially supported)
- `CustomDetector`: Manual path specification for unsupported apps

**Registry System**:

- `APP_REGISTRY`: Dictionary mapping `AppType` → detector class
- `get_detector(app_type)`: Factory function for detector instances
- Extensible design: Add new apps by implementing AppDetector and registering

#### `app.py` - Main Application

- CLI argument parsing and validation (using `argparse`)
- **Multi-Profile Support**: New CLI arguments
    - `--profile/-p`: Use specific profile for operation
    - `--list-profiles`: Display all configured profiles
    - `--config-menu`: Launch interactive profile management
- `select_profile()`: Profile selection logic (arg → default → prompt)
- `upload()`: Garmin Connect upload with OAuth authentication via `garth` (now accepts `Profile` parameter)
    - Handles authentication and credential prompting
    - Caches credentials in profile-specific `.garth_{profile_name}` directories
    - Gracefully handles HTTP 409 conflicts (duplicate activities)
- `upload_all()`: Batch processes all FIT files in a directory (profile-aware)
    - Maintains `.uploaded_files.json` to track processed files
    - Creates temporary files for uploads (discarded after upload)
- `monitor()`: Watches directory for new FIT files using `watchdog` (profile-specific)
- `NewFileEventHandler`: Event handler class for monitoring mode (uses profile)
      - 5-second delay after file creation to ensure write completion
      - Automatically processes and uploads new files
- Rich console output with colored logs and tracebacks

#### `utils.py` - Utility Functions

- `apply_fit_tool_patch()`: Monkey patches fit_tool to handle malformed FIT files
- `_lenient_get_length_from_size()`: Lenient field size validation (truncates instead of raising)
- `fit_crc_get16()`: FIT file CRC-16 checksum calculation
- Required for COROS and other manufacturers with non-standard FIT files

### Supported Source Platforms

The tool recognizes and modifies FIT files from:

| Platform | Manufacturer Code | Notes |
|----------|------------------|-------|
| TrainingPeaks Virtual | `DEVELOPMENT` or `PEAKSWARE` | Formerly indieVelo |
| Zwift | `ZWIFT` | Popular virtual cycling platform |
| Wahoo devices | `WAHOO_FITNESS` | Wahoo bike computers |
| Hammerhead Karoo | `HAMMERHEAD` | Karoo bike computers |
| MyWhoosh | `331` | Not in `fit_tool`'s enum |
| COROS | `COROS` | Requires `fit_tool` patch for malformed fields |

### Logging and Output

- Uses `rich` library for formatted console output (configured in `app.py`)
- `RichHandler` for colored, timestamped logs with traceback support
- Custom `FitFileLogFilter` in `fit_editor.py` to suppress fit_tool's "actual:" warnings
- Debug mode (`-v`) provides detailed message-by-message processing logs
- Separate log level configuration for different modules (urllib3, oauth1_auth, watchdog, asyncio, etc.)


## 📚 Extensibility

### Adding New Trainer Apps

The architecture is designed to be extensible. To add support for a new trainer app:

1. **Add enum value**: Add to `AppType` enum in `config.py`
2. **Create detector**: Implement `AppDetector` subclass in `app_registry.py`
3. **Register detector**: Add to `APP_REGISTRY` dictionary
4. **Done!**: App automatically appears in creation menu

### Example: Adding Rouvy Support

```python
# 1. Add to AppType enum
class AppType(str, Enum):
    ROUVY = "rouvy"

# 2. Create detector class
class RouvyDetector(AppDetector):
    def get_display_name(self) -> str:
        return "Rouvy"
    
    def get_default_path(self) -> Path | None:
        # Implement platform-specific detection
        pass
    
    def validate_path(self, path: Path) -> bool:
        # Implement path validation
        pass

# 3. Register in APP_REGISTRY
APP_REGISTRY = {
    # ... existing entries
    AppType.ROUVY: RouvyDetector,
}
```

## Important Implementation Notes

### FIT File Structure

!!! warning "Critical Information"
    FIT files contain a series of messages (records). Each data message must be preceded by a definition message.

When rewriting messages, always write:
```python
DefinitionMessage.from_data_message(message)
```
then the message itself.

`FitFileBuilder(auto_define=True)` handles definition messages automatically when `add()` is called.

### Edge 830 Simulation

The tool specifically emulates a **Garmin Edge 830** with these values:

- **Manufacturer**: 1 (`GARMIN`)
- **Product**: 3122 (`EDGE_830`)
- **Software version**: 975 (in `FileCreatorMessage`)
- **Hardware version**: 255

### File Naming Convention

Modified files are saved as `{original_stem}_modified.fit` unless uploading in batch mode (which uses temp files).

### Platform Detection

The tool auto-detects TrainingPeaks Virtual user directories on:

- **macOS**: `~/TPVirtual`
- **Windows**: `~/Documents/TPVirtual`
- **Linux**: Prompts user for path (no auto-detection)

Override with `TPV_DATA_PATH` environment variable.

## Testing

### Quick Start

```bash
# Run all tests
python3 run_tests.py

# Run with coverage (HTML report)
python3 run_tests.py --html
```

### Test Suite Overview

The test suite includes **53+ tests** with **100% code coverage** for all major functionality.

#### Test File Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── test_fit_editor.py       # FIT editing tests (32 tests)
├── test_config.py           # Configuration tests (55 tests)
├── test_app_registry.py     # NEW: App registry and detector tests (28 tests)
├── test_app.py              # Application and upload tests (30 tests)
├── test_utils.py            # Utility function tests
└── files/                   # Test FIT files from various platforms
    ├── tpv_20250111.fit
    ├── tpv_20251120.fit
    ├── zwift_20250401.fit
    ├── mywhoosh_20260111.fit
    ├── karoo_20251119.fit
    └── coros_20251118.fit
```

### Test Isolation

All tests should be **completely isolated** from a real environment:

- ✅ Config directories redirected to temporary locations
- ✅ Cache directories use temp space
- ✅ No network calls (all external services mocked)
- ✅ Automatic cleanup after each test
- ✅ Safe to run in parallel

The `isolate_config_dirs` autouse fixture in `conftest.py` ensures that no test ever touches:

- Your real Garmin credentials
- Your actual FIT files
- Your user configuration directory
- Your system cache

### Test Fixtures and Helpers

The test suite uses shared fixtures in `conftest.py` to reduce duplication:

#### Shared Mock Classes

- **`MockQuestion`**: Mock for questionary interactive prompts
- **`MockGarthHTTPError`**: Configurable HTTP error mock with status codes
- **`MockGarthException`**: Standard Garth exception for auth flow testing

#### Shared Fixtures

- **`mock_garth_basic`**: Basic Garmin Connect mock for successful operations
- **`mock_garth_with_login`**: Garmin mock requiring authentication
- **`isolate_config_dirs`** (autouse): Automatically isolates all tests from real user directories
- **`temp_dir`**: Creates temporary directories for test outputs
- **`mock_config_file`**: Creates mock configuration files

### Mocking Strategy

#### External Services

- **Garmin Connect** (`garth`): Mocked using `sys.modules` patching with shared fixtures
- **User prompts** (`questionary`): Mocked using `MockQuestion` helper class
- **File system** (`platformdirs`): Automatically redirected to temp directories via `isolate_config_dirs`

!!! note "Why sys.modules for garth?"
    The `garth` library is imported inside functions (lazy import), so we use `patch.dict('sys.modules')` to inject mock modules that get imported at runtime.

### Running Tests

#### Using the Helper Script

```bash
# Basic usage
python3 run_tests.py

# With coverage
python3 run_tests.py --coverage

# HTML coverage report
python3 run_tests.py --html

# Verbose output
python3 run_tests.py -v

# Specific test file
python3 run_tests.py tests/test_fit_editor.py

# Specific test
python3 run_tests.py tests/test_fit_editor.py::TestFitEditor::test_edit_tpv_fit_file

# Combined options
python3 run_tests.py --coverage --html -v
```

#### Using pytest Directly

```bash
# Run all tests
uv run pytest tests/

# With coverage
uv run pytest tests/ --cov=fit_file_faker --cov-report=html

# Verbose
uv run pytest tests/ -v
```

### Continuous Integration

The test suite runs automatically on GitHub Actions for:

- **Python versions**: 3.12, 3.13, 3.14
- **Operating systems**: Ubuntu, macOS, Windows
- **Triggers**: Push to main/develop/refactor branches, pull requests

Workflow file: `.github/workflows/test.yml`

Coverage reports are uploaded to Codecov on successful Ubuntu + Python 3.12 runs.

### Adding New Tests

When adding support for a new platform:

1. Add the FIT file to `tests/files/` (sanitize it of any personally identifiable information)
2. Create a fixture in `conftest.py`:
   ```python
   @pytest.fixture
   def new_platform_fit_file(test_files_dir):
       return test_files_dir / "new_platform.fit"
   ```
3. Add a test in `test_fit_editor.py`:
   ```python
   def test_edit_new_platform_fit_file(self, fit_editor, new_platform_fit_file, temp_dir):
       output_file = temp_dir / "new_platform_modified.fit"
       result = fit_editor.edit_fit(new_platform_fit_file, output=output_file)

       assert result == output_file
       assert output_file.exists()

       # Verify modifications
       modified_fit = FitFile.from_file(str(output_file))
       for record in modified_fit.records:
           if isinstance(record.message, FileIdMessage):
               assert record.message.manufacturer == Manufacturer.GARMIN.value
   ```

### Test Best Practices

1. **Always use fixtures** for test data (don't hardcode paths)
2. **Mock external services** (no real network calls)
3. **Use temp directories** for output files
4. **Test both success and failure** paths
5. **Keep tests independent** (no shared state)
6. **Use descriptive test names** that explain what's being tested
7. **Verify behavior, not implementation** (test outcomes, not internals)

## Contributing

We welcome contributions! Here's how to get started:

### Contribution Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Run tests: `python3 run_tests.py --coverage`
5. Run linting: `ruff check . && ruff format .`
6. Commit your changes following [conventional commits](https://www.conventionalcommits.org/)
7. Push to your fork: `git push origin feature/your-feature-name`
8. Open a Pull Request

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/) for automatic changelog generation. Commit messages are **automatically validated** by gitlint through pre-commit hooks.

**Required format**:
```
<type>: <description>

[optional body]

[optional footer]
```

**Allowed types**:

- `feat:` New features
- `minor-feat:` New minor features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions or modifications
- `refactor:` Code refactoring
- `chore:` Maintenance tasks
- `ci:` CI/CD changes
- `build:` Build system changes
- `perf:` Performance improvements
- `style:` Code style changes
- `revert:` Revert previous commits

**Example**:
```
feat: add support for COROS FIT files

Add manufacturer code recognition and device ID modification for COROS
devices to enable Garmin Connect Training Effect calculations.
```

!!! tip "Commit Message Validation"
    The pre-commit hook will reject commits that don't follow the conventional commits format. The hook configuration is in `.gitlint` and validates:

    - Type is one of the allowed types
    - Format follows `type(optional-scope): description`
    - Title is ≤100 characters
    - Body is optional (not required)

### Code Style

- Follow PEP 8
- Use `ruff` for formatting and linting
- Maximum line length: 100 characters (configured in `pyproject.toml`)
- Use type hints where appropriate

### Pull Request Guidelines

- Provide a clear description of the changes
- Reference any related issues
- Ensure all tests pass
- Maintain 100% code coverage
- Update documentation if needed

## Release Process

Releases are automated via `.github/workflows/publish_and_release.yml`:

1. All pushes build the package and publish to TestPyPI
2. Tag pushes (e.g., `v1.2.3`) trigger PyPI publication and GitHub Release creation
3. Version is defined in `pyproject.toml` and must be manually updated before tagging

### To Release a New Version

1. **Update version** in `pyproject.toml`:
   ```toml
   version = "1.2.5"
   ```

2. **Commit the version change**:
   ```bash
   git add pyproject.toml
   git commit -m "chore: bump version to 1.2.5"
   ```

3. **Create and push a git tag with a detailed message**:
   ```bash
   git tag v1.2.5 -m "Release v1.2.5: Add support for new platforms

   This release includes support for MyWhoosh and COROS devices, along with
   improved error handling and comprehensive test coverage."
   git push origin main
   git push origin v1.2.5
   ```

    !!! tip "Tag Messages in Changelog"
        Detailed tag messages (using the `-m` flag) will be rendered in the auto-generated changelog and GitHub Release notes. Use this to provide release highlights, breaking changes, or upgrade instructions that won't fit in individual commit messages.

4. **Automated steps** (handled by GitHub Actions):
    - Build package
    - Publish to PyPI
    - Create GitHub Release
    - Generate changelog
    - Deploy documentation

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.x.x): Breaking changes
- **MINOR** (x.1.x): New features (backwards-compatible)
- **PATCH** (x.x.1): Bug fixes (backwards-compatible)

## Documentation

The project has a comprehensive documentation site built with MkDocs Material and hosted on GitHub Pages.

### Documentation Site

- **URL**: [https://jat255.github.io/Fit-File-Faker/](https://jat255.github.io/Fit-File-Faker/)
- **Framework**: [MkDocs](https://www.mkdocs.org/) with [Material theme](https://squidfunk.github.io/mkdocs-material/)
- **Deployment**: Automated via GitHub Actions to `gh-pages` branch
- **Changelog**: Auto-generated from git commits using [git-cliff](https://git-cliff.org/)

### Documentation Structure

```
docs/
├── index.md              # Home page (user guide, from README.md)
├── developer-guide.md    # Developer guide (this file)
├── changelog.md          # Auto-generated changelog
└── assets/               # Images, custom CSS, and other assets
```

### Building Documentation Locally

#### Prerequisites

Install documentation dependencies:

```bash
# Using uv (recommended)
uv sync --group docs

# Using pip
pip install mkdocs mkdocs-material mkdocs-minify-plugin
```

#### Local Development

**Option 1: Using the build script (Recommended)**

The `build_docs.sh` script generates the complete changelog (including historical releases) and builds/serves the documentation, mirroring the CI/CD workflow:

```bash
# Build static documentation with changelog
./build_docs.sh

# Serve with live reload for development
./build_docs.sh serve

# Opens at http://127.0.0.1:8000
# Changes to docs/ files will automatically reload the browser
```

**Option 2: Using mkdocs directly**

```bash
# Serve documentation locally with live reload
uv run mkdocs serve

# Opens at http://127.0.0.1:8000
# Changes to docs/ files will automatically reload the browser
```

!!! note "Changelog Generation"
    When using `mkdocs serve` directly, the changelog won't be regenerated. Use `./build_docs.sh serve` to include the latest changelog in your local preview.

#### Build Static Site

```bash
# Using the build script (includes changelog generation)
./build_docs.sh

# Or build directly with mkdocs (without changelog update)
mkdocs build

# The generated site can be found in the site/ directory
```

#### Deploy to GitHub Pages

```bash
# Deploy to gh-pages branch (requires push access)
mkdocs gh-deploy
```

!!! warning "Manual Deployment"
    Manual deployment via `mkdocs gh-deploy` is rarely needed since documentation is automatically deployed by GitHub Actions. Only use this if the automated deployment fails.

### Documentation Automation

Documentation automatically rebuilds and deploys in two scenarios:

#### 1. Documentation Changes

When changes are pushed to `main` branch that affect:
- `docs/**` (any documentation files)
- `mkdocs.yml` (MkDocs configuration)
- `pyproject.toml` (contains git-cliff changelog generation config)

**Workflow**: `.github/workflows/docs.yml`

This workflow:

1. Checks out the repository
2. Sets up Python and installs dependencies
3. Builds the documentation with `mkdocs build`
4. Deploys to GitHub Pages (`gh-pages` branch)

#### 2. Release Process

After a new release is created (when a tag like `v1.2.5` is pushed):

**Workflow**: `.github/workflows/publish_and_release.yml`

This workflow:

1. Builds and publishes the package to PyPI
2. Creates a GitHub Release
3. Generates the changelog using `git-cliff`
4. Deploys updated documentation

### Changelog Generation

The changelog is automatically generated using [git-cliff](https://git-cliff.org/) based on conventional commit messages.

#### Configuration

Changelog generation is configured in `pyproject.toml` under the `[tool.git-cliff.*]` sections:

- **Commit parsers**: Categorize commits by type (feat, fix, docs, etc.)
- **Format**: Markdown with links to commits and releases
- **Sections**: Features, Bug Fixes, Documentation, etc.
- **Skipped tags**: Old releases (v1.0.0 - v1.2.4) that predate conventional commits

#### Historical Releases

The project adopted conventional commits starting with v1.3.0. Earlier releases (v1.0.0 - v1.2.4) don't follow this format, so they are handled specially:

**Configuration in `pyproject.toml`:**
```toml
[tool.git-cliff.git]
# Skip old tags that predate conventional commits
skip_tags = "v0.0.1-beta.1|v1.0.0|v1.0.1|v1.0.2|v1.0.3|v1.1.0|v1.1.1|v1.2.0|v1.2.1|v1.2.2|v1.2.3|v1.2.4"
```

**Workflow integration:**

1. Git-cliff generates the changelog from conventional commits only (v1.3.0+)
2. The historical changelog from `docs/.changelog_pre_1.3.0.md` is appended
3. Result: Complete changelog with both new and legacy releases

This approach:
- ✅ Keeps the generated changelog clean with conventional commits
- ✅ Preserves historical release information
- ✅ Works automatically in both CI/CD and local builds (`./build_docs.sh`)

#### Conventional Commits

For commits to appear in the changelog, they must follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>: <description>

[optional body]

[optional footer]
```

**Types**:

- `feat:` - New features
- `minor-feat:` - New minor features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions or modifications
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks
- `ci:` - CI/CD changes
- `build:` - Build system changes

**Example**:
```
feat: add support for COROS FIT files

Add lenient field size validation to handle malformed FIT files from
COROS devices. This enables Training Effect calculations for COROS
activities uploaded to Garmin Connect.
```

#### Manual Changelog Generation

To generate the changelog locally (for testing):

```bash
# Install git-cliff
cargo install git-cliff
# or
brew install git-cliff

# Generate changelog (reads config from pyproject.toml automatically)
git cliff --output docs/changelog.md

# Generate changelog for specific version range
git cliff --output docs/changelog.md v1.3.0..HEAD
```

!!! note "Github API limits"
    `git cliff` will make requests to the Github API to get information about various
    bits of information, and without authentication, the API limit is very low, so you
    may see errors such as:
    ```
    thread 'main' (37956221) panicked at git-cliff-core/src/changelog.rs:558:18:
    Could not get github metadata: HttpClientError(reqwest::Error { kind: Status(403, None), url: "https://api.github.com/repos/jat255/Fit-File-Faker/commits?per_page=100&page=0&sha=v1.2.3" })
    note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
    ```
    To work around this, you can either generate a Github access token and provide it
    via the `GITHUB_TOKEN` environment variable, or to do this dynamically with the
    [Github CLI](https://cli.github.com/), you can run a command such as
    `$ gh auth token | GITHUB_TOKEN=$(cat) git cliff v1.0.2..v1.2.4`

### Documentation Best Practices

When contributing to documentation:

1. **Write in Markdown**: Use standard Markdown with MkDocs Material extensions
2. **Use admonitions**: Highlight important information with note/warning/tip boxes
   ```markdown
   !!! note "Important Information"
       This is a note with important information.
   ```
3. **Code blocks**: Always specify language for syntax highlighting
   ````markdown
   ```python
   def example():
       pass
   ```
   ````
   will render as:
   ```python
   def example():
       pass
   ```

4. **Link to code**: Use relative links for internal documentation
5. **Test locally**: Always run `mkdocs serve` to preview changes
6. **Keep synchronized**: Ensure README.md and docs/index.md stay in sync for the user guide

### MkDocs Configuration

The site is configured in `mkdocs.yml`:

```yaml
site_name: FIT File Faker
theme:
  name: material
  # ... theme configuration

nav:
  - Home: index.md
  - Developer Guide: developer-guide.md
  - API Reference: api.md
  - Changelog: changelog.md

plugins:
  - search                      # Built-in search
  - minify:                     # Minify HTML/CSS/JS
    ...
  - autorefs                    # cross reference support
  - mkdocstrings:               # auto generation of API docs
    ...
```

Key features:

- **Material theme**: Modern, responsive design
- **Search**: Built-in search functionality
- **Minification**: Optimized HTML/CSS/JS output
- **Code highlighting**: Syntax highlighting for all code blocks
- **Navigation**: Organized sidebar navigation

### Troubleshooting Documentation

#### Local build fails

```bash
# Ensure dependencies are installed
uv sync --group docs

# Clear MkDocs cache
rm -rf site/

# Rebuild
mkdocs build
```

#### Changes not appearing on GitHub Pages

1. Check the GitHub Actions workflow status
2. Ensure the `gh-pages` branch exists
3. Verify GitHub Pages is enabled in repository settings
4. Wait a few minutes for deployment to propagate

#### Changelog not updating

1. Ensure commits follow conventional commit format
2. Check git-cliff configuration in `pyproject.toml` under `[tool.git-cliff.*]` sections
3. Verify the release workflow completed successfully

## Resources

- **GitHub Repository**: [jat255/Fit-File-Faker](https://github.com/jat255/Fit-File-Faker)
- **PyPI Package**: [fit-file-faker](https://pypi.org/project/fit-file-faker/)
- **Issue Tracker**: [GitHub Issues](https://github.com/jat255/Fit-File-Faker/issues)
- **pytest Documentation**: [https://docs.pytest.org/](https://docs.pytest.org/)
- **GitHub Actions**: `.github/workflows/`

## Getting Help

If you need help:

1. Check the [documentation](index.md)
2. Search [existing issues](https://github.com/jat255/Fit-File-Faker/issues)
3. Create a [new issue](https://github.com/jat255/Fit-File-Faker/issues/new/choose)

!!! note
    As this is a side-project provided for free, support times may vary 😅.
