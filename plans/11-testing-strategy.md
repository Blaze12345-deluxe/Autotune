# Testing Strategy

## Test Organization
```
tests/
├── conftest.py              # Pytest fixtures, shared config
├── test_notes.py            # Note/frequency/MIDI conversions
├── test_scales.py           # Scale membership, quantization
├── test_chords.py           # Chord construction, voicing
├── test_intervals.py        # Interval arithmetic
├── test_harmony.py          # Harmony generation rules
├── test_pitch_detector.py   # YIN algorithm accuracy
├── test_pitch_shifter.py    # Phase vocoder quality
├── test_autotune.py         # Auto-Tune integration
├── test_harmoniser.py       # Harmoniser integration
├── test_audio_engine.py     # Audio I/O, buffering
├── test_cli.py              # Argument parsing
└── integration/
    ├── test_realtime.py     # Full pipeline timing
    └── test_latency.py      # Latency measurement
```

## Unit Test Principles
- **Fast**: < 100ms per test file
- **Isolated**: No audio hardware, no filesystem, no network
- **Deterministic**: Fixed seeds, no randomness
- **Pure functions**: Test inputs → outputs, no side effects

## Fixtures (conftest.py)
```python
import pytest
import numpy as np

@pytest.fixture
def sample_rate():
    return 48000

@pytest.fixture
def block_size():
    return 256

@pytest.fixture
def sine_440(sample_rate, block_size):
    """Generate 440 Hz sine wave block."""
    t = np.arange(block_size) / sample_rate
    return np.sin(2 * np.pi * 440 * t).astype(np.float32)

@pytest.fixture
def sine_220(sample_rate, block_size):
    t = np.arange(block_size) / sample_rate
    return np.sin(2 * np.pi * 220 * t).astype(np.float32)

@pytest.fixture
def silence(block_size):
    return np.zeros(block_size, dtype=np.float32)

@pytest.fixture
def white_noise(block_size):
    return np.random.randn(block_size).astype(np.float32) * 0.01

@pytest.fixture
def chirp_signal(sample_rate):
    """Frequency sweep for testing pitch tracking."""
    duration = 1.0
    t = np.arange(int(sample_rate * duration)) / sample_rate
    f0, f1 = 220, 880
    return np.sin(2 * np.pi * (f0 + (f1 - f0) * t) * t).astype(np.float32)
```

## Pitch Detector Tests
```python
# test_pitch_detector.py

def test_sine_wave_detection(sine_440, sample_rate):
    detector = PitchDetector(sample_rate)
    result = detector.process(sine_440)
    assert result.voiced
    assert abs(result.frequency - 440) < 2.0  # ±2 Hz
    assert result.confidence > 0.9

def test_octave_detection(sine_220, sample_rate):
    detector = PitchDetector(sample_rate)
    result = detector.process(sine_220)
    assert result.voiced
    assert abs(result.frequency - 220) < 2.0

def test_silence_rejection(silence, sample_rate):
    detector = PitchDetector(sample_rate)
    result = detector.process(silence)
    assert not result.voiced
    assert result.frequency == 0.0

def test_noise_rejection(white_noise, sample_rate):
    detector = PitchDetector(sample_rate)
    result = detector.process(white_noise)
    assert not result.voiced or result.confidence < 0.3

def test_chirp_tracking(chirp_signal, sample_rate):
    detector = PitchDetector(sample_rate, frame_size=1024, hop_size=256)
    # Process in chunks, verify frequency tracks sweep
    frequencies = []
    for i in range(0, len(chirp_signal), 256):
        block = chirp_signal[i:i+256]
        if len(block) == 256:
            result = detector.process(block)
            if result.voiced:
                frequencies.append(result.frequency)
    # Verify monotonic increase
    assert all(frequencies[i] <= frequencies[i+1] for i in range(len(frequencies)-1))
```

