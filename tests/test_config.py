"""
Tests for configuration management functionality.
"""

import json
import logging
from pathlib import Path

import pytest
import questionary

from fit_file_faker.config import (
    AppType,
    Config,
    ConfigManager,
    Profile,
    ProfileManager,
    get_fitfiles_path,
    get_tpv_folder,
    migrate_legacy_config,
)

# Import shared mock classes from conftest
from .conftest import MockQuestion


# Test Fixtures and Helpers


@pytest.fixture
def mock_questionary_basic(monkeypatch):
    """Mock questionary with basic return values for text/password inputs."""

    def mock_text(prompt):
        return MockQuestion("")

    def mock_password(prompt):
        return MockQuestion("")

    monkeypatch.setattr(questionary, "text", mock_text)
    monkeypatch.setattr(questionary, "password", mock_password)


@pytest.fixture
def mock_get_fitfiles_path(monkeypatch):
    """Mock get_fitfiles_path to return a test path."""

    def _mock(*args, **kwargs):
        return Path("/mocked/fitfiles/path")

    monkeypatch.setattr("fit_file_faker.config.get_fitfiles_path", _mock)
    return _mock


@pytest.fixture
def mock_get_tpv_folder(monkeypatch):
    """Mock get_tpv_folder to return a test path."""

    def _mock(existing_path):
        return Path("/mocked/tpv/folder")

    monkeypatch.setattr("fit_file_faker.config.get_tpv_folder", _mock)
    return _mock


@pytest.fixture
def config_with_all_fields():
    """Create a Config with all fields populated."""
    return Config(
        garmin_username="test@example.com",
        garmin_password="password123",
        fitfiles_path=Path("/path/to/fitfiles"),
    )


class TestConfig:
    """Tests for the Config dataclass."""

    def test_config_initialization(self):
        """Test Config initialization with default and provided values."""
        # Test defaults
        config = Config()
        assert config.garmin_username is None
        assert config.garmin_password is None
        assert config.fitfiles_path is None

        # Test with values
        config = Config(
            garmin_username="test@example.com",
            garmin_password="password123",
            fitfiles_path=Path("/path/to/fitfiles"),
        )
        assert config.garmin_username == "test@example.com"
        assert config.garmin_password == "password123"
        assert config.fitfiles_path == Path("/path/to/fitfiles")


