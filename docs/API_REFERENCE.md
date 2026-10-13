# API Reference

## Core Classes

### AudioEngine
```python
class AudioEngine:
    def __init__(self, processor: AudioProcessor, settings: Settings):
        """Create audio engine with processor and settings."""
    
    def start(self) -> None:
        """Open audio streams and start processing."""
    
    def stop(self) -> None:
        """Stop streams and release resources."""
    
    def run_until_interrupted(self) -> None:
        """Block until SIGINT/SIGTERM received."""
    
    @property
    def stats(self) -> EngineStats:
        """Current engine statistics."""
```

### EngineStats
```python
@dataclass
class EngineStats:
    blocks_processed: int = 0
    input_overruns: int = 0
    output_underruns: int = 0
    avg_processing_ms: float = 0.0
    max_processing_ms: float = 0.0
    current_latency_ms: float = 0.0
    cpu_percent: float = 0.0
```

### Settings
```python
@dataclass
class Settings:
    # Audio
    sample_rate: int = 48000
    block_size: int = 256
    input_device: str | int | None = None
    output_device: str | int | None = None
    channels: int = 1
    
    # Mode
    mode: str = "autotune"  # "autotune" | "harmonise"
    
    # Auto-Tune
    autotune: AutoTuneSettings = field(default_factory=AutoTuneSettings)
    
    # Harmoniser
    harmoniser: HarmoniserSettings = field(default_factory=HarmoniserSettings)
    
    # Advanced
    pitch_detector: PitchDetectorSettings = field(default_factory=PitchDetectorSettings)
    pitch_shifter: PitchShifterSettings = field(default_factory=PitchShifterSettings)
```

## Processing

### AudioProcessor (Abstract Base)
```python
class AudioProcessor(ABC):
    @abstractmethod
    def process(self, audio_block: np.ndarray, sample_rate: int) -> np.ndarray:
        """Process one audio block. Returns same shape array."""
    
    def reset(self) -> None:
        """Reset internal state."""
    
    @property
    def latency_samples(self) -> int:
        """Algorithmic latency in samples."""
    
    @property
    def name(self) -> str:
        """Processor name for display."""
```

### PitchDetector
```python
class PitchDetector:
    def __init__(
        self,
        sample_rate: int,
        frame_size: int = 2048,
        hop_size: int = 512,
        min_freq: float = 65.0,
        max_freq: float = 1050.0,
        threshold: float = 0.1,
    ):
        """Initialize YIN pitch detector."""
    
    def process(self, audio_block: np.ndarray) -> PitchResult:
        """Process audio block, return pitch estimate."""
    
    def reset(self) -> None:
        """Clear internal buffers."""
```

### PitchResult
```python
@dataclass
class PitchResult:
    frequency: float      # Fundamental frequency in Hz (0 if unvoiced)
    confidence: float     # Confidence 0.0-1.0
    voiced: bool          # True if pitched sound detected
    rms: float            # RMS energy of block
```

### PitchShifter
```python
class PitchShifter:
    def __init__(
        self,
        sample_rate: int,
        fft_size: int = 2048,
        hop_size: int = 512,
        window: str = 'hann',
    ):
        """Initialize phase vocoder pitch shifter."""
    
    def shift(
        self,
        audio: np.ndarray,
        ratio: float,
        preserve_formants: bool = True,
    ) -> np.ndarray:
        """Pitch shift audio by ratio (offline/batch)."""
    
    def shift_streaming(
        self,
        audio_block: np.ndarray,
        ratio: float,
    ) -> np.ndarray:
        """Pitch shift in streaming mode (maintains phase continuity)."""
    
    def reset(self) -> None:
        """Clear phase memory and overlap buffers."""
    
    @property
    def latency_samples(self) -> int:
        return self.fft_size
```

## Auto-Tune

### AutoTuneSettings
```python
@dataclass
class AutoTuneSettings:
    key: str = "C"
    scale: str = "major"
    correction_speed: float = 0.5      # 0.0 (slow) to 1.0 (fast)
    threshold: float = 25.0             # Cents threshold
    max_correction_cents: float = 600.0 # Max correction
    formant_preserve: bool = True
    mix: float = 1.0                    # Wet/dry mix
```

### AutoTuneProcessor
```python
class AutoTuneProcessor(AudioProcessor):
    def __init__(self, settings: AutoTuneSettings, sample_rate: int, block_size: int):
        """Create Auto-Tune processor."""
    
    def process(self, audio_block: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply pitch correction to audio block."""
    
    def reset(self) -> None:
        """Reset detector, shifter, and smoother."""
```

## Harmoniser

### HarmoniserSettings
```python
@dataclass
class HarmoniserSettings:
    key: str = "C"
    scale: str = "major"
    intervals: tuple = (3, 7)           # Semitone intervals
    voice_volumes: tuple = (1.0, 0.7, 0.7)  # Per-voice volumes
    chord_mode: str = "intervals"       # "intervals" | "scale" | "chord"
    chord_quality: str = "major"        # For chord_mode="chord"
    formant_preserve: bool = True
    lead_mix: float = 1.0               # Original voice level
    max_voices: int = 4                 # Including lead
```

### HarmoniserProcessor
```python
class HarmoniserProcessor(AudioProcessor):
    def __init__(self, settings: HarmoniserSettings, sample_rate: int, block_size: int):
        """Create Harmoniser processor."""
    
    def process(self, audio_block: np.ndarray, sample_rate: int) -> np.ndarray:
        """Generate harmonies and mix with original."""
    
    def reset(self) -> None:
        """Reset detector and all voice shifters."""
```

