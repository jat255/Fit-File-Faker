"""Application registry for trainer app directory detection.

This module provides an extensible pattern for detecting FIT file directories
for different trainer/cycling applications. Each supported app has a detector
class that implements platform-specific directory detection logic.

Typical usage example:

    from fit_file_faker.app_registry import get_detector
    from fit_file_faker.config import AppType

    detector = get_detector(AppType.ZWIFT)
    default_path = detector.get_default_path()
    if default_path:
        print(f"Found Zwift directory: {default_path}")
"""

import os
import re
import sys
from abc import ABC, abstractmethod
from pathlib import Path

from fit_file_faker.config import AppType


class AppDetector(ABC):
    """Abstract base class for app-specific directory detection.

    All detector classes must implement the three abstract methods to provide
    app-specific functionality for directory detection and validation.
    """

    @abstractmethod
    def get_display_name(self) -> str:
        """Get human-readable app name for UI display.

        Returns:
            The display name of the application (e.g., "Zwift", "TrainingPeaks Virtual").
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_short_name(self) -> str:
        """Get short app name for compact display (tables, lists).

        Returns:
            A short name suitable for table columns (e.g., "TPVirtual", "Zwift").
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_default_path(self) -> Path | None:
        """Get platform-specific default FIT files directory.

        Attempts to auto-detect the application's FIT files directory based on
        the current platform. Returns None if detection fails or the app is not
        installed.

        Returns:
            Path to FIT files directory if found, None otherwise.
        """
        pass  # pragma: no cover

    @abstractmethod
    def validate_path(self, path: Path) -> bool:
        """Check if path looks like correct app directory.

        Performs basic validation to ensure the path is appropriate for this
        application's FIT files.

        Args:
            path: The path to validate.

        Returns:
            True if path exists and appears valid for this app, False otherwise.
        """
        pass  # pragma: no cover


class TPVDetector(AppDetector):
    """TrainingPeaks Virtual directory detector."""

    def get_display_name(self) -> str:
        """Get human-readable app name."""
        return "TrainingPeaks Virtual"

    def get_short_name(self) -> str:
        """Get short app name for compact display."""
        return "TPVirtual"

    def get_default_path(self) -> Path | None:
        """Detect TrainingPeaks Virtual FIT files directory.

        Uses existing get_tpv_folder() logic to detect TPV installation and
        scans for user directories.

        Returns:
            Path to TPV FIT files directory if found, None otherwise.
        """
        from fit_file_faker.config import get_tpv_folder

        try:
            base = get_tpv_folder(None)
            # Scan for user folders (16-character hex names)
            if not base or not base.exists():
                return None

            user_folders = [
                f for f in os.listdir(base) if re.search(r"\A(\w){16}\Z", f)
            ]
            if user_folders:
                # Return first user folder's FITFiles directory
                return base / user_folders[0] / "FITFiles"
        except Exception:
            pass

        return None

    def validate_path(self, path: Path) -> bool:
        """Check if path contains TPV structure."""
        return path.exists() and path.is_dir()


class ZwiftDetector(AppDetector):
    """Zwift directory detector."""

    def get_display_name(self) -> str:
        """Get human-readable app name."""
        return "Zwift"

    def get_short_name(self) -> str:
        """Get short app name for compact display."""
        return "Zwift"

    def get_default_path(self) -> Path | None:
        """Detect Zwift Activities folder.

        Returns platform-specific Zwift directory:
        - macOS: ~/Documents/Zwift/Activities/
        - Windows: %USERPROFILE%\\Documents\\Zwift\\Activities\\
        - Linux: Multiple possible Wine/Proton locations

        Returns:
            Path to Zwift Activities directory if found, None otherwise.
        """
        if sys.platform == "darwin":
            # macOS
            base = Path.home() / "Documents" / "Zwift" / "Activities"
            return base if base.exists() else None

        elif sys.platform == "win32":
            # Windows
            base = Path.home() / "Documents" / "Zwift" / "Activities"
            return base if base.exists() else None

        else:
            # Linux - try common Wine/Proton locations
            possible_paths = [
                # Standard Wine prefix
                Path.home()
                / ".wine"
                / "drive_c"
                / "users"
                / os.getenv("USER", "")
                / "Documents"
                / "Zwift"
                / "Activities",
                # Steam Proton
                Path.home()
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
                / "Activities",
                # Linux native (if exists)
                Path.home() / "Documents" / "Zwift" / "Activities",
            ]

            for p in possible_paths:
                if p.exists():
                    return p

            return None

    def validate_path(self, path: Path) -> bool:
        """Check if path looks like Zwift Activities folder."""
        return path.exists() and path.is_dir()


