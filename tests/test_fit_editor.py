"""
Tests for the FIT file editing functionality.
"""

from pathlib import Path

import pytest
from fit_file_faker.vendor.fit_tool.fit_file import FitFile
from fit_file_faker.vendor.fit_tool.profile.messages.file_creator_message import (
    FileCreatorMessage,
)
from fit_file_faker.vendor.fit_tool.profile.messages.file_id_message import (
    FileIdMessage,
)
from fit_file_faker.vendor.fit_tool.profile.messages.software_message import (
    SoftwareMessage,
)
from fit_file_faker.vendor.fit_tool.profile.messages.device_info_message import (
    DeviceInfoMessage,
)
from fit_file_faker.vendor.fit_tool.profile.profile_type import (
    GarminProduct,
    Manufacturer,
    DeviceIndex,
)

from fit_file_faker.fit_editor import FitEditor


def verify_garmin_device_info(
    fit_file_path: Path,
    expected_product=None,
    expected_manufacturer=None,
):
    """
    Helper function to verify a FIT file has been modified to specified Garmin device.

    Args:
        fit_file_path: Path to the FIT file to verify
        expected_product: Expected product ID (defaults to EDGE_830)
        expected_manufacturer: Expected manufacturer ID (defaults to GARMIN)

    Raises:
        AssertionError: If FileIdMessage not found or not properly modified
    """
    if expected_product is None:
        expected_product = GarminProduct.EDGE_830.value
    if expected_manufacturer is None:
        expected_manufacturer = Manufacturer.GARMIN.value

    modified_fit = FitFile.from_file(str(fit_file_path))

    file_id_found = False
    for record in modified_fit.records:
        message = record.message
        if isinstance(message, FileIdMessage):
            file_id_found = True
            assert message.manufacturer == expected_manufacturer, (
                f"Expected manufacturer {expected_manufacturer} but got {message.manufacturer}"
            )
            assert message.product == expected_product, (
                f"Expected product {expected_product} but got {message.product}"
            )
            break

    assert file_id_found, "FileIdMessage not found in modified file"


@pytest.fixture
def fit_editor():
    """Create a FitEditor instance."""
    return FitEditor()


