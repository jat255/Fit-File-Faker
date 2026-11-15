# Changelog

All notable changes to FIT File Faker are documented here.

This changelog is automatically generated from git commit messages using [git-cliff](https://git-cliff.org/).
See our [release history](https://github.com/jat255/Fit-File-Faker/releases) on GitHub for downloadable releases.

## [2.3.0](https://github.com/jat255/fit-file-faker/releases/tag/v2.3.0) - (2026-11-15)

### Features

- review release notes before publication ([004d03a](https://github.com/jat255/Fit-File-Faker/commit/004d03a42650b43d4f2e714cdb11eff2b5eb08ca))

- complete and monitor GitHub releases ([971b423](https://github.com/jat255/Fit-File-Faker/commit/971b42365770eb097dd35a9d4774bc831272ae97))

- add release workflow skill ([e878fc0](https://github.com/jat255/Fit-File-Faker/commit/e878fc09dc9fdd8a385cc7d2ac09156eb07f2d99))

- add object with name and hash to .uploaded_files.json ([4d33848](https://github.com/jat255/Fit-File-Faker/commit/4d33848e61c2ffebe29cdd135c5586c62024ae3d))

- support Forerunner 970 device simulation ([#91](https://github.com/jat255/fit-file-faker/issues/91)) ([37dbef7](https://github.com/jat255/Fit-File-Faker/commit/37dbef7c81e69c6f46c741754d15fbc8517d5803))


### Bug Fixes

- allow GitHub merge commits in release validation ([edc08bf](https://github.com/jat255/Fit-File-Faker/commit/edc08bf83d751303c54d38c8f40e4a4537f8a025))

- preserve upload tracking across file changes ([42cc9bb](https://github.com/jat255/Fit-File-Faker/commit/42cc9bb46d57bd973881b1762e770eeba6fbaffe))

- prevent missed activities during upload tracking ([43fa499](https://github.com/jat255/Fit-File-Faker/commit/43fa499ee585c7274abfb93e5626996fc180d7cd))

- preserve upload tracking across hash migration ([f39df59](https://github.com/jat255/Fit-File-Faker/commit/f39df5911da8455dbf2d9c18def2824119e8fe99))

- add file hash to .uploaded_files.json ([c87ed55](https://github.com/jat255/Fit-File-Faker/commit/c87ed55e1600299dced8f5f80c14dd40d1d8322d))

- exclude external sensors from creator detection ([709210c](https://github.com/jat255/Fit-File-Faker/commit/709210c53ce326ee7a1d04bc643e282011638785))

- retain custom device data in the identity stack ([f827d57](https://github.com/jat255/Fit-File-Faker/commit/f827d57a217cffec5d0ba3fd0f511bc49501edb2))

- preserve developer fields when rebuilding device metadata ([18b8cfa](https://github.com/jat255/Fit-File-Faker/commit/18b8cfa06079c83cf6703627ce95693320415e6e))

- stack Garmin identity preservation without duplicate creators ([71140cf](https://github.com/jat255/Fit-File-Faker/commit/71140cfde5e30ea5745622de68f7b354db40270f))

- integrate consistent creator identity into COROS device rebuilds ([9af742d](https://github.com/jat255/Fit-File-Faker/commit/9af742dc817b8c2c650bf5eca5cfd0e9ae9f9033))

- fill missing creator serial numbers and verify device identity ([54100bb](https://github.com/jat255/Fit-File-Faker/commit/54100bb6f1f00715d67af6779a52334241ad7764))

- write serial number and software version to device_info if needed ([50d1292](https://github.com/jat255/Fit-File-Faker/commit/50d1292ae29ae904b4ad4088539a199494212424))

- mark rebuilt device_info as creator device ([#80](https://github.com/jat255/fit-file-faker/issues/80)) ([e64239d](https://github.com/jat255/Fit-File-Faker/commit/e64239d7fe56f10d695fe1bf6b69c5ce7ed3a065))

- set product on device_info records that lack it ([#80](https://github.com/jat255/fit-file-faker/issues/80)) ([4054f98](https://github.com/jat255/Fit-File-Faker/commit/4054f983a1b734dbd8e66072192898cd96ed1b3c))

- keep device identity for unmodified manufacturers and add missing creator device_info ([490ce39](https://github.com/jat255/Fit-File-Faker/commit/490ce39c85de8bb446e8db45a341b6d236800bc2))


### Testing

- cover retry after batch edit failure ([e660982](https://github.com/jat255/Fit-File-Faker/commit/e66098297d56b2029cbcdf36f6fa054070091fba))

- cover Fenix 8 device identity for Karoo files ([fae4d1a](https://github.com/jat255/Fit-File-Faker/commit/fae4d1a67f4c624030b1a69853ef701fba5d5fd0))

- propagate device rebuild coverage through stack ([b24157d](https://github.com/jat255/Fit-File-Faker/commit/b24157d84f2d8bfca5298f7e119df52e3108a5ef))

- cover unknown fields in device info rebuilds ([44ecf53](https://github.com/jat255/Fit-File-Faker/commit/44ecf539fdbb6c22ec50d329bbf2d0aad585544f))

- skip release script test without usable bash ([df45da1](https://github.com/jat255/Fit-File-Faker/commit/df45da184d01fd087b7dbf630f6cce0760146799))

- run release script through bash ([f9a5611](https://github.com/jat255/Fit-File-Faker/commit/f9a56119c33fdd1cdc7db6bd4f90078440eee32f))

## [2.2.1](https://github.com/jat255/fit-file-faker/releases/tag/v2.2.1) - (2026-07-10)

### Bug Fixes

- validate release changelog commit subjects ([d6aa0ec](https://github.com/jat255/Fit-File-Faker/commit/d6aa0ecc72a2609e42c39164fbff3aabdea9b0c2))

## [2.2.0](https://github.com/jat255/fit-file-faker/releases/tag/v2.2.0) - (2026-07-10)

### Documentation

- move agent guidance to AGENTS.md ([79750d3](https://github.com/jat255/Fit-File-Faker/commit/79750d3cde33645cf11fd6f43a899d7390e87b1e))


### Styling

- format Onelap support changes ([0ab0b34](https://github.com/jat255/Fit-File-Faker/commit/0ab0b344ea3602fbf85ed76adad008d018fa26e7))

## [2.1.5](https://github.com/jat255/fit-file-faker/releases/tag/v2.1.5) - (2026-04-27)

### Features

- replace garth with garminconnect for Garmin Connect uploads ([#79](https://github.com/jat255/fit-file-faker/issues/79)) ([5ab22dc](https://github.com/jat255/Fit-File-Faker/commit/5ab22dc6a31620477ab9422df6f4be4f9721f4fa))

## [2.1.4](https://github.com/jat255/fit-file-faker/releases/tag/v2.1.4) - (2026-02-23)

### Bug Fixes

- properly handle FIT files with empty/invalid developer-defined fields ([#71](https://github.com/jat255/fit-file-faker/issues/71)) ([5dcde9b](https://github.com/jat255/Fit-File-Faker/commit/5dcde9b162b6e114bdef5ad069236ad59047cc26))

## [2.1.3](https://github.com/jat255/fit-file-faker/releases/tag/v2.1.3) - (2026-02-01)

### Documentation

- clarify that serial_number field requires device Unit ID, not Serial Number ([#68](https://github.com/jat255/fit-file-faker/issues/68)) ([d5553ce](https://github.com/jat255/Fit-File-Faker/commit/d5553ce20065e908fd9e4825c072a05a7918d73c))

- update paths to config videos in README ([#67](https://github.com/jat255/fit-file-faker/issues/67)) ([6192294](https://github.com/jat255/Fit-File-Faker/commit/61922943ecbbd0ba17db0900533743b2355eaf3c))

## [2.1.2](https://github.com/jat255/fit-file-faker/releases/tag/v2.1.2) - (2026-01-31)

### Bug Fixes

- UTF-8 Decoding Errors and Add Serial Number Documentation ([#66](https://github.com/jat255/fit-file-faker/issues/66)) ([55c9173](https://github.com/jat255/Fit-File-Faker/commit/55c9173689b0aa1cbb9bd3a8532278ddee236663))

## [2.1.1](https://github.com/jat255/fit-file-faker/releases/tag/v2.1.1) - (2026-01-30)

### Bug Fixes

- include all vendor subpackages in distribution ([b365e85](https://github.com/jat255/Fit-File-Faker/commit/b365e85c353b4c12cd810d74cf0471583156cd84))

## [2.1.0](https://github.com/jat255/fit-file-faker/releases/tag/v2.1.0) - (2026-01-30)

### Features

- add --version flag with release date ([aea73c5](https://github.com/jat255/Fit-File-Faker/commit/aea73c5023b8c44f8f7fb1e48cf185fa8bb16c10))


### Bug Fixes

- prevent duplicate uploads when MyWhoosh app version updates ([#62](https://github.com/jat255/fit-file-faker/issues/62)) ([d41c478](https://github.com/jat255/Fit-File-Faker/commit/d41c47811198c65a06862c9517fc238174ce67f3))


### Build System

- vendor fit-tool library to eliminate external dependency ([#64](https://github.com/jat255/fit-file-faker/issues/64)) ([1bb4822](https://github.com/jat255/Fit-File-Faker/commit/1bb48222541556814e1ab9e8f56325ae05eb55a8))


### Miscellaneous Tasks

- pin dependency for fit-tool to 0.9.13 ([94a32ff](https://github.com/jat255/Fit-File-Faker/commit/94a32ffe71ad8605d4797bbf8c018b3afb2756f0))

- fix git cliff processing rules ([a26df4c](https://github.com/jat255/Fit-File-Faker/commit/a26df4cc1d10b397f945465634adaafd06edeb94))

## [2.0.3](https://github.com/jat255/fit-file-faker/releases/tag/v2.0.3) - (2026-01-24)


> **Note:** Versions 2.0.1 and 2.0.2 were skipped due to CI/CD configuration issues during the release process and those versions yanked from PyPI. Please do not use them.

### Features

- add draft GitHub release creation to release script ([99072e7](https://github.com/jat255/Fit-File-Faker/commit/99072e7e2de780e020b8dedda0431809dcf0c1a8))


### Bug Fixes

- force uv to use matrix Python version in CI tests ([88dfc11](https://github.com/jat255/Fit-File-Faker/commit/88dfc11761c1ad68c83df129aad31d3405742859))

- properly install dependencies for release pipeline mkdocs build ([4bf7258](https://github.com/jat255/Fit-File-Faker/commit/4bf72587094378ca4280b49d3d783647f3e9b426))

- correct git-cliff template and workflow configuration ([8ad5b4d](https://github.com/jat255/Fit-File-Faker/commit/8ad5b4d54bda75da43529fe03dbc1afe919097f9))

- add missing mkdocs-autorefs dependency and fix Windows CI compatibility ([1269fed](https://github.com/jat255/Fit-File-Faker/commit/1269fed94b21285893f674bfe84fdb358b206204))


### CI/CD

- ci: move draft release creation to publish workflow and improve... ([c68fb94](https://github.com/jat255/Fit-File-Faker/commit/c68fb948832b73e55b09a965ebfceb3870a5c3cc))


### Build System

- replace gitlint with commitlint for Windows compatibility ([506f9c9](https://github.com/jat255/Fit-File-Faker/commit/506f9c97377701b53e853c745189081dd0940946))

## [2.0.0](https://github.com/jat255/fit-file-faker/releases/tag/v2.0.0) - (2026-01-24)

### Features

- add configurable Garmin device simulation per profile ([#46](https://github.com/jat255/fit-file-faker/issues/46)) ([de5ff1f](https://github.com/jat255/Fit-File-Faker/commit/de5ff1fd5ba4726b32329e9fbca74bae9146f782))

- add FIT CRC-16 checksum calculation utility ([9fa247c](https://github.com/jat255/Fit-File-Faker/commit/9fa247cbc9492adceaceb7081b59eef055fc9fae))


### Refactoring

- Extract FIT file editing functionality into dedicated fit_editor.py module (issue [#40](https://github.com/jat255/fit-file-faker/issues/40)) ([c164854](https://github.com/jat255/Fit-File-Faker/commit/c164854b9ebfdd09547864f6b4886b06544d2b57))

- Extract configuration management into dedicated config.py module (issue [#40](https://github.com/jat255/fit-file-faker/issues/40)) ([3868e26](https://github.com/jat255/Fit-File-Faker/commit/3868e260d4e4c3a1dda7e225633eed50b2fac66f))


### Documentation

- fix outdated class level docstrings ([#47](https://github.com/jat255/fit-file-faker/issues/47)) ([9bb4800](https://github.com/jat255/Fit-File-Faker/commit/9bb48005f44773af7aaeaf791065d5c4539e2e12))

- Refactor README and enhance documentation site (issue [#41](https://github.com/jat255/fit-file-faker/issues/41)) ([2efd4c7](https://github.com/jat255/Fit-File-Faker/commit/2efd4c7584f2c6092c6aa07d50cd58d93c484fba))

- Add comprehensive documentation site with MkDocs and automated deployment ([#41](https://github.com/jat255/fit-file-faker/issues/41)) ([031b19c](https://github.com/jat255/Fit-File-Faker/commit/031b19c6dfc8b7b4927bfab027d686ada7436f6a))


### Testing

- Add comprehensive test suite with pytest, fixtures, and CI workflow (issue [#18](https://github.com/jat255/fit-file-faker/issues/18)) ([f97fad5](https://github.com/jat255/Fit-File-Faker/commit/f97fad504de822b378819cbf70c608d201efb62c))


### Miscellaneous Tasks

- Implements conventional commit validation with gitlint ([1f4c279](https://github.com/jat255/Fit-File-Faker/commit/1f4c279cb384362ae4c8a9c862acfa7ef3089f81))

<!-- generated by git-cliff -->

---


## [1.2.4](https://github.com/jat255/Fit-File-Faker/releases/tag/v1.2.4) (2026-01-11)

### Features
- **COROS:** Add support for COROS FIT files with lenient field size validation ([0f3ddde](https://github.com/jat255/Fit-File-Faker/commit/0f3ddde))
- **MyWhoosh:** Add support for MyWhoosh FIT files (manufacturer code 331) ([72c5029](https://github.com/jat255/Fit-File-Faker/commit/72c5029))

### Bug Fixes
- **FIT files:** Strip unknown field definitions before writing to prevent corruption ([28265e2](https://github.com/jat255/Fit-File-Faker/commit/28265e2))
- **FIT files:** Fix Activity message ordering for COROS compatibility ([0f3ddde](https://github.com/jat255/Fit-File-Faker/commit/0f3ddde))
- **device info:** Properly index device_index at 0 to fix images not showing on Garmin Connect ([18186a7](https://github.com/jat255/Fit-File-Faker/commit/18186a7))
- **CI:** Fix broken "test pypi" release step ([72c5029](https://github.com/jat255/Fit-File-Faker/commit/72c5029))

### Miscellaneous Tasks
- Update dependencies and add setuptools configuration ([dc7e309](https://github.com/jat255/Fit-File-Faker/commit/dc7e309))
- Bump version to 1.2.4 ([b4d1877](https://github.com/jat255/Fit-File-Faker/commit/b4d1877))

### Contributors
- @dermarzel (MyWhoosh support)

---

## [1.2.3](https://github.com/jat255/Fit-File-Faker/releases/tag/v1.2.3) (2025-11-05)

### Features
- **Hammerhead:** Add support for Hammerhead Karoo devices ([df6c3d6](https://github.com/jat255/Fit-File-Faker/commit/df6c3d6))

### Miscellaneous Tasks
- Bump version and update README ([d606c18](https://github.com/jat255/Fit-File-Faker/commit/d606c18))

### Contributors
- @lrybak (Hammerhead support)

---

## [1.2.2](https://github.com/jat255/Fit-File-Faker/releases/tag/v1.2.2) (2025-01-26)

### Bug Fixes
- **FIT processing:** Change to generate FileIdMessage rather than editing in place to ensure device is properly set ([4026db3](https://github.com/jat255/Fit-File-Faker/commit/4026db3))
- **FIT processing:** Add FileCreator message for better compatibility ([4026db3](https://github.com/jat255/Fit-File-Faker/commit/4026db3))
- **TrainingPeaks Virtual:** Fix issue with new TPV FIT file structure (#22) ([391e1eb](https://github.com/jat255/Fit-File-Faker/commit/391e1eb))

---

## [1.2.1](https://github.com/jat255/Fit-File-Faker/releases/tag/v1.2.1) (2025-01-07)

### CI/CD
- Don't run testpypi on non-tag pushes ([5e83493](https://github.com/jat255/Fit-File-Faker/commit/5e83493))
- Update GitHub Actions configuration ([a5028b0](https://github.com/jat255/Fit-File-Faker/commit/a5028b0), [e164d69](https://github.com/jat255/Fit-File-Faker/commit/e164d69))

### Miscellaneous Tasks
- Update version to 1.2.1 ([1123c43](https://github.com/jat255/Fit-File-Faker/commit/1123c43))

---

## [1.2.0](https://github.com/jat255/Fit-File-Faker/releases/tag/v1.2.0) (2025-01-07)

### Build System
- Add UV package manager support ([497d1ed](https://github.com/jat255/Fit-File-Faker/commit/497d1ed))
- Add build/release GitHub Action ([497d1ed](https://github.com/jat255/Fit-File-Faker/commit/497d1ed))
- Rename project to fit-file-faker for PyPI ([497d1ed](https://github.com/jat255/Fit-File-Faker/commit/497d1ed))

### Miscellaneous Tasks
- Fix version number ([4376a50](https://github.com/jat255/Fit-File-Faker/commit/4376a50))
- Bump version to 1.0.0 ([4888355](https://github.com/jat255/Fit-File-Faker/commit/4888355))
- Change install action command ([b44334e](https://github.com/jat255/Fit-File-Faker/commit/b44334e))

---

## [1.1.1](https://github.com/jat255/Fit-File-Faker/releases/tag/v1.1.1) (2025-01-07)

### Features
- **Zwift:** Add support for Zwift FIT files ([7efa28d](https://github.com/jat255/Fit-File-Faker/commit/7efa28d))
- **device info:** Properly modify device manufacturer and product IDs ([4d0d0a3](https://github.com/jat255/Fit-File-Faker/commit/4d0d0a3))

### Bug Fixes
- Don't use magic numbers for device identification ([b6400c9](https://github.com/jat255/Fit-File-Faker/commit/b6400c9))
- Remove unused variables ([9415c62](https://github.com/jat255/Fit-File-Faker/commit/9415c62))
- Remove unneeded commented code ([bc78a6e](https://github.com/jat255/Fit-File-Faker/commit/bc78a6e))

### Documentation
- Update README with Zwift support information ([09d8785](https://github.com/jat255/Fit-File-Faker/commit/09d8785))
- Update config example file ([cd352c7](https://github.com/jat255/Fit-File-Faker/commit/cd352c7))
- Various documentation improvements ([450c7e6](https://github.com/jat255/Fit-File-Faker/commit/450c7e6))

### Styling
- Code formatting improvements ([132f22c](https://github.com/jat255/Fit-File-Faker/commit/132f22c))

---

## [1.1.0](https://github.com/jat255/Fit-File-Faker/releases/tag/v1.1.0) (2025-01-05)

### Features
- **config:** Implement configuration as dataclass stored in local JSON file ([90c75c1](https://github.com/jat255/Fit-File-Faker/commit/90c75c1))
- **config:** Add questionary for interactive config file generation ([90c75c1](https://github.com/jat255/Fit-File-Faker/commit/90c75c1))
- **monitoring:** Rename daemonise to monitor for clarity ([90c75c1](https://github.com/jat255/Fit-File-Faker/commit/90c75c1))
- **monitoring:** Use polling handler for monitor mode (better cross-platform support) ([90c75c1](https://github.com/jat255/Fit-File-Faker/commit/90c75c1))
- **monitoring:** Add monitor option to watch directory for new FIT files ([c9491d7](https://github.com/jat255/Fit-File-Faker/commit/c9491d7))
- **monitoring:** Add short pause after file creation to avoid CRC errors ([63b7374](https://github.com/jat255/Fit-File-Faker/commit/63b7374))
- **upload:** Add dryrun option for testing without uploading ([acf863e](https://github.com/jat255/Fit-File-Faker/commit/acf863e))
- **upload:** Add option to preinitialise the list of uploaded files ([3ad9103](https://github.com/jat255/Fit-File-Faker/commit/3ad9103))
- **upload:** Store credentials on first run ([6d5e4d2](https://github.com/jat255/Fit-File-Faker/commit/6d5e4d2))
- **upload:** Set default upload directory to configured TPV user dir ([c537bcd](https://github.com/jat255/Fit-File-Faker/commit/c537bcd))
- **upload:** Change uploaded files tracking to be local to FIT files directory ([c9491d7](https://github.com/jat255/Fit-File-Faker/commit/c9491d7))
- **platform:** Add macOS compatibility ([3343374](https://github.com/jat255/Fit-File-Faker/commit/3343374))
- **platform:** Add minimum Python version check ([90c75c1](https://github.com/jat255/Fit-File-Faker/commit/90c75c1))

### Bug Fixes
- **FIT processing:** Set FitFileBuilder autodefine param to True, fixes issue with Strava FIT files ([d7a2da3](https://github.com/jat255/Fit-File-Faker/commit/d7a2da3))
- **upload:** Fix upload all bug when running on a directory other than cwd ([bd704e6](https://github.com/jat255/Fit-File-Faker/commit/bd704e6))
- **upload:** Fix preinitialise bug ([4c8de1f](https://github.com/jat255/Fit-File-Faker/commit/4c8de1f))
- **platform:** Fix TPV path issues ([5847de9](https://github.com/jat255/Fit-File-Faker/commit/5847de9), [8b94533](https://github.com/jat255/Fit-File-Faker/commit/8b94533))
- **platform:** Fix FITfiles directory detection ([c613c36](https://github.com/jat255/Fit-File-Faker/commit/c613c36))

### Miscellaneous Tasks
- Move .garth directory to script folder rather than FITFiles folder ([90c75c1](https://github.com/jat255/Fit-File-Faker/commit/90c75c1))
- Better organize main code path ([90c75c1](https://github.com/jat255/Fit-File-Faker/commit/90c75c1))
- Remove .env file ([90c75c1](https://github.com/jat255/Fit-File-Faker/commit/90c75c1))
- Update requirements.txt ([53ced03](https://github.com/jat255/Fit-File-Faker/commit/53ced03))
- Bump Garth version ([358409f](https://github.com/jat255/Fit-File-Faker/commit/358409f))

### Documentation
- Update README with new features and improved help output ([e3480ff](https://github.com/jat255/Fit-File-Faker/commit/e3480ff), [90c75c1](https://github.com/jat255/Fit-File-Faker/commit/90c75c1))
- Add example .config file ([2296c38](https://github.com/jat255/Fit-File-Faker/commit/2296c38))

### Styling
- Implement ruff formatting and import order ([90c75c1](https://github.com/jat255/Fit-File-Faker/commit/90c75c1))
- Fix spelling issues ([c613c36](https://github.com/jat255/Fit-File-Faker/commit/c613c36), [e2f545c](https://github.com/jat255/Fit-File-Faker/commit/e2f545c))

### Contributors
- @benjmarshall (multiple contributions including daemon mode, config improvements, and bug fixes)

---

## [1.0.3](https://github.com/jat255/Fit-File-Faker/releases/tag/v1.0.3) (2024-12-03)

### Bug Fixes
- **dependencies:** Update garth version requirement to address compatibility issue ([e413e23](https://github.com/jat255/Fit-File-Faker/commit/e413e23))
  - Resolves [garth issue #73](https://github.com/matin/garth/issues/73)

---

## [1.0.2](https://github.com/jat255/Fit-File-Faker/releases/tag/v1.0.2) (2024-10-31)

### Testing
- Add install tests for CI/CD pipeline ([91ba6f5](https://github.com/jat255/Fit-File-Faker/commit/91ba6f5))

### Miscellaneous Tasks
- Update requirements.txt ([47133a1](https://github.com/jat255/Fit-File-Faker/commit/47133a1))

---

## [1.0.1](https://github.com/jat255/Fit-File-Faker/releases/tag/v1.0.1) (2024-05-28)

### Bug Fixes
- **Windows:** Add tempfile options to workaround Windows permission issue (#1) ([b3ae2cf](https://github.com/jat255/Fit-File-Faker/commit/b3ae2cf))

### Documentation
- Update README with required Python version ([fd82175](https://github.com/jat255/Fit-File-Faker/commit/fd82175))

---

## [1.0.0](https://github.com/jat255/Fit-File-Faker/releases/tag/v1.0.0) (2024-05-22)

### Features
- **Initial Release:** First public release of Fit File Faker ([7c78e47](https://github.com/jat255/Fit-File-Faker/commit/7c78e47))
  - Modify FIT files to appear as Garmin Edge 830 device
  - Support for TrainingPeaks Virtual (formerly indieVelo) FIT files
  - Upload modified files to Garmin Connect
  - Batch processing of multiple FIT files
  - Credential storage and authentication
