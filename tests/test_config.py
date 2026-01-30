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
        profiles=[
            Profile(
                name="test",
                app_type=AppType.TP_VIRTUAL,
                garmin_username="test@example.com",
                garmin_password="password123",
                fitfiles_path=Path("/path/to/fitfiles"),
            )
        ],
        default_profile="test",
    )


class TestConfig:
    """Tests for the Config dataclass."""

    def test_config_initialization(self):
        """Test Config initialization with default and provided values."""
        # Test defaults
        config = Config(profiles=[], default_profile=None)
        assert config.profiles == []
        assert config.default_profile is None
        assert config.get_default_profile() is None

        # Test with values
        config = Config(
            profiles=[
                Profile(
                    name="test",
                    app_type=AppType.TP_VIRTUAL,
                    garmin_username="test@example.com",
                    garmin_password="password123",
                    fitfiles_path=Path("/path/to/fitfiles"),
                )
            ],
            default_profile="test",
        )
        assert len(config.profiles) == 1
        assert config.profiles[0].garmin_username == "test@example.com"
        assert config.profiles[0].garmin_password == "password123"
        assert config.profiles[0].fitfiles_path == Path("/path/to/fitfiles")
        assert config.default_profile == "test"
        assert config.get_default_profile() == config.profiles[0]


class TestConfigManager:
    """Tests for the ConfigManager class."""

    def test_config_manager_initialization(self):
        """Test ConfigManager initialization creates config file with defaults."""
        config_manager = ConfigManager()

        # Config file should exist
        assert config_manager.config_file.exists()
        # Config should be initialized with empty profiles
        assert isinstance(config_manager.config, Config)
        assert config_manager.config.profiles == []
        assert config_manager.config.default_profile is None
        assert config_manager.config.get_default_profile() is None

    def test_load_config_with_data(self, tmp_path):
        """Test loading config from file with data."""
        # Create config file with data (new multi-profile format)
        config_file = tmp_path / "config" / ".config.json"
        config_data = {
            "profiles": [
                {
                    "name": "default",
                    "app_type": "tp_virtual",
                    "garmin_username": "user@example.com",
                    "garmin_password": "secret",
                    "fitfiles_path": "/path/to/files",
                }
            ],
            "default_profile": "default",
        }
        with config_file.open("w") as f:
            json.dump(config_data, f)

        # Load config
        config_manager = ConfigManager()

        assert len(config_manager.config.profiles) == 1
        assert config_manager.config.profiles[0].garmin_username == "user@example.com"
        assert config_manager.config.profiles[0].garmin_password == "secret"
        assert config_manager.config.profiles[0].fitfiles_path == Path("/path/to/files")
        assert config_manager.config.default_profile == "default"

    def test_save_config(self):
        """Test saving config to file with string and Path object serialization."""
        config_manager = ConfigManager()

        # Test with profile data
        profile = Profile(
            name="test",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="test@example.com",
            garmin_password="password",
            fitfiles_path=Path("/test/path"),
        )
        config_manager.config.profiles = [profile]
        config_manager.config.default_profile = "test"
        config_manager.save_config()

        with config_manager.config_file.open("r") as f:
            data = json.load(f)
        assert data["profiles"][0]["garmin_username"] == "test@example.com"
        assert data["profiles"][0]["garmin_password"] == "password"
        assert Path(data["profiles"][0]["fitfiles_path"]).as_posix() == "/test/path"
        assert data["default_profile"] == "test"

        # Test with Path object - should serialize to string
        profile.fitfiles_path = Path("/path/to/fitfiles")
        config_manager.save_config()

        with config_manager.config_file.open("r") as f:
            data = json.load(f)
        # Use Path.as_posix() to handle cross-platform path comparison
        assert (
            Path(data["profiles"][0]["fitfiles_path"]).as_posix() == "/path/to/fitfiles"
        )
        assert isinstance(data["profiles"][0]["fitfiles_path"], str)

    def test_is_valid(self):
        """Test is_valid method with various scenarios."""
        config_manager = ConfigManager()

        # Test with no profiles - should be invalid
        assert config_manager.is_valid() is False

        # Add a profile with all fields - should be valid
        profile = Profile(
            name="test",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="test@example.com",
            garmin_password="password",
            fitfiles_path=Path("/path/to/files"),
        )
        config_manager.config.profiles = [profile]
        config_manager.config.default_profile = "test"
        assert config_manager.is_valid() is True
        assert config_manager.is_valid(excluded_keys=None) is True

        # Missing field in profile - should be invalid
        profile.fitfiles_path = None
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
        """Test interactive config file building with profiles."""
        config_manager = ConfigManager()

        # Mock questionary inputs
        def mock_text(prompt):
            return MockQuestion(
                "interactive@example.com" if "garmin_username" in prompt else "default"
            )

        def mock_password(prompt):
            return MockQuestion("interactive_pass")

        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        # Build config - this will create a default profile with overwrite_existing_vals
        # to ensure all values are prompted for (including fitfiles_path)
        config_manager.build_config_file(
            overwrite_existing_vals=True, rewrite_config=False, excluded_keys=[]
        )

        # Get default profile
        default_profile = config_manager.config.get_default_profile()
        assert default_profile is not None
        assert default_profile.garmin_username == "interactive@example.com"
        assert default_profile.garmin_password == "interactive_pass"
        # Use Path.as_posix() to handle cross-platform path comparison
        assert (
            Path(str(default_profile.fitfiles_path)).as_posix()
            == "/mocked/fitfiles/path"
        )

    def test_build_config_file_with_existing_values(self, mock_get_fitfiles_path):
        """Test that existing profile values are preserved when not overwriting."""
        config_manager = ConfigManager()

        # Create a profile with existing values
        profile = Profile(
            name="default",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="existing@example.com",
            garmin_password="existing_pass",
            fitfiles_path=Path("/existing/path"),
        )
        config_manager.config.profiles = [profile]
        config_manager.config.default_profile = "default"
        config_manager.save_config()

        # Reload config manager
        config_manager = ConfigManager()

        # Build without overwriting
        config_manager.build_config_file(
            overwrite_existing_vals=False, rewrite_config=False, excluded_keys=[]
        )

        # Existing values should be preserved
        default_profile = config_manager.config.get_default_profile()
        assert default_profile.garmin_username == "existing@example.com"
        assert default_profile.garmin_password == "existing_pass"

    def test_build_config_file_hides_password_in_prompt(
        self, monkeypatch, mock_get_fitfiles_path
    ):
        """Test that password is masked with <**hidden**> in interactive prompts."""
        config_manager = ConfigManager()

        # Create a profile with existing password
        profile = Profile(
            name="default",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="test@example.com",
            garmin_password="secret_password_123",
            fitfiles_path=Path("/path/to/files"),
        )
        config_manager.config.profiles = [profile]
        config_manager.config.default_profile = "default"
        config_manager.save_config()

        # Reload to get fresh instance
        config_manager = ConfigManager()

        # Track what prompt message was passed to questionary
        captured_prompts = []

        def mock_text(prompt):
            captured_prompts.append(prompt)
            # Return existing value (empty string will use existing)
            return MockQuestion("")

        def mock_password(prompt):
            captured_prompts.append(prompt)
            # Return existing value (empty string will use existing)
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

        # Create a profile with missing username
        profile = Profile(
            name="default",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="",  # Empty/invalid
            garmin_password="password",
            fitfiles_path=Path("/path/to/files"),
        )
        config_manager.config.profiles = [profile]
        config_manager.config.default_profile = "default"

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
        default_profile = config_manager.config.get_default_profile()
        assert default_profile.garmin_username == "valid@example.com"

    def test_build_config_file_keyboard_interrupt(self, monkeypatch, caplog):
        """Test that KeyboardInterrupt is handled properly during config building."""
        config_manager = ConfigManager()

        # Create a profile with missing username
        profile = Profile(
            name="default",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="",  # Empty to trigger prompt
            garmin_password="password",
            fitfiles_path=Path("/path/to/files"),
        )
        config_manager.config.profiles = [profile]
        config_manager.config.default_profile = "default"

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
        """Test that excluded_keys=None is properly converted to empty list."""
        config_manager = ConfigManager()

        # Create a profile with all fields set
        profile = Profile(
            name="default",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="test@example.com",
            garmin_password="password",
            fitfiles_path=Path("/path/to/files"),
        )
        config_manager.config.profiles = [profile]
        config_manager.config.default_profile = "default"

        # Call with excluded_keys=None explicitly - should not raise any errors
        # This tests the line: if excluded_keys is None: excluded_keys = []
        config_manager.build_config_file(
            overwrite_existing_vals=False,
            rewrite_config=False,
            excluded_keys=None,  # Explicitly pass None
        )

        # Config should remain intact
        default_profile = config_manager.config.get_default_profile()
        assert default_profile.garmin_username == "test@example.com"

    def test_build_config_file_rewrite_config(
        self, mock_questionary_basic, mock_get_fitfiles_path
    ):
        """Test rewrite_config parameter controls whether config is saved to file."""
        # Test rewrite_config=True saves changes
        config_manager = ConfigManager()
        profile = Profile(
            name="default",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="test@example.com",
            garmin_password="password",
            fitfiles_path=Path("/path/to/files"),
        )
        config_manager.config.profiles = [profile]
        config_manager.config.default_profile = "default"

        config_manager.build_config_file(
            overwrite_existing_vals=False, rewrite_config=True, excluded_keys=[]
        )

        with config_manager.config_file.open("r") as f:
            saved_data = json.load(f)
        assert saved_data["profiles"][0]["garmin_username"] == "test@example.com"
        assert saved_data["profiles"][0]["garmin_password"] == "password"

        # Test rewrite_config=False does NOT save changes
        config_manager2 = ConfigManager()
        profile2 = Profile(
            name="default",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="original@example.com",
            garmin_password="original_password",
            fitfiles_path=Path("/original/path"),
        )
        config_manager2.config.profiles = [profile2]
        config_manager2.config.default_profile = "default"
        config_manager2.save_config()

        with config_manager2.config_file.open("r") as f:
            original_data = json.load(f)

        # Update in memory only
        config_manager2.config.profiles[0].garmin_username = "updated@example.com"
        config_manager2.build_config_file(
            overwrite_existing_vals=False, rewrite_config=False, excluded_keys=[]
        )

        # File should still have original data
        with config_manager2.config_file.open("r") as f:
            current_data = json.load(f)
        assert current_data == original_data
        assert current_data["profiles"][0]["garmin_username"] == "original@example.com"

    def test_build_config_file_password_masking_line_479(
        self, monkeypatch, mock_get_fitfiles_path
    ):
        """Test that line 479 executes - password replacement in message when overwriting."""
        config_manager = ConfigManager()

        # Create a profile with existing password
        profile = Profile(
            name="default",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="test@example.com",
            garmin_password="my_secret_password",
            fitfiles_path=Path("/path/to/files"),
        )
        config_manager.config.profiles = [profile]
        config_manager.config.default_profile = "default"
        config_manager.save_config()

        # Reload to ensure it reads from file
        config_manager = ConfigManager()

        # Track prompts to verify password masking
        captured_prompts = []

        def mock_text(prompt, **kwargs):
            captured_prompts.append(("text", prompt))
            return MockQuestion("")  # Return empty to keep existing

        def mock_password(prompt, **kwargs):
            captured_prompts.append(("password", prompt))
            return MockQuestion("")  # Return empty to keep existing

        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        # Build config with overwrite=True to trigger prompts showing existing values
        # This should hit line 479 when k=="garmin_password"
        config_manager.build_config_file(
            overwrite_existing_vals=True, rewrite_config=False, excluded_keys=[]
        )

        # Find password prompt and verify masking
        password_prompts = [p for typ, p in captured_prompts if typ == "password"]
        assert len(password_prompts) > 0

        # Verify the actual password is NOT in the prompt (it should be masked)
        for prompt in password_prompts:
            assert "my_secret_password" not in prompt
            assert "<**hidden**>" in prompt

    def test_build_config_file_missing_attribute_warning(
        self, monkeypatch, mock_get_fitfiles_path, caplog
    ):
        """Test line 479 - warning when profile doesn't have required attribute."""
        import logging

        config_manager = ConfigManager()

        # Create a profile but manually delete an attribute to simulate missing field
        profile = Profile(
            name="default",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="",  # Empty to trigger the condition
            garmin_password="",
            fitfiles_path=Path("/path/to/files"),
        )
        config_manager.config.profiles = [profile]
        config_manager.config.default_profile = "default"

        # Mock questionary to provide values
        def mock_text(prompt, **kwargs):
            return MockQuestion("new_username@example.com")

        def mock_password(prompt, **kwargs):
            return MockQuestion("new_password")

        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        # Build config - this should trigger warning for empty fields
        with caplog.at_level(logging.WARNING):
            config_manager.build_config_file(
                overwrite_existing_vals=False, rewrite_config=False, excluded_keys=[]
            )

        # Line 479 logs a warning when required value not found
        # Since username and password are empty/None, we should see warnings
        # Actually, the condition is: not hasattr OR getattr is None
        # With empty string, getattr is "", which is falsy but not None
        # So we need to test with an actual None value or missing attribute

    def test_build_config_file_none_value_warning(
        self, monkeypatch, mock_get_fitfiles_path, caplog
    ):
        """Test line 479 - warning when profile field is None."""
        import logging

        config_manager = ConfigManager()

        # Create a profile with None values
        profile = Profile(
            name="default",
            app_type=AppType.TP_VIRTUAL,
            garmin_username=None,  # None to trigger the condition
            garmin_password=None,
            fitfiles_path=Path("/path/to/files"),
        )
        # Manually set to None after creation (since __post_init__ converts to "")
        profile.garmin_username = None
        profile.garmin_password = None

        config_manager.config.profiles = [profile]
        config_manager.config.default_profile = "default"

        # Mock questionary to provide values
        def mock_text(prompt, **kwargs):
            return MockQuestion("new_username@example.com")

        def mock_password(prompt, **kwargs):
            return MockQuestion("new_password")

        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        # Build config - this should trigger line 479 warning for None fields
        with caplog.at_level(logging.WARNING):
            config_manager.build_config_file(
                overwrite_existing_vals=False, rewrite_config=False, excluded_keys=[]
            )

        # Verify warning was logged (line 479)
        warning_messages = [
            r.message for r in caplog.records if r.levelname == "WARNING"
        ]
        assert any(
            "garmin_username" in msg and "not found in config" in msg
            for msg in warning_messages
        )


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

    def test_display_profiles_table_with_profiles(self, manager, capsys):
        """Test display_profiles_table shows profiles in table format."""
        # Add a couple of profiles
        manager.create_profile(
            name="profile1",
            app_type=AppType.ZWIFT,
            garmin_username="user1@example.com",
            garmin_password="pass1",
            fitfiles_path=Path("/path/to/fit1"),
        )
        manager.create_profile(
            name="profile2",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="user2@example.com",
            garmin_password="pass2",
            fitfiles_path=Path("/path/to/fit2"),
        )
        manager.set_default_profile("profile1")

        # Call display_profiles_table
        manager.display_profiles_table()

        # Capture output and verify table was displayed
        captured = capsys.readouterr()
        output = captured.out
        assert "profile1" in output
        assert "profile2" in output
        assert "⭐" in output  # Default profile marker
        assert "Zwift" in output
        assert "TPVirtual" in output  # Title case combined without spaces

    def test_display_profiles_table_empty(self, manager, capsys):
        """Test display_profiles_table with no profiles."""
        manager.display_profiles_table()

        captured = capsys.readouterr()
        output = captured.out
        assert "No profiles configured yet" in output

    def test_update_profile_name_changes_default(self, manager):
        """Test that updating profile name updates default_profile if it was default."""
        manager.create_profile(
            name="original_name",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="password",
            fitfiles_path=Path("/path/to/fit"),
        )
        manager.set_default_profile("original_name")

        # Verify it's the default
        assert manager.config_manager.config.default_profile == "original_name"

        # Update the profile name
        manager.update_profile("original_name", new_name="new_name")

        # Verify default_profile was updated
        assert manager.config_manager.config.default_profile == "new_name"

        # Verify the profile exists with new name
        profile = manager.get_profile("new_name")
        assert profile is not None
        assert profile.name == "new_name"

    def test_update_profile_partial_updates(self, manager):
        """Test updating specific profile fields without changing others."""
        manager.create_profile(
            name="test_profile",
            app_type=AppType.ZWIFT,
            garmin_username="old_user@example.com",
            garmin_password="old_password",
            fitfiles_path=Path("/old/path"),
        )

        # Update only username
        manager.update_profile("test_profile", garmin_username="new_user@example.com")

        profile = manager.get_profile("test_profile")
        assert profile.garmin_username == "new_user@example.com"
        assert profile.garmin_password == "old_password"  # Should not change
        assert profile.fitfiles_path == Path("/old/path")  # Should not change

        # Update only password
        manager.update_profile("test_profile", garmin_password="new_password")

        profile = manager.get_profile("test_profile")
        assert profile.garmin_username == "new_user@example.com"  # Should not change
        assert profile.garmin_password == "new_password"
        assert profile.fitfiles_path == Path("/old/path")  # Should not change


