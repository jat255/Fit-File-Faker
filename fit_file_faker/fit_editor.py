"""FIT file editing functionality for Fit File Faker.

This module handles the core FIT file manipulation logic, converting files
from virtual cycling platforms to appear as Garmin Edge 830 (by default)
recordings.

The primary class, FitEditor, provides methods to read FIT files, modify
device metadata (manufacturer and product IDs), and save the modified files
while preserving all activity data (records, laps, sessions).

Typical usage example:
    >>> from fit_file_faker.fit_editor import fit_editor
    >>> from pathlib import Path
    >>>
    >>> output_file = fit_editor.edit_fit(Path("activity.fit"))
    >>> print(f"Modified file saved to: {output_file}")
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fit_file_faker.vendor.fit_tool.definition_message import DefinitionMessage
from fit_file_faker.vendor.fit_tool.fit_file import FitFile
from fit_file_faker.vendor.fit_tool.fit_file_builder import FitFileBuilder
from fit_file_faker.vendor.fit_tool.profile.messages.activity_message import (
    ActivityMessage,
)
from fit_file_faker.vendor.fit_tool.profile.messages.device_info_message import (
    DeviceInfoMessage,
)
from fit_file_faker.vendor.fit_tool.profile.messages.file_creator_message import (
    FileCreatorMessage,
)
from fit_file_faker.vendor.fit_tool.profile.messages.file_id_message import (
    FileIdMessage,
)
from fit_file_faker.vendor.fit_tool.profile.profile_type import (
    GarminProduct,
    Manufacturer,
)

_logger = logging.getLogger("garmin")


class FitFileLogFilter(logging.Filter):
    """Logging filter to suppress noisy fit_tool warnings.

    This filter removes log messages from the fit_tool library that contain
    "\\n\\tactual: " which are verbose field validation warnings that clutter
    the output without providing useful information for end users.

    The filter is automatically applied to the fit_tool logger when a
    FitEditor instance is created.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Determine if the specified record should be logged.

        Args:
            record: The log record to filter.

        Returns:
            True if the record should be logged (doesn't contain the
            filtered pattern), False otherwise.
        """
        res = "\n\tactual: " not in record.getMessage()
        return res


class FitEditor:
    """Handles FIT file editing and manipulation.

    This class provides methods to read, modify, and save FIT files from
    various cycling platforms (TrainingPeaks Virtual, Zwift, COROS, etc.),
    converting them to appear as if they came from a Garmin Edge 830 device
    (or a custom device if configured via profile).

    The editor modifies only device metadata (manufacturer, product IDs) while
    preserving all activity data including records, laps, and sessions. This
    enables Garmin Connect's Training Effect calculations for activities from
    non-Garmin sources.

    Examples:
        >>> from fit_file_faker.fit_editor import fit_editor
        >>> from pathlib import Path
        >>>
        >>> # Edit a single file
        >>> output = fit_editor.edit_fit(Path("activity.fit"))
        >>>
        >>> # Dry run mode (no file written)
        >>> output = fit_editor.edit_fit(Path("activity.fit"), dryrun=True)
        >>>
        >>> # Custom output location
        >>> output = fit_editor.edit_fit(
        ...     Path("activity.fit"),
        ...     output=Path("modified_activity.fit")
        ... )
    """

    def __init__(self, profile=None):
        """Initialize the FIT editor.

        Args:
            profile: Optional Profile object for device simulation settings.
                If None, defaults to Garmin Edge 830.

        Applies a logging filter to suppress verbose fit_tool warnings.
        """
        # Apply the log filter to suppress noisy fit_tool warnings
        logging.getLogger("fit_tool").addFilter(FitFileLogFilter())
        self.profile = profile

    def set_profile(self, profile):
        """Set the profile to use for device simulation.

        Args:
            profile: Profile object containing manufacturer and device settings.

        Examples:
            >>> from fit_file_faker.config import profile_manager
            >>> profile = profile_manager.get_profile("tpv")
            >>> fit_editor.set_profile(profile)
        """
        self.profile = profile

    def print_message(
        self, prefix: str, message: FileIdMessage | DeviceInfoMessage
    ) -> None:
        """Print debug information about FIT file messages.

        Logs detailed information about FileIdMessage or DeviceInfoMessage
        records, including manufacturer names, product IDs, and garmin_product
        values. This is only logged at DEBUG level for troubleshooting.

        Args:
            prefix: Descriptive prefix for the log message (e.g., "FileIdMessage Record: 1").
            message: The FIT message to log information about.

        Note:
            This method is primarily used for debugging and troubleshooting
            FIT file modifications.
        """
        man = (
            Manufacturer(message.manufacturer).name
            if message.manufacturer in Manufacturer
            else "BLANK"
        )
        gar_prod = (
            GarminProduct(message.garmin_product)
            if message.garmin_product in GarminProduct
            else "BLANK"
        )
        _logger.debug(
            f"{prefix} - {message.to_row()=}\n"
            f"(Manufacturer: {man}, product: {message.product}, garmin_product: {gar_prod})"
        )

    def get_date_from_fit(self, fit_path: Path) -> Optional[datetime]:
        """Extract the creation date from a FIT file.

        Reads the FIT file and extracts the timestamp from the `FileIdMessage`,
        which indicates when the activity was recorded.

        Args:
            fit_path: `Path` to the FIT file to read.

        Returns:
            The activity creation datetime, or `None` if no `FileIdMessage` with
            a valid timestamp was found.

        Note:
            The timestamp in FIT files is stored in milliseconds since the
            FIT epoch, which is converted to a standard Python datetime object.
        """
        fit_file = FitFile.from_file(str(fit_path))
        res = None
        for i, record in enumerate(fit_file.records):
            message = record.message
            if message.global_id == FileIdMessage.ID:
                if isinstance(message, FileIdMessage):
                    res = datetime.fromtimestamp(message.time_created / 1000.0)  # type: ignore
                    break
        return res

    def rewrite_file_id_message(
        self,
        m: FileIdMessage,
        message_num: int,
    ) -> tuple[DefinitionMessage, FileIdMessage]:
        """Rewrite FileIdMessage to appear as if from Garmin Edge 830.

        Creates a new FileIdMessage with Garmin Edge 830 manufacturer and
        product IDs while preserving the original timestamp, type, and serial
        number. This is the primary transformation that enables Garmin Connect
        to recognize and process the activity.

        Args:
            m: The original FileIdMessage to rewrite.
            message_num: The record number for logging purposes.

        Returns:
            A tuple containing:

                - `DefinitionMessage`: Auto-generated definition for the new message.
                - `FileIdMessage`: The rewritten message with Garmin Edge 830 metadata.

        Note:
            The product_name field is intentionally not copied as Garmin devices
            typically don't set this field. Only files from supported manufacturers
            (`DEVELOPMENT`, `ZWIFT`, `WAHOO_FITNESS`, `PEAKSWARE`, `HAMMERHEAD`, `COROS`,
            `MYWHOOSH`) are modified; others are returned unchanged.
        """
        dt = datetime.fromtimestamp(m.time_created / 1000.0)  # type: ignore
        _logger.info(f'Activity timestamp is "{dt.isoformat()}"')
        self.print_message(f"FileIdMessage Record: {message_num}", m)

        new_m = FileIdMessage()
        new_m.time_created = (
            m.time_created if m.time_created else int(datetime.now().timestamp() * 1000)
        )
        if m.type:
            new_m.type = m.type
        # Use profile serial number if available, otherwise use default
        if self.profile and self.profile.serial_number:
            new_m.serial_number = self.profile.serial_number
        else:
            # Fallback to default for backwards compatibility
            new_m.serial_number = 1234567890

        _logger.debug(f"Using serial number: {new_m.serial_number}")
        if m.product_name:
            # garmin does not appear to define product_name, so don't copy it over
            pass

        if self._should_modify_manufacturer(m.manufacturer):
            # Use profile device settings if available, otherwise defaults
            if self.profile:
                new_m.manufacturer = self.profile.manufacturer
                new_m.product = self.profile.device
            else:
                new_m.manufacturer = Manufacturer.GARMIN.value
                new_m.product = GarminProduct.EDGE_830.value
            _logger.debug("    Modifying values")
            self.print_message(f"    New Record: {message_num}", new_m)

        return (DefinitionMessage.from_data_message(new_m), new_m)

    def _should_modify_manufacturer(self, manufacturer: int | None) -> bool:
        """Check if manufacturer should be modified to Garmin.

        Determines whether a FIT file's manufacturer should be changed to
        Garmin based on whether it's from a supported virtual cycling platform.

        Args:
            manufacturer: The manufacturer code from the FIT file, or `None`.

        Returns:
            True if the manufacturer is from a supported platform and should
            be modified, False otherwise.

        Note:
            Supported manufacturers include: `DEVELOPMENT` (TrainingPeaks Virtual),
            `ZWIFT`, `WAHOO_FITNESS`, `PEAKSWARE`, `HAMMERHEAD`, `COROS`, and
            `MYWHOOSH` (`331`).
        """
        if manufacturer is None:
            return False
        return manufacturer in [
            Manufacturer.DEVELOPMENT.value,
            Manufacturer.ZWIFT.value,
            Manufacturer.WAHOO_FITNESS.value,
            Manufacturer.PEAKSWARE.value,
            Manufacturer.HAMMERHEAD.value,
            Manufacturer.COROS.value,
            331,  # MYWHOOSH is unknown to fit_tools
        ]

    def _should_modify_device_info(self, manufacturer: int | None) -> bool:
        """Check if device info should be modified to Garmin Edge 830.

        Similar to _should_modify_manufacturer but also includes blank/unknown
        manufacturers (code 0) for `DeviceInfoMessage` records.

        Args:
            manufacturer: The manufacturer code from the `DeviceInfoMessage`, or `None`.

        Returns:
            True if the device info should be modified to Garmin Edge 830,
            False otherwise.

        Note:
            This includes all manufacturers from
            [`_should_modify_manufacturer()`][fit_file_faker.fit_editor.FitEditor._should_modify_manufacturer]
            plus manufacturer code 0 (blank/unknown).
        """
        if manufacturer is None:
            return False
        return manufacturer in [
            Manufacturer.DEVELOPMENT.value,
            0,  # Blank/unknown manufacturer
            Manufacturer.WAHOO_FITNESS.value,
            Manufacturer.ZWIFT.value,
            Manufacturer.PEAKSWARE.value,
            Manufacturer.HAMMERHEAD.value,
            Manufacturer.COROS.value,
            331,  # MYWHOOSH is unknown to fit_tools
        ]

    def strip_unknown_fields(self, fit_file: FitFile) -> None:
        """Force regeneration of definition messages for messages with unknown fields.

        This fixes a bug where `fit_tool` skips unknown fields (like Zwift's field 193)
        during reading but keeps them in the definition, causing a mismatch when writing.
        Without this fix, the file would be corrupted when written back out.

        The method sets `definition_message` to `None` for affected messages, forcing
        `FitFileBuilder` to regenerate clean definitions based only on fields that
        actually exist in the message.

        Args:
            fit_file: The parsed FIT file to process. Messages are modified in place.

        Note:
            This is called automatically by
            [`edit_fit()`][fit_file_faker.fit_editor.FitEditor.edit_fit] before
            processing any FIT file. It's essential for handling files from platforms
            like Zwift that use custom/unknown field IDs.
        """
        for record in fit_file.records:
            message = record.message
            if (
                not hasattr(message, "definition_message")
                or message.definition_message is None
            ):
                continue
            if not hasattr(message, "fields"):  # pragma: no cover
                continue

            # Get the set of field IDs that actually exist in the message
            existing_field_ids = {
                field.field_id for field in message.fields if field.is_valid()
            }

            # Check if definition has fields that don't exist in the message
            definition_field_ids = {
                fd.field_id for fd in message.definition_message.field_definitions
            }

            unknown_fields = definition_field_ids - existing_field_ids
            if unknown_fields:
                _logger.debug(
                    f"Clearing definition for {message.name} (global_id={message.global_id}) "
                    f"to force regeneration (had {len(unknown_fields)} unknown field(s))"
                )
                # Set to None to force FitFileBuilder to regenerate it
                message.definition_message = None

    def edit_fit(
        self,
        fit_input: Path | FitFile,
        output: Optional[Path] = None,
        dryrun: bool = False,
    ) -> Path | None:
        """Edit a FIT file to appear as if it came from a Garmin Edge 830.

        This is the primary method for converting FIT files from virtual cycling
        platforms to Garmin-compatible format. It modifies device metadata
        (manufacturer and product IDs) while preserving all activity data.

        The method performs the following transformations:

        1. Strips unknown field definitions to prevent corruption
        2. Rewrites `FileIdMessage` with Garmin Edge 830 metadata
        3. Adds a `FileCreatorMessage` with Edge 830 software/hardware versions
        4. Modifies `DeviceInfoMessage` records to match Edge 830
        5. Reorders `Activity` messages to end of file (COROS compatibility)

        Args:
            fit_input: Either a `Path` to the input FIT file OR a pre-parsed
                `FitFile` object. Using a `Path` is recommended for most cases.
            output: Optional output path. Defaults to {original}_modified.fit
                when `fit_input` is a `Path`. Required if `fit_input` is a `FitFile`
                object.
            dryrun: If `True`, performs all processing but doesn't write the
                output file. Useful for validation and testing.

        Returns:
            Path to the output file if successful, or `None` if processing
            failed (e.g., invalid FIT file).

        Raises:
            None: Errors are logged but not raised. Returns `None` on failure.

        Examples:
            >>> from pathlib import Path
            >>> from fit_file_faker.fit_editor import fit_editor
            >>>
            >>> # Basic usage
            >>> output = fit_editor.edit_fit(Path("activity.fit"))
            >>> print(f"Modified file: {output}")
            >>>
            >>> # Custom output path
            >>> output = fit_editor.edit_fit(
            ...     Path("activity.fit"),
            ...     output=Path("custom_output.fit")
            ... )
            >>>
            >>> # Dry run (no file written)
            >>> output = fit_editor.edit_fit(Path("activity.fit"), dryrun=True)

        Note:
            Only modifies device metadata. All activity data (records, laps,
            sessions, heart rate, power, etc.) is preserved exactly as-is.
        """
        if dryrun:
            _logger.warning('In "dryrun" mode; will not actually write new file.')

        # Handle both Path and FitFile inputs
        if isinstance(fit_input, Path):
            fit_path = fit_input
            _logger.info(f'Processing "{fit_path}"')

            try:
                fit_file = FitFile.from_file(str(fit_path))
            except Exception:
                _logger.error("File does not appear to be a FIT file, skipping...")
                return None
        elif isinstance(fit_input, FitFile):
            fit_file = fit_input
            fit_path = None  # No source path available
            _logger.info("Processing parsed FIT file")
        else:
            _logger.error(f"Invalid input type: {type(fit_input)}")
            return None

        # Strip unknown field definitions to prevent corruption when rewriting
        self.strip_unknown_fields(fit_file)

        if not output:
            if fit_path:
                output = fit_path.parent / f"{fit_path.stem}_modified.fit"
            else:
                _logger.error("Output path required when using parsed FIT file")
                return None

        builder = FitFileBuilder(auto_define=True)
        skipped_device_type_zero = False

        # Collect Activity messages to write at the end (fixes COROS file ordering)
        activity_messages = []

        # Loop through records, find the ones we need to change, and modify the values
        for i, record in enumerate(fit_file.records):
            message = record.message

            # Defer Activity messages until the end to ensure proper ordering
            if isinstance(message, ActivityMessage):
                activity_messages.append(message)
                continue

            # Change file id to indicate file was saved by Edge 830
            if message.global_id == FileIdMessage.ID:
                if isinstance(message, DefinitionMessage):
                    # If this is the definition message for the FileIdMessage, skip it
                    # since we're going to write a new one
                    continue
                if isinstance(message, FileIdMessage):
                    # Rewrite the FileIdMessage and its definition and add to builder
                    def_message, message = self.rewrite_file_id_message(message, i)
                    builder.add(def_message)
                    builder.add(message)
                    # Add FileCreatorMessage only if profile has software_version set
                    if self.profile and self.profile.software_version is not None:
                        creator_message = FileCreatorMessage()
                        creator_message.software_version = self.profile.software_version
                        builder.add(
                            DefinitionMessage.from_data_message(creator_message)
                        )
                        builder.add(creator_message)
                    continue

            if message.global_id == FileCreatorMessage.ID:
                # Skip any existing file creator message
                continue

            # Change device info messages
            if message.global_id == DeviceInfoMessage.ID:
                if isinstance(message, DeviceInfoMessage):
                    self.print_message(f"DeviceInfoMessage Record: {i}", message)
                    if message.device_type == 0:
                        _logger.debug("    Skipping device_type 0")
                        skipped_device_type_zero = True
                        continue

                    # Renumber device_index if we skipped device_type 0
                    if skipped_device_type_zero and message.device_index is not None:
                        _logger.debug(
                            f"    Renumbering device_index from {message.device_index} to {message.device_index - 1}"
                        )
                        message.device_index = message.device_index - 1

                    if self._should_modify_device_info(message.manufacturer):
                        _logger.debug("    Modifying values")
                        _logger.debug(f"garmin_product: {message.garmin_product}")
                        _logger.debug(f"product: {message.product}")

                        # Use profile device settings if available, otherwise defaults
                        if self.profile:
                            target_manufacturer = self.profile.manufacturer
                            target_device = self.profile.device
                        else:
                            target_manufacturer = Manufacturer.GARMIN.value
                            target_device = GarminProduct.EDGE_830.value

                        # have not seen this set explicitly in testing, but probable good to set regardless
                        if message.garmin_product:  # pragma: no cover
                            message.garmin_product = target_device
                        if message.product:
                            message.product = target_device  # type: ignore
                        if message.manufacturer:
                            message.manufacturer = target_manufacturer
                        message.product_name = ""
                        self.print_message(f"    New Record: {i}", message)

            builder.add(message)

        # Add Activity messages at the end to ensure proper FIT file structure
        if activity_messages:
            _logger.debug(
                f"Adding {len(activity_messages)} Activity message(s) at the end"
            )
            for activity_msg in activity_messages:
                builder.add(activity_msg)

        modified_file = builder.build()

        if not dryrun:
            _logger.info(f'Saving modified data to "{output}"')
            modified_file.to_file(str(output))
        else:
            _logger.info(
                f"Dryrun requested, so not saving data "
                f'(would have written to "{output}")'
            )

        return output


# Global FIT editor instance
fit_editor = FitEditor()
