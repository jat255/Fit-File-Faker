"""
Pytest configuration and shared fixtures for Fit File Faker tests.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

# Apply monkey patch for COROS files before importing FitFile
from fit_file_faker.utils import apply_fit_tool_patch

apply_fit_tool_patch()

# Now import FitFile after the monkey patch
from fit_file_faker.vendor.fit_tool.fit_file import FitFile  # noqa: E402


# Auto-use fixture to isolate all tests from real config/cache directories
@pytest.fixture(autouse=True)
def isolate_config_dirs(monkeypatch, tmp_path):
    """
    Automatically patch platformdirs for ALL tests to use temporary directories.
    This prevents tests from touching real user config/cache directories.
    """
    config_dir = tmp_path / "config"
    cache_dir = tmp_path / "cache"
    config_dir.mkdir()
    cache_dir.mkdir()

    # Create a mock PlatformDirs class
    class MockPlatformDirs:
        def __init__(self, *args, **kwargs):
            self.user_config_path = config_dir
            self.user_cache_path = cache_dir

    # Patch platformdirs in both config and app modules
    monkeypatch.setattr("fit_file_faker.config.PlatformDirs", MockPlatformDirs)

    # Also ensure the dirs object is recreated with mocked PlatformDirs
    from fit_file_faker import config

    config.dirs = MockPlatformDirs("FitFileFaker", appauthor=False)

    # Recreate config_manager to use the mocked directories
    config.config_manager = config.ConfigManager()

    yield


@pytest.fixture(scope="module")
def test_files_dir():
    """Return the path to the test files directory."""
    return Path(__file__).parent / "files"


@pytest.fixture(scope="module")
def tpv_fit_file_0_4_7(test_files_dir):
    """
    Return path to TrainingPeaks Virtual test FIT file.

    This file was created by v0.4.7 of TPV on Jan 11, 2025
    """
    return test_files_dir / "tpv_20250111.fit"


@pytest.fixture(scope="module")
def tpv_fit_file_0_4_30(test_files_dir):
    """
    Return path to TrainingPeaks Virtual test FIT file.

    This file was created by v0.4.30 of TPV on Nov 20, 2025. This file
    includes the TPV "product indicator" added in v0.4.10 (see release
    notes: https://help.trainingpeaks.com/hc/en-us/articles/34924247758477-TrainingPeaks-Virtual-Release-Notes)
    """
    return test_files_dir / "tpv_20251120.fit"


@pytest.fixture(scope="module")
def zwift_fit_file(test_files_dir):
    """Return path to Zwift test FIT file."""
    return test_files_dir / "zwift_20250401.fit"


@pytest.fixture(scope="module")
def mywhoosh_fit_file(test_files_dir):
    """Return path to MyWhoosh test FIT file."""
    return test_files_dir / "mywhoosh_20260111.fit"


@pytest.fixture(scope="module")
def karoo_fit_file(test_files_dir):
    """Return path to Hammerhead Karoo test FIT file."""
    return test_files_dir / "karoo_20251119.fit"


@pytest.fixture(scope="module")
def coros_fit_file(test_files_dir):
    """Return path to COROS test FIT file."""
    return test_files_dir / "coros_20251118.fit"


@pytest.fixture(scope="module")
def zwift_non_utf8_fit_file(test_files_dir):
    """
    Return path to Zwift test FIT file with non-UTF-8 encoded strings.

    This file contains string fields encoded with Windows-1252/Latin-1
    instead of UTF-8, which was causing UnicodeDecodeError before the
    lenient string decoding patch was added.
    """
    return test_files_dir / "zwift_non_utf8_20260130.fit"


@pytest.fixture(scope="module")
def all_test_fit_files(
    tpv_fit_file, zwift_fit_file, mywhoosh_fit_file, karoo_fit_file, coros_fit_file
):
    """Return all test FIT files."""
    return [
        tpv_fit_file,
        zwift_fit_file,
        mywhoosh_fit_file,
        karoo_fit_file,
        coros_fit_file,
    ]


# Parsed FIT file fixtures - function scoped for test isolation
@pytest.fixture
def tpv_fit_0_4_7_parsed(tpv_fit_file_0_4_7):
    """
    Return parsed TrainingPeaks Virtual FIT file.

    This file was created by v0.4.7 of TPV on Jan 11, 2025
    """
    return FitFile.from_file(str(tpv_fit_file_0_4_7))


@pytest.fixture(scope="module")
def tpv_fit_file(tpv_fit_file_0_4_30):
    """Return path to TrainingPeaks Virtual test FIT file."""
    return tpv_fit_file_0_4_30


@pytest.fixture
def tpv_fit_parsed(tpv_fit_file_0_4_30):
    """Return parsed TrainingPeaks Virtual FIT file."""
    return FitFile.from_file(str(tpv_fit_file_0_4_30))


@pytest.fixture
def tpv_fit_0_4_30_parsed(tpv_fit_file_0_4_30):
    """
    Return parsed TrainingPeaks Virtual FIT file.

    This file was created by v0.4.30 of TPV on Nov 20, 2025
    """
    return FitFile.from_file(str(tpv_fit_file_0_4_30))


@pytest.fixture
def zwift_fit_parsed(zwift_fit_file):
    """Return parsed Zwift FIT file."""
    return FitFile.from_file(str(zwift_fit_file))


@pytest.fixture
def mywhoosh_fit_parsed(mywhoosh_fit_file):
    """Return parsed MyWhoosh FIT file."""
    return FitFile.from_file(str(mywhoosh_fit_file))


@pytest.fixture
def karoo_fit_parsed(karoo_fit_file):
    """Return parsed Karoo FIT file."""
    return FitFile.from_file(str(karoo_fit_file))


@pytest.fixture
def coros_fit_parsed(coros_fit_file):
    """Return parsed COROS FIT file."""
    return FitFile.from_file(str(coros_fit_file))


@pytest.fixture
def zwift_non_utf8_fit_parsed(zwift_non_utf8_fit_file):
    """
    Return parsed Zwift FIT file with non-UTF-8 encoded strings.

    This file requires the lenient string decoding patch to parse correctly.
    """
    return FitFile.from_file(str(zwift_non_utf8_fit_file))


@pytest.fixture(scope="module")
def tpv_dev_fields_fit_file(test_files_dir):
    """
    Return path to TrainingPeaks Virtual test FIT file with developer fields.

    This file was created by TPV on Feb 22, 2026 and contains developer-defined
    fields (e.g. skin_temperature) where some records have empty/invalid values.
    These caused an exception in fit_tool before the lenient developer field patch.
    """
    return test_files_dir / "tpv_dev_fields_20260222.fit"


@pytest.fixture
def tpv_dev_fields_fit_parsed(tpv_dev_fields_fit_file):
    """
    Return parsed TPV FIT file with developer fields.

    Requires the lenient developer field patch to parse correctly.
    """
    return FitFile.from_file(str(tpv_dev_fields_fit_file))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config_file(tmp_path):
    """Create a mock configuration file in the isolated config directory."""
    from fit_file_faker.config import config_manager

    config_manager.config.garmin_username = "test_user@example.com"
    config_manager.config.garmin_password = "test_password"
    config_manager.config.fitfiles_path = str(tmp_path / "fitfiles")
    config_manager.save_config()

    return config_manager.config_file


# Shared Mock Classes and Fixtures


class MockQuestion:
    """Mock questionary question object for testing interactive prompts."""

    def __init__(self, return_value):
        self.return_value = return_value

    def ask(self):
        return self.return_value

    def unsafe_ask(self):
        return self.return_value


class MockGarthHTTPError(Exception):
    """Mock Garth HTTP error with configurable status code."""

    def __init__(self, status_code=500):
        from unittest.mock import MagicMock

        self.error = MagicMock()
        self.error.response.status_code = status_code


class MockGarthException(Exception):
    """Mock Garth exception for testing authentication flows."""

    pass


@pytest.fixture
def mock_garth_basic():
    """Create basic mock garth module with successful operations."""
    from unittest.mock import MagicMock, Mock

    mock_garth = MagicMock()
    mock_garth_exc = MagicMock()

    mock_garth_exc.GarthException = MockGarthException
    mock_garth_exc.GarthHTTPError = MockGarthHTTPError

    mock_garth.resume.return_value = None
    mock_garth.client.username = "test_user"
    mock_garth.client.upload = Mock()

    return mock_garth, mock_garth_exc


@pytest.fixture
def mock_garth_with_login(mock_garth_basic):
    """Create mock garth that requires login."""
    mock_garth, mock_garth_exc = mock_garth_basic

    mock_garth.resume.side_effect = MockGarthException("Session expired")
    mock_garth.login.return_value = None
    mock_garth.save.return_value = None

    return mock_garth, mock_garth_exc


# ==============================================================================
# Questionary Mock Fixtures
# ==============================================================================


@pytest.fixture
def mock_questionary_empty_responses(monkeypatch):
    """Mock all questionary inputs to return empty strings."""
    import questionary

    monkeypatch.setattr(questionary, "text", lambda *a, **k: MockQuestion(""))
    monkeypatch.setattr(questionary, "password", lambda *a, **k: MockQuestion(""))
    monkeypatch.setattr(questionary, "path", lambda *a, **k: MockQuestion(""))
    monkeypatch.setattr(questionary, "confirm", lambda *a, **k: MockQuestion(False))
    monkeypatch.setattr(questionary, "select", lambda *a, **k: MockQuestion(None))


@pytest.fixture
def mock_questionary_profile_inputs(monkeypatch):
    """Mock questionary for standard profile creation (user@example.com, password123)."""
    import questionary

    def mock_text(prompt, **kwargs):
        if "email" in prompt.lower() or "username" in prompt.lower():
            return MockQuestion("user@example.com")
        elif "name" in prompt.lower() and "profile" in prompt.lower():
            return MockQuestion("test_profile")
        return MockQuestion("")

    def mock_password(prompt, **kwargs):
        return MockQuestion("password123")

    monkeypatch.setattr(questionary, "text", mock_text)
    monkeypatch.setattr(questionary, "password", mock_password)
    monkeypatch.setattr(questionary, "confirm", lambda *a, **k: MockQuestion(True))


@pytest.fixture
def mock_questionary_factory(monkeypatch):
    """
    Factory fixture for creating custom questionary mocks.

    Returns a function that accepts various response configurations.
    """
    import questionary

    def _create_mocks(
        text_responses=None,
        password_response="password",
        confirm_response=True,
        select_responses=None,
        path_response=None,
    ):
        """
        Create questionary mocks with custom responses.

        Args:
            text_responses: Dict mapping prompt keywords to responses, or single string
            password_response: String response for password prompts
            confirm_response: Boolean for confirm prompts
            select_responses: List of responses for select calls (cycles through)
            path_response: String response for path prompts
        """
        # Text mock
        if isinstance(text_responses, dict):

            def mock_text(prompt, **kwargs):
                for keyword, response in text_responses.items():
                    if keyword.lower() in prompt.lower():
                        return MockQuestion(response)
                return MockQuestion("")

        elif isinstance(text_responses, str):

            def mock_text(*a, **k):
                return MockQuestion(text_responses)

        else:

            def mock_text(*a, **k):
                return MockQuestion("")

        # Password mock
        def mock_password(*a, **k):
            return MockQuestion(password_response)

        # Confirm mock
        def mock_confirm(*a, **k):
            return MockQuestion(confirm_response)

        # Select mock with cycling through responses
        if select_responses:
            select_call_count = {"count": 0}

            def mock_select(prompt, choices=None, **kwargs):
                idx = select_call_count["count"]
                select_call_count["count"] += 1
                if idx < len(select_responses):
                    return MockQuestion(select_responses[idx])
                return MockQuestion(select_responses[-1])

        else:

            def mock_select(*a, **k):
                return MockQuestion(None)

        # Path mock
        if path_response:

            def mock_path(*a, **k):
                return MockQuestion(path_response)

        else:

            def mock_path(*a, **k):
                return MockQuestion("")

        # Apply patches
        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)
        monkeypatch.setattr(questionary, "confirm", mock_confirm)
        monkeypatch.setattr(questionary, "select", mock_select)
        monkeypatch.setattr(questionary, "path", mock_path)

    return _create_mocks


# ==============================================================================
# Profile and Config Fixtures
# ==============================================================================


@pytest.fixture
def standard_profile():
    """Create a standard test profile with ZWIFT app type."""
    from pathlib import Path

    from fit_file_faker.config import AppType, Profile

    return Profile(
        name="test",
        app_type=AppType.ZWIFT,
        garmin_username="user@example.com",
        garmin_password="password",
        fitfiles_path=Path("/path/to/fitfiles"),
    )


@pytest.fixture
def profile_manager(tmp_path, monkeypatch):
    """Create ProfileManager with temporary config and cache directories."""
    from fit_file_faker.config import ConfigManager, ProfileManager, dirs

    config_dir = tmp_path / "config"
    cache_dir = tmp_path / "cache"
    config_dir.mkdir(exist_ok=True)
    cache_dir.mkdir(exist_ok=True)

    monkeypatch.setattr(dirs, "user_config_path", config_dir)
    monkeypatch.setattr(dirs, "user_cache_path", cache_dir)

    return ProfileManager(ConfigManager())


@pytest.fixture
def two_profile_manager(tmp_path, monkeypatch):
    """ProfileManager pre-populated with two test profiles."""
    from pathlib import Path

    from fit_file_faker.config import AppType, ConfigManager, ProfileManager, dirs

    config_dir = tmp_path / "config"
    cache_dir = tmp_path / "cache"
    config_dir.mkdir(exist_ok=True)
    cache_dir.mkdir(exist_ok=True)

    monkeypatch.setattr(dirs, "user_config_path", config_dir)
    monkeypatch.setattr(dirs, "user_cache_path", cache_dir)

    mgr = ProfileManager(ConfigManager())
    mgr.create_profile(
        "profile1",
        AppType.ZWIFT,
        "user1@example.com",
        "pass1",
        Path("/path/to/fit1"),
    )
    mgr.create_profile(
        "profile2",
        AppType.TP_VIRTUAL,
        "user2@example.com",
        "pass2",
        Path("/path/to/fit2"),
    )
    return mgr


# ==============================================================================
# Mock App Detector Fixtures
# ==============================================================================


@pytest.fixture
def mock_detector_factory(monkeypatch):
    """Factory for creating mock app detectors with configurable behavior."""

    def _create_detector(
        display_name="Test App", default_path=None, short_name=None, app_type=None
    ):
        """
        Create and install a mock app detector.

        Args:
            display_name: Display name returned by get_display_name()
            default_path: Path object or None returned by get_default_path()
            short_name: Short name for the app (defaults to display_name)
            app_type: AppType to associate with this detector

        Returns:
            The MockDetector class (for additional assertions if needed)
        """

        class MockDetector:
            def get_default_path(self):
                return default_path

            def get_display_name(self):
                return display_name

            def get_short_name(self):
                return short_name or display_name

            def validate_path(self, path):
                return True

        # Install the mock
        monkeypatch.setattr(
            "fit_file_faker.app_registry.get_detector", lambda x: MockDetector()
        )

        return MockDetector

    return _create_detector
