# Music Theory - Note Conversions

"""Note name, frequency, and MIDI number conversions."""


import numpy as np

# Constants
A4_MIDI = 69
A4_FREQ = 440.0

NOTE_NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTE_NAMES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

# Voice frequency range
VOICE_MIN_FREQ = 65.41  # C2
VOICE_MAX_FREQ = 1046.50  # C6


def midi_to_freq(midi: float | np.ndarray) -> float | np.ndarray:
    """Convert MIDI note number(s) to frequency in Hz.

    Args:
        midi: MIDI note number (69 = A4 = 440Hz), can be fractional for cents

    Returns:
        Frequency in Hz
    """
    return A4_FREQ * 2.0 ** ((midi - A4_MIDI) / 12.0)


def freq_to_midi(freq: float | np.ndarray) -> float | np.ndarray:
    """Convert frequency in Hz to MIDI note number.

    Args:
        freq: Frequency in Hz

    Returns:
        Continuous MIDI note number (can be fractional)
    """
    if isinstance(freq, np.ndarray):
        result = np.zeros_like(freq, dtype=float)
        mask = freq > 0
        result[mask] = A4_MIDI + 12.0 * np.log2(freq[mask] / A4_FREQ)
        result[~mask] = 0.0
        return result
    if freq <= 0:
        return 0.0
    return A4_MIDI + 12.0 * np.log2(freq / A4_FREQ)


def note_name_to_midi(note_name: str) -> int:
    """Convert note name (e.g., 'C4', 'F#3', 'Bb5') to MIDI note number.

    Args:
        note_name: Note name with optional accidental and octave

    Returns:
        MIDI note number (0-127)

    Raises:
        ValueError: If note name is invalid
    """
    note_name = note_name.strip()
    if len(note_name) < 2:
        raise ValueError(f"Invalid note name: {note_name}")

    # Parse note letter
    letter = note_name[0].upper()
    if letter not in "ABCDEFG":
        raise ValueError(f"Invalid note letter: {letter}")

    # Parse accidental
    accidental = 0
    idx = 1
    if idx < len(note_name):
        if note_name[idx] == "#":
            accidental = 1
            idx += 1
        elif note_name[idx] in ("b", "♭"):
            accidental = -1
            idx += 1

    # Parse octave
    if idx >= len(note_name):
        raise ValueError(f"Missing octave in note name: {note_name}")

    try:
        octave = int(note_name[idx:])
    except ValueError:
        raise ValueError(f"Invalid octave in note name: {note_name}")

    # Note to pitch class (C=0, D=2, E=4, F=5, G=7, A=9, B=11)
    note_to_pc = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    pitch_class = (note_to_pc[letter] + accidental) % 12

    # MIDI note = pitch_class + (octave + 1) * 12
    midi = pitch_class + (octave + 1) * 12

    if not 0 <= midi <= 127:
        raise ValueError(f"Note out of MIDI range: {note_name} -> {midi}")

    return midi


def midi_to_note_name(midi: int, prefer_sharps: bool = True) -> str:
    """Convert MIDI note number to note name (e.g., 'C4', 'F#3').

    Args:
        midi: MIDI note number (0-127)
        prefer_sharps: Use sharps (True) or flats (False) for accidentals

    Returns:
        Note name string
    """
    if not 0 <= midi <= 127:
        raise ValueError(f"MIDI note out of range: {midi}")

    octave = midi // 12 - 1
    pitch_class = midi % 12

    if prefer_sharps:
        name = NOTE_NAMES_SHARP[pitch_class]
    else:
        name = NOTE_NAMES_FLAT[pitch_class]

    return f"{name}{octave}"


def cents_to_ratio(cents: float) -> float:
    """Convert cents to frequency ratio.

    Args:
        cents: Interval in cents (100 cents = 1 semitone)

    Returns:
        Frequency ratio
    """
    return 2.0 ** (cents / 1200.0)


def ratio_to_cents(ratio: float) -> float:
    """Convert frequency ratio to cents.

    Args:
        ratio: Frequency ratio

    Returns:
        Interval in cents
    """
    if ratio <= 0:
        return 0.0
    return 1200.0 * np.log2(ratio)


def cents_between(f1: float, f2: float) -> float:
    """Calculate cents difference from f1 to f2.

    Args:
        f1: Reference frequency
        f2: Target frequency

    Returns:
        Cents difference (positive = f2 higher than f1)
    """
    if f1 <= 0 or f2 <= 0:
        return 0.0
    return 1200.0 * np.log2(f2 / f1)


def transpose_freq(freq: float, semitones: float) -> float:
    """Transpose frequency by semitones.

    Args:
        freq: Input frequency in Hz
        semitones: Number of semitones to transpose (can be fractional)

    Returns:
        Transposed frequency in Hz
    """
    return freq * 2.0 ** (semitones / 12.0)


def hz_to_note_name(freq: float, prefer_sharps: bool = True) -> str:
    """Convert frequency to nearest note name.

    Args:
        freq: Frequency in Hz
        prefer_sharps: Use sharps for accidentals

    Returns:
        Nearest note name
    """
    midi = freq_to_midi(freq)
    return midi_to_note_name(int(round(midi)), prefer_sharps)


def get_note_info(freq: float) -> dict:
    """Get detailed note information for a frequency.

    Args:
        freq: Frequency in Hz

    Returns:
        Dictionary with note info
    """
    midi = freq_to_midi(freq)
    midi_rounded = int(round(midi))
    cents_off = (midi - midi_rounded) * 100

    return {
        "frequency": freq,
        "midi": midi,
        "midi_rounded": midi_rounded,
        "note_name": midi_to_note_name(midi_rounded),
        "cents_off": float(cents_off),
        "is_in_tune": abs(cents_off) < 25,
    }


def get_enharmonic_equivalent(note_name: str) -> str:
    """Get enharmonic equivalent (e.g., G#4 -> Ab4)."""
    # This is a simple mapping for common cases
    equivalents = {
        "C#": "Db",
        "D#": "Eb",
        "F#": "Gb",
        "G#": "Ab",
        "A#": "Bb",
        "Db": "C#",
        "Eb": "D#",
        "Gb": "F#",
        "Ab": "G#",
        "Bb": "A#",
    }
    for sharp, flat in equivalents.items():
        if note_name.startswith(sharp):
            return note_name.replace(sharp, flat)
    return note_name