class TestConfigManager:
    """Tests for the ConfigManager class."""

    def test_config_manager_initialization(self):
        """Test ConfigManager initialization creates config file with defaults."""
        config_manager = ConfigManager()

        # Config file should exist
        assert config_manager.config_file.exists()
        # Config should be initialized with None values
        assert isinstance(config_manager.config, Config)
        assert config_manager.config.garmin_username is None
        assert config_manager.config.garmin_password is None
        assert config_manager.config.fitfiles_path is None

    def test_load_config_with_data(self, tmp_path):
        """Test loading config from file with data."""
        # Create config file with data
        config_file = tmp_path / "config" / ".config.json"
        config_data = {
            "garmin_username": "user@example.com",
            "garmin_password": "secret",
            "fitfiles_path": "/path/to/files",
        }
        with config_file.open("w") as f:
            json.dump(config_data, f)

        # Load config
        config_manager = ConfigManager()

        assert config_manager.config.garmin_username == "user@example.com"
        assert config_manager.config.garmin_password == "secret"
        assert config_manager.config.fitfiles_path == "/path/to/files"

    def test_save_config(self):
        """Test saving config to file with string and Path object serialization."""
        config_manager = ConfigManager()

        # Test with string path
        config_manager.config.garmin_username = "test@example.com"
        config_manager.config.garmin_password = "password"
        config_manager.config.fitfiles_path = "/test/path"
        config_manager.save_config()

        with config_manager.config_file.open("r") as f:
            data = json.load(f)
        assert data["garmin_username"] == "test@example.com"
        assert data["garmin_password"] == "password"
        assert data["fitfiles_path"] == "/test/path"

        # Test with Path object - should serialize to string
        config_manager.config.fitfiles_path = Path("/path/to/fitfiles")
        config_manager.save_config()

        with config_manager.config_file.open("r") as f:
            data = json.load(f)
        # Use Path.as_posix() to handle cross-platform path comparison
        assert Path(data["fitfiles_path"]).as_posix() == "/path/to/fitfiles"
        assert isinstance(data["fitfiles_path"], str)

    def test_is_valid(self):
        """Test is_valid method with various scenarios."""
        config_manager = ConfigManager()

        # All fields present - should be valid
        config_manager.config.garmin_username = "test@example.com"
        config_manager.config.garmin_password = "password"
        config_manager.config.fitfiles_path = Path("/path/to/files")
        assert config_manager.is_valid() is True
        assert config_manager.is_valid(excluded_keys=None) is True

        # Missing field - should be invalid
        config_manager.config.fitfiles_path = None
        assert config_manager.is_valid() is False

        # Missing field but excluded - should be valid
        assert config_manager.is_valid(excluded_keys=["fitfiles_path"]) is True

    def test_get_config_file_path(self, tmp_path):
        """Test getting config file path."""
        config_manager = ConfigManager()

        config_path = config_manager.get_config_file_path()

        assert isinstance(config_path, Path)
        assert config_path.name == ".config.json"
        assert config_path.parent == tmp_path / "config"

    def test_build_config_file_interactive(self, monkeypatch, mock_get_fitfiles_path):
        """Test interactive config file building."""
        config_manager = ConfigManager()

        # Mock questionary inputs
        def mock_text(prompt):
            return MockQuestion(
                "interactive@example.com" if "garmin_username" in prompt else ""
            )

        def mock_password(prompt):
            return MockQuestion("interactive_pass")

        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        # Build config
        config_manager.build_config_file(rewrite_config=False, excluded_keys=[])

        assert config_manager.config.garmin_username == "interactive@example.com"
        assert config_manager.config.garmin_password == "interactive_pass"
        # Use Path.as_posix() to handle cross-platform path comparison
        assert (
            Path(str(config_manager.config.fitfiles_path)).as_posix()
            == "/mocked/fitfiles/path"
        )

    def test_build_config_file_with_existing_values(self, mock_get_fitfiles_path):
        """Test that existing values are preserved when not overwriting."""
        config_manager = ConfigManager()

        # Set existing values
        config_manager.config.garmin_username = "existing@example.com"
        config_manager.config.garmin_password = "existing_pass"
        config_manager.save_config()

        # Reload config manager
        config_manager = ConfigManager()

        # Build without overwriting
        config_manager.build_config_file(
            overwrite_existing_vals=False, rewrite_config=False, excluded_keys=[]
        )

        # Existing values should be preserved
        assert config_manager.config.garmin_username == "existing@example.com"
        assert config_manager.config.garmin_password == "existing_pass"

    def test_build_config_file_hides_password_in_prompt(
        self, monkeypatch, mock_get_fitfiles_path
    ):
        """Test that password is masked with <**hidden**> in interactive prompts."""
        config_manager = ConfigManager()

        # Set existing password
        config_manager.config.garmin_username = "test@example.com"
        config_manager.config.garmin_password = "secret_password_123"
        config_manager.config.fitfiles_path = Path("/path/to/files")
        config_manager.save_config()

        # Reload to get fresh instance
        config_manager = ConfigManager()

        # Track what prompt message was passed to questionary
        captured_prompts = []

        def mock_text(prompt):
            captured_prompts.append(prompt)
            return MockQuestion("")

        def mock_password(prompt):
            captured_prompts.append(prompt)
            return MockQuestion("")

        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        # Build config with overwrite enabled to trigger prompts for existing values
        config_manager.build_config_file(
            overwrite_existing_vals=True, rewrite_config=False, excluded_keys=[]
        )

        # Find the password prompt and verify masking
        password_prompts = [p for p in captured_prompts if "garmin_password" in p]
        assert len(password_prompts) > 0
        for prompt in password_prompts:
            assert "secret_password_123" not in prompt
            assert "<**hidden**>" in prompt

    def test_build_config_file_warns_on_invalid_input(
        self, monkeypatch, caplog, mock_get_fitfiles_path
    ):
        """Test that warning is logged when user provides invalid (empty) input."""
        config_manager = ConfigManager()
        config_manager.config.garmin_username = None
        config_manager.config.garmin_password = "password"
        config_manager.config.fitfiles_path = Path("/path/to/files")

        # Track number of times questionary is called
        call_count = {"text": 0}

        def mock_text(prompt):
            call_count["text"] += 1
            # First call returns empty (invalid), second returns valid
            return MockQuestion("" if call_count["text"] == 1 else "valid@example.com")

        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", lambda p: MockQuestion(""))

        # Build config
        with caplog.at_level(logging.WARNING):
            config_manager.build_config_file(
                overwrite_existing_vals=True, rewrite_config=False, excluded_keys=[]
            )

        # Verify warning was logged and valid value was eventually set
        assert any(
            "Entered input was not valid, please try again" in record.message
            for record in caplog.records
        )
        assert config_manager.config.garmin_username == "valid@example.com"

    def test_build_config_file_keyboard_interrupt(self, monkeypatch, caplog):
        """Test that KeyboardInterrupt is handled properly during config building."""
        config_manager = ConfigManager()
        config_manager.config.garmin_username = None
        config_manager.config.garmin_password = "password"
        config_manager.config.fitfiles_path = Path("/path/to/files")

        # Mock to raise KeyboardInterrupt
        def mock_text(prompt):
            class MockQuestion:
                def unsafe_ask(self):
                    raise KeyboardInterrupt()

            return MockQuestion()

        monkeypatch.setattr(questionary, "text", mock_text)

        # Should exit with code 1 when interrupted
        with pytest.raises(SystemExit) as exc_info:
            with caplog.at_level(logging.ERROR):
                config_manager.build_config_file(
                    overwrite_existing_vals=True, rewrite_config=False, excluded_keys=[]
                )

        assert exc_info.value.code == 1
        assert any(
            "User canceled input; exiting!" in record.message
            for record in caplog.records
        )

    def test_build_config_file_excluded_keys_none_handling(
        self, mock_questionary_basic, mock_get_fitfiles_path
    ):
        """Test that excluded_keys=None is properly converted to empty list (covers lines 88-89)."""
        config_manager = ConfigManager()
        config_manager.config.garmin_username = "test@example.com"
        config_manager.config.garmin_password = "password"
        config_manager.config.fitfiles_path = Path("/path/to/files")

        # Call with excluded_keys=None explicitly - should not raise any errors
        # This tests the line: if excluded_keys is None: excluded_keys = []
        config_manager.build_config_file(
            overwrite_existing_vals=False,
            rewrite_config=False,
            excluded_keys=None,  # Explicitly pass None
        )

        # Config should remain intact
        assert config_manager.config.garmin_username == "test@example.com"

    def test_build_config_file_rewrite_config(
        self, mock_questionary_basic, mock_get_fitfiles_path
    ):
        """Test rewrite_config parameter controls whether config is saved to file."""
        # Test rewrite_config=True saves changes
        config_manager = ConfigManager()
        config_manager.config.garmin_username = "test@example.com"
        config_manager.config.garmin_password = "password"
        config_manager.config.fitfiles_path = Path("/path/to/files")

        config_manager.build_config_file(
            overwrite_existing_vals=False, rewrite_config=True, excluded_keys=[]
        )

        with config_manager.config_file.open("r") as f:
            saved_data = json.load(f)
        assert saved_data["garmin_username"] == "test@example.com"
        assert saved_data["garmin_password"] == "password"

        # Test rewrite_config=False does NOT save changes
        config_manager2 = ConfigManager()
        config_manager2.config.garmin_username = "original@example.com"
        config_manager2.config.garmin_password = "original_password"
        config_manager2.config.fitfiles_path = Path("/original/path")
        config_manager2.save_config()

        with config_manager2.config_file.open("r") as f:
            original_data = json.load(f)

        # Update in memory only
        config_manager2.config.garmin_username = "updated@example.com"
        config_manager2.build_config_file(
            overwrite_existing_vals=False, rewrite_config=False, excluded_keys=[]
        )

        # File should still have original data
        with config_manager2.config_file.open("r") as f:
            current_data = json.load(f)
        assert current_data == original_data
        assert current_data["garmin_username"] == "original@example.com"


