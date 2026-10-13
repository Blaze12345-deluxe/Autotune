# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - Development

### Added
- Initial project structure and architecture
- Real-time audio I/O with sounddevice/PortAudio
- Lock-free ring buffers for inter-thread communication
- YIN pitch detection algorithm
- Phase vocoder pitch shifting (STFT-based)
- Auto-Tune processor with musical quantization
- Harmoniser processor with multiple harmony modes
- Music theory module (scales, chords, intervals, harmony)
- Command-line interface with argparse
- Comprehensive test suite structure
- Documentation (README, API, Architecture, CLI, Troubleshooting)

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

## [0.1.0] - Planned First Release

### Added
- Auto-Tune mode with adjustable correction speed and threshold
- Harmoniser mode with interval, scale, and chord-based harmonies
- Musical key/scale selection (12 keys × 13 scales)
- Audio device selection (input/output)
- Configurable block size and sample rate
- Verbose logging levels
- Clean shutdown on SIGINT/SIGTERM
- Buffer overrun/underrun statistics
- Formant preservation in pitch shifting
- Anti-clipping mixer for harmonies
- Voice leading smoothing for harmony transitions

### Known Issues
- Phase vocoder latency ~40ms (algorithmic)
- Single-pitch detection (not polyphonic)
- Formant preservation quality varies with shift amount
- Windows latency higher than Linux/macOS
- No GUI (CLI only)
- No preset save/load
- No MIDI input support

## Release Template

### [X.Y.Z] - YYYY-MM-DD

#### Added
- New features

#### Changed
- Changes in existing functionality

#### Deprecated
- Soon-to-be removed features

#### Removed
- Removed features

#### Fixed
- Bug fixes

#### Security
- Vulnerability fixes