class MyWhooshDetector(AppDetector):
    """MyWhoosh directory detector."""

    def get_display_name(self) -> str:
        """Get human-readable app name."""
        return "MyWhoosh"

    def get_short_name(self) -> str:
        """Get short app name for compact display."""
        return "MyWhoosh"

    def get_default_path(self) -> Path | None:
        """Detect MyWhoosh FIT files directory.

        MyWhoosh stores FIT files in platform-specific application data directories:
        - macOS: ~/Library/Containers/com.whoosh.whooshgame/.../MyWhoosh/Content/Data
        - Windows: ~/AppData/Local/Packages/<PREFIX>/.../MyWhoosh/Content/Data
        - Linux: Not officially supported

        Returns:
            Path to MyWhoosh data directory if found, None otherwise.
        """
        if sys.platform == "darwin":
            # macOS - check container directory
            base = (
                Path.home()
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
            return base if base.exists() else None

        elif sys.platform == "win32":
            # Windows - scan Packages directory for MyWhoosh
            try:
                base_path = Path.home() / "AppData" / "Local" / "Packages"
                if not base_path.exists():
                    return None

                # Look for directories starting with MyWhoosh package prefix
                # The exact prefix can vary, so we search for any containing "MyWhoosh"
                for directory in base_path.iterdir():
                    if directory.is_dir() and "MyWhoosh" in directory.name:
                        target_path = (
                            directory
                            / "LocalCache"
                            / "Local"
                            / "MyWhoosh"
                            / "Content"
                            / "Data"
                        )
                        if target_path.exists():
                            return target_path

            except (PermissionError, OSError):
                pass

            return None

        else:
            # Linux - not officially supported
            return None

    def validate_path(self, path: Path) -> bool:
        """Check if path looks like MyWhoosh directory."""
        return path.exists() and path.is_dir()


class CustomDetector(AppDetector):
    """Custom/manual path specification detector."""

    def get_display_name(self) -> str:
        """Get human-readable app name."""
        return "Custom (Manual Path)"

    def get_short_name(self) -> str:
        """Get short app name for compact display."""
        return "Custom"

    def get_default_path(self) -> Path | None:
        """No default for custom paths.

        Custom paths must be manually specified by the user.

        Returns:
            None - custom paths have no auto-detection.
        """
        return None

    def validate_path(self, path: Path) -> bool:
        """Basic directory existence check."""
        return path.exists() and path.is_dir()


# Registry mapping AppType to detector classes
APP_REGISTRY: dict[AppType, type[AppDetector]] = {
    AppType.TP_VIRTUAL: TPVDetector,
    AppType.ZWIFT: ZwiftDetector,
    AppType.MYWHOOSH: MyWhooshDetector,
    AppType.CUSTOM: CustomDetector,
}


def get_detector(app_type: AppType) -> AppDetector:
    """Factory function to get detector instance for app type.

    Args:
        app_type: The type of application to get a detector for.

    Returns:
        An instance of the appropriate AppDetector subclass.

    Raises:
        ValueError: If no detector is registered for the given app_type.

    Examples:
        >>> from fit_file_faker.config import AppType
        >>> detector = get_detector(AppType.ZWIFT)
        >>> print(detector.get_display_name())
        Zwift
        >>> path = detector.get_default_path()
    """
    detector_class = APP_REGISTRY.get(app_type)
    if not detector_class:
        raise ValueError(f"No detector registered for {app_type}")
    return detector_class()