class TestFitEditor:
    """Tests for the FitEditor class."""

    @pytest.mark.slow
    @pytest.mark.parametrize(
        "fit_file_fixture,output_name",
        [
            ("tpv_fit_0_4_7_parsed", "tpv_0_4_7_modified.fit"),
            ("tpv_fit_0_4_30_parsed", "tpv_0_4_30_modified.fit"),
            ("zwift_fit_parsed", "zwift_modified.fit"),
            ("mywhoosh_fit_parsed", "mywhoosh_modified.fit"),
            ("onelap_fit_parsed", "onelap_modified.fit"),
            ("karoo_fit_parsed", "karoo_modified.fit"),
            ("coros_fit_parsed", "coros_modified.fit"),
            ("zwift_non_utf8_fit_parsed", "zwift_non_utf8_modified.fit"),
            ("tpv_dev_fields_fit_parsed", "tpv_dev_fields_modified.fit"),
        ],
    )
    def test_edit_fit_files(
        self, fit_editor, fit_file_fixture, output_name, temp_dir, request
    ):
        """Test editing FIT files from various platforms (TPV, Zwift, MyWhoosh, Onelap, Karoo, COROS).

        Includes test for Zwift file with non-UTF-8 encoded strings.
        """
        # Get the fixture value using request.getfixturevalue
        fit_file_parsed = request.getfixturevalue(fit_file_fixture)
        output_file = temp_dir / output_name

        # Edit the file using cached parsed FIT file
        result = fit_editor.edit_fit(fit_file_parsed, output=output_file)

        # Verify the file was created
        assert result == output_file
        assert output_file.exists()

        # Verify modifications
        verify_garmin_device_info(output_file)

    @pytest.mark.slow
    def test_dryrun_mode(self, fit_editor, tpv_fit_parsed, temp_dir):
        """Test that dryrun mode doesn't create output files."""
        output_file = temp_dir / "dryrun_output.fit"

        result = fit_editor.edit_fit(tpv_fit_parsed, output=output_file, dryrun=True)

        # Result should still be the output path
        assert result == output_file
        # But the file should NOT exist
        assert not output_file.exists()

    @pytest.mark.slow
    def test_default_output_path(self, fit_editor, tpv_fit_file, temp_dir):
        """Test that default output path uses _modified.fit suffix."""
        # Copy file to temp_dir first
        import shutil

        temp_input = temp_dir / tpv_fit_file.name
        shutil.copy(tpv_fit_file, temp_input)

        # Edit without specifying output
        result = fit_editor.edit_fit(temp_input)

        # Should create file with _modified suffix
        expected_output = temp_dir / f"{tpv_fit_file.stem}_modified.fit"
        assert result == expected_output
        assert expected_output.exists()

    def test_get_date_from_fit(self, fit_editor, tpv_fit_file):
        """Test extracting date from FIT file."""
        date = fit_editor.get_date_from_fit(tpv_fit_file)

        assert date is not None
        # Check that it's a reasonable date (after 2020)
        assert date.year >= 2020

    def test_invalid_file_handling(self, fit_editor, temp_dir, caplog):
        """Test that non-FIT files are handled gracefully with an informative error message."""
        import logging

        invalid_file = temp_dir / "not_a_fit.fit"
        invalid_file.write_text("This is not a FIT file")

        with caplog.at_level(logging.ERROR, logger="garmin"):
            result = fit_editor.edit_fit(invalid_file, output=temp_dir / "output.fit")

        assert result is None

        error_messages = [
            r.message for r in caplog.records if r.levelno == logging.ERROR
        ]
        assert len(error_messages) == 1
        msg = error_messages[0]
        assert "does not appear to be a FIT file" in msg
        assert "Error:" in msg
        assert "-v" in msg
        assert "https://github.com/jat255/Fit-File-Faker/issues" in msg

    def test_should_modify_manufacturer(self, fit_editor):
        """Test the manufacturer modification logic."""
        # Should modify these manufacturers
        assert fit_editor._should_modify_manufacturer(Manufacturer.DEVELOPMENT.value)
        assert fit_editor._should_modify_manufacturer(Manufacturer.ZWIFT.value)
        assert fit_editor._should_modify_manufacturer(Manufacturer.WAHOO_FITNESS.value)
        assert fit_editor._should_modify_manufacturer(Manufacturer.PEAKSWARE.value)
        assert fit_editor._should_modify_manufacturer(Manufacturer.HAMMERHEAD.value)
        assert fit_editor._should_modify_manufacturer(Manufacturer.COROS.value)
        assert fit_editor._should_modify_manufacturer(331)  # MYWHOOSH
        assert fit_editor._should_modify_manufacturer(Manufacturer.ONELAP.value)

        # Should NOT modify Garmin
        assert not fit_editor._should_modify_manufacturer(Manufacturer.GARMIN.value)

        # Should NOT modify None
        assert not fit_editor._should_modify_manufacturer(None)

    def test_should_modify_device_info(self, fit_editor):
        """Test the device info modification logic."""
        # Should modify these manufacturers
        assert fit_editor._should_modify_device_info(
            Manufacturer.DEVELOPMENT.value, DeviceIndex.CREATOR.value
        )
        assert fit_editor._should_modify_device_info(
            0, DeviceIndex.CREATOR.value
        )  # Blank manufacturer
        assert fit_editor._should_modify_device_info(
            Manufacturer.ZWIFT.value, DeviceIndex.CREATOR.value
        )
        assert fit_editor._should_modify_device_info(
            Manufacturer.WAHOO_FITNESS.value, DeviceIndex.CREATOR.value
        )
        assert fit_editor._should_modify_device_info(
            Manufacturer.PEAKSWARE.value, DeviceIndex.CREATOR.value
        )
        assert fit_editor._should_modify_device_info(
            Manufacturer.HAMMERHEAD.value, DeviceIndex.CREATOR.value
        )
        assert fit_editor._should_modify_device_info(
            Manufacturer.COROS.value, DeviceIndex.CREATOR.value
        )
        assert fit_editor._should_modify_device_info(
            331, DeviceIndex.CREATOR.value
        )  # MYWHOOSH
        assert fit_editor._should_modify_device_info(
            Manufacturer.ONELAP.value, DeviceIndex.CREATOR.value
        )
        # Also modify if no device_index is written. Then it is surely no external sensor
        assert fit_editor._should_modify_device_info(
            Manufacturer.DEVELOPMENT.value, None
        )

        # Should NOT modify None
        assert not fit_editor._should_modify_device_info(None, None)
        assert not fit_editor._should_modify_device_info(
            None, DeviceIndex.CREATOR.value
        )

        # Should NOT modify if source type is not LOCAL
        assert not fit_editor._should_modify_device_info(
            Manufacturer.DEVELOPMENT.value, 1
        )
        assert not fit_editor._should_modify_device_info(0, 2)  # Blank manufacturer
        assert not fit_editor._should_modify_device_info(
            Manufacturer.WAHOO_FITNESS.value, 1
        )

    def test_invalid_input_type(self, fit_editor, temp_dir):
        """Test that invalid input types are rejected gracefully."""
        output_file = temp_dir / "output.fit"

        # Pass an invalid type (e.g., string instead of Path or FitFile)
        result = fit_editor.edit_fit("not_a_path", output=output_file)

        # Should return None for invalid input
        assert result is None
        # Should not create output file
        assert not output_file.exists()

    def test_parsed_fit_without_output_path(self, fit_editor, tpv_fit_parsed):
        """Test that parsed FIT file requires output path."""
        # Pass a parsed FitFile without specifying output path
        result = fit_editor.edit_fit(tpv_fit_parsed, output=None)

        # Should return None when output path is not provided for parsed FIT
        assert result is None

    def test_skip_software_message_for_onelap(
        self, fit_editor, onelap_fit_parsed, temp_dir
    ):
        """Test that Software message (ID 35) is skipped when the file is from Onelap."""
        from fit_file_faker.vendor.fit_tool.fit_file import FitFile
        from fit_file_faker.vendor.fit_tool.data_message import DataMessage

        output_file = temp_dir / "onelap_no_software.fit"

        # This will trigger the skip logic for global_id == 35 because is_onelap will be True
        result = fit_editor.edit_fit(onelap_fit_parsed, output=output_file)
        assert result == output_file

        # Verify that the generated file does not have a Software DataMessage
        modified_fit = FitFile.from_file(str(output_file))
        for record in modified_fit.records:
            if isinstance(record.message, DataMessage):
                assert record.message.global_id != 35

    def test_preserves_software_message_for_non_onelap_source(
        self, fit_editor, onelap_fit_parsed, temp_dir
    ):
        """Test that Software messages are only skipped for source Onelap files."""
        output_file = temp_dir / "non_onelap_with_software.fit"

        original_software_count = sum(
            1
            for record in onelap_fit_parsed.records
            if record.message.global_id == SoftwareMessage.ID
        )
        assert original_software_count > 0

        for record in onelap_fit_parsed.records:
            if isinstance(record.message, FileIdMessage):
                record.message.manufacturer = Manufacturer.ZWIFT.value
                break

        result = fit_editor.edit_fit(onelap_fit_parsed, output=output_file)
        assert result == output_file

        modified_fit = FitFile.from_file(str(output_file))
        modified_software_count = sum(
            1
            for record in modified_fit.records
            if record.message.global_id == SoftwareMessage.ID
        )
        assert modified_software_count == original_software_count

    def test_strip_unknown_fields(self, fit_editor, zwift_fit_parsed):
        """Test that unknown fields are properly stripped."""
        # Use cached parsed file
        fit_file = zwift_fit_parsed

        # Apply the strip function
        fit_editor.strip_unknown_fields(fit_file)

        # Verify file still has records
        assert len(fit_file.records) > 0


