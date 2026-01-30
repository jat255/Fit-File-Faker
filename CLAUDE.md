# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fit File Faker is a Python tool that modifies FIT (Flexible and Interoperable Data Transfer) files to make them appear as if they came from Garmin devices. The primary use case is enabling Garmin Connect's "Training Effect" calculations for activities from non-Garmin sources like TrainingPeaks Virtual (formerly indieVelo), Zwift, and other cycling platforms.

Users can configure which Garmin device to emulate (Edge 1050, Fenix 8, Forerunner 965, etc.) with per-profile settings. The tool supports 70+ modern Garmin devices with appropriate firmware versions.

The tool is distributed as a Python package via PyPI as `fit-file-faker`.

## Commands

### Development Setup
```bash
# Install dependencies with uv (preferred)
uv sync

# Or use pip in a virtual environment
python -m venv .venv
source .venv/bin/activate
pip install .
```

### Build and Distribution
```bash
# Build the package
uv build

# Install locally for testing
pip install -e .
```

### Running the Tool
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

## Architecture

### Package Structure
The application is organized as a modular Python package (`fit_file_faker/`) with ~998 total lines across five files:

```
fit_file_faker/
├── __init__.py           # Package initialization (1 line)
├── app.py                # Main application, CLI, uploads, monitoring (356 lines)
├── config.py             # Configuration management (225 lines)
├── fit_editor.py         # FIT file editing core logic (313 lines)
└── utils.py              # Utility functions and monkey patches (103 lines)
```

**Entry Point**: `fit_file_faker.app:run` (defined in `pyproject.toml`)

**Updated Package Structure** (with multi-profile support):
```
fit_file_faker/
├── __init__.py           # Package initialization (1 line)
├── app.py                # Main application, CLI, uploads, monitoring (550 lines)
├── app_registry.py       # NEW: Trainer app detection system (305 lines)
├── config.py             # Configuration management (750 lines)
├── fit_editor.py         # FIT file editing core logic (313 lines)
└── utils.py              # Utility functions and monkey patches (103 lines)
```

### Core Workflow
1. **Read FIT file**: Uses the `fit_tool` library to parse binary FIT files
2. **Apply fit_tool patch**: Applies monkey patch from `utils.py` to handle malformed FIT files (e.g., COROS)
3. **Identify device messages**: Locates `FileIdMessage`, `FileCreatorMessage`, and `DeviceInfoMessage` records
4. **Rewrite manufacturer/product IDs**: Changes manufacturer codes from DEVELOPMENT (255), ZWIFT, WAHOO_FITNESS, PEAKSWARE, HAMMERHEAD, COROS, or MYWHOOSH (331) to GARMIN (1) with Edge 830 product ID (3122)
5. **Rebuild FIT file**: Uses `FitFileBuilder` to reconstruct the file with modified messages
6. **Upload (optional)**: Authenticates to Garmin Connect via `garth` library and uploads the modified file

### Module Breakdown

**`config.py` - Configuration Management**
- **Multi-Profile Architecture**: Supports multiple profiles with different Garmin accounts and trainer apps
- `AppType` enum: TP_VIRTUAL, ZWIFT, MYWHOOSH, CUSTOM for trainer app types
- `Profile` dataclass: Holds profile-specific settings (name, app_type, credentials, fitfiles_path, manufacturer, device, serial_number)
- `Config` dataclass: Contains `profiles: list[Profile]` and `default_profile: str | None`
- `ConfigManager`: Handles config file I/O, validation, auto-migration from v1.2.4 format
- `ProfileManager`: CRUD operations for profile management (create, read, update, delete, set_default)
- `migrate_legacy_config()`: Auto-converts single-profile configs to multi-profile format
- `get_garth_dir(profile_name)`: Profile-specific credential isolation
- Stored in platform-specific user config directory (via `platformdirs`) as `.config.json`
- **Auto-detection**: Platform-specific directory detection for TPV, Zwift, MyWhoosh via `app_registry.py`
- **TUI**: Rich-based interactive menu system for profile management

