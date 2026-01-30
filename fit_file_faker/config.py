"""Configuration management for Fit File Faker.

This module handles all configuration file operations including creation,
validation, loading, and saving. Configuration is stored in a platform-specific
user configuration directory using platformdirs.

The configuration includes Garmin Connect credentials and the path to the
directory containing FIT files to process. Depending on the trainer app
selected in the profile, the FIT files directory is auto-detected (but can
be overridden).


!!! note "Typical usage example:"
    ```python
    from fit_file_faker.config import config_manager

    # Check if config is valid
    if not config_manager.is_valid():
        config_manager.build_config_file()

    # Access configuration values
    username = config_manager.config.garmin_username
    fit_path = config_manager.config.fitfiles_path
    ```
"""

import json
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import cast

import questionary
from platformdirs import PlatformDirs
from rich.console import Console
from rich.table import Table

_logger = logging.getLogger("garmin")

# Platform-specific directories for config and cache
dirs = PlatformDirs("FitFileFaker", appauthor=False, ensure_exists=True)


class PathEncoder(json.JSONEncoder):
    """JSON encoder that handles `pathlib.Path` and `Enum` objects.

    Extends `json.JSONEncoder` to automatically convert Path and Enum objects
    to strings when serializing configuration to JSON format.

    Examples:
        >>> import json
        >>> from pathlib import Path
        >>> data = {"path": Path("/home/user"), "type": AppType.ZWIFT}
        >>> json.dumps(data, cls=PathEncoder)
        '{"path": "/home/user", "type": "zwift"}'
    """

    def default(self, obj):
        """Override default encoding for Path and Enum objects.

        Args:
            obj: The object to encode.

        Returns:
            String representation of Path and Enum objects, or delegates to
            the parent class for other types.
        """
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)  # pragma: no cover


@dataclass(frozen=True)
class GarminDeviceInfo:
    """Metadata for a Garmin device (supplemental to fit_tool's enum).

    Provides enhanced device information for modern Garmin devices not fully
    represented in fit_tool's GarminProduct enum, or to add curation metadata
    for devices that already exist.

    Attributes:
        name: Human-readable device name (e.g., "Edge 1050")
        product_id: FIT file product ID (integer)
        category: Device category ("bike_computer", "multisport_watch", "trainer")
        year_released: Release year for sorting (integer)
        is_common: Show in first-level menu (boolean)
        description: Brief description for UI display
        software_version: Latest stable firmware version in FIT format (int, e.g., 2922 = v29.22)
        software_date: Latest firmware release date (YYYY-MM-DD format)
    """

    name: str
    product_id: int
    category: str
    year_released: int
    is_common: bool
    description: str
    software_version: int | None = None
    software_date: str | None = None


# Supplemental device registry with modern Garmin devices
# Device IDs sourced from FIT SDK 21.188.00 (docs/reference/FitSDK_21.188.00_device_ids.tsv)
SUPPLEMENTAL_GARMIN_DEVICES = [
    # Common bike computers (is_common=True)
    GarminDeviceInfo(
        "Edge 1050",
        4440,
        "bike_computer",
        2024,
        True,
        "Latest flagship bike computer - 2024",
        2922,
        "2025-11-04",
    ),
    GarminDeviceInfo(
        "Edge 1040",
        3843,
        "bike_computer",
        2022,
        True,
        "Multi-band GNSS bike computer - 2022",
        2922,
        "2025-11-04",
    ),
    GarminDeviceInfo(
        "Edge 840",
        4062,
        "bike_computer",
        2023,
        True,
        "Mid-range touchscreen - 2023",
        2922,
        "2025-11-04",
    ),
    GarminDeviceInfo(
        "Edge 830",
        3122,
        "bike_computer",
        2019,
        True,
        "Current default - 2019",
        975,
        "2023-03-22",
    ),
    GarminDeviceInfo(
        "Edge 540",
        4061,
        "bike_computer",
        2023,
        True,
        "Mid-range button-based - 2023",
        2922,
        "2025-11-04",
    ),
    GarminDeviceInfo(
        "Edge 530",
        3121,
        "bike_computer",
        2019,
        True,
        "Popular non-touchscreen - 2019",
        975,
        "2023-03-22",
    ),
    # Common multisport watches (is_common=True)
    GarminDeviceInfo(
        "Fenix 8 47mm",
        4536,
        "multisport_watch",
        2024,
        True,
        "Latest multisport watch - 2024",
        2029,
        "2026-01-14",
    ),
    GarminDeviceInfo(
        "Fenix 7",
        3906,
        "multisport_watch",
        2022,
        True,
        "Popular multisport watch - 2022",
        2511,
        "2026-01-21",
    ),
    GarminDeviceInfo(
        "Epix Gen 2",
        3943,
        "multisport_watch",
        2022,
        True,
        "AMOLED multisport watch - 2022",
        2511,
        "2026-01-21",
    ),
    GarminDeviceInfo(
        "Forerunner 965",
        4315,
        "multisport_watch",
        2023,
        True,
        "Premium running/cycling - 2023",
        2709,
        "2026-01-15",
    ),
    GarminDeviceInfo(
        "Forerunner 955",
        4024,
        "multisport_watch",
        2022,
        True,
        "Running watch with maps - 2022",
        2709,
        "2026-01-15",
    ),
    # Additional bike computers (is_common=False)
    GarminDeviceInfo(
        "Edge 1030 Plus",
        3570,
        "bike_computer",
        2020,
        False,
        "Previous flagship - 2020",
        675,
        "2023-03-22",
    ),
    GarminDeviceInfo(
        "Edge 1030",
        2713,
        "bike_computer",
        2017,
        False,
        "Previous flagship - 2017",
        1375,
        "2023-03-22",
    ),
    GarminDeviceInfo(
        "Edge 820",
        2530,
        "bike_computer",
        2016,
        False,
        "Mid-range with touchscreen - 2016",
        1270,
        "2020-09-11",
    ),
    GarminDeviceInfo(
        "Edge 520 Plus",
        3112,
        "bike_computer",
        2018,
        False,
        "Mid-range with navigation - 2018",
        570,
        "2020-09-11",
    ),
    GarminDeviceInfo(
        "Edge 520", 2067, "bike_computer", 2015, False, "Popular mid-range - 2015"
    ),
    GarminDeviceInfo(
        "Edge 130 Plus",
        3558,
        "bike_computer",
        2020,
        False,
        "Compact bike computer - 2020",
        300,
        "2023-01-19",
    ),
    GarminDeviceInfo(
        "Edge 130", 2909, "bike_computer", 2018, False, "Compact bike computer - 2018"
    ),
    GarminDeviceInfo(
        "Edge 550",
        4633,
        "bike_computer",
        2024,
        False,
        "Mid-range bike computer - 2024",
        2922,
        "2025-11-04",
    ),
    GarminDeviceInfo(
        "Edge 850",
        4634,
        "bike_computer",
        2024,
        False,
        "Touchscreen bike computer - 2024",
        2922,
        "2025-11-04",
    ),
    # Additional multisport watches (is_common=False)
    GarminDeviceInfo(
        "Fenix 8 Solar 51mm",
        4532,
        "multisport_watch",
        2024,
        False,
        "Solar multisport watch - 2024",
        2029,
        "2026-01-14",
    ),
    GarminDeviceInfo(
        "Fenix 8 Solar 47mm",
        4533,
        "multisport_watch",
        2024,
        False,
        "Solar multisport watch - 2024",
        2029,
        "2026-01-14",
    ),
    GarminDeviceInfo(
        "Fenix 8 43mm",
        4534,
        "multisport_watch",
        2024,
        False,
        "Compact multisport watch - 2024",
        2029,
        "2026-01-14",
    ),
    GarminDeviceInfo(
        "Fenix 8 Pro",
        4631,
        "multisport_watch",
        2024,
        False,
        "Pro multisport watch - 2024",
        2029,
        "2026-01-14",
    ),
    GarminDeviceInfo(
        "Fenix 7S",
        3905,
        "multisport_watch",
        2022,
        False,
        "Compact multisport watch - 2022",
        2511,
        "2026-01-21",
    ),
    GarminDeviceInfo(
        "Fenix 7X",
        3907,
        "multisport_watch",
        2022,
        False,
        "Large multisport watch - 2022",
        2511,
        "2026-01-21",
    ),
    GarminDeviceInfo(
        "Fenix 7S Pro Solar",
        4374,
        "multisport_watch",
        2023,
        False,
        "Compact pro solar - 2023",
        2511,
        "2026-01-21",
    ),
    GarminDeviceInfo(
        "Fenix 7 Pro Solar",
        4375,
        "multisport_watch",
        2023,
        False,
        "Pro solar multisport - 2023",
        2511,
        "2026-01-21",
    ),
    GarminDeviceInfo(
        "Fenix 7X Pro Solar",
        4376,
        "multisport_watch",
        2023,
        False,
        "Large pro solar - 2023",
        2511,
        "2026-01-21",
    ),
    GarminDeviceInfo(
        "Epix Pro 42mm",
        4312,
        "multisport_watch",
        2023,
        False,
        "Compact AMOLED - 2023",
        2511,
        "2026-01-21",
    ),
    GarminDeviceInfo(
        "Epix Pro 47mm",
        4313,
        "multisport_watch",
        2023,
        False,
        "Mid AMOLED - 2023",
        2511,
        "2026-01-21",
    ),
    GarminDeviceInfo(
        "Epix Pro 51mm",
        4314,
        "multisport_watch",
        2023,
        False,
        "Large AMOLED - 2023",
        2511,
        "2026-01-21",
    ),
    GarminDeviceInfo(
        "Forerunner 265 Large",
        4257,
        "multisport_watch",
        2023,
        False,
        "AMOLED running watch - 2023",
        2709,
        "2026-01-15",
    ),
    GarminDeviceInfo(
        "Forerunner 265 Small",
        4258,
        "multisport_watch",
        2023,
        False,
        "Compact AMOLED running - 2023",
        2709,
        "2026-01-15",
    ),
    GarminDeviceInfo(
        "Forerunner 255",
        3992,
        "multisport_watch",
        2022,
        False,
        "Mid-range running watch - 2022",
        2709,
        "2026-01-15",
    ),
    GarminDeviceInfo(
        "Forerunner 255 Music",
        3990,
        "multisport_watch",
        2022,
        False,
        "Running watch with music - 2022",
        2709,
        "2026-01-15",
    ),
    GarminDeviceInfo(
        "Forerunner 255S",
        3993,
        "multisport_watch",
        2022,
        False,
        "Compact running watch - 2022",
        2709,
        "2026-01-15",
    ),
    GarminDeviceInfo(
        "Forerunner 255S Music",
        3991,
        "multisport_watch",
        2022,
        False,
        "Compact with music - 2022",
        2709,
        "2026-01-15",
    ),
    GarminDeviceInfo(
        "Forerunner 945",
        3113,
        "multisport_watch",
        2019,
        False,
        "Premium running watch - 2019",
        1370,
        "2024-12-02",
    ),
    # Tacx trainers (is_common=False)
    GarminDeviceInfo(
        "Tacx Training App (Win)",
        20533,
        "trainer",
        2020,
        False,
        "Tacx desktop app - Windows",
    ),
    GarminDeviceInfo(
        "Tacx Training App (Mac)",
        20534,
        "trainer",
        2020,
        False,
        "Tacx desktop app - macOS",
    ),
    GarminDeviceInfo(
        "Tacx Training App (Android)",
        30045,
        "trainer",
        2020,
        False,
        "Tacx mobile app - Android",
    ),
    GarminDeviceInfo(
        "Tacx Training App (iOS)",
        30046,
        "trainer",
        2020,
        False,
        "Tacx mobile app - iOS",
    ),
]


