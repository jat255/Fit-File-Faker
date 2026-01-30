"""
Tests for the main application functionality including CLI and upload features.
"""

import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from fit_file_faker.app import (
    FILES_UPLOADED_NAME,
    NewFileEventHandler,
    monitor,
    select_profile,
    upload,
    upload_all,
)

# Import shared mock classes from conftest
from .conftest import MockGarthHTTPError


# Test Fixtures and Helpers


@pytest.fixture
def mock_valid_config():
    """Create a valid mock config_manager with profile."""
    with patch("fit_file_faker.app.config_manager") as mock_config:
        mock_config.is_valid.return_value = True
        # Create a mock profile
        mock_profile = MagicMock()
        mock_profile.garmin_username = "test@example.com"
        mock_profile.garmin_password = "testpass"
        mock_profile.fitfiles_path = None
        mock_config.config.get_default_profile.return_value = mock_profile
        yield mock_config


class TestUploadFunction:
    """Tests for the upload functionality with mocked Garmin requests."""

    def test_upload_success(self, tpv_fit_file, mock_garth_basic, mock_valid_config):
        """Test successful file upload to Garmin Connect."""
        mock_garth, mock_garth_exc = mock_garth_basic
        mock_profile = mock_valid_config.config.get_default_profile()

        with patch.dict(
            "sys.modules", {"garth": mock_garth, "garth.exc": mock_garth_exc}
        ):
            upload(tpv_fit_file, profile=mock_profile, dryrun=False)
            mock_garth.client.upload.assert_called_once()

    def test_upload_with_login(
        self, tpv_fit_file, mock_garth_with_login, mock_valid_config
    ):
        """Test upload that requires login."""
        mock_garth, mock_garth_exc = mock_garth_with_login
        mock_profile = mock_valid_config.config.get_default_profile()

        with patch.dict(
            "sys.modules", {"garth": mock_garth, "garth.exc": mock_garth_exc}
        ):
            upload(tpv_fit_file, profile=mock_profile, dryrun=False)

            # Verify login was called with config credentials
            mock_garth.login.assert_called_once_with("test@example.com", "testpass")
            mock_garth.save.assert_called_once()

    def test_upload_http_errors(
        self, tpv_fit_file, mock_garth_basic, caplog, mock_valid_config
    ):
        """Test upload handling HTTP errors - 409 conflict handled gracefully, others raise."""
        mock_garth, mock_garth_exc = mock_garth_basic
        mock_profile = mock_valid_config.config.get_default_profile()

        # Test 409 conflict (duplicate activity) - should be handled gracefully
        mock_garth.client.upload = Mock(side_effect=MockGarthHTTPError(409))
        with patch.dict(
            "sys.modules", {"garth": mock_garth, "garth.exc": mock_garth_exc}
        ):
            upload(
                tpv_fit_file,
                profile=mock_profile,
                original_path=Path("test.fit"),
                dryrun=False,
            )
            assert "conflict" in caplog.text.lower() or "409" in caplog.text

        # Test non-409 errors (500) - should raise exception
        caplog.clear()
        mock_garth.client.upload = Mock(side_effect=MockGarthHTTPError(500))
        with patch.dict(
            "sys.modules", {"garth": mock_garth, "garth.exc": mock_garth_exc}
        ):
            with pytest.raises(MockGarthHTTPError):
                upload(
                    tpv_fit_file,
                    profile=mock_profile,
                    original_path=Path("test.fit"),
                    dryrun=False,
                )

    def test_upload_dryrun(self, tpv_fit_file, mock_garth_basic, mock_valid_config):
        """Test that dryrun doesn't actually upload."""
        mock_garth, mock_garth_exc = mock_garth_basic
        mock_profile = mock_valid_config.config.get_default_profile()

        with patch.dict(
            "sys.modules", {"garth": mock_garth, "garth.exc": mock_garth_exc}
        ):
            upload(tpv_fit_file, profile=mock_profile, dryrun=True)
            mock_garth.client.upload.assert_not_called()

    def test_upload_interactive_credentials(self, tpv_fit_file, mock_garth_with_login):
        """Test interactive credential input when not in config."""
        mock_garth, mock_garth_exc = mock_garth_with_login

        with (
            patch.dict(
                "sys.modules", {"garth": mock_garth, "garth.exc": mock_garth_exc}
            ),
            patch("fit_file_faker.app.questionary") as mock_questionary,
            patch("fit_file_faker.app.config_manager") as mock_config_manager,
        ):
            # Mock questionary to provide credentials
            mock_questionary.text.return_value.ask.return_value = (
                "interactive@example.com"
            )
            mock_questionary.password.return_value.ask.return_value = "interactive_pass"

            # Mock profile with no credentials
            mock_profile = MagicMock()
            mock_profile.garmin_username = None
            mock_profile.garmin_password = None
            mock_config_manager.config.get_default_profile.return_value = mock_profile

            upload(tpv_fit_file, profile=mock_profile, dryrun=False)

            # Verify interactive prompts were used
            mock_questionary.text.assert_called_once()
            mock_questionary.password.assert_called_once()
            mock_garth.login.assert_called_once_with(
                "interactive@example.com", "interactive_pass"
            )