class TestDeveloperFields:
    """Tests for FIT files containing developer-defined fields."""

    def test_parse_file_with_empty_developer_fields(self, tpv_dev_fields_fit_file):
        """Test that a FIT file with empty developer fields can be parsed without error."""
        from fit_file_faker.vendor.fit_tool.fit_file import FitFile

        fit_file = FitFile.from_file(str(tpv_dev_fields_fit_file))
        assert fit_file is not None
        assert len(fit_file.records) > 0

    def test_developer_field_file_is_tpv(self, tpv_dev_fields_fit_file):
        """Test that the developer fields file is recognized as a TrainingPeaks Virtual file."""
        from fit_file_faker.vendor.fit_tool.fit_file import FitFile
        from fit_file_faker.vendor.fit_tool.profile.messages.file_id_message import (
            FileIdMessage,
        )
        from fit_file_faker.vendor.fit_tool.profile.profile_type import Manufacturer

        fit_file = FitFile.from_file(str(tpv_dev_fields_fit_file))
        for record in fit_file.records:
            message = record.message
            if isinstance(message, FileIdMessage):
                assert message.manufacturer == Manufacturer.PEAKSWARE.value
                assert message.product_name == "TrainingPeaks Virtual"
                return

        pytest.fail("FileIdMessage not found in file")

    @pytest.mark.slow
    def test_edit_fit_with_developer_fields(
        self, fit_editor, tpv_dev_fields_fit_file, temp_dir
    ):
        """Test that a FIT file with empty developer fields can be edited end-to-end."""
        output_file = temp_dir / "tpv_dev_fields_modified.fit"

        result = fit_editor.edit_fit(tpv_dev_fields_fit_file, output=output_file)

        assert result == output_file
        assert output_file.exists()
        verify_garmin_device_info(output_file)

    @pytest.mark.slow
    def test_dryrun_with_developer_fields(
        self, fit_editor, tpv_dev_fields_fit_file, temp_dir
    ):
        """Test dryrun mode on a FIT file with empty developer fields."""
        output_file = temp_dir / "tpv_dev_fields_dryrun.fit"

        result = fit_editor.edit_fit(
            tpv_dev_fields_fit_file, output=output_file, dryrun=True
        )

        assert result == output_file
        assert not output_file.exists()


