"""
Tests for the FIT file editing functionality.
"""

from pathlib import Path

import pytest
from fit_tool.fit_file import FitFile
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.profile_type import GarminProduct, Manufacturer

from fit_file_faker.fit_editor import FitEditor


def verify_garmin_device_info(fit_file_path: Path):
    """
    Helper function to verify a FIT file has been modified to Garmin Edge 830.

    Args:
        fit_file_path: Path to the FIT file to verify

    Raises:
        AssertionError: If FileIdMessage not found or not properly modified
    """
    modified_fit = FitFile.from_file(str(fit_file_path))

    file_id_found = False
    for record in modified_fit.records:
        message = record.message
        if isinstance(message, FileIdMessage):
            file_id_found = True
            assert message.manufacturer == Manufacturer.GARMIN.value, (
                f"Expected manufacturer GARMIN but got {message.manufacturer}"
            )
            assert message.product == GarminProduct.EDGE_830.value, (
                f"Expected product EDGE_830 but got {message.product}"
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
            ("karoo_fit_parsed", "karoo_modified.fit"),
            ("coros_fit_parsed", "coros_modified.fit"),
        ],
    )
    def test_edit_fit_files(
        self, fit_editor, fit_file_fixture, output_name, temp_dir, request
    ):
        """Test editing FIT files from various platforms (TPV, Zwift, MyWhoosh, Karoo, COROS)."""
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

    def test_invalid_file_handling(self, fit_editor, temp_dir):
        """Test that non-FIT files are handled gracefully."""
        # Create a non-FIT file
        invalid_file = temp_dir / "not_a_fit.fit"
        invalid_file.write_text("This is not a FIT file")

        result = fit_editor.edit_fit(invalid_file, output=temp_dir / "output.fit")

        # Should return None for invalid files
        assert result is None

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

        # Should NOT modify Garmin
        assert not fit_editor._should_modify_manufacturer(Manufacturer.GARMIN.value)

        # Should NOT modify None
        assert not fit_editor._should_modify_manufacturer(None)

    def test_should_modify_device_info(self, fit_editor):
        """Test the device info modification logic."""
        # Should modify these manufacturers
        assert fit_editor._should_modify_device_info(Manufacturer.DEVELOPMENT.value)
        assert fit_editor._should_modify_device_info(0)  # Blank manufacturer
        assert fit_editor._should_modify_device_info(Manufacturer.ZWIFT.value)
        assert fit_editor._should_modify_device_info(Manufacturer.WAHOO_FITNESS.value)
        assert fit_editor._should_modify_device_info(Manufacturer.PEAKSWARE.value)
        assert fit_editor._should_modify_device_info(Manufacturer.HAMMERHEAD.value)
        assert fit_editor._should_modify_device_info(Manufacturer.COROS.value)
        assert fit_editor._should_modify_device_info(331)  # MYWHOOSH

        # Should NOT modify None
        assert not fit_editor._should_modify_device_info(None)

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

    def test_strip_unknown_fields(self, fit_editor, zwift_fit_parsed):
        """Test that unknown fields are properly stripped."""
        # Use cached parsed file
        fit_file = zwift_fit_parsed

        # Apply the strip function
        fit_editor.strip_unknown_fields(fit_file)

        # Verify file still has records
        assert len(fit_file.records) > 0


class TestCustomDeviceSimulation:
    """Tests for custom device simulation via profile settings."""

    @pytest.mark.slow
    def test_edit_fit_with_custom_profile(self, tpv_fit_parsed, temp_dir):
        """Test editing FIT file with custom device profile."""
        from fit_file_faker.config import Profile, AppType
        from fit_tool.profile.profile_type import GarminProduct, Manufacturer

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
        modified_fit = FitFile.from_file(str(output_file))
        file_id_found = False
        for record in modified_fit.records:
            message = record.message
            if isinstance(message, FileIdMessage):
                file_id_found = True
                assert message.manufacturer == Manufacturer.GARMIN.value
                assert message.product == GarminProduct.EDGE_1030.value
                break

        assert file_id_found

    @pytest.mark.slow
    def test_set_profile_after_init(self, tpv_fit_parsed, temp_dir):
        """Test setting profile after initialization."""
        from fit_file_faker.config import Profile, AppType
        from fit_tool.profile.profile_type import GarminProduct

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
        modified_fit = FitFile.from_file(str(output_file))
        for record in modified_fit.records:
            message = record.message
            if isinstance(message, FileIdMessage):
                assert message.product == GarminProduct.EDGE_1030.value
                break

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
        modified_fit = FitFile.from_file(str(output_file))
        for record in modified_fit.records:
            message = record.message
            if isinstance(message, FileIdMessage):
                assert message.manufacturer == Manufacturer.GARMIN.value
                assert message.product == GarminProduct.EDGE_830.value
                break