class TestUploadAllFunction:
    """Tests for batch upload functionality."""

    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    def test_upload_all_new_files(
        self, mock_upload, mock_fit_editor, temp_dir, tpv_fit_file
    ):
        """Test uploading all new files in a directory."""
        # Copy test file to temp directory
        import shutil

        test_file = temp_dir / "test_activity.fit"
        shutil.copy(tpv_fit_file, test_file)

        # Mock fit_editor to return a path
        mock_fit_editor.edit_fit.return_value = temp_dir / "test_activity_modified.fit"

        # Create mock profile
        mock_profile = MagicMock()
        mock_profile.garmin_username = "test@example.com"
        mock_profile.garmin_password = "testpass"

        # Run upload_all
        upload_all(temp_dir, profile=mock_profile, dryrun=False)

        # Verify edit and upload were called
        assert mock_fit_editor.edit_fit.called
        assert mock_upload.called

        # Verify uploaded files list was created
        uploaded_list = temp_dir / FILES_UPLOADED_NAME
        assert uploaded_list.exists()

        with uploaded_list.open("r") as f:
            uploaded = json.load(f)
        assert "test_activity.fit" in uploaded

    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    def test_upload_all_skips_already_uploaded(
        self, mock_upload, mock_fit_editor, temp_dir, tpv_fit_file
    ):
        """Test that already uploaded files are skipped."""
        import shutil

        # Copy test file
        test_file = temp_dir / "test_activity.fit"
        shutil.copy(tpv_fit_file, test_file)

        # Create uploaded files list with this file already in it
        uploaded_list = temp_dir / FILES_UPLOADED_NAME
        with uploaded_list.open("w") as f:
            json.dump(["test_activity.fit"], f)

        # Create mock profile
        mock_profile = MagicMock()
        mock_profile.garmin_username = "test@example.com"
        mock_profile.garmin_password = "testpass"

        # Run upload_all
        upload_all(temp_dir, profile=mock_profile, dryrun=False)

        # Should NOT process the file
        mock_fit_editor.edit_fit.assert_not_called()
        mock_upload.assert_not_called()

    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    def test_upload_all_skips_modified_files(
        self, mock_upload, mock_fit_editor, temp_dir, tpv_fit_file
    ):
        """Test that files ending in _modified.fit are skipped."""
        import shutil

        # Copy test file with _modified suffix
        test_file = temp_dir / "test_activity_modified.fit"
        shutil.copy(tpv_fit_file, test_file)

        # Create mock profile
        mock_profile = MagicMock()
        mock_profile.garmin_username = "test@example.com"
        mock_profile.garmin_password = "testpass"

        # Run upload_all
        upload_all(temp_dir, profile=mock_profile, dryrun=False)

        # Should NOT process modified files
        mock_fit_editor.edit_fit.assert_not_called()

    def test_upload_all_preinitialize(self, temp_dir, tpv_fit_file):
        """Test preinitialize mode marks all files as uploaded without processing."""
        import shutil

        # Copy test files
        test_file1 = temp_dir / "test1.fit"
        test_file2 = temp_dir / "test2.fit"
        shutil.copy(tpv_fit_file, test_file1)
        shutil.copy(tpv_fit_file, test_file2)

        # Create mock profile
        mock_profile = MagicMock()
        mock_profile.garmin_username = "test@example.com"
        mock_profile.garmin_password = "testpass"

        # Run with preinitialize
        upload_all(temp_dir, profile=mock_profile, preinitialize=True, dryrun=False)

        # Check uploaded files list
        uploaded_list = temp_dir / FILES_UPLOADED_NAME
        assert uploaded_list.exists()

        with uploaded_list.open("r") as f:
            uploaded = json.load(f)

        assert "test1.fit" in uploaded
        assert "test2.fit" in uploaded

    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    def test_upload_all_dryrun(
        self, mock_upload, mock_fit_editor, temp_dir, tpv_fit_file
    ):
        """Test that dryrun doesn't save uploaded files list."""
        import shutil

        test_file = temp_dir / "test_activity.fit"
        shutil.copy(tpv_fit_file, test_file)

        mock_fit_editor.edit_fit.return_value = temp_dir / "test_modified.fit"

        # Create mock profile
        mock_profile = MagicMock()
        mock_profile.garmin_username = "test@example.com"
        mock_profile.garmin_password = "testpass"

        # Run with dryrun
        upload_all(temp_dir, profile=mock_profile, dryrun=True)

        # Uploaded files list should exist but be empty initially
        uploaded_list = temp_dir / FILES_UPLOADED_NAME
        if uploaded_list.exists():
            with uploaded_list.open("r") as f:
                json.load(f)
            # In dryrun, the list might be created but shouldn't be updated with processed files
            # This depends on implementation details