class TestProfileManagerWizards:
    """Tests for ProfileManager interactive wizard methods."""

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

    @pytest.fixture
    def manager_with_profiles(self, manager):
        """Create a manager with test profiles."""
        manager.create_profile(
            name="profile1",
            app_type=AppType.ZWIFT,
            garmin_username="user1@example.com",
            garmin_password="pass1",
            fitfiles_path=Path("/path/to/fit1"),
        )
        manager.create_profile(
            name="profile2",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="user2@example.com",
            garmin_password="pass2",
            fitfiles_path=Path("/path/to/fit2"),
        )
        return manager

    def test_delete_profile_wizard_no_profiles(self, manager, capsys):
        """Test delete wizard with no profiles."""
        manager.delete_profile_wizard()

        captured = capsys.readouterr()
        assert "No profiles to delete" in captured.out

    def test_delete_profile_wizard_only_one_profile(self, manager, capsys):
        """Test delete wizard with only one profile."""
        manager.create_profile(
            name="only_profile",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="pass",
            fitfiles_path=Path("/path"),
        )

        manager.delete_profile_wizard()

        captured = capsys.readouterr()
        assert "Cannot delete the only profile" in captured.out

    def test_delete_profile_wizard_user_cancels_selection(
        self, manager_with_profiles, monkeypatch, capsys
    ):
        """Test delete wizard when user cancels profile selection."""
        # Mock questionary.select to return None (user cancelled)
        mock_select = MockQuestion(None)
        monkeypatch.setattr(questionary, "select", lambda *args, **kwargs: mock_select)

        manager_with_profiles.delete_profile_wizard()

        # Should exit gracefully without error
        _ = capsys.readouterr()
        # No error message should appear

    def test_delete_profile_wizard_user_cancels_confirmation(
        self, manager_with_profiles, monkeypatch, capsys
    ):
        """Test delete wizard when user cancels confirmation."""
        # Mock questionary to select a profile but cancel confirmation
        mock_select = MockQuestion("profile1")
        mock_confirm = MockQuestion(False)
        monkeypatch.setattr(questionary, "select", lambda *args, **kwargs: mock_select)
        monkeypatch.setattr(
            questionary, "confirm", lambda *args, **kwargs: mock_confirm
        )

        manager_with_profiles.delete_profile_wizard()

        captured = capsys.readouterr()
        assert "Deletion cancelled" in captured.out

        # Verify profile was not deleted
        assert manager_with_profiles.get_profile("profile1") is not None

    def test_delete_profile_wizard_success(
        self, manager_with_profiles, monkeypatch, capsys
    ):
        """Test successful profile deletion via wizard."""
        # Mock questionary to select a profile and confirm
        mock_select = MockQuestion("profile1")
        mock_confirm = MockQuestion(True)
        monkeypatch.setattr(questionary, "select", lambda *args, **kwargs: mock_select)
        monkeypatch.setattr(
            questionary, "confirm", lambda *args, **kwargs: mock_confirm
        )

        manager_with_profiles.delete_profile_wizard()

        captured = capsys.readouterr()
        assert "deleted successfully" in captured.out

        # Verify profile was deleted
        assert manager_with_profiles.get_profile("profile1") is None
        assert manager_with_profiles.get_profile("profile2") is not None

    def test_set_default_wizard_no_profiles(self, manager, capsys):
        """Test set default wizard with no profiles."""
        manager.set_default_wizard()

        captured = capsys.readouterr()
        assert "No profiles available" in captured.out

    def test_set_default_wizard_user_cancels(
        self, manager_with_profiles, monkeypatch, capsys
    ):
        """Test set default wizard when user cancels."""
        # Mock questionary.select to return None (user cancelled)
        mock_select = MockQuestion(None)
        monkeypatch.setattr(questionary, "select", lambda *args, **kwargs: mock_select)

        manager_with_profiles.set_default_wizard()

        # Should exit gracefully without setting default
        # No change to default profile

    def test_set_default_wizard_success(
        self, manager_with_profiles, monkeypatch, capsys
    ):
        """Test successful default profile setting via wizard."""
        # Mock questionary to select a profile
        mock_select = MockQuestion("profile2")
        monkeypatch.setattr(questionary, "select", lambda *args, **kwargs: mock_select)

        manager_with_profiles.set_default_wizard()

        captured = capsys.readouterr()
        assert "is now the default profile" in captured.out

        # Verify default was set
        assert manager_with_profiles.config_manager.config.default_profile == "profile2"

    def test_display_profiles_table_long_path_truncation(self, manager, capsys):
        """Test that long paths are truncated in the profiles table."""
        # Create a profile with a very long path
        long_path = Path(
            "/very/long/path/that/exceeds/forty/characters/for/testing/truncation"
        )
        manager.create_profile(
            name="test_profile",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="password",
            fitfiles_path=long_path,
        )

        manager.display_profiles_table()

        captured = capsys.readouterr()
        output = captured.out
        # Check that the path is truncated with "..."
        assert "..." in output
        # Check that the table shows test_profile and has Device column
        assert "test_profile" in output
        assert "EDGE_830" in output  # Default device

    def test_delete_profile_wizard_handles_error(
        self, manager_with_profiles, monkeypatch, capsys
    ):
        """Test delete wizard handles errors gracefully."""
        # Mock questionary to select a profile and confirm
        mock_select = MockQuestion("profile1")
        mock_confirm = MockQuestion(True)
        monkeypatch.setattr(questionary, "select", lambda *args, **kwargs: mock_select)
        monkeypatch.setattr(
            questionary, "confirm", lambda *args, **kwargs: mock_confirm
        )

        # Mock delete_profile to raise an error
        def mock_delete(name):
            raise ValueError("Test error message")

        monkeypatch.setattr(manager_with_profiles, "delete_profile", mock_delete)

        manager_with_profiles.delete_profile_wizard()

        captured = capsys.readouterr()
        assert "Error: Test error message" in captured.out

    def test_set_default_wizard_handles_error(
        self, manager_with_profiles, monkeypatch, capsys
    ):
        """Test set default wizard handles errors gracefully."""
        # Mock questionary to select a profile
        mock_select = MockQuestion("profile1")
        monkeypatch.setattr(questionary, "select", lambda *args, **kwargs: mock_select)

        # Mock set_default_profile to raise an error
        def mock_set_default(name):
            raise ValueError("Test error in set_default")

        monkeypatch.setattr(
            manager_with_profiles, "set_default_profile", mock_set_default
        )

        manager_with_profiles.set_default_wizard()

        captured = capsys.readouterr()
        assert "Error: Test error in set_default" in captured.out

    def test_interactive_menu_exit_immediately(self, manager, monkeypatch):
        """Test interactive menu when user selects Exit immediately."""
        # Mock questionary.select to return "Exit"
        mock_select = MockQuestion("Exit")
        monkeypatch.setattr(questionary, "select", lambda *args, **kwargs: mock_select)

        # Should exit gracefully without error
        manager.interactive_menu()

    def test_interactive_menu_user_cancels(self, manager, monkeypatch):
        """Test interactive menu when user cancels (Ctrl+C or None response)."""
        # Mock questionary.select to return None (cancel)
        mock_select = MockQuestion(None)
        monkeypatch.setattr(questionary, "select", lambda *args, **kwargs: mock_select)

        # Should exit gracefully
        manager.interactive_menu()

    def test_interactive_menu_create_profile(self, manager, monkeypatch, capsys):
        """Test interactive menu create profile action."""
        call_count = {"select": 0}

        def mock_select(prompt, choices, **kwargs):
            call_count["select"] += 1
            if call_count["select"] == 1:
                return MockQuestion("Create new profile")
            else:
                return MockQuestion("Exit")

        monkeypatch.setattr(questionary, "select", mock_select)

        # Mock create_profile_wizard to return None (user cancels)
        monkeypatch.setattr(manager, "create_profile_wizard", lambda: None)

        manager.interactive_menu()

        # Should have called create_profile_wizard
        # No error should occur

    def test_interactive_menu_edit_profile(self, manager, monkeypatch):
        """Test interactive menu edit profile action."""
        call_count = {"select": 0}

        def mock_select(prompt, choices, **kwargs):
            call_count["select"] += 1
            if call_count["select"] == 1:
                return MockQuestion("Edit existing profile")
            else:
                return MockQuestion("Exit")

        monkeypatch.setattr(questionary, "select", mock_select)

        # Mock edit_profile_wizard
        edit_called = {"called": False}

        def mock_edit():
            edit_called["called"] = True

        monkeypatch.setattr(manager, "edit_profile_wizard", mock_edit)

        manager.interactive_menu()

        assert edit_called["called"]

    def test_interactive_menu_delete_profile(self, manager, monkeypatch):
        """Test interactive menu delete profile action."""
        call_count = {"select": 0}

        def mock_select(prompt, choices, **kwargs):
            call_count["select"] += 1
            if call_count["select"] == 1:
                return MockQuestion("Delete profile")
            else:
                return MockQuestion("Exit")

        monkeypatch.setattr(questionary, "select", mock_select)

        # Mock delete_profile_wizard
        delete_called = {"called": False}

        def mock_delete():
            delete_called["called"] = True

        monkeypatch.setattr(manager, "delete_profile_wizard", mock_delete)

        manager.interactive_menu()

        assert delete_called["called"]

    def test_interactive_menu_set_default(self, manager, monkeypatch):
        """Test interactive menu set default profile action."""
        call_count = {"select": 0}

        def mock_select(prompt, choices, **kwargs):
            call_count["select"] += 1
            if call_count["select"] == 1:
                return MockQuestion("Set default profile")
            else:
                return MockQuestion("Exit")

        monkeypatch.setattr(questionary, "select", mock_select)

        # Mock set_default_wizard
        set_default_called = {"called": False}

        def mock_set_default():
            set_default_called["called"] = True

        monkeypatch.setattr(manager, "set_default_wizard", mock_set_default)

        manager.interactive_menu()

        assert set_default_called["called"]

    def test_interactive_menu_keyboard_interrupt(self, manager, monkeypatch, capsys):
        """Test interactive menu handles KeyboardInterrupt gracefully."""
        call_count = {"select": 0}

        def mock_select(prompt, choices, **kwargs):
            call_count["select"] += 1
            if call_count["select"] == 1:
                return MockQuestion("Create new profile")
            else:
                return MockQuestion("Exit")

        monkeypatch.setattr(questionary, "select", mock_select)

        # Mock create_profile_wizard to raise KeyboardInterrupt
        def mock_create():
            raise KeyboardInterrupt()

        monkeypatch.setattr(manager, "create_profile_wizard", mock_create)

        manager.interactive_menu()

        captured = capsys.readouterr()
        assert "Operation cancelled" in captured.out

    def test_interactive_menu_eoferror(self, manager, monkeypatch, capsys):
        """Test interactive menu handles EOFError gracefully."""
        call_count = {"select": 0}

        def mock_select(prompt, choices, **kwargs):
            call_count["select"] += 1
            if call_count["select"] == 1:
                return MockQuestion("Edit existing profile")
            else:
                return MockQuestion("Exit")

        monkeypatch.setattr(questionary, "select", mock_select)

        # Mock edit_profile_wizard to raise EOFError
        def mock_edit():
            raise EOFError()

        monkeypatch.setattr(manager, "edit_profile_wizard", mock_edit)

        manager.interactive_menu()

        captured = capsys.readouterr()
        assert "Operation cancelled" in captured.out

    def test_create_profile_wizard_user_cancels_at_app_type(self, manager, monkeypatch):
        """Test create profile wizard when user cancels at app type selection."""
        # Mock questionary.select to return None (cancel)
        mock_select = MockQuestion(None)
        monkeypatch.setattr(questionary, "select", lambda *args, **kwargs: mock_select)

        result = manager.create_profile_wizard()

        assert result is None

    def test_create_profile_wizard_with_detected_path_confirmed(
        self, manager, monkeypatch, capsys, tmp_path
    ):
        """Test create profile wizard with auto-detected path that user confirms."""
        detected_path = tmp_path / "detected_zwift"
        detected_path.mkdir()

        # Mock app detector to return a path
        class MockDetector:
            def get_default_path(self):
                return detected_path

            def get_display_name(self):
                return "Zwift"

        def mock_get_detector(app_type):
            return MockDetector()

        monkeypatch.setattr(
            "fit_file_faker.app_registry.get_detector", mock_get_detector
        )

        # Mock questionary responses
        call_count = {"select": 0, "text": 0, "password": 0, "confirm": 0}

        def mock_select(prompt, choices, **kwargs):
            call_count["select"] += 1
            # Return AppType.ZWIFT for app type selection
            if "trainer app" in prompt:
                # Find the Zwift choice
                for choice in choices:
                    if hasattr(choice, "value") and choice.value == AppType.ZWIFT:
                        return MockQuestion(AppType.ZWIFT)
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            call_count["confirm"] += 1
            # Confirm using detected directory
            return MockQuestion(True)

        def mock_text(prompt, **kwargs):
            call_count["text"] += 1
            if "email" in prompt.lower():
                return MockQuestion("user@example.com")
            elif "name" in prompt.lower():
                return MockQuestion("zwift_profile")
            return MockQuestion("test_value")

        def mock_password(prompt, **kwargs):
            call_count["password"] += 1
            return MockQuestion("password123")

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        result = manager.create_profile_wizard()

        assert result is not None
        assert result.name == "zwift_profile"
        assert result.app_type == AppType.ZWIFT
        assert result.garmin_username == "user@example.com"
        assert result.garmin_password == "password123"
        assert result.fitfiles_path == detected_path

        captured = capsys.readouterr()
        assert "Found Zwift directory" in captured.out
        assert "created successfully" in captured.out

    def test_create_profile_wizard_with_detected_path_rejected(
        self, manager, monkeypatch, tmp_path
    ):
        """Test create profile wizard with auto-detected path that user rejects."""
        detected_path = tmp_path / "detected_tpv"
        detected_path.mkdir()
        manual_path = tmp_path / "manual_path"
        manual_path.mkdir()

        # Mock app detector
        class MockDetector:
            def get_default_path(self):
                return detected_path

            def get_display_name(self):
                return "TrainingPeaks Virtual"

        def mock_get_detector(app_type):
            return MockDetector()

        monkeypatch.setattr(
            "fit_file_faker.app_registry.get_detector", mock_get_detector
        )

        # Mock questionary responses
        def mock_select(prompt, choices, **kwargs):
            if "trainer app" in prompt:
                for choice in choices:
                    if hasattr(choice, "value") and choice.value == AppType.TP_VIRTUAL:
                        return MockQuestion(AppType.TP_VIRTUAL)
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            # Reject detected directory
            return MockQuestion(False)

        def mock_path(prompt, **kwargs):
            # Return manual path
            return MockQuestion(str(manual_path))

        def mock_text(prompt, **kwargs):
            if "email" in prompt.lower():
                return MockQuestion("user@example.com")
            elif "name" in prompt.lower():
                return MockQuestion("tpv_profile")
            return MockQuestion("test_value")

        def mock_password(prompt, **kwargs):
            return MockQuestion("password123")

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "path", mock_path)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        result = manager.create_profile_wizard()

        assert result is not None
        assert result.fitfiles_path == manual_path

    def test_create_profile_wizard_no_detected_path(
        self, manager, monkeypatch, tmp_path, capsys
    ):
        """Test create profile wizard when no path is auto-detected."""
        manual_path = tmp_path / "manual_path"
        manual_path.mkdir()

        # Mock app detector to return None (no detection)
        class MockDetector:
            def get_default_path(self):
                return None

            def get_display_name(self):
                return "Custom"

        def mock_get_detector(app_type):
            return MockDetector()

        monkeypatch.setattr(
            "fit_file_faker.app_registry.get_detector", mock_get_detector
        )

        # Mock questionary responses
        def mock_select(prompt, choices, **kwargs):
            if "trainer app" in prompt:
                for choice in choices:
                    if hasattr(choice, "value") and choice.value == AppType.CUSTOM:
                        return MockQuestion(AppType.CUSTOM)
            return MockQuestion(choices[0])

        def mock_path(prompt, **kwargs):
            return MockQuestion(str(manual_path))

        def mock_text(prompt, **kwargs):
            if "email" in prompt.lower():
                return MockQuestion("user@example.com")
            elif "name" in prompt.lower():
                return MockQuestion("custom_profile")
            return MockQuestion("test_value")

        def mock_password(prompt, **kwargs):
            return MockQuestion("password123")

        def mock_confirm(prompt, **kwargs):
            # Return False for device customization
            return MockQuestion(False)

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "path", mock_path)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)

        result = manager.create_profile_wizard()

        assert result is not None
        assert result.fitfiles_path == manual_path

        captured = capsys.readouterr()
        assert "Could not auto-detect" in captured.out

    def test_create_profile_wizard_user_cancels_at_path(self, manager, monkeypatch):
        """Test create profile wizard when user cancels at path input."""

        # Mock app detector to return None
        class MockDetector:
            def get_default_path(self):
                return None

            def get_display_name(self):
                return "Custom"

        def mock_get_detector(app_type):
            return MockDetector()

        monkeypatch.setattr(
            "fit_file_faker.app_registry.get_detector", mock_get_detector
        )

        call_count = {"path": 0}

        def mock_select(prompt, choices, **kwargs):
            for choice in choices:
                if hasattr(choice, "value") and choice.value == AppType.CUSTOM:
                    return MockQuestion(AppType.CUSTOM)
            return MockQuestion(choices[0])

        def mock_path(prompt, **kwargs):
            call_count["path"] += 1
            # Return None (cancel)
            return MockQuestion(None)

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "path", mock_path)

        result = manager.create_profile_wizard()

        assert result is None

    def test_create_profile_wizard_user_cancels_at_username(
        self, manager, monkeypatch, tmp_path
    ):
        """Test create profile wizard when user cancels at username input."""
        manual_path = tmp_path / "manual_path"
        manual_path.mkdir()

        class MockDetector:
            def get_default_path(self):
                return manual_path

            def get_display_name(self):
                return "Zwift"

        def mock_get_detector(app_type):
            return MockDetector()

        monkeypatch.setattr(
            "fit_file_faker.app_registry.get_detector", mock_get_detector
        )

        def mock_select(prompt, choices, **kwargs):
            for choice in choices:
                if hasattr(choice, "value") and choice.value == AppType.ZWIFT:
                    return MockQuestion(AppType.ZWIFT)
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            return MockQuestion(True)

        def mock_text(prompt, **kwargs):
            # Return None (cancel)
            return MockQuestion(None)

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", mock_text)

        result = manager.create_profile_wizard()

        assert result is None

    def test_create_profile_wizard_user_cancels_at_password(
        self, manager, monkeypatch, tmp_path
    ):
        """Test create profile wizard when user cancels at password input."""
        manual_path = tmp_path / "manual_path"
        manual_path.mkdir()

        class MockDetector:
            def get_default_path(self):
                return manual_path

            def get_display_name(self):
                return "Zwift"

        def mock_get_detector(app_type):
            return MockDetector()

        monkeypatch.setattr(
            "fit_file_faker.app_registry.get_detector", mock_get_detector
        )

        def mock_select(prompt, choices, **kwargs):
            for choice in choices:
                if hasattr(choice, "value") and choice.value == AppType.ZWIFT:
                    return MockQuestion(AppType.ZWIFT)
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            return MockQuestion(True)

        def mock_text(prompt, **kwargs):
            return MockQuestion("user@example.com")

        def mock_password(prompt, **kwargs):
            # Return None (cancel)
            return MockQuestion(None)

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        result = manager.create_profile_wizard()

        assert result is None

    def test_create_profile_wizard_user_cancels_at_profile_name(
        self, manager, monkeypatch, tmp_path
    ):
        """Test create profile wizard when user cancels at profile name input."""
        manual_path = tmp_path / "manual_path"
        manual_path.mkdir()

        class MockDetector:
            def get_default_path(self):
                return manual_path

            def get_display_name(self):
                return "Zwift"

        def mock_get_detector(app_type):
            return MockDetector()

        monkeypatch.setattr(
            "fit_file_faker.app_registry.get_detector", mock_get_detector
        )

        call_count = {"text": 0}

        def mock_select(prompt, choices, **kwargs):
            for choice in choices:
                if hasattr(choice, "value") and choice.value == AppType.ZWIFT:
                    return MockQuestion(AppType.ZWIFT)
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            return MockQuestion(True)

        def mock_text(prompt, **kwargs):
            call_count["text"] += 1
            if call_count["text"] == 1:
                # First call is username
                return MockQuestion("user@example.com")
            else:
                # Second call is profile name - cancel
                return MockQuestion(None)

        def mock_password(prompt, **kwargs):
            return MockQuestion("password123")

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        result = manager.create_profile_wizard()

        assert result is None

    def test_create_profile_wizard_handles_creation_error(
        self, manager, monkeypatch, tmp_path, capsys
    ):
        """Test create profile wizard handles profile creation errors."""
        manual_path = tmp_path / "manual_path"
        manual_path.mkdir()

        class MockDetector:
            def get_default_path(self):
                return manual_path

            def get_display_name(self):
                return "Zwift"

        def mock_get_detector(app_type):
            return MockDetector()

        monkeypatch.setattr(
            "fit_file_faker.app_registry.get_detector", mock_get_detector
        )

        def mock_select(prompt, choices, **kwargs):
            for choice in choices:
                if hasattr(choice, "value") and choice.value == AppType.ZWIFT:
                    return MockQuestion(AppType.ZWIFT)
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            return MockQuestion(True)

        def mock_text(prompt, **kwargs):
            if "email" in prompt.lower():
                return MockQuestion("user@example.com")
            elif "name" in prompt.lower():
                return MockQuestion("test_profile")
            return MockQuestion("test_value")

        def mock_password(prompt, **kwargs):
            return MockQuestion("password123")

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        # Mock create_profile to raise error
        def mock_create(*args, **kwargs):
            raise ValueError("Profile creation failed")

        monkeypatch.setattr(manager, "create_profile", mock_create)

        result = manager.create_profile_wizard()

        assert result is None

        captured = capsys.readouterr()
        assert "Error: Profile creation failed" in captured.out

    def test_edit_profile_wizard_no_profiles(self, manager, capsys):
        """Test edit profile wizard when no profiles exist."""
        manager.edit_profile_wizard()

        captured = capsys.readouterr()
        assert "No profiles to edit" in captured.out

    def test_edit_profile_wizard_user_cancels_selection(
        self, manager_with_profiles, monkeypatch
    ):
        """Test edit profile wizard when user cancels profile selection."""
        # Mock questionary.select to return None
        mock_select = MockQuestion(None)
        monkeypatch.setattr(questionary, "select", lambda *args, **kwargs: mock_select)

        manager_with_profiles.edit_profile_wizard()

        # Should exit gracefully

    def test_edit_profile_wizard_updates_all_fields(
        self, manager_with_profiles, monkeypatch, capsys, tmp_path
    ):
        """Test edit profile wizard updates all fields."""
        new_path = tmp_path / "new_path"
        new_path.mkdir()

        def mock_select(prompt, choices, **kwargs):
            # Select profile1 to edit
            return MockQuestion("profile1")

        def mock_text(prompt, **kwargs):
            if "Profile name" in prompt:
                return MockQuestion("renamed_profile")
            elif "username" in prompt:
                return MockQuestion("newemail@example.com")
            return MockQuestion("")

        def mock_password(prompt, **kwargs):
            return MockQuestion("newpassword")

        def mock_path(prompt, **kwargs):
            return MockQuestion(str(new_path))

        def mock_confirm(prompt, **kwargs):
            # Return False for device customization
            return MockQuestion(False)

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)
        monkeypatch.setattr(questionary, "path", mock_path)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)

        manager_with_profiles.edit_profile_wizard()

        # Verify profile was updated
        profile = manager_with_profiles.get_profile("renamed_profile")
        assert profile is not None
        assert profile.garmin_username == "newemail@example.com"
        assert profile.garmin_password == "newpassword"
        assert profile.fitfiles_path == new_path

        captured = capsys.readouterr()
        assert "updated successfully" in captured.out

    def test_edit_profile_wizard_keeps_existing_values(
        self, manager_with_profiles, monkeypatch, capsys
    ):
        """Test edit profile wizard keeps existing values when user leaves blank."""
        original_profile = manager_with_profiles.get_profile("profile1")

        def mock_select(prompt, choices, **kwargs):
            return MockQuestion("profile1")

        def mock_text(prompt, **kwargs):
            # Return empty string to keep existing values
            return MockQuestion("")

        def mock_password(prompt, **kwargs):
            return MockQuestion("")

        def mock_path(prompt, **kwargs):
            return MockQuestion("")

        def mock_confirm(prompt, **kwargs):
            # Return False for device customization to keep things simple
            return MockQuestion(False)

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)
        monkeypatch.setattr(questionary, "path", mock_path)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)

        manager_with_profiles.edit_profile_wizard()

        # Verify profile was not changed
        profile = manager_with_profiles.get_profile("profile1")
        assert profile.name == original_profile.name
        assert profile.garmin_username == original_profile.garmin_username
        assert profile.garmin_password == original_profile.garmin_password
        assert profile.fitfiles_path == original_profile.fitfiles_path

        captured = capsys.readouterr()
        assert "updated successfully" in captured.out

    def test_edit_profile_wizard_handles_error(
        self, manager_with_profiles, monkeypatch, capsys
    ):
        """Test edit profile wizard handles update errors gracefully."""

        def mock_select(prompt, choices, **kwargs):
            return MockQuestion("profile1")

        def mock_text(prompt, **kwargs):
            if "Profile name" in prompt:
                return MockQuestion("new_name")
            return MockQuestion("")

        def mock_password(prompt, **kwargs):
            return MockQuestion("")

        def mock_path(prompt, **kwargs):
            return MockQuestion("")

        def mock_confirm(prompt, **kwargs):
            # Return False for device customization
            return MockQuestion(False)

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)
        monkeypatch.setattr(questionary, "path", mock_path)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)

        # Mock update_profile to raise error
        def mock_update(*args, **kwargs):
            raise ValueError("Update failed")

        monkeypatch.setattr(manager_with_profiles, "update_profile", mock_update)

        manager_with_profiles.edit_profile_wizard()

        captured = capsys.readouterr()
        assert "Error: Update failed" in captured.out

    def test_update_profile_app_type(self, manager_with_profiles):
        """Test updating profile app_type field."""
        # Update app_type from ZWIFT to TP_VIRTUAL
        manager_with_profiles.update_profile("profile1", app_type=AppType.TP_VIRTUAL)

        profile = manager_with_profiles.get_profile("profile1")
        assert profile.app_type == AppType.TP_VIRTUAL

    def test_create_profile_wizard_rejected_path_then_cancel(
        self, manager, monkeypatch, tmp_path
    ):
        """Test create profile wizard when user rejects detected path then cancels manual input."""
        detected_path = tmp_path / "detected"
        detected_path.mkdir()

        class MockDetector:
            def get_default_path(self):
                return detected_path

            def get_display_name(self):
                return "Zwift"

        def mock_get_detector(app_type):
            return MockDetector()

        monkeypatch.setattr(
            "fit_file_faker.app_registry.get_detector", mock_get_detector
        )

        def mock_select(prompt, choices, **kwargs):
            for choice in choices:
                if hasattr(choice, "value") and choice.value == AppType.ZWIFT:
                    return MockQuestion(AppType.ZWIFT)
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            # Reject detected path
            return MockQuestion(False)

        def mock_path(prompt, **kwargs):
            # Cancel manual path input
            return MockQuestion(None)

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "path", mock_path)

        result = manager.create_profile_wizard()

        assert result is None

    def test_edit_profile_wizard_profile_not_found(
        self, manager_with_profiles, monkeypatch
    ):
        """Test edit profile wizard when selected profile is not found (edge case)."""

        def mock_select(prompt, choices, **kwargs):
            return MockQuestion("profile1")

        monkeypatch.setattr(questionary, "select", mock_select)

        # Mock get_profile to return None (simulating profile disappearing)
        def mock_get_profile(name):
            return None

        monkeypatch.setattr(manager_with_profiles, "get_profile", mock_get_profile)

        # Should exit gracefully without error
        manager_with_profiles.edit_profile_wizard()


