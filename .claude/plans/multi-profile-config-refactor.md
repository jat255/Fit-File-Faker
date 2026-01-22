# Multi-Profile Configuration Refactoring Plan

## Objective

Refactor Fit File Faker's configuration system from single-profile to multi-profile architecture, supporting:
- Multiple Garmin user accounts (isolated garth credentials)
- Multiple trainer apps (TrainingPeaks Virtual, Zwift, MyWhoosh) with auto-detection
- Menu-based TUI for profile management (CRUD operations)
- Backward-compatible migration from v1.2.4 single-profile format
- Extensible design for adding future trainer apps

## User Requirements Summary

- ✅ Multiple profiles with different Garmin users
- ✅ Support for TPV, Zwift, MyWhoosh with auto-detection
- ✅ Menu-based TUI using Rich framework (arrow key navigation)
- ✅ App-first configuration flow (select app → auto-detect → credentials → name)
- ✅ Full CRUD profile management
- ✅ Monitor mode uses default profile (override with `--profile` flag)
- ✅ Store app type but allow manual path override

---

## 🎯 Implementation Status

**Last Updated:** 2026-01-21

### ✅ Phase 1: Core Data Structures (COMPLETED)
**Commit:** `371c602` - feat(config): add multi-profile data structures and migration

**Deliverables:**
- ✅ AppType enum added (TP_VIRTUAL, ZWIFT, MYWHOOSH, CUSTOM)
- ✅ Profile dataclass implemented with __post_init__ conversions
- ✅ Config dataclass refactored for multi-profile support
- ✅ migrate_legacy_config() function for v1.2.4 compatibility
- ✅ ConfigManager._load_config() auto-migrates legacy configs
- ✅ PathEncoder updated to handle Enum serialization
- ✅ Config.get_profile() and get_default_profile() methods added
- ✅ 19 comprehensive tests (TestProfile, TestConfigMultiProfile, TestMigration)

**Test Results:** 19/19 passing ✅

### ✅ Phase 2: App Registry & Detection (COMPLETED)
**Commit:** `63df98e` - feat(config): add app registry with detector classes

**Deliverables:**
- ✅ app_registry.py module created with AppDetector ABC
- ✅ TPVDetector implemented (reuses existing get_tpv_folder logic)
- ✅ ZwiftDetector implemented (macOS/Windows/Linux with Wine/Proton)
- ✅ MyWhooshDetector implemented (container and package scanning)
- ✅ CustomDetector implemented (manual path specification)
- ✅ APP_REGISTRY dictionary and get_detector() factory function
- ✅ Platform-specific directory auto-detection for all apps
- ✅ 28 comprehensive tests (all detector classes + registry)

**Test Results:** 28/28 passing ✅

### ✅ Phase 3: Profile Management TUI (COMPLETED)
**Commit:** `d13bf96` - feat(config): add Rich TUI and interactive wizards

**Deliverables:**
- ✅ ProfileManager class with CRUD operations (create, read, update, delete, set_default)
- ✅ display_profiles_table() with Rich table formatting
- ✅ interactive_menu() with Questionary-based navigation
- ✅ Profile creation wizard (app-first flow: select app → auto-detect → credentials → name)
- ✅ Profile edit wizard with field selection
- ✅ Profile deletion wizard with confirmation
- ✅ Set default profile wizard
- ✅ Default profile marked with ⭐ in display
- ✅ Graceful error handling and cancellation support
- ✅ 15 comprehensive tests for ProfileManager

**Test Results:** 15/15 passing ✅

### ✅ Phase 4: Multi-Profile CLI Integration (COMPLETED)
**Commit:** `511816b` - feat(app): add multi-profile CLI integration with profile selection