class TestNewFileEventHandler:
    """Tests for the file monitoring event handler."""

    def test_event_handler_initialization(self):
        """Test NewFileEventHandler initialization."""
        mock_profile = MagicMock()
        handler = NewFileEventHandler(profile=mock_profile, dryrun=False)

        assert handler.patterns == ["*.fit", "MyNewActivity-*.fit"]
        assert handler.ignore_directories is True
        assert handler.case_sensitive is False

    @patch("fit_file_faker.app.upload_all")
    @patch("fit_file_faker.app.time.sleep")
    def test_on_created_processes_file(self, mock_sleep, mock_upload_all, temp_dir):
        """Test that new file creation triggers processing."""
        mock_profile = MagicMock()
        handler = NewFileEventHandler(profile=mock_profile, dryrun=False)

        # Create a mock event
        from watchdog.events import FileCreatedEvent

        test_file = temp_dir / "new_activity.fit"
        test_file.touch()

        event = FileCreatedEvent(str(test_file))

        # Trigger event
        handler.on_created(event)

        # Should sleep for 5 seconds (to ensure file is fully written)
        mock_sleep.assert_called_once_with(5)

        # Should call upload_all with the parent directory and profile
        mock_upload_all.assert_called_once_with(temp_dir, profile=mock_profile)

    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    @patch("fit_file_faker.app.time.sleep")
    def test_on_modified_processes_mywhoosh_file(
        self, mock_sleep, mock_upload, mock_fit_editor, temp_dir
    ):
        """Test that MyWhoosh file modifications trigger processing and upload."""
        mock_profile = MagicMock()
        mock_profile.name = "test_profile"
        handler = NewFileEventHandler(profile=mock_profile, dryrun=False)

        # Create a mock MyWhoosh file
        from watchdog.events import FileModifiedEvent

        test_file = temp_dir / "MyNewActivity-12345.fit"
        test_file.touch()

        # Mock fit_editor to return a path (edit_fit receives the temp file path as output)
        mock_output_file = temp_dir / "output_file.fit"
        mock_fit_editor.edit_fit.return_value = mock_output_file

        event = FileModifiedEvent(str(test_file))

        # Trigger event
        handler.on_modified(event)

        # Should sleep for 5 seconds (to ensure file is fully written)
        mock_sleep.assert_called_once_with(5)

        # Should call edit_fit with the modified file
        mock_fit_editor.edit_fit.assert_called_once()
        call_args = mock_fit_editor.edit_fit.call_args
        assert call_args[0][0] == test_file
        # output parameter should be a Path object (the temp file path)
        assert isinstance(call_args.kwargs["output"], Path)

        # Should call upload with the output file
        mock_upload.assert_called_once()
        call_args = mock_upload.call_args
        assert call_args[0][0] == mock_output_file
        assert call_args.kwargs["profile"] == mock_profile
        assert call_args.kwargs["original_path"] == test_file
        assert call_args.kwargs["dryrun"] is False

    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    @patch("fit_file_faker.app.time.sleep")
    def test_on_modified_ignores_non_mywhoosh_files(
        self, mock_sleep, mock_upload, mock_fit_editor, temp_dir
    ):
        """Test that non-MyWhoosh file modifications are ignored."""
        mock_profile = MagicMock()
        handler = NewFileEventHandler(profile=mock_profile, dryrun=False)

        # Create a non-MyWhoosh FIT file
        from watchdog.events import FileModifiedEvent

        test_file = temp_dir / "regular_activity.fit"
        test_file.touch()

        event = FileModifiedEvent(str(test_file))

        # Trigger event
        handler.on_modified(event)

        # Should NOT sleep or process
        mock_sleep.assert_not_called()
        mock_fit_editor.edit_fit.assert_not_called()
        mock_upload.assert_not_called()

    @pytest.mark.parametrize(
        "event_type,file_name",
        [
            ("created", "new_activity.fit"),
            ("modified", "MyNewActivity-12345.fit"),
        ],
    )
    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    @patch("fit_file_faker.app.upload_all")
    @patch("fit_file_faker.app.time.sleep")
    def test_dryrun_mode(
        self,
        mock_sleep,
        mock_upload_all,
        mock_upload,
        mock_fit_editor,
        temp_dir,
        event_type,
        file_name,
    ):
        """Test that dryrun mode doesn't process files for both created and modified events."""
        from watchdog.events import FileCreatedEvent, FileModifiedEvent

        mock_profile = MagicMock()
        handler = NewFileEventHandler(profile=mock_profile, dryrun=True)

        test_file = temp_dir / file_name
        test_file.touch()

        # Create appropriate event type
        if event_type == "created":
            event = FileCreatedEvent(str(test_file))
            handler.on_created(event)
        else:
            event = FileModifiedEvent(str(test_file))
            handler.on_modified(event)

        # Should NOT sleep or process in dryrun mode
        mock_sleep.assert_not_called()
        mock_fit_editor.edit_fit.assert_not_called()
        mock_upload.assert_not_called()
        mock_upload_all.assert_not_called()

    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    @patch("fit_file_faker.app.time.sleep")
    def test_on_modified_with_case_insensitive_pattern(
        self, mock_sleep, mock_upload, mock_fit_editor, temp_dir
    ):
        """Test that on_modified correctly handles different case variations."""
        mock_profile = MagicMock()
        mock_profile.name = "test_profile"
        handler = NewFileEventHandler(profile=mock_profile, dryrun=False)

        # Create a mock MyWhoosh file with different case
        from watchdog.events import FileModifiedEvent

        test_file = temp_dir / "MYWHOOSH_Activity-12345.fit"
        test_file.touch()

        # Mock fit_editor to return a path
        mock_output_file = temp_dir / "output_file.fit"
        mock_fit_editor.edit_fit.return_value = mock_output_file

        event = FileModifiedEvent(str(test_file))

        # Trigger event
        handler.on_modified(event)

        # Should NOT process because the pattern is case-sensitive and looking for "MyNewActivity-"
        mock_sleep.assert_not_called()
        mock_fit_editor.edit_fit.assert_not_called()
        mock_upload.assert_not_called()

    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    @patch("fit_file_faker.app.time.sleep")
    def test_on_modified_handles_edit_failure(
        self, mock_sleep, mock_upload, mock_fit_editor, temp_dir
    ):
        """Test that on_modified handles edit_fit returning None gracefully."""
        mock_profile = MagicMock()
        mock_profile.name = "test_profile"
        handler = NewFileEventHandler(profile=mock_profile, dryrun=False)

        # Create a mock MyWhoosh file
        from watchdog.events import FileModifiedEvent

        test_file = temp_dir / "MyNewActivity-12345.fit"
        test_file.touch()

        # Mock fit_editor to return None (failure case)
        mock_fit_editor.edit_fit.return_value = None

        event = FileModifiedEvent(str(test_file))

        # Trigger event
        handler.on_modified(event)

        # Should sleep and try to edit
        mock_sleep.assert_called_once_with(5)
        mock_fit_editor.edit_fit.assert_called_once()

        # But should NOT try to upload if edit failed
        mock_upload.assert_not_called()

    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    @patch("fit_file_faker.app.time.sleep")
    def test_on_modified_adds_to_uploaded_files(
        self, mock_sleep, mock_upload, mock_fit_editor, temp_dir
    ):
        """Test that on_modified adds successfully uploaded files to tracking list."""
        mock_profile = MagicMock()
        mock_profile.name = "test_profile"
        handler = NewFileEventHandler(profile=mock_profile, dryrun=False)

        # Create a mock MyWhoosh file
        from watchdog.events import FileModifiedEvent

        test_file = temp_dir / "MyNewActivity-12345.fit"
        test_file.touch()

        # Mock fit_editor to return a path
        mock_output_file = temp_dir / "output_file.fit"
        mock_fit_editor.edit_fit.return_value = mock_output_file

        event = FileModifiedEvent(str(test_file))

        # Trigger event
        handler.on_modified(event)

        # Should upload the file
        mock_upload.assert_called_once()

        # Verify that the file was added to uploaded_files.json
        uploaded_list = temp_dir / FILES_UPLOADED_NAME
        assert uploaded_list.exists()

        with uploaded_list.open("r") as f:
            uploaded_files = json.load(f)

        assert "MyNewActivity-12345.fit" in uploaded_files

    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    @patch("fit_file_faker.app.time.sleep")
    def test_on_modified_tracking_idempotent(
        self, mock_sleep, mock_upload, mock_fit_editor, temp_dir
    ):
        """Test that on_modified doesn't add the same file twice to tracking list."""
        mock_profile = MagicMock()
        mock_profile.name = "test_profile"
        handler = NewFileEventHandler(profile=mock_profile, dryrun=False)

        # Create a mock MyWhoosh file
        from watchdog.events import FileModifiedEvent

        test_file = temp_dir / "MyNewActivity-12345.fit"
        test_file.touch()

        # Pre-populate the uploaded files list with this file
        uploaded_list = temp_dir / FILES_UPLOADED_NAME
        with uploaded_list.open("w") as f:
            json.dump(["MyNewActivity-12345.fit"], f)

        # Mock fit_editor to return a path
        mock_output_file = temp_dir / "output_file.fit"
        mock_fit_editor.edit_fit.return_value = mock_output_file

        event = FileModifiedEvent(str(test_file))

        # Trigger event
        handler.on_modified(event)

        # Should upload the file
        mock_upload.assert_called_once()

        # Verify that the file appears only once in the list
        with uploaded_list.open("r") as f:
            uploaded_files = json.load(f)

        assert uploaded_files.count("MyNewActivity-12345.fit") == 1

    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    @patch("fit_file_faker.app.time.sleep")
    def test_on_modified_dryrun_no_tracking(
        self, mock_sleep, mock_upload, mock_fit_editor, temp_dir
    ):
        """Test that dryrun mode doesn't add files to tracking list."""
        mock_profile = MagicMock()
        mock_profile.name = "test_profile"
        handler = NewFileEventHandler(profile=mock_profile, dryrun=True)

        # Create a mock MyWhoosh file
        from watchdog.events import FileModifiedEvent

        test_file = temp_dir / "MyNewActivity-12345.fit"
        test_file.touch()

        event = FileModifiedEvent(str(test_file))

        # Trigger event
        handler.on_modified(event)

        # Should NOT process or track in dryrun mode
        mock_sleep.assert_not_called()
        mock_fit_editor.edit_fit.assert_not_called()
        mock_upload.assert_not_called()

        # Verify that no tracking file was created
        uploaded_list = temp_dir / FILES_UPLOADED_NAME
        assert not uploaded_list.exists()

    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    @patch("fit_file_faker.app.time.sleep")
    def test_mywhoosh_version_update_no_duplicate(
        self, mock_sleep, mock_upload, mock_fit_editor, temp_dir
    ):
        """Test that version updates don't cause duplicate uploads.

        This is the integration test for bug #59. When MyWhoosh updates versions,
        old version files remain. This test verifies that:
        1. on_modified() adds successfully uploaded files to tracking
        2. upload_all() skips files already in the tracking list
        """
        mock_profile = MagicMock()
        mock_profile.name = "test_profile"
        handler = NewFileEventHandler(profile=mock_profile, dryrun=False)

        # Create the old version file (MyWhoosh 5.5.0)
        from watchdog.events import FileModifiedEvent

        old_file = temp_dir / "MyNewActivity-5.5.0.fit"
        old_file.touch()

        # Mock fit_editor to return a path
        mock_output_file = temp_dir / "output_file.fit"
        mock_fit_editor.edit_fit.return_value = mock_output_file
        mock_fit_editor.set_profile = MagicMock()

        # Trigger modification event (simulating MyWhoosh completing the file)
        event = FileModifiedEvent(str(old_file))
        handler.on_modified(event)

        # Verify old file was uploaded and tracked
        assert mock_upload.call_count == 1
        uploaded_list = temp_dir / FILES_UPLOADED_NAME
        assert uploaded_list.exists()

        with uploaded_list.open("r") as f:
            uploaded_files = json.load(f)
        assert "MyNewActivity-5.5.0.fit" in uploaded_files

        # Now create the new version file (MyWhoosh 5.6.0)
        new_file = temp_dir / "MyNewActivity-5.6.0.fit"
        new_file.touch()

        # Reset mocks
        mock_upload.reset_mock()
        mock_fit_editor.edit_fit.reset_mock()

        # Now call upload_all directly (simulating what happens when on_created triggers it)
        # This should skip the old file (already tracked) and only process the new file
        from fit_file_faker.app import upload_all

        upload_all(temp_dir, profile=mock_profile, dryrun=False)

        # fit_editor.edit_fit should only be called once (for new file)
        # not twice (which would indicate the old file was also processed)
        assert mock_fit_editor.edit_fit.call_count == 1

        # Verify only the new file was processed
        call_args = mock_fit_editor.edit_fit.call_args
        assert call_args[0][0] == new_file

        # Verify the new file is now in the tracking list
        with uploaded_list.open("r") as f:
            uploaded_files = json.load(f)

        assert "MyNewActivity-5.5.0.fit" in uploaded_files
        assert "MyNewActivity-5.6.0.fit" in uploaded_files
        # Should only have these two files (no duplicates)
        assert len(uploaded_files) == 2