class TestGetFitfilesPath:
    """Tests for the get_fitfiles_path function."""

    @pytest.fixture
    def tpv_path_with_user(self, tmp_path):
        """Create TPVirtual directory with a valid user folder."""
        tpv_path = tmp_path / "TPVirtual"
        tpv_path.mkdir()
        user_folder = tpv_path / "a1b2c3d4e5f6g7h8"  # 16 alphanumeric chars
        user_folder.mkdir()
        fit_folder = user_folder / "FITFiles"
        fit_folder.mkdir()
        return tpv_path, fit_folder

    def test_get_fitfiles_path_no_user_folders(self, tmp_path, monkeypatch, caplog):
        """Test error when no TPVirtual user folders are found."""
        # Create empty TPVirtual directory
        tpv_path = tmp_path / "TPVirtual"
        tpv_path.mkdir()

        monkeypatch.setattr("fit_file_faker.config.get_tpv_folder", lambda x: tpv_path)

        # Should exit when no user folders found
        with pytest.raises(SystemExit) as exc_info:
            with caplog.at_level(logging.ERROR):
                get_fitfiles_path(None)

        assert exc_info.value.code == 1
        assert any(
            "Cannot find a TP Virtual User folder" in record.message
            for record in caplog.records
        )

    def test_get_fitfiles_path_single_folder(
        self, monkeypatch, caplog, tpv_path_with_user
    ):
        """Test with single user folder - both confirmed and rejected scenarios."""
        tpv_path, fit_folder = tpv_path_with_user
        monkeypatch.setattr("fit_file_faker.config.get_tpv_folder", lambda x: tpv_path)

        # Test user confirms folder
        monkeypatch.setattr(
            questionary, "select", lambda t, choices: MockQuestion("yes")
        )
        with caplog.at_level(logging.INFO):
            result = get_fitfiles_path(None)
        assert result == fit_folder
        assert any(
            "Found TP Virtual User directory" in r.message for r in caplog.records
        )

        # Test user rejects folder
        caplog.clear()
        monkeypatch.setattr(
            questionary, "select", lambda t, choices: MockQuestion("no")
        )
        with pytest.raises(SystemExit) as exc_info:
            with caplog.at_level(logging.ERROR):
                get_fitfiles_path(None)
        assert exc_info.value.code == 1
        assert any(
            "Failed to find correct TP Virtual User folder" in r.message
            for r in caplog.records
        )

    def test_get_fitfiles_path_multiple_folders(self, tmp_path, monkeypatch, caplog):
        """Test with multiple user folders and user selects one."""
        tpv_path = tmp_path / "TPVirtual"
        tpv_path.mkdir()
        user_folder1 = tpv_path / "a1b2c3d4e5f6g7h8"
        user_folder2 = tpv_path / "z9y8x7w6v5u4t3s2"
        user_folder1.mkdir()
        user_folder2.mkdir()
        fit_folder2 = user_folder2 / "FITFiles"
        (user_folder1 / "FITFiles").mkdir()
        fit_folder2.mkdir()

        monkeypatch.setattr("fit_file_faker.config.get_tpv_folder", lambda x: tpv_path)
        monkeypatch.setattr(
            questionary, "select", lambda t, choices: MockQuestion("z9y8x7w6v5u4t3s2")
        )

        with caplog.at_level(logging.INFO):
            result = get_fitfiles_path(None)

        assert result == fit_folder2
        assert any(
            "Found TP Virtual User directory" in r.message for r in caplog.records
        )

    def test_get_fitfiles_path_ignores_non_matching_folders(
        self, tmp_path, monkeypatch
    ):
        """Test that folders not matching the 16-char pattern are ignored."""
        tpv_path = tmp_path / "TPVirtual"
        tpv_path.mkdir()
        valid_folder = tpv_path / "a1b2c3d4e5f6g7h8"
        valid_folder.mkdir()
        (tpv_path / "too_short").mkdir()
        (tpv_path / "this_is_too_long_folder").mkdir()
        (tpv_path / "has-special-chars").mkdir()
        fit_folder = valid_folder / "FITFiles"
        fit_folder.mkdir()

        monkeypatch.setattr("fit_file_faker.config.get_tpv_folder", lambda x: tpv_path)
        monkeypatch.setattr(
            questionary, "select", lambda t, choices: MockQuestion("yes")
        )

        result = get_fitfiles_path(None)
        assert result == fit_folder  # Should only find the valid folder