def get_supported_garmin_devices(show_all: bool = False) -> list[tuple[str, int, str]]:
    """Get list of Garmin devices for picker UI.

    Combines devices from fit_tool's GarminProduct enum (filtered to cycling/training
    devices with "EDGE", "TACX", or "TRAINING" in their names) with the supplemental
    device registry containing modern devices with metadata.

    Args:
        show_all: If False, return only common devices (is_common=True). If True,
            return all devices. Defaults to False.

    Returns:
        List of tuples containing (display_name, product_id, description).
        Sorted by: is_common (desc), year_released (desc), name (asc).

    Examples:
        >>> # Get common devices only
        >>> devices = get_supported_garmin_devices(show_all=False)
        >>> print(devices[0])
        ('Edge 1050', 4440, 'Latest flagship bike computer - 2024')
        >>>
        >>> # Get all devices
        >>> all_devices = get_supported_garmin_devices(show_all=True)
        >>> len(all_devices) > len(devices)
        True
    """
    from fit_file_faker.vendor.fit_tool.profile.profile_type import GarminProduct

    # Step 1: Get devices from fit_tool enum (filtered to cycling/training)
    fit_tool_devices = {}
    for attr_name in dir(GarminProduct):
        if not attr_name.startswith("_") and attr_name.isupper():
            if any(kw in attr_name for kw in ["EDGE", "TACX", "TRAINING"]):
                try:
                    value = getattr(GarminProduct, attr_name).value
                    # Convert enum name to readable format (e.g., EDGE_1030 -> Edge 1030)
                    display_name = attr_name.replace("_", " ").title()
                    fit_tool_devices[value] = (display_name, value, "")
                except AttributeError:  # pragma: no cover
                    continue

    # Step 2: Get devices from supplemental registry
    supplemental_devices = {}
    for device in SUPPLEMENTAL_GARMIN_DEVICES:
        if not show_all and not device.is_common:
            continue
        supplemental_devices[device.product_id] = (
            device.name,
            device.product_id,
            device.description,
        )

    # Step 3: Merge (supplemental overrides fit_tool for duplicate IDs)
    merged_devices = {**fit_tool_devices, **supplemental_devices}

    # Step 4: Sort by is_common (desc), year (desc), name (asc)
    # Create lookup for sorting metadata
    device_meta = {d.product_id: d for d in SUPPLEMENTAL_GARMIN_DEVICES}

    def sort_key(item):
        name, product_id, description = item
        meta = device_meta.get(product_id)
        if meta:
            # Supplemental device - use metadata
            return (not meta.is_common, -meta.year_released, meta.name)
        else:
            # fit_tool device - sort after common devices
            return (True, 0, name)

    return sorted(merged_devices.values(), key=sort_key)


class AppType(Enum):
    """Supported trainer/cycling applications.

    Each app type has associated directory detection logic and display names.
    Used to identify the source application for FIT files and enable
    platform-specific auto-detection.

    Attributes:
        TP_VIRTUAL: TrainingPeaks Virtual (formerly indieVelo)
        ZWIFT: Zwift virtual cycling platform
        MYWHOOSH: MyWhoosh virtual cycling platform
        CUSTOM: Custom/manual path specification
    """

    TP_VIRTUAL = "tp_virtual"
    ZWIFT = "zwift"
    MYWHOOSH = "mywhoosh"
    CUSTOM = "custom"