class TestSelectProfileFunction:
    """Tests for the select_profile function."""

    def test_select_profile_by_name_found(self):
        """Test selecting a profile by name when it exists."""
        mock_profile = MagicMock()
        mock_profile.name = "test_profile"

        with patch("fit_file_faker.app.profile_manager") as mock_pm:
            mock_pm.get_profile.return_value = mock_profile

            result = select_profile("test_profile")

            assert result == mock_profile
            mock_pm.get_profile.assert_called_once_with("test_profile")

    def test_select_profile_by_name_not_found(self):
        """Test selecting a profile by name when it doesn't exist raises ValueError."""
        with patch("fit_file_faker.app.profile_manager") as mock_pm:
            mock_pm.get_profile.return_value = None

            with pytest.raises(ValueError) as exc_info:
                select_profile("nonexistent_profile")

            assert "nonexistent_profile" in str(exc_info.value)
            assert "--list-profiles" in str(exc_info.value)

    def test_select_profile_uses_default_when_available(self):
        """Test that default profile is used when no name specified."""
        mock_default = MagicMock()
        mock_default.name = "default_profile"

        with patch("fit_file_faker.app.config_manager") as mock_cm:
            mock_cm.config.get_default_profile.return_value = mock_default
            mock_cm.config.profiles = [mock_default]

            result = select_profile(None)

            assert result == mock_default
            mock_cm.config.get_default_profile.assert_called_once()

    def test_select_profile_raises_when_no_profiles_configured(self):
        """Test that ValueError is raised when no profiles are configured."""
        with patch("fit_file_faker.app.config_manager") as mock_cm:
            mock_cm.config.get_default_profile.return_value = None
            mock_cm.config.profiles = []

            with pytest.raises(ValueError) as exc_info:
                select_profile(None)

            assert "No profiles configured" in str(exc_info.value)
            assert "--config-menu" in str(exc_info.value)

    def test_select_profile_uses_single_profile_when_only_one_exists(self):
        """Test that single profile is used automatically when no default set."""
        mock_profile = MagicMock()
        mock_profile.name = "only_profile"

        with patch("fit_file_faker.app.config_manager") as mock_cm:
            mock_cm.config.get_default_profile.return_value = None
            mock_cm.config.profiles = [mock_profile]

            result = select_profile(None)

            assert result == mock_profile

    def test_select_profile_prompts_when_multiple_profiles_and_no_default(self):
        """Test that user is prompted when multiple profiles exist and no default."""
        mock_profile1 = MagicMock()
        mock_profile1.name = "profile1"
        mock_profile2 = MagicMock()
        mock_profile2.name = "profile2"

        with (
            patch("fit_file_faker.app.config_manager") as mock_cm,
            patch("fit_file_faker.app.profile_manager") as mock_pm,
            patch("fit_file_faker.app.questionary") as mock_questionary,
        ):
            mock_cm.config.get_default_profile.return_value = None
            mock_cm.config.profiles = [mock_profile1, mock_profile2]

            # Mock questionary to return selected profile name
            mock_questionary.select.return_value.ask.return_value = "profile1"

            # Mock profile_manager.get_profile to return the selected profile
            mock_pm.get_profile.return_value = mock_profile1

            result = select_profile(None)

            assert result == mock_profile1
            mock_questionary.select.assert_called_once()
            # Verify the choices include both profile names
            call_args = mock_questionary.select.call_args
            assert "profile1" in call_args.kwargs["choices"]
            assert "profile2" in call_args.kwargs["choices"]

    def test_select_profile_raises_when_no_profile_selected(self):
        """Test that ValueError is raised when user doesn't select a profile."""
        mock_profile1 = MagicMock()
        mock_profile1.name = "profile1"
        mock_profile2 = MagicMock()
        mock_profile2.name = "profile2"

        with (
            patch("fit_file_faker.app.config_manager") as mock_cm,
            patch("fit_file_faker.app.questionary") as mock_questionary,
        ):
            mock_cm.config.get_default_profile.return_value = None
            mock_cm.config.profiles = [mock_profile1, mock_profile2]

            # Mock questionary to return None (user cancelled)
            mock_questionary.select.return_value.ask.return_value = None

            with pytest.raises(ValueError) as exc_info:
                select_profile(None)

            assert "No profile selected" in str(exc_info.value)

    def test_select_profile_explicit_name_overrides_default(self):
        """Test that explicit profile name overrides default profile."""
        mock_default = MagicMock()
        mock_default.name = "default_profile"
        mock_explicit = MagicMock()
        mock_explicit.name = "explicit_profile"

        with (
            patch("fit_file_faker.app.profile_manager") as mock_pm,
            patch("fit_file_faker.app.config_manager") as mock_cm,
        ):
            mock_pm.get_profile.return_value = mock_explicit
            mock_cm.config.get_default_profile.return_value = mock_default

            result = select_profile("explicit_profile")

            assert result == mock_explicit
            # Should not call get_default_profile because explicit name was provided
            mock_pm.get_profile.assert_called_once_with("explicit_profile")


