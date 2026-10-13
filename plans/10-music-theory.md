# Music Theory Module Specification

## Overview
The `music/` package provides musical intelligence: scales, chords, intervals, and harmony rules. Pure Python, no audio dependencies, fully testable.

## Module Structure
```
music/
├── __init__.py         # Public API exports
├── notes.py            # Note names, frequencies, MIDI conversion
├── scales.py           # Scale definitions and operations
├── chords.py           # Chord definitions and voicing
├── intervals.py        # Interval arithmetic
└── harmony.py          # Harmony generation rules
```

## Notes Module (`notes.py`)

### Constants
```python
# Note names (sharps and flats)
NOTE_NAMES_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
NOTE_NAMES_FLAT = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']

# MIDI note 69 = A4 = 440 Hz
A4_MIDI = 69
A4_FREQ = 440.0

# Frequency range for voice
VOICE_MIN_FREQ = 65.41   # C2
VOICE_MAX_FREQ = 1046.50 # C6
```

### Core Functions
```python
def note_name_to_midi(note_name: str) -> int:
    """Convert 'C4', 'F#3', 'Bb5' to MIDI note number."""
    # Parse note letter, accidental, octave
    # C4 = 60, A4 = 69

def midi_to_note_name(midi: int, prefer_sharps: bool = True) -> str:
    """Convert MIDI note to 'C4' format."""

def midi_to_freq(midi: float) -> float:
    """MIDI note (can be fractional) to Hz."""
    return A4_FREQ * 2 ** ((midi - A4_MIDI) / 12)

def freq_to_midi(freq: float) -> float:
    """Hz to continuous MIDI note number."""
    return A4_MIDI + 12 * np.log2(freq / A4_FREQ)

def cents_to_ratio(cents: float) -> float:
    """Cents to frequency ratio."""
    return 2 ** (cents / 1200)

def ratio_to_cents(ratio: float) -> float:
    """Frequency ratio to cents."""
    return 1200 * np.log2(ratio)
```

## Scales Module (`scales.py`)

### Scale Definitions
```python
# Scale intervals in semitones from root
SCALES = {
    # Major modes
    'major': [0, 2, 4, 5, 7, 9, 11],           # Ionian
    'minor': [0, 2, 3, 5, 7, 8, 10],           # Natural minor (Aeolian)
    'harmonic_minor': [0, 2, 3, 5, 7, 8, 11],  # Raised 7th
    'melodic_minor': [0, 2, 3, 5, 7, 9, 11],   # Raised 6th, 7th ascending
    
    # Pentatonic
    'pentatonic_major': [0, 2, 4, 7, 9],
    'pentatonic_minor': [0, 3, 5, 7, 10],
    'blues': [0, 3, 5, 6, 7, 10],              # Minor pentatonic + blue note
    
    # Modes
    'dorian': [0, 2, 3, 5, 7, 9, 10],
    'phrygian': [0, 1, 3, 5, 7, 8, 10],
    'lydian': [0, 2, 4, 6, 7, 9, 11],
    'mixolydian': [0, 2, 4, 5, 7, 9, 10],
    'locrian': [0, 1, 3, 5, 6, 8, 10],
    
    # Other
    'chromatic': list(range(12)),
    'whole_tone': [0, 2, 4, 6, 8, 10],
    'diminished': [0, 2, 3, 5, 6, 8, 9, 11],   # Half-whole
}
```

### Scale Class
```python
class Scale:
    def __init__(self, root: str, scale_type: str):
        self.root = note_name_to_midi(root + '4') % 12  # Pitch class
        self.scale_type = scale_type
        self.intervals = SCALES[scale_type]
        self._build_note_set()
    
    def _build_note_set(self):
        """Build set of all MIDI notes in this scale across piano range."""
        self.notes = set()
        for octave in range(0, 11):  # MIDI octaves 0-10
            for interval in self.intervals:
                midi = self.root + interval + octave * 12
                if 0 <= midi <= 127:
                    self.notes.add(midi)
        self.sorted_notes = sorted(self.notes)
    
    def contains(self, midi: int) -> bool:
        """Check if MIDI note is in scale."""
        return midi in self.notes
    
    def nearest_note(self, midi: float) -> int:
        """Find nearest scale note to given MIDI (can be fractional)."""
        return min(self.sorted_notes, key=lambda n: abs(n - midi))
    
    def get_degree(self, midi: int) -> int:
        """Get scale degree (1-7) of a note, or 0 if not in scale."""
        pc = midi % 12
        for i, interval in enumerate(self.intervals):
            if (self.root + interval) % 12 == pc:
                return i + 1
        return 0
    
    def get_chord(self, degree: int, quality: str = 'triad') -> 'Chord':
        """Build chord on scale degree."""
        root_midi = self.sorted_notes[degree - 1]  # Approximate
        return Chord(root_midi, quality, self)
```

