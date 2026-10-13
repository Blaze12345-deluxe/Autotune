# Music Theory - Scales

"""Scale definitions, quantization, and operations."""

from typing import List, Set, Dict, Optional
from dataclasses import dataclass
import numpy as np

from .notes import midi_to_freq, freq_to_midi, note_name_to_midi, midi_to_note_name


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

VALID_SCALES = list(SCALES.keys())
VALID_KEYS = ['C', 'C#', 'Db', 'D', 'D#', 'Eb', 'E', 'F', 'F#', 'Gb', 'G', 'G#', 'Ab', 'A', 'A#', 'Bb', 'B']


@dataclass
class Scale:
    """Musical scale with root and type."""
    root: str
    scale_type: str
    
    def __post_init__(self):
        self.root = self.root.strip().capitalize()
        self.scale_type = self.scale_type.strip().lower()
        
        if self.root not in VALID_KEYS:
            raise ValueError(f"Invalid key: {self.root}. Valid: {VALID_KEYS}")
        if self.scale_type not in VALID_SCALES:
            raise ValueError(f"Invalid scale: {self.scale_type}. Valid: {VALID_SCALES}")
        
        self.root_pc = note_name_to_midi(self.root + '4') % 12
        self.intervals = SCALES[self.scale_type]
        self._build_note_set()
    
    def _build_note_set(self):
        """Build set of all MIDI notes in this scale across piano range."""
        self.notes: Set[int] = set()
        for octave in range(0, 11):  # MIDI octaves 0-10
            for interval in self.intervals:
                midi = self.root_pc + interval + octave * 12
                if 0 <= midi <= 127:
                    self.notes.add(midi)
        self.sorted_notes = sorted(self.notes)
    
    def contains(self, midi: int) -> bool:
        """Check if MIDI note is in scale."""
        return midi in self.notes
    
    def contains_freq(self, freq: float) -> bool:
        """Check if frequency corresponds to a scale note."""
        if freq <= 0:
            return False
        midi = int(round(freq_to_midi(freq)))
        return self.contains(midi)
    
    def nearest_note(self, midi: float) -> int:
        """Find nearest scale note to given MIDI (can be fractional)."""
        if not self.sorted_notes:
            return int(round(midi))
        return min(self.sorted_notes, key=lambda n: abs(n - midi))
    
    def nearest_note_freq(self, freq: float) -> float:
        """Find nearest scale frequency to given frequency."""
        if freq <= 0:
            return 0.0
        midi = freq_to_midi(freq)
        nearest_midi = self.nearest_note(midi)
        return midi_to_freq(nearest_midi)
    
    def get_degree(self, midi: int) -> int:
        """Get scale degree (1-7) of a note, or 0 if not in scale."""
        pc = midi % 12
        for i, interval in enumerate(self.intervals):
            if (self.root_pc + interval) % 12 == pc:
                return i + 1
        return 0
    
    def get_degree_freq(self, freq: float) -> int:
        """Get scale degree of a frequency."""
        if freq <= 0:
            return 0
        midi = int(round(freq_to_midi(freq)))
        return self.get_degree(midi)
    
    def quantize(self, midi: float) -> int:
        """Quantize continuous MIDI to nearest scale note."""
        return self.nearest_note(midi)
    
    def quantize_freq(self, freq: float) -> float:
        """Quantize frequency to nearest scale frequency."""
        return self.nearest_note_freq(freq)
    
    def get_notes_in_octave(self, octave: int) -> List[int]:
        """Get scale notes in a specific MIDI octave (where C4 = octave 4 = MIDI 60)."""
        # MIDI convention: C4 = 60, C3 = 48
        # Formula: midi = (octave + 1) * 12 + pitch_class
        # For C major (root_pc=0), octave 4 -> base = (4+1)*12 + 0 = 60 (C4)
        base = (octave + 1) * 12 + self.root_pc
        notes = []
        for interval in self.intervals:
            midi = base + interval
            if 0 <= midi <= 127:
                notes.append(midi)
        return sorted(notes)


def get_scale_notes(key: str, scale_type: str) -> List[int]:
    """Get all MIDI notes in scale for given key across full range.
    
    Args:
        key: Root note name (e.g., 'C', 'F#', 'Bb')
        scale_type: Scale type (e.g., 'major', 'minor')
        
    Returns:
        Sorted list of MIDI note numbers in the scale
    """
    scale = Scale(key, scale_type)
    return scale.sorted_notes


def quantize_to_scale(midi: float, key: str, scale_type: str) -> int:
    """Quantize continuous MIDI to nearest scale note.
    
    Args:
        midi: Continuous MIDI note number
        key: Root note name
        scale_type: Scale type
        
    Returns:
        Quantized MIDI note number (integer)
    """
    scale = Scale(key, scale_type)
    return scale.nearest_note(midi)


def quantize_freq_to_scale(freq: float, key: str, scale_type: str) -> float:
    """Quantize frequency to nearest scale frequency.
    
    Args:
        freq: Frequency in Hz
        key: Root note name
        scale_type: Scale type
        
    Returns:
        Quantized frequency in Hz
    """
    if freq <= 0:
        return 0.0
    scale = Scale(key, scale_type)
    return scale.nearest_note_freq(freq)


def cents_to_scale(freq: float, key: str, scale_type: str) -> float:
    """Calculate cents difference from frequency to nearest scale note.
    
    Args:
        freq: Input frequency
        key: Root note name
        scale_type: Scale type
        
    Returns:
        Cents offset (positive = sharp, negative = flat)
    """
    if freq <= 0:
        return 0.0
    target = quantize_freq_to_scale(freq, key, scale_type)
    if target <= 0:
        return 0.0
    return 1200.0 * np.log2(freq / target)


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


def get_scale_info(key: str, scale_type: str) -> dict:
    """Get detailed information about a scale."""
    scale = Scale(key, scale_type)
    return {
        'key': scale.root,
        'scale_type': scale.scale_type,
        'intervals': scale.intervals,
        'note_names': [midi_to_note_name(n) for n in scale.get_notes_in_octave(4)],
        'pitch_classes': sorted([n % 12 for n in scale.sorted_notes]),
    }