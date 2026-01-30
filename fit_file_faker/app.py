# ruff: noqa: E402
"""Main application module for Fit File Faker.

This module provides the command-line interface and core application logic
for modifying FIT files and uploading them to Garmin Connect. It simulates
a Garmin Edge 830 device (by default) to enable Training Effect calculations
for activities from non-Garmin sources.

The module includes:

- CLI argument parsing and validation
- FIT file upload to Garmin Connect with OAuth authentication
- Batch processing of multiple FIT files
- Directory monitoring for automatic processing of new files
- Rich console output with colored logs

Typical usage:

    $ fit-file-faker --config-menu         # Initial setup
    $ fit-file-faker activity.fit          # Edit single file
    $ fit-file-faker -u activity.fit       # Edit and upload
    $ fit-file-faker -ua                   # Upload all new files
    $ fit-file-faker -m                    # Monitor directory

"""

import argparse
import json
import logging
import sys
import time
from importlib.metadata import version
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional, cast

import questionary
import semver
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install
from watchdog.events import (
    PatternMatchingEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
)
from watchdog.observers.polling import PollingObserver as Observer

_logger = logging.getLogger("garmin")
install()

# fit_tool configures logging for itself, so need to do this before importing it
logging.basicConfig(
    level=logging.NOTSET,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(markup=True)],
)
_logger.setLevel(logging.INFO)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("oauth1_auth").setLevel(logging.WARNING)

from . import __version_date__
from .config import config_manager, dirs, profile_manager, Profile
from .fit_editor import fit_editor
from .utils import apply_fit_tool_patch

# Apply monkey patch to handle malformed FIT files (e.g., COROS)
apply_fit_tool_patch()

c = Console()
FILES_UPLOADED_NAME = Path(".uploaded_files.json")


def get_garth_dir(profile_name: str) -> Path:
    """Get profile-specific garth directory for credential isolation.

    Each profile gets its own garth directory to prevent credential conflicts
    when managing multiple Garmin accounts. The profile name is sanitized to
    ensure filesystem compatibility.

    Args:
        profile_name: The name of the profile.

    Returns:
        Path to the profile-specific garth directory.

    Examples:
        >>> get_garth_dir("tpv")
        PosixPath('/Users/josh/Library/Caches/FitFileFaker/.garth_tpv')
        >>>
        >>> get_garth_dir("work-account")
        PosixPath('/Users/josh/Library/Caches/FitFileFaker/.garth_work-account')

    Note:
        The directory is automatically created if it doesn't exist.
        Profile names with special characters are sanitized (replaced with '_').
    """
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in profile_name)
    garth_dir = dirs.user_cache_path / f".garth_{safe_name}"
    garth_dir.mkdir(exist_ok=True, parents=True)
    return garth_dir


