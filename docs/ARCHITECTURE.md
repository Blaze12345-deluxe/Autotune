# Architecture Documentation

## Overview
This document describes the internal architecture of the Auto-Tune & Harmoniser application. It is intended for developers who want to understand, extend, or contribute to the codebase.

## Design Principles

1. **Separation of Concerns**: Audio I/O, signal processing, musical logic, and UI are separate modules
2. **Real-time Safety**: Audio callback never allocates, locks, or blocks
3. **Extensibility**: New processors implement a common interface
4. **Testability**: Pure functions where possible, dependency injection
5. **Musical Correctness**: Proper music theory implementation

## Module Dependency Graph
```
auto-tune.py (CLI)
    │
    ├─▶ config/defaults.py
    │
    ├─▶ audio/
    │     ├─▶ engine.py ◀──┐
    │     ├─▶ input.py     │
    │     ├─▶ output.py    │   Uses
    │     └─▶ buffer.py    │
    │                      │
    ├─▶ processing/        │
    │     ├─▶ base.py      │
    │     ├─▶ pitch_detector.py  Uses
    │     ├─▶ pitch_shifter.py   Uses
    │     ├─▶ autotune.py        │
    │     ├─▶ harmoniser.py      │
    │     └─▶ effects.py         │
    │                      │
    └─▶ music/              Uses
          ├─▶ notes.py
          ├─▶ scales.py
          ├─▶ chords.py
          ├─▶ intervals.py
          └─▶ harmony.py
```

## Core Components

### 1. Audio Engine (`audio/engine.py`)

**Responsibility**: Manages the real-time audio stream, coordinates input→processing→output.

**Key Classes**:
```python
class AudioEngine:
    def __init__(self, processor: AudioProcessor, settings: Settings):
        self.processor = processor
        self.settings = settings
        self.input_stream = None
        self.output_stream = None
        self.running = False
    
    def start(self): ...
    def stop(self): ...
    def run_until_interrupted(self): ...
    
    def _callback(self, indata, outdata, frames, time_info, status):
        # Called from PortAudio thread (high priority)
        # Must be fast and deterministic
```

**Threading Model**:
- Main thread: `start()`, `stop()`, signal handling
- PortAudio callback thread: Real-time audio processing
- Optional worker thread: Heavy processing (future)

**Buffer Flow**:
```
PortAudio Input Callback
        │
        ▼
   InputBuffer (ring buffer, lock-free)
        │
        ▼
AudioEngine._callback() pulls block
        │
        ▼
processor.process(block, sample_rate)
        │
        ▼
OutputBuffer (ring buffer, lock-free)
        │
        ▼
PortAudio Output Callback
```

### 2. Ring Buffer (`audio/buffer.py`)

**Responsibility**: Lock-free single-producer/single-consumer buffer for inter-thread audio transfer.