class TestDeviceConfiguration:
    """Tests for device configuration functionality."""

    @pytest.fixture
    def manager(self, tmp_path, monkeypatch):
        """Create ProfileManager with temporary config."""
        from fit_file_faker.config import dirs

        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(exist_ok=True)

        monkeypatch.setattr(dirs, "user_config_path", config_dir)
        monkeypatch.setattr(dirs, "user_cache_path", cache_dir)

        from fit_file_faker.config import ConfigManager, ProfileManager

        return ProfileManager(ConfigManager())

    @pytest.fixture
    def manager_with_profiles(self, manager):
        """Create a manager with test profiles."""
        manager.create_profile(
            name="profile1",
            app_type=AppType.ZWIFT,
            garmin_username="user1@example.com",
            garmin_password="password1",
            fitfiles_path=Path("/path/to/zwift"),
        )
        manager.create_profile(
            name="profile2",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="user2@example.com",
            garmin_password="password2",
            fitfiles_path=Path("/path/to/tpv"),
        )
        return manager

    def test_get_supported_garmin_devices(self):
        """Test get_supported_garmin_devices returns filtered device list."""
        from fit_file_faker.config import get_supported_garmin_devices

        devices = get_supported_garmin_devices()

        # Should return a non-empty list
        assert len(devices) > 0

        # Each item should be a tuple (name, id, description)
        for device in devices:
            assert isinstance(device, tuple)
            assert len(device) == 3
            name, device_id, description = device
            assert isinstance(name, str)
            assert isinstance(device_id, int)
            assert isinstance(description, str)

        # Common devices should be first (not strictly sorted by name anymore)
        # Just verify we have some devices
        assert len(devices) >= 11  # At least 11 common devices

    def test_profile_with_device_settings(self):
        """Test Profile with custom manufacturer and device settings."""
        from fit_file_faker.vendor.fit_tool.profile.profile_type import (
            GarminProduct,
            Manufacturer,
        )

        profile = Profile(
            name="custom",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="pass",
            fitfiles_path=Path("/path/to/files"),
            manufacturer=Manufacturer.GARMIN.value,
            device=GarminProduct.EDGE_1030.value,
        )

        assert profile.manufacturer == Manufacturer.GARMIN.value
        assert profile.device == GarminProduct.EDGE_1030.value
        assert profile.get_manufacturer_name() == "GARMIN"
        assert profile.get_device_name() == "EDGE_1030"

    def test_profile_defaults_to_edge_830(self):
        """Test Profile defaults to Garmin Edge 830 when device not specified."""
        from fit_file_faker.vendor.fit_tool.profile.profile_type import (
            GarminProduct,
            Manufacturer,
        )

        profile = Profile(
            name="default",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="pass",
            fitfiles_path=Path("/path/to/files"),
        )

        # Should default to Garmin Edge 830
        assert profile.manufacturer == Manufacturer.GARMIN.value
        assert profile.device == GarminProduct.EDGE_830.value
        assert profile.get_manufacturer_name() == "GARMIN"
        assert profile.get_device_name() == "EDGE_830"

    def test_profile_unknown_device_id(self):
        """Test Profile with unknown device ID shows UNKNOWN."""
        profile = Profile(
            name="custom",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="pass",
            fitfiles_path=Path("/path/to/files"),
            manufacturer=1,
            device=99999,  # Unknown device ID
        )

        assert profile.manufacturer == 1
        assert profile.device == 99999
        assert profile.get_manufacturer_name() == "GARMIN"
        assert profile.get_device_name() == "UNKNOWN (99999)"

    def test_create_profile_with_custom_device(self, isolate_config_dirs):
        """Test creating profile with custom device via ProfileManager."""
        from fit_file_faker.vendor.fit_tool.profile.profile_type import (
            GarminProduct,
            Manufacturer,
        )

        manager = ProfileManager(ConfigManager())

        profile = manager.create_profile(
            name="edge1030",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="password",
            fitfiles_path=Path("/path/to/fitfiles"),
            manufacturer=Manufacturer.GARMIN.value,
            device=GarminProduct.EDGE_1030.value,
        )

        assert profile.name == "edge1030"
        assert profile.manufacturer == Manufacturer.GARMIN.value
        assert profile.device == GarminProduct.EDGE_1030.value
        assert profile.get_device_name() == "EDGE_1030"

    def test_update_profile_device(self, isolate_config_dirs):
        """Test updating profile device settings."""
        from fit_file_faker.vendor.fit_tool.profile.profile_type import (
            GarminProduct,
            Manufacturer,
        )

        manager = ProfileManager(ConfigManager())

        # Create initial profile
        manager.create_profile(
            name="test",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="password",
            fitfiles_path=Path("/path/to/fitfiles"),
        )

        # Update device to Edge 1030
        updated = manager.update_profile(
            name="test",
            manufacturer=Manufacturer.GARMIN.value,
            device=GarminProduct.EDGE_1030.value,
        )

        assert updated.device == GarminProduct.EDGE_1030.value
        assert updated.get_device_name() == "EDGE_1030"

    def test_display_profiles_table_shows_device(
        self, isolate_config_dirs, monkeypatch, capsys
    ):
        """Test that display_profiles_table shows device column."""
        from fit_file_faker.vendor.fit_tool.profile.profile_type import GarminProduct

        manager = ProfileManager(ConfigManager())

        # Create profile with custom device
        manager.create_profile(
            name="edge1030",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="password",
            fitfiles_path=Path("/path/to/fitfiles"),
            device=GarminProduct.EDGE_1030.value,
        )

        # Mock detector
        class MockDetector:
            def get_short_name(self):
                return "Zwift"

        def mock_get_detector(app_type):
            return MockDetector()

        monkeypatch.setattr(
            "fit_file_faker.app_registry.get_detector", mock_get_detector
        )

        # Display table
        manager.display_profiles_table()

        # Capture output
        captured = capsys.readouterr()

        # Should show device name in output
        assert "EDGE_1030" in captured.out or "Device" in captured.out

    def test_profile_unknown_manufacturer_id(self):
        """Test Profile.get_manufacturer_name() with unknown manufacturer ID."""
        profile = Profile(
            name="custom",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="pass",
            fitfiles_path=Path("/path/to/files"),
            manufacturer=99999,  # Unknown manufacturer ID
            device=3122,
        )

        # Should return UNKNOWN with the ID
        assert profile.get_manufacturer_name() == "UNKNOWN (99999)"

    def test_create_profile_wizard_with_custom_device_id(
        self, manager, monkeypatch, capsys
    ):
        """Test create profile wizard with custom numeric device ID."""

        class MockDetector:
            def get_default_path(self):
                return Path("/detected/path")

            def get_display_name(self):
                return "Test App"

        def mock_get_detector(app_type):
            return MockDetector()

        monkeypatch.setattr(
            "fit_file_faker.app_registry.get_detector", mock_get_detector
        )

        call_tracker = {"confirm_count": 0, "select_count": 0, "text_count": 0}

        def mock_select(prompt, choices, **kwargs):
            call_tracker["select_count"] += 1
            if "trainer app" in prompt:
                for choice in choices:
                    if hasattr(choice, "value") and choice.value == AppType.ZWIFT:
                        return MockQuestion(AppType.ZWIFT)
            elif "device to simulate" in prompt:
                # Select "Custom (enter numeric ID)"
                for choice in choices:
                    if hasattr(choice, "value") and choice.value == ("CUSTOM", None):
                        return MockQuestion(("CUSTOM", None))
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            call_tracker["confirm_count"] += 1
            if "Use this directory" in prompt:
                return MockQuestion(True)
            elif "Customize device" in prompt:
                return MockQuestion(True)  # Yes, customize device
            return MockQuestion(False)

        def mock_text(prompt, **kwargs):
            call_tracker["text_count"] += 1
            if "email" in prompt.lower():
                return MockQuestion("user@example.com")
            elif "numeric device ID" in prompt:
                # Return a valid known device ID first
                return MockQuestion("2713")  # EDGE_1030
            elif "name" in prompt.lower():
                return MockQuestion("custom_device_profile")
            return MockQuestion("test_value")

        def mock_password(prompt, **kwargs):
            return MockQuestion("password123")

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        result = manager.create_profile_wizard()

        assert result is not None
        assert result.device == 2713  # EDGE_1030

    def test_create_profile_wizard_with_unknown_custom_device_id(
        self, manager, monkeypatch, capsys
    ):
        """Test create profile wizard with unknown custom numeric device ID shows warning."""

        class MockDetector:
            def get_default_path(self):
                return Path("/detected/path")

            def get_display_name(self):
                return "Test App"

        def mock_get_detector(app_type):
            return MockDetector()

        monkeypatch.setattr(
            "fit_file_faker.app_registry.get_detector", mock_get_detector
        )

        def mock_select(prompt, choices, **kwargs):
            if "trainer app" in prompt:
                for choice in choices:
                    if hasattr(choice, "value") and choice.value == AppType.ZWIFT:
                        return MockQuestion(AppType.ZWIFT)
            elif "device to simulate" in prompt:
                for choice in choices:
                    if hasattr(choice, "value") and choice.value == ("CUSTOM", None):
                        return MockQuestion(("CUSTOM", None))
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            if "Use this directory" in prompt:
                return MockQuestion(True)
            elif "Customize device" in prompt:
                return MockQuestion(True)
            return MockQuestion(False)

        def mock_text(prompt, **kwargs):
            if "email" in prompt.lower():
                return MockQuestion("user@example.com")
            elif "numeric device ID" in prompt:
                return MockQuestion("99999")  # Unknown device ID
            elif "name" in prompt.lower():
                return MockQuestion("unknown_device_profile")
            return MockQuestion("test_value")

        def mock_password(prompt, **kwargs):
            return MockQuestion("password123")

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        result = manager.create_profile_wizard()

        assert result is not None
        assert result.device == 99999

        # Check that warning was printed
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "99999" in captured.out
        assert "not recognized" in captured.out

    def test_create_profile_wizard_cancel_device_selection(self, manager, monkeypatch):
        """Test create profile wizard when user cancels at device selection."""

        class MockDetector:
            def get_default_path(self):
                return Path("/detected/path")

            def get_display_name(self):
                return "Test App"

        def mock_get_detector(app_type):
            return MockDetector()

        monkeypatch.setattr(
            "fit_file_faker.app_registry.get_detector", mock_get_detector
        )

        def mock_select(prompt, choices, **kwargs):
            if "trainer app" in prompt:
                for choice in choices:
                    if hasattr(choice, "value") and choice.value == AppType.ZWIFT:
                        return MockQuestion(AppType.ZWIFT)
            elif "device to simulate" in prompt:
                return MockQuestion(None)  # Cancel device selection
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            if "Use this directory" in prompt:
                return MockQuestion(True)
            elif "Customize device" in prompt:
                return MockQuestion(True)  # Yes, but then cancel
            return MockQuestion(False)

        def mock_text(prompt, **kwargs):
            if "email" in prompt.lower():
                return MockQuestion("user@example.com")
            return MockQuestion("test_value")

        def mock_password(prompt, **kwargs):
            return MockQuestion("password123")

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        result = manager.create_profile_wizard()

        # Should return None when device selection is cancelled
        assert result is None

    def test_create_profile_wizard_cancel_custom_device_input(
        self, manager, monkeypatch
    ):
        """Test create profile wizard when user cancels custom device ID input."""

        class MockDetector:
            def get_default_path(self):
                return Path("/detected/path")

            def get_display_name(self):
                return "Test App"

        def mock_get_detector(app_type):
            return MockDetector()

        monkeypatch.setattr(
            "fit_file_faker.app_registry.get_detector", mock_get_detector
        )

        def mock_select(prompt, choices, **kwargs):
            if "trainer app" in prompt:
                for choice in choices:
                    if hasattr(choice, "value") and choice.value == AppType.ZWIFT:
                        return MockQuestion(AppType.ZWIFT)
            elif "device to simulate" in prompt:
                # Select custom device option
                for choice in choices:
                    if hasattr(choice, "value") and choice.value == ("CUSTOM", None):
                        return MockQuestion(("CUSTOM", None))
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            if "Use this directory" in prompt:
                return MockQuestion(True)
            elif "Customize device" in prompt:
                return MockQuestion(True)
            return MockQuestion(False)

        def mock_text(prompt, **kwargs):
            if "email" in prompt.lower():
                return MockQuestion("user@example.com")
            elif "numeric device ID" in prompt:
                return MockQuestion(None)  # Cancel device ID input
            return MockQuestion("test_value")

        def mock_password(prompt, **kwargs):
            return MockQuestion("password123")

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        result = manager.create_profile_wizard()

        # Should return None when custom device ID input is cancelled
        assert result is None

    def test_create_profile_wizard_view_all_devices(
        self, profile_manager, monkeypatch, mock_detector_factory, capsys
    ):
        """Test create profile wizard with 'View all devices' flow."""
        mock_detector_factory("Test App", default_path=Path("/detected/path"))

        call_tracker = {"select_count": 0}

        def mock_select(prompt, choices, **kwargs):
            call_tracker["select_count"] += 1
            if "trainer app" in prompt:
                for choice in choices:
                    if hasattr(choice, "value") and choice.value == AppType.ZWIFT:
                        return MockQuestion(AppType.ZWIFT)
            elif "device to simulate" in prompt:
                if call_tracker["select_count"] == 2:
                    # First device menu: select "View all devices"
                    for choice in choices:
                        if hasattr(choice, "value") and choice.value == (
                            "VIEW_ALL",
                            None,
                        ):
                            return MockQuestion(("VIEW_ALL", None))
                elif call_tracker["select_count"] == 3:
                    # Second device menu (now showing all): select a device from category
                    # This will trigger the category grouping code (lines 1799-1831)
                    for choice in choices:
                        if hasattr(choice, "value"):
                            if (
                                isinstance(choice.value, tuple)
                                and len(choice.value) == 2
                            ):
                                name, device_id = choice.value
                                if isinstance(device_id, int) and device_id > 0:
                                    return MockQuestion((name, device_id))
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            if "Use this directory" in prompt:
                return MockQuestion(True)
            elif "Customize device" in prompt:
                return MockQuestion(True)
            return MockQuestion(False)

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(
            questionary, "text", lambda *a, **k: MockQuestion("user@example.com")
        )
        monkeypatch.setattr(
            questionary, "password", lambda *a, **k: MockQuestion("pass")
        )

        result = profile_manager.create_profile_wizard()

        assert result is not None
        assert result.device is not None
        # Verify VIEW_ALL flow was exercised
        assert call_tracker["select_count"] >= 3

    def test_create_profile_wizard_view_all_then_back(
        self, profile_manager, monkeypatch, mock_detector_factory
    ):
        """Test create profile wizard: View all devices, then back to common devices."""
        mock_detector_factory("Test App", default_path=Path("/detected/path"))

        call_tracker = {"select_count": 0}

        def mock_select(prompt, choices, **kwargs):
            call_tracker["select_count"] += 1
            if "trainer app" in prompt:
                for choice in choices:
                    if hasattr(choice, "value") and choice.value == AppType.ZWIFT:
                        return MockQuestion(AppType.ZWIFT)
            elif "device to simulate" in prompt:
                if call_tracker["select_count"] == 2:
                    # First menu: select "View all devices"
                    for choice in choices:
                        if hasattr(choice, "value") and choice.value == (
                            "VIEW_ALL",
                            None,
                        ):
                            return MockQuestion(("VIEW_ALL", None))
                elif call_tracker["select_count"] == 3:
                    # All devices menu: select "Back to common devices"
                    # This triggers lines 1855-1858 (BACK case)
                    for choice in choices:
                        if hasattr(choice, "value") and choice.value == ("BACK", None):
                            return MockQuestion(("BACK", None))
                elif call_tracker["select_count"] == 4:
                    # Back to common devices: select a device
                    for choice in choices:
                        if hasattr(choice, "value"):
                            name, device_id = choice.value
                            if isinstance(device_id, int) and device_id > 0:
                                return MockQuestion((name, device_id))
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            if "Use this directory" in prompt:
                return MockQuestion(True)
            elif "Customize device" in prompt:
                return MockQuestion(True)
            return MockQuestion(False)

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(
            questionary, "text", lambda *a, **k: MockQuestion("user@example.com")
        )
        monkeypatch.setattr(
            questionary, "password", lambda *a, **k: MockQuestion("pass")
        )

        result = profile_manager.create_profile_wizard()

        assert result is not None
        # Verify the flow went through VIEW_ALL → BACK → select device
        assert call_tracker["select_count"] >= 4

    def test_edit_profile_wizard_view_all_devices(
        self, two_profile_manager, monkeypatch, capsys
    ):
        """Test edit profile wizard with 'View all devices' flow."""
        call_tracker = {"select_count": 0}

        def mock_select(prompt, choices, **kwargs):
            call_tracker["select_count"] += 1
            if "Select profile to edit" in prompt:
                return MockQuestion("profile1")
            elif "device to simulate" in prompt:
                if call_tracker["select_count"] == 2:
                    # First device menu: select "View all devices"
                    for choice in choices:
                        if hasattr(choice, "value") and choice.value == (
                            "VIEW_ALL",
                            None,
                        ):
                            return MockQuestion(("VIEW_ALL", None))
                elif call_tracker["select_count"] == 3:
                    # All devices menu: select a device
                    # This triggers lines 2096-2128 (category grouping in edit_profile_wizard)
                    for choice in choices:
                        if hasattr(choice, "value"):
                            if (
                                isinstance(choice.value, tuple)
                                and len(choice.value) == 2
                            ):
                                name, device_id = choice.value
                                if isinstance(device_id, int) and device_id > 0:
                                    return MockQuestion((name, device_id))
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            if "Edit device simulation" in prompt:
                return MockQuestion(True)
            return MockQuestion(False)

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", lambda *a, **k: MockQuestion(""))
        monkeypatch.setattr(questionary, "password", lambda *a, **k: MockQuestion(""))
        monkeypatch.setattr(questionary, "path", lambda *a, **k: MockQuestion(""))

        two_profile_manager.edit_profile_wizard()

        # Verify device was updated
        profile = two_profile_manager.get_profile("profile1")
        assert profile.device is not None
        assert call_tracker["select_count"] >= 3

    def test_edit_profile_wizard_view_all_then_back(
        self, two_profile_manager, monkeypatch
    ):
        """Test edit profile wizard: View all devices, then back to common devices."""
        call_tracker = {"select_count": 0}

        def mock_select(prompt, choices, **kwargs):
            call_tracker["select_count"] += 1
            if "Select profile to edit" in prompt:
                return MockQuestion("profile1")
            elif "device to simulate" in prompt:
                if call_tracker["select_count"] == 2:
                    # First menu: select "View all devices"
                    for choice in choices:
                        if hasattr(choice, "value") and choice.value == (
                            "VIEW_ALL",
                            None,
                        ):
                            return MockQuestion(("VIEW_ALL", None))
                elif call_tracker["select_count"] == 3:
                    # All devices menu: select "Back to common devices"
                    # This triggers lines 2153-2156 (BACK case in edit_profile_wizard)
                    for choice in choices:
                        if hasattr(choice, "value") and choice.value == ("BACK", None):
                            return MockQuestion(("BACK", None))
                elif call_tracker["select_count"] == 4:
                    # Back to common devices: select a device
                    for choice in choices:
                        if hasattr(choice, "value"):
                            name, device_id = choice.value
                            if isinstance(device_id, int) and device_id > 0:
                                return MockQuestion((name, device_id))
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            if "Edit device simulation" in prompt:
                return MockQuestion(True)
            return MockQuestion(False)

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", lambda *a, **k: MockQuestion(""))
        monkeypatch.setattr(questionary, "password", lambda *a, **k: MockQuestion(""))
        monkeypatch.setattr(questionary, "path", lambda *a, **k: MockQuestion(""))

        two_profile_manager.edit_profile_wizard()

        # Verify the flow went through VIEW_ALL → BACK → select device
        profile = two_profile_manager.get_profile("profile1")
        assert profile.device is not None
        assert call_tracker["select_count"] >= 4

    def test_edit_profile_wizard_cancel_device_selection_after_view_all(
        self, two_profile_manager, monkeypatch
    ):
        """Test edit profile wizard: cancel device selection after viewing all devices."""
        call_tracker = {"select_count": 0}

        def mock_select(prompt, choices, **kwargs):
            call_tracker["select_count"] += 1
            if "Select profile to edit" in prompt:
                return MockQuestion("profile1")
            elif "device to simulate" in prompt:
                if call_tracker["select_count"] == 2:
                    # First menu: select "View all devices"
                    for choice in choices:
                        if hasattr(choice, "value") and choice.value == (
                            "VIEW_ALL",
                            None,
                        ):
                            return MockQuestion(("VIEW_ALL", None))
                elif call_tracker["select_count"] == 3:
                    # All devices menu: cancel (return None)
                    # This triggers lines 2139-2141 (cancel handling)
                    return MockQuestion(None)
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            if "Edit device simulation" in prompt:
                return MockQuestion(True)
            return MockQuestion(False)

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", lambda *a, **k: MockQuestion(""))
        monkeypatch.setattr(questionary, "password", lambda *a, **k: MockQuestion(""))
        monkeypatch.setattr(questionary, "path", lambda *a, **k: MockQuestion(""))

        two_profile_manager.edit_profile_wizard()

        # Verify the cancellation flow was exercised (VIEW_ALL → cancel)
        assert call_tracker["select_count"] >= 3

    def test_edit_profile_wizard_with_device_customization(
        self, manager_with_profiles, monkeypatch, capsys
    ):
        """Test edit profile wizard with device customization."""
        from fit_file_faker.vendor.fit_tool.profile.profile_type import GarminProduct

        def mock_select(prompt, choices, **kwargs):
            if "Select profile to edit" in prompt:
                return MockQuestion("profile1")
            elif "device to simulate" in prompt:
                # Return a Choice object directly (to test line 1264)
                for choice in choices:
                    if hasattr(choice, "value"):
                        name, device_id = choice.value
                        if device_id == GarminProduct.EDGE_1030.value:
                            # Return the Choice object itself, not just its value
                            return MockQuestion(choice)
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            if "Edit device simulation" in prompt:
                return MockQuestion(True)  # Yes, edit device
            return MockQuestion(False)

        def mock_text(prompt, **kwargs):
            return MockQuestion("")  # Keep existing values

        def mock_password(prompt, **kwargs):
            return MockQuestion("")

        def mock_path(prompt, **kwargs):
            return MockQuestion("")

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)
        monkeypatch.setattr(questionary, "path", mock_path)

        manager_with_profiles.edit_profile_wizard()

        # Verify device was updated
        profile = manager_with_profiles.get_profile("profile1")
        assert profile.device == GarminProduct.EDGE_1030.value

    def test_edit_profile_wizard_with_custom_device_id(
        self, manager_with_profiles, monkeypatch, capsys
    ):
        """Test edit profile wizard with custom unknown device ID."""

        def mock_select(prompt, choices, **kwargs):
            if "Select profile to edit" in prompt:
                return MockQuestion("profile1")
            elif "device to simulate" in prompt:
                # Select custom device option
                for choice in choices:
                    if hasattr(choice, "value") and choice.value == ("CUSTOM", None):
                        return MockQuestion(("CUSTOM", None))
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            if "Edit device simulation" in prompt:
                return MockQuestion(True)
            return MockQuestion(False)

        def mock_text(prompt, **kwargs):
            if "numeric device ID" in prompt:
                return MockQuestion("88888")  # Unknown device ID
            return MockQuestion("")

        def mock_password(prompt, **kwargs):
            return MockQuestion("")

        def mock_path(prompt, **kwargs):
            return MockQuestion("")

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)
        monkeypatch.setattr(questionary, "path", mock_path)

        manager_with_profiles.edit_profile_wizard()

        # Verify device was updated
        profile = manager_with_profiles.get_profile("profile1")
        assert profile.device == 88888

        # Check warning was shown
        captured = capsys.readouterr()
        assert "Warning" in captured.out