class NewFileEventHandler(PatternMatchingEventHandler):
    """Event handler for monitoring directory changes and processing new FIT files.

    Extends watchdog's PatternMatchingEventHandler to automatically process
    and upload new FIT files as they're created in the monitored directory.
    Also handles file modification events for MyWhoosh files that follow the
    pattern "MyNewActivity-*.fit", as MyWhoosh overwrites the same file on
    completion rather than creating a new file.

    Includes a 5-second delay to ensure the file is fully written before processing.

    Attributes:
        dryrun: If `True`, detects files but doesn't process them. Useful for testing.
        profile: The profile to use for uploading files.

    Examples:
        >>> # Typically used via monitor() function, but can be instantiated directly:
        >>> from watchdog.observers.polling import PollingObserver as Observer
        >>> handler = NewFileEventHandler(profile=profile, dryrun=False)
        >>> observer = Observer()
        >>> observer.schedule(handler, "/path/to/fitfiles", recursive=True)
        >>> observer.start()
    """

    def __init__(self, profile: Profile, dryrun: bool = False):
        """Initialize the file event handler.

        Args:
            profile: The profile to use for uploading files.
            dryrun: If `True`, log file detections but don't process them.
                Defaults to `False`.
        """
        _logger.debug(f"Creating NewFileEventHandler with {dryrun=}")
        super().__init__(
            patterns=["*.fit", "MyNewActivity-*.fit"],
            ignore_directories=True,
            case_sensitive=False,
        )
        self.profile = profile
        self.dryrun = dryrun

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file creation events.

        Called by watchdog when a new `.fit` file is created in the monitored
        directory. Waits 5 seconds to ensure the file is fully written, then
        processes all new files in the directory via
        [`upload_all()`][fit_file_faker.app.upload_all].

        Args:
            event: The file system event containing the path to the new file.

        Note:
            The 5-second delay is necessary because TrainingPeaks Virtual may
            still be writing to the file when the creation event fires. Without
            this delay, the file might be incomplete or corrupt.
        """
        _logger.info(
            f'New file detected - "{event.src_path}"; sleeping for 5 seconds '
            "to ensure TPV finishes writing file"
        )
        if not self.dryrun:
            # Wait for a short time to make sure TPV has finished writing to the file
            time.sleep(5)
            # Run the upload all function
            p = event.src_path
            if isinstance(p, bytes):
                p = p.decode()  # pragma: no cover
            p = cast(str, p)
            upload_all(Path(p).parent.absolute(), profile=self.profile)
        else:
            _logger.warning(
                "Found new file, but not processing because dryrun was requested"
            )

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events.

        Called by watchdog when a `.fit` file is modified in the monitored
        directory. This is specifically useful for MyWhoosh files that follow
        the pattern "MyNewActivity-*.fit", as MyWhoosh overwrites the same file
        on completion rather than creating a new file.

        Args:
            event: The file system event containing the path to the modified file.

        Note:
            Waits 5 seconds to ensure the file is fully written, similar to
            the creation event handler. This handles the case where MyWhoosh
            overwrites existing files. Only processes the specific modified file
            rather than all files in the directory.
        """
        # Only process MyWhoosh files that match the pattern
        if "MyNewActivity-" in event.src_path:
            _logger.info(
                f'File modified detected - "{event.src_path}"; sleeping for 5 seconds '
                "to ensure MyWhoosh finishes writing file"
            )
            if not self.dryrun:
                # Wait for a short time to make sure MyWhoosh has finished writing to the file
                time.sleep(5)
                # Process only the modified file
                p = event.src_path
                if isinstance(p, bytes):
                    p = p.decode()  # pragma: no cover
                p = cast(str, p)
                source_file = Path(p).absolute()

                # Edit the file and upload it
                with NamedTemporaryFile(delete=True, delete_on_close=False) as fp:
                    fit_editor.set_profile(self.profile)
                    output = fit_editor.edit_fit(source_file, output=Path(fp.name))
                    if output:
                        _logger.info(
                            f"Uploading modified file ({output}) to Garmin Connect"
                        )
                        upload(
                            output,
                            profile=self.profile,
                            original_path=source_file,
                            dryrun=self.dryrun,
                        )

                        # Track uploaded file to prevent re-processing
                        uploaded_list = source_file.parent / FILES_UPLOADED_NAME
                        uploaded_files = []
                        if uploaded_list.exists():
                            with uploaded_list.open("r") as f:
                                uploaded_files = json.load(f)

                        filename = source_file.name
                        if filename not in uploaded_files:
                            uploaded_files.append(filename)
                            with uploaded_list.open("w") as f:
                                json.dump(uploaded_files, f, indent=2)
                            _logger.debug(f'Added "{filename}" to uploaded files list')
            else:
                _logger.warning(
                    "Found modified file, but not processing because dryrun was requested"
                )


