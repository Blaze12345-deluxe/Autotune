# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-13

### Added
- **Audio I/O**: Real-time audio capture/playback with sounddevice/PortAudio
- **Ring Buffers**: Lock-free single-producer/single-consumer buffers for thread-safe audio transfer
- **YIN Pitch Detection**: Fundamental frequency estimator with confidence measure
- **Phase Vocoder**: STFT-based pitch shifting preserving timing and formants
- **Auto-Tune Processor**: Musical pitch correction with key/scale quantization, correction speed, and threshold gating
- **Harmoniser Processor**: Multi-voice harmony generation with interval, scale, and chord modes
- **Music Theory Module**: Complete scale/chord/interval/harmony system with 13 scale types
- **CLI Interface**: Full argparse implementation with device selection, musical settings, and verbose logging
- **Testing**: 63 unit tests passing for music theory (notes, scales, chords)
- **Code Quality**: Black formatting, Ruff linting, MyPy type checking, pre-commit hooks
- **Documentation**: Comprehensive docs (README, API, Architecture, CLI, Troubleshooting, Quickstart)

### Changed
- N/A (initial release)

### Fixed
- N/A (initial release)

### Known Issues
- Phase vocoder algorithmic latency ~40ms
- Single-pitch detection (not polyphonic)
- Formant preservation quality varies with shift amount
- Windows baseline latency higher than Linux/macOS
- CLI only (no GUI)
- No preset save/load or MIDI input support

## [Unreleased] - Development

### Planned
- Additional unit tests for pitch detection and processing modules
- Integration tests with audio hardware
- Performance benchmarks
- Preset system
- Additional effects (reverb, delay, EQ, compressor)

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