**Supplemental Device Registry** (in `config.py`):
- `GarminDeviceInfo` dataclass: Metadata for modern Garmin devices (name, product_id, category, year_released, is_common, description, software_version, software_date)
- `SUPPLEMENTAL_GARMIN_DEVICES`: Registry of 43 modern devices (2019-2026) to supplement outdated fit_tool enum
- `get_supported_garmin_devices(show_all)`: Returns device list for picker UI, merges fit_tool + supplemental
- **Two-level device picker**: Common devices (11) shown first, "View all devices" option shows full catalog (70+)
- **Device categories**: bike_computer, multisport_watch, trainer
- **Firmware data source**: Extracted from http://gpsinformation.net/allory/test/garfeat_index.htm
- **Device reference CSV**: `docs/reference/FitSDK_21.188.00_device_ids.csv` contains product IDs, firmware versions, and release dates
- **FIT version format**: Integer where last 2 digits are decimals (e.g., 2922 = v29.22, 975 = v9.75)

**`fit_editor.py` - FIT File Editing**
- `FitEditor` class: Main editor with logging filter for fit_tool warnings
- `edit_fit()`: Main function that reads, modifies, and saves FIT files
- `rewrite_file_id_message()`: Converts FileIdMessage to Garmin Edge 830 format
- `strip_unknown_fields()`: Handles unknown field definitions to prevent file corruption
- Device info messages are similarly rewritten to Garmin Edge 830
- Preserves activity data (records, laps, sessions) - only modifies device metadata
- Special handling for Activity messages (reordered to end for COROS compatibility)

**`app_registry.py` - Trainer App Detection**
- `AppDetector` ABC: Abstract base class for trainer app detection
- `TPVDetector`: TrainingPeaks Virtual directory detection (macOS/Windows/Linux)
- `ZwiftDetector`: Zwift activities directory detection (macOS/Windows/Linux with Wine/Proton)
- `MyWhooshDetector`: MyWhoosh data directory detection (macOS container, Windows package scanning)
- `CustomDetector`: Manual path specification for unsupported apps
- `APP_REGISTRY`: Dictionary mapping `AppType` → detector class
- `get_detector(app_type)`: Factory function for detector instances
- Platform-specific auto-detection with graceful fallbacks to user prompts

**`app.py` - Main Application**
- CLI argument parsing and validation
- **Multi-Profile Support**: `--profile/-p`, `--list-profiles`, `--config-menu` arguments
- `select_profile()`: Profile selection logic (arg → default → prompt)
- `upload()`: Garmin Connect upload with OAuth authentication via `garth` (now accepts `Profile` parameter)
- `upload_all()`: Batch processes all FIT files in a directory (profile-aware)
- `monitor()`: Watches directory for new FIT files using `watchdog` (profile-specific)
- `NewFileEventHandler`: Event handler for monitoring mode (uses profile)
- Credentials cached in profile-specific cache directories (`.garth_{profile_name}` folders)
- Handles HTTP 409 conflicts (duplicate activities) gracefully
- Maintains `.uploaded_files.json` to track processed files

**`utils.py` - Utility Functions**
- `apply_fit_tool_patch()`: Monkey patches fit_tool to handle malformed FIT files
- `_lenient_get_length_from_size()`: Lenient field size validation (truncates instead of raising)
- `fit_crc_get16()`: FIT file CRC-16 checksum calculation
- Required for COROS and other manufacturers with non-standard FIT files

### Multi-Profile Workflow

**Profile Selection Priority**:
1. `--profile/-p` CLI argument (explicit selection)
2. `default_profile` from config (if set)
3. Interactive prompt (if multiple profiles exist)
4. Error if no profiles configured

**Profile Management Commands**:
- `fit-file-faker --config-menu`: Launch interactive TUI for profile CRUD operations
- `fit-file-faker --list-profiles`: Display all configured profiles
- `fit-file-faker --profile <name> <command>`: Execute command with specific profile

**Profile Creation Wizard** (App-First Flow):
1. Select trainer app type (TPV, Zwift, MyWhoosh, Custom)
2. Auto-detect or manually specify FIT files directory
3. Enter Garmin username and password
4. Name the profile (suggested based on app type)
5. Confirm and save

