# Music Theory - Harmony Generation

"""Harmony generation rules and voice leading."""



from .chords import get_diatonic_chords
from .intervals import interval_between
from .notes import freq_to_midi, midi_to_freq, transpose_freq
from .scales import Scale

# Traditional harmony intervals above melody note
HARMONY_RULES = {
    "parallel_thirds": {
        "name": "Parallel Thirds",
        "intervals_fn": lambda scale, degree: [3 if scale.get_degree(degree) in [2, 3, 6] else 4],
        "description": "Diatonic third above melody",
    },
    "parallel_sixths": {
        "name": "Parallel Sixths",
        "intervals_fn": lambda scale, degree: [9 if scale.get_degree(degree) in [2, 3, 6] else 8],
        "description": "Diatonic sixth below melody (inverted third)",
    },
    "triad": {
        "name": "Root Position Triad",
        "intervals": [4, 7],
        "description": "Major triad (adjusts for minor)",
    },
    "first_inversion": {
        "name": "First Inversion Triad",
        "intervals": [3, 8],
        "description": "Third in bass",
    },
    "second_inversion": {
        "name": "Second Inversion Triad",
        "intervals": [5, 9],
        "description": "Fifth in bass",
    },
    "power_chord": {
        "name": "Power Chord",
        "intervals": [7, 12],
        "description": "Fifth + octave",
    },
    "quartal": {
        "name": "Quartal Harmony",
        "intervals": [5, 10],
        "description": "Fourth + minor seventh",
    },
    "quintal": {
        "name": "Quintal Harmony",
        "intervals": [7, 14],
        "description": "Fifth + major ninth",
    },
    "octaves": {
        "name": "Octave Doubling",
        "intervals": [-12, 12],
        "description": "Octave below and above",
    },
}


def generate_harmony_notes(
    melody_freq: float,
    key: str,
    scale_type: str,
    rule: str = "parallel_thirds",
    voices: int = 2,
) -> list[float]:
    """Generate harmony frequencies for a melody note.

    Args:
        melody_freq: Melody frequency in Hz
        key: Musical key
        scale_type: Scale type
        rule: Harmony rule name
        voices: Number of harmony voices to generate

    Returns:
        List of harmony frequencies (not including melody)
    """
    if melody_freq <= 0:
        return []

    scale = Scale(key, scale_type)
    melody_midi = freq_to_midi(melody_freq)
    melody_degree = scale.get_degree(round(melody_midi))

    rule_config = HARMONY_RULES.get(rule, HARMONY_RULES["parallel_thirds"])

    if "intervals_fn" in rule_config:
        # Dynamic intervals based on scale degree
        intervals = rule_config["intervals_fn"](scale, melody_degree)
    else:
        # Fixed intervals
        intervals = rule_config.get("intervals", [3, 7])

    # Generate harmony frequencies
    harmonies = []
    for interval in intervals[:voices]:
        harmony_freq = transpose_freq(melody_freq, interval)
        harmonies.append(harmony_freq)

    return harmonies


def generate_diatonic_harmonies(
    melody_freq: float,
    key: str,
    scale_type: str,
    degrees: tuple[int, ...] = (2, 4),  # Scale degrees for harmonies (1=root, 3=third, etc.)
    max_voices: int = 3,
) -> list[float]:
    """Generate diatonic harmonies based on scale degrees.

    Args:
        melody_freq: Melody frequency
        key: Musical key
        scale_type: Scale type
        degrees: Scale degrees to use for harmonies (relative to melody)
        max_voices: Maximum number of harmony voices

    Returns:
        List of harmony frequencies
    """
    if melody_freq <= 0:
        return []

    scale = Scale(key, scale_type)
    melody_midi = freq_to_midi(melody_freq)
    melody_degree = scale.get_degree(round(melody_midi))

    if melody_degree == 0:
        # Not in scale, fall back to fixed intervals
        return generate_harmony_notes(melody_freq, key, scale_type, "triad", max_voices)

    harmonies = []
    scale_notes = scale.sorted_notes

    for degree_offset in degrees[:max_voices]:
        target_degree = (melody_degree + degree_offset - 1) % 7 + 1
        target_midi = scale_notes[target_degree - 1]

        # Adjust octave to be close to melody
        while target_midi < melody_midi - 6:
            target_midi += 12
        while target_midi > melody_midi + 18:
            target_midi -= 12

        harmonies.append(midi_to_freq(target_midi))

    return harmonies


def generate_chord_harmonies(
    melody_freq: float,
    key: str,
    scale_type: str,
    chord_quality: str = "major",
    max_voices: int = 3,
) -> list[float]:
    """Generate harmonies based on current chord.

    Args:
        melody_freq: Melody frequency
        key: Musical key
        scale_type: Scale type
        chord_quality: Chord quality to harmonize with
        max_voices: Maximum harmony voices

    Returns:
        List of harmony frequencies
    """
    if melody_freq <= 0:
        return []

    # Get diatonic chords for the key
    chords = get_diatonic_chords(key, scale_type)

    # Find which chord the melody note belongs to
    melody_midi = round(freq_to_midi(melody_freq))

    best_chord = None

    for _degree, chord in chords.items():
        if melody_midi in chord.notes:
            best_chord = chord
            break

    if best_chord is None:
        # Fallback to scale-based
        return generate_diatonic_harmonies(melody_freq, key, scale_type, (2, 4), max_voices)

    # Get chord tones above melody
    chord_tones = [n for n in best_chord.notes if n > melody_midi]
    chord_tones = sorted(chord_tones)[:max_voices]

    return [midi_to_freq(n) for n in chord_tones]