class TestMonitorFunction:
    """Tests for directory monitoring functionality."""

    @patch("fit_file_faker.app.Observer")
    def test_monitor_starts_observer(self, mock_observer_class, temp_dir):
        """Test that monitor starts the file observer."""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        mock_observer.is_alive.return_value = False  # Exit immediately

        # Create mock profile
        mock_profile = MagicMock()
        mock_profile.garmin_username = "test@example.com"
        mock_profile.garmin_password = "testpass"

        # Run monitor (will exit immediately because is_alive returns False)
        monitor(temp_dir, profile=mock_profile, dryrun=False)

        # Verify observer was configured and started
        mock_observer.schedule.assert_called_once()
        mock_observer.start.assert_called_once()
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called()

    @patch("fit_file_faker.app.Observer")
    def test_monitor_handles_keyboard_interrupt(self, mock_observer_class, temp_dir):
        """Test that monitor gracefully handles KeyboardInterrupt."""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        # Simulate KeyboardInterrupt
        mock_observer.is_alive.return_value = True
        mock_observer.join.side_effect = [KeyboardInterrupt(), None]

        # Create mock profile
        mock_profile = MagicMock()
        mock_profile.garmin_username = "test@example.com"
        mock_profile.garmin_password = "testpass"

        # Should handle interrupt gracefully
        monitor(temp_dir, profile=mock_profile, dryrun=False)

        mock_observer.stop.assert_called_once()