class TestGetTpvFolder:
    """Tests for the get_tpv_folder function."""

    def test_get_tpv_folder_from_environment(self, monkeypatch, caplog):
        """Test that TPV_DATA_PATH environment variable is used when set."""
        test_path = "/custom/tpv/path"
        monkeypatch.setenv("TPV_DATA_PATH", test_path)

        with caplog.at_level(logging.INFO):
            result = get_tpv_folder(None)

        assert result == Path(test_path)
        assert any(
            f'Using TPV_DATA_PATH value read from the environment: "{test_path}"'
            in r.message
            for r in caplog.records
        )

    def test_get_tpv_folder_platform_defaults(self, monkeypatch):
        """Test default paths on different platforms."""
        monkeypatch.delenv("TPV_DATA_PATH", raising=False)

        # macOS
        monkeypatch.setattr("sys.platform", "darwin")
        assert get_tpv_folder(None) == Path.home() / "TPVirtual"

        # Windows
        monkeypatch.setattr("sys.platform", "win32")
        assert get_tpv_folder(None) == Path.home() / "Documents" / "TPVirtual"

    def test_get_tpv_folder_linux_manual_entry(self, monkeypatch, caplog):
        """Test manual path entry on Linux with and without default path."""
        monkeypatch.delenv("TPV_DATA_PATH", raising=False)
        monkeypatch.setattr("sys.platform", "linux")
        user_path = "/home/user/TPVirtual"

        # Test with default path
        monkeypatch.setattr(
            questionary, "path", lambda p, default="": MockQuestion(user_path)
        )
        with caplog.at_level(logging.WARNING):
            result = get_tpv_folder(Path("/home/user/default/path"))
        assert result == Path(user_path)
        assert any(
            "TrainingPeaks Virtual user folder can only be automatically detected on Windows and OSX"
            in r.message
            for r in caplog.records
        )

        # Test without default path (verifies default="" is used)
        caplog.clear()

        def mock_path_verify_default(prompt, default=""):
            assert default == ""  # Verify default is empty when None passed
            return MockQuestion(user_path)

        monkeypatch.setattr(questionary, "path", mock_path_verify_default)
        with caplog.at_level(logging.WARNING):
            result = get_tpv_folder(None)
        assert result == Path(user_path)

    def test_get_tpv_folder_environment_overrides_platform(self, monkeypatch):
        """Test that environment variable takes precedence over platform detection."""
        test_path = "/env/override/path"
        monkeypatch.setenv("TPV_DATA_PATH", test_path)
        monkeypatch.setattr("sys.platform", "darwin")

        result = get_tpv_folder(None)

        # Should use environment variable, not ~/TPVirtual
        assert result == Path(test_path)
        assert result != Path.home() / "TPVirtual"