**Deliverables:**
- ✅ get_garth_dir() function for profile-specific credential isolation
- ✅ Modified upload() to accept Profile parameter
- ✅ Modified upload_all() to accept and pass Profile parameter
- ✅ Updated NewFileEventHandler for profile support
- ✅ Added CLI arguments: --profile/-p, --list-profiles, --config-menu
- ✅ Implemented select_profile() with priority logic (arg → default → prompt)
- ✅ Updated monitor mode for profile selection
- ✅ All uploads use profile-specific garth directories
- ✅ 8 comprehensive tests for profile selection and CLI integration

**Test Results:** 8/8 passing ✅

### ✅ Phase 5: Documentation & Polish (COMPLETED)
**Status:** Completed
**Estimated:** 2 days

**Completed Tasks:**
- ✅ Made -s/--initial-setup alias for --config-menu (backward compatibility)
- ✅ Removed obsolete single-profile setup flow
- ✅ Updated docstrings in modified functions
- ✅ Maintained 100% test coverage for core modules
- ✅ Updated README.md with multi-profile examples and CLI usage
- ✅ Updated CLAUDE.md with new architecture and module breakdown
- ✅ Updated docs/developer-guide.md with multi-profile architecture and testing details
- ✅ Updated docs/index.md user guide with multi-profile configuration
- ✅ Created docs/profiles.md comprehensive profile guide (13.6KB)
- ✅ Added multi-profile workflow examples and use cases
- ✅ Documented extensibility pattern for new apps
- ✅ Added troubleshooting section for common issues
- ✅ Updated CLI documentation with new --profile, --list-profiles, --config-menu options
- ✅ Added migration documentation and backward compatibility notes

### 🚧 Phase 6: Testing & Validation (IN PROGRESS)
**Status:** Partial completion
**Estimated:** 2 days

**Completed Tasks:**
- ✅ All tests pass locally (135 tests total)
- ✅ 100% coverage maintained for config.py and app.py
- ✅ 95%+ coverage for app_registry.py
- ✅ Ruff linting passes
- ✅ Conventional commit format validation passes
- ✅ Documentation builds successfully (`mkdocs build`)
- ✅ All documentation links verified

**Remaining Tasks:**
- [ ] Test on Python 3.12, 3.13, 3.14 via CI
- [ ] Test on macOS, Windows, Linux via CI
- [ ] Manual testing of TUI on different terminals
- [ ] Test migration from real v1.2.4 config
- [ ] Add integration tests for end-to-end workflows
- [ ] Create test_integration_profiles.py with ~10 tests

**Overall Progress:** 5/6 phases complete (83%)
**Total Tests Added:** 135/146 (92%)
**Current Branch:** `feat/config_refactor`

---

## Architecture Overview

### New Data Structure

**Current (Single Profile):**
```python
Config(
    garmin_username: str,
    garmin_password: str,
    fitfiles_path: Path
)
```

**Proposed (Multi-Profile):**
```python
AppType(Enum):
    TP_VIRTUAL, ZWIFT, MYWHOOSH, CUSTOM

Profile(
    name: str,
    app_type: AppType,
    garmin_username: str,
    garmin_password: str,
    fitfiles_path: Path
)

Config(
    profiles: list[Profile],
    default_profile: str | None
)
```

### Key Architectural Patterns

1. **App Registry Pattern** - Each trainer app has a detector class implementing `AppDetector` ABC
2. **Garth Isolation** - Profile-specific directories: `~/.cache/FitFileFaker/.garth_{profile_name}/`
3. **Automatic Migration** - Old configs auto-migrate to "default" profile on first run
4. **TUI Library** - Questionary (already a dependency) + Rich for display
5. **Extensibility** - Adding new apps requires: enum value + detector class + registry entry

### Directory Detection Research

**TrainingPeaks Virtual (Existing):**
- macOS: `~/TPVirtual/<user_id>/FITFiles`
- Windows: `~/Documents/TPVirtual/<user_id>/FITFiles`
- Linux: User prompt