def upload(
    fn: Path,
    profile: Profile,
    original_path: Optional[Path] = None,
    dryrun: bool = False,
):
    """Upload a FIT file to Garmin Connect.

    Authenticates to Garmin Connect using credentials from the specified profile,
    then uploads the specified FIT file. Credentials are cached in a profile-specific
    cache directory for future use.

    Args:
        fn: Path to the (modified) FIT file to upload.
        profile: The profile to use for authentication and upload.
        original_path: Optional path to the original file for logging purposes.
            Defaults to `None`.
        dryrun: If `True`, authenticates but doesn't actually upload the file.
            Defaults to `False`.

    Raises:
        GarthHTTPError: If upload fails with an HTTP error. 409 (conflict/duplicate)
            errors are caught and logged as warnings, but other HTTP errors are re-raised.

    Examples:
        >>> from pathlib import Path
        >>> # Upload a modified file
        >>> upload(Path("activity_modified.fit"), profile=my_profile)
        >>>
        >>> # Dry run (authenticate but don't upload)
        >>> upload(Path("activity_modified.fit"), profile=my_profile, dryrun=True)

    Note:
        Garmin Connect credentials are read from the profile. Credentials are cached
        in profile-specific directories like ~/.cache/FitFileFaker/.garth_<profile_name>
        (location varies by platform).
    """
    # get credentials and login if needed
    import garth
    from garth.exc import GarthException, GarthHTTPError

    garth_dir = get_garth_dir(profile.name)
    _logger.debug(f'Using "{garth_dir}" for garth credentials')

    try:
        garth.resume(str(garth_dir.absolute()))
        garth.client.username
        _logger.debug(f'Using stored Garmin credentials from "{garth_dir}" directory')
    except (GarthException, FileNotFoundError):
        # Session is expired. You'll need to log in again
        _logger.info("Authenticating to Garmin Connect")
        email = profile.garmin_username
        password = profile.garmin_password
        if not email:
            email = questionary.text(
                'No "garmin_username" variable set; Enter email address: '
            ).ask()
        _logger.debug(f'Using username "{email}"')
        if not password:
            password = questionary.password(
                'No "garmin_password" variable set; Enter password: '
            ).ask()
            _logger.debug("Using password from user input")
        else:
            _logger.debug('Using password stored in "garmin_password"')
        garth.login(email, password)
        garth.save(str(garth_dir.absolute()))

    with fn.open("rb") as f:
        try:
            if not dryrun:
                _logger.info(f'Uploading "{fn}" using garth')
                garth.client.upload(f)
                _logger.info(
                    f':white_check_mark: Successfully uploaded "{str(original_path)}"'
                )
            else:
                _logger.info(f'Skipping upload of "{fn}" because dryrun was requested')
        except GarthHTTPError as e:
            if e.error.response.status_code == 409:
                _logger.warning(
                    f':x: Received HTTP conflict (activity already exists) for "{str(original_path)}"'
                )
            else:
                raise e


def upload_all(
    dir: Path, profile: Profile, preinitialize: bool = False, dryrun: bool = False
):
    """Batch process and upload all new FIT files in a directory.

    Scans the directory for FIT files that haven't been processed yet, edits them
    to appear as Garmin Edge 830 files, and uploads them to Garmin Connect. Maintains
    a `.uploaded_files.json` file to track which files have been processed.

    Args:
        dir: Path to the directory containing FIT files to process.
        profile: The profile to use for authentication and upload.
        preinitialize: If `True`, marks all existing files as already uploaded
            without actually processing them. Useful for initializing the tracking
            file. Defaults to `False`.
        dryrun: If `True`, processes files but doesn't upload or update the tracking
            file. Defaults to `False`.

    Note:
        Files ending in "_modified.fit" are automatically excluded to avoid
        re-processing previously modified files. Temporary files are used for
        uploads and are automatically deleted afterwards.

    Examples:
        >>> from pathlib import Path
        >>>
        >>> # Process and upload all new files
        >>> upload_all(Path("/home/user/TPVirtual/abc123/FITFiles"), profile=my_profile)
        >>>
        >>> # Initialize tracking without processing
        >>> upload_all(Path("/path/to/fitfiles"), profile=my_profile, preinitialize=True)
        >>>
        >>> # Dry run (no uploads or tracking updates)
        >>> upload_all(Path("/path/to/fitfiles"), profile=my_profile, dryrun=True)
    """
    files_uploaded = dir.joinpath(FILES_UPLOADED_NAME)
    if files_uploaded.exists():
        # load uploaded file list from disk
        with files_uploaded.open("r") as f:
            uploaded_files = json.load(f)
    else:
        uploaded_files = []
        with files_uploaded.open("w") as f:
            # write blank file
            json.dump(uploaded_files, f, indent=2)
    _logger.debug(f"Found the following already uploaded files: {uploaded_files}")

    # glob all .fit files in the current directory
    files = [str(i) for i in dir.glob("*.fit", case_sensitive=False)]
    # strip any leading/trailing slashes from filenames
    files = [i.replace(str(dir), "").strip("/").strip("\\") for i in files]
    # remove files matching what we may have already processed
    files = [i for i in files if not i.endswith("_modified.fit")]
    # remove files found in the "already uploaded" list
    files = [i for i in files if i not in uploaded_files]

    _logger.info(f"Found {len(files)} files to edit/upload")
    _logger.debug(f"Files to upload: {files}")

    if not files:
        return

    for f in files:
        _logger.info(f'Processing "{f}"')  # type: ignore

        if not preinitialize:
            with NamedTemporaryFile(delete=True, delete_on_close=False) as fp:
                fit_editor.set_profile(profile)
                output = fit_editor.edit_fit(dir.joinpath(f), output=Path(fp.name))
                if output:
                    _logger.info("Uploading modified file to Garmin Connect")
                    upload(
                        output, profile=profile, original_path=Path(f), dryrun=dryrun
                    )
                    _logger.debug(f'Adding "{f}" to "uploaded_files"')
        else:
            _logger.info(
                "Preinitialize was requested, so just marking as uploaded (not actually processing)"
            )
        uploaded_files.append(f)

    if not dryrun:
        with files_uploaded.open("w") as f:
            json.dump(uploaded_files, f, indent=2)