class TestCustomDeviceSimulation:
    """Tests for custom device simulation via profile settings."""

    @pytest.mark.slow
    def test_edit_fit_with_custom_profile(self, tpv_fit_parsed, temp_dir):
        """Test editing FIT file with custom device profile."""
        from fit_file_faker.config import Profile, AppType
        from fit_file_faker.vendor.fit_tool.profile.profile_type import (
            GarminProduct,
            Manufacturer,
        )

        # Create profile with Edge 1030
        profile = Profile(
            name="custom",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="pass",
            fitfiles_path=Path("/path/to/files"),
            manufacturer=Manufacturer.GARMIN.value,
            device=GarminProduct.EDGE_1030.value,
        )

        # Create editor with profile
        editor = FitEditor(profile=profile)
        output_file = temp_dir / "custom_device.fit"

        # Edit the file
        result = editor.edit_fit(tpv_fit_parsed, output=output_file)

        # Verify the file was created
        assert result == output_file
        assert output_file.exists()

        # Verify it uses Edge 1030 instead of Edge 830
        verify_garmin_device_info(
            output_file,
            expected_product=GarminProduct.EDGE_1030.value,
        )

    @pytest.mark.slow
    def test_edit_fit_with_forerunner_970(self, tpv_fit_parsed, temp_dir):
        """Test that the Forerunner 970 product and firmware are written to FIT."""
        from fit_file_faker.config import AppType, ConfigManager, ProfileManager

        profile = ProfileManager(ConfigManager()).create_profile(
            name="forerunner_970",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="pass",
            fitfiles_path=Path("/path/to/files"),
            device=4565,
        )
        assert profile.software_version == 1832
        output_file = temp_dir / "forerunner_970.fit"

        assert (
            FitEditor(profile=profile).edit_fit(tpv_fit_parsed, output=output_file)
            == output_file
        )
        verify_garmin_device_info(output_file, expected_product=4565)
        assert any(
            isinstance(record.message, FileCreatorMessage)
            and record.message.software_version == 1832
            for record in FitFile.from_file(str(output_file)).records
        )

    @pytest.mark.slow
    def test_set_profile_after_init(self, tpv_fit_parsed, temp_dir):
        """Test setting profile after initialization."""
        from fit_file_faker.config import Profile, AppType
        from fit_file_faker.vendor.fit_tool.profile.profile_type import GarminProduct

        # Create editor without profile
        editor = FitEditor()

        # Create and set profile
        profile = Profile(
            name="custom",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="pass",
            fitfiles_path=Path("/path/to/files"),
            device=GarminProduct.EDGE_1030.value,
        )

        editor.set_profile(profile)
        output_file = temp_dir / "set_profile.fit"

        # Edit the file
        result = editor.edit_fit(tpv_fit_parsed, output=output_file)

        # Verify the file uses Edge 1030
        assert result == output_file
        verify_garmin_device_info(
            output_file,
            expected_product=GarminProduct.EDGE_1030.value,
        )

    @pytest.mark.slow
    def test_edit_fit_without_profile_uses_defaults(self, tpv_fit_parsed, temp_dir):
        """Test that editor without profile defaults to Edge 830."""
        # Create editor without profile
        editor = FitEditor()
        output_file = temp_dir / "defaults.fit"

        # Edit the file
        result = editor.edit_fit(tpv_fit_parsed, output=output_file)

        # Verify it uses default Edge 830
        assert result == output_file
        verify_garmin_device_info(output_file)  # Uses default Edge 830

    @pytest.mark.slow
    def test_edit_fit_with_software_version(self, tpv_fit_parsed, temp_dir):
        """Test that FileCreatorMessage is created when profile has software_version."""
        from fit_file_faker.config import Profile, AppType

        # Create profile with software_version
        # Using Edge 1050 (device ID 4440) from supplemental registry
        profile = Profile(
            name="test",
            app_type=AppType.ZWIFT,
            garmin_username="user@example.com",
            garmin_password="pass",
            fitfiles_path=Path("/path/to/files"),
            device=4440,  # Edge 1050
            software_version=2922,  # v29.22 in FIT format
        )

        editor = FitEditor(profile=profile)
        output_file = temp_dir / "with_software_version.fit"

        # Edit the file
        result = editor.edit_fit(tpv_fit_parsed, output=output_file)

        # Verify FileCreatorMessage exists with software_version
        assert result == output_file
        modified_fit = FitFile.from_file(str(output_file))

        file_creator_found = False
        for record in modified_fit.records:
            message = record.message
            if isinstance(message, FileCreatorMessage):
                file_creator_found = True
                assert message.software_version == 2922
                break

        assert file_creator_found, "FileCreatorMessage not found in modified file"

    @pytest.mark.slow
    def test_edit_fit_with_device_info_serial_number(self, karoo_fit_parsed, temp_dir):
        """Test that software version and serial number are also written to device_info if needed (for Karoo)"""
        from fit_file_faker.config import Profile, AppType

        # Create profile with software_version
        # Using Edge 1050 (device ID 4440) from supplemental registry
        profile = Profile(
            name="test",
            app_type=AppType.CUSTOM,
            garmin_username="user@example.com",
            garmin_password="pass",
            fitfiles_path=Path("/path/to/files"),
            device=4440,  # Edge 1050
            software_version=2922,  # v29.22 in FIT format
            serial_number=1234567890,
        )

        editor = FitEditor(profile=profile)
        output_file = temp_dir / "with_device_info_serial_number.fit"

        # Snapshot before edit_fit mutates parsed messages in place.
        from copy import deepcopy

        original = deepcopy(karoo_fit_parsed)
        result = editor.edit_fit(karoo_fit_parsed, output=output_file)

        assert result == output_file
        # filter out device_type == 0 like in fit-editor
        source_entries = [
            r.message
            for r in original.records
            if isinstance(r.message, DeviceInfoMessage) and r.message.device_type != 0
        ]
        modified_fit = FitFile.from_file(str(output_file))
        modified_entries = [
            record.message
            for record in modified_fit.records
            if (isinstance(record.message, DeviceInfoMessage))
        ]
        assert len(modified_entries) == len(source_entries)

        for source_entry, modified_entry in zip(source_entries, modified_entries):
            if editor._should_modify_device_info(
                source_entry.manufacturer, source_entry.device_index
            ):
                assert modified_entry.garmin_product == profile.device
                assert modified_entry.product == profile.device
                assert modified_entry.manufacturer == profile.manufacturer
                assert modified_entry.serial_number == profile.serial_number
                assert (
                    modified_entry.software_version == profile.software_version / 100.0
                )
            else:
                assert modified_entry.garmin_product == source_entry.garmin_product
                assert modified_entry.product == source_entry.garmin_product
                assert modified_entry.manufacturer == source_entry.manufacturer
                assert modified_entry.serial_number == source_entry.serial_number
                assert modified_entry.software_version == source_entry.software_version