**Zwift (NEW):**
- macOS: `~/Documents/Zwift/Activities/`
- Windows: `%USERPROFILE%\Documents\Zwift\Activities\`
- Linux: `~/.wine/drive_c/.../Documents/Zwift/Activities/` or Steam Proton path

**MyWhoosh (NEW):**
- **macOS**: `~/Library/Containers/com.whoosh.whooshgame/Data/Library/Application Support/Epic/MyWhoosh/Content/Data`
- **Windows**: `~/AppData/Local/Packages/<MYWHOOSH_PREFIX>*/LocalCache/Local/MyWhoosh/Content/Data`
  - Requires scanning `Packages` directory for folders starting with MyWhoosh prefix
- **Linux**: Not officially supported by MyWhoosh (fallback to user prompt)

---

## Implementation Phases

### Phase 1: Core Data Structures ✅ (COMPLETED)

**Objectives:**
- Add `AppType` enum to `config.py`
- Add `Profile` dataclass to `config.py`
- Modify `Config` dataclass to contain `profiles: list[Profile]` and `default_profile: str`
- Implement `migrate_legacy_config()` function to auto-convert old format
- Update `ConfigManager._load_config()` to detect and migrate legacy configs
- Update `ConfigManager.save_config()` to handle new structure

**Critical Files:**
- `fit_file_faker/config.py` (lines 75-167)
  - Add enums and new dataclasses
  - Modify ConfigManager methods

**Tests to Add:**
- `tests/test_config.py`:
  - `TestProfile` class (5 tests): instantiation, validation, path conversion
  - `TestConfigMultiProfile` class (8 tests): get_profile(), get_default_profile(), multiple profiles
  - `TestMigration` class (6 tests): legacy format detection, migration correctness, edge cases

**Success Criteria:**
- Config loads both old (single) and new (multi-profile) formats
- Migration preserves all existing data in "default" profile
- Profile CRUD operations work correctly
- All tests pass with 100% coverage maintained

**Migration Example:**
```json
// OLD (v1.2.4)
{
  "garmin_username": "user@email.com",
  "garmin_password": "secret",
  "fitfiles_path": "/Users/josh/TPVirtual/abc123/FITFiles"
}

// NEW (v2.0.0) - Auto-migrated
{
  "profiles": [
    {
      "name": "default",
      "app_type": "tp_virtual",
      "garmin_username": "user@email.com",
      "garmin_password": "secret",
      "fitfiles_path": "/Users/josh/TPVirtual/abc123/FITFiles"
    }
  ],
  "default_profile": "default"
}
```

---

### Phase 2: App Registry & Detection ✅ (COMPLETED)

**Objectives:**
- Create new `app_registry.py` module
- Implement `AppDetector` abstract base class
- Implement detector classes: `TPVDetector`, `ZwiftDetector`, `MyWhooshDetector`, `CustomDetector`
- Create `APP_REGISTRY` dictionary mapping `AppType` → detector class
- Add `get_detector(app_type)` factory function
- Refactor existing TPV detection to use new `TPVDetector`

**New File:**
- `fit_file_faker/app_registry.py` (~200-250 lines)

**AppDetector Interface:**
```python
class AppDetector(ABC):
    @abstractmethod
    def get_display_name(self) -> str:
        """Human-readable app name for UI"""

    @abstractmethod
    def get_default_path(self) -> Path | None:
        """Platform-specific FIT files directory"""

    @abstractmethod
    def validate_path(self, path: Path) -> bool:
        """Check if path looks correct for this app"""