def monitor(watch_dir: Path, profile: Profile, dryrun: bool = False):
    """Monitor a directory for new FIT files and automatically process them.

    Uses watchdog's PollingObserver to watch for new .fit files in the specified
    directory. When a new file is detected, waits 5 seconds to ensure it's fully
    written, then processes and uploads it via [`upload_all()`][fit_file_faker.app.upload_all].

    The monitor runs until interrupted by Ctrl-C (`KeyboardInterrupt`).

    Args:
        watch_dir: Path to the directory to monitor.
        profile: The profile to use for authentication and upload.
        dryrun: If `True`, detects new files but doesn't process them.
            Defaults to `False`.

    Examples:
        >>> from pathlib import Path
        >>>
        >>> # Monitor a directory
        >>> monitor(Path("/home/user/TPVirtual/abc123/FITFiles"), profile=my_profile)
        Monitoring directory: "/home/user/TPVirtual/abc123/FITFiles"
        # Press Ctrl-C to stop

    Note:
        Uses `PollingObserver` for cross-platform compatibility. This may be
        less efficient than platform-specific observers but works consistently
        across macOS, Windows, and Linux.
    """
    event_handler = NewFileEventHandler(profile=profile, dryrun=dryrun)
    observer = Observer()
    observer.schedule(event_handler, str(watch_dir.absolute()), recursive=True)
    observer.start()
    if dryrun:  # pragma: no cover
        _logger.warning("Dryrun was requested, so will not actually take any actions")
    _logger.info(f'Monitoring directory: "{watch_dir.absolute()}"')
    try:
        while observer.is_alive():
            observer.join(1)
    except KeyboardInterrupt:
        _logger.info("Received keyboard interrupt, shutting down monitor")
    finally:
        observer.stop()
        observer.join()


def select_profile(profile_name: Optional[str] = None) -> Profile:
    """Select a profile to use for the current operation.

    Uses the following priority:
    1. If profile_name is provided, use that profile (error if not found)
    2. Use the default profile if one is set
    3. If only one profile exists, use it
    4. If multiple profiles exist, prompt the user to select one
    5. If no profiles exist, raise an error

    Args:
        profile_name: Optional name of the profile to use. If not provided,
            uses the default profile or prompts the user.

    Returns:
        The selected Profile object.

    Raises:
        ValueError: If the specified profile is not found or no profiles are configured.

    Examples:
        >>> # Use a specific profile
        >>> profile = select_profile("tpv")
        >>>
        >>> # Use default profile (or prompt if no default)
        >>> profile = select_profile()
    """
    if profile_name:
        profile = profile_manager.get_profile(profile_name)
        if not profile:
            raise ValueError(
                f'Profile "{profile_name}" not found. '
                f"Run with --list-profiles to see available profiles."
            )
        _logger.info(f'Using profile: "{profile.name}"')
        return profile

    # Try to get default profile
    default = config_manager.config.get_default_profile()
    if default:
        _logger.info(f'Using default profile: "{default.name}"')
        return default

    # Check if any profiles exist
    if not config_manager.config.profiles:
        raise ValueError(
            "No profiles configured. Run with --config-menu to create a profile."
        )

    # If only one profile, use it
    if len(config_manager.config.profiles) == 1:
        profile = config_manager.config.profiles[0]
        _logger.info(f'Using only available profile: "{profile.name}"')
        return profile

    # Multiple profiles, no default - prompt user
    profile_choices = [p.name for p in config_manager.config.profiles]
    selected_name = questionary.select(
        "Multiple profiles found. Select profile to use:", choices=profile_choices
    ).ask()

    if not selected_name:
        raise ValueError("No profile selected")

    profile = profile_manager.get_profile(selected_name)
    if not profile:  # pragma: no cover
        raise ValueError(f'Profile "{selected_name}" not found')

    _logger.info(f'Using selected profile: "{profile.name}"')
    return profile


