"""
Tests for app registry and detector classes.
"""

from pathlib import Path

import pytest

from fit_file_faker.app_registry import (
    APP_REGISTRY,
    CustomDetector,
    MyWhooshDetector,
    TPVDetector,
    ZwiftDetector,
    get_detector,
)
from fit_file_faker.config import AppType


class TestDetectorNames:
    """Tests for detector display and short names."""

    @pytest.mark.parametrize(
        "detector_class,expected_display_name",
        [
            (TPVDetector, "TrainingPeaks Virtual"),
            (ZwiftDetector, "Zwift"),
            (MyWhooshDetector, "MyWhoosh"),
            (CustomDetector, "Custom (Manual Path)"),
        ],
    )
    def test_display_names(self, detector_class, expected_display_name):
        """Test that detectors return correct display names."""
        detector = detector_class()
        assert detector.get_display_name() == expected_display_name

    @pytest.mark.parametrize(
        "detector_class,expected_short_name",
        [
            (TPVDetector, "TPVirtual"),
            (ZwiftDetector, "Zwift"),
            (MyWhooshDetector, "MyWhoosh"),
            (CustomDetector, "Custom"),
        ],
    )
    def test_short_names(self, detector_class, expected_short_name):
        """Test that detectors return correct short names."""
        detector = detector_class()
        assert detector.get_short_name() == expected_short_name


class TestDetectorValidation:
    """Tests for detector path validation."""

    @pytest.mark.parametrize(
        "detector_class",
        [TPVDetector, ZwiftDetector, MyWhooshDetector, CustomDetector],
    )
    def test_validate_path_exists(self, detector_class, tmp_path):
        """Test that validation succeeds for existing directory."""
        detector = detector_class()
        test_dir = tmp_path / "test_fitfiles"
        test_dir.mkdir()

        assert detector.validate_path(test_dir) is True

    @pytest.mark.parametrize(
        "detector_class",
        [TPVDetector, ZwiftDetector, MyWhooshDetector, CustomDetector],
    )
    def test_validate_path_not_exists(self, detector_class):
        """Test that validation fails for non-existent path."""
        detector = detector_class()
        assert detector.validate_path(Path("/nonexistent/path")) is False

    def test_validate_path_is_file(self, tmp_path):
        """Test that validation fails for file (not directory)."""
        detector = TPVDetector()
        test_file = tmp_path / "test.fit"
        test_file.touch()

        assert detector.validate_path(test_file) is False


class TestZwiftDetector:
    """Tests for Zwift detector platform-specific paths."""

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


class TestMyWhooshDetector:
    """Tests for MyWhoosh detector platform-specific paths."""

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


class TestCustomDetector:
    """Tests for Custom detector."""

    def test_get_default_path_returns_none(self):
        """Test that Custom detector always returns None for default path."""
        detector = CustomDetector()
        assert detector.get_default_path() is None


class TestGetDefaultPathNotFound:
    """Tests for detectors returning None when default path not found."""

    @pytest.mark.parametrize(
        "detector_class",
        [ZwiftDetector, MyWhooshDetector],
    )
    def test_get_default_path_not_found(self, detector_class, monkeypatch, tmp_path):
        """Test that None is returned when detector's directory doesn't exist."""
        monkeypatch.setattr("sys.platform", "darwin")
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        detector = detector_class()
        result = detector.get_default_path()

        assert result is None


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

    def test_get_detector_invalid_app_type(self):
        """Test that get_detector raises ValueError for invalid app type."""
        import pytest

        # Create an invalid AppType-like object
        class InvalidAppType:
            pass

        with pytest.raises(ValueError) as exc_info:
            get_detector(InvalidAppType())  # type: ignore

        assert "No detector registered" in str(exc_info.value)