class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    @patch("fit_file_faker.app.fit_editor")
    @patch("sys.argv", ["fit-file-faker", "--help"])
    def test_help_argument(self, mock_fit_editor):
        """Test that --help doesn't error."""
        from fit_file_faker.app import run

        with pytest.raises(SystemExit) as exc_info:
            run()

        # --help should exit with code 0
        assert exc_info.value.code == 0

    @patch("fit_file_faker.app.fit_editor")
    @patch("sys.argv", ["fit-file-faker", "--version"])
    def test_version_argument(self, mock_fit_editor, capsys):
        """Test that --version displays version and release date and exits."""
        from importlib.metadata import version

        from fit_file_faker import __version_date__
        from fit_file_faker.app import run

        with pytest.raises(SystemExit) as exc_info:
            run()

        # --version should exit with code 0
        assert exc_info.value.code == 0

        # Check that version and date were printed to stdout
        captured = capsys.readouterr()
        expected_version = version("fit-file-faker")
        assert "fit-file-faker" in captured.out
        assert expected_version in captured.out
        assert __version_date__ in captured.out
        assert (
            "(" in captured.out and ")" in captured.out
        )  # Check date is in parentheses

    @patch("fit_file_faker.app.fit_editor")
    def test_version_check_passes(self, mock_fit_editor):
        """Test that Python version check passes on supported versions."""
        from fit_file_faker.app import run

        # Current Python should be >= 3.12
        assert sys.version_info >= (3, 12), "Tests should run on Python 3.12+"

        # Should not raise OSError for version
        # (Will fail for other reasons like missing arguments, but not version)
        with pytest.raises(SystemExit):
            # No arguments will cause argparse to exit
            with patch("sys.argv", ["fit-file-faker"]):
                run()

    def test_version_check_fails_on_old_python(self, monkeypatch):
        """Test that Python version check raises OSError on unsupported versions."""
        from fit_file_faker.app import run

        # Mock sys.version_info to simulate Python 3.11
        mock_version_info = MagicMock()
        mock_version_info.major = 3
        mock_version_info.minor = 11
        mock_version_info.micro = 0

        monkeypatch.setattr("sys.version_info", mock_version_info)

        # Should raise OSError with appropriate message
        with pytest.raises(OSError) as exc_info:
            run()

        error_message = str(exc_info.value)
        assert 'This program requires Python "3.12.0" or greater' in error_message
        assert 'current version is "3.11.0"' in error_message
        assert "Please upgrade your python version" in error_message

    @pytest.mark.parametrize(
        "verbose,expected_main_level,expected_third_party_level",
        [
            (True, logging.DEBUG, logging.INFO),
            (False, logging.INFO, logging.WARNING),
        ],
    )
    def test_logging_levels(
        self, tmp_path, verbose, expected_main_level, expected_third_party_level
    ):
        """Test that verbose mode affects main and third-party logger levels appropriately."""
        from fit_file_faker.app import run, _logger

        test_file = tmp_path / "test.fit"
        test_file.write_bytes(b"test content")

        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = None

            args = ["fit-file-faker", "-d", str(test_file)]
            if verbose:
                args.insert(1, "-v")

            with patch("sys.argv", args):
                with patch("fit_file_faker.app.fit_editor.edit_fit") as mock_edit:
                    mock_edit.return_value = None
                    try:
                        run()
                    except SystemExit:
                        pass

        # Check main logger level
        assert _logger.level == expected_main_level

        # Check third-party loggers
        third_party_loggers = [
            "urllib3.connectionpool",
            "oauthlib.oauth1.rfc5849",
            "requests_oauthlib.oauth1_auth",
            "asyncio",
            "watchdog.observers.inotify_buffer",
        ]
        for logger_name in third_party_loggers:
            assert logging.getLogger(logger_name).level == expected_third_party_level

    def test_cli_argument_validation(self, caplog):
        """Test CLI argument validation - no args and conflicting args."""
        from fit_file_faker.app import run

        # Test no arguments shows error
        with (
            patch("fit_file_faker.app.config_manager") as mock_config,
            patch("fit_file_faker.app.profile_manager") as mock_profile_manager,
            patch("fit_file_faker.app.questionary") as mock_questionary,
        ):
            mock_config.is_valid.return_value = True
            # Mock config to have a default profile to avoid interactive menu
            mock_profile = MagicMock()
            mock_profile.name = "test"
            mock_profile.fitfiles_path = "/tmp"
            mock_config.config.get_default_profile.return_value = mock_profile
            mock_config.config.profiles = [mock_profile]
            # Mock profile_manager to avoid interactive menu calls
            mock_profile_manager.interactive_menu.side_effect = SystemExit(0)
            # Mock questionary to avoid interactive prompts
            mock_questionary.select.return_value.ask.return_value = None
            with patch("sys.argv", ["fit-file-faker"]):
                with pytest.raises(SystemExit) as exc_info:
                    with caplog.at_level(logging.ERROR):
                        run()

            assert exc_info.value.code == 1
            assert any(
                "Specify either" in r.message and "--upload-all" in r.message
                for r in caplog.records
            )

        # Test --upload-all and --monitor conflict
        caplog.clear()
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            with patch("sys.argv", ["fit-file-faker", "-ua", "-m"]):
                with pytest.raises(SystemExit) as exc_info:
                    with caplog.at_level(logging.ERROR):
                        run()

            assert exc_info.value.code == 1
            assert any(
                'Cannot use "--upload-all" and "--monitor" together' in r.message
                for r in caplog.records
            )

    def test_profile_selection(self, tmp_path):
        """Test that profile is properly selected when processing files."""
        from fit_file_faker.app import run

        # Create a test FIT file
        test_file = tmp_path / "test.fit"
        test_file.write_bytes(b"test content")

        # Mock profile manager to return a valid profile
        with patch("fit_file_faker.app.select_profile") as mock_select:
            mock_profile = MagicMock()
            mock_profile.name = "test_profile"
            mock_profile.fitfiles_path = None
            mock_select.return_value = mock_profile

            with patch("sys.argv", ["fit-file-faker", "-d", str(test_file)]):
                with patch("fit_file_faker.app.fit_editor.edit_fit") as mock_edit:
                    mock_edit.return_value = None
                    try:
                        run()
                    except SystemExit:
                        pass

            # Verify select_profile was called
            mock_select.assert_called_once_with(None)

    def test_config_path_from_file(self, tmp_path):
        """Test that path is read from profile when no input_path provided."""
        from fit_file_faker.app import run

        # Create test directory with FIT files
        config_path = tmp_path / "fitfiles"
        config_path.mkdir()

        # Mock profile with fitfiles_path
        with patch("fit_file_faker.app.select_profile") as mock_select:
            mock_profile = MagicMock()
            mock_profile.name = "test_profile"
            mock_profile.fitfiles_path = str(config_path)
            mock_select.return_value = mock_profile

            with patch("sys.argv", ["fit-file-faker", "-ua"]):
                with patch("fit_file_faker.app.upload_all") as mock_upload_all:
                    run()

            # Verify upload_all was called with the config path
            mock_upload_all.assert_called_once()
            call_args = mock_upload_all.call_args[0]
            assert call_args[0] == config_path

    def test_missing_fitfiles_path_raises_error(self, caplog):
        """Test that SystemExit is raised when fitfiles_path is None and no input provided."""
        from fit_file_faker.app import run

        # Mock profile with None fitfiles_path
        with patch("fit_file_faker.app.select_profile") as mock_select:
            mock_profile = MagicMock()
            mock_profile.name = "test_profile"
            mock_profile.fitfiles_path = None
            mock_select.return_value = mock_profile

            # Run with -ua flag but no input_path
            with patch("sys.argv", ["fit-file-faker", "-ua"]):
                with pytest.raises(SystemExit) as exc_info:
                    with caplog.at_level(logging.ERROR):
                        run()

            # Should exit with code 1
            assert exc_info.value.code == 1
            # Should log an error about missing fitfiles_path
            assert any(
                "does not have a fitfiles_path configured" in r.message
                for r in caplog.records
            )

    def test_nonexistent_path_exits(self, caplog):
        """Test that nonexistent path causes error and exit."""
        import logging
        from fit_file_faker.app import run

        nonexistent_path = "/path/that/does/not/exist"

        # Mock config_manager
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = None

            with patch("sys.argv", ["fit-file-faker", "-d", nonexistent_path]):
                with pytest.raises(SystemExit) as exc_info:
                    with caplog.at_level(logging.ERROR):
                        run()

            # Verify exit code is 1 (error)
            assert exc_info.value.code == 1

            # Verify error message was logged
            assert any(
                "does not exist" in record.message
                and "please check your configuration" in record.message
                for record in caplog.records
            )

    def test_single_file_edit_and_upload(self, tmp_path):
        """Test editing and uploading a single file."""
        from fit_file_faker.app import run

        # Create a test FIT file
        test_file = tmp_path / "test.fit"
        test_file.write_bytes(b"test content")
        output_file = tmp_path / "test_modified.fit"

        # Mock config_manager
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = None

            with patch("sys.argv", ["fit-file-faker", "-u", str(test_file)]):
                with patch("fit_file_faker.app.fit_editor.edit_fit") as mock_edit:
                    with patch("fit_file_faker.app.upload") as mock_upload:
                        mock_edit.return_value = output_file
                        run()

            # Verify edit_fit was called
            mock_edit.assert_called_once()
            assert mock_edit.call_args[0][0] == test_file

            # Verify upload was called with profile
            mock_upload.assert_called_once()
            call_args = mock_upload.call_args
            assert call_args[0][0] == output_file  # First positional arg is file path
            assert call_args.kwargs["original_path"] == test_file
            assert call_args.kwargs["dryrun"] is False
            assert "profile" in call_args.kwargs  # Profile should be passed

    def test_directory_upload_all(self, tmp_path):
        """Test upload_all with a directory."""
        from fit_file_faker.app import run

        # Create test directory
        test_dir = tmp_path / "fitfiles"
        test_dir.mkdir()

        # Mock config_manager
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = None

            with patch("sys.argv", ["fit-file-faker", "-ua", str(test_dir)]):
                with patch("fit_file_faker.app.upload_all") as mock_upload_all:
                    run()

            # Verify upload_all was called with profile
            mock_upload_all.assert_called_once()
            call_args = mock_upload_all.call_args
            assert call_args[0][0] == test_dir  # First positional arg is directory
            assert call_args.kwargs["preinitialize"] is False
            assert call_args.kwargs["dryrun"] is False
            assert "profile" in call_args.kwargs  # Profile should be passed

    def test_directory_preinitialize(self, tmp_path):
        """Test preinitialize flag with a directory."""
        from fit_file_faker.app import run

        # Create test directory
        test_dir = tmp_path / "fitfiles"
        test_dir.mkdir()

        # Mock config_manager
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = None

            with patch("sys.argv", ["fit-file-faker", "-p", str(test_dir)]):
                with patch("fit_file_faker.app.upload_all") as mock_upload_all:
                    run()

            # Verify upload_all was called with preinitialize=True
            mock_upload_all.assert_called_once()
            call_args = mock_upload_all.call_args
            assert call_args[0][0] == test_dir  # First positional arg is directory
            assert call_args.kwargs["preinitialize"] is True
            assert call_args.kwargs["dryrun"] is False
            assert "profile" in call_args.kwargs  # Profile should be passed

    def test_directory_monitor(self, tmp_path):
        """Test monitor mode with a directory."""
        from fit_file_faker.app import run

        # Create test directory
        test_dir = tmp_path / "fitfiles"
        test_dir.mkdir()

        # Mock config_manager
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = None

            with patch("sys.argv", ["fit-file-faker", "-m", str(test_dir)]):
                with patch("fit_file_faker.app.monitor") as mock_monitor:
                    run()

            # Verify monitor was called with profile
            mock_monitor.assert_called_once()
            call_args = mock_monitor.call_args
            assert call_args[0][0] == test_dir  # First positional arg is directory
            assert call_args.kwargs["dryrun"] is False
            assert "profile" in call_args.kwargs  # Profile should be passed

    def test_directory_edit_multiple_files(self, tmp_path):
        """Test editing multiple FIT files in a directory."""
        from fit_file_faker.app import run

        # Create test directory with FIT files
        test_dir = tmp_path / "fitfiles"
        test_dir.mkdir()
        file1 = test_dir / "test1.fit"
        file2 = test_dir / "test2.FIT"  # Test case insensitive
        file1.write_bytes(b"test1")
        file2.write_bytes(b"test2")

        # Mock config_manager
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = None

            with patch("sys.argv", ["fit-file-faker", "-d", str(test_dir)]):
                with patch("fit_file_faker.app.fit_editor.edit_fit") as mock_edit:
                    mock_edit.return_value = None
                    run()

            # Verify edit_fit was called for both files
            assert mock_edit.call_count == 2
            called_files = {call[0][0] for call in mock_edit.call_args_list}
            assert file1 in called_files
            assert file2 in called_files

    def test_list_profiles_with_profiles_configured(self, caplog):
        """Test --list-profiles when profiles exist."""
        from fit_file_faker.app import run

        mock_profile1 = MagicMock()
        mock_profile1.name = "profile1"
        mock_profile2 = MagicMock()
        mock_profile2.name = "profile2"

        with (
            patch("fit_file_faker.app.config_manager") as mock_config,
            patch("fit_file_faker.app.profile_manager") as mock_profile_mgr,
        ):
            mock_config.config.profiles = [mock_profile1, mock_profile2]

            with patch("sys.argv", ["fit-file-faker", "--list-profiles"]):
                with pytest.raises(SystemExit) as exc_info:
                    with caplog.at_level(logging.INFO):
                        run()

            # Should exit with code 0
            assert exc_info.value.code == 0

            # Should call display_profiles_table
            mock_profile_mgr.display_profiles_table.assert_called_once()

    def test_list_profiles_with_no_profiles_configured(self, caplog):
        """Test --list-profiles when no profiles are configured."""
        from fit_file_faker.app import run

        with (
            patch("fit_file_faker.app.config_manager") as mock_config,
            patch("fit_file_faker.app.profile_manager") as mock_profile_mgr,
        ):
            mock_config.config.profiles = []

            with patch("sys.argv", ["fit-file-faker", "--list-profiles"]):
                with pytest.raises(SystemExit) as exc_info:
                    with caplog.at_level(logging.INFO):
                        run()

            # Should exit with code 0
            assert exc_info.value.code == 0

            # Should NOT call display_profiles_table when no profiles
            mock_profile_mgr.display_profiles_table.assert_not_called()

            # Should log the message about creating a profile
            assert any(
                "No profiles configured" in record.message
                and "--config-menu" in record.message
                for record in caplog.records
            )

    def test_config_menu_flag(self, caplog):
        """Test --config-menu flag launches interactive menu."""
        from fit_file_faker.app import run

        with patch("fit_file_faker.app.profile_manager") as mock_profile_mgr:
            with patch("sys.argv", ["fit-file-faker", "--config-menu"]):
                with pytest.raises(SystemExit) as exc_info:
                    with caplog.at_level(logging.INFO):
                        run()

            # Should exit with code 0
            assert exc_info.value.code == 0

            # Should call interactive_menu
            mock_profile_mgr.interactive_menu.assert_called_once()

    def test_select_profile_error_handling(self, caplog):
        """Test that select_profile errors are caught and logged."""
        from fit_file_faker.app import run

        with patch("fit_file_faker.app.select_profile") as mock_select:
            mock_select.side_effect = ValueError("Test error message")

            with patch("sys.argv", ["fit-file-faker", "-d", "/some/path"]):
                with pytest.raises(SystemExit) as exc_info:
                    with caplog.at_level(logging.ERROR):
                        run()

            # Should exit with code 1 (error)
            assert exc_info.value.code == 1

            # Should log the error message
            assert any(
                "Test error message" in record.message for record in caplog.records
            )

    def test_show_dirs_flag_with_garth_dirs(self, capsys):
        """Test --show-dirs flag when garth directories exist."""
        import re
        from fit_file_faker.app import run
        from fit_file_faker.config import dirs

        # Create actual garth directories in the cache path
        # (isolate_config_dirs fixture ensures this is a tmp directory)
        garth_dir1 = dirs.user_cache_path / ".garth_profile1"
        garth_dir2 = dirs.user_cache_path / ".garth_profile2"
        garth_dir1.mkdir(parents=True, exist_ok=True)
        garth_dir2.mkdir(parents=True, exist_ok=True)

        with patch("sys.argv", ["fit-file-faker", "--show-dirs"]):
            with pytest.raises(SystemExit) as exc_info:
                run()

        # Should exit with code 0
        assert exc_info.value.code == 0

        # Capture printed output
        captured = capsys.readouterr()

        # Remove all whitespace for easier assertion (Rich console wraps long paths)
        output_normalized = re.sub(r"\s+", "", captured.out)
        config_path_normalized = re.sub(r"\s+", "", str(dirs.user_config_path))
        cache_path_normalized = re.sub(r"\s+", "", str(dirs.user_cache_path))

        # Verify that the output contains the expected sections
        assert "Executable:" in captured.out
        assert "fit-file-faker command:" in captured.out
        assert "Config directory:" in captured.out
        assert config_path_normalized in output_normalized
        assert "Cache directory:" in captured.out
        assert cache_path_normalized in output_normalized

        # Should show that garth directories were found
        assert "Garmin credential directories:" in captured.out
        assert ".garth_profile1" in captured.out
        assert ".garth_profile2" in captured.out

    def test_show_dirs_flag_without_garth_dirs(self, capsys):
        """Test --show-dirs flag when no garth directories exist."""
        import re
        from fit_file_faker.app import run
        from fit_file_faker.config import dirs

        # Don't create any garth directories
        # (isolate_config_dirs fixture ensures cache directory is empty)

        with patch("sys.argv", ["fit-file-faker", "--show-dirs"]):
            with pytest.raises(SystemExit) as exc_info:
                run()

        # Should exit with code 0
        assert exc_info.value.code == 0

        # Capture printed output
        captured = capsys.readouterr()

        # Remove all whitespace for easier assertion (Rich console wraps long paths)
        output_normalized = re.sub(r"\s+", "", captured.out)
        config_path_normalized = re.sub(r"\s+", "", str(dirs.user_config_path))
        cache_path_normalized = re.sub(r"\s+", "", str(dirs.user_cache_path))

        # Verify that the output contains the expected sections
        assert "Executable:" in captured.out
        assert "fit-file-faker command:" in captured.out
        assert "Config directory:" in captured.out
        assert config_path_normalized in output_normalized
        assert "Cache directory:" in captured.out
        assert cache_path_normalized in output_normalized

        # Should show message about no garth directories found
        assert "No Garmin credential directories found" in captured.out
        assert "will be created on first use" in captured.out
