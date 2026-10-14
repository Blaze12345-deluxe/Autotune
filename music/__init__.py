# Music Theory Package

"""Music theory utilities for Auto-Tune & Harmoniser.

This package provides:
- Note/frequency/MIDI conversions
- Scale definitions and quantization
- Chord construction and voicing
- Interval arithmetic
- Harmony generation rules
"""

from .chords import (
    CHORD_QUALITIES,
    Chord,
    chord_from_degree,
    get_chord_notes,
    get_chord_symbol,
    get_diatonic_chords,
    parse_chord_symbol,
    voice_lead_chords,
)
from .harmony import (
    HARMONY_RULES,
    apply_harmony_smoothing,
    create_harmony_preset,
    generate_chord_harmonies,
    generate_diatonic_harmonies,
    generate_harmony_notes,
    get_harmony_mode_description,
    smooth_voice_leading,
)
from .intervals import (
    INTERVALS,
    SEMITONES_TO_INTERVAL,
    equal_temp_to_just,
    get_harmonic_series,
    get_intervals_from_root,
    get_subharmonic_series,
    interval_between,
    interval_between_midi,
    interval_name,
    interval_quality,
    invert_interval,
    just_intervals,
    transpose_freq,
    transpose_midi,
)
from .notes import (
    A4_FREQ,
    A4_MIDI,
    VOICE_MAX_FREQ,
    VOICE_MIN_FREQ,
    cents_between,
    cents_to_ratio,
    freq_to_midi,
    get_note_info,
    hz_to_note_name,
    midi_to_freq,
    midi_to_note_name,
    note_name_to_midi,
    ratio_to_cents,
    transpose_freq,
)
from .scales import (
    SCALES,
    VALID_KEYS,
    VALID_SCALES,
    Scale,
    cents_to_scale,
    get_scale_info,
    get_scale_notes,
    quantize_freq_to_scale,
    quantize_to_scale,
    validate_key,
    validate_scale,
)

__all__ = [
    # Notes
    "midi_to_freq",
    "freq_to_midi",
    "note_name_to_midi",
    "midi_to_note_name",
    "cents_to_ratio",
    "ratio_to_cents",
    "cents_between",
    "transpose_freq",
    "hz_to_note_name",
    "get_note_info",
    "A4_FREQ",
    "A4_MIDI",
    "VOICE_MIN_FREQ",
    "VOICE_MAX_FREQ",
    # Scales
    "Scale",
    "get_scale_notes",
    "quantize_to_scale",
    "quantize_freq_to_scale",
    "cents_to_scale",
    "validate_key",
    "validate_scale",
    "get_scale_info",
    "SCALES",
    "VALID_KEYS",
    "VALID_SCALES",
    # Chords
    "Chord",
    "get_diatonic_chords",
    "chord_from_degree",
    "get_chord_notes",
    "voice_lead_chords",
    "get_chord_symbol",
    "parse_chord_symbol",
    "CHORD_QUALITIES",
    # Intervals
    "interval_name",
    "interval_between",
    "interval_between_midi",
    "transpose_freq",
    "transpose_midi",
    "invert_interval",
    "interval_quality",
    "get_intervals_from_root",
    "get_harmonic_series",
    "get_subharmonic_series",
    "just_intervals",
    "equal_temp_to_just",
    "INTERVALS",
    "SEMITONES_TO_INTERVAL",
    # Harmony
    "generate_harmony_notes",
    "generate_diatonic_harmonies",
    "generate_chord_harmonies",
    "smooth_voice_leading",
    "apply_harmony_smoothing",
    "create_harmony_preset",
    "get_harmony_mode_description",
    "HARMONY_RULES",
]

__version__ = "0.1.0"