@pytest.mark.parametrize("serial", [None, 111])
def test_creator_identity_and_sensor_preservation(tmp_path, serial):
    """Fill absent creator serials and leave supported-manufacturer sensors intact."""
    from fit_file_faker.vendor.fit_tool.fit_file_builder import FitFileBuilder

    builder = FitFileBuilder(auto_define=True)
    fid = FileIdMessage()
    fid.type = 4
    fid.manufacturer = Manufacturer.HAMMERHEAD.value
    fid.product = 3
    fid.time_created = 1785916974000
    builder.add(fid)
    for index in (0, 1):
        dev = DeviceInfoMessage()
        dev.device_index = index
        dev.manufacturer = Manufacturer.WAHOO_FITNESS.value
        dev.product = 3
        dev.product_name = "Original device"
        if serial is not None:
            dev.serial_number = serial
        builder.add(dev)
    src, out = tmp_path / "source.fit", tmp_path / "out.fit"
    builder.build().to_file(str(src))
    FitEditor().edit_fit(src, output=out)
    messages = [r.message for r in FitFile.from_file(str(out)).records]
    fid = next(m for m in messages if isinstance(m, FileIdMessage))
    creator, sensor = [m for m in messages if isinstance(m, DeviceInfoMessage)]
    assert creator.serial_number == fid.serial_number
    assert creator.product == fid.product
    assert sensor.manufacturer == Manufacturer.WAHOO_FITNESS.value
    assert sensor.product == 3
    assert sensor.serial_number == serial
    assert sensor.product_name == "Original device"


