# Music Theory - Intervals

"""Interval arithmetic and operations."""

import numpy as np

from .notes import transpose_freq

# Interval names to semitones
INTERVALS = {
    "unison": 0,
    "minor_second": 1,
    "major_second": 2,
    "minor_third": 3,
    "major_third": 4,
    "perfect_fourth": 5,
    "tritone": 6,
    "augmented_fourth": 6,
    "diminished_fifth": 6,
    "perfect_fifth": 7,
    "minor_sixth": 8,
    "major_sixth": 9,
    "minor_seventh": 10,
    "major_seventh": 11,
    "octave": 12,
    "minor_ninth": 13,
    "major_ninth": 14,
    "perfect_eleventh": 17,
    "major_thirteenth": 21,
}

# Reverse lookup
SEMITONES_TO_INTERVAL = {v: k for k, v in INTERVALS.items()}

# Simple interval names (within octave)
SIMPLE_INTERVALS = {
    0: "unison",
    1: "minor 2nd",
    2: "major 2nd",
    3: "minor 3rd",
    4: "major 3rd",
    5: "perfect 4th",
    6: "tritone",
    7: "perfect 5th",
    8: "minor 6th",
    9: "major 6th",
    10: "minor 7th",
    11: "major 7th",
    12: "octave",
}

# Compound interval names
COMPOUND_INTERVALS = {
    13: "minor 9th",
    14: "major 9th",
    15: "minor 10th",
    16: "major 10th",
    17: "perfect 11th",
    18: "augmented 11th",
    19: "minor 12th",
    20: "major 12th",
    21: "major 13th",
    22: "minor 13th",
    24: "double octave",
}


def interval_name(semitones: int) -> str:
    """Get interval name from semitone count.

    Args:
        semitones: Number of semitones (can be negative or > 12)

    Returns:
        Interval name string
    """
    if semitones == 0:
        return "unison"

    sign = "-" if semitones < 0 else ""
    semitones = abs(semitones)

    octaves = semitones // 12
    simple = semitones % 12

    if simple == 0:
        return f"{sign}{octaves} octave{'s' if octaves > 1 else ''}"

    name = SIMPLE_INTERVALS.get(simple, f"{semitones} semitones")

    if octaves > 0:
        if simple in COMPOUND_INTERVALS:
            # Use compound name for common ones
            name = COMPOUND_INTERVALS.get(semitones, name)
        else:
            name = f"{name} (+{octaves} octave{'s' if octaves > 1 else ''})"

    return f"{sign}{name}"


def interval_between(f1: float, f2: float) -> float:
    """Calculate semitones between two frequencies.

    Args:
        f1: Reference frequency
        f2: Target frequency

    Returns:
        Semitone difference (positive = f2 higher)
    """
    if f1 <= 0 or f2 <= 0:
        return 0.0
    return 12.0 * np.log2(f2 / f1)


def interval_between_midi(m1: float, m2: float) -> float:
    """Calculate semitones between two MIDI note numbers.

    Args:
        m1: Reference MIDI note
        m2: Target MIDI note

    Returns:
        Semitone difference
    """
    return m2 - m1


def transpose_freq(freq: float, semitones: float) -> float:
    """Transpose frequency by semitones.

    Args:
        freq: Input frequency in Hz
        semitones: Number of semitones to transpose (can be fractional)

    Returns:
        Transposed frequency in Hz
    """
    if freq <= 0:
        return 0.0
    return freq * 2.0 ** (semitones / 12.0)


def transpose_midi(midi: float, semitones: float) -> float:
    """Transpose MIDI note by semitones.

    Args:
        midi: Input MIDI note number
        semitones: Number of semitones to transpose

    Returns:
        Transposed MIDI note number
    """
    return midi + semitones


def invert_interval(semitones: int) -> int:
    """Invert an interval (e.g., major 3rd -> minor 6th).

    Args:
        semitones: Interval in semitones (0-12)

    Returns:
        Inverted interval in semitones
    """
    return (12 - semitones) % 12


def interval_quality(semitones: int) -> str:
    """Get interval quality (perfect, major, minor, augmented, diminished).

    Args:
        semitones: Interval in semitones (0-12)

    Returns:
        Quality string
    """
    semitones = semitones % 12
    if semitones in (0, 5, 7, 12):
        return "perfect"
    elif semitones in (2, 4, 9, 11):
        return "major"
    elif semitones in (1, 3, 8, 10):
        return "minor"
    elif semitones in (6,):
        return "augmented/diminished"
    return "unknown"


def get_intervals_from_root(root_freq: float, intervals: list[int]) -> list[float]:
    """Get frequencies at specified intervals from root.

    Args:
        root_freq: Root frequency in Hz
        intervals: List of semitone intervals

    Returns:
        List of frequencies
    """
    return [transpose_freq(root_freq, i) for i in intervals]


def get_harmonic_series(fundamental: float, n_harmonics: int = 16) -> list[float]:
    """Get harmonic series frequencies.

    Args:
        fundamental: Fundamental frequency
        n_harmonics: Number of harmonics to generate

    Returns:
        List of harmonic frequencies
    """
    return [fundamental * (i + 1) for i in range(n_harmonics)]


def get_subharmonic_series(fundamental: float, n_subharmonics: int = 8) -> list[float]:
    """Get subharmonic series frequencies (undertones).

    Args:
        fundamental: Fundamental frequency
        n_subharmonics: Number of subharmonics

    Returns:
        List of subharmonic frequencies
    """
    return [fundamental / (i + 1) for i in range(n_subharmonics)]


def just_intervals() -> dict[str, float]:
    """Get just intonation intervals as frequency ratios.

    Returns:
        Dictionary mapping interval name to ratio
    """
    return {
        "unison": 1 / 1,
        "minor_second": 16 / 15,
        "major_second": 9 / 8,
        "minor_third": 6 / 5,
        "major_third": 5 / 4,
        "perfect_fourth": 4 / 3,
        "tritone": 45 / 32,  # or 64/45
        "perfect_fifth": 3 / 2,
        "minor_sixth": 8 / 5,
        "major_sixth": 5 / 3,
        "minor_seventh": 9 / 5,  # or 16/9
        "major_seventh": 15 / 8,
        "octave": 2 / 1,
    }


def equal_temp_to_just(semitones: int) -> float:
    """Convert equal temperament semitones to just intonation ratio.

    Args:
        semitones: Semitones in 12-TET

    Returns:
        Just intonation frequency ratio
    """
    just = just_intervals()
    interval_map = {
        0: "unison",
        1: "minor_second",
        2: "major_second",
        3: "minor_third",
        4: "major_third",
        5: "perfect_fourth",
        6: "tritone",
        7: "perfect_fifth",
        8: "minor_sixth",
        9: "major_sixth",
        10: "minor_seventh",
        11: "major_seventh",
        12: "octave",
    }
    name = interval_map.get(semitones % 12)
    if name:
        return just[name]
    # Fallback to equal temperament
    return 2.0 ** (semitones / 12.0)