@dataclass
class Profile:
    """Single profile configuration.

    Represents a complete configuration profile with app type, credentials,
    and FIT files directory. Each profile is independent with isolated
    Garmin Connect credentials.

    Attributes:
        name: Unique profile identifier (used for display and garth dir naming)
        app_type: Type of trainer app (for auto-detection and validation)
        garmin_username: Garmin Connect account email address
        garmin_password: Garmin Connect account password
        fitfiles_path: Path to directory containing FIT files to process
        manufacturer: Manufacturer ID to use for device simulation (defaults to Garmin)
        device: Device/product ID to use for device simulation (defaults to Edge 830)
        serial_number: Device serial number (auto-generated if not specified)
        software_version: Firmware version in FIT format (e.g., 2922 = v29.22). If None,
            no FileCreatorMessage will be added to FIT files.

    Examples:
        >>> from pathlib import Path
        >>> profile = Profile(
        ...     name="zwift",
        ...     app_type=AppType.ZWIFT,
        ...     garmin_username="user@example.com",
        ...     garmin_password="secret",
        ...     fitfiles_path=Path("/Users/user/Documents/Zwift/Activities")
        ... )
    """

    name: str
    app_type: AppType
    garmin_username: str
    garmin_password: str
    fitfiles_path: Path
    manufacturer: int | None = None
    device: int | None = None
    serial_number: int | None = None
    software_version: int | None = None

    def __post_init__(self):
        """Convert string types to proper objects after initialization.

        Handles deserialization from JSON where app_type may be a string
        and fitfiles_path may be a string path. Also sets default values
        for manufacturer and device if not specified.
        """
        from fit_file_faker.vendor.fit_tool.profile.profile_type import (
            GarminProduct,
            Manufacturer,
        )

        if isinstance(self.app_type, str):
            self.app_type = AppType(self.app_type)
        if isinstance(self.fitfiles_path, str):
            self.fitfiles_path = Path(self.fitfiles_path)

        # Set defaults for manufacturer and device if not specified
        if self.manufacturer is None:
            self.manufacturer = Manufacturer.GARMIN.value
        if self.device is None:
            self.device = GarminProduct.EDGE_830.value

        # Generate serial number if not specified
        if self.serial_number is None:
            import random

            self.serial_number = random.randint(1_000_000_000, 4_294_967_295)

    def get_manufacturer_name(self) -> str:
        """Get human-readable manufacturer name.

        Returns:
            Manufacturer name if found in enum, otherwise "UNKNOWN (id)".

        Examples:
            >>> profile.get_manufacturer_name()
            'GARMIN'
        """
        from fit_file_faker.vendor.fit_tool.profile.profile_type import Manufacturer

        try:
            return Manufacturer(self.manufacturer).name
        except ValueError:
            return f"UNKNOWN ({self.manufacturer})"

    def get_device_name(self) -> str:
        """Get human-readable device name.

        Returns:
            Device name if found in GarminProduct enum or supplemental registry,
            otherwise "UNKNOWN (id)".

        Examples:
            >>> profile.get_device_name()
            'EDGE_830'
            >>> # For supplemental device
            >>> profile.device = 4440
            >>> profile.get_device_name()
            'Edge 1050'
        """
        from fit_file_faker.vendor.fit_tool.profile.profile_type import GarminProduct

        # Try fit_tool enum first
        try:
            return GarminProduct(self.device).name
        except ValueError:
            # Fallback to supplemental registry
            for device_info in SUPPLEMENTAL_GARMIN_DEVICES:
                if device_info.product_id == self.device:
                    return device_info.name
            # Unknown device
            return f"UNKNOWN ({self.device})"

    def validate_serial_number(self) -> bool:
        """Validate that serial_number is valid for FIT spec (uint32z).

        Returns:
            True if serial_number is valid (1,000,000,000 to 4,294,967,295), False otherwise.

        Examples:
            >>> profile.serial_number = 1234567890
            >>> profile.validate_serial_number()
            True
        """
        if self.serial_number is None:
            return False
        if not isinstance(self.serial_number, int):
            return False
        return 1_000_000_000 <= self.serial_number <= 4_294_967_295


@dataclass
class Config:
    """Multi-profile configuration container for Fit File Faker.

    Stores multiple profile configurations, each with independent Garmin
    credentials and FIT files directory. Supports backward compatibility
    with single-profile configs via automatic migration.

    Attributes:
        profiles: List of Profile objects, each representing a complete
            configuration for a trainer app and Garmin account.
        default_profile: Name of the default profile to use when no profile
            is explicitly specified. If None, the first profile is used.

    Examples:
        >>> from pathlib import Path
        >>> config = Config(
        ...     profiles=[
        ...         Profile(
        ...             name="tpv",
        ...             app_type=AppType.TP_VIRTUAL,
        ...             garmin_username="user@example.com",
        ...             garmin_password="secret",
        ...             fitfiles_path=Path("/home/user/TPVirtual/abc123/FITFiles")
        ...         )
        ...     ],
        ...     default_profile="tpv"
        ... )
        >>> profile = config.get_profile("tpv")
        >>> default = config.get_default_profile()
    """

    profiles: list[Profile]
    default_profile: str | None = None

    def __post_init__(self):
        """Convert dict profiles to Profile objects after initialization.

        Handles deserialization from JSON where profiles may be dictionaries
        instead of Profile objects.
        """
        # Convert dict profiles to Profile objects
        if self.profiles and isinstance(self.profiles[0], dict):
            self.profiles = [Profile(**p) for p in self.profiles]

    def get_profile(self, name: str) -> Profile | None:
        """Get profile by name.

        Args:
            name: The name of the profile to retrieve.

        Returns:
            Profile object if found, None otherwise.

        Examples:
            >>> config = Config(profiles=[Profile(name="test", ...)])
            >>> profile = config.get_profile("test")
        """
        return next((p for p in self.profiles if p.name == name), None)

    def get_default_profile(self) -> Profile | None:
        """Get the default profile or first profile if no default set.

        Returns:
            The default Profile object, or the first profile if no default
            is set, or None if no profiles exist.

        Examples:
            >>> config = Config(profiles=[...], default_profile="tpv")
            >>> profile = config.get_default_profile()
        """
        if self.default_profile:
            return self.get_profile(self.default_profile)
        return self.profiles[0] if self.profiles else None


def migrate_legacy_config(old_config: dict) -> Config:
    """Migrate single-profile config to multi-profile format.

    Detects legacy config structure (v1.2.4 and earlier) and converts to
    multi-profile format. Creates a "default" profile with existing values
    and sets it as the default profile.

    Args:
        old_config: Dictionary containing either legacy single-profile config
            (keys: garmin_username, garmin_password, fitfiles_path) or new
            multi-profile config (keys: profiles, default_profile).

    Returns:
        Config object in multi-profile format. If already migrated, returns
        as-is. Otherwise, creates new Config with "default" profile.

    Examples:
        >>> legacy = {
        ...     "garmin_username": "user@example.com",
        ...     "garmin_password": "secret",
        ...     "fitfiles_path": "/path/to/fitfiles"
        ... }
        >>> config = migrate_legacy_config(legacy)
        >>> config.profiles[0].name
        'default'
        >>> config.default_profile
        'default'
    """
    # Check if already migrated (has 'profiles' key)
    if "profiles" in old_config:
        _logger.debug("Config already in multi-profile format")
        return Config(**old_config)

    # Legacy config detected - migrate to multi-profile format
    _logger.info(
        "Detected legacy single-profile config, migrating to multi-profile format"
    )

    # Extract legacy values
    garmin_username = old_config.get("garmin_username")
    garmin_password = old_config.get("garmin_password")
    fitfiles_path = old_config.get("fitfiles_path")

    # Create default profile from legacy values
    # Default to TP_VIRTUAL as that was the original use case
    profile = Profile(
        name="default",
        app_type=AppType.TP_VIRTUAL,
        garmin_username=garmin_username or "",
        garmin_password=garmin_password or "",
        fitfiles_path=Path(fitfiles_path) if fitfiles_path else Path.home(),
    )

    # Create new multi-profile config
    new_config = Config(profiles=[profile], default_profile="default")

    _logger.info(
        'Migration complete. Your existing settings are now in the "default" profile.'
    )
    return new_config


