# Pitch Shifting Specification

## Algorithm: Phase Vocoder (STFT-based)

### Why Phase Vocoder?
- Preserves timing (unlike resampling)
- Preserves formants (with corrections)
- Well-understood, many reference implementations
- Streaming-friendly with overlap-add
- Can achieve high quality with sufficient overlap

## Core Concept
```
Time Domain                    Frequency Domain
┌──────────────┐              ┌──────────────┐
│ Audio Block  │ ──STFT──▶    │ Magnitude    │
│ (N samples)  │              │ Phase        │
└──────────────┘              └──────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
             Phase Advance      Magnitude         Phase
             (freq scaling)     Scaling           Locking
                    │                │                │
                    └────────────────┼────────────────┘
                                     ▼
                              ┌──────────────┐
                              │ Inverse STFT │
                              └──────────────┘
                                     │
                                     ▼
                              ┌──────────────┐
                              │ Overlap-Add  │
                              │ Reconstruction │
                              └──────────────┘
```

## Implementation Interface
```python
@dataclass
class ShiftConfig:
    ratio: float              # Pitch ratio (2.0 = octave up, 0.5 = octave down)
    preserve_formants: bool   # Formant correction
    fft_size: int             # STFT frame size (1024, 2048)
    hop_size: int             # STFT hop (256, 512)
    window: str               # 'hann', 'hamming', 'blackman'

class PitchShifter:
    def __init__(
        self,
        sample_rate: int,
        fft_size: int = 2048,
        hop_size: int = 512,
        window: str = 'hann',
    ): ...
    
    def shift(
        self,
        audio: np.ndarray,
        ratio: float,
        preserve_formants: bool = True,
    ) -> np.ndarray:
        """Pitch shift audio by ratio. Returns same-length array."""
    
    def shift_streaming(
        self,
        audio_block: np.ndarray,
        ratio: float,
    ) -> np.ndarray:
        """Streaming version - maintains phase continuity across blocks."""
    
    def reset(self) -> None:
        """Clear phase memory, overlap buffers."""
    
    @property
    def latency_samples(self) -> int:
        """Algorithmic latency (fft_size)."""
```

## Phase Vocoder Steps

### 1. STFT Analysis
```python
def stft(x, fft_size, hop_size, window):
    frames = frame_signal(x, fft_size, hop_size, window)
    X = np.fft.rfft(frames, axis=-1)
    magnitude = np.abs(X)
    phase = np.angle(X)
    return magnitude, phase
```

### 2. Phase Advance (Frequency Scaling)
```python
# Expected phase advance per hop at analysis rate
expected_phase_advance = 2 * np.pi * np.arange(fft_size//2 + 1) * hop_size / fft_size

# Actual phase difference
phase_diff = np.diff(phase, axis=0, prepend=phase[0:1])
phase_diff = wrap_to_pi(phase_diff - expected_phase_advance)

# True frequency per bin
true_freq = expected_phase_advance + phase_diff
true_freq = true_freq * ratio  # Scale frequencies

# Accumulate phase for synthesis
synthesis_phase = np.cumsum(true_freq, axis=0)
synthesis_phase = wrap_to_pi(synthesis_phase)
```

### 3. Formant Preservation (Optional)
- **Spectral envelope**: Compute cepstrum or LPC of magnitude
- **Warping**: Stretch/compress envelope inversely to pitch shift
- **Application**: Multiply shifted magnitude by warped envelope

### 4. ISTFT Synthesis
```python
def istft(magnitude, phase, fft_size, hop_size, window):
    X = magnitude * np.exp(1j * phase)
    frames = np.fft.irfft(X, n=fft_size, axis=-1)
    x = overlap_add(frames, hop_size, window)
    return x
```

## Streaming Considerations

### Overlap-Add Buffer Management
```python
class StreamingPhaseVocoder:
    def __init__(self, fft_size, hop_size):
        self.fft_size = fft_size
        self.hop_size = hop_size
        self.analysis_buffer = np.zeros(fft_size)
        self.synthesis_buffer = np.zeros(fft_size)
        self.phase_accumulator = np.zeros(fft_size // 2 + 1)
        self.prev_phase = np.zeros(fft_size // 2 + 1)
    
    def process_block(self, input_block, ratio):
        # Fill analysis buffer
        # Process complete frames
        # Return available output samples
        # Maintain phase continuity
```

### Block Synchronization
- Input block size ≠ hop_size typically
- Internal buffering required
- Output block size = input block size (for engine)
- Phase accumulator persists across blocks

## Quality Parameters

| Parameter | Low Quality | Medium | High Quality |
|-----------|-------------|--------|--------------|
| `fft_size` | 1024 | 2048 | 4096 |
| `hop_size` | fft_size/4 | fft_size/4 | fft_size/8 |
| `window` | Hann | Hann | Blackman-Harris |
| Formant correction | No | Yes | Yes + cepstral |

## Latency
- **Algorithmic**: fft_size samples (2048 @ 48kHz = 42.7ms)
- **Can reduce**: Smaller fft_size, but worse frequency resolution
- **Trade-off**: 1024 frame = 21ms latency, poorer low-freq resolution

## Testing Vectors
| Input | Ratio | Expected Output |
|-------|-------|-----------------|
| Sine 440 Hz | 2.0 | Sine 880 Hz, same duration |
| Sine 440 Hz | 0.5 | Sine 220 Hz, same duration |
| Speech | 1.0 | Identical (within numerical precision) |
| Click/transient | Any | Preserved timing, no smearing |

## Performance Targets
- **CPU**: < 2ms per 256-sample block at 48kHz (fft=2048, hop=512)
- **Memory**: ~2-4 MB for buffers
- **Quality**: PESQ > 3.5 for ±1 octave shifts

## Alternative: Rubber Band Library
```python
# When quality is paramount and CPU allows
import pyrubberband as rubberband

def shift_rubberband(audio, ratio, sr):
    return rubberband.pitch_shift(audio, sr, n_semitones=12*np.log2(ratio))
```
- Pros: Best quality, handles transients well
- Cons: Not streaming-friendly, higher latency, GPL license

## Integration with Processor
```python
# In autotune.py
def correct_pitch(audio_block, target_freq, source_freq, settings):
    if source_freq <= 0:
        return audio_block  # No pitch detected
    
    ratio = target_freq / source_freq
    # Limit correction range
    ratio = np.clip(ratio, 0.5, 2.0)  # ±1 octave max
    
    # Smooth ratio based on correction speed
    ratio = smooth_ratio(ratio, settings.correction_speed)
    
    return pitch_shifter.shift_streaming(audio_block, ratio)
```