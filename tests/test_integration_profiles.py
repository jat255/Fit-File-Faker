"""
Integration tests for multi-profile end-to-end workflows.

These tests verify complete workflows including profile management,
file processing, and credential isolation across multiple profiles.
"""

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from fit_file_faker.app import get_garth_dir, upload, upload_all
from fit_file_faker.config import AppType, ConfigManager, Profile, ProfileManager


class TestMultiProfileWorkflows:
    """Integration tests for multi-profile workflows."""

    def test_create_multiple_profiles_and_switch(self):
        """Test creating multiple profiles and switching between them."""
        config_manager = ConfigManager()
        profile_manager = ProfileManager(config_manager)

        # Create TPV profile
        tpv_profile = profile_manager.create_profile(
            name="tpv",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="tpv@example.com",
            garmin_password="tpv_pass",
            fitfiles_path=Path("/tpv/files"),
        )

        # Create Zwift profile
        zwift_profile = profile_manager.create_profile(
            name="zwift",
            app_type=AppType.ZWIFT,
            garmin_username="zwift@example.com",
            garmin_password="zwift_pass",
            fitfiles_path=Path("/zwift/files"),
        )

        # Verify both profiles exist
        assert len(config_manager.config.profiles) == 2
        assert config_manager.config.get_profile("tpv") == tpv_profile
        assert config_manager.config.get_profile("zwift") == zwift_profile

        # Set default profile
        profile_manager.set_default_profile("zwift")
        assert config_manager.config.default_profile == "zwift"
        assert config_manager.config.get_default_profile() == zwift_profile

        # Switch default
        profile_manager.set_default_profile("tpv")
        assert config_manager.config.default_profile == "tpv"
        assert config_manager.config.get_default_profile() == tpv_profile

    def test_profile_specific_garth_isolation(self):
        """Test that each profile gets its own isolated garth directory."""
        profile1_dir = get_garth_dir("profile1")
        profile2_dir = get_garth_dir("profile2")

        # Verify directories are different
        assert profile1_dir != profile2_dir
        assert "profile1" in str(profile1_dir)
        assert "profile2" in str(profile2_dir)

        # Verify both directories exist
        assert profile1_dir.exists()
        assert profile2_dir.exists()

        # Test with special characters in profile name (should be sanitized)
        special_profile_dir = get_garth_dir("my profile!")
        assert special_profile_dir.exists()
        assert "my_profile_" in str(special_profile_dir)

    def test_upload_with_different_profiles(
        self, tmp_path, tpv_fit_file, mock_garth_basic
    ):
        """Test uploading the same file with different profiles."""
        mock_garth, mock_garth_exc = mock_garth_basic

        # Create two profiles
        profile1 = Profile(
            name="user1",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="user1@example.com",
            garmin_password="pass1",
            fitfiles_path=tmp_path,
        )
        profile2 = Profile(
            name="user2",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="user2@example.com",
            garmin_password="pass2",
            fitfiles_path=tmp_path,
        )

        # Mock garth module for upload function
        with patch.dict(
            "sys.modules", {"garth": mock_garth, "garth.exc": mock_garth_exc}
        ):
            # Upload with profile 1
            upload(tpv_fit_file, profile=profile1, dryrun=False)
            # Upload with profile 2
            upload(tpv_fit_file, profile=profile2, dryrun=False)

            # Verify upload was called twice
            assert mock_garth.client.upload.call_count == 2

    def test_migration_workflow(self, tmp_path):
        """Test complete migration workflow from legacy to multi-profile."""
        # Create a legacy config file (v1.2.4 format)
        config_file = tmp_path / "config" / ".config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        legacy_config = {
            "garmin_username": "legacy@example.com",
            "garmin_password": "legacy_pass",
            "fitfiles_path": "/legacy/path",
        }

        with config_file.open("w") as f:
            json.dump(legacy_config, f)

        # Load config (should auto-migrate)
        config_manager = ConfigManager()

        # Verify migration occurred
        assert len(config_manager.config.profiles) == 1
        default_profile = config_manager.config.get_default_profile()
        assert default_profile is not None
        assert default_profile.name == "default"
        assert default_profile.garmin_username == "legacy@example.com"
        assert default_profile.garmin_password == "legacy_pass"
        assert default_profile.fitfiles_path.as_posix() == "/legacy/path"
        assert default_profile.app_type == AppType.TP_VIRTUAL

        # Verify config is now in new format
        with config_file.open("r") as f:
            new_config = json.load(f)
        assert "profiles" in new_config
        assert new_config["default_profile"] == "default"

    def test_profile_crud_persistence(self):
        """Test that profile CRUD operations persist across ConfigManager instances."""
        config_manager1 = ConfigManager()
        profile_manager1 = ProfileManager(config_manager1)

        # Create a profile
        _ = profile_manager1.create_profile(
            name="persistent",
            app_type=AppType.ZWIFT,
            garmin_username="persist@example.com",
            garmin_password="persist_pass",
            fitfiles_path=Path("/persist/path"),
        )
        profile_manager1.set_default_profile("persistent")

        # Create a new ConfigManager instance (simulates restart)
        config_manager2 = ConfigManager()

        # Verify profile persisted
        assert len(config_manager2.config.profiles) == 1
        loaded_profile = config_manager2.config.get_profile("persistent")
        assert loaded_profile is not None
        assert loaded_profile.garmin_username == "persist@example.com"
        assert loaded_profile.app_type == AppType.ZWIFT
        assert config_manager2.config.default_profile == "persistent"

    def test_batch_upload_with_profile(self, tmp_path, tpv_fit_file):
        """Test batch uploading files with a specific profile."""
        # Copy test files to temp directory
        test_dir = tmp_path / "uploads"
        test_dir.mkdir()
        file1 = test_dir / "activity1.fit"
        file2 = test_dir / "activity2.fit"
        shutil.copy(tpv_fit_file, file1)
        shutil.copy(tpv_fit_file, file2)

        # Create a profile
        profile = Profile(
            name="batch",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="batch@example.com",
            garmin_password="batch_pass",
            fitfiles_path=test_dir,
        )

        # Mock fit_editor and upload functions
        with (
            patch("fit_file_faker.app.fit_editor") as mock_editor,
            patch("fit_file_faker.app.upload") as mock_upload,
        ):
            mock_editor.edit_fit.side_effect = (
                lambda f, output, dryrun=False: tmp_path / f"{f.stem}_modified.fit"
            )

            # Run batch upload
            upload_all(test_dir, profile=profile, dryrun=False)

            # Verify both files were processed
            assert mock_editor.edit_fit.call_count == 2
            assert mock_upload.call_count == 2

            # Verify uploaded files list was created
            uploaded_list = test_dir / ".uploaded_files.json"
            assert uploaded_list.exists()

            with uploaded_list.open("r") as f:
                uploaded = json.load(f)
            assert "activity1.fit" in uploaded
            assert "activity2.fit" in uploaded

    def test_profile_update_workflow(self):
        """Test updating profile credentials and path."""
        config_manager = ConfigManager()
        profile_manager = ProfileManager(config_manager)

        # Create initial profile
        _ = profile_manager.create_profile(
            name="updatable",
            app_type=AppType.MYWHOOSH,
            garmin_username="old@example.com",
            garmin_password="old_pass",
            fitfiles_path=Path("/old/path"),
        )

        # Update username
        profile_manager.update_profile("updatable", garmin_username="new@example.com")
        updated = config_manager.config.get_profile("updatable")
        assert updated.garmin_username == "new@example.com"
        assert updated.garmin_password == "old_pass"  # Unchanged

        # Update password
        profile_manager.update_profile("updatable", garmin_password="new_pass")
        updated = config_manager.config.get_profile("updatable")
        assert updated.garmin_password == "new_pass"

        # Update path
        profile_manager.update_profile("updatable", fitfiles_path=Path("/new/path"))
        updated = config_manager.config.get_profile("updatable")
        assert updated.fitfiles_path == Path("/new/path")

        # Update app_type
        profile_manager.update_profile("updatable", app_type=AppType.ZWIFT)
        updated = config_manager.config.get_profile("updatable")
        assert updated.app_type == AppType.ZWIFT

    def test_delete_profile_workflow(self):
        """Test deleting profiles and automatic default reassignment."""
        config_manager = ConfigManager()
        profile_manager = ProfileManager(config_manager)

        # Create multiple profiles
        _ = profile_manager.create_profile(
            name="profile1",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="user1@example.com",
            garmin_password="pass1",
            fitfiles_path=Path("/path1"),
        )
        _ = profile_manager.create_profile(
            name="profile2",
            app_type=AppType.ZWIFT,
            garmin_username="user2@example.com",
            garmin_password="pass2",
            fitfiles_path=Path("/path2"),
        )
        profile_manager.set_default_profile("profile1")

        # Delete the default profile
        profile_manager.delete_profile("profile1")

        # Verify profile1 is gone
        assert config_manager.config.get_profile("profile1") is None
        assert len(config_manager.config.profiles) == 1

        # Verify default was reassigned to remaining profile
        assert config_manager.config.default_profile == "profile2"

        # Cannot delete the last profile
        with pytest.raises(ValueError, match="Cannot delete the only profile"):
            profile_manager.delete_profile("profile2")

    def test_same_garmin_account_different_apps(self):
        """Test using the same Garmin account across multiple trainer apps."""
        config_manager = ConfigManager()
        profile_manager = ProfileManager(config_manager)

        # Create profiles for different apps but same Garmin account
        _ = profile_manager.create_profile(
            name="tpv_profile",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="shared@example.com",
            garmin_password="shared_pass",
            fitfiles_path=Path("/tpv"),
        )
        _ = profile_manager.create_profile(
            name="zwift_profile",
            app_type=AppType.ZWIFT,
            garmin_username="shared@example.com",
            garmin_password="shared_pass",
            fitfiles_path=Path("/zwift"),
        )
        _ = profile_manager.create_profile(
            name="mywhoosh_profile",
            app_type=AppType.MYWHOOSH,
            garmin_username="shared@example.com",
            garmin_password="shared_pass",
            fitfiles_path=Path("/mywhoosh"),
        )

        # Verify all profiles exist with correct app types
        assert len(config_manager.config.profiles) == 3
        assert (
            config_manager.config.get_profile("tpv_profile").app_type
            == AppType.TP_VIRTUAL
        )
        assert (
            config_manager.config.get_profile("zwift_profile").app_type == AppType.ZWIFT
        )
        assert (
            config_manager.config.get_profile("mywhoosh_profile").app_type
            == AppType.MYWHOOSH
        )

        # Verify they all share the same Garmin credentials
        for profile_name in ["tpv_profile", "zwift_profile", "mywhoosh_profile"]:
            profile = config_manager.config.get_profile(profile_name)
            assert profile.garmin_username == "shared@example.com"
            assert profile.garmin_password == "shared_pass"

    def test_profile_name_validation(self):
        """Test that profile names are validated properly."""
        config_manager = ConfigManager()
        profile_manager = ProfileManager(config_manager)

        # Create a profile
        _ = profile_manager.create_profile(
            name="original",
            app_type=AppType.TP_VIRTUAL,
            garmin_username="user@example.com",
            garmin_password="pass",
            fitfiles_path=Path("/path"),
        )

        # Cannot create duplicate profile
        with pytest.raises(ValueError, match='Profile "original" already exists'):
            profile_manager.create_profile(
                name="original",
                app_type=AppType.TP_VIRTUAL,
                garmin_username="user@example.com",
                garmin_password="pass",
                fitfiles_path=Path("/path"),
            )

        # Cannot rename to existing profile name
        _ = profile_manager.create_profile(
            name="another",
            app_type=AppType.ZWIFT,
            garmin_username="user2@example.com",
            garmin_password="pass2",
            fitfiles_path=Path("/path2"),
        )

        with pytest.raises(ValueError, match='Profile "original" already exists'):
            profile_manager.update_profile("another", new_name="original")