```

**Tests to Add:**
- `tests/test_app_registry.py` (NEW, ~12 tests):
  - Test each detector class (3 tests each: display name, default path, validation)
  - Mock filesystem operations for platform-specific testing
  - Test factory function

**Success Criteria:**
- All detectors work on macOS, Windows, Linux
- TPV detection maintains existing behavior
- Zwift detection finds correct directories
- MyWhoosh detection finds correct directories (including Windows package scanning)
- Tests cover all platform branches

---

### Phase 3: Profile Management TUI (Est. 3 days)

**Objectives:**
- Create `ProfileManager` class in `config.py` with CRUD methods
- Implement Rich table display for profile list
- Implement Questionary-based menu system with arrow key navigation
- Create profile creation wizard (app-first flow)
- Create profile edit wizard
- Create profile deletion with confirmation
- Create set-default-profile wizard
- Refactor `build_config_file()` to use new TUI

**Files to Modify:**
- `fit_file_faker/config.py` (expand from 225 → ~450 lines)

**Menu Flow:**
```
┌─── FIT File Faker - Profile Manager ───┐
│ Current Profiles:                       │
│ ┏━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━┓    │
│ ┃ Name  ┃ App       ┃ Garmin User ┃    │
│ ┡━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━┩    │
│ │ tpv ⭐ │ TPV       │ user@...    │    │
│ │ zwift │ Zwift     │ user2@...   │    │
│ └───────┴───────────┴─────────────┘    │
│                                         │
│ What would you like to do?              │
│ > Create new profile                   │
│   Edit existing profile                 │
│   Delete profile                        │
│   Set default profile                   │
│   Exit                                  │
└─────────────────────────────────────────┘
```

**Profile Creation Wizard (App-First Flow):**
1. Select app type (questionary.select with AppType choices)
2. Auto-detect directory (show Rich panel with result, confirm/override)
3. Enter Garmin username (questionary.text)
4. Enter Garmin password (questionary.password, masked)
5. Enter profile name (questionary.text, suggest app name)
6. Confirm and save (show Rich panel with summary)

**Tests to Add:**
- `tests/test_profile_manager.py` (NEW, ~33 tests):
  - `TestProfileCRUD` (10 tests): create, read, update, delete, default setting
  - `TestProfileMenu` (8 tests): menu navigation (mocked questionary)
  - `TestProfileWizards` (15 tests): creation wizard, edit wizard, deletion wizard

**Success Criteria:**
- Menu displays profiles in Rich table format
- Profile creation wizard works for all app types
- Edit/delete operations work correctly
- Default profile setting persists
- All interactions testable with mocked questionary/rich
- TUI works on macOS, Windows, Linux

---

### Phase 4: Multi-Profile CLI Integration (Est. 2 days)

**Objectives:**
- Add `get_garth_dir(profile_name)` function to isolate credentials
- Modify `upload()` to accept `Profile` parameter instead of reading global config
- Modify `upload_all()` to accept and pass `Profile` parameter
- Add CLI arguments: `--profile <name>`, `--list-profiles`, `--config-menu`
- Implement profile selection logic in `run()` function
- Update monitor mode to use profile

**Files to Modify:**
- `fit_file_faker/app.py` (lines 136-216 for upload, 342-533 for CLI)

**New CLI Arguments:**
```bash
--profile <name>, -p <name>  # Select profile for operation
--list-profiles              # Display all profiles and exit
--config-menu                # Launch profile management TUI
```

**Profile Selection Logic:**
```python
def select_profile(args) -> Profile:
    """Priority: 1) --profile arg, 2) default profile, 3) prompt if multiple, 4) error"""
    if args.profile:
        profile = config_manager.config.get_profile(args.profile)
        if not profile:
            raise ValueError(f"Profile '{args.profile}' not found")
        return profile

    default = config_manager.config.get_default_profile()
    if default:
        return default

    if not config_manager.config.profiles:
        raise ValueError("No profiles configured. Run with --config-menu")

    # Multiple profiles, no default - prompt user
    profile_name = questionary.select(
        "Select profile:",
        choices=[p.name for p in config_manager.config.profiles]
    ).ask()
    return config_manager.config.get_profile(profile_name)
```

**Garth Isolation:**
```python
def get_garth_dir(profile_name: str) -> Path:
    """Get profile-specific garth directory.

    Example: ~/.cache/FitFileFaker/.garth_tpv/
    """
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in profile_name)
    garth_dir = dirs.user_cache_path / f".garth_{safe_name}"
    garth_dir.mkdir(exist_ok=True, parents=True)
    return garth_dir