### Helper Functions
```python
def get_scale_notes(key: str, scale_type: str) -> list[int]:
    """Get all MIDI notes in scale for given key."""
    scale = Scale(key, scale_type)
    return scale.sorted_notes

def quantize_to_scale(midi: float, key: str, scale_type: str) -> int:
    """Quantize continuous MIDI to nearest scale note."""
    scale = Scale(key, scale_type)
    return scale.nearest_note(midi)
```

## Chords Module (`chords.py`)

### Chord Definitions
```python
# Chord quality intervals from root (semitones)
CHORD_QUALITIES = {
    # Triads
    'major': [0, 4, 7],
    'minor': [0, 3, 7],
    'diminished': [0, 3, 6],
    'augmented': [0, 4, 8],
    
    # Seventh chords
    'dom7': [0, 4, 7, 10],
    'maj7': [0, 4, 7, 11],
    'min7': [0, 3, 7, 10],
    'min_maj7': [0, 3, 7, 11],
    'half_dim7': [0, 3, 6, 10],  # m7b5
    'dim7': [0, 3, 6, 9],
    
    # Extensions
    '9': [0, 4, 7, 10, 14],
    'maj9': [0, 4, 7, 11, 14],
    'min9': [0, 3, 7, 10, 14],
    '13': [0, 4, 7, 10, 14, 21],
}
```

### Chord Class
```python
class Chord:
    def __init__(self, root_midi: int, quality: str, scale: Scale = None):
        self.root = root_midi
        self.quality = quality
        self.scale = scale
        self.intervals = CHORD_QUALITIES[quality]
        self.notes = [root_midi + i for i in self.intervals]
    
    def get_notes(self, octave: int = 4) -> list[int]:
        """Get chord notes in specific octave range."""
        base = self.root % 12 + octave * 12
        return [base + i for i in self.intervals]
    
    def transpose(self, semitones: int) -> 'Chord':
        return Chord(self.root + semitones, self.quality, self.scale)
    
    def invert(self, inversion: int) -> list[int]:
        """Return chord notes with given inversion (0=root, 1=first, etc.)."""
        notes = self.notes.copy()
        for _ in range(inversion):
            notes.append(notes.pop(0) + 12)
        return notes
    
    def voice_lead_to(self, target: 'Chord') -> list[int]:
        """Find smoothest voice leading to target chord."""
        # Minimize total voice movement
        # This is a simplified greedy approach
        pass
```

### Diatonic Chords
```python
def get_diatonic_chords(key: str, scale_type: str) -> dict[int, Chord]:
    """Get all diatonic chords for a key/scale."""
    scale = Scale(key, scale_type)
    chords = {}
    
    # Major scale chord qualities
    if scale_type in ['major', 'ionian']:
        qualities = ['major', 'minor', 'minor', 'major', 'major', 'minor', 'diminished']
    elif scale_type in ['minor', 'aeolian']:
        qualities = ['minor', 'diminished', 'major', 'minor', 'minor', 'major', 'major']
    elif scale_type == 'harmonic_minor':
        qualities = ['minor', 'diminished', 'augmented', 'minor', 'major', 'major', 'diminished']
    else:
        qualities = ['major'] * 7  # Fallback
    
    for degree, quality in enumerate(qualities, 1):
        root = scale.sorted_notes[degree - 1]
        chords[degree] = Chord(root, quality, scale)
    
    return chords
```

## Intervals Module (`intervals.py`)