# ==============================================================================
# Phase 1: Multi-Profile Tests
# ==============================================================================


class TestProfile:
    """Tests for Profile dataclass."""

    def test_profile_creation(self):
        """Test creating a Profile with all fields."""
        profile = Profile(
            name="test",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="secret",
            fitfiles_path=Path("/path/to/fitfiles"),
        )
        assert profile.name == "test"
        assert profile.app_type == AppType.ZWIFT
        assert profile.garmin_username == "user@example.com"
        assert profile.garmin_password == "secret"
        assert profile.fitfiles_path == Path("/path/to/fitfiles")

    def test_profile_post_init_converts_string_app_type(self):
        """Test that __post_init__ converts string app_type to Enum."""
        profile = Profile(
            name="test",
            app_type="zwift",  # String instead of Enum
            garmin_username="user@example.com",
            garmin_password="secret",
            fitfiles_path=Path("/path/to/fitfiles"),
        )
        assert profile.app_type == AppType.ZWIFT
        assert isinstance(profile.app_type, AppType)

    def test_profile_post_init_converts_string_path(self):
        """Test that __post_init__ converts string fitfiles_path to Path."""
        profile = Profile(
            name="test",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="secret",
            fitfiles_path="/path/to/fitfiles",  # String instead of Path
        )
        assert profile.fitfiles_path == Path("/path/to/fitfiles")
        assert isinstance(profile.fitfiles_path, Path)

    def test_profile_serialization_to_dict(self):
        """Test that Profile can be converted to dict with asdict()."""
        from dataclasses import asdict

        profile = Profile(
            name="test",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="user@example.com",
            garmin_password="secret",
            fitfiles_path=Path("/path/to/fitfiles"),
        )
        profile_dict = asdict(profile)
        assert profile_dict["name"] == "test"
        assert profile_dict["app_type"] == AppType.TP_VIRTUAL
        assert profile_dict["garmin_username"] == "user@example.com"

    def test_profile_deserialization_from_dict(self):
        """Test that Profile can be created from dict."""
        profile_dict = {
            "name": "test",
            "app_type": "mywhoosh",
            "garmin_username": "user@example.com",
            "garmin_password": "secret",
            "fitfiles_path": "/path/to/fitfiles",
        }
        profile = Profile(**profile_dict)
        assert profile.name == "test"
        assert profile.app_type == AppType.MYWHOOSH
        assert profile.fitfiles_path == Path("/path/to/fitfiles")


