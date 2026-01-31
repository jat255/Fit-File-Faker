# FIT File Faker

<div align="center">
  <img src="docs/assets/logo.svg" alt="Fit File Faker Logo" width="400" />

  [![Documentation](https://img.shields.io/badge/-documentation-blue?style=flat-square&logo=Read%20the%20Docs&logoColor=white&labelColor=555&color=blue)](https://jat255.github.io/Fit-File-Faker/)
  [![PyPI](https://img.shields.io/pypi/v/fit-file-faker?style=flat-square)](https://pypi.org/project/fit-file-faker/)
  [![License](https://img.shields.io/github/license/jat255/Fit-File-Faker?style=flat-square)](LICENSE)
  [![Tests](https://img.shields.io/github/actions/workflow/status/jat255/Fit-File-Faker/test.yml?branch=main&style=flat-square&label=tests)](https://github.com/jat255/Fit-File-Faker/actions/workflows/test.yml)
  [![Codecov](https://img.shields.io/codecov/c/github/jat255/fit-file-faker/refactor?style=flat-square&logo=codecov)](https://codecov.io/gh/jat255/fit-file-faker)
  [![Ko-fi](https://img.shields.io/badge/-Donate-ff5e5b?style=flat-square&logo=ko-fi&logoColor=white&labelColor=555)](https://ko-fi.com/josh851356)
</div>

A Python tool to modify [FIT](https://developer.garmin.com/fit/overview/) files and upload them to [Garmin Connect](https://connect.garmin.com/).

> **☕ Enjoying this tool?** If FIT File Faker saves you time or enhances your training workflow, consider [buying me a coffee](https://ko-fi.com/josh851356). Your support helps maintain and improve this project!

**Edit** FIT files to appear as if they came from a Garmin device (70+ modern devices supported, including Edge 1050, Fenix 8, Forerunner 965), enabling Training Effect calculations and other Garmin features for activities from platforms like:
- [TrainingPeaks Virtual](https://www.trainingpeaks.com/virtual/)
- [Zwift](https://www.zwift.com/)
- [MyWhoosh](https://mywhoosh.com/)
- [Hammerhead Karoo](https://www.hammerhead.io/)
- [COROS](https://coros.com/)

**Upload** edited files directly to Garmin Connect, or run in **monitor mode** for automatic uploads.

## 📖 Documentation

For comprehensive documentation, visit: **https://jat255.github.io/Fit-File-Faker/**

Quick references:
- [User Guide & Installation](https://jat255.github.io/Fit-File-Faker/)
- [Developer Guide & Testing](https://jat255.github.io/Fit-File-Faker/developer-guide/)
- [Changelog](https://jat255.github.io/Fit-File-Faker/changelog/)

## ⚡ Quick Start

<div align="center">
  <img src="docs/vhs_gifs/features.gif" alt="FIT File Faker Features Demo" width="800" />
</div>

### Install
```bash
# Using uv (recommended)
uv tool install fit-file-faker

# Or using pipx
pipx install fit-file-faker

# Or using pip
pip install fit-file-faker
```

### Configure
```bash
# Interactive profile management menu
fit-file-faker --config-menu
```

<div align="center">
  <img src="docs/vhs_gifs/config_new.gif" alt="Creating a new profile" width="800" />
  <p><em>Creating a new profile with the interactive menu</em></p>
</div>

### Edit & Upload
```bash
# Edit and upload a single FIT file
fit-file-faker -u path/to/file.fit

# Upload all files in configured directory
fit-file-faker -ua

# Monitor directory for new files
fit-file-faker -m
```

See the [documentation](https://jat255.github.io/Fit-File-Faker/) for detailed usage instructions.

## 🔐 Multi-Profile Support

FIT File Faker supports multiple profiles, allowing you to manage different Garmin accounts and trainer apps:

```bash
# Launch interactive profile management menu
fit-file-faker --config-menu

# List all profiles
fit-file-faker --list-profiles

# Show directories used for configuration and cache
fit-file-faker --show-dirs

# Use a specific profile
fit-file-faker --profile my-profile -ua

# Monitor with a specific profile
fit-file-faker --profile zwift -m
```

<div align="center">
  <img src="docs/vhs_gifs/config_edit.gif" alt="Editing a profile" width="800" />
  <p><em>Editing an existing profile configuration</em></p>
</div>

Each profile can have:
- **Different Garmin accounts** (credentials are isolated per profile)
- **Different trainer apps** (TrainingPeaks Virtual, Zwift, MyWhoosh)
- **Different FIT file directories**
- **Different Garmin device simulation** (Edge 830, Edge 1030, Tacx, etc.)

Example workflow for multiple accounts:
```bash
# Create profiles
fit-file-faker --config-menu
# Select "Create new profile" and follow prompts for each trainer app

# Daily usage
fit-file-faker --profile tpv -ua      # Upload TPV files to work account
fit-file-faker --profile zwift -ua    # Upload Zwift files to personal account
```

See the [profiles guide](https://jat255.github.io/Fit-File-Faker/profiles/) for comprehensive multi-profile documentation.

## ⚠️ Important: Device Serial Numbers

For Garmin Connect to correctly recognize an activity as coming from a specific device (which affects Training Status, challenges, badges, and other features), **both the device ID and serial number must match a valid Garmin device**.

### Why This Matters

Garmin Connect uses internal validation to ensure that:
- The device product ID (e.g., Edge 1050, Fenix 8) is legitimate
- The serial number is valid for that specific device type
- The combination of device ID + serial number represents a real device

If the serial number doesn't match the device type, Garmin Connect may:
- Not apply Training Effect calculations correctly
- Not count the activity toward challenges or badges
- Not update Training Status or training load metrics
- Display the activity with incorrect device information

### Recommendations

**Option 1: Use Your Real Garmin Device Serial Number (Recommended)**

If you own a Garmin device and want your activities to count properly for all Garmin Connect features:

1. Find your device's serial number (Unit ID):
   - On the device: Settings → About → Copyright Info → Unit ID
   - On Garmin Connect: Device settings page
   - On the device packaging or receipt
2. During profile setup, choose to customize the serial number
3. Enter your actual device's serial number
4. Select the matching device model (e.g., if you have an Edge 830, select Edge 830)

**Option 2: Accept Limited Functionality**

If you don't own a Garmin device or don't need full Garmin Connect integration:

- The tool will generate a random serial number automatically
- Activities will upload successfully to Garmin Connect
- Basic activity data (distance, time, power, heart rate) will display correctly
- However, advanced features may not work as expected

### What We Don't Know

The mapping of serial number ranges to specific device models is proprietary Garmin information and not publicly documented. This means:
- We cannot automatically generate valid serial numbers for specific devices
- Random serial numbers may or may not be accepted by Garmin Connect
- The only guaranteed way to ensure full functionality is to use a real device's serial number

### Finding Your Serial Number

When you customize the serial number during profile creation, the tool will show you where to find it:
```bash
fit-file-faker --config-menu
# Select "Create new profile" → customize device → customize serial number
```

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

```bash
git clone https://github.com/jat255/Fit-File-Faker.git
cd Fit-File-Faker
uv sync
uv run pre-commit install
```

Run tests and checks:
```bash
python3 run_tests.py          # Run tests with coverage
python3 run_tests.py --html   # Generate HTML coverage report
ruff check . && ruff format . # Lint and format code
```

See the [developer guide](https://jat255.github.io/Fit-File-Faker/developer-guide/) for much more detail on development practices and expectations.

## 👥 Contributors

- [jat255](https://github.com/jat255) — Primary author
- [benjmarshall](https://github.com/benjmarshall) — Bug fixes, monitor mode
- [Kellett](https://github.com/Kellett) — Zwift support
- [lrybak](https://github.com/lrybak) — Hammerhead Karoo support
- [dermarzel](https://github.com/dermarzel) — MyWhoosh support

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

## ⚠️ Disclaimer

This tool is provided as-is for personal use. The FIT format and Garmin Connect are registered trademarks of Garmin Ltd. This tool is not affiliated with or endorsed by Garmin or any other platform owners.

---

**Have questions or found an issue?** [Open an issue](https://github.com/jat255/Fit-File-Faker/issues) on GitHub.