## Pitch Shifter Tests
```python
# test_pitch_shifter.py

def test_octave_up(sine_440, sample_rate):
    shifter = PitchShifter(sample_rate)
    shifted = shifter.shift(sine_440, 2.0)
    # Detect pitch of result
    detector = PitchDetector(sample_rate)
    result = detector.process(shifted)
    assert result.voiced
    assert abs(result.frequency - 880) < 5.0

def test_octave_down(sine_440, sample_rate):
    shifter = PitchShifter(sample_rate)
    shifted = shifter.shift(sine_440, 0.5)
    detector = PitchDetector(sample_rate)
    result = detector.process(shifted)
    assert result.voiced
    assert abs(result.frequency - 220) < 5.0

def test_unity_ratio(sine_440, sample_rate):
    shifter = PitchShifter(sample_rate)
    shifted = shifter.shift(sine_440, 1.0)
    # Should be nearly identical
    mse = np.mean((sine_440 - shifted) ** 2)
    assert mse < 1e-6

def test_timing_preserved(sine_440, sample_rate):
    """Verify output length matches input."""
    shifter = PitchShifter(sample_rate)
    for ratio in [0.5, 0.75, 1.0, 1.5, 2.0]:
        shifted = shifter.shift(sine_440, ratio)
        assert len(shifted) == len(sine_440)

def test_formant_preservation(sample_rate):
    """Test with more complex signal (formant-like)."""
    # Create signal with formant at 1000 Hz
    t = np.arange(2048) / sample_rate
    signal = np.sin(2*np.pi*220*t) + 0.5*np.sin(2*np.pi*1000*t)
    signal = signal.astype(np.float32)
    
    shifter = PitchShifter(sample_rate)
    shifted = shifter.shift(signal, 2.0, preserve_formants=True)
    
    # Formant should stay ~1000 Hz, not shift to 2000 Hz
    # This is a qualitative test - spectral analysis needed
```

## Auto-Tune Tests
```python
# test_autotune.py

def test_correct_flat_note(sample_rate, block_size):
    """Test correction of a flat note."""
    # 438 Hz (slightly flat A4)
    t = np.arange(block_size) / sample_rate
    flat_a = np.sin(2 * np.pi * 438 * t).astype(np.float32)
    
    settings = AutoTuneSettings(key='C', scale='major', correction_speed=1.0, threshold=0)
    processor = AutoTuneProcessor(settings, sample_rate, block_size)
    
    output = processor.process(flat_a, sample_rate)
    
    detector = PitchDetector(sample_rate)
    result = detector.process(output)
    assert result.voiced
    assert abs(result.frequency - 440) < 5.0  # Corrected to A4

def test_no_correction_when_in_tune(sample_rate, block_size):
    """In-tune note should pass through unchanged."""
    t = np.arange(block_size) / sample_rate
    in_tune = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    
    settings = AutoTuneSettings(key='C', scale='major', threshold=50)
    processor = AutoTuneProcessor(settings, sample_rate, block_size)
    
    output = processor.process(in_tune, sample_rate)
    mse = np.mean((in_tune - output) ** 2)
    assert mse < 1e-4  # Minimal change

def test_threshold_gating(sample_rate, block_size):
    """Notes within threshold should not be corrected."""
    # 442 Hz (2 cents sharp - within 25 cent threshold)
    t = np.arange(block_size) / sample_rate
    sharp = np.sin(2 * np.pi * 442 * t).astype(np.float32)
    
    settings = AutoTuneSettings(key='C', scale='major', threshold=25)
    processor = AutoTuneProcessor(settings, sample_rate, block_size)
    
    output = processor.process(sharp, sample_rate)
    mse = np.mean((sharp - output) ** 2)
    assert mse < 1e-4

def test_correction_speed_smoothing(sample_rate, block_size):
    """Fast correction should reach target faster."""
    # This requires multi-block processing
    pass  # Integration test
```

## Harmoniser Tests
```python
# test_harmoniser.py

def test_major_third_harmony(sample_rate, block_size):
    """Generate major third above C4."""
    t = np.arange(block_size) / sample_rate
    c4 = np.sin(2 * np.pi * 261.63 * t).astype(np.float32)
    
    settings = HarmoniserSettings(key='C', scale='major', intervals=(4,), voice_volumes=(1.0, 0.7))
    processor = HarmoniserProcessor(settings, sample_rate, block_size)
    
    output = processor.process(c4, sample_rate)
    
    detector = PitchDetector(sample_rate)
    result = detector.process(output)
    # Should detect both C4 and E4 (approx 329.63 Hz)
    # This is hard to test with single detector - need multi-pitch or spectral check

def test_multiple_voices(sample_rate, block_size):
    """Test 3-voice harmony."""
    t = np.arange(block_size) / sample_rate
    c4 = np.sin(2 * np.pi * 261.63 * t).astype(np.float32)
    
    settings = HarmoniserSettings(intervals=(4, 7), voice_volumes=(1.0, 0.6, 0.6))
    processor = HarmoniserProcessor(settings, sample_rate, block_size)
    
    output = processor.process(c4, sample_rate)
    # RMS should be higher than input (multiple voices)
    assert np.sqrt(np.mean(output**2)) > np.sqrt(np.mean(c4**2))

def test_silence_passthrough(sample_rate, block_size, silence):
    settings = HarmoniserSettings()
    processor = HarmoniserProcessor(settings, sample_rate, block_size)
    output = processor.process(silence, sample_rate)
    assert np.allclose(output, 0, atol=1e-6)
```