class TestConfigMultiProfile:
    """Tests for Config multi-profile functionality."""

    def test_config_empty_profiles(self):
        """Test creating Config with no profiles."""
        config = Config(profiles=[], default_profile=None)
        assert config.profiles == []
        assert config.default_profile is None

    def test_config_with_single_profile(self):
        """Test creating Config with single profile."""
        profile = Profile(
            name="test",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="secret",
            fitfiles_path=Path("/path/to/fitfiles"),
        )
        config = Config(profiles=[profile], default_profile="test")
        assert len(config.profiles) == 1
        assert config.default_profile == "test"

    def test_config_get_profile_exists(self):
        """Test getting existing profile by name."""
        profile1 = Profile(
            "profile1",
            AppType.ZWIFT,
            "user1@example.com",
            "secret1",
            Path("/path1"),
        )
        profile2 = Profile(
            "profile2",
            AppType.TP_VIRTUAL,
            "user2@example.com",
            "secret2",
            Path("/path2"),
        )
        config = Config(profiles=[profile1, profile2], default_profile="profile1")

        result = config.get_profile("profile2")
        assert result is not None
        assert result.name == "profile2"
        assert result.app_type == AppType.TP_VIRTUAL

    def test_config_get_profile_not_exists(self):
        """Test getting non-existent profile returns None."""
        profile = Profile(
            "test", AppType.ZWIFT, "user@example.com", "secret", Path("/path")
        )
        config = Config(profiles=[profile], default_profile="test")

        result = config.get_profile("nonexistent")
        assert result is None

    def test_config_get_default_profile_with_default_set(self):
        """Test getting default profile when default_profile is set."""
        profile1 = Profile(
            "profile1",
            AppType.ZWIFT,
            "user1@example.com",
            "secret1",
            Path("/path1"),
        )
        profile2 = Profile(
            "profile2",
            AppType.TP_VIRTUAL,
            "user2@example.com",
            "secret2",
            Path("/path2"),
        )
        config = Config(profiles=[profile1, profile2], default_profile="profile2")

        result = config.get_default_profile()
        assert result is not None
        assert result.name == "profile2"

    def test_config_get_default_profile_no_default_set(self):
        """Test getting default profile when no default_profile set (returns first)."""
        profile1 = Profile(
            "profile1",
            AppType.ZWIFT,
            "user1@example.com",
            "secret1",
            Path("/path1"),
        )
        profile2 = Profile(
            "profile2",
            AppType.TP_VIRTUAL,
            "user2@example.com",
            "secret2",
            Path("/path2"),
        )
        config = Config(profiles=[profile1, profile2], default_profile=None)

        result = config.get_default_profile()
        assert result is not None
        assert result.name == "profile1"  # Should return first profile

    def test_config_get_default_profile_empty(self):
        """Test getting default profile when no profiles exist."""
        config = Config(profiles=[], default_profile=None)

        result = config.get_default_profile()
        assert result is None

    def test_config_post_init_converts_dict_profiles(self):
        """Test that __post_init__ converts dict profiles to Profile objects."""
        config_data = {
            "profiles": [
                {
                    "name": "test",
                    "app_type": "zwift",
                    "garmin_username": "user@example.com",
                    "garmin_password": "secret",
                    "fitfiles_path": "/path/to/fitfiles",
                }
            ],
            "default_profile": "test",
        }
        config = Config(**config_data)

        assert len(config.profiles) == 1
        assert isinstance(config.profiles[0], Profile)
        assert config.profiles[0].name == "test"
        assert config.profiles[0].app_type == AppType.ZWIFT