### Interval Arithmetic
```python
# Interval names to semitones
INTERVALS = {
    'unison': 0, 'minor_second': 1, 'major_second': 2,
    'minor_third': 3, 'major_third': 4, 'perfect_fourth': 5,
    'tritone': 6, 'perfect_fifth': 7, 'minor_sixth': 8,
    'major_sixth': 9, 'minor_seventh': 10, 'major_seventh': 11,
    'octave': 12, 'minor_ninth': 13, 'major_ninth': 14,
    'perfect_eleventh': 17, 'major_thirteenth': 21,
}

# Reverse lookup
SEMITONES_TO_INTERVAL = {v: k for k, v in INTERVALS.items()}

def transpose_freq(freq: float, semitones: int) -> float:
    """Transpose frequency by semitones."""
    return freq * (2 ** (semitones / 12))

def interval_between(f1: float, f2: float) -> float:
    """Semitones between two frequencies."""
    return 12 * np.log2(f2 / f1)

def interval_name(semitones: int) -> str:
    """Get interval name from semitones (mod 12)."""
    return SEMITONES_TO_INTERVAL.get(semitones % 12, f'{semitones}_semitones')
```

## Harmony Module (`harmony.py`)

### Harmony Rules
```python
# Traditional harmony intervals above melody note
HARMONY_INTERVALS = {
    'parallel_thirds': [3, 4],      # Minor/major third (scale-dependent)
    'parallel_sixths': [9, 8],      # Minor/major sixth
    'triad': [4, 7],                # Root position major triad
    'first_inversion': [3, 8],      # Third in bass
    'second_inversion': [5, 9],     # Fifth in bass
    'power_chord': [7, 12],         # Fifth, octave
    'quartal': [5, 10],             # Fourth, minor seventh
    'quintal': [7, 14],             # Fifth, major ninth
}

def generate_harmony_notes(
    melody_freq: float,
    key: str,
    scale_type: str,
    rule: str = 'parallel_thirds',
    voices: int = 2,
) -> list[float]:
    """Generate harmony frequencies for a melody note."""
    scale = Scale(key, scale_type)
    melody_midi = freq_to_midi(melody_freq)
    melody_degree = scale.get_degree(round(melody_midi))
    
    if rule == 'parallel_thirds':
        # Diatonic third above
        if melody_degree > 0:
            third_degree = (melody_degree + 1) % 7 + 1
            third_midi = scale.sorted_notes[third_degree - 1]
            # Adjust octave
            while third_midi < melody_midi:
                third_midi += 12
            return [midi_to_freq(third_midi)]
    
    elif rule == 'triad':
        # Build triad on melody note's scale degree
        if melody_degree > 0:
            chord = scale.get_chord(melody_degree)
            return [midi_to_freq(n) for n in chord.notes[1:]]  # Exclude root
    
    # Fixed intervals fallback
    intervals = HARMONY_INTERVALS.get(rule, [3, 7])
    return [transpose_freq(melody_freq, i) for i in intervals[:voices]]
```

### Voice Leading
```python
def smooth_voice_leading(
    prev_harmonies: list[float],
    new_harmonies: list[float],
    max_jump_semitones: float = 6,
) -> list[float]:
    """Adjust harmony octaves for smooth voice leading."""
    smoothed = []
    for i, new_f in enumerate(new_harmonies):
        if i < len(prev_harmonies):
            prev_f = prev_harmonies[i]
            # Find closest octave
            while interval_between(prev_f, new_f) > max_jump_semitones:
                new_f *= 0.5  # Down an octave
            while interval_between(prev_f, new_f) < -max_jump_semitones:
                new_f *= 2.0  # Up an octave
        smoothed.append(new_f)
    return smoothed
```

## Key/Scale Validation
```python
VALID_KEYS = ['C', 'C#', 'Db', 'D', 'D#', 'Eb', 'E', 'F', 'F#', 'Gb', 'G', 'G#', 'Ab', 'A', 'A#', 'Bb', 'B']
VALID_SCALES = list(SCALES.keys())

def validate_key(key: str) -> str:
    """Normalize and validate key name."""
    key = key.strip().capitalize()
    if key not in VALID_KEYS:
        raise ValueError(f"Invalid key: {key}. Valid: {VALID_KEYS}")
    return key

def validate_scale(scale: str) -> str:
    """Normalize and validate scale name."""
    scale = scale.strip().lower()
    if scale not in VALID_SCALES:
        raise ValueError(f"Invalid scale: {scale}. Valid: {VALID_SCALES}")
    return scale
```

## Testing Strategy
- Unit tests for each conversion function
- Property tests: `midi_to_freq(freq_to_midi(f)) ≈ f`
- Scale membership tests
- Chord spelling tests
- Harmony generation with known melodies