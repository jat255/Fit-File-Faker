"""
Tests for app registry and detector classes.
"""

from pathlib import Path


from fit_file_faker.app_registry import (
    APP_REGISTRY,
    CustomDetector,
    MyWhooshDetector,
    TPVDetector,
    ZwiftDetector,
    get_detector,
)
from fit_file_faker.config import AppType


class TestTPVDetector:
    """Tests for TrainingPeaks Virtual detector."""

    def test_display_name(self):
        """Test that TPV detector returns correct display name."""
        detector = TPVDetector()
        assert detector.get_display_name() == "TrainingPeaks Virtual"

    def test_validate_path_exists(self, tmp_path):
        """Test that validation succeeds for existing directory."""
        detector = TPVDetector()
        test_dir = tmp_path / "tpv_fitfiles"
        test_dir.mkdir()

        assert detector.validate_path(test_dir) is True

    def test_validate_path_not_exists(self):
        """Test that validation fails for non-existent path."""
        detector = TPVDetector()
        assert detector.validate_path(Path("/nonexistent/path")) is False

    def test_validate_path_is_file(self, tmp_path):
        """Test that validation fails for file (not directory)."""
        detector = TPVDetector()
        test_file = tmp_path / "test.fit"
        test_file.touch()

        assert detector.validate_path(test_file) is False


class TestZwiftDetector:
    """Tests for Zwift detector."""

    def test_display_name(self):
        """Test that Zwift detector returns correct display name."""
        detector = ZwiftDetector()
        assert detector.get_display_name() == "Zwift"

    def test_validate_path_exists(self, tmp_path):
        """Test that validation succeeds for existing directory."""
        detector = ZwiftDetector()
        test_dir = tmp_path / "zwift_activities"
        test_dir.mkdir()

        assert detector.validate_path(test_dir) is True

    def test_validate_path_not_exists(self):
        """Test that validation fails for non-existent path."""
        detector = ZwiftDetector()
        assert detector.validate_path(Path("/nonexistent/path")) is False

    def test_get_default_path_macos(self, monkeypatch, tmp_path):
        """Test Zwift default path detection on macOS."""
        monkeypatch.setattr("sys.platform", "darwin")

        # Create mock Zwift directory
        zwift_dir = tmp_path / "Documents" / "Zwift" / "Activities"
        zwift_dir.mkdir(parents=True)

        # Mock Path.home() to return our tmp_path
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        detector = ZwiftDetector()
        result = detector.get_default_path()

        assert result == zwift_dir

    def test_get_default_path_windows(self, monkeypatch, tmp_path):
        """Test Zwift default path detection on Windows."""
        monkeypatch.setattr("sys.platform", "win32")

        # Create mock Zwift directory
        zwift_dir = tmp_path / "Documents" / "Zwift" / "Activities"
        zwift_dir.mkdir(parents=True)

        # Mock Path.home() to return our tmp_path
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        detector = ZwiftDetector()
        result = detector.get_default_path()

        assert result == zwift_dir

    def test_get_default_path_linux_wine(self, monkeypatch, tmp_path):
        """Test Zwift default path detection on Linux (Wine)."""
        monkeypatch.setattr("sys.platform", "linux")
        monkeypatch.setenv("USER", "testuser")

        # Create mock Wine Zwift directory
        zwift_dir = (
            tmp_path
            / ".wine"
            / "drive_c"
            / "users"
            / "testuser"
            / "Documents"
            / "Zwift"
            / "Activities"
        )
        zwift_dir.mkdir(parents=True)

        # Mock Path.home() to return our tmp_path
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        detector = ZwiftDetector()
        result = detector.get_default_path()

        assert result == zwift_dir

    def test_get_default_path_not_found(self, monkeypatch, tmp_path):
        """Test that None is returned when Zwift directory doesn't exist."""
        monkeypatch.setattr("sys.platform", "darwin")
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        detector = ZwiftDetector()
        result = detector.get_default_path()

        assert result is None


