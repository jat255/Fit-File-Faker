# Multi-Profile Configuration Guide

FIT File Faker's multi-profile system allows you to manage multiple Garmin accounts and trainer apps from a single installation, which helps if you're a multi-trainer-user household. This guide covers everything you need to know about setting up and using profiles.

## Overview

### What are Profiles?

A **profile** is a complete configuration that includes:

- **Trainer App Type**: Currently, TrainingPeaks Virtual, Zwift, MyWhoosh, or Custom
- **Garmin Account**: Username and password (credentials are isolated per profile)
- **FIT Files Directory**: Where to find and monitor FIT files
- **Profile Name**: Unique identifier for the profile

### Key Benefits

- **Multiple Garmin Accounts**: Upload to different Garmin Connect accounts
- **Multiple Trainer Apps**: Manage TPV, Zwift, MyWhoosh simultaneously
- **Isolated Credentials**: Each profile has separate Garmin authentication
- **Flexible Workflows**: Quickly switch between different setups

## Getting Started

### Launch Profile Manager

```bash
fit-file-faker --config-menu
```

This launches the interactive TUI (Text User Interface) for profile management. Example output:

```

                            📋 FIT File Faker - Profiles
┏━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name       ┃ App        ┃ Garmin User ┃ FIT Path                                 ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ TPV ⭐     │ Tp Virtual │ j123@gm...  │ ...h/TPVirtual/C123456789012345/FITFiles │
│ zwift      │ Zwift      │ j234@gm...  │ /Users/test/Documents/Zwift/Activities   │
│ mywhoosh   │ Mywhoosh   │ j123@gm...  │ ...on Support/Epic/MyWhoosh/Content/Data │
│ custom     │ Custom     │ j789@gm...  │ /Users/test/tmp                          │
└────────────┴────────────┴─────────────┴──────────────────────────────────────────┘

? What would you like to do? (Use arrow keys)
 » Create new profile
   Edit existing profile
   Delete profile
   Set default profile
   Exit
```

### List Existing Profiles

```bash
fit-file-faker --list-profiles
```

Example output:
```
📋 FIT File Faker - Profiles
┏━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name       ┃ App        ┃ Garmin User ┃ FIT Path                                 ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ TPV ⭐     │ Tp Virtual │ j123@gm...  │ ...h/TPVirtual/C123456789012345/FITFiles │
│ zwift      │ Zwift      │ j234@gm...  │ /Users/test/Documents/Zwift/Activities   │
│ mywhoosh   │ Mywhoosh   │ j123@gm...  │ ...on Support/Epic/MyWhoosh/Content/Data │
│ custom     │ Custom     │ j789@gm...  │ /Users/test/tmp                          │
└────────────┴────────────┴─────────────┴──────────────────────────────────────────┘
```

The ⭐ symbol indicates the default profile.

## Profile Management

### Create a New Profile

1. **Launch the menu**: `fit-file-faker --config-menu`
2. **Select**: "Create new profile"
3. **Follow the wizard**

#### Profile Creation Wizard (App-First Flow)

1. **Select Trainer App**: Choose from TPV, Zwift, MyWhoosh, or Custom
2. **Directory Detection**: 

     - Auto-detects the FIT files directory for your platform
     - Shows detected path with confirmation prompt
     - Option to manually override path

3. **Garmin Credentials**:

     - Enter Garmin username (email)
     - Enter Garmin password (masked input)

4. **Profile Name**:
   
     - Suggested name based on app type (e.g., "tpv", "zwift")
     - Option to customize name

5. **Confirm & Save**: Review all settings and confirm

#### Example: Creating a Zwift Profile

```
Create New Profile
? Which trainer app will this profile use? (Use arrow keys)
   TrainingPeaks Virtual
 » Zwift
   MyWhoosh
   Custom (manual path)

✓ Found Zwift directory:
  /Users/test/Documents/Zwift/Activities
? Use this directory? (Y/n)

? Enter Garmin Connect email: user@gmail.com
? Enter Garmin Connect password: ****************

? Enter profile name: zwift
```

### Edit an Existing Profile

1. **Launch the menu**: `fit-file-faker --config-menu`
2. **Select**: "Edit existing profile"
3. **Choose profile** from list
4. **Edit values as needed**: pressing "Enter" without any change will use the pre-existing value
5. **Save changes**

### Delete a Profile

1. **Launch the menu**: `fit-file-faker --config-menu`
2. **Select**: "Delete profile"
3. **Choose profile** from list
4. **Confirm deletion** (with safety checks)

