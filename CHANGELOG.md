# Changelog

All notable changes to this project will be documented in this file.

---

## [1.0.0] — 2025-05-25
### Initial Version
**Core Functionality**
- Real-time, full-duplex voice assistant powered by OpenAI GPT-4o.
- Assistant input/output using `sounddevice` with a push-button session trigger.
- Streaming response handling with chunked playback and lip-syncing via RMS analysis.
- Motor control using Raspberry Pi GPIO:
    - PWM-based mouth movement synchronized to speech.
    - Head and tail motion via H-bridge motor drivers.

**Personality System**
- Configurable personality traits via `persona.ini` with real-time runtime updates using function calling.
- Trait categories include: `humor`, `sarcasm`, `honesty`, `confidence`, `verbosity`, `curiosity`, and more.
- Backstory and behavioral instructions stored in `persona.ini` with structured `[PERSONALITY]`, `[BACKSTORY]`, and `[META]` sections.

**Hardware & Setup**
- 3D-printable backplate to mount USB microphone and speaker in the Billy Bass enclosure.
- GPIO safe boot state configuration to prevent motor activation during Pi startup.
- Systemd integration (`billy.service`) for background operation and autostart at boot.

**Audio System**
- Configurable voice model (`VOICE`) via `.env` file.
- Adjustable silence threshold and mic timeout for voice session logic.

**MQTT Integration (Optional)**
- Basic MQTT connectivity for status reporting, safe shutdown raspberry pi command and future integration with Home Assistant.

**Song Mode**
- Folder-based song playback system supporting:
    - `full.wav` for audio
    - `vocals.wav` and `drums.wav` for animated flapping (mouth and tail)
    - `metadata.txt` to control animation timing and motion profiles
- Function-calling support to trigger songs via conversation with Billy.

## [1.1.0] — 2025-07-18
### Adds initial version of Home Assistant API integration and major stability improvements.

### Added

- Initial integration with Home Assistant's conversation API.
- Graceful fallback when Home Assistant is not configured.
- New environment variable `ALLOW_UPDATE_PERSONALITY_INI` to prevent users from permanently changing Billy's personality traits.
- Wake-up audio now blocks the assistant from listening until playback is complete.
- Retain reference to mic checker task to avoid premature destruction.
- Added Ruff linter with configuration and a pre-commit hook.
- Added `CHANGELOG.md`.

### Changed

- Audio session now ensures WebSocket session is created before sending audio.
- All audio sends are awaited to prevent race conditions.
- WebSocket connections now use additional mutex locking to avoid lifecycle errors.
- Improved full audio transcript logging with newlines.
- Error responses from the assistant API are now shown clearly in the output stream.
- Cleaned up import statements and used proper relative imports.
- MQTT logic now checks if MQTT is configured before sending or receiving.

### Fixed

- Fixed race condition where audio might be sent before the session is initialized.
- Prevented audio from being interpreted when `self.ws` is unexpectedly reset.
- Suppressed redundant session-end output.
- Addressed expected `CancelledError` when stopping sessions.
- Removed duplicate and unused imports and functions.
- Removed duplicate `aiohttp` dependency from `requirements.txt`.
- Fixed potential undefined variable.
- Fixed usage of legacy `websockets` API.
- Added missing dependencies: `aiohttp`, `lgpio`.

## [1.2.0] — 2025-07-??

### Web UI 

### Added
- Web-based user interface for configuration
- Version check and updater with `versions.ini`.
- Speaker volume test and control in UI.
- Tailwind CSS included locally for styling.
- Password field visibility toggles in the UI.
- Dropdown for selecting voice options in UI.
- Mic input level check utility.
- Frontend notifications and layout styling.
- Config save reliability from the web UI.
- Audio settings section in UI.
- Versioning check logic during boot.
- Bugfixes in early version updater.

### Improved
- Folder structure simplified and clarified.
- Automatic creation of `.env` and `persona.ini` from *.example files on first run.
- Committed `persona.ini`; now ignored by `.gitignore`.

### Added in beta
- MQTT "say" command integration.
- Systemd service install process.
- Wi-Fi onboarding form with country selection.