# ruff: noqa: E402
"""Main application module for Fit File Faker.

This module provides the command-line interface and core application logic
for modifying FIT files and uploading them to Garmin Connect. It simulates
a Garmin Edge 830 device to enable Training Effect calculations for activities
from non-Garmin sources.

The module includes:

- CLI argument parsing and validation
- FIT file upload to Garmin Connect with OAuth authentication
- Batch processing of multiple FIT files
- Directory monitoring for automatic processing of new files
- Rich console output with colored logs

Typical usage:

    $ fit-file-faker -s                    # Initial setup
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

from .config import config_manager, dirs
from .fit_editor import fit_editor
from .utils import apply_fit_tool_patch

# Apply monkey patch to handle malformed FIT files (e.g., COROS)
apply_fit_tool_patch()

c = Console()
FILES_UPLOADED_NAME = Path(".uploaded_files.json")


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

    Examples:
        >>> # Typically used via monitor() function, but can be instantiated directly:
        >>> from watchdog.observers.polling import PollingObserver as Observer
        >>> handler = NewFileEventHandler(dryrun=False)
        >>> observer = Observer()
        >>> observer.schedule(handler, "/path/to/fitfiles", recursive=True)
        >>> observer.start()
    """

    def __init__(self, dryrun: bool = False):
        """Initialize the file event handler.

        Args:
            dryrun: If `True`, log file detections but don't process them.
                Defaults to `False`.
        """
        _logger.debug(f"Creating NewFileEventHandler with {dryrun=}")
        super().__init__(
            patterns=["*.fit", "MyNewActivity-*.fit"],
            ignore_directories=True,
            case_sensitive=False,
        )
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
            upload_all(Path(p).parent.absolute())
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
                modified_file = Path(p).absolute()

                # Edit the file and upload it
                with NamedTemporaryFile(delete=True, delete_on_close=False) as fp:
                    output = fit_editor.edit_fit(modified_file, output=Path(fp.name))
                    if output:
                        _logger.info(
                            f"Uploading modified file ({output}) to Garmin Connect"
                        )
                        upload(output, original_path=modified_file, dryrun=self.dryrun)
            else:
                _logger.warning(
                    "Found modified file, but not processing because dryrun was requested"
                )


def upload(fn: Path, original_path: Optional[Path] = None, dryrun: bool = False):
    """Upload a FIT file to Garmin Connect.

    Authenticates to Garmin Connect using stored credentials or interactive prompts,
    then uploads the specified FIT file. Credentials are cached in a platform-specific
    cache directory for future use.

    Args:
        fn: Path to the (modified) FIT file to upload.
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
        >>> upload(Path("activity_modified.fit"))
        >>>
        >>> # Dry run (authenticate but don't upload)
        >>> upload(Path("activity_modified.fit"), dryrun=True)

    Note:
        Garmin Connect credentials are read from the configuration file. If not
        found there, the user is prompted interactively. Credentials are cached
        in ~/.cache/FitFileFaker/.garth (location varies by platform).
    """
    # get credentials and login if needed
    import garth
    from garth.exc import GarthException, GarthHTTPError

    garth_dir = dirs.user_cache_path / ".garth"
    garth_dir.mkdir(exist_ok=True)
    _logger.debug(f'Using "{garth_dir}" for garth credentials')

    try:
        garth.resume(str(garth_dir.absolute()))
        garth.client.username
        _logger.debug(f'Using stored Garmin credentials from "{garth_dir}" directory')
    except (GarthException, FileNotFoundError):
        # Session is expired. You'll need to log in again
        _logger.info("Authenticating to Garmin Connect")
        email = config_manager.config.garmin_username
        password = config_manager.config.garmin_password
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


