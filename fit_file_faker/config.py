"""Configuration management for Fit File Faker.

This module handles all configuration file operations including creation,
validation, loading, and saving. Configuration is stored in a platform-specific
user configuration directory using platformdirs.

The configuration includes Garmin Connect credentials and the path to the
directory containing FIT files to process. For TrainingPeaks Virtual users,
the FIT files directory is auto-detected on macOS and Windows.




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

    def __post_init__(self):
        """Convert string types to proper objects after initialization.

        Handles deserialization from JSON where app_type may be a string
        and fitfiles_path may be a string path.
        """
        if isinstance(self.app_type, str):
            self.app_type = AppType(self.app_type)
        if isinstance(self.fitfiles_path, str):
            self.fitfiles_path = Path(self.fitfiles_path)


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

        missing_vals = []
        for k in self.config_keys:
            if (
                not hasattr(self.config, k) or getattr(self.config, k) is None
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

        for k in self.config_keys:
            if (
                getattr(self.config, k) is None or overwrite_existing_vals
            ) and k not in excluded_keys:
                valid_input = False
                while not valid_input:
                    try:
                        if (
                            not hasattr(self.config, k)
                            or getattr(self.config, k) is None
                        ):
                            _logger.warning(f'Required value "{k}" not found in config')
                        msg = f'Enter value to use for "{k}"'

                        if hasattr(self.config, k) and getattr(self.config, k):
                            msg += f'\nor press enter to use existing value of "{getattr(self.config, k)}"'
                            if k == "garmin_password":
                                msg = msg.replace(
                                    getattr(self.config, k), "<**hidden**>"
                                )

                        if k != "fitfiles_path":
                            if "password" in k:
                                val = questionary.password(msg).unsafe_ask()
                            else:
                                val = questionary.text(msg).unsafe_ask()
                        else:
                            val = str(
                                get_fitfiles_path(
                                    Path(self.config.fitfiles_path).parent.parent
                                    if self.config.fitfiles_path
                                    else None
                                )
                            )

                        if val:
                            valid_input = True
                            setattr(self.config, k, val)
                        elif hasattr(self.config, k) and getattr(self.config, k):
                            valid_input = True
                            val = getattr(self.config, k)
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
            hasattr(self.config, "garmin_password")
            and getattr(self.config, "garmin_password") is not None
        ):
            config_content = config_content.replace(
                cast(str, self.config.garmin_password), "<**hidden**>"
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
    ) -> Profile:
        """Create a new profile and add it to config.

        Args:
            name: Unique profile name.
            app_type: Type of trainer application.
            garmin_username: Garmin Connect email.
            garmin_password: Garmin Connect password.
            fitfiles_path: Path to FIT files directory.

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

        # Create new profile
        profile = Profile(
            name=name,
            app_type=app_type,
            garmin_username=garmin_username,
            garmin_password=garmin_password,
            fitfiles_path=fitfiles_path,
        )

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
    ) -> Profile:
        """Update an existing profile.

        Args:
            name: Name of profile to update.
            app_type: New app type (optional).
            garmin_username: New Garmin username (optional).
            garmin_password: New Garmin password (optional).
            fitfiles_path: New FIT files path (optional).
            new_name: New profile name (optional).

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


# Global configuration manager instance
config_manager = ConfigManager()

# Global profile manager instance
profile_manager = ProfileManager(config_manager)
