# Developer Guide

## Getting Started

### Prerequisites
- Python 3.10+
- PortAudio development headers
- Git

### System Dependencies
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y portaudio19-dev python3-dev

# macOS
brew install portaudio

# Windows
# PortAudio is bundled with sounddevice wheels
```

### Development Setup

**Using uv (recommended):**
```bash
# Clone repository
git clone <repo-url>
cd autotune

# Install uv if needed
pip install uv

# Create venv and install with dev dependencies
uv sync --extra dev

# Install pre-commit hooks
uv run pre-commit install
```

**Using pip (traditional):**
```bash
# Clone repository
git clone <repo-url>
cd autotune

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install in development mode
pip install -e ".[dev]"

# Or manually
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

## Project Structure
```
autotune/
├── auto-tune.py              # Main entry point
├── pyproject.toml            # Package metadata
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # Development dependencies
├── config/
│   └── defaults.py           # Default settings
├── audio/
│   ├── __init__.py
│   ├── engine.py             # Audio engine
│   ├── input.py              # Input stream
│   ├── output.py             # Output stream
│   └── buffer.py             # Ring buffers
├── processing/
│   ├── __init__.py
│   ├── base.py               # Processor interface
│   ├── pitch_detector.py     # YIN pitch detection
│   ├── pitch_shifter.py      # Phase vocoder
│   ├── autotune.py           # Auto-Tune processor
│   ├── harmoniser.py         # Harmoniser processor
│   └── effects.py            # Effects (future)
├── music/
│   ├── __init__.py
│   ├── notes.py              # Note conversions
│   ├── scales.py             # Scale definitions
│   ├── chords.py             # Chord definitions
│   ├── intervals.py          # Interval arithmetic
│   └── harmony.py            # Harmony rules
└── tests/
    ├── conftest.py
    ├── test_*.py             # Unit tests
    └── integration/          # Integration tests
```

## Development Workflow

### Running the Application
```bash
# Development mode (auto-reload not needed for CLI)
python auto-tune.py --autotune --key C --scale major -v

# With custom settings
python auto-tune.py --harmonise --key G --scale major --intervals 4,7 -vv
```

### Running Tests
```bash
# All tests
pytest

# Verbose
pytest -v

# With coverage
pytest --cov=autotune --cov-report=html

# Specific test file
pytest tests/test_pitch_detector.py -v

# Integration tests (require audio hardware)
pytest tests/integration/ -v
```

### Code Quality
```bash
# Format code
# With uv
uv run black .

# With pip
black .

# Check formatting
uv run black --check .
# black --check .

# Lint
uv run ruff check .
# ruff check .

# Fix lint issues
uv run ruff check --fix .
# ruff check --fix .

# Type check
uv run mypy .
# mypy .

# Run all checks
uv run pre-commit run --all-files
# pre-commit run --all-files
```

### Adding a New Processor

1. **Create processor module** (`processing/my_effect.py`):
```python
import numpy as np
from processing.base import AudioProcessor
from dataclasses import dataclass

@dataclass
class MyEffectSettings:
    param1: float = 1.0
    param2: float = 0.5

class MyEffectProcessor(AudioProcessor):
    def __init__(self, settings: MyEffectSettings, sample_rate: int, block_size: int):
        self.settings = settings
        self.sample_rate = sample_rate
        self.block_size = block_size
        # Initialize any state
    
    def process(self, audio_block: np.ndarray, sample_rate: int) -> np.ndarray:
        # Your real-time processing here
        # Must be fast, no allocations in hot path
        return processed_audio
    
    def reset(self):
        # Reset state
        pass
```

2. **Register in factory** (`auto-tune.py`):
```python
from processing.my_effect import MyEffectProcessor, MyEffectSettings

def create_processor(mode: str, settings: Settings, sample_rate: int, block_size: int):
    if mode == "autotune":
        return AutoTuneProcessor(settings.autotune, sample_rate, block_size)
    elif mode == "harmonise":
        return HarmoniserProcessor(settings.harmoniser, sample_rate, block_size)
    elif mode == "myeffect":
        return MyEffectProcessor(settings.myeffect, sample_rate, block_size)
    else:
        raise ValueError(f"Unknown mode: {mode}")
```

3. **Add CLI arguments** (`auto-tune.py`):
```python
parser.add_argument("--myeffect", action="store_true", help="Enable my effect")
# Add effect-specific arguments...
```

4. **Add settings** (`config/defaults.py`):
```python
@dataclass
class Settings:
    # ... existing ...
    myeffect: MyEffectSettings = field(default_factory=MyEffectSettings)
```