def upload_all(dir: Path, preinitialize: bool = False, dryrun: bool = False):
    """Batch process and upload all new FIT files in a directory.

    Scans the directory for FIT files that haven't been processed yet, edits them
    to appear as Garmin Edge 830 files, and uploads them to Garmin Connect. Maintains
    a `.uploaded_files.json` file to track which files have been processed.

    Args:
        dir: Path to the directory containing FIT files to process.
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
        >>> upload_all(Path("/home/user/TPVirtual/abc123/FITFiles"))
        >>>
        >>> # Initialize tracking without processing
        >>> upload_all(Path("/path/to/fitfiles"), preinitialize=True)
        >>>
        >>> # Dry run (no uploads or tracking updates)
        >>> upload_all(Path("/path/to/fitfiles"), dryrun=True)
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
                output = fit_editor.edit_fit(dir.joinpath(f), output=Path(fp.name))
                if output:
                    _logger.info("Uploading modified file to Garmin Connect")
                    upload(output, original_path=Path(f), dryrun=dryrun)
                    _logger.debug(f'Adding "{f}" to "uploaded_files"')
        else:
            _logger.info(
                "Preinitialize was requested, so just marking as uploaded (not actually processing)"
            )
        uploaded_files.append(f)

    if not dryrun:
        with files_uploaded.open("w") as f:
            json.dump(uploaded_files, f, indent=2)


def monitor(watch_dir: Path, dryrun: bool = False):
    """Monitor a directory for new FIT files and automatically process them.

    Uses watchdog's PollingObserver to watch for new .fit files in the specified
    directory. When a new file is detected, waits 5 seconds to ensure it's fully
    written, then processes and uploads it via [`upload_all()`][fit_file_faker.app.upload_all].

    The monitor runs until interrupted by Ctrl-C (`KeyboardInterrupt`).

    Args:
        watch_dir: Path to the directory to monitor.
        dryrun: If `True`, detects new files but doesn't process them.
            Defaults to `False`.

    Examples:
        >>> from pathlib import Path
        >>>
        >>> # Monitor a directory
        >>> monitor(Path("/home/user/TPVirtual/abc123/FITFiles"))
        Monitoring directory: "/home/user/TPVirtual/abc123/FITFiles"
        # Press Ctrl-C to stop

    Note:
        Uses `PollingObserver` for cross-platform compatibility. This may be
        less efficient than platform-specific observers but works consistently
        across macOS, Windows, and Linux.
    """
    event_handler = NewFileEventHandler(dryrun=dryrun)
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


def run():
    """Main entry point for the fit-file-faker command-line application.

    Parses command-line arguments, validates configuration, and executes the
    appropriate operation (edit, upload, batch upload, or monitor). This function
    is registered as the console script entry point in pyproject.toml.

    Command-line options:

        -s, --initial-setup: Interactive configuration setup
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
        $ fit-file-faker -s
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
        "Currently, only FIT files produced by TrainingPeaks Virtual (https://www.trainingpeaks.com/virtual/) "
        "and Zwift (https://www.zwift.com/) are supported, but it's possible others may work."
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
        "-s",
        "--initial-setup",
        help="Use this option to interactively initialize the configuration file (.config.json)",
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

    # if initial_setup, just do config file building
    if args.initial_setup:
        config_manager.build_config_file(
            overwrite_existing_vals=True, rewrite_config=True
        )
        _logger.info(
            f'Config file has been written to "{config_manager.get_config_file_path()}", now run one of the other options to '
            "start editing/uploading files!"
        )
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

    # check configuration and prompt for values if needed
    excluded_keys = ["fitfiles_path"] if args.input_path else []
    if not config_manager.is_valid(excluded_keys=excluded_keys):
        _logger.warning(
            "Config file was not valid, please fill out the following values."
        )
        config_manager.build_config_file(
            overwrite_existing_vals=False,
            rewrite_config=True,
            excluded_keys=excluded_keys,
        )

    if args.input_path:
        p = Path(args.input_path).absolute()
        _logger.info(f'Using path "{p}" from command line input')
    else:
        if config_manager.config.fitfiles_path is None:
            raise EnvironmentError
        p = Path(config_manager.config.fitfiles_path).absolute()
        _logger.info(f'Using path "{p}" from configuration file')

    if not p.exists():
        _logger.error(
            f'Configured/selected path "{p}" does not exist, please check your configuration.'
        )
        sys.exit(1)
    if p.is_file():
        # if p is a single file, do edit and upload
        _logger.debug(f'"{p}" is a single file')
        output_path = fit_editor.edit_fit(p, dryrun=args.dryrun)
        if (args.upload or args.upload_all) and output_path:
            upload(output_path, original_path=p, dryrun=args.dryrun)
    else:
        _logger.debug(f'"{p}" is a directory')
        # if p is directory, do other stuff
        if args.upload_all or args.preinitialize:
            upload_all(p, args.preinitialize, args.dryrun)
        elif args.monitor:
            monitor(p, args.dryrun)
        else:
            files_to_edit = list(p.glob("*.fit", case_sensitive=False))
            _logger.info(f"Found {len(files_to_edit)} FIT files to edit")
            for f in files_to_edit:
                fit_editor.edit_fit(f, dryrun=args.dryrun)


if __name__ == "__main__":  # pragma: no cover
    run()