class TestDeviceInfoWithoutProduct:
    """Regression tests for issue #80 (COROS DURA device_info lacks product)."""

    @staticmethod
    def _build_dura_like_file(path: Path) -> None:
        from datetime import datetime

        from fit_file_faker.vendor.fit_tool.fit_file_builder import FitFileBuilder
        from fit_file_faker.vendor.fit_tool.profile.messages.device_info_message import (
            DeviceInfoMessage,
        )
        from fit_file_faker.vendor.fit_tool.profile.messages.record_message import (
            RecordMessage,
        )
        from fit_file_faker.vendor.fit_tool.profile.profile_type import FileType

        ts = int(datetime(2026, 8, 4, 8).timestamp() * 1000)
        builder = FitFileBuilder(auto_define=True)
        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.COROS.value
        file_id.time_created = ts
        file_id.serial_number = 111
        builder.add(file_id)
        dev = DeviceInfoMessage()
        dev.timestamp = ts
        dev.device_index = 0
        dev.manufacturer = Manufacturer.COROS.value
        dev.product_name = "COROS DURA"
        dev.serial_number = 111
        builder.add(dev)
        rec = RecordMessage()
        rec.timestamp = ts
        rec.heart_rate = 120
        builder.add(rec)
        builder.build().to_file(str(path))

    def test_device_info_gets_product_when_source_has_none(self, tmp_path):
        from fit_file_faker.vendor.fit_tool.profile.messages.device_info_message import (
            DeviceInfoMessage,
        )

        src = tmp_path / "dura.fit"
        out = tmp_path / "dura_modified.fit"
        self._build_dura_like_file(src)

        result = FitEditor().edit_fit(src, output=out)
        assert result == out

        devices = [
            r.message
            for r in FitFile.from_file(str(out)).records
            if isinstance(r.message, DeviceInfoMessage)
        ]
        assert len(devices) == 1
        dev = devices[0]
        assert dev.manufacturer == Manufacturer.GARMIN.value
        assert dev.product == GarminProduct.EDGE_830.value
        assert dev.serial_number == 1234567890
        assert dev.device_index == 0

    @pytest.mark.parametrize("source_type", [None, 5])
    def test_device_info_without_index_marked_as_creator(self, tmp_path, source_type):
        """COROS DURA device_info also omits device_index/serial/source_type."""
        from datetime import datetime

        from fit_file_faker.vendor.fit_tool.fit_file_builder import FitFileBuilder
        from fit_file_faker.vendor.fit_tool.profile.messages.device_info_message import (
            DeviceInfoMessage,
        )
        from fit_file_faker.vendor.fit_tool.profile.profile_type import FileType

        ts = int(datetime(2026, 8, 4, 8).timestamp() * 1000)
        builder = FitFileBuilder(auto_define=True)
        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.COROS.value
        file_id.time_created = ts
        builder.add(file_id)
        dev = DeviceInfoMessage()
        dev.timestamp = ts
        dev.manufacturer = Manufacturer.COROS.value
        dev.product_name = "COROS DURA"
        if source_type is not None:
            dev.source_type = source_type
        builder.add(dev)
        src = tmp_path / "dura_min.fit"
        out = tmp_path / "dura_min_modified.fit"
        builder.build().to_file(str(src))

        FitEditor().edit_fit(src, output=out)
        devs = [
            r.message
            for r in FitFile.from_file(str(out)).records
            if isinstance(r.message, DeviceInfoMessage)
        ]
        assert devs[0].device_index == 0
        assert devs[0].source_type == 5
        assert devs[0].serial_number is not None
        assert devs[0].product == GarminProduct.EDGE_830.value