### Supported Source Platforms
The tool recognizes and modifies FIT files from:
- **TrainingPeaks Virtual** (manufacturer: DEVELOPMENT or PEAKSWARE) - Formerly indieVelo
- **Zwift** (manufacturer: ZWIFT) - Full platform support with auto-detection
- **Wahoo devices** (manufacturer: WAHOO_FITNESS)
- **Hammerhead Karoo** (manufacturer: HAMMERHEAD)
- **MyWhoosh** (manufacturer code: 331, not in fit_tool's enum) - Container/package detection
- **COROS** (manufacturer: COROS) - Requires fit_tool patch for malformed fields

**Auto-Detection Support**:
- TrainingPeaks Virtual: macOS (`~/TPVirtual`), Windows (`~/Documents/TPVirtual`), Linux (prompt)
- Zwift: macOS (`~/Documents/Zwift/Activities`), Windows (`%USERPROFILE%\Documents\Zwift\Activities`), Linux (Wine/Proton paths)
- MyWhoosh: macOS (Epic container), Windows (AppData package scanning), Linux (not officially supported)

### Logging and Output
- Uses `rich` library for formatted console output (configured in `app.py`)
- `RichHandler` for colored, timestamped logs
- Custom `FitFileLogFilter` in `fit_editor.py` to suppress fit_tool's "actual:" warnings
- Debug mode (`-v`) provides detailed message-by-message processing logs
- Separate loggers for different modules (urllib3, oauth1_auth, watchdog, etc.)

## Important Implementation Notes

### FIT File Structure
- FIT files contain a series of messages (records)
- Each data message must be preceded by a definition message
- When rewriting messages, always write: `DefinitionMessage.from_data_message(message)` then the message itself
- `FitFileBuilder(auto_define=True)` handles definition messages automatically when `add()` is called

### Device Simulation
The tool emulates Garmin devices by rewriting manufacturer and product IDs in FIT files. The specific device can be configured per-profile.

**Default device** (if not configured):
- Manufacturer: 1 (GARMIN)
- Product: 3122 (EDGE_830)
- Software version: 975 (v9.75 in FIT format)
- Hardware version: 255

**Supported devices**: 70+ devices from supplemental registry and fit_tool library, including:
- Modern bike computers (Edge 1050, 1040, 840, 540, etc.)
- Multisport watches (Fenix 8, Fenix 7, Epix Gen 2, etc.)
- Running watches (Forerunner 965, 955, 265, 255, etc.)
- Training apps (Tacx Training App variants)

**Custom device IDs**: Users can enter any numeric device ID manually during profile configuration.

**Firmware version maintenance**: Versions sourced from gpsinformation.net can be updated via extraction scripts:
- `./extract_firmware_versions.sh` - Fetches latest firmware data from gpsinformation.net
- `python3 update_firmware_csv.py` - Updates CSV with extracted firmware versions/dates

### File Naming Convention
Modified files are saved as `{original_stem}_modified.fit` unless uploading in batch mode (which uses temp files).

### Platform Detection
The tool auto-detects TrainingPeaks Virtual user directories on:
- macOS: `~/TPVirtual`
- Windows: `~/Documents/TPVirtual`
- Linux: Prompts user for path (no auto-detection)

Override with `TPV_DATA_PATH` environment variable.

## Documentation

The project has a comprehensive documentation site built with MkDocs Material and hosted on GitHub Pages.

### Documentation Structure

```
docs/
├── index.md              # Home page (user guide, from README.md)
├── developer-guide.md    # Developer guide (testing, architecture)
├── changelog.md          # Auto-generated changelog
└── assets/               # Images, custom CSS
```

### Documentation Site

- **URL**: https://jat255.github.io/Fit-File-Faker/
- **Framework**: MkDocs with Material theme
- **Deployment**: Automated via GitHub Actions to gh-pages branch
- **Changelog**: Auto-generated from git commits using git-cliff

### Building Documentation Locally

```bash
# Install docs dependencies
uv sync --group docs

# Serve documentation locally (http://127.0.0.1:8000)
mkdocs serve

# Build static site
mkdocs build

# Deploy to GitHub Pages (requires push access)
mkdocs gh-deploy
```

### Documentation Automation

Documentation automatically rebuilds and deploys:
1. On push to main when `docs/`, `mkdocs.yml`, or `pyproject.toml` changes (via `.github/workflows/docs.yml`)
2. On release (after creating GitHub Release, via `.github/workflows/publish_and_release.yml`)

The changelog is automatically generated from conventional commits and updated on each release.

## Testing Strategy

### Test Suite Structure

The test suite is organized into four test files covering all modules:

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── test_fit_editor.py       # FIT editing tests (15 tests)
├── test_config.py           # Configuration tests (21 tests, 100% coverage)
├── test_app.py              # Application and upload tests (32 tests, 100% coverage)
├── test_utils.py            # Utility function tests (~29 lines)
└── files/                   # Test FIT files from various platforms
    ├── tpv_20250111.fit
    ├── tpv_20251120.fit
    ├── zwift_20250401.fit
    ├── mywhoosh_20260111.fit
    ├── karoo_20251119.fit
    └── coros_20251118.fit
```

**Total**: 53+ tests with **100% code coverage** for `config.py` and `app.py`.

### Running Tests

```bash
# Run all tests (use -n auto for parallel execution)
python3 run_tests.py

# With coverage report (HTML)
python3 run_tests.py --html

# Verbose output
python3 run_tests.py -v

# Using pytest directly (with parallel execution)
uv run pytest tests/ -n auto

# With coverage
uv run pytest tests/ -n auto --cov=fit_file_faker --cov-report=term-missing
```

### Continuous Integration

The CI pipeline (`.github/workflows/test.yml`) tests on:
- **Python versions**: 3.12, 3.13, 3.14
- **Operating systems**: Ubuntu, macOS, Windows
- **Triggers**: Push to main/develop/refactor branches, pull requests

Coverage reports are uploaded to Codecov on successful Ubuntu + Python 3.12 runs.

### Test Features

- ✅ **Complete isolation**: All tests use temporary directories (no real config touched)
- ✅ **Mocked services**: Garmin Connect (`garth`) and user prompts (`questionary`)
- ✅ **Shared fixtures**: `conftest.py` provides reusable fixtures to reduce duplication
- ✅ **Platform coverage**: Tests run on all supported platforms (TPV, Zwift, MyWhoosh, Karoo, COROS)

See `TESTING.md` for comprehensive documentation.

### Development Workflow

**IMPORTANT: Commit Message Format**

ALL commits MUST follow the [Conventional Commits](https://www.conventionalcommits.org/) format:
- Format: `<type>: <description>` (e.g., `feat: add new feature`, `fix: resolve bug`)
- Allowed types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `build`, `perf`, `style`, `revert`, `plan`
- This is enforced by pre-commit hooks (commitlint) and required for automatic changelog generation
- **Never** create commits that don't follow this format

When making changes:
1. Run tests locally: `python3 run_tests.py --html`
2. Check coverage report in `htmlcov/index.html`
3. Use the `-d` (dryrun) flag for manual testing without creating files or uploading
4. Run linting: `ruff check . && ruff format .`
5. **Ensure all commits follow conventional commit format** (enforced by pre-commit hooks)

## Release Process

Releases are automated via `.github/workflows/publish_and_release.yml`:
1. All pushes build the package and publish to TestPyPI
2. Tag pushes (e.g., `v1.2.3`) trigger PyPI publication and GitHub Release creation
3. Version is defined in `pyproject.toml` and must be manually updated before tagging

To release a new version:

**Option 1: Using the release script (Recommended)**
```bash
./release.sh 2.0.1 "Fix changelog generation and dependencies"
```

**Option 2: Manual release**
1. Update version in `pyproject.toml`
2. Commit: `git commit -am "chore: bump version to 1.2.4"`
3. Tag: `git tag v1.2.4 -m "Release v1.2.4"`
4. Push: `git push origin main && git push origin v1.2.4`
