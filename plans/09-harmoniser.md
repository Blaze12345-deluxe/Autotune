# Harmoniser Processor Specification

## Processing Pipeline
```
Audio Block (256 samples)
       │
       ▼
┌──────────────────┐
│ Pitch Detector   │──▶ f0, confidence, voiced
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Harmony Engine   │──▶ [target_freq_1, target_freq_2, ...]
│ (Intervals/Chord)│
└──────────────────┘
       │
       ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Pitch Shifter 1  │  │ Pitch Shifter 2  │  │ Pitch Shifter N  │
│ (Lead/Orig)      │  │ (Harmony 1)      │  │ (Harmony N)      │
└──────────────────┘  └──────────────────┘  └──────────────────┘
       │                     │                     │
       └─────────────────────┼─────────────────────┘
                             ▼
                    ┌──────────────────┐
                    │ Mixer + Gain     │
                    │ (Anti-clip)      │
                    └──────────────────┘
                             │
                             ▼
                        Output Block
```

## Configuration
```python
@dataclass
class HarmoniserSettings:
    key: str = "C"                    # Musical key
    scale: str = "major"              # Scale type
    intervals: tuple = (3, 7)         # Semitone intervals above root (major triad)
    voice_volumes: tuple = (1.0, 0.7, 0.7)  # Volume per voice [lead, harm1, harm2...]
    chord_mode: str = "intervals"     # 'intervals', 'scale', 'chord'
    chord_quality: str = "major"      # When chord_mode='chord'
    formant_preserve: bool = True     # Preserve formants on shifted voices
    lead_mix: float = 1.0             # Original voice level
    max_voices: int = 4               # Including lead
```

## Harmony Generation Modes

### 1. Fixed Intervals (Default)
```python
def generate_interval_harmonies(
    root_freq: float,
    intervals: tuple[int, ...],
) -> list[float]:
    """Generate harmony frequencies at fixed semitone intervals."""
    return [root_freq * (2 ** (interval / 12)) for interval in intervals]
```

### 2. Scale-Degree (Diatonic) Harmony
```python
def generate_diatonic_harmonies(
    root_freq: float,
    key: str,
    scale: str,
    degrees: tuple[int, ...] = (2, 4),  # Scale degrees (1=root, 3=third, 5=fifth)
) -> list[float]:
    """Generate harmonies at specific scale degrees."""
    scale_notes = get_scale_notes(key, scale)  # MIDI notes in scale
    root_midi = freq_to_midi(root_freq)
    
    # Find root's position in scale
    root_degree = scale_notes.index(round(root_midi)) if round(root_midi) in scale_notes else 0
    
    harmonies = []
    for degree in degrees:
        target_degree = (root_degree + degree) % len(scale_notes)
        target_midi = scale_notes[target_degree]
        # Adjust octave to be close to root
        while target_midi < root_midi - 6:
            target_midi += 12
        while target_midi > root_midi + 18:
            target_midi -= 12
        harmonies.append(midi_to_freq(target_midi))
    
    return harmonies
```

### 3. Chord-Based Harmony
```python
def generate_chord_harmonies(
    root_freq: float,
    key: str,
    scale: str,
    chord_quality: str = "major",
) -> list[float]:
    """Generate harmonies based on current chord."""
    # Determine chord from scale degree of root
    # Major scale: I=maj, ii=min, iii=min, IV=maj, V=maj, vi=min, vii°=dim
    chord_map = {
        'major': [0, 4, 7],      # Root, M3, P5
        'minor': [0, 3, 7],      # Root, m3, P5
        'diminished': [0, 3, 6], # Root, m3, d5
        'augmented': [0, 4, 8],  # Root, M3, A5
        'dom7': [0, 4, 7, 10],   # Root, M3, P5, m7
        'maj7': [0, 4, 7, 11],   # Root, M3, P5, M7
        'min7': [0, 3, 7, 10],   # Root, m3, P5, m7
    }
    intervals = chord_map.get(chord_quality, [0, 4, 7])
    return generate_interval_harmonies(root_freq, intervals)
```

## Voice Management
```python
class VoiceManager:
    """Manages multiple pitch shifters for parallel harmony voices."""
    
    def __init__(self, sample_rate: int, max_voices: int = 4):
        self.shifters = [PitchShifter(sample_rate) for _ in range(max_voices)]
        self.max_voices = max_voices
    
    def process_block(
        self,
        audio_block: np.ndarray,
        source_freq: float,
        target_freqs: list[float],
        volumes: list[float],
    ) -> np.ndarray:
        """
        Process one block into multiple harmony voices.
        
        Returns: mixed output block
        """
        n_voices = min(len(target_freqs) + 1, self.max_voices)
        output = np.zeros_like(audio_block)
        
        # Voice 0: Original (lead) - can be pitch-corrected or dry
        if volumes[0] > 0:
            output += audio_block * volumes[0]
        
        # Voices 1..N: Harmonies
        for i in range(1, n_voices):
            if i - 1 < len(target_freqs) and volumes[i] > 0:
                ratio = target_freqs[i - 1] / source_freq if source_freq > 0 else 1.0
                ratio = np.clip(ratio, 0.25, 4.0)  # ±2 octaves max
                harmony = self.shifters[i].shift_streaming(audio_block, ratio)
                output += harmony * volumes[i]
        
        return output
    
    def reset(self):
        for shifter in self.shifters:
            shifter.reset()
```