class ConfigManager:
    """Manages configuration file operations and validation.

    Handles loading, saving, and validating configuration stored in a
    platform-specific user configuration directory. Provides interactive
    configuration building for missing or invalid values.

    The configuration file is stored as `.config.json` in the user's
    config directory (location varies by platform).

    Attributes:
        config_file: Path to the JSON configuration file.
        config_keys: List of required configuration keys.
        config: Current Config object loaded from file.

    Examples:
        >>> from fit_file_faker.config import config_manager
        >>>
        >>> # Check if config is valid
        >>> if not config_manager.is_valid():
        ...     print(f"Config file: {config_manager.get_config_file_path()}")
        ...     config_manager.build_config_file()
        >>>
        >>> # Access config values
        >>> username = config_manager.config.garmin_username
    """

    def __init__(self):
        """Initialize the configuration manager.

        Creates the config file if it doesn't exist and loads existing
        configuration or creates a new empty Config object.
        """
        self.config_file = dirs.user_config_path / ".config.json"
        self.config_keys = ["garmin_username", "garmin_password", "fitfiles_path"]
        self.config = self._load_config()

    def _load_config(self) -> Config:
        """Load configuration from file or create new Config if file doesn't exist.

        Automatically migrates legacy single-profile configs (v1.2.4 and earlier)
        to multi-profile format. The migration is transparent and preserves all
        existing settings in a "default" profile. Migrated configs are automatically
        saved back to disk in the new format.

        Returns:
            Loaded Config object if file exists and contains valid JSON,
            otherwise a new empty Config object with no profiles.

        Note:
            Creates an empty config file if one doesn't exist.
        """
        self.config_file.touch(exist_ok=True)

        with self.config_file.open("r") as f:
            if self.config_file.stat().st_size == 0:
                # Empty file - return empty config
                return Config(profiles=[], default_profile=None)
            else:
                # Load from JSON and migrate if necessary
                config_dict = json.load(f)
                was_legacy = "profiles" not in config_dict
                config = migrate_legacy_config(config_dict)

                # Save migrated config back to file if migration occurred
                if was_legacy:
                    _logger.debug("Saving migrated config to file")
                    with self.config_file.open("w") as fw:
                        json.dump(asdict(config), fw, indent=2, cls=PathEncoder)

                # Migrate profiles without serial numbers
                migrated = False
                for profile in config.profiles:
                    if profile.serial_number is None:
                        import random

                        profile.serial_number = random.randint(
                            1_000_000_000, 4_294_967_295
                        )
                        migrated = True
                        _logger.info(
                            f'Generated serial number for profile "{profile.name}": {profile.serial_number}'
                        )

                # Save migrated config if serial numbers were added
                if migrated:
                    _logger.debug("Saving config with new serial numbers to file")
                    with self.config_file.open("w") as fw:
                        json.dump(asdict(config), fw, indent=2, cls=PathEncoder)

                return config

    def save_config(self) -> None:
        """Save current configuration to file.

        Serializes the current Config object to JSON and writes it to the
        config file with 2-space indentation. Path objects are automatically
        converted to strings via PathEncoder.
        """
        with self.config_file.open("w") as f:
            json.dump(asdict(self.config), f, indent=2, cls=PathEncoder)

    def is_valid(self, excluded_keys: list[str] | None = None) -> bool:
        """Check if configuration is valid (all required keys have values).

        Args:
            excluded_keys: Optional list of keys to exclude from validation.
                Useful when certain config values aren't needed for specific
                operations (e.g., fitfiles_path when path is provided via CLI).

        Returns:
            True if all required (non-excluded) keys have non-None values,
            False otherwise. Logs missing keys as errors.

        Examples:
            >>> # Check all keys
            >>> if not config_manager.is_valid():
            ...     print("Configuration incomplete")
            >>>
            >>> # Exclude fitfiles_path from validation
            >>> if not config_manager.is_valid(excluded_keys=["fitfiles_path"]):
            ...     print("Missing Garmin credentials")
        """
        if excluded_keys is None:
            excluded_keys = []

        # Get default profile for validation
        default_profile = self.config.get_default_profile()
        if not default_profile:
            _logger.error("No default profile configured")
            return False

        missing_vals = []
        for k in self.config_keys:
            if (
                not hasattr(default_profile, k) or getattr(default_profile, k) is None
            ) and k not in excluded_keys:
                missing_vals.append(k)

        if missing_vals:
            _logger.error(
                f"The following configuration values are missing: {missing_vals}"
            )
            return False
        return True

    def build_config_file(
        self,
        overwrite_existing_vals: bool = False,
        rewrite_config: bool = True,
        excluded_keys: list[str] | None = None,
    ) -> None:
        """Interactively build configuration file.

        Prompts the user for missing or invalid configuration values using
        questionary for an interactive CLI experience. Passwords are masked
        during input, and the FIT files path is auto-detected for TrainingPeaks
        Virtual users when possible.

        Args:
            overwrite_existing_vals: If `True`, prompts for all values even if
                they already exist. If `False`, only prompts for missing values.
                Defaults to `False`.
            rewrite_config: If `True`, saves the configuration to disk after
                building. If `False`, only updates the in-memory config object.
                Defaults to `True`.
            excluded_keys: Optional list of keys to skip during interactive
                building. Useful for partial configuration.

        Raises:
            SystemExit: If user presses Ctrl-C to cancel configuration.

        Examples:
            >>> # Interactive setup for missing values only
            >>> config_manager.build_config_file()
            >>>
            >>> # Rebuild entire configuration
            >>> config_manager.build_config_file(overwrite_existing_vals=True)
            >>>
            >>> # Update only credentials (skip fitfiles_path)
            >>> config_manager.build_config_file(
            ...     excluded_keys=["fitfiles_path"]
            ... )

        Note:
            Passwords are masked in both user input and log output for security.
            The final configuration is logged with passwords hidden.
        """
        if excluded_keys is None:
            excluded_keys = []

        # Get or create default profile
        default_profile = self.config.get_default_profile()
        if not default_profile:
            # Create a default profile if none exists
            default_profile = Profile(
                name="default",
                app_type=AppType.TP_VIRTUAL,
                garmin_username="",
                garmin_password="",
                fitfiles_path=Path.home(),
            )
            self.config.profiles.append(default_profile)
            self.config.default_profile = "default"

        for k in self.config_keys:
            if (
                getattr(default_profile, k) is None
                or not getattr(default_profile, k)
                or overwrite_existing_vals
            ) and k not in excluded_keys:
                valid_input = False
                while not valid_input:
                    try:
                        if (
                            not hasattr(default_profile, k)
                            or getattr(default_profile, k) is None
                        ):
                            _logger.warning(f'Required value "{k}" not found in config')
                        msg = f'Enter value to use for "{k}"'

                        if hasattr(default_profile, k) and getattr(default_profile, k):
                            msg += f'\nor press enter to use existing value of "{getattr(default_profile, k)}"'
                            if k == "garmin_password":
                                msg = msg.replace(
                                    getattr(default_profile, k), "<**hidden**>"
                                )

                        if k != "fitfiles_path":
                            if "password" in k:
                                val = questionary.password(msg).unsafe_ask()
                            else:
                                val = questionary.text(msg).unsafe_ask()
                        else:
                            val = str(
                                get_fitfiles_path(
                                    Path(
                                        getattr(default_profile, "fitfiles_path")
                                    ).parent.parent
                                    if getattr(default_profile, "fitfiles_path")
                                    else None
                                )
                            )

                        if val:
                            valid_input = True
                            setattr(default_profile, k, val)
                        elif hasattr(default_profile, k) and getattr(
                            default_profile, k
                        ):
                            valid_input = True
                            val = getattr(default_profile, k)
                        else:
                            _logger.warning(
                                "Entered input was not valid, please try again (or press Ctrl-C to cancel)"
                            )
                    except KeyboardInterrupt:
                        _logger.error("User canceled input; exiting!")
                        sys.exit(1)

        if rewrite_config:
            self.save_config()

        config_content = json.dumps(asdict(self.config), indent=2, cls=PathEncoder)
        if (
            hasattr(default_profile, "garmin_password")
            and getattr(default_profile, "garmin_password") is not None
        ):
            config_content = config_content.replace(
                cast(str, default_profile.garmin_password), "<**hidden**>"
            )
        _logger.info(f"Config file is now:\n{config_content}")

    def get_config_file_path(self) -> Path:
        """Get the path to the configuration file.

        Returns:
            Path to the .config.json file in the platform-specific user
            configuration directory.

        Examples:
            >>> path = config_manager.get_config_file_path()
            >>> print(f"Config file: {path}")
            Config file: /home/user/.config/FitFileFaker/.config.json
        """
        return self.config_file