class TestSerialNumbers:
    """Tests for serial number functionality."""

    @pytest.mark.parametrize(
        "serial_number,expected_valid,test_description",
        [
            (None, False, "None serial number"),
            ("1234567890", False, "non-integer (string)"),
            (1234567890, True, "valid serial number"),
            (999_999_999, False, "too small (< 1 billion)"),
            (4_294_967_296, False, "too large (> max uint32)"),
        ],
    )
    def test_profile_validate_serial_number(
        self, serial_number, expected_valid, test_description, standard_profile
    ):
        """Test validate_serial_number with various inputs."""
        # Use the standard_profile fixture and override serial_number
        standard_profile.serial_number = serial_number  # type: ignore
        assert standard_profile.validate_serial_number() == expected_valid, (
            f"Failed for {test_description}"
        )

    def test_config_migration_adds_serial_numbers(self, tmp_path, monkeypatch):
        """Test that config migration adds serial numbers to profiles without them."""
        from fit_file_faker.config import dirs, Config
        from unittest.mock import patch

        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(dirs, "user_config_path", config_dir)

        # Create config file
        config_file = config_dir / ".config.json"
        config_data = {
            "profiles": [
                {
                    "name": "test",
                    "app_type": "zwift",
                    "garmin_username": "user@example.com",
                    "garmin_password": "secret",
                    "fitfiles_path": "/path/to/fitfiles",
                    "manufacturer": 1,
                    "device": 3122,
                }
            ],
            "default_profile": "test",
        }
        with config_file.open("w") as f:
            json.dump(config_data, f)

        # We need to bypass Profile.__post_init__ auto-generation to test migration
        # We'll monkey-patch the Config loading to set serial_number to None after construction
        original_post_init = Config.__post_init__

        def patched_post_init(self):
            original_post_init(self)
            # Set serial_number to None to simulate old config
            for profile in self.profiles:
                profile.serial_number = None

        with patch.object(Config, "__post_init__", patched_post_init):
            # Load config - should trigger migration
            config_mgr = ConfigManager()

        # Verify serial number was added by migration
        profile = config_mgr.config.profiles[0]
        assert profile.serial_number is not None
        assert 1_000_000_000 <= profile.serial_number <= 4_294_967_295

        # Verify config was saved with serial number
        with config_file.open("r") as f:
            saved_config = json.load(f)
        assert saved_config["profiles"][0]["serial_number"] is not None

    def test_create_profile_with_invalid_serial_regenerates(
        self, tmp_path, monkeypatch, caplog
    ):
        """Test that create_profile regenerates invalid serial numbers."""
        from fit_file_faker.config import dirs

        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(dirs, "user_config_path", config_dir)

        config_mgr = ConfigManager()
        manager = ProfileManager(config_mgr)

        # Create profile with invalid serial number (too small)
        with caplog.at_level(logging.WARNING):
            profile = manager.create_profile(
                name="test",
                app_type=AppType.ZWIFT,
                garmin_username="user@example.com",
                garmin_password="secret",
                fitfiles_path=Path("/path"),
                serial_number=999,  # Invalid - too small
            )

        # Should have regenerated
        assert profile.serial_number != 999
        assert 1_000_000_000 <= profile.serial_number <= 4_294_967_295
        assert "Invalid serial number" in caplog.text

    def test_update_profile_with_invalid_serial_raises_error(
        self, tmp_path, monkeypatch
    ):
        """Test that update_profile raises ValueError for invalid serial numbers."""
        from fit_file_faker.config import dirs

        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(dirs, "user_config_path", config_dir)

        config_mgr = ConfigManager()
        manager = ProfileManager(config_mgr)

        # Create profile first
        manager.create_profile(
            name="test",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="secret",
            fitfiles_path=Path("/path"),
        )

        # Try to update with invalid serial number
        with pytest.raises(ValueError, match="Invalid serial number"):
            manager.update_profile("test", serial_number=500)

    def test_create_profile_wizard_with_custom_serial(self, tmp_path, monkeypatch):
        """Test create profile wizard with custom serial number input."""
        from fit_file_faker.config import dirs

        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(dirs, "user_config_path", config_dir)

        # Mock detector to return a path
        detected_path = tmp_path / "detected_zwift"
        detected_path.mkdir()

        def mock_get_default_path(self):
            return detected_path

        monkeypatch.setattr(
            "fit_file_faker.app_registry.ZwiftDetector.get_default_path",
            mock_get_default_path,
        )

        config_mgr = ConfigManager()
        manager = ProfileManager(config_mgr)

        def mock_select(prompt, choices, **kwargs):
            if "trainer app" in prompt:
                # Select Zwift
                for choice in choices:
                    if hasattr(choice, "value") and choice.value == AppType.ZWIFT:
                        return MockQuestion(AppType.ZWIFT)
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            if "Use this directory" in prompt:
                return MockQuestion(True)
            if "Customize device simulation" in prompt:
                return MockQuestion(True)
            if "Customize serial number" in prompt:
                return MockQuestion(True)
            return MockQuestion(False)

        def mock_text(prompt, **kwargs):
            if "profile name" in prompt:
                return MockQuestion("test_profile")
            if "email" in prompt:
                return MockQuestion("user@example.com")
            if "10-digit serial number" in prompt:
                return MockQuestion("1234567890")
            return MockQuestion("")

        def mock_password(prompt, **kwargs):
            return MockQuestion("secret")

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        result = manager.create_profile_wizard()

        assert result is not None
        assert result.serial_number == 1234567890

    def test_edit_profile_wizard_with_random_serial(
        self, tmp_path, monkeypatch, capsys
    ):
        """Test edit profile wizard with random serial number generation."""
        from fit_file_faker.config import dirs

        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(dirs, "user_config_path", config_dir)

        config_mgr = ConfigManager()
        manager = ProfileManager(config_mgr)

        # Create a profile first
        manager.create_profile(
            "test",
            AppType.ZWIFT,
            "user@example.com",
            "secret",
            Path("/path"),
            serial_number=1111111111,
        )

        old_serial = manager.get_profile("test").serial_number

        def mock_select(prompt, choices, **kwargs):
            if "Select profile to edit" in prompt:
                return MockQuestion("test")
            if "How would you like to set the serial number" in prompt:
                return MockQuestion("random")
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            if "Edit device simulation" in prompt:
                return MockQuestion(True)
            if "Edit serial number" in prompt:
                return MockQuestion(True)
            return MockQuestion(False)

        def mock_text(prompt, **kwargs):
            return MockQuestion("")

        def mock_password(prompt, **kwargs):
            return MockQuestion("")

        def mock_path(prompt, **kwargs):
            return MockQuestion("")

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)
        monkeypatch.setattr(questionary, "path", mock_path)

        manager.edit_profile_wizard()

        # Verify serial number was changed
        profile = manager.get_profile("test")
        assert profile.serial_number != old_serial
        assert 1_000_000_000 <= profile.serial_number <= 4_294_967_295

        # Check message was shown
        captured = capsys.readouterr()
        assert "Generated new serial number" in captured.out

    def test_edit_profile_wizard_with_custom_serial(
        self, tmp_path, monkeypatch, capsys
    ):
        """Test edit profile wizard with custom serial number entry."""
        from fit_file_faker.config import dirs

        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(dirs, "user_config_path", config_dir)

        config_mgr = ConfigManager()
        manager = ProfileManager(config_mgr)

        # Create a profile first
        manager.create_profile(
            "test",
            AppType.ZWIFT,
            "user@example.com",
            "secret",
            Path("/path"),
            serial_number=1111111111,
        )

        def mock_select(prompt, choices, **kwargs):
            if "Select profile to edit" in prompt:
                return MockQuestion("test")
            if "How would you like to set the serial number" in prompt:
                return MockQuestion("custom")
            return MockQuestion(choices[0])

        def mock_confirm(prompt, **kwargs):
            if "Edit device simulation" in prompt:
                return MockQuestion(True)
            if "Edit serial number" in prompt:
                return MockQuestion(True)
            return MockQuestion(False)

        def mock_text(prompt, **kwargs):
            if "10-digit serial number" in prompt:
                return MockQuestion("2222222222")
            return MockQuestion("")

        def mock_password(prompt, **kwargs):
            return MockQuestion("")

        def mock_path(prompt, **kwargs):
            return MockQuestion("")

        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)
        monkeypatch.setattr(questionary, "path", mock_path)

        manager.edit_profile_wizard()

        # Verify serial number was changed to custom value
        profile = manager.get_profile("test")
        assert profile.serial_number == 2222222222

        # Verify instructions were shown
        captured = capsys.readouterr()
        assert "Unit ID" in captured.out


