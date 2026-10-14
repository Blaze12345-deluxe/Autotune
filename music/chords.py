# Music Theory - Chords

"""Chord definitions, construction, and voicing."""

from dataclasses import dataclass

from .notes import midi_to_freq, midi_to_note_name, note_name_to_midi
from .scales import Scale

# Chord quality intervals from root (semitones)
CHORD_QUALITIES = {
    # Triads
    "major": [0, 4, 7],
    "minor": [0, 3, 7],
    "diminished": [0, 3, 6],
    "augmented": [0, 4, 8],
    # Seventh chords
    "dom7": [0, 4, 7, 10],
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "min_maj7": [0, 3, 7, 11],
    "half_dim7": [0, 3, 6, 10],  # m7b5
    "dim7": [0, 3, 6, 9],
    # Extended chords
    "9": [0, 4, 7, 10, 14],
    "maj9": [0, 4, 7, 11, 14],
    "min9": [0, 3, 7, 10, 14],
    "11": [0, 4, 7, 10, 14, 17],
    "13": [0, 4, 7, 10, 14, 21],
    # Suspended
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    # Power chord
    "power": [0, 7],
    "power_octave": [0, 7, 12],
}


@dataclass
class Chord:
    """Chord with root, quality, and optional scale context."""

    root_midi: int
    quality: str
    scale: Scale | None = None

    def __post_init__(self):
        self.quality = self.quality.lower()
        if self.quality not in CHORD_QUALITIES:
            raise ValueError(
                f"Unknown chord quality: {self.quality}. Valid: {list(CHORD_QUALITIES.keys())}"
            )
        self.intervals = CHORD_QUALITIES[self.quality]
        self.notes = [self.root_midi + i for i in self.intervals]

    @classmethod
    def from_root_name(cls, root_name: str, quality: str, scale: Scale | None = None) -> "Chord":
        """Create chord from root note name (e.g., 'C4', 'G3')."""
        root_midi = note_name_to_midi(root_name)
        return cls(root_midi, quality, scale)

    def get_notes(self, octave: int = 4) -> list[int]:
        """Get chord notes in specific octave range."""
        base = self.root_midi % 12 + octave * 12
        return [base + i for i in self.intervals]

    def get_frequencies(self) -> list[float]:
        """Get frequencies of chord notes."""
        return [midi_to_freq(n) for n in self.notes]

    def transpose(self, semitones: int) -> "Chord":
        """Return transposed chord."""
        return Chord(self.root_midi + semitones, self.quality, self.scale)

    def invert(self, inversion: int) -> list[int]:
        """Return chord notes with given inversion (0=root, 1=first, etc.)."""
        notes = self.notes.copy()
        for _ in range(inversion % len(notes)):
            notes.append(notes.pop(0) + 12)
        return notes

    def get_voicing(self, inversion: int = 0, octave: int = 4) -> list[int]:
        """Get chord voicing with inversion in specific MIDI octave (C4 = 60)."""
        notes = self.invert(inversion)
        # Transpose to target octave (MIDI convention: C4 = 60)
        # Target absolute MIDI for the chord root
        root_pc = self.root_midi % 12
        target_absolute_root = (octave + 1) * 12 + root_pc
        current_absolute_root = notes[0]
        diff = target_absolute_root - current_absolute_root
        return [n + diff for n in notes]

    def __repr__(self) -> str:
        root_name = midi_to_note_name(self.root_midi)
        return f"Chord({root_name}, {self.quality})"


def get_diatonic_chords(key: str, scale_type: str) -> dict[int, Chord]:
    """Get all diatonic chords for a key/scale.

    Args:
        key: Root note name (e.g., 'C', 'G')
        scale_type: Scale type (e.g., 'major', 'minor')

    Returns:
        Dictionary mapping scale degree (1-7) to Chord
    """
    scale = Scale(key, scale_type)
    chords = {}

    # Define chord qualities for each scale degree
    if scale_type in ["major", "ionian"]:
        # I, ii, iii, IV, V, vi, vii°
        qualities = ["major", "minor", "minor", "major", "major", "minor", "diminished"]
    elif scale_type in ["minor", "aeolian"]:
        # i, ii°, III, iv, v, VI, VII
        qualities = ["minor", "diminished", "major", "minor", "minor", "major", "major"]
    elif scale_type == "harmonic_minor":
        # i, ii°, III+, iv, V, VI, vii°
        qualities = ["minor", "diminished", "augmented", "minor", "major", "major", "diminished"]
    elif scale_type == "melodic_minor":
        # i, ii, III+, IV, V, vi°, vii°
        qualities = ["minor", "minor", "augmented", "major", "major", "diminished", "diminished"]
    elif scale_type == "dorian":
        qualities = ["minor", "minor", "major", "major", "minor", "diminished", "major"]
    elif scale_type == "phrygian":
        qualities = ["minor", "major", "major", "minor", "diminished", "major", "minor"]
    elif scale_type == "lydian":
        qualities = ["major", "major", "minor", "diminished", "major", "minor", "minor"]
    elif scale_type == "mixolydian":
        qualities = ["major", "minor", "diminished", "major", "minor", "major", "minor"]
    elif scale_type == "locrian":
        qualities = ["diminished", "major", "minor", "minor", "major", "major", "minor"]
    else:
        # Default to major qualities
        qualities = ["major"] * 7

    for degree, quality in enumerate(qualities, 1):
        # Get root note for this degree
        root_midi = scale.sorted_notes[degree - 1]
        # Adjust to be in a reasonable octave (around middle C = C4 = 60)
        while root_midi < 60:  # C4
            root_midi += 12
        while root_midi > 72:  # C5
            root_midi -= 12
        chords[degree] = Chord(root_midi, quality, scale)

    return chords