```

**Tests to Add:**
- `tests/test_app.py` (update existing 32 tests):
  - `TestProfileSelection` (8 tests): CLI arg priority, default behavior, error cases
  - `TestMultiProfileUploads` (6 tests): upload with different profiles
  - `TestGarthIsolation` (5 tests): verify separate directories per profile
  - Update existing tests to pass `Profile` objects

**Success Criteria:**
- Profile selection works via `--profile` flag
- Default profile used when no flag specified
- Garth directories isolated per profile (no credential leakage)
- Upload function accepts Profile object
- Monitor mode respects profile selection
- All CLI tests pass with new argument structure

---

### Phase 5: Documentation & Polish (Est. 2 days)

**Objectives:**
- Update README.md with multi-profile examples
- Update CLAUDE.md with new architecture
- Update docs/index.md user guide
- Create docs/profiles.md comprehensive profile guide
- Add multi-profile workflow examples
- Document extensibility pattern for new apps
- Update docstrings in all modified functions

**Files to Update:**
- `README.md` - Add multi-profile section before "Development Setup"
- `CLAUDE.md` - Update "Package Structure", "Configuration Management", "Commands" sections
- `docs/index.md` - Add profile management section
- `docs/profiles.md` (NEW) - Comprehensive guide

**Example Workflows to Document:**

**Scenario 1: User with TPV and Zwift**
```bash
# Initial setup
fit-file-faker --config-menu
# Create "tpv" profile → Select TPV → Auto-detect → Enter Garmin creds
# Create "zwift" profile → Select Zwift → Auto-detect → Enter same/different Garmin creds

# Daily usage
fit-file-faker -p tpv -ua       # Upload all new TPV files
fit-file-faker -p zwift -ua     # Upload all new Zwift files
fit-file-faker -p zwift -m      # Monitor Zwift directory
```

**Scenario 2: Multiple Garmin accounts**
```bash
fit-file-faker --config-menu
# Create "work" profile → Select TPV → work-garmin@company.com
# Create "personal" profile → Select TPV → personal@gmail.com