5. **Write tests** (`tests/test_my_effect.py`):
```python
def test_my_effect_process(sample_rate, block_size):
    settings = MyEffectSettings()
    processor = MyEffectProcessor(settings, sample_rate, block_size)
    audio = np.random.randn(block_size).astype(np.float32) * 0.1
    output = processor.process(audio, sample_rate)
    assert output.shape == audio.shape
```

## Real-Time Programming Guidelines

### DO
- Pre-allocate all buffers in `__init__`
- Use NumPy vectorized operations
- Keep callback execution time < 50% of block duration
- Use lock-free data structures for thread communication
- Handle errors gracefully (never crash callback)

### DON'T
- Allocate memory in callback (no `np.zeros`, `list.append`, etc.)
- Use locks (`threading.Lock`, `queue.Queue`)
- Call Python functions that may block (I/O, `time.sleep`, logging)
- Raise exceptions in callback
- Do heavy computation (FFT, pitch detection) without profiling

### Buffer Management Pattern
```python
class MyProcessor:
    def __init__(self, sample_rate, block_size):
        # Pre-allocate
        self.work_buffer = np.zeros(block_size, dtype=np.float32)
        self.fft_buffer = np.zeros(2048, dtype=np.complex64)
        # ...
    
    def process(self, audio_block, sample_rate):
        # Reuse buffers
        np.copyto(self.work_buffer, audio_block)
        # In-place operations where possible
        self.work_buffer *= gain
        return self.work_buffer
```

## Testing Guidelines

### Unit Test Structure
```python
# tests/test_my_module.py
import pytest
import numpy as np
from my_module import MyClass

class TestMyClass:
    def test_basic_functionality(self, sample_rate):
        obj = MyClass(sample_rate)
        result = obj.process(np.ones(256))
        assert result.shape == (256,)
    
    @pytest.mark.parametrize("input_freq,expected", [
        (440, 440),
        (220, 220),
    ])
    def test_frequency_response(self, input_freq, expected, sample_rate):
        # Test with known input
        pass
```

### Fixtures (conftest.py)
```python
@pytest.fixture
def sample_rate():
    return 48000

@pytest.fixture
def block_size():
    return 256

@pytest.fixture
def sine_wave(sample_rate, block_size):
    def _sine(freq):
        t = np.arange(block_size) / sample_rate
        return np.sin(2 * np.pi * freq * t).astype(np.float32)
    return _sine
```

### Property-Based Testing
```python
from hypothesis import given, strategies as st

@given(st.floats(min_value=20, max_value=20000))
def test_freq_midi_roundtrip(freq):
    midi = freq_to_midi(freq)
    reconstructed = midi_to_freq(midi)
    assert abs(freq - reconstructed) / freq < 0.001
```

## Debugging

### Visualizing Pitch
```bash
# Run with debug output
python auto-tune.py --autotune -vv 2>&1 | grep PITCH
```

### Measuring Latency
```python
# In audio callback
import time
start = time.perf_counter()
# ... processing ...
latency_ms = (time.perf_counter() - start) * 1000
```

### Profiling CPU Usage
```bash
# Using cProfile
python -m cProfile -o profile.stats auto-tune.py --autotune

# Analyze
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

### Audio Debugging
```python
# Save audio for analysis
import soundfile as sf
sf.write('debug_input.wav', input_audio, 48000)
sf.write('debug_output.wav', output_audio, 48000)
```

## Performance Optimization

### NumPy Best Practices
- Use `np.dot` or `@` for matrix multiplication
- Avoid Python loops over arrays
- Use `out=` parameter for in-place operations
- Prefer `np.fft.rfft` over `np.fft.fft` for real signals

### Phase Vocoder Optimization
- Use `scipy.signal.stft` / `istft` (optimized C)
- Cache window functions
- Minimize FFT size for acceptable quality
- Consider `pypy` for pure Python loops

### Memory Management
- Reuse arrays with `np.copyto` or slice assignment
- Avoid creating new arrays in hot paths
- Use `dtype=np.float32` (not float64) for audio

## Contributing

### Pull Request Process
1. Fork repository
2. Create feature branch (`git checkout -b feature/my-feature`)
3. Make changes with tests
4. Run quality checks (`pre-commit run --all-files`)
5. Submit PR with description

### Commit Message Format
```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Coding Standards
- Type hints for all public functions
- Docstrings for all classes and public methods
- Maximum line length: 100 characters
- Follow PEP 8 (enforced by black/ruff)

## Release Process

### Versioning
Semantic Versioning (MAJOR.MINOR.PATCH)
- MAJOR: Breaking API changes
- MINOR: New features, backward compatible
- PATCH: Bug fixes

### Release Checklist
- [ ] All tests pass
- [ ] Version bumped in `pyproject.toml`
- [ ] Changelog updated
- [ ] Documentation updated
- [ ] Tag created: `git tag v0.1.0`
- [ ] GitHub release created
- [ ] PyPI package published (if applicable)