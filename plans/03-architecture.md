# System Architecture

## High-Level Component Diagram
```
┌─────────────────────────────────────────────────────────────────┐
│                        auto-tune.py (CLI)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   argparse  │  │  Settings   │  │   Processor Factory     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AudioEngine                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ AudioInput   │──▶│  Processor   │──▶│ AudioOutput          │  │
│  │ (sounddevice)│  │  (ABC impl)  │  │ (sounddevice)        │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│         │                │                       │              │
│         ▼                ▼                       ▼              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ InputBuffer  │  │  Processing  │  │ OutputBuffer         │  │
│  │ (ring buffer)│  │  Pipeline    │  │ (ring buffer)        │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌────────────┐ ┌───────────┐ ┌──────────┐
       │ Pitch      │ │ Pitch     │ │ Music    │
       │ Detector   │ │ Shifter   │ │ Theory   │
       └────────────┘ └───────────┘ └──────────┘
```

## Module Responsibilities

### `auto-tune.py` - Entry Point
- Parse command-line arguments
- Validate mutually exclusive modes
- Build settings object
- Instantiate processor via factory
- Create and run AudioEngine
- Handle signals (SIGINT, SIGTERM) for clean shutdown

### `audio/engine.py` - Audio Engine
- Manage sounddevice InputStream/OutputStream
- Coordinate callback between input → processor → output
- Handle buffer overruns/underruns
- Measure and report latency
- Thread-safe start/stop

### `audio/input.py` - Microphone Input
- Device enumeration and selection
- Stream configuration (sample rate, channels, blocksize)
- Callback: fills InputBuffer with raw audio

### `audio/output.py` - Speaker Output
- Device enumeration and selection
- Stream configuration
- Callback: pulls from OutputBuffer

### `audio/buffer.py` - Ring Buffers
- Lock-free single-producer/single-consumer ring buffer
- Overrun/underrun detection and statistics
- Configurable capacity (power of 2 for modulo efficiency)

### `processing/base.py` - Processor Interface
```python
class AudioProcessor(ABC):
    @abstractmethod
    def process(self, audio_block: np.ndarray, sample_rate: int) -> np.ndarray: ...
    def reset(self) -> None: ...
    @property
    def latency_samples(self) -> int: ...
    @property
    def name(self) -> str: ...
```

### `processing/pitch_detector.py` - Pitch Detection
- YIN algorithm implementation (or similar)
- Returns: frequency (Hz), confidence (0-1), voiced_flag
- Configurable: min/max frequency, frame size, hop size
- Handles silence/unvoiced gracefully

### `processing/pitch_shifter.py` - Pitch Shifting
- Phase vocoder implementation (STFT-based)
- Preserves timing/formants
- Interface: `shift(audio, ratio, sample_rate) -> shifted_audio`
- Supports real-time streaming with overlap-add

### `processing/autotune.py` - Auto-Tune Processor
- Implements `AudioProcessor`
- Pipeline: detect → quantize → calculate correction → shift → smooth
- Settings: key, scale, correction_speed, correction_threshold

### `processing/harmoniser.py` - Harmoniser Processor
- Implements `AudioProcessor`
- Pipeline: detect → determine harmony notes → shift copies → mix
- Settings: key, scale, intervals, voice_volumes, chord_mode

### `music/scales.py` - Scale Definitions
- Scale classes: Major, Minor, Pentatonic, Blues, Custom
- Methods: `nearest_note(freq)`, `note_in_scale(freq)`, `get_degrees()`

### `music/chords.py` - Chord Definitions
- Chord types: major, minor, diminished, augmented, 7th, etc.
- Methods: `notes_in_chord(root, quality)`, `voice_leading(prev, next)`

### `music/harmony.py` - Harmony Logic
- Interval-based: thirds, fifths, octaves
- Scale-degree based: diatonic thirds, parallel harmony
- Chord-based: harmonize to current chord
- Voice leading for smooth transitions

## Data Flow

### Audio Block Processing (per callback)
```
Input Block (N samples)
       │
       ▼
┌──────────────────┐
│ Pitch Detector   │──▶ f0 (Hz), confidence, voiced
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Musical Quantizer│──▶ target_freq (Hz), correction_cents
│ (scale/key)      │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Pitch Shifter    │──▶ corrected_audio (N samples)
│ (phase vocoder)  │
└──────────────────┘
       │
       ▼
Output Block (N samples)
```

### Harmoniser Data Flow
```
Input Block
       │
       ▼
┌──────────────────┐
│ Pitch Detector   │──▶ f0, confidence
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Harmony Engine   │──▶ [target_freq_1, target_freq_2, ...]
│ (intervals/chord)│
└──────────────────┘
       │
       ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Pitch Shifter 1  │     │ Pitch Shifter 2  │     │ Pitch Shifter N  │
│ (lead/voice 1)   │     │ (harmony 1)      │     │ (harmony N)      │
└──────────────────┘     └──────────────────┘     └──────────────────┘
       │                         │                         │
       └─────────────────────────┼─────────────────────────┘
                                 ▼
                        ┌──────────────────┐
                        │ Mixer + Gain     │
                        │ (prevent clip)   │
                        └──────────────────┘
                                 │
                                 ▼
                          Output Block
```

## Threading Model
- **Main thread**: CLI, engine lifecycle, signal handling
- **Audio callback thread** (PortAudio): Real-time, highest priority
  - Must NOT: allocate memory, lock mutexes, call Python GC, I/O
  - Must: be deterministic, bounded execution time
- **Optional worker thread**: Heavy pitch shifting (if needed)
  - Communicates via lock-free ring buffers
  - Double-buffered to avoid contention

## Configuration System
```
Settings (dataclass)
├── audio: sample_rate, block_size, input_device, output_device, channels
├── autotune: key, scale, correction_speed, threshold, formant_preserve
├── harmoniser: key, scale, intervals, voice_volumes, chord_mode
└── advanced: pitch_detector_params, pitch_shifter_params
```

## Error Handling Strategy
- Audio callback: never raise, log errors to ring buffer for main thread
- Device errors: fallback to default device, notify user
- Processing errors: pass through dry signal, log diagnostic
- Clean shutdown: always close streams, join threads, release PortAudio