def smooth_voice_leading(
    prev_harmonies: list[float],
    new_harmonies: list[float],
    max_jump_semitones: float = 6,
    max_octave_jump: int = 1,
) -> list[float]:
    """Adjust harmony octaves for smooth voice leading.

    Args:
        prev_harmonies: Previous harmony frequencies
        new_harmonies: New target harmony frequencies
        max_jump_semitones: Maximum semitone jump between consecutive harmonies
        max_octave_jump: Maximum octaves to adjust

    Returns:
        Octave-adjusted harmony frequencies
    """
    if not prev_harmonies:
        return new_harmonies

    smoothed = []
    for i, new_f in enumerate(new_harmonies):
        if i < len(prev_harmonies):
            prev_f = prev_harmonies[i]

            # Find the best octave for this harmony
            best_f = new_f
            best_distance = float("inf")

            for octave_shift in range(-max_octave_jump, max_octave_jump + 1):
                candidate = new_f * (2**octave_shift)
                distance = abs(interval_between(prev_f, candidate))

                if distance < best_distance:
                    best_distance = distance
                    best_f = candidate

            # If still too large a jump, limit it
            if best_distance > max_jump_semitones:
                # Move toward previous note but limit jump
                direction = 1 if new_f > prev_f else -1
                best_f = prev_f * (2 ** (direction * max_jump_semitones / 12))

            smoothed.append(best_f)
        else:
            smoothed.append(new_f)

    return smoothed


def apply_harmony_smoothing(
    harmonies: list[float],
    prev_harmonies: list[float] | None,
    alpha: float = 0.1,
) -> list[float]:
    """Apply exponential smoothing to harmony frequencies.

    Args:
        harmonies: Current target harmonies
        prev_harmonies: Previous harmonies (or None)
        alpha: Smoothing factor (0-1, higher = faster)

    Returns:
        Smoothed harmony frequencies
    """
    if prev_harmonies is None:
        return harmonies

    smoothed = []
    for i, new_f in enumerate(harmonies):
        if i < len(prev_harmonies):
            prev_f = prev_harmonies[i]
            # Exponential smoothing in log space (cents)
            new_cents = freq_to_midi(new_f) * 100
            prev_cents = freq_to_midi(prev_f) * 100
            smoothed_cents = prev_cents + alpha * (new_cents - prev_cents)
            smoothed.append(midi_to_freq(smoothed_cents / 100))
        else:
            smoothed.append(new_f)

    return smoothed


def create_harmony_preset(name: str) -> dict:
    """Get predefined harmony preset.

    Args:
        name: Preset name

    Returns:
        Dictionary with harmony settings
    """
    presets = {
        "subtle": {
            "voice_volumes": (1.0, 0.3, 0.2),
            "intervals": (3, 7),  # Third, fifth
            "description": "Subtle backup harmony",
        },
        "backup_vocal": {
            "voice_volumes": (1.0, 0.6, 0.6),
            "intervals": (3, 7),
            "description": "Standard backup vocal style",
        },
        "choir": {
            "voice_volumes": (0.8, 0.5, 0.5, 0.4),
            "intervals": (-12, 3, 7, 12),
            "description": "Full choir with octaves",
        },
        "power_chord": {
            "voice_volumes": (1.0, 0.8, 0.6),
            "intervals": (7, 12),
            "description": "Rock power chord style",
        },
        "barbershop": {
            "voice_volumes": (1.0, 0.7, 0.7, 0.6),
            "intervals": (-5, 4, 7),  # Tenor, lead, baritone, bass (relative)
            "description": "Barbershop quartet style",
        },
        "jazz": {
            "voice_volumes": (1.0, 0.5, 0.5, 0.4),
            "intervals": (4, 7, 11),  # Maj7 chord
            "description": "Jazz major 7th harmony",
        },
        "parallel_fifths": {
            "voice_volumes": (1.0, 0.7),
            "intervals": (7,),
            "description": "Parallel fifths (organum style)",
        },
        "parallel_fourths": {
            "voice_volumes": (1.0, 0.7),
            "intervals": (5,),
            "description": "Parallel fourths",
        },
    }

    return presets.get(name, presets["backup_vocal"])


def get_harmony_mode_description(mode: str) -> str:
    """Get description of harmony mode."""
    descriptions = {
        "intervals": "Fixed semitone intervals above detected pitch",
        "scale": "Diatonic harmonies following the key/scale",
        "chord": "Harmonize to the current chord (requires chord detection)",
    }
    return descriptions.get(mode, "Unknown mode")