class TestGarminFileIdWithoutDeviceInfo:
    """Files that already claim Garmin (e.g. TrainerDay) and have no device_info."""

    @staticmethod
    def _build(path: Path) -> None:
        from datetime import datetime

        from fit_file_faker.vendor.fit_tool.fit_file_builder import FitFileBuilder
        from fit_file_faker.vendor.fit_tool.profile.messages.record_message import (
            RecordMessage,
        )
        from fit_file_faker.vendor.fit_tool.profile.profile_type import FileType

        ts = int(datetime(2026, 10, 13, 20).timestamp() * 1000)
        builder = FitFileBuilder(auto_define=True)
        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.GARMIN.value
        file_id.product = GarminProduct.EDGE_530.value
        file_id.serial_number = 3987112345
        file_id.time_created = ts
        builder.add(file_id)
        rec = RecordMessage()
        rec.timestamp = ts
        rec.power = 200
        builder.add(rec)
        builder.build().to_file(str(path))

    def test_garmin_file_id_identity_preserved(self, tmp_path):
        src, out = tmp_path / "td.fit", tmp_path / "td_modified.fit"
        self._build(src)
        FitEditor().edit_fit(src, output=out)
        fid = next(
            r.message
            for r in FitFile.from_file(str(out)).records
            if isinstance(r.message, FileIdMessage)
        )
        assert fid.manufacturer == Manufacturer.GARMIN.value
        assert fid.product == GarminProduct.EDGE_530.value
        assert fid.serial_number == 3987112345

    def test_creator_device_info_added_when_missing(self, tmp_path):
        from fit_file_faker.vendor.fit_tool.profile.messages.device_info_message import (
            DeviceInfoMessage,
        )

        src, out = tmp_path / "td.fit", tmp_path / "td_modified.fit"
        self._build(src)
        FitEditor().edit_fit(src, output=out)
        devs = [
            r.message
            for r in FitFile.from_file(str(out)).records
            if isinstance(r.message, DeviceInfoMessage)
        ]
        assert len(devs) == 1
        assert devs[0].device_index == 0
        assert devs[0].manufacturer == Manufacturer.GARMIN.value
        assert devs[0].product == GarminProduct.EDGE_530.value
        assert devs[0].serial_number == 3987112345


def test_renumbered_creator_is_not_duplicated(tmp_path):
    from fit_file_faker.vendor.fit_tool.fit_file_builder import FitFileBuilder

    builder = FitFileBuilder(auto_define=True)
    fid = FileIdMessage()
    fid.type = 4
    fid.manufacturer = Manufacturer.HAMMERHEAD.value
    fid.product = 3
    fid.time_created = 1785916974000
    builder.add(fid)
    for index, device_type in ((0, 0), (1, 4)):
        dev = DeviceInfoMessage()
        dev.device_index = index
        dev.device_type = device_type
        dev.manufacturer = Manufacturer.HAMMERHEAD.value
        dev.product = 3
        dev.product_name = "Karoo"
        builder.add(dev)
    src, out = tmp_path / "source.fit", tmp_path / "out.fit"
    builder.build().to_file(str(src))
    FitEditor().edit_fit(src, output=out)
    devices = [
        r.message
        for r in FitFile.from_file(str(out)).records
        if isinstance(r.message, DeviceInfoMessage)
    ]
    assert len(devices) == 1
    assert devices[0].device_index == 0