class TestMyWhooshDetector:
    """Tests for MyWhoosh detector."""

    def test_display_name(self):
        """Test that MyWhoosh detector returns correct display name."""
        detector = MyWhooshDetector()
        assert detector.get_display_name() == "MyWhoosh"

    def test_validate_path_exists(self, tmp_path):
        """Test that validation succeeds for existing directory."""
        detector = MyWhooshDetector()
        test_dir = tmp_path / "mywhoosh_data"
        test_dir.mkdir()

        assert detector.validate_path(test_dir) is True

    def test_validate_path_not_exists(self):
        """Test that validation fails for non-existent path."""
        detector = MyWhooshDetector()
        assert detector.validate_path(Path("/nonexistent/path")) is False

    def test_get_default_path_macos(self, monkeypatch, tmp_path):
        """Test MyWhoosh default path detection on macOS."""
        monkeypatch.setattr("sys.platform", "darwin")

        # Create mock MyWhoosh directory
        mywhoosh_dir = (
            tmp_path
            / "Library"
            / "Containers"
            / "com.whoosh.whooshgame"
            / "Data"
            / "Library"
            / "Application Support"
            / "Epic"
            / "MyWhoosh"
            / "Content"
            / "Data"
        )
        mywhoosh_dir.mkdir(parents=True)

        # Mock Path.home() to return our tmp_path
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        detector = MyWhooshDetector()
        result = detector.get_default_path()

        assert result == mywhoosh_dir

    def test_get_default_path_windows(self, monkeypatch, tmp_path):
        """Test MyWhoosh default path detection on Windows."""
        monkeypatch.setattr("sys.platform", "win32")

        # Create mock MyWhoosh Windows directory
        packages_dir = tmp_path / "AppData" / "Local" / "Packages"
        packages_dir.mkdir(parents=True)

        mywhoosh_package = packages_dir / "MyWhoosh.12345_abcdef"
        mywhoosh_dir = (
            mywhoosh_package / "LocalCache" / "Local" / "MyWhoosh" / "Content" / "Data"
        )
        mywhoosh_dir.mkdir(parents=True)

        # Mock Path.home() to return our tmp_path
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        detector = MyWhooshDetector()
        result = detector.get_default_path()

        assert result == mywhoosh_dir

    def test_get_default_path_linux(self, monkeypatch):
        """Test that MyWhoosh returns None on Linux (not supported)."""
        monkeypatch.setattr("sys.platform", "linux")

        detector = MyWhooshDetector()
        result = detector.get_default_path()

        assert result is None

    def test_get_default_path_not_found(self, monkeypatch, tmp_path):
        """Test that None is returned when MyWhoosh directory doesn't exist."""
        monkeypatch.setattr("sys.platform", "darwin")
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        detector = MyWhooshDetector()
        result = detector.get_default_path()

        assert result is None


class TestCustomDetector:
    """Tests for Custom detector."""

    def test_display_name(self):
        """Test that Custom detector returns correct display name."""
        detector = CustomDetector()
        assert detector.get_display_name() == "Custom (Manual Path)"

    def test_get_default_path_returns_none(self):
        """Test that Custom detector always returns None for default path."""
        detector = CustomDetector()
        assert detector.get_default_path() is None

    def test_validate_path_exists(self, tmp_path):
        """Test that validation succeeds for existing directory."""
        detector = CustomDetector()
        test_dir = tmp_path / "custom_fitfiles"
        test_dir.mkdir()

        assert detector.validate_path(test_dir) is True

    def test_validate_path_not_exists(self):
        """Test that validation fails for non-existent path."""
        detector = CustomDetector()
        assert detector.validate_path(Path("/nonexistent/path")) is False


class TestAppRegistry:
    """Tests for app registry and factory function."""

    def test_registry_contains_all_app_types(self):
        """Test that registry has entries for all AppType values."""
        assert AppType.TP_VIRTUAL in APP_REGISTRY
        assert AppType.ZWIFT in APP_REGISTRY
        assert AppType.MYWHOOSH in APP_REGISTRY
        assert AppType.CUSTOM in APP_REGISTRY

    def test_get_detector_tp_virtual(self):
        """Test getting TPV detector from factory."""
        detector = get_detector(AppType.TP_VIRTUAL)
        assert isinstance(detector, TPVDetector)
        assert detector.get_display_name() == "TrainingPeaks Virtual"

    def test_get_detector_zwift(self):
        """Test getting Zwift detector from factory."""
        detector = get_detector(AppType.ZWIFT)
        assert isinstance(detector, ZwiftDetector)
        assert detector.get_display_name() == "Zwift"

    def test_get_detector_mywhoosh(self):
        """Test getting MyWhoosh detector from factory."""
        detector = get_detector(AppType.MYWHOOSH)
        assert isinstance(detector, MyWhooshDetector)
        assert detector.get_display_name() == "MyWhoosh"

    def test_get_detector_custom(self):
        """Test getting Custom detector from factory."""
        detector = get_detector(AppType.CUSTOM)
        assert isinstance(detector, CustomDetector)
        assert detector.get_display_name() == "Custom (Manual Path)"

    def test_get_detector_creates_new_instance(self):
        """Test that factory creates new instances each time."""
        detector1 = get_detector(AppType.ZWIFT)
        detector2 = get_detector(AppType.ZWIFT)

        assert detector1 is not detector2
        assert isinstance(detector1, ZwiftDetector)
        assert isinstance(detector2, ZwiftDetector)
