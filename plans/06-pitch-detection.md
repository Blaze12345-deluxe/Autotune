# Pitch Detection Specification

## Algorithm: YIN (Yet Another Algorithm for Pitch Tracking)

### Why YIN?
- Robust for voice (handles formants well)
- Computationally efficient O(N log N) with FFT
- Returns confidence measure (aperiodicity)
- Well-documented, reference implementations available
- Better than autocorrelation for voiced/unvoiced discrimination

### YIN Algorithm Steps
1. **Difference function**: d(τ) = Σ(x[n] - x[n+τ])² for τ = 0..W
2. **Cumulative mean normalized difference**: d'(τ) = d(τ) / (1/τ Σ d(j))
3. **Absolute threshold**: Find first τ where d'(τ) < threshold (0.1)
4. **Parabolic interpolation**: Refine τ for sub-sample accuracy
5. **Aperiodicity/confidence**: d'(τ) at minimum → confidence = 1 - d'(τ)

## Implementation Interface
```python
@dataclass
class PitchResult:
    frequency: float      # Hz, 0 if unvoiced/silence
    confidence: float     # 0.0 - 1.0
    voiced: bool          # True if pitched sound detected
    rms: float            # RMS energy of block

class PitchDetector:
    def __init__(
        self,
        sample_rate: int,
        frame_size: int = 2048,      # YIN window (W)
        hop_size: int = 512,         # Overlap
        min_freq: float = 65.0,      # C2
        max_freq: float = 1050.0,    # C6
        threshold: float = 0.1,      # YIN threshold
    ): ...
    
    def process(self, audio_block: np.ndarray) -> PitchResult:
        """Process one block, return pitch estimate."""
    
    def reset(self) -> None:
        """Clear internal state (buffers)."""
```

## Configuration Parameters
| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `frame_size` | 2048 | 1024-4096 | Frequency resolution vs latency |
| `hop_size` | 512 | 128-1024 | Update rate vs CPU |
| `min_freq` | 65 Hz | 40-100 | Lowest detectable pitch |
| `max_freq` | 1050 Hz | 800-2000 | Highest detectable pitch |
| `threshold` | 0.1 | 0.05-0.2 | Voiced/unvoiced boundary |

## Processing Strategy for Real-Time
- **Frame size > block size**: Need to accumulate blocks
- **Internal buffer**: Accumulate until frame_size reached
- **Hop processing**: Process every hop_size samples
- **Output**: Latest pitch result for each output block

```
Input blocks (256) ──▶ Accumulate ──▶ 2048 frame ──▶ YIN ──▶ PitchResult
       │                    │               │
       │                    ▼               ▼
       │             Every 512          Every 512
       │             samples            samples
       ▼                    │               │
Output (256) ◀─── Interpolate/hold ──────┘
```

## Silence/Unvoiced Handling
- **RMS gate**: If RMS < -60 dBFS → silence, return frequency=0, voiced=False
- **Confidence gate**: If confidence < 0.3 → unvoiced, return frequency=0, voiced=False
- **Transition smoothing**: Hold previous pitch for 2-3 blocks during unvoiced
- **Octave error correction**: Check 2× and 0.5× frequency if confidence low

## Frequency to MIDI Note Conversion
```python
def freq_to_midi(freq: float) -> float:
    """Convert Hz to continuous MIDI note number."""
    if freq <= 0:
        return 0.0
    return 69 + 12 * np.log2(freq / 440.0)

def midi_to_freq(midi: float) -> float:
    """Convert MIDI note to Hz."""
    return 440.0 * 2**((midi - 69) / 12)

def cents_between(f1: float, f2: float) -> float:
    """Cents difference from f1 to f2."""
    return 1200 * np.log2(f2 / f1)
```

## Testing Vectors
| Input | Expected Frequency | Expected Confidence |
|-------|-------------------|---------------------|
| Sine 440 Hz | 440 ± 1 Hz | > 0.9 |
| Sine 220 Hz | 220 ± 1 Hz | > 0.9 |
| White noise | 0 | < 0.1 |
| Silence | 0 | 0.0 |
| Speech "ah" | ~F0 ± 5 Hz | > 0.6 |
| Speech "s" | 0 | < 0.2 |

## Performance Requirements
- **CPU**: < 1ms per 2048-frame at 48kHz (single core)
- **Memory**: < 1 MB working memory
- **Latency**: 1 frame (2048 samples = 42.7ms) - can be reduced with smaller frame

## Future Improvements
- **CREPE**: Deep learning pitch tracker (higher accuracy, more CPU)
- **SWIPE**: Sawtooth waveform inspired pitch estimator
- **PYIN**: Probabilistic YIN with HMM smoothing
- **Multi-pitch**: Detect multiple simultaneous voices (for harmoniser input)