def test_rebuild_device_info_preserves_developer_fields():
    """Rebuilding a creator must retain independent copies of custom data."""
    from fit_file_faker.vendor.fit_tool.base_type import BaseType
    from fit_file_faker.vendor.fit_tool.developer_field import DeveloperField

    dev = DeviceInfoMessage()
    custom = DeveloperField(
        field_id=1,
        name="custom",
        base_type=BaseType.UINT16,
        developer_data_index=2,
        growable=True,
    )
    custom.set_value(0, 123)
    dev.developer_fields.append(custom)
    rebuilt = FitEditor._rebuild_device_info(dev)
    assert len(rebuilt.developer_fields) == 1
    copied = rebuilt.developer_fields[0]
    assert copied.get_value() == 123
    assert copied.developer_data_index == 2
    assert copied is not custom
    copied.set_value(0, 456)
    assert custom.get_value() == 123


def test_rebuild_device_info_skips_unknown_standard_fields():
    """An unsupported field must not prevent copying known device metadata."""
    from fit_file_faker.vendor.fit_tool.base_type import BaseType
    from fit_file_faker.vendor.fit_tool.field import Field

    dev = DeviceInfoMessage()
    dev.manufacturer = Manufacturer.COROS.value
    dev.product_name = "COROS DURA"
    unknown = Field(field_id=254, base_type=BaseType.UINT8, growable=True)
    unknown.set_value(0, 42)
    dev.fields.append(unknown)

    rebuilt = FitEditor._rebuild_device_info(dev)
    assert rebuilt.get_field(254) is None
    assert rebuilt.manufacturer == dev.manufacturer
    assert rebuilt.product_name == dev.product_name


@pytest.mark.parametrize("source_type", [0, 1, 2, 3, 4])
@pytest.mark.parametrize(
    "manufacturer", [Manufacturer.GARMIN.value, Manufacturer.WAHOO_FITNESS.value]
)
def test_unindexed_external_sensor_does_not_replace_creator(
    tmp_path, source_type, manufacturer
):
    """External sensor records neither suppress a creator nor get rewritten."""
    from fit_file_faker.vendor.fit_tool.fit_file_builder import FitFileBuilder

    builder = FitFileBuilder(auto_define=True)
    fid = FileIdMessage()
    fid.type = 4
    fid.manufacturer = Manufacturer.GARMIN.value
    fid.product = GarminProduct.EDGE_530.value
    fid.serial_number = 3987112345
    fid.time_created = 1785916974000
    builder.add(fid)
    sensor = DeviceInfoMessage()
    sensor.source_type = source_type
    sensor.device_type = 120
    sensor.manufacturer = manufacturer
    sensor.product = 42
    sensor.serial_number = 1234567891
    sensor.product_name = "Heart rate sensor"
    builder.add(sensor)
    src, out = tmp_path / "sensor_only.fit", tmp_path / "modified.fit"
    builder.build().to_file(str(src))

    FitEditor().edit_fit(src, output=out)
    devices = [
        r.message
        for r in FitFile.from_file(str(out)).records
        if isinstance(r.message, DeviceInfoMessage)
    ]
    assert len(devices) == 2
    creator, preserved_sensor = devices
    assert creator.device_index == 0
    assert creator.source_type == 5
    assert creator.manufacturer == fid.manufacturer
    assert creator.product == fid.product
    assert creator.serial_number == fid.serial_number
    assert preserved_sensor.device_index is None
    assert preserved_sensor.source_type == source_type
    assert preserved_sensor.device_type == 120
    assert preserved_sensor.manufacturer == manufacturer
    assert preserved_sensor.product == 42
    assert preserved_sensor.serial_number == 1234567891
    assert preserved_sensor.product_name == "Heart rate sensor"