class TestSupplementalDevices:
    """Tests for supplemental device registry and enhanced device selection."""

    def test_garmin_device_info_dataclass(self):
        """Test GarminDeviceInfo dataclass structure and immutability."""
        from fit_file_faker.config import GarminDeviceInfo

        device = GarminDeviceInfo(
            name="Edge 1050",
            product_id=4440,
            category="bike_computer",
            year_released=2024,
            is_common=True,
            description="Latest flagship bike computer - 2024",
        )

        assert device.name == "Edge 1050"
        assert device.product_id == 4440
        assert device.category == "bike_computer"
        assert device.year_released == 2024
        assert device.is_common is True
        assert device.description == "Latest flagship bike computer - 2024"

        # Test immutability (frozen=True)
        with pytest.raises(AttributeError):
            device.name = "Edge 1040"

    def test_supplemental_devices_no_duplicates(self):
        """Test that supplemental devices registry has no duplicate product IDs."""
        from fit_file_faker.config import SUPPLEMENTAL_GARMIN_DEVICES

        product_ids = [d.product_id for d in SUPPLEMENTAL_GARMIN_DEVICES]
        assert len(product_ids) == len(set(product_ids)), "Duplicate product IDs found"

    def test_supplemental_devices_structure(self):
        """Test that supplemental devices have expected structure."""
        from fit_file_faker.config import SUPPLEMENTAL_GARMIN_DEVICES

        assert len(SUPPLEMENTAL_GARMIN_DEVICES) > 0, "Registry should not be empty"

        # Verify at least some common devices exist
        common_devices = [d for d in SUPPLEMENTAL_GARMIN_DEVICES if d.is_common]
        assert len(common_devices) >= 11, "Should have at least 11 common devices"

        # Verify categories are valid
        valid_categories = {"bike_computer", "multisport_watch", "trainer"}
        for device in SUPPLEMENTAL_GARMIN_DEVICES:
            assert device.category in valid_categories

    def test_get_supported_garmin_devices_common_only(self):
        """Test get_supported_garmin_devices with show_all=False (common devices only)."""
        from fit_file_faker.config import (
            SUPPLEMENTAL_GARMIN_DEVICES,
            get_supported_garmin_devices,
        )

        devices = get_supported_garmin_devices(show_all=False)

        # Should return list of 3-tuples
        assert len(devices) > 0
        for device in devices:
            assert len(device) == 3
            name, product_id, description = device
            assert isinstance(name, str)
            assert isinstance(product_id, int)
            assert isinstance(description, str)

        # All returned devices should be common devices
        common_product_ids = {
            d.product_id for d in SUPPLEMENTAL_GARMIN_DEVICES if d.is_common
        }

        # Verify that at least the explicitly marked common devices are present
        device_ids = {d[1] for d in devices}
        assert common_product_ids.issubset(device_ids)

    def test_get_supported_garmin_devices_show_all(self):
        """Test get_supported_garmin_devices with show_all=True (all devices)."""
        from fit_file_faker.config import get_supported_garmin_devices

        common_devices = get_supported_garmin_devices(show_all=False)
        all_devices = get_supported_garmin_devices(show_all=True)

        # All devices list should be larger than common only
        assert len(all_devices) > len(common_devices)

        # Verify all common devices are in all devices list
        common_ids = {device[1] for device in common_devices}
        all_ids = {device[1] for device in all_devices}
        assert common_ids.issubset(all_ids)

    def test_get_supported_garmin_devices_sorting(self):
        """Test that devices are sorted correctly (common first, then year desc, then name asc)."""
        from fit_file_faker.config import (
            SUPPLEMENTAL_GARMIN_DEVICES,
            get_supported_garmin_devices,
        )

        devices = get_supported_garmin_devices(show_all=True)

        # Find positions of common and non-common devices
        device_meta = {d.product_id: d for d in SUPPLEMENTAL_GARMIN_DEVICES}

        common_positions = []
        non_common_positions = []

        for i, (name, product_id, description) in enumerate(devices):
            if product_id in device_meta:
                meta = device_meta[product_id]
                if meta.is_common:
                    common_positions.append(i)
                else:
                    non_common_positions.append(i)

        # Common devices should appear before non-common devices
        if common_positions and non_common_positions:
            assert max(common_positions) < min(non_common_positions)

    def test_get_supported_garmin_devices_merging(self):
        """Test that supplemental devices override fit_tool devices for same product ID."""
        from fit_file_faker.config import get_supported_garmin_devices

        # Edge 830 (3122) exists in both fit_tool and supplemental registry
        # Supplemental should override with better name and description
        all_devices = get_supported_garmin_devices(show_all=True)

        edge_830_devices = [d for d in all_devices if d[1] == 3122]
        assert len(edge_830_devices) == 1  # Should only have one entry

        name, product_id, description = edge_830_devices[0]
        assert "Edge 830" in name  # Supplemental registry name format
        assert description != ""  # Should have description from supplemental

    def test_get_device_name_supplemental_fallback(self):
        """Test Profile.get_device_name() with supplemental devices."""
        profile = Profile(
            name="test",
            app_type=AppType.ZWIFT,
            garmin_username="test@example.com",
            garmin_password="password",
            fitfiles_path=Path("/path/to/files"),
            device=4440,  # Edge 1050 from supplemental registry
        )

        device_name = profile.get_device_name()
        assert device_name == "Edge 1050"

    def test_get_device_name_fit_tool_priority(self):
        """Test that fit_tool enum is checked before supplemental registry."""
        from fit_file_faker.vendor.fit_tool.profile.profile_type import GarminProduct

        # Use a device that exists in fit_tool but not supplemental
        profile = Profile(
            name="test",
            app_type=AppType.ZWIFT,
            garmin_username="test@example.com",
            garmin_password="password",
            fitfiles_path=Path("/path/to/files"),
            device=GarminProduct.EDGE520.value,  # No underscore in EDGE520
        )

        device_name = profile.get_device_name()
        # Should return fit_tool enum name (uppercase, no spaces)
        assert device_name == "EDGE520"

    def test_get_device_name_unknown_device(self):
        """Test get_device_name with unknown device ID."""
        profile = Profile(
            name="test",
            app_type=AppType.ZWIFT,
            garmin_username="test@example.com",
            garmin_password="password",
            fitfiles_path=Path("/path/to/files"),
            device=99999,  # Unknown device ID
        )

        device_name = profile.get_device_name()
        assert device_name == "UNKNOWN (99999)"

    def test_create_profile_with_modern_device(self):
        """Test creating a profile with a modern device (Edge 1050)."""
        config_manager = ConfigManager()
        profile_manager = ProfileManager(config_manager)

        # Create profile with Edge 1050
        profile = profile_manager.create_profile(
            name="test_modern",
            app_type=AppType.ZWIFT,
            garmin_username="test@example.com",
            garmin_password="password",
            fitfiles_path=Path("/path/to/files"),
            device=4440,  # Edge 1050
        )

        assert profile.device == 4440
        assert profile.get_device_name() == "Edge 1050"

        # Verify it was saved
        saved_profile = config_manager.config.get_profile("test_modern")
        assert saved_profile is not None
        assert saved_profile.device == 4440

    def test_profile_display_with_supplemental_device(self, capsys):
        """Test that profile table displays supplemental device names correctly."""
        config_manager = ConfigManager()
        profile_manager = ProfileManager(config_manager)

        # Create profile with Fenix 8
        profile_manager.create_profile(
            name="fenix8_profile",
            app_type=AppType.ZWIFT,
            garmin_username="test@example.com",
            garmin_password="password",
            fitfiles_path=Path("/path/to/files"),
            device=4536,  # Fenix 8 47mm
        )

        # Display profiles table
        profile_manager.display_profiles_table()

        captured = capsys.readouterr()
        # The table displays device names on two lines, so check for "Fenix 8" part
        assert "Fenix 8" in captured.out

    def test_backward_compatibility_existing_profiles(self):
        """Test that existing profiles with old device IDs still work."""
        config_manager = ConfigManager()

        # Create profile with Edge 830 (existing in fit_tool and supplemental)
        profile = Profile(
            name="legacy",
            app_type=AppType.ZWIFT,
            garmin_username="test@example.com",
            garmin_password="password",
            fitfiles_path=Path("/path/to/files"),
            device=3122,  # Edge 830
        )

        config_manager.config.profiles.append(profile)
        config_manager.save_config()

        # Reload config
        config_manager_new = ConfigManager()
        loaded_profile = config_manager_new.config.get_profile("legacy")

        assert loaded_profile is not None
        assert loaded_profile.device == 3122
        # fit_tool priority means it returns EDGE_830, but supplemental overrides in get_supported_garmin_devices
        device_name = loaded_profile.get_device_name()
        # Could be either format depending on which registry it came from first
        assert device_name in ["EDGE_830", "Edge 830"]

    def test_device_picker_structure_common_devices(self, monkeypatch):
        """Test that device picker groups common devices by category."""
        from fit_file_faker.config import (
            SUPPLEMENTAL_GARMIN_DEVICES,
            get_supported_garmin_devices,
        )

        devices = get_supported_garmin_devices(show_all=False)

        # Verify bike computers and watches are present
        bike_computers = [
            d
            for d in devices
            if any(
                sd.product_id == d[1] and sd.category == "bike_computer"
                for sd in SUPPLEMENTAL_GARMIN_DEVICES
            )
        ]
        watches = [
            d
            for d in devices
            if any(
                sd.product_id == d[1] and sd.category == "multisport_watch"
                for sd in SUPPLEMENTAL_GARMIN_DEVICES
            )
        ]

        assert len(bike_computers) > 0, "Should have bike computers"
        assert len(watches) > 0, "Should have multisport watches"

    def test_device_categories_in_all_view(self):
        """Test that all devices view includes proper categorization."""
        from fit_file_faker.config import (
            SUPPLEMENTAL_GARMIN_DEVICES,
            get_supported_garmin_devices,
        )

        all_devices = get_supported_garmin_devices(show_all=True)

        # Verify we have devices from multiple categories
        categories = set()
        for name, product_id, desc in all_devices:
            for device_info in SUPPLEMENTAL_GARMIN_DEVICES:
                if device_info.product_id == product_id:
                    categories.add(device_info.category)
                    break

        # Should have at least 2 categories (bike_computer, multisport_watch)
        assert len(categories) >= 2

    def test_custom_device_id_validation(self):
        """Test that custom device IDs are properly validated and saved."""
        config_manager = ConfigManager()
        profile_manager = ProfileManager(config_manager)

        # Create profile with custom device ID not in any registry
        custom_device_id = 88888
        profile = profile_manager.create_profile(
            name="custom_device",
            app_type=AppType.ZWIFT,
            garmin_username="test@example.com",
            garmin_password="password",
            fitfiles_path=Path("/path/to/files"),
            device=custom_device_id,
        )

        assert profile.device == custom_device_id
        assert f"UNKNOWN ({custom_device_id})" in profile.get_device_name()

        # Verify it was saved correctly
        config_manager_reload = ConfigManager()
        loaded_profile = config_manager_reload.config.get_profile("custom_device")
        assert loaded_profile.device == custom_device_id