class TestMigration:
    """Tests for legacy config migration."""

    def test_migrate_legacy_config_simple(self):
        """Test migrating simple legacy config."""
        legacy_config = {
            "garmin_username": "user@example.com",
            "garmin_password": "secret",
            "fitfiles_path": "/path/to/fitfiles",
        }

        config = migrate_legacy_config(legacy_config)

        assert len(config.profiles) == 1
        assert config.profiles[0].name == "default"
        assert config.profiles[0].app_type == AppType.TP_VIRTUAL
        assert config.profiles[0].garmin_username == "user@example.com"
        assert config.profiles[0].garmin_password == "secret"
        assert config.profiles[0].fitfiles_path == Path("/path/to/fitfiles")
        assert config.default_profile == "default"

    def test_migrate_legacy_config_with_none_values(self):
        """Test migrating legacy config with None values."""
        legacy_config = {
            "garmin_username": None,
            "garmin_password": None,
            "fitfiles_path": None,
        }

        config = migrate_legacy_config(legacy_config)

        assert len(config.profiles) == 1
        assert config.profiles[0].garmin_username == ""
        assert config.profiles[0].garmin_password == ""
        # When fitfiles_path is None, should default to Path.home()
        assert config.profiles[0].fitfiles_path == Path.home()

    def test_migrate_already_migrated_config(self):
        """Test that already migrated config passes through unchanged."""
        migrated_config = {
            "profiles": [
                {
                    "name": "test",
                    "app_type": "zwift",
                    "garmin_username": "user@example.com",
                    "garmin_password": "secret",
                    "fitfiles_path": "/path/to/fitfiles",
                }
            ],
            "default_profile": "test",
        }

        config = migrate_legacy_config(migrated_config)

        assert len(config.profiles) == 1
        assert config.profiles[0].name == "test"
        assert config.profiles[0].app_type == AppType.ZWIFT
        assert config.default_profile == "test"

    def test_migrate_legacy_config_empty_dict(self):
        """Test migrating empty legacy config."""
        legacy_config = {}

        config = migrate_legacy_config(legacy_config)

        assert len(config.profiles) == 1
        assert config.profiles[0].name == "default"
        assert config.profiles[0].garmin_username == ""
        assert config.profiles[0].garmin_password == ""

    def test_migrate_legacy_config_partial(self):
        """Test migrating legacy config with only some values set."""
        legacy_config = {
            "garmin_username": "user@example.com",
            # password and fitfiles_path missing
        }

        config = migrate_legacy_config(legacy_config)

        assert len(config.profiles) == 1
        assert config.profiles[0].garmin_username == "user@example.com"
        assert config.profiles[0].garmin_password == ""
        assert config.profiles[0].fitfiles_path == Path.home()

    def test_config_manager_loads_and_migrates_legacy(self, tmp_path, monkeypatch):
        """Test that ConfigManager automatically migrates legacy config on load."""
        # Create a temporary config file with legacy format
        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / ".config.json"

        legacy_config = {
            "garmin_username": "user@example.com",
            "garmin_password": "secret",
            "fitfiles_path": str(tmp_path / "fitfiles"),
        }

        with open(config_file, "w") as f:
            json.dump(legacy_config, f)

        # Mock the config directory to use our temp directory
        from fit_file_faker.config import dirs

        monkeypatch.setattr(dirs, "user_config_path", config_dir)

        # Create ConfigManager - should auto-migrate
        manager = ConfigManager()

        # Verify migration occurred
        assert len(manager.config.profiles) == 1
        assert manager.config.profiles[0].name == "default"
        assert manager.config.profiles[0].garmin_username == "user@example.com"
        assert manager.config.default_profile == "default"

        # Verify migrated config was saved back to file
        with open(config_file, "r") as f:
            saved_config = json.load(f)

        assert "profiles" in saved_config
        assert "default_profile" in saved_config
        assert len(saved_config["profiles"]) == 1


