# Technology Stack & Dependencies

## Core Dependencies (Phase 1)
| Library | Version | Purpose |
|---------|---------|---------|
| `sounddevice` | >=0.4.6 | Real-time audio I/O (PortAudio bindings) |
| `numpy` | >=1.24 | Numerical operations on audio buffers |
| `scipy` | >=1.10 | Signal processing, FFT, filtering, YIN pitch detection |
| `argparse` | stdlib | Command-line argument parsing |
| `pytest` | >=7.0 | Unit testing framework |

## Advanced Pitch Shifting (Phase 3+)
| Library | Purpose | Integration |
|---------|---------|-------------|
| `pyrubberband` | Rubber Band library bindings | High-quality time-stretch/pitch-shift |
| `librosa` | Phase vocoder, pitch shifting | Alternative implementation |
| `pedalboard` | Audio effects pipeline | Future effects chain |

## Development Dependencies
| Tool | Purpose |
|------|---------|
| `black` | Code formatting |
| `ruff` | Fast linting |
| `mypy` | Type checking |
| `pytest-cov` | Coverage reporting |
| `pre-commit` | Git hooks |

## Installation Commands
```bash
# Core dependencies
python -m pip install sounddevice numpy scipy pytest

# Development tools
python -m pip install black ruff mypy pytest-cov pre-commit

# Advanced pitch shifting (when needed)
python -m pip install pyrubberband librosa pedalboard
```

## System Requirements
- **Python**: 3.10+
- **PortAudio**: System library (install via `apt-get install portaudio19-dev` / `brew install portaudio`)
- **FFTW**: Optional, for faster FFT (scipy can use it)
- **OS**: Linux, macOS, Windows (sounddevice is cross-platform)

## Version Pinning Strategy
- Pin major versions in `requirements.txt`
- Use `requirements-dev.txt` for development tools
- Update quarterly or when security issues arise