class TestTPVDetectorDefaultPath:
    """Tests for TPV detector default path detection."""

    def test_get_default_path_returns_none_on_error(self, monkeypatch):
        """Test that get_default_path returns None when get_tpv_folder fails."""

        # Mock get_tpv_folder to raise an exception
        def mock_get_tpv_folder(path):
            raise RuntimeError("TPV folder detection failed")

        monkeypatch.setattr("fit_file_faker.config.get_tpv_folder", mock_get_tpv_folder)

        detector = TPVDetector()
        result = detector.get_default_path()

        assert result is None

    def test_get_default_path_returns_none_when_base_not_exists(self, monkeypatch):
        """Test that get_default_path returns None when base directory doesn't exist."""
        # Mock get_tpv_folder to return a non-existent path
        monkeypatch.setattr(
            "fit_file_faker.config.get_tpv_folder",
            lambda path: Path("/nonexistent/path"),
        )

        detector = TPVDetector()
        result = detector.get_default_path()

        assert result is None

    def test_get_default_path_returns_none_when_no_user_folders(
        self, monkeypatch, tmp_path
    ):
        """Test that get_default_path returns None when no user folders found."""
        base_dir = tmp_path / "tpv_test"
        base_dir.mkdir()

        # Mock get_tpv_folder to return our test directory
        monkeypatch.setattr(
            "fit_file_faker.config.get_tpv_folder", lambda path: base_dir
        )

        detector = TPVDetector()
        result = detector.get_default_path()

        assert result is None

    def test_get_default_path_finds_user_folder(self, monkeypatch, tmp_path):
        """Test that get_default_path finds and returns user folder's FITFiles directory."""
        base_dir = tmp_path / "tpv_base"
        base_dir.mkdir()

        # Create a user folder with 16-character hex name
        user_folder = base_dir / ("a" * 16)
        user_folder.mkdir()
        fit_files_dir = user_folder / "FITFiles"
        fit_files_dir.mkdir()

        # Mock get_tpv_folder to return our test directory
        monkeypatch.setattr(
            "fit_file_faker.config.get_tpv_folder", lambda path: base_dir
        )

        detector = TPVDetector()
        result = detector.get_default_path()

        assert result == fit_files_dir


class TestZwiftDetectorPlatformPaths:
    """Tests for Zwift detector platform-specific paths."""

    def test_get_default_path_linux_proton(self, monkeypatch, tmp_path):
        """Test Zwift default path detection on Linux (Steam Proton)."""
        monkeypatch.setattr("sys.platform", "linux")

        # Create mock Proton Zwift directory
        zwift_dir = (
            tmp_path
            / ".steam"
            / "steam"
            / "steamapps"
            / "compatdata"
            / "1134130"
            / "pfx"
            / "drive_c"
            / "users"
            / "steamuser"
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

    def test_get_default_path_linux_native(self, monkeypatch, tmp_path):
        """Test Zwift default path detection on Linux (native)."""
        monkeypatch.setattr("sys.platform", "linux")

        # Create mock native Linux Zwift directory (no Wine/Proton)
        zwift_dir = tmp_path / "Documents" / "Zwift" / "Activities"
        zwift_dir.mkdir(parents=True)

        # Mock Path.home() to return our tmp_path
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        detector = ZwiftDetector()
        result = detector.get_default_path()

        assert result == zwift_dir

    def test_get_default_path_linux_no_paths_found(self, monkeypatch, tmp_path):
        """Test Zwift returns None on Linux when no paths exist."""
        monkeypatch.setattr("sys.platform", "linux")
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        detector = ZwiftDetector()
        result = detector.get_default_path()

        assert result is None


class TestMyWhooshDetectorWindowsPermissions:
    """Tests for MyWhoosh detector Windows permission handling."""

    def test_get_default_path_windows_permission_error(self, monkeypatch, tmp_path):
        """Test that MyWhoosh handles PermissionError gracefully on Windows."""
        monkeypatch.setattr("sys.platform", "win32")

        # Mock Path.home() to return our tmp_path
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        # Create the packages directory
        packages_dir = tmp_path / "AppData" / "Local" / "Packages"
        packages_dir.mkdir(parents=True)

        # Mock iterdir to raise PermissionError
        def mock_iterdir(self):
            raise PermissionError("Access denied")

        monkeypatch.setattr("pathlib.Path.iterdir", mock_iterdir)

        detector = MyWhooshDetector()
        result = detector.get_default_path()

        assert result is None

    def test_get_default_path_windows_os_error(self, monkeypatch, tmp_path):
        """Test that MyWhoosh handles OSError gracefully on Windows."""
        monkeypatch.setattr("sys.platform", "win32")

        # Mock Path.home() to return our tmp_path
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        # Create the packages directory
        packages_dir = tmp_path / "AppData" / "Local" / "Packages"
        packages_dir.mkdir(parents=True)

        # Mock iterdir to raise OSError
        def mock_iterdir(self):
            raise OSError("I/O error")

        monkeypatch.setattr("pathlib.Path.iterdir", mock_iterdir)

        detector = MyWhooshDetector()
        result = detector.get_default_path()

        assert result is None

    def test_get_default_path_windows_packages_not_exists(self, monkeypatch, tmp_path):
        """Test that MyWhoosh returns None when Packages dir doesn't exist on Windows."""
        monkeypatch.setattr("sys.platform", "win32")
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        # Don't create the packages directory

        detector = MyWhooshDetector()
        result = detector.get_default_path()

        assert result is None