**Safety Features**:

- Cannot delete the only remaining profile
- If deleting the default profile, you'll be prompted to set a new default
- Confirmation required before permanent deletion

### Set Default Profile

1. **Launch the menu**: `fit-file-faker --config-menu`
2. **Select**: "Set default profile"
3. **Choose profile** from list
4. **Confirm selection**

The default profile is used when no `--profile` argument is specified.

## Using Profiles

### Profile Selection Priority

When you run a command, FIT File Faker selects a profile in this order:

1. **Explicit selection**: `--profile <name>` or `-p <name>`
2. **Default profile**: The profile marked with ⭐
3. **First in config file**: If multiple profiles exist but no default is set
4. **Error**: If no profiles are configured

### Upload with Specific Profile

```bash
# Upload all files with TPV profile
fit-file-faker --profile TPV -ua

# Upload single file with Zwift profile
fit-file-faker --profile zwift -u ride.fit

# Monitor directory with MyWhoosh profile
fit-file-faker --profile mywhoosh -m
```

### Shortcut Alias

```bash
# -p is a shortcut for --profile
fit-file-faker -p zwift -ua
```

## 🎮 Trainer App Support

### TrainingPeaks Virtual (TPV)

**Auto-Detection Paths**:

- **macOS**: `~/TPVirtual/<user_id>/FITFiles`
- **Windows**: `~/Documents/TPVirtual/<user_id>/FITFiles`
- **Linux**: User prompt (no standard path)

**Environment Variable**:
```bash
# Override auto-detection
export TPV_DATA_PATH=/custom/path/to/FITFiles
```

### Zwift

**Auto-Detection Paths**:

- **macOS**: `~/Documents/Zwift/Activities/`
- **Windows**: `%USERPROFILE%\Documents\Zwift\Activities\`
- **Linux**: Wine/Proton paths (e.g., `~/.wine/drive_c/.../Documents/Zwift/Activities/`)

### MyWhoosh

**Auto-Detection Paths**:

- **macOS**: `~/Library/Containers/com.whoosh.whooshgame/Data/Library/Application Support/Epic/MyWhoosh/Content/Data`
- **Windows**: `~/AppData/Local/Packages/<MYWHOOSH_PREFIX>/LocalCache/Local/MyWhoosh/Content/Data`
  - Scans `Packages` directory for MyWhoosh prefixes
- **Linux**: Not officially supported (user prompt)

### Custom

For unsupported trainer apps or custom setups:

- Manual path specification
- No auto-detection
- Full flexibility for any FIT file source

## Credential Isolation

### How It Works

Each profile has its own isolated Garmin authentication:

- **Garth directories**: `/Users/test/Library/Caches/FitFileFaker/.garth_{profile_name}/`
- **Separate OAuth tokens**: No credential sharing between profiles
- **Secure storage**: Platform-specific storage via `platformdirs`

### Example Directory Structure

```
/Users/test/Library/Caches/FitFileFaker
├── .garth_tpv/          # TPV profile credentials
├── .garth_zwift/        # Zwift profile credentials
└── .garth_mywhoosh/     # MyWhoosh profile credentials
```

## Configuration File

### Location

The configuration file is stored in your platform's user config directory:

- **macOS**: `~/Library/Application Support/FitFileFaker/.config.json`
- **Windows**: `%APPDATA%\FitFileFaker\.config.json`
- **Linux**: `~/.config/FitFileFaker/.config.json`

### Format

```json
{
  "profiles": [
    {
      "name": "tpv",
      "app_type": "tp_virtual",
      "garmin_username": "user@work.com",
      "garmin_password": "secret123",
      "fitfiles_path": "/Users/test/TPVirtual/abc123/FITFiles"
    },
    {
      "name": "zwift",
      "app_type": "zwift",
      "garmin_username": "personal@gmail.com",
      "garmin_password": "secret456",
      "fitfiles_path": "/Users/test/Documents/Zwift/Activities"
    }
  ],
  "default_profile": "zwift"
}
```

### Manual Editing

⚠️ **Caution**: While you can manually edit the config file, it's recommended to use the interactive menu to avoid syntax errors.

If you do edit manually:

1. Stop any running FIT File Faker processes
2. Make a backup of the file
3. Validate JSON syntax
4. Restart the tool

## Migration from v1.2.4

### Automatic Migration

When you first run FIT File Faker v2.0.0+, your existing v1.2.4 configuration will be automatically migrated:

**Before (v1.2.4)**:
```json
{
  "garmin_username": "user@email.com",
  "garmin_password": "secret",
  "fitfiles_path": "/Users/test/TPVirtual/abc123/FITFiles"
}
```

**After (v2.0.0)**:
```json
{
  "profiles": [
    {
      "name": "default",
      "app_type": "tp_virtual",
      "garmin_username": "user@email.com",
      "garmin_password": "secret",
      "fitfiles_path": "/Users/test/TPVirtual/abc123/FITFiles"
    }
  ],
  "default_profile": "default"
}
```

### What Happens During Migration

1. **Detection**: Tool detects legacy single-profile format
2. **Backup**: Original config is backed up (if possible)
3. **Conversion**: Creates "default" profile with existing settings
4. **App Type**: Auto-detects as TP_VIRTUAL (original use case)
5. **Notification**: Logs migration information
6. **Continuity**: Tool works exactly as before

### Migration Log Message

```
[INFO] Detected legacy single-profile config, migrating to multi-profile format
[INFO] Migration complete. Your existing settings are now in the 'default' profile.
[INFO] Using default profile: default
```

## Use Case Examples

### Scenario 1: Multiple Trainer Apps, Single Garmin Account

**Setup**:
```bash
fit-file-faker --config-menu
# Create "tpv" profile → Select TPV → Auto-detect → Enter Garmin creds
# Create "zwift" profile → Select Zwift → Auto-detect → Enter same Garmin creds
```

**Daily Usage**:
```bash
# Upload TPV rides
fit-file-faker -p tpv -ua