def get_fitfiles_path(existing_path: Path | None) -> Path:
    """Auto-find the FITFiles folder inside a TrainingPeaks Virtual directory.

    Attempts to automatically locate the user's TrainingPeaks Virtual FITFiles
    directory. On macOS/Windows, the TPVirtual data directory is auto-detected.
    On Linux, the user is prompted to provide the path.

    If multiple user directories exist, the user is prompted to select one.

    Args:
        existing_path: Optional path to use as default. If provided, this path's
            `parent.parent` is used as the TPVirtual base directory.

    Returns:
        Path to the FITFiles directory (e.g., `~/TPVirtual/abc123def/FITFiles`).

    Raises:
        SystemExit: If no TP Virtual user folder is found, the user rejects
            the auto-detected folder, or the user cancels the selection.

    Note:
        The TPVirtual folder location can be overridden using the
        `TPV_DATA_PATH` environment variable. User directories are identified
        by 16-character hexadecimal folder names.

    Examples:
        >>> # Auto-detect FITFiles path
        >>> path = get_fitfiles_path(None)
        >>> print(path)
        /Users/me/TPVirtual/a1b2c3d4e5f6g7h8/FITFiles
    """
    _logger.info("Getting FITFiles folder")

    TPVPath = get_tpv_folder(existing_path)
    res = [f for f in os.listdir(TPVPath) if re.search(r"\A(\w){16}\Z", f)]
    if len(res) == 0:
        _logger.error(
            'Cannot find a TP Virtual User folder in "%s", please check if you have previously logged into TP Virtual',
            TPVPath,
        )
        sys.exit(1)
    elif len(res) == 1:
        title = f'Found TP Virtual User directory at "{Path(TPVPath) / res[0]}", is this correct? '
        option = questionary.select(title, choices=["yes", "no"]).ask()
        if option == "no":
            # Get config manager instance to access config file path
            config_manager = ConfigManager()
            _logger.error(
                'Failed to find correct TP Virtual User folder please manually configure "fitfiles_path" in config file: %s',
                config_manager.get_config_file_path().absolute(),
            )
            sys.exit(1)
        else:
            option = res[0]
    else:
        title = "Found multiple TP Virtual User directories, please select the directory for your user: "
        option = questionary.select(title, choices=res).ask()
    TPV_data_path = Path(TPVPath) / option
    _logger.info(
        f'Found TP Virtual User directory: "{str(TPV_data_path.absolute())}", '
        'setting "fitfiles_path" in config file'
    )
    return TPV_data_path / "FITFiles"


def get_tpv_folder(default_path: Path | None) -> Path:
    """Get the TrainingPeaks Virtual base folder path.

    Auto-detects the TPVirtual directory based on platform, or prompts the
    user to provide it if auto-detection is not available.

    Platform-specific default locations:

    - macOS: `~/TPVirtual`
    - Windows: `~/Documents/TPVirtual`
    - Linux: User is prompted (no auto-detection)

    Args:
        default_path: Optional default path to show in the prompt for Linux users.

    Returns:
        Path to the `TPVirtual` base directory (not the `FITFiles` subdirectory).

    Note:
        The auto-detected path can be overridden by setting the `TPV_DATA_PATH`
        environment variable.

    Examples:
        >>> # macOS
        >>> path = get_tpv_folder(None)
        >>> print(path)
        /Users/me/TPVirtual
        >>>
        >>> # Linux (prompts user)
        >>> path = get_tpv_folder(Path("/home/me/custom/path"))
        Please enter your TrainingPeaks Virtual data folder: /home/me/TPVirtual
    """
    if os.environ.get("TPV_DATA_PATH", None):
        p = str(os.environ.get("TPV_DATA_PATH"))
        _logger.info(f'Using TPV_DATA_PATH value read from the environment: "{p}"')
        return Path(p)
    if sys.platform == "darwin":
        TPVPath = os.path.expanduser("~/TPVirtual")
    elif sys.platform == "win32":
        TPVPath = os.path.expanduser("~/Documents/TPVirtual")
    else:
        _logger.warning(
            "TrainingPeaks Virtual user folder can only be automatically detected on Windows and OSX"
        )
        TPVPath = questionary.path(
            'Please enter your TrainingPeaks Virtual data folder (by default, ends with "TPVirtual"): ',
            default=str(default_path) if default_path else "",
        ).ask()
    return Path(TPVPath)