class TestProfileManager:
    """Tests for ProfileManager CRUD operations."""

    @pytest.fixture
    def manager(self, tmp_path, monkeypatch):
        """Create ProfileManager with temporary config."""
        from fit_file_faker.config import dirs

        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(dirs, "user_config_path", config_dir)

        # Create fresh config manager and profile manager
        config_mgr = ConfigManager()
        return ProfileManager(config_mgr)

    def test_create_profile(self, manager):
        """Test creating a new profile."""
        profile = manager.create_profile(
            name="test",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="secret",
            fitfiles_path=Path("/path/to/fitfiles"),
        )

        assert profile.name == "test"
        assert profile.app_type == AppType.ZWIFT
        assert len(manager.list_profiles()) == 1

    def test_create_duplicate_profile_raises_error(self, manager):
        """Test that creating duplicate profile raises ValueError."""
        manager.create_profile(
            "test",
            AppType.ZWIFT,
            "user@example.com",
            "secret",
            Path("/path"),
        )

        with pytest.raises(ValueError, match='Profile "test" already exists'):
            manager.create_profile(
                "test",
                AppType.TP_VIRTUAL,
                "user2@example.com",
                "secret2",
                Path("/path2"),
            )

    def test_get_profile(self, manager):
        """Test getting profile by name."""
        manager.create_profile(
            "test",
            AppType.ZWIFT,
            "user@example.com",
            "secret",
            Path("/path"),
        )

        profile = manager.get_profile("test")
        assert profile is not None
        assert profile.name == "test"

    def test_get_nonexistent_profile(self, manager):
        """Test getting non-existent profile returns None."""
        assert manager.get_profile("nonexistent") is None

    def test_list_profiles(self, manager):
        """Test listing all profiles."""
        manager.create_profile(
            "profile1",
            AppType.ZWIFT,
            "user1@example.com",
            "secret1",
            Path("/path1"),
        )
        manager.create_profile(
            "profile2",
            AppType.TP_VIRTUAL,
            "user2@example.com",
            "secret2",
            Path("/path2"),
        )

        profiles = manager.list_profiles()
        assert len(profiles) == 2
        assert profiles[0].name == "profile1"
        assert profiles[1].name == "profile2"

    def test_update_profile_username(self, manager):
        """Test updating profile username."""
        manager.create_profile(
            "test",
            AppType.ZWIFT,
            "old@example.com",
            "secret",
            Path("/path"),
        )

        manager.update_profile("test", garmin_username="new@example.com")

        profile = manager.get_profile("test")
        assert profile.garmin_username == "new@example.com"

    def test_update_profile_name(self, manager):
        """Test renaming a profile."""
        manager.create_profile(
            "oldname",
            AppType.ZWIFT,
            "user@example.com",
            "secret",
            Path("/path"),
        )

        manager.update_profile("oldname", new_name="newname")

        assert manager.get_profile("oldname") is None
        assert manager.get_profile("newname") is not None

    def test_update_nonexistent_profile_raises_error(self, manager):
        """Test updating non-existent profile raises ValueError."""
        with pytest.raises(ValueError, match='Profile "nonexistent" not found'):
            manager.update_profile("nonexistent", garmin_username="user@example.com")

    def test_update_profile_to_existing_name_raises_error(self, manager):
        """Test renaming to existing name raises ValueError."""
        manager.create_profile(
            "profile1",
            AppType.ZWIFT,
            "user1@example.com",
            "secret1",
            Path("/path1"),
        )
        manager.create_profile(
            "profile2",
            AppType.TP_VIRTUAL,
            "user2@example.com",
            "secret2",
            Path("/path2"),
        )

        with pytest.raises(ValueError, match='Profile "profile2" already exists'):
            manager.update_profile("profile1", new_name="profile2")

    def test_delete_profile(self, manager):
        """Test deleting a profile."""
        manager.create_profile(
            "profile1",
            AppType.ZWIFT,
            "user1@example.com",
            "secret1",
            Path("/path1"),
        )
        manager.create_profile(
            "profile2",
            AppType.TP_VIRTUAL,
            "user2@example.com",
            "secret2",
            Path("/path2"),
        )

        manager.delete_profile("profile1")

        assert manager.get_profile("profile1") is None
        assert len(manager.list_profiles()) == 1

    def test_delete_only_profile_raises_error(self, manager):
        """Test deleting the only profile raises ValueError."""
        manager.create_profile(
            "test",
            AppType.ZWIFT,
            "user@example.com",
            "secret",
            Path("/path"),
        )

        with pytest.raises(ValueError, match="Cannot delete the only profile"):
            manager.delete_profile("test")

    def test_delete_nonexistent_profile_raises_error(self, manager):
        """Test deleting non-existent profile raises ValueError."""
        with pytest.raises(ValueError, match='Profile "nonexistent" not found'):
            manager.delete_profile("nonexistent")

    def test_delete_default_profile_updates_default(self, manager):
        """Test deleting default profile sets new default."""
        manager.create_profile(
            "profile1",
            AppType.ZWIFT,
            "user1@example.com",
            "secret1",
            Path("/path1"),
        )
        manager.create_profile(
            "profile2",
            AppType.TP_VIRTUAL,
            "user2@example.com",
            "secret2",
            Path("/path2"),
        )
        manager.set_default_profile("profile1")

        manager.delete_profile("profile1")

        # Should auto-set first remaining profile as default
        assert manager.config_manager.config.default_profile == "profile2"

    def test_set_default_profile(self, manager):
        """Test setting default profile."""
        manager.create_profile(
            "profile1",
            AppType.ZWIFT,
            "user1@example.com",
            "secret1",
            Path("/path1"),
        )
        manager.create_profile(
            "profile2",
            AppType.TP_VIRTUAL,
            "user2@example.com",
            "secret2",
            Path("/path2"),
        )

        manager.set_default_profile("profile2")

        assert manager.config_manager.config.default_profile == "profile2"

    def test_set_nonexistent_default_raises_error(self, manager):
        """Test setting non-existent profile as default raises ValueError."""
        with pytest.raises(ValueError, match='Profile "nonexistent" not found'):
            manager.set_default_profile("nonexistent")