# Upload Zwift rides
fit-file-faker -p zwift -ua

# Monitor Zwift directory
fit-file-faker -p zwift -m
```

### Scenario 2: Multiple Garmin Accounts

**Setup**:
```bash
fit-file-faker --config-menu
# Create "jim" profile → Select TPV → jim@gmail.com
# Create "jenny" profile → Select TPV → jenny@gmail.com
```

**Daily Usage**:
```bash
# Upload to Jim's account
fit-file-faker -p jim -u ride.fit

# Upload to Jenny's account
fit-file-faker -p jenny -u ride.fit
```

### Scenario 3: Family Sharing

**Setup**:
```bash
fit-file-faker --config-menu
# Create "dad" profile → Zwift → dad@gmail.com
# Create "mom" profile → TPV → mom@gmail.com
# Create "kid" profile → MyWhoosh → kid@gmail.com
```

**Daily Usage**:
```bash
# Each family member uses their profile
fit-file-faker -p dad -ua
fit-file-faker -p mom -ua
fit-file-faker -p kid -ua
```

## 🔧 Troubleshooting

### Common Issues

- **Issue**: "Profile not found" error
    - **Solution**: Check profile name spelling with `--list-profiles`

- **Issue**: Can't delete the only profile
    - **Solution**: Create a new profile first, then delete the old one

- **Issue**: Auto-detection fails
    - **Solution**: Use Custom app type and manually specify path

- **Issue**: Garmin credentials not working
    - **Solution**: Edit the profile and re-enter credentials

### Debugging

```bash
# Verbose mode shows detailed profile selection
fit-file-faker -v --profile tpv -u ride.fit

# Check which profile is being used
fit-file-faker --list-profiles
```

## Security

### Credential Safety

- **Credential storage**: Garmin credentials are stored via `platformdirs`, but in plain text, so please protect these files
- **Isolated profiles**: Each profile has separate credential storage
- **No plaintext logging**: Passwords are never logged or displayed
- **Secure transmission**: OAuth tokens use HTTPS for Garmin Connect API

### Best Practices

- Use different passwords for different Garmin accounts
- Regularly update your Garmin Connect password
- Don't share your config file
- Use profile-specific credentials, not shared accounts

## 🔗 Related Documentation

- [Main User Guide](index.md)
- [Developer Guide](developer-guide.md)
- [Changelog](changelog.md)
- [API Reference](api.md)

## 📋 Summary

FIT File Faker's multi-profile system provides:

- ✅ Multiple Garmin accounts with isolated credentials
- ✅ Support for TPV, Zwift, MyWhoosh with auto-detection
- ✅ Interactive TUI for easy profile management
- ✅ Profile-specific monitoring and uploads
- ✅ Automatic migration from single-profile configs
- ✅ Extensible architecture for new trainer apps

The system is designed to be intuitive for beginners while powerful enough for advanced users managing complex multi-account workflows.