## Music Theory Tests
```python
# test_scales.py

def test_major_scale_notes():
    notes = get_scale_notes('C', 'major')
    # C major: C, D, E, F, G, A, B (no sharps/flats)
    expected_pcs = {0, 2, 4, 5, 7, 9, 11}  # Pitch classes
    actual_pcs = {n % 12 for n in notes}
    assert actual_pcs == expected_pcs

def test_minor_scale_notes():
    notes = get_scale_notes('A', 'minor')
    expected_pcs = {9, 11, 0, 2, 4, 5, 7}  # A, B, C, D, E, F, G
    actual_pcs = {n % 12 for n in notes}
    assert actual_pcs == expected_pcs

def test_quantize_to_scale():
    # 438 Hz ≈ 68.8 MIDI (flat A4)
    # In C major, nearest is A4 (69) or G4 (67)
    quantized = quantize_to_scale(68.8, 'C', 'major')
    assert quantized in [67, 69]  # G4 or A4

# test_chords.py

def test_diatonic_chords_c_major():
    chords = get_diatonic_chords('C', 'major')
    assert chords[1].quality == 'major'    # C major
    assert chords[2].quality == 'minor'    # D minor
    assert chords[5].quality == 'major'    # G major
    assert chords[7].quality == 'diminished'  # B diminished
```

## Integration Tests
```python
# integration/test_realtime.py

def test_engine_start_stop():
    """Test engine can start and stop cleanly."""
    settings = Settings(autotune=True, block_size=256)
    processor = AutoTuneProcessor(settings, 48000, 256)
    engine = AudioEngine(processor, settings)
    
    engine.start()
    assert engine.running
    time.sleep(0.1)
    engine.stop()
    assert not engine.running

def test_callback_timing():
    """Verify callback completes within budget."""
    settings = Settings(block_size=256, sample_rate=48000)
    processor = AutoTuneProcessor(settings, 48000, 256)
    engine = AudioEngine(processor, settings)
    
    # Simulate callback
    indata = np.random.randn(256, 1).astype(np.float32) * 0.1
    outdata = np.zeros((256, 1), dtype=np.float32)
    
    import time
    start = time.perf_counter()
    engine._callback(indata, outdata, 256, None, None)
    elapsed = (time.perf_counter() - start) * 1000  # ms
    
    # Should complete in < 2.6ms (50% of 5.33ms block)
    assert elapsed < 2.6

# integration/test_latency.py

def test_end_to_end_latency():
    """Measure actual latency with loopback."""
    # Requires hardware loopback or virtual audio cable
    # Skip in CI
    pytest.skip("Requires audio hardware")
```

## Performance Benchmarks
```python
# benchmarks/benchmark_pitch_detection.py
def test_pitch_detector_speed(benchmark, sample_rate):
    detector = PitchDetector(sample_rate)
    audio = np.random.randn(2048).astype(np.float32)
    benchmark(detector.process, audio)

# benchmarks/benchmark_pitch_shifter.py
def test_pitch_shifter_speed(benchmark, sample_rate):
    shifter = PitchShifter(sample_rate)
    audio = np.random.randn(2048).astype(np.float32)
    benchmark(shifter.shift, audio, 1.5)
```

## CI/CD Pipeline
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install system deps
        run: sudo apt-get update && sudo apt-get install -y portaudio19-dev
      - name: Install Python deps
        run: pip install -r requirements.txt -r requirements-dev.txt
      - name: Run tests
        run: pytest --cov=auto_tune --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Coverage Targets
| Module | Target |
|--------|--------|
| `music/` | 95% |
| `processing/base.py` | 90% |
| `processing/pitch_detector.py` | 85% |
| `processing/pitch_shifter.py` | 80% |
| `processing/autotune.py` | 85% |
| `processing/harmoniser.py` | 85% |
| `audio/` | 70% (harder to test without hardware) |
| Overall | 80% |

## Property-Based Testing (Hypothesis)
```python
# tests/test_properties.py
from hypothesis import given, strategies as st

@given(st.floats(min_value=20, max_value=20000))
def test_freq_midi_roundtrip(freq):
    midi = freq_to_midi(freq)
    reconstructed = midi_to_freq(midi)
    assert abs(freq - reconstructed) / freq < 0.001  # < 0.1% error

@given(st.integers(min_value=0, max_value=127))
def test_midi_note_name_roundtrip(midi):
    name = midi_to_note_name(midi)
    reconstructed = note_name_to_midi(name)
    assert midi == reconstructed
```