def chord_from_degree(
    key: str, scale_type: str, degree: int, quality: str | None = None
) -> Chord:
    """Get chord for a specific scale degree."""
    chords = get_diatonic_chords(key, scale_type)
    if degree not in chords:
        raise ValueError(f"Invalid degree: {degree}. Must be 1-7.")
    chord = chords[degree]
    if quality:
        return Chord(chord.root_midi, quality, chord.scale)
    return chord


def get_chord_notes(key: str, scale_type: str, degree: int) -> list[float]:
    """Get frequencies of diatonic chord on scale degree."""
    chord = chord_from_degree(key, scale_type, degree)
    # Ensure chord is in a reasonable octave for output
    freqs = chord.get_frequencies()
    return freqs


def voice_lead_chords(prev_chord: Chord, target_chord: Chord) -> list[int]:
    """Find smoothest voice leading from prev_chord to target_chord.

    Uses greedy algorithm to minimize total voice movement.

    Args:
        prev_chord: Previous chord
        target_chord: Target chord

    Returns:
        List of target chord notes with optimal voicing
    """
    prev_notes = prev_chord.notes
    target_notes = target_chord.notes

    # Try all inversions of target chord
    best_voicing = None
    best_movement = float("inf")

    for inv in range(len(target_notes)):
        voiced = target_chord.invert(inv)
        # Calculate total semitone movement
        movement = sum(abs(v - p) for v, p in zip(voiced, prev_notes, strict=False))
        if movement < best_movement:
            best_movement = movement
            best_voicing = voiced

    return best_voicing if best_voicing else target_chord.notes


def get_chord_symbol(chord: Chord) -> str:
    """Get chord symbol string (e.g., 'Cmaj7', 'G7', 'Dm')."""
    root = midi_to_note_name(chord.root_midi).rstrip("0123456789")
    quality_map = {
        "major": "",
        "minor": "m",
        "diminished": "dim",
        "augmented": "aug",
        "dom7": "7",
        "maj7": "maj7",
        "min7": "m7",
        "min_maj7": "m(maj7)",
        "half_dim7": "m7b5",
        "dim7": "dim7",
        "9": "9",
        "maj9": "maj9",
        "min9": "m9",
        "sus2": "sus2",
        "sus4": "sus4",
        "power": "5",
    }
    suffix = quality_map.get(chord.quality, chord.quality)
    return f"{root}{suffix}"


def parse_chord_symbol(symbol: str) -> tuple[str, str]:
    """Parse chord symbol into root and quality.

    Args:
        symbol: Chord symbol (e.g., 'Cmaj7', 'G7', 'Dm', 'F#dim', 'C')

    Returns:
        Tuple of (root_note, quality)
    """
    symbol = symbol.strip()
    if not symbol:
        raise ValueError(f"Invalid chord symbol: {symbol}")

    # Root is first char + optional accidental
    if len(symbol) >= 2 and symbol[1] in ("#", "b", "♭"):
        root = symbol[:2]
        quality = symbol[2:]
    else:
        root = symbol[0]
        quality = symbol[1:] if len(symbol) > 1 else ""

    # Map common quality suffixes
    quality_map = {
        "": "major",
        "m": "minor",
        "min": "minor",
        "mi": "minor",
        "dim": "diminished",
        "°": "diminished",
        "o": "diminished",
        "aug": "augmented",
        "+": "augmented",
        "7": "dom7",
        "dom7": "dom7",
        "maj7": "maj7",
        "M7": "maj7",
        "Δ7": "maj7",
        "Δ": "maj7",
        "m7": "min7",
        "min7": "min7",
        "mi7": "min7",
        "-7": "min7",
        "m7b5": "half_dim7",
        "ø7": "half_dim7",
        "ø": "half_dim7",
        "dim7": "dim7",
        "°7": "dim7",
        "o7": "dim7",
        "sus2": "sus2",
        "sus4": "sus4",
        "sus": "sus4",
        "5": "power",
        "power": "power",
    }

    quality = quality_map.get(quality, quality)
    return root, quality