### VoiceManager
```python
class VoiceManager:
    def __init__(self, sample_rate: int, max_voices: int = 4):
        """Manage multiple pitch shifters for harmony voices."""
    
    def process_block(
        self,
        audio_block: np.ndarray,
        source_freq: float,
        target_freqs: list[float],
        volumes: list[float],
    ) -> np.ndarray:
        """Process block into multiple harmony voices."""
    
    def reset(self) -> None:
        """Reset all voice shifters."""
```

## Music Theory

### Notes
```python
def midi_to_freq(midi: float) -> float:
    """Convert MIDI note number to frequency in Hz."""

def freq_to_midi(freq: float) -> float:
    """Convert frequency in Hz to MIDI note number."""

def note_name_to_midi(note_name: str) -> int:
    """Convert note name (e.g., 'C4', 'F#3') to MIDI number."""

def midi_to_note_name(midi: int, prefer_sharps: bool = True) -> str:
    """Convert MIDI number to note name."""

def cents_to_ratio(cents: float) -> float:
    """Convert cents to frequency ratio."""

def ratio_to_cents(ratio: float) -> float:
    """Convert frequency ratio to cents."""
```

### Scales
```python
class Scale:
    def __init__(self, root: str, scale_type: str):
        """Create scale with root note and type."""
    
    def contains(self, midi: int) -> bool:
        """Check if MIDI note is in scale."""
    
    def nearest_note(self, midi: float) -> int:
        """Find nearest scale note to given MIDI."""
    
    def get_degree(self, midi: int) -> int:
        """Get scale degree (1-7) of note, 0 if not in scale."""

def get_scale_notes(key: str, scale_type: str) -> list[int]:
    """Get all MIDI notes in scale across piano range."""

def quantize_to_scale(midi: float, key: str, scale_type: str) -> int:
    """Quantize continuous MIDI to nearest scale note."""
```

### Chords
```python
class Chord:
    def __init__(self, root_midi: int, quality: str, scale: Scale = None):
        """Create chord with root, quality, and optional scale context."""
    
    def get_notes(self, octave: int = 4) -> list[int]:
        """Get chord notes in specific octave."""
    
    def invert(self, inversion: int) -> list[int]:
        """Get chord notes with given inversion."""
    
    def transpose(self, semitones: int) -> Chord:
        """Return transposed chord."""

def get_diatonic_chords(key: str, scale_type: str) -> dict[int, Chord]:
    """Get all diatonic chords for key/scale."""
```

### Intervals
```python
def transpose_freq(freq: float, semitones: int) -> float:
    """Transpose frequency by semitones."""

def interval_between(f1: float, f2: float) -> float:
    """Semitones between two frequencies."""

def interval_name(semitones: int) -> str:
    """Get interval name from semitone count."""
```

### Harmony
```python
def generate_harmony_notes(
    melody_freq: float,
    key: str,
    scale_type: str,
    rule: str = 'parallel_thirds',
    voices: int = 2,
) -> list[float]:
    """Generate harmony frequencies for melody note."""

def smooth_voice_leading(
    prev_harmonies: list[float],
    new_harmonies: list[float],
    max_jump_semitones: float = 6,
) -> list[float]:
    """Adjust harmony octaves for smooth voice leading."""
```

## Audio I/O

### RingBuffer
```python
class RingBuffer:
    def __init__(self, capacity: int, channels: int = 1, dtype=np.float32):
        """Create lock-free ring buffer."""
    
    def write(self, data: np.ndarray) -> int:
        """Write data, return samples written."""
    
    def read(self, n_samples: int) -> np.ndarray:
        """Read data, zero-pad on underrun."""
    
    @property
    def available(self) -> int:
        """Samples available to read."""
    
    @property
    def free(self) -> int:
        """Free space for writing."""
```

### Device Management
```python
def list_audio_devices() -> list[DeviceInfo]:
    """List all available audio devices."""

def get_default_input_device() -> DeviceInfo:
    """Get default input device."""

def get_default_output_device() -> DeviceInfo:
    """Get default output device."""

def find_device(query: str) -> DeviceInfo | None:
    """Find device by ID or name substring."""
```

### DeviceInfo
```python
@dataclass
class DeviceInfo:
    index: int
    name: str
    host_api: str
    max_input_channels: int
    max_output_channels: int
    default_sample_rate: float
    default_low_input_latency: float
    default_low_output_latency: float
```

## Utility Functions

### Signal Processing
```python
def db_to_amplitude(db: float) -> float:
    """Convert dB to linear amplitude."""

def amplitude_to_db(amp: float) -> float:
    """Convert linear amplitude to dB."""

def rms(audio: np.ndarray) -> float:
    """Calculate RMS of audio block."""

def peak_normalize(audio: np.ndarray, target: float = 0.95) -> np.ndarray:
    """Normalize audio to target peak level."""

def soft_clip(audio: np.ndarray, threshold: float = 0.95) -> np.ndarray:
    """Apply soft clipping/limiting."""
```

## Exceptions
```python
class AutoTuneError(Exception):
    """Base exception for Auto-Tune errors."""

class AudioDeviceError(AutoTuneError):
    """Audio device error."""

class ProcessingError(AutoTuneError):
    """Signal processing error."""

class ConfigurationError(AutoTuneError):
    """Invalid configuration error."""
```

## Version Information
```python
__version__ = "0.1.0"

def get_version() -> str:
    """Get version string."""
```