class ProfileManager:
    """Manages profile CRUD operations and TUI interactions.

    Provides methods for creating, reading, updating, and deleting profiles,
    as well as interactive TUI wizards for profile management.

    Attributes:
        config_manager: Reference to the global ConfigManager instance.
    """

    def __init__(self, config_manager: ConfigManager):
        """Initialize ProfileManager with config manager reference.

        Args:
            config_manager: The ConfigManager instance to use for persistence.
        """
        self.config_manager = config_manager

    def create_profile(
        self,
        name: str,
        app_type: AppType,
        garmin_username: str,
        garmin_password: str,
        fitfiles_path: Path,
        manufacturer: int | None = None,
        device: int | None = None,
        serial_number: int | None = None,
        software_version: int | None = None,
    ) -> Profile:
        """Create a new profile and add it to config.

        Args:
            name: Unique profile name.
            app_type: Type of trainer application.
            garmin_username: Garmin Connect email.
            garmin_password: Garmin Connect password.
            fitfiles_path: Path to FIT files directory.
            manufacturer: Manufacturer ID for device simulation (defaults to Garmin).
            device: Device/product ID for device simulation (defaults to Edge 830).
            serial_number: Device serial number (defaults to auto-generated 10-digit number).
            software_version: Firmware version in FIT format (e.g., 2922 = v29.22). If None,
                no FileCreatorMessage will be added to FIT files.

        Returns:
            The newly created Profile object.

        Raises:
            ValueError: If profile name already exists.

        Examples:
            >>> manager = ProfileManager(config_manager)
            >>> profile = manager.create_profile(
            ...     "zwift",
            ...     AppType.ZWIFT,
            ...     "user@example.com",
            ...     "secret",
            ...     Path("/path/to/fitfiles")
            ... )
        """
        # Check if profile name already exists
        if self.config_manager.config.get_profile(name):
            raise ValueError(f'Profile "{name}" already exists')

        # Auto-lookup software_version from device if not provided
        if software_version is None and device is not None:
            device_info = next(
                (d for d in SUPPLEMENTAL_GARMIN_DEVICES if d.product_id == device), None
            )
            if device_info and device_info.software_version:
                software_version = device_info.software_version

        # Create new profile
        profile = Profile(
            name=name,
            app_type=app_type,
            garmin_username=garmin_username,
            garmin_password=garmin_password,
            fitfiles_path=fitfiles_path,
            manufacturer=manufacturer,
            device=device,
            serial_number=serial_number,
            software_version=software_version,
        )

        # Validate serial number if provided
        if serial_number is not None and not profile.validate_serial_number():
            import random

            _logger.warning(
                f"Invalid serial number {serial_number}, generating a new one"
            )
            profile.serial_number = random.randint(1_000_000_000, 4_294_967_295)

        # Add to config and save
        self.config_manager.config.profiles.append(profile)
        self.config_manager.save_config()

        _logger.info(f'Created profile "{name}"')
        return profile

    def get_profile(self, name: str) -> Profile | None:
        """Get profile by name.

        Args:
            name: The profile name to retrieve.

        Returns:
            Profile object if found, None otherwise.
        """
        return self.config_manager.config.get_profile(name)

    def list_profiles(self) -> list[Profile]:
        """Get list of all profiles.

        Returns:
            List of all Profile objects.
        """
        return self.config_manager.config.profiles

    def update_profile(
        self,
        name: str,
        app_type: AppType | None = None,
        garmin_username: str | None = None,
        garmin_password: str | None = None,
        fitfiles_path: Path | None = None,
        new_name: str | None = None,
        manufacturer: int | None = None,
        device: int | None = None,
        serial_number: int | None = None,
        software_version: int | None = None,
    ) -> Profile:
        """Update an existing profile.

        Args:
            name: Name of profile to update.
            app_type: New app type (optional).
            garmin_username: New Garmin username (optional).
            garmin_password: New Garmin password (optional).
            fitfiles_path: New FIT files path (optional).
            new_name: New profile name (optional).
            manufacturer: New manufacturer ID (optional).
            device: New device ID (optional).
            serial_number: New serial number (optional).
            software_version: New firmware version in FIT format (optional).

        Returns:
            The updated Profile object.

        Raises:
            ValueError: If profile not found or new name already exists.
        """
        profile = self.get_profile(name)
        if not profile:
            raise ValueError(f'Profile "{name}" not found')

        # Check if new name conflicts
        if new_name and new_name != name:
            if self.get_profile(new_name):
                raise ValueError(f'Profile "{new_name}" already exists')
            profile.name = new_name

        # Update fields if provided
        if app_type is not None:
            profile.app_type = app_type
        if garmin_username is not None:
            profile.garmin_username = garmin_username
        if garmin_password is not None:
            profile.garmin_password = garmin_password
        if fitfiles_path is not None:
            profile.fitfiles_path = fitfiles_path
        if manufacturer is not None:
            profile.manufacturer = manufacturer
        if device is not None:
            profile.device = device
            # Auto-lookup software_version from device if not explicitly provided
            if software_version is None:
                device_info = next(
                    (d for d in SUPPLEMENTAL_GARMIN_DEVICES if d.product_id == device),
                    None,
                )
                if device_info and device_info.software_version:
                    software_version = device_info.software_version
        if serial_number is not None:
            # Validate serial number
            temp_profile = Profile(
                name="temp",
                app_type=profile.app_type,
                garmin_username="",
                garmin_password="",
                fitfiles_path=Path(),
                serial_number=serial_number,
            )
            if not temp_profile.validate_serial_number():
                raise ValueError(
                    f"Invalid serial number {serial_number}. Must be a 10-digit integer."
                )
            profile.serial_number = serial_number
        if software_version is not None:
            profile.software_version = software_version

        # Update default_profile if name changed
        if new_name and self.config_manager.config.default_profile == name:
            self.config_manager.config.default_profile = new_name

        self.config_manager.save_config()
        _logger.info(f'Updated profile "{new_name or name}"')
        return profile

    def delete_profile(self, name: str) -> None:
        """Delete a profile.

        Args:
            name: Name of profile to delete.

        Raises:
            ValueError: If profile not found or trying to delete the only profile.
        """
        profile = self.get_profile(name)
        if not profile:
            raise ValueError(f'Profile "{name}" not found')

        # Prevent deleting the only profile
        if len(self.config_manager.config.profiles) == 1:
            raise ValueError("Cannot delete the only profile")

        # Remove from profiles list
        self.config_manager.config.profiles.remove(profile)

        # Update default if we deleted the default profile
        if self.config_manager.config.default_profile == name:
            # Set first remaining profile as default
            self.config_manager.config.default_profile = (
                self.config_manager.config.profiles[0].name
            )

        self.config_manager.save_config()
        _logger.info(f'Deleted profile "{name}"')

    def set_default_profile(self, name: str) -> None:
        """Set a profile as the default.

        Args:
            name: Name of profile to set as default.

        Raises:
            ValueError: If profile not found.
        """
        profile = self.get_profile(name)
        if not profile:
            raise ValueError(f'Profile "{name}" not found')

        self.config_manager.config.default_profile = name
        self.config_manager.save_config()
        _logger.info(f'Set "{name}" as default profile')

    def display_profiles_table(self) -> None:
        """Display all profiles in a Rich table.

        Shows profile name, app type, device, Garmin username, and FIT files path
        in a formatted table. Marks the default profile with ⭐.
        """
        console = Console()
        table = Table(
            title="📋 FIT File Faker - Profiles",
            show_header=True,
            header_style="bold cyan",
        )

        table.add_column("Name", style="green", no_wrap=True)
        table.add_column("App", style="blue")
        table.add_column("Device", style="cyan")
        table.add_column("Serial #", style="bright_blue")
        table.add_column("Garmin User", style="yellow")
        table.add_column("FIT Path", style="magenta")

        profiles = self.list_profiles()
        if not profiles:
            console.print("[yellow]No profiles configured yet.[/yellow]")
            return

        for profile in profiles:
            # Mark default profile with star
            name_display = profile.name
            if profile.name == self.config_manager.config.default_profile:
                name_display = f"{profile.name} ⭐"

            # Format app type for display using detector's short name
            from fit_file_faker.app_registry import get_detector

            detector = get_detector(profile.app_type)
            app_display = detector.get_short_name()

            # Get device name
            device_display = profile.get_device_name()

            # Format serial number
            serial_display = (
                str(profile.serial_number) if profile.serial_number else "N/A"
            )

            # Truncate long paths
            path_str = str(profile.fitfiles_path)
            if len(path_str) > 40:
                path_str = "..." + path_str[-37:]

            table.add_row(
                name_display,
                app_display,
                device_display,
                serial_display,
                profile.garmin_username,
                path_str,
            )

        console.print(table)

    def interactive_menu(self) -> None:
        """Display interactive profile management menu.

        Shows profile table and presents menu options for creating,
        editing, deleting profiles, and setting default.
        """
        while True:
            console = Console()
            console.print()  # Blank line
            self.display_profiles_table()
            console.print()  # Blank line

            choices = [
                "Create new profile",
                "Edit existing profile",
                "Delete profile",
                "Set default profile",
                "Exit",
            ]

            action = questionary.select(
                "What would you like to do?",
                choices=choices,
                style=questionary.Style([("highlighted", "fg:cyan bold")]),
            ).ask()

            if not action or action == "Exit":
                break

            try:
                if action == "Create new profile":
                    self.create_profile_wizard()
                elif action == "Edit existing profile":
                    self.edit_profile_wizard()
                elif action == "Delete profile":
                    self.delete_profile_wizard()
                elif action == "Set default profile":
                    self.set_default_wizard()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Operation cancelled.[/yellow]")
                continue

    def create_profile_wizard(self) -> Profile | None:
        """Interactive wizard for creating a new profile.

        Follows app-first flow:
        1. Select app type
        2. Auto-detect directory (with confirm/override)
        3. Enter Garmin credentials
        4. Enter profile name

        Returns:
            The newly created Profile, or None if cancelled.
        """
        from fit_file_faker.app_registry import get_detector

        console = Console()
        console.print("\n[bold cyan]Create New Profile[/bold cyan]")

        # Step 1: Select app type
        app_choices = [
            questionary.Choice("TrainingPeaks Virtual", AppType.TP_VIRTUAL),
            questionary.Choice("Zwift", AppType.ZWIFT),
            questionary.Choice("MyWhoosh", AppType.MYWHOOSH),
            questionary.Choice("Custom (manual path)", AppType.CUSTOM),
        ]

        app_type = questionary.select(
            "Which trainer app will this profile use?", choices=app_choices
        ).ask()

        if not app_type:
            return None

        # Step 2: Directory detection
        detector = get_detector(app_type)
        suggested_path = detector.get_default_path()

        if suggested_path:
            console.print(
                f"\n[green]✓ Found {detector.get_display_name()} directory:[/green]"
            )
            console.print(f"  {suggested_path}")
            use_detected = questionary.confirm(
                "Use this directory?", default=True
            ).ask()

            if use_detected:
                fitfiles_path = suggested_path
            else:
                path_input = questionary.path("Enter FIT files directory path:").ask()
                if not path_input:
                    return None
                fitfiles_path = Path(path_input)
        else:
            console.print(
                f"\n[yellow]Could not auto-detect {detector.get_display_name()} directory[/yellow]"
            )
            path_input = questionary.path("Enter FIT files directory path:").ask()
            if not path_input:
                return None
            fitfiles_path = Path(path_input)

        # Step 3: Garmin credentials
        garmin_username = questionary.text(
            "Enter Garmin Connect email:", validate=lambda x: len(x) > 0
        ).ask()
        if not garmin_username:
            return None

        garmin_password = questionary.password(
            "Enter Garmin Connect password:", validate=lambda x: len(x) > 0
        ).ask()
        if not garmin_password:
            return None

        # Step 4: Device customization (optional)
        manufacturer = None
        device = None
        serial_number = None
        software_version = None
        customize_device = questionary.confirm(
            "Customize device simulation? (default: Garmin Edge 830)", default=False
        ).ask()

        if customize_device:
            # Two-level menu: common devices first, then "View all devices" option
            show_all = False
            device_selected = False
            selected_device_name = None

            while not device_selected:
                # Get list of supported devices (common or all based on show_all flag)
                supported_devices = get_supported_garmin_devices(show_all=show_all)

                # Build device choices for the menu
                device_choices = []

                if not show_all:
                    # Level 1: Common devices grouped by category
                    # Bike computers
                    bike_computers = [
                        (name, device_id, desc)
                        for name, device_id, desc in supported_devices
                        if any(
                            d.product_id == device_id and d.category == "bike_computer"
                            for d in SUPPLEMENTAL_GARMIN_DEVICES
                        )
                    ]
                    for name, device_id, desc in bike_computers:
                        device_choices.append(
                            questionary.Choice(
                                f"{name} ({device_id})", (name, device_id)
                            )
                        )

                    # Add separator
                    device_choices.append(
                        questionary.Separator("───────────────────────────")
                    )

                    # Multisport watches
                    watches = [
                        (name, device_id, desc)
                        for name, device_id, desc in supported_devices
                        if any(
                            d.product_id == device_id
                            and d.category == "multisport_watch"
                            for d in SUPPLEMENTAL_GARMIN_DEVICES
                        )
                    ]
                    for name, device_id, desc in watches:
                        device_choices.append(
                            questionary.Choice(
                                f"{name} ({device_id})", (name, device_id)
                            )
                        )

                    # Add separator and special options
                    device_choices.append(
                        questionary.Separator("───────────────────────────")
                    )
                    device_choices.append(
                        questionary.Choice(
                            "View all devices (70+ options)...", ("VIEW_ALL", None)
                        )
                    )
                    device_choices.append(
                        questionary.Choice(
                            "Custom (enter numeric ID)", ("CUSTOM", None)
                        )
                    )
                else:
                    # Level 2: All devices
                    # Group by category
                    categories = {}
                    for name, device_id, desc in supported_devices:
                        # Determine category
                        category = "Other"
                        for d in SUPPLEMENTAL_GARMIN_DEVICES:
                            if d.product_id == device_id:
                                category = d.category.replace("_", " ").title()
                                break

                        if category not in categories:
                            categories[category] = []

                        display = f"{name} ({device_id})"
                        categories[category].append((display, (name, device_id)))

                    # Add devices by category
                    for category in sorted(categories.keys()):
                        device_choices.append(
                            questionary.Separator(f"─── {category} ───")
                        )
                        for display, value in categories[category]:
                            device_choices.append(questionary.Choice(display, value))

                    # Add separator and special options
                    device_choices.append(
                        questionary.Separator("───────────────────────────")
                    )
                    device_choices.append(
                        questionary.Choice("Back to common devices", ("BACK", None))
                    )
                    device_choices.append(
                        questionary.Choice(
                            "Custom (enter numeric ID)", ("CUSTOM", None)
                        )
                    )

                # Show the menu
                selected = questionary.select(
                    "Select Garmin device to simulate:", choices=device_choices
                ).ask()

                if not selected:
                    return None

                # Extract value from Choice object if necessary (for testing)
                if hasattr(selected, "value"):
                    selected = selected.value

                device_name, device_id = selected

                if device_name == "VIEW_ALL":
                    # Switch to showing all devices
                    show_all = True
                    continue
                elif device_name == "BACK":
                    # Switch back to common devices
                    show_all = False
                    continue
                elif device_name == "CUSTOM":
                    # Allow custom numeric ID
                    device_input = questionary.text(
                        "Enter numeric device ID:",
                        validate=lambda x: x.isdigit() and int(x) > 0,
                    ).ask()

                    if not device_input:
                        return None

                    device = int(device_input)
                    device_selected = True

                    # Warn if device ID not in enum or supplemental registry
                    from fit_file_faker.vendor.fit_tool.profile.profile_type import (
                        GarminProduct,
                    )

                    try:
                        GarminProduct(device)
                    except ValueError:
                        # Check supplemental registry
                        found = any(
                            d.product_id == device for d in SUPPLEMENTAL_GARMIN_DEVICES
                        )
                        if not found:
                            console.print(
                                f"\n[yellow]⚠ Warning: Device ID {device} is not recognized in the "
                                f"GarminProduct enum or supplemental registry. The profile will still be created.[/yellow]"
                            )
                else:
                    # Device selected
                    device = device_id
                    selected_device_name = device_name
                    device_selected = True

            # Look up software_version from supplemental registry
            if device is not None:
                device_info = next(
                    (d for d in SUPPLEMENTAL_GARMIN_DEVICES if d.product_id == device),
                    None,
                )
                if device_info and device_info.software_version:
                    software_version = device_info.software_version

            # Always use Garmin manufacturer for now
            from fit_file_faker.vendor.fit_tool.profile.profile_type import Manufacturer

            manufacturer = Manufacturer.GARMIN.value

            # Ask about serial number customization
            customize_serial = questionary.confirm(
                "Customize serial number for this device?", default=False
            ).ask()

            if customize_serial:
                # Show instructions for finding device serial number
                console.print(
                    "\n[dim]To find your device's serial number (Unit ID):[/dim]"
                )
                console.print(
                    "[dim]  Garmin Edge: System → About → Copyright Info → Unit ID[/dim]\n"
                )

                serial_input = questionary.text(
                    "Enter 10-digit serial number:",
                    validate=lambda x: (
                        x.isdigit()
                        and len(x) == 10
                        and 1_000_000_000 <= int(x) <= 4_294_967_295
                    )
                    or "Must be a 10-digit number between 1000000000 and 4294967295",
                ).ask()

                if serial_input and serial_input.isdigit():
                    serial_number = int(serial_input)

            if serial_number is None:
                # User declined customization, generate random
                import random

                serial_number = random.randint(1_000_000_000, 4_294_967_295)
        else:
            # User declined device customization, still generate serial for default device
            import random

            serial_number = random.randint(1_000_000_000, 4_294_967_295)

        # Display final device configuration before profile creation
        if device is None:
            device_display = '"Edge 830" (3122)'
        elif selected_device_name:
            device_display = f'"{selected_device_name}" ({device})'
        else:
            device_display = f"Device {device}"
        console.print(f"\n[cyan]Device:[/cyan] [yellow]{device_display}[/yellow]")
        console.print(f"[cyan]Serial Number:[/cyan] [yellow]{serial_number}[/yellow]")
        console.print(
            "[dim](You can change these later via the edit profile menu)[/dim]"
        )

        # Step 5: Profile name
        suggested_name = app_type.value.split("_")[0].lower()
        profile_name = questionary.text(
            "Enter profile name:", default=suggested_name, validate=lambda x: len(x) > 0
        ).ask()
        if not profile_name:
            return None

        # Create the profile
        try:
            profile = self.create_profile(
                name=profile_name,
                app_type=app_type,
                garmin_username=garmin_username,
                garmin_password=garmin_password,
                fitfiles_path=fitfiles_path,
                manufacturer=manufacturer,
                device=device,
                serial_number=serial_number,
                software_version=software_version,
            )
            console.print(
                f"\n[green]✓ Profile '{profile_name}' created successfully![/green]"
            )
            return profile
        except ValueError as e:
            console.print(f"\n[red]✗ Error: {e}[/red]")
            return None

    def edit_profile_wizard(self) -> None:
        """Interactive wizard for editing an existing profile."""
        console = Console()

        profiles = self.list_profiles()
        if not profiles:
            console.print("[yellow]No profiles to edit.[/yellow]")
            return

        # Select profile to edit
        profile_choices = [p.name for p in profiles]
        profile_name = questionary.select(
            "Select profile to edit:", choices=profile_choices
        ).ask()

        if not profile_name:
            return

        profile = self.get_profile(profile_name)
        if not profile:
            return

        console.print(f"\n[bold cyan]Editing Profile: {profile_name}[/bold cyan]")
        console.print("[dim]Leave blank to keep current value[/dim]\n")

        # Ask which fields to update
        new_name = questionary.text(f"Profile name [{profile.name}]:", default="").ask()

        new_username = questionary.text(
            f"Garmin username [{profile.garmin_username}]:", default=""
        ).ask()

        new_password = questionary.password("Garmin password [****]:", default="").ask()

        new_path = questionary.path(
            f"FIT files path [{profile.fitfiles_path}]:", default=""
        ).ask()

        # Ask about device simulation
        new_manufacturer = None
        new_device = None
        new_serial = None
        new_software_version = None
        current_device = profile.get_device_name()
        current_serial = profile.serial_number if profile.serial_number else "N/A"
        edit_device = questionary.confirm(
            f"Edit device simulation? (current: {current_device}, serial: {current_serial})",
            default=False,
        ).ask()

        if edit_device:
            # Two-level menu: common devices first, then "View all devices" option
            show_all = False
            device_selected = False

            while not device_selected:
                # Get list of supported devices (common or all based on show_all flag)
                supported_devices = get_supported_garmin_devices(show_all=show_all)

                # Build device choices for the menu
                device_choices = []

                if not show_all:
                    # Level 1: Common devices grouped by category
                    # Bike computers
                    bike_computers = [
                        (name, device_id, desc)
                        for name, device_id, desc in supported_devices
                        if any(
                            d.product_id == device_id and d.category == "bike_computer"
                            for d in SUPPLEMENTAL_GARMIN_DEVICES
                        )
                    ]
                    for name, device_id, desc in bike_computers:
                        device_choices.append(
                            questionary.Choice(
                                f"{name} ({device_id})", (name, device_id)
                            )
                        )

                    # Add separator
                    device_choices.append(
                        questionary.Separator("───────────────────────────")
                    )

                    # Multisport watches
                    watches = [
                        (name, device_id, desc)
                        for name, device_id, desc in supported_devices
                        if any(
                            d.product_id == device_id
                            and d.category == "multisport_watch"
                            for d in SUPPLEMENTAL_GARMIN_DEVICES
                        )
                    ]
                    for name, device_id, desc in watches:
                        device_choices.append(
                            questionary.Choice(
                                f"{name} ({device_id})", (name, device_id)
                            )
                        )

                    # Add separator and special options
                    device_choices.append(
                        questionary.Separator("───────────────────────────")
                    )
                    device_choices.append(
                        questionary.Choice(
                            "View all devices (70+ options)...", ("VIEW_ALL", None)
                        )
                    )
                    device_choices.append(
                        questionary.Choice(
                            "Custom (enter numeric ID)", ("CUSTOM", None)
                        )
                    )
                else:
                    # Level 2: All devices
                    # Group by category
                    categories = {}
                    for name, device_id, desc in supported_devices:
                        # Determine category
                        category = "Other"
                        for d in SUPPLEMENTAL_GARMIN_DEVICES:
                            if d.product_id == device_id:
                                category = d.category.replace("_", " ").title()
                                break

                        if category not in categories:
                            categories[category] = []

                        display = f"{name} ({device_id})"
                        categories[category].append((display, (name, device_id)))

                    # Add devices by category
                    for category in sorted(categories.keys()):
                        device_choices.append(
                            questionary.Separator(f"─── {category} ───")
                        )
                        for display, value in categories[category]:
                            device_choices.append(questionary.Choice(display, value))

                    # Add separator and special options
                    device_choices.append(
                        questionary.Separator("───────────────────────────")
                    )
                    device_choices.append(
                        questionary.Choice("Back to common devices", ("BACK", None))
                    )
                    device_choices.append(
                        questionary.Choice(
                            "Custom (enter numeric ID)", ("CUSTOM", None)
                        )
                    )

                # Show the menu
                selected = questionary.select(
                    "Select Garmin device to simulate:", choices=device_choices
                ).ask()

                if not selected:
                    device_selected = True
                    continue

                # Extract value from Choice object if necessary (for testing)
                if hasattr(selected, "value"):
                    selected = selected.value

                device_name, device_id = selected

                if device_name == "VIEW_ALL":
                    # Switch to showing all devices
                    show_all = True
                    continue
                elif device_name == "BACK":
                    # Switch back to common devices
                    show_all = False
                    continue
                elif device_name == "CUSTOM":
                    # Allow custom numeric ID
                    device_input = questionary.text(
                        "Enter numeric device ID:",
                        validate=lambda x: x.isdigit() and int(x) > 0,
                    ).ask()

                    if device_input:
                        new_device = int(device_input)
                        device_selected = True

                        # Warn if device ID not in enum or supplemental registry
                        from fit_file_faker.vendor.fit_tool.profile.profile_type import (
                            GarminProduct,
                        )

                        try:
                            GarminProduct(new_device)
                        except ValueError:
                            # Check supplemental registry
                            found = any(
                                d.product_id == new_device
                                for d in SUPPLEMENTAL_GARMIN_DEVICES
                            )
                            if not found:
                                console.print(
                                    f"\n[yellow]⚠ Warning: Device ID {new_device} is not recognized in the "
                                    f"GarminProduct enum or supplemental registry. The profile will still be updated.[/yellow]"
                                )
                else:
                    # Device selected
                    new_device = device_id
                    device_selected = True

            # Look up software_version from supplemental registry
            if new_device is not None:
                device_info = next(
                    (
                        d
                        for d in SUPPLEMENTAL_GARMIN_DEVICES
                        if d.product_id == new_device
                    ),
                    None,
                )
                if device_info and device_info.software_version:
                    new_software_version = device_info.software_version

                # Always use Garmin manufacturer
                from fit_file_faker.vendor.fit_tool.profile.profile_type import (
                    Manufacturer,
                )

                new_manufacturer = Manufacturer.GARMIN.value

            # Ask about serial number editing
            edit_serial = questionary.confirm(
                f"Edit serial number? (current: {current_serial})", default=False
            ).ask()

            if edit_serial:
                # Ask if user wants to enter custom or generate random
                serial_choice = questionary.select(
                    "How would you like to set the serial number?",
                    choices=[
                        questionary.Choice("Generate random serial number", "random"),
                        questionary.Choice("Enter custom serial number", "custom"),
                    ],
                ).ask()

                if serial_choice == "random":
                    import random

                    new_serial = random.randint(1_000_000_000, 4_294_967_295)
                    console.print(
                        f"\n[green]Generated new serial number: {new_serial}[/green]"
                    )
                elif serial_choice == "custom":
                    # Show instructions for finding device serial number
                    console.print(
                        "\n[dim]To find your device's serial number (Unit ID):[/dim]"
                    )
                    console.print(
                        "[dim]  Garmin Edge: System → About → Copyright Info → Unit ID[/dim]\n"
                    )

                    serial_input = questionary.text(
                        "Enter new 10-digit serial number:",
                        default=str(profile.serial_number)
                        if profile.serial_number
                        else "",
                        validate=lambda x: (
                            x.isdigit()
                            and len(x) == 10
                            and 1_000_000_000 <= int(x) <= 4_294_967_295
                        )
                        or "Must be a 10-digit number between 1000000000 and 4294967295",
                    ).ask()

                    if serial_input and serial_input.isdigit():
                        new_serial = int(serial_input)

        # Update profile with provided values
        try:
            self.update_profile(
                name=profile_name,
                new_name=new_name if new_name else None,
                garmin_username=new_username if new_username else None,
                garmin_password=new_password if new_password else None,
                fitfiles_path=Path(new_path) if new_path else None,
                manufacturer=new_manufacturer,
                device=new_device,
                serial_number=new_serial,
                software_version=new_software_version,
            )
            console.print("\n[green]✓ Profile updated successfully![/green]")
        except ValueError as e:
            console.print(f"\n[red]✗ Error: {e}[/red]")

    def delete_profile_wizard(self) -> None:
        """Interactive wizard for deleting a profile with confirmation."""
        console = Console()

        profiles = self.list_profiles()
        if not profiles:
            console.print("[yellow]No profiles to delete.[/yellow]")
            return

        if len(profiles) == 1:
            console.print("[yellow]Cannot delete the only profile.[/yellow]")
            return

        # Select profile to delete
        profile_choices = [p.name for p in profiles]
        profile_name = questionary.select(
            "Select profile to delete:", choices=profile_choices
        ).ask()

        if not profile_name:
            return

        # Confirm deletion
        confirm = questionary.confirm(
            f'Are you sure you want to delete profile "{profile_name}"?',
            default=False,
        ).ask()

        if not confirm:
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return

        # Delete the profile
        try:
            self.delete_profile(profile_name)
            console.print(
                f"\n[green]✓ Profile '{profile_name}' deleted successfully![/green]"
            )
        except ValueError as e:
            console.print(f"\n[red]✗ Error: {e}[/red]")

    def set_default_wizard(self) -> None:
        """Interactive wizard for setting the default profile."""
        console = Console()

        profiles = self.list_profiles()
        if not profiles:
            console.print("[yellow]No profiles available.[/yellow]")
            return

        # Select profile to set as default
        profile_choices = [p.name for p in profiles]
        current_default = self.config_manager.config.default_profile

        profile_name = questionary.select(
            f"Select default profile (current: {current_default}):",
            choices=profile_choices,
        ).ask()

        if not profile_name:
            return

        # Set as default
        try:
            self.set_default_profile(profile_name)
            console.print(
                f"\n[green]✓ '{profile_name}' is now the default profile![/green]"
            )
        except ValueError as e:
            console.print(f"\n[red]✗ Error: {e}[/red]")


# Global configuration manager instance
config_manager = ConfigManager()

# Global profile manager instance
profile_manager = ProfileManager(config_manager)