**Design**:
- Power-of-2 capacity for fast modulo
- Atomic indices (Python's GIL makes simple ints atomic)
- Overrun/underrun counters for diagnostics

```python
class RingBuffer:
    def __init__(self, capacity: int, channels: int = 1):
        self.capacity = capacity
        self.buffer = np.zeros((capacity, channels), dtype=np.float32)
        self.write_idx = 0
        self.read_idx = 0
        self.overruns = 0
        self.underruns = 0
    
    def write(self, data: np.ndarray) -> int:
        # Non-blocking, drops oldest on overrun
    
    def read(self, n_samples: int) -> np.ndarray:
        # Non-blocking, zero-pads on underrun
```

### 3. Processor Interface (`processing/base.py`)

**Responsibility**: Common interface for all audio processors.

```python
from abc import ABC, abstractmethod
import numpy as np

class AudioProcessor(ABC):
    @abstractmethod
    def process(self, audio_block: np.ndarray, sample_rate: int) -> np.ndarray:
        """Process one audio block. Must be real-time safe."""
        pass
    
    def reset(self) -> None:
        """Reset internal state (called on stream start/stop)."""
        pass
    
    @property
    def latency_samples(self) -> int:
        """Algorithmic latency in samples."""
        return 0
    
    @property
    def name(self) -> str:
        return self.__class__.__name__
```

**Implementations**:
- `AutoTuneProcessor` - Pitch correction
- `HarmoniserProcessor` - Harmony generation
- Future: `ReverbProcessor`, `VocoderProcessor`, etc.

### 4. Pitch Detector (`processing/pitch_detector.py`)

**Algorithm**: YIN (Yet Another Algorithm for Pitch Tracking)

**Interface**:
```python
@dataclass
class PitchResult:
    frequency: float      # Hz, 0 if unvoiced
    confidence: float     # 0.0-1.0
    voiced: bool          # True if pitched
    rms: float            # Energy level

class PitchDetector:
    def __init__(self, sample_rate: int, frame_size: int = 2048, 
                 hop_size: int = 512, min_freq: float = 65.0, 
                 max_freq: float = 1050.0, threshold: float = 0.1):
        ...
    
    def process(self, audio_block: np.ndarray) -> PitchResult:
        # Accumulates blocks until frame_size reached
        # Runs YIN every hop_size
        # Returns latest result
    
    def reset(self): ...
```

**Internal Buffering**:
- Accumulates input blocks until `frame_size` reached
- Processes YIN every `hop_size` samples
- Returns most recent result for each output block

### 5. Pitch Shifter (`processing/pitch_shifter.py`)

**Algorithm**: Phase Vocoder (STFT-based)

**Interface**:
```python
class PitchShifter:
    def __init__(self, sample_rate: int, fft_size: int = 2048, 
                 hop_size: int = 512, window: str = 'hann'):
        ...
    
    def shift(self, audio: np.ndarray, ratio: float, 
              preserve_formants: bool = True) -> np.ndarray:
        # Offline/batch processing
    
    def shift_streaming(self, audio_block: np.ndarray, 
                        ratio: float) -> np.ndarray:
        # Real-time streaming with phase continuity
    
    def reset(self): ...
    
    @property
    def latency_samples(self) -> int:
        return self.fft_size
```

**Phase Vocoder Steps**:
1. STFT analysis (windowed FFT)
2. Phase unwrapping and true frequency estimation
3. Frequency scaling by ratio
4. Phase accumulation for synthesis
5. ISTFT synthesis
6. Overlap-add reconstruction

### 6. Auto-Tune Processor (`processing/autotune.py`)

**Pipeline**:
```python
class AutoTuneProcessor(AudioProcessor):
    def __init__(self, settings: AutoTuneSettings, sample_rate: int, block_size: int):
        self.pitch_detector = PitchDetector(sample_rate)
        self.pitch_shifter = PitchShifter(sample_rate)
        self.smoother = CorrectionSmoother(settings.correction_speed, sample_rate, block_size)
        self.scale_notes = get_scale_notes(settings.key, settings.scale)
    
    def process(self, audio_block, sample_rate):
        # 1. Detect pitch
        pitch = self.pitch_detector.process(audio_block)
        
        # 2. If not voiced, pass through
        if not pitch.voiced:
            return audio_block
        
        # 3. Quantize to scale
        target_freq, target_midi, cents_off = quantize_to_scale(
            pitch.frequency, self.settings.key, self.settings.scale
        )
        
        # 4. Apply threshold
        if abs(cents_off) < self.settings.threshold:
            return audio_block
        
        # 5. Calculate shift ratio
        ratio = 2 ** (cents_off / 1200)
        ratio = np.clip(ratio, 0.5, 2.0)  # ±1 octave max
        
        # 6. Smooth correction
        ratio = self.smoother.process(ratio)
        
        # 7. Pitch shift
        corrected = self.pitch_shifter.shift_streaming(audio_block, ratio)
        
        # 8. Wet/dry mix
        return corrected * self.settings.mix + audio_block * (1 - self.settings.mix)
```

### 7. Harmoniser Processor (`processing/harmoniser.py`)

**Pipeline**:
```python
class HarmoniserProcessor(AudioProcessor):
    def __init__(self, settings, sample_rate, block_size):
        self.pitch_detector = PitchDetector(sample_rate)
        self.voice_manager = VoiceManager(sample_rate, settings.max_voices)
    
    def process(self, audio_block, sample_rate):
        # 1. Detect pitch
        pitch = self.pitch_detector.process(audio_block)
        
        if not pitch.voiced:
            return audio_block * self.settings.lead_mix
        
        # 2. Generate harmony targets
        harmonies = self._generate_harmonies(pitch.frequency)
        
        # 3. Smooth transitions
        harmonies = self._smooth_harmonies(harmonies)
        
        # 4. Process voices
        volumes = [self.settings.lead_mix] + list(self.settings.voice_volumes[1:])
        output = self.voice_manager.process_block(
            audio_block, pitch.frequency, harmonies, volumes
        )
        
        return output
```

### 8. Music Theory (`music/`)

**Modules**:
- `notes.py`: Frequency↔MIDI↔Note name conversions
- `scales.py`: Scale definitions, quantization, membership
- `chords.py`: Chord construction, voicing, diatonic chords
- `intervals.py`: Interval arithmetic, transposition
- `harmony.py`: Harmony rules, voice leading

**Key Abstractions**:
```python
class Scale:
    def __init__(self, root: str, scale_type: str):
        self.root_pc = note_to_pitch_class(root)
        self.intervals = SCALES[scale_type]
    
    def contains(self, midi: int) -> bool: ...
    def nearest_note(self, midi: float) -> int: ...
    def get_degree(self, midi: int) -> int: ...

def quantize_to_scale(midi: float, key: str, scale_type: str) -> int:
    scale = Scale(key, scale_type)
    return scale.nearest_note(midi)
```

## Real-Time Constraints

### Callback Requirements
The PortAudio callback runs on a high-priority thread. **Must not**:
- Allocate memory (numpy arrays, lists)
- Acquire locks (mutexes, threading.Lock)
- Call Python functions that may block (I/O, GC)
- Raise exceptions

**Must**:
- Complete in < 50% of block time
- Use pre-allocated buffers
- Handle errors gracefully (log to ring buffer)

### Buffer Sizing Guidelines
| Block Size | Latency | CPU Budget | Use Case |
|------------|---------|------------|----------|
| 64 | ~1.3ms | ~0.6ms | Ultra-low latency |
| 128 | ~2.7ms | ~1.3ms | Low latency |
| 256 | ~5.3ms | ~2.6ms | **Default, balanced** |
| 512 | ~10.7ms | ~5.3ms | High CPU loads |
| 1024 | ~21.3ms | ~10.6ms | Maximum stability |

## Extending the System

### Adding a New Processor
1. Create `processing/new_effect.py`:
```python
from processing.base import AudioProcessor
import numpy as np

class NewEffectProcessor(AudioProcessor):
    def __init__(self, settings, sample_rate, block_size):
        ...
    
    def process(self, audio_block, sample_rate):
        # Your processing here
        return processed_audio
    
    def reset(self):
        ...
```

2. Add factory function in `auto-tune.py`:
```python
def create_processor(mode, settings, sample_rate, block_size):
    if mode == 'autotune':
        return AutoTuneProcessor(settings.autotune, sample_rate, block_size)
    elif mode == 'harmonise':
        return HarmoniserProcessor(settings.harmoniser, sample_rate, block_size)
    elif mode == 'neweffect':
        return NewEffectProcessor(settings.neweffect, sample_rate, block_size)
```

3. Add CLI flags in `auto-tune.py`

### Adding a New Scale
Edit `music/scales.py`:
```python
SCALES = {
    # ... existing scales ...
    'my_custom_scale': [0, 2, 4, 6, 7, 9, 10],  # Semitone intervals
}
```

### Adding a New Harmony Rule
Edit `music/harmony.py`:
```python
def generate_my_harmony(melody_freq, key, scale_type, ...):
    # Your harmony logic
    return [harmony_freq1, harmony_freq2, ...]
```

## Performance Profiling

### Key Metrics
- **Callback duration**: Time spent in `_callback()`
- **Processing duration**: Time in `processor.process()`
- **Buffer health**: Overrun/underrun counts
- **Latency**: End-to-end delay

### Profiling Tools
```python
# In AudioEngine._callback()
import time
start = time.perf_counter()
# ... processing ...
elapsed = (time.perf_counter() - start) * 1000  # ms
self.stats.processing_time_ms = elapsed
```

## Error Handling

### Audio Callback Errors
- Never raise exceptions
- Log to thread-safe ring buffer
- Fall back to silence or passthrough
- Increment error counters

### Device Errors
- Detect in stream callbacks
- Attempt fallback to default device
- Notify main thread via event queue

### Graceful Degradation
- Pitch detection fails → passthrough
- Pitch shifting fails → passthrough
- Buffer overrun → drop samples, continue
- CPU overload → increase block size (manual)

## Future Architecture Considerations

1. **Plugin System**: Dynamic loading of processor modules
2. **Parameter Automation**: Smooth parameter changes over time
3. **Preset Management**: Save/load processor configurations
4. **MIDI Integration**: External control of harmony/pitch
5. **Multi-channel**: Stereo, surround, ambisonics
6. **GPU Acceleration**: For heavy pitch shifting
7. **Distributed Processing**: Network audio (JackTrip, etc.)