## Mixing & Anti-Clipping
```python
def mix_harmonies(
    voices: list[np.ndarray],
    volumes: list[float],
    limiter_threshold: float = 0.95,
) -> np.ndarray:
    """Mix voices with soft limiting to prevent clipping."""
    # Weighted sum
    mixed = sum(v * vol for v, vol in zip(voices, volumes))
    
    # Peak detection
    peak = np.max(np.abs(mixed))
    
    # Soft limiting if needed
    if peak > limiter_threshold:
        # Soft knee compression
        gain = limiter_threshold / peak
        # Smooth gain reduction
        mixed = np.tanh(mixed * gain) / np.tanh(gain) * limiter_threshold
    
    return mixed
```

## HarmoniserProcessor Class
```python
class HarmoniserProcessor(AudioProcessor):
    def __init__(self, settings: HarmoniserSettings, sample_rate: int, block_size: int):
        self.settings = settings
        self.sample_rate = sample_rate
        self.block_size = block_size
        
        # Components
        self.pitch_detector = PitchDetector(sample_rate)
        self.voice_manager = VoiceManager(sample_rate, settings.max_voices)
        
        # State
        self.last_freq = 0.0
        self.last_harmonies: list[float] = []
    
    def process(self, audio_block: np.ndarray, sample_rate: int) -> np.ndarray:
        # 1. Detect pitch
        pitch_result = self.pitch_detector.process(audio_block)
        
        # 2. If not voiced, pass through lead only
        if not pitch_result.voiced:
            return audio_block * self.settings.lead_mix
        
        # 3. Generate harmony targets
        source_freq = pitch_result.frequency
        
        if self.settings.chord_mode == "intervals":
            harmony_freqs = generate_interval_harmonies(source_freq, self.settings.intervals)
        elif self.settings.chord_mode == "scale":
            harmony_freqs = generate_diatonic_harmonies(
                source_freq, self.settings.key, self.settings.scale, (2, 4)
            )
        elif self.settings.chord_mode == "chord":
            harmony_freqs = generate_chord_harmonies(
                source_freq, self.settings.key, self.settings.scale, self.settings.chord_quality
            )
        else:
            harmony_freqs = []
        
        # 4. Smooth harmony transitions (avoid jumps)
        harmony_freqs = self._smooth_harmonies(harmony_freqs)
        self.last_harmonies = harmony_freqs
        self.last_freq = source_freq
        
        # 5. Process voices
        volumes = [self.settings.lead_mix] + list(self.settings.voice_volumes[1:])
        output = self.voice_manager.process_block(
            audio_block, source_freq, harmony_freqs, volumes
        )
        
        return output
    
    def _smooth_harmonies(self, new_harmonies: list[float], alpha: float = 0.1) -> list[float]:
        """Smooth harmony frequency changes to avoid artifacts."""
        if not self.last_harmonies:
            return new_harmonies
        
        smoothed = []
        for i, new_f in enumerate(new_harmonies):
            if i < len(self.last_harmonies):
                # Exponential smoothing
                smoothed_f = self.last_harmonies[i] + alpha * (new_f - self.last_harmonies[i])
                smoothed.append(smoothed_f)
            else:
                smoothed.append(new_f)
        return smoothed
    
    def reset(self):
        self.pitch_detector.reset()
        self.voice_manager.reset()
        self.last_freq = 0.0
        self.last_harmonies = []
    
    @property
    def latency_samples(self) -> int:
        return self.voice_manager.shifters[0].latency_samples + self.pitch_detector.frame_size
    
    @property
    def name(self) -> str:
        return "Harmoniser"
```

## Volume Balancing Presets
```python
PRESETS = {
    "subtle": {
        "voice_volumes": (1.0, 0.3, 0.2),      # Lead prominent
        "intervals": (3, 7),                    # Third, fifth
    },
    "backup_vocal": {
        "voice_volumes": (1.0, 0.6, 0.6),       # Balanced
        "intervals": (3, 7),
    },
    "choir": {
        "voice_volumes": (0.8, 0.5, 0.5, 0.4),  # Multiple voices
        "intervals": (-12, 3, 7, 12),           # Octave down, third, fifth, octave up
    },
    "power_chord": {
        "voice_volumes": (1.0, 0.8, 0.6),
        "intervals": (7, 12),                   # Fifth, octave
    },
}
```

## Future: MIDI-Controlled Harmony
```python
# Extension point for Phase 7
class MidiHarmoniserProcessor(HarmoniserProcessor):
    def __init__(self, *args, midi_input=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.midi_input = midi_input
        self.current_chord_notes: list[int] = []  # MIDI notes from keyboard
    
    def process(self, audio_block, sample_rate):
        if self.current_chord_notes:
            # Use MIDI notes as harmony targets instead of algorithmic
            harmony_freqs = [midi_to_freq(n) for n in self.current_chord_notes]
            # ... process with these targets
        return super().process(audio_block, sample_rate)
```