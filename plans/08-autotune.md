# Auto-Tune Processor Specification

## Processing Pipeline
```
Audio Block (256 samples)
       │
       ▼
┌──────────────────┐
│ Pitch Detector   │──▶ f0, confidence, voiced
│ (YIN, 2048 frame)│
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Note Quantizer   │──▶ target_freq, target_midi, cents_off
│ (Scale/Key)      │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Correction Logic │──▶ shift_ratio, smoothed_ratio
│ (Speed/Threshold)│
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Pitch Shifter    │──▶ corrected_audio
│ (Phase Vocoder)  │
└──────────────────┘
       │
       ▼
Output Block
```

## Configuration
```python
@dataclass
class AutoTuneSettings:
    key: str = "C"                    # Musical key
    scale: str = "major"              # Scale type
    correction_speed: float = 0.5     # 0.0 (slow/natural) - 1.0 (fast/robotic)
    correction_threshold: float = 25  # Cents: only correct if off by more
    max_correction_cents: float = 600 # Max ±600 cents (±5 semitones)
    formant_preserve: bool = True     # Preserve vocal formants
    mix: float = 1.0                  # Wet/dry mix (1.0 = full correction)
```

## Note Quantization
```python
def quantize_to_scale(
    frequency: float,
    key: str,
    scale: str,
) -> tuple[float, float, float]:
    """
    Returns: (target_freq, target_midi, cents_off)
    """
    # 1. Convert to continuous MIDI
    midi = freq_to_midi(frequency)
    
    # 2. Get allowed MIDI notes for scale/key
    allowed_notes = get_scale_notes(key, scale)  # List of MIDI note numbers
    
    # 3. Find nearest allowed note
    target_midi = min(allowed_notes, key=lambda n: abs(n - midi))
    
    # 4. Calculate cents off
    cents_off = (midi - target_midi) * 100
    
    # 5. Convert back to frequency
    target_freq = midi_to_freq(target_midi)
    
    return target_freq, target_midi, cents_off
```

## Correction Speed Smoothing
```python
class CorrectionSmoother:
    """Exponential smoothing for natural pitch transitions."""
    
    def __init__(self, speed: float, sample_rate: int, block_size: int):
        # Time constant: speed=0 → slow (1000ms), speed=1 → fast (5ms)
        self.tau = 1000 * (1 - speed) + 5  # ms
        self.alpha = 1 - np.exp(-block_size / (sample_rate * self.tau / 1000))
        self.current_ratio = 1.0
    
    def process(self, target_ratio: float) -> float:
        # Exponential smoothing toward target
        self.current_ratio += self.alpha * (target_ratio - self.current_ratio)
        return self.current_ratio
    
    def reset(self):
        self.current_ratio = 1.0
```

## Threshold Gating
```python
def apply_threshold(cents_off: float, threshold: float, max_cents: float) -> float:
    """Return shift ratio (1.0 = no change)."""
    if abs(cents_off) < threshold:
        return 1.0  # No correction
    
    # Limit maximum correction
    cents_off = np.clip(cents_off, -max_cents, max_cents)
    
    # Convert cents to ratio
    return 2 ** (cents_off / 1200)
```

## AutoTuneProcessor Class
```python
class AutoTuneProcessor(AudioProcessor):
    def __init__(self, settings: AutoTuneSettings, sample_rate: int, block_size: int):
        self.settings = settings
        self.sample_rate = sample_rate
        self.block_size = block_size
        
        # Components
        self.pitch_detector = PitchDetector(sample_rate)
        self.pitch_shifter = PitchShifter(sample_rate)
        self.smoother = CorrectionSmoother(
            settings.correction_speed, sample_rate, block_size
        )
        self.scale_notes = get_scale_notes(settings.key, settings.scale)
    
    def process(self, audio_block: np.ndarray, sample_rate: int) -> np.ndarray:
        # 1. Detect pitch
        pitch_result = self.pitch_detector.process(audio_block)
        
        # 2. If not voiced or silent, pass through (maybe with dry mix)
        if not pitch_result.voiced:
            return audio_block * self.settings.mix + audio_block * (1 - self.settings.mix)
        
        # 3. Quantize to scale
        target_freq, target_midi, cents_off = quantize_to_scale(
            pitch_result.frequency, self.settings.key, self.settings.scale
        )
        
        # 4. Apply threshold
        shift_ratio = apply_threshold(
            cents_off, self.settings.correction_threshold, self.settings.max_correction_cents
        )
        
        # 5. Smooth correction
        shift_ratio = self.smoother.process(shift_ratio)
        
        # 6. Pitch shift
        if abs(shift_ratio - 1.0) > 0.001:  # Only shift if meaningful
            corrected = self.pitch_shifter.shift_streaming(audio_block, shift_ratio)
        else:
            corrected = audio_block
        
        # 7. Wet/dry mix
        output = corrected * self.settings.mix + audio_block * (1 - self.settings.mix)
        
        return output
    
    def reset(self):
        self.pitch_detector.reset()
        self.pitch_shifter.reset()
        self.smoother.reset()
    
    @property
    def latency_samples(self) -> int:
        return self.pitch_shifter.latency_samples + self.pitch_detector.frame_size
    
    @property
    def name(self) -> str:
        return "AutoTune"
```

## Edge Cases
| Scenario | Behavior |
|----------|----------|
| Silence (RMS < -60dB) | Pass through dry |
| Unvoiced (confidence < 0.3) | Pass through dry |
| Octave error (confidence low) | Hold previous correction |
| Rapid pitch changes | Smoother handles naturally |
| Note outside range | Clamp to nearest scale note |
| Scale change at runtime | Recompute scale_notes, reset smoother |

## "T-Pain" Mode (Fast Correction)
```python
# Settings for robotic effect
AutoTuneSettings(
    correction_speed=1.0,      # Instant correction
    correction_threshold=0,    # Correct everything
    max_correction_cents=1200, # Full octave
    mix=1.0,                   # 100% wet
)
```

## Natural Mode (Subtle Correction)
```python
# Settings for transparent correction
AutoTuneSettings(
    correction_speed=0.2,      # Slow, natural
    correction_threshold=50,   # Only correct obvious errors
    max_correction_cents=200,  # Max 2 semitones
    mix=0.7,                   # Blend with dry
)
```