def run():
    """Main entry point for the fit-file-faker command-line application.

    Parses command-line arguments, validates configuration, and executes the
    appropriate operation (edit, upload, batch upload, or monitor). This function
    is registered as the console script entry point in pyproject.toml.

    Command-line options:

        --profile: Specify which profile to use
        --list-profiles: List all available profiles
        --config-menu: Launch the interactive profile management menu
        --show-dirs: Show directories used for configuration and cache
        -u, --upload: Upload file after editing
        -ua, --upload-all: Batch upload all new files
        -p, --preinitialize: Mark all existing files as already uploaded
        -m, --monitor: Monitor directory for new files
        -d, --dryrun: Perform dry run (no file writes or uploads)
        -v, --verbose: Enable verbose debug logging

    Raises:
        SystemExit: If configuration is invalid, required arguments are missing,
            or conflicting arguments are provided.

    Examples:

        # run() is called automatically when running the installed command:
        $ fit-file-faker --config-menu
        $ fit-file-faker --show-dirs
        $ fit-file-faker -u activity.fit
        $ fit-file-faker -ua
        $ fit-file-faker -m

    Note:
        Requires Python 3.12 or higher. Exits with error if Python version
        requirement is not met.
    """
    v = sys.version_info
    v_str = f"{v.major}.{v.minor}.{v.micro}"
    min_ver = "3.12.0"
    ver = semver.Version.parse(v_str)
    if not ver >= semver.Version.parse(min_ver):
        msg = f'This program requires Python "{min_ver}" or greater (current version is "{v_str}"). Please upgrade your python version.'
        raise OSError(msg)

    parser = argparse.ArgumentParser(
        description="Tool to add Garmin device information to FIT files and upload them to Garmin Connect. "
        "Currently, only FIT files produced by TrainingPeaks Virtual (https://www.trainingpeaks.com/virtual/), "
        "Zwift (https://www.zwift.com/), and MyWhoosh (https://mywhoosh.com/) are supported, but it's "
        "possible others may work."
    )
    parser.add_argument(
        "input_path",
        nargs="?",
        default=[],
        help="the FIT file or directory to process. This argument can be omitted if the 'fitfiles_path' "
        "config value is set (that directory will be used instead). By default, files will just be edited. "
        'Specify the "-u" flag to also upload them to Garmin Connect.',
    )
    parser.add_argument(
        "--profile",
        help="specify which profile to use (if not specified, uses default profile)",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--list-profiles",
        help="list all available profiles and exit",
        action="store_true",
    )
    parser.add_argument(
        "--config-menu",
        help="launch the interactive profile management menu",
        action="store_true",
    )
    parser.add_argument(
        "--show-dirs",
        help="show the directories used by Fit File Faker for configuration and cache",
        action="store_true",
    )
    parser.add_argument(
        "-u",
        "--upload",
        help="upload FIT file (after editing) to Garmin Connect",
        action="store_true",
    )
    parser.add_argument(
        "-ua",
        "--upload-all",
        action="store_true",
        help='upload all FIT files in directory (if they are not in "already processed" list)',
    )
    parser.add_argument(
        "-p",
        "--preinitialize",
        help="preinitialize the list of processed FIT files (mark all existing files in directory as already uploaded)",
        action="store_true",
    )
    parser.add_argument(
        "-m",
        "--monitor",
        help="monitor a directory and upload all newly created FIT files as they are found",
        action="store_true",
    )
    parser.add_argument(
        "-d",
        "--dryrun",
        help="perform a dry run, meaning any files processed will not be saved nor uploaded",
        action="store_true",
    )
    parser.add_argument(
        "-v", "--verbose", help="increase verbosity of log output", action="store_true"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version('fit-file-faker')} (released {__version_date__})",
        help="show program version and exit",
    )
    args = parser.parse_args()

    # setup logging before anything else
    if args.verbose:
        _logger.setLevel(logging.DEBUG)
        for logger in [
            "urllib3.connectionpool",
            "oauthlib.oauth1.rfc5849",
            "requests_oauthlib.oauth1_auth",
            "asyncio",
            "watchdog.observers.inotify_buffer",
        ]:
            logging.getLogger(logger).setLevel(logging.INFO)
        _logger.debug(f'Using "{config_manager.get_config_file_path()}" as config file')
    else:
        _logger.setLevel(logging.INFO)
        for logger in [
            "urllib3.connectionpool",
            "oauthlib.oauth1.rfc5849",
            "requests_oauthlib.oauth1_auth",
            "asyncio",
            "watchdog.observers.inotify_buffer",
        ]:
            logging.getLogger(logger).setLevel(logging.WARNING)

    # Handle --list-profiles
    if args.list_profiles:
        if not config_manager.config.profiles:
            _logger.info(
                "No profiles configured. Run with --config-menu to create one."
            )
        else:
            profile_manager.display_profiles_table()
        sys.exit(0)

    # Handle --config-menu
    if args.config_menu:
        profile_manager.interactive_menu()
        sys.exit(0)

    # Handle --show-dirs
    if args.show_dirs:
        from fit_file_faker.config import dirs as config_dirs

        console = Console()
        console.print("\n[bold cyan]Fit File Faker - Directories[/bold cyan]\n")

        # Show executable path
        console.print(f'[green]Executable:[/green] [yellow]"{sys.executable}"[/yellow]')
        console.print(
            f'  [dim]fit-file-faker command:[/dim] [yellow]"{sys.argv[0]}"[/yellow]'
        )

        # Show config directory
        console.print(
            f'\n[green]Config directory:[/green] [yellow]"{config_dirs.user_config_path}"[/yellow]'
        )
        console.print(
            f'  [dim]Configuration file:[/dim] [yellow]"{config_manager.get_config_file_path()}"[/yellow]'
        )

        # Show cache directory
        console.print(
            f'\n[green]Cache directory:[/green] [yellow]"{config_dirs.user_cache_path}"[/yellow]'
        )

        # Find and list actual .garth directories
        garth_dirs = sorted(config_dirs.user_cache_path.glob(".garth_*"))
        if garth_dirs:
            console.print("  [dim]Garmin credential directories:[/dim]")
            for garth_dir in garth_dirs:
                console.print(f'    [yellow]"{garth_dir}"[/yellow]')
        else:
            console.print(
                "  [dim]No Garmin credential directories found (will be created on first use)[/dim]"
            )

        console.print()
        sys.exit(0)

    if not args.input_path and not (
        args.upload_all or args.monitor or args.preinitialize
    ):
        _logger.error(
            '***************************\nSpecify either "--upload-all", "--monitor", "--preinitialize", or one input file/directory to use\n***************************\n'
        )
        parser.print_help()
        sys.exit(1)
    if args.monitor and args.upload_all:
        _logger.error(
            '***************************\nCannot use "--upload-all" and "--monitor" together\n***************************\n'
        )
        parser.print_help()
        sys.exit(1)

    # Select profile to use
    try:
        profile = select_profile(args.profile)
    except ValueError as e:
        _logger.error(str(e))
        sys.exit(1)

    # Determine path to use (from input_path or profile's fitfiles_path)
    if args.input_path:
        p = Path(args.input_path).absolute()
        _logger.info(f'Using path "{p}" from command line input')
    else:
        if profile.fitfiles_path is None:
            _logger.error(
                f'Profile "{profile.name}" does not have a fitfiles_path configured. '
                f"Please update the profile with --config-menu or provide a path as an argument."
            )
            sys.exit(1)
        p = Path(profile.fitfiles_path).absolute()
        _logger.info(f'Using path "{p}" from profile "{profile.name}" configuration')

    if not p.exists():
        _logger.error(
            f'Configured/selected path "{p}" does not exist, please check your configuration.'
        )
        sys.exit(1)
    if p.is_file():
        # if p is a single file, do edit and upload
        _logger.debug(f'"{p}" is a single file')
        fit_editor.set_profile(profile)
        output_path = fit_editor.edit_fit(p, dryrun=args.dryrun)
        if (args.upload or args.upload_all) and output_path:
            upload(output_path, profile=profile, original_path=p, dryrun=args.dryrun)
    else:
        _logger.debug(f'"{p}" is a directory')
        # if p is directory, do other stuff
        if args.upload_all or args.preinitialize:
            upload_all(
                p, profile=profile, preinitialize=args.preinitialize, dryrun=args.dryrun
            )
        elif args.monitor:
            monitor(p, profile=profile, dryrun=args.dryrun)
        else:
            files_to_edit = list(p.glob("*.fit", case_sensitive=False))
            _logger.info(f"Found {len(files_to_edit)} FIT files to edit")
            fit_editor.set_profile(profile)
            for f in files_to_edit:
                fit_editor.edit_fit(f, dryrun=args.dryrun)


if __name__ == "__main__":  # pragma: no cover
    run()