fit-file-faker -p work -u ride.fit      # Upload to work account
fit-file-faker -p personal -u ride.fit  # Upload to personal account
```

**Scenario 3: List and manage profiles**
```bash
fit-file-faker --list-profiles          # Show all profiles
fit-file-faker --config-menu            # Launch TUI to edit/delete
```

**Extensibility Guide:**
Document how to add new trainer app (e.g., Rouvy):
1. Add `ROUVY = "rouvy"` to `AppType` enum
2. Create `RouvyDetector(AppDetector)` class
3. Add `AppType.ROUVY: RouvyDetector` to `APP_REGISTRY`
4. Done! App automatically appears in creation menu

**Tests to Add:**
- `tests/test_integration_profiles.py` (NEW, ~10 tests):
  - End-to-end profile workflows
  - Migration scenarios
  - Multi-profile concurrent operations

**Success Criteria:**
- Documentation covers all new features clearly
- Examples are practical and tested
- Migration guide for v1.2.4 users
- Troubleshooting section addresses common issues
- Extensibility guide is clear and complete

---

### Phase 6: Testing & Validation (Est. 2 days)

**Objectives:**
- Run full test suite locally
- Achieve 100% coverage for `config.py` and `app.py`
- Achieve 95%+ coverage for `app_registry.py`
- Test on Python 3.12, 3.13, 3.14
- Test on macOS, Windows (via CI), Linux (via CI)
- Run ruff linting
- Test migration from real v1.2.4 config
- Manual testing of TUI on different terminals

**Test Summary:**
- `tests/test_config.py` - 40 tests (21 existing + 19 new)
- `tests/test_app.py` - 51 tests (32 existing + 19 new)
- `tests/test_app_registry.py` - 12 tests (NEW)
- `tests/test_profile_manager.py` - 33 tests (NEW)
- `tests/test_integration_profiles.py` - 10 tests (NEW)
- **Total: 146 tests** (53 existing → 146 total, +93 tests)

**CI Validation Checklist:**
- ✅ All tests pass on Python 3.12, 3.13, 3.14
- ✅ All tests pass on Ubuntu, macOS, Windows
- ✅ Code coverage ≥ 100% for config.py and app.py
- ✅ Code coverage ≥ 95% for app_registry.py
- ✅ Ruff linting passes (`ruff check . && ruff format .`)
- ✅ Conventional commit format validation passes
- ✅ Documentation builds successfully (`mkdocs build`)

**Manual Testing Checklist:**
- ✅ Fresh install migration (v1.2.4 → v2.0.0)
- ✅ TUI menu navigation (arrow keys, selections)
- ✅ Profile creation for TPV, Zwift, MyWhoosh
- ✅ Profile edit and deletion
- ✅ Default profile setting
- ✅ Multi-profile upload isolation (check garth dirs)
- ✅ Monitor mode with profile selection
- ✅ TUI rendering on macOS Terminal, iTerm2, Windows Terminal

**Success Criteria:**
- All automated tests pass
- Code coverage targets met
- Linting passes
- Manual testing confirms UI works correctly
- Migration from v1.2.4 works flawlessly
- No regressions in existing functionality

---

## Critical Files for Implementation

| File | Current Lines | Est. New Lines | Changes |
|------|--------------|----------------|---------|
| `fit_file_faker/config.py` | 225 | ~450 | Core data structures, ProfileManager, TUI |
| `fit_file_faker/app.py` | 533 | ~650 | Profile selection, garth isolation, CLI args |
| `fit_file_faker/app_registry.py` | 0 | ~250 | NEW - App detector classes and registry |
| `tests/test_config.py` | 21 tests | ~40 tests | Profile/Config/Migration tests |
| `tests/test_app.py` | 32 tests | ~51 tests | Profile selection, garth isolation |
| `tests/test_app_registry.py` | 0 | ~12 tests | NEW - Detector class tests |
| `tests/test_profile_manager.py` | 0 | ~33 tests | NEW - TUI and CRUD tests |
| `tests/test_integration_profiles.py` | 0 | ~10 tests | NEW - E2E workflow tests |

---

## Backward Compatibility Strategy

### Automatic Migration

When user upgrades from v1.2.4 to v2.0.0:

1. **First run:** Config manager detects legacy format (no "profiles" key)
2. **Auto-migrate:** Creates "default" profile with existing values
3. **Set app_type:** Defaults to `TP_VIRTUAL` (original use case)
4. **Preserve credentials:** All garmin credentials and paths copied exactly
5. **Log notification:** Info message explains migration
6. **No user action:** Tool works exactly as before

**User sees:**
```
[INFO] Detected legacy single-profile config, migrating to multi-profile format
[INFO] Migration complete. Your existing settings are now in the 'default' profile.
[INFO] Using default profile: default
```

### No Breaking Changes

**Guaranteed behaviors:**
- ✅ Existing config files load successfully
- ✅ All existing CLI commands work identically
- ✅ Default profile used when no `--profile` specified
- ✅ Monitor mode uses default profile automatically
- ✅ Garth credentials preserved and functional
- ✅ Upload behavior unchanged for single-profile users

**New optional features:**
- `--profile` flag (optional, defaults to default profile)
- `--list-profiles` (new command)
- `--config-menu` (new command, `-s` still works)

---

## Risk Mitigation

| Risk | Mitigation | Testing |
|------|-----------|---------|
| Config corruption during migration | Backup old config before migration, validate new config after | Migration tests with edge cases (empty values, invalid paths) |
| Garth credential conflicts | Isolated directories per profile (`~/.garth_{profile}`) | Garth isolation tests, concurrent profile tests |
| Platform-specific path detection failures | Fallback to user prompt if auto-detection fails | Mock filesystem tests for all platforms, manual testing |
| Questionary/Rich rendering issues on Windows | Use questionary's built-in Windows compatibility, test in CI | CI tests on Windows, manual testing in Windows Terminal |
| Test coverage regression | Strict CI enforcement of 100% for core modules | Coverage reports in CI, fail build if < 100% |

---

## Timeline Estimate

| Phase | Days | Cumulative |
|-------|------|-----------|
| Phase 1: Core Data Structures | 2 | 2 days |
| Phase 2: App Registry & Detection | 2 | 4 days |
| Phase 3: Profile Management TUI | 3 | 7 days |
| Phase 4: CLI Integration | 2 | 9 days |
| Phase 5: Documentation & Polish | 2 | 11 days |
| Phase 6: Testing & Validation | 2 | 13 days |

**Total: ~13 development days (~2.5 weeks)**

---

## Verification Steps (Post-Implementation)

After implementation, verify:

1. **Migration Works:**
   ```bash
   # Save v1.2.4 config, upgrade, verify migration
   cp ~/.config/FitFileFaker/.config.json ~/.config/FitFileFaker/.config.json.bak
   # Install new version
   fit-file-faker --list-profiles  # Should show "default" profile
   ```

2. **Profile Creation:**
   ```bash
   fit-file-faker --config-menu
   # Create profiles for TPV, Zwift, MyWhoosh
   # Verify auto-detection works for each
   ```

3. **Multi-Profile Upload:**
   ```bash
   fit-file-faker -p tpv -d test.fit      # Dry run with TPV profile
   fit-file-faker -p zwift -d test.fit    # Dry run with Zwift profile
   # Check garth directories are separate:
   ls ~/Library/Caches/FitFileFaker/.garth_*
   ```

4. **Monitor Mode:**
   ```bash
   fit-file-faker -p zwift -m  # Monitor with specific profile
   # Verify uploads go to correct Garmin account
   ```

5. **TUI Navigation:**
   ```bash
   fit-file-faker --config-menu
   # Test: create, edit, delete, set default
   # Verify Rich tables render correctly
   # Verify arrow key navigation works
   ```

6. **Test Suite:**
   ```bash
   python3 run_tests.py --html
   # Open htmlcov/index.html
   # Verify 100% coverage for config.py and app.py
   ```

7. **Linting:**
   ```bash
   ruff check .
   ruff format .
   # Should pass with no errors
   ```

8. **Documentation:**
   ```bash
   mkdocs serve
   # Open http://127.0.0.1:8000
   # Verify all new documentation renders correctly
   ```

---

## Success Criteria Summary

✅ **Functionality:**
- Multiple profiles with different Garmin users work
- TPV, Zwift, MyWhoosh auto-detection works on all platforms
- Menu-based TUI works with arrow keys and Rich formatting
- Profile CRUD operations work correctly
- Monitor mode uses default profile (overridable with `--profile`)
- Garth credentials isolated per profile

✅ **Quality:**
- 100% test coverage for config.py and app.py maintained
- 95%+ test coverage for app_registry.py
- All tests pass on Python 3.12, 3.13, 3.14
- All tests pass on macOS, Windows, Linux
- Ruff linting passes
- Conventional commit format enforced

✅ **Compatibility:**
- Automatic migration from v1.2.4 to v2.0.0
- No breaking changes to CLI interface
- Existing configs load and work correctly
- Default profile behavior matches old single-profile behavior

✅ **Documentation:**
- README.md updated with multi-profile examples
- CLAUDE.md updated with new architecture
- docs/ site updated with comprehensive profile guide
- Extensibility guide for adding new apps
- Troubleshooting section added

✅ **Extensibility:**
- Adding new trainer app requires only: enum + detector class + registry entry
- Clear pattern established and documented
- Future-proof design

---

## Next Steps After Plan Approval

1. Create feature branch: `git checkout -b feat/multi-profile-config`
2. Implement Phase 1 (Core Data Structures)
3. Commit with conventional format: `feat(config): add multi-profile data structures and migration`
4. Continue through phases 2-6
5. Open PR when complete with full test coverage
6. Update version to v2.0.0 in pyproject.toml
7. Create release tag and publish to PyPI
