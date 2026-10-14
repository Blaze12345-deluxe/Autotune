# Tests for Music Scales Module

"""Tests for scale definitions, quantization, and operations."""

import pytest

from music import (
    SCALES,
    Scale,
    cents_to_scale,
    get_scale_info,
    get_scale_notes,
    quantize_freq_to_scale,
    quantize_to_scale,
    validate_key,
    validate_scale,
)


class TestScaleDefinitions:
    """Test scale interval definitions."""

    def test_major_scale_intervals(self):
        """Major scale should be W-W-H-W-W-W-H."""
        assert SCALES["major"] == [0, 2, 4, 5, 7, 9, 11]

    def test_minor_scale_intervals(self):
        """Natural minor should be W-H-W-W-H-W-W."""
        assert SCALES["minor"] == [0, 2, 3, 5, 7, 8, 10]

    def test_pentatonic_scales(self):
        """Pentatonic scales should have 5 notes."""
        assert len(SCALES["pentatonic_major"]) == 5
        assert len(SCALES["pentatonic_minor"]) == 5

    def test_chromatic_scale(self):
        """Chromatic scale should have all 12 semitones."""
        assert SCALES["chromatic"] == list(range(12))

    def test_all_scales_valid(self):
        """All defined scales should have valid intervals."""
        for _name, intervals in SCALES.items():
            assert len(intervals) > 0
            assert all(0 <= i <= 11 for i in intervals)
            assert intervals[0] == 0  # Root
            assert intervals == sorted(intervals)  # Sorted


class TestScaleClass:
    """Test Scale class."""

    def test_c_major_scale(self):
        """C major scale notes."""
        scale = Scale("C", "major")
        assert scale.root == "C"
        assert scale.scale_type == "major"
        assert scale.root_pc == 0  # C = 0

    def test_fsharp_major_scale(self):
        """F# major scale."""
        scale = Scale("F#", "major")
        assert scale.root_pc == 6  # F# = 6

    def test_flat_keys(self):
        """Test flat key names."""
        scale = Scale("Bb", "major")
        assert scale.root_pc == 10  # Bb = 10

    def test_contains_c_major(self):
        """Test note membership in C major."""
        scale = Scale("C", "major")
        # C major: C, D, E, F, G, A, B
        assert scale.contains(60)  # C4
        assert scale.contains(62)  # D4
        assert scale.contains(64)  # E4
        assert scale.contains(65)  # F4
        assert scale.contains(67)  # G4
        assert scale.contains(69)  # A4
        assert scale.contains(71)  # B4
        # Not in C major
        assert not scale.contains(61)  # C#4
        assert not scale.contains(63)  # D#4

    def test_contains_a_minor(self):
        """Test note membership in A minor."""
        scale = Scale("A", "minor")
        # A minor: A, B, C, D, E, F, G
        assert scale.contains(69)  # A4
        assert scale.contains(71)  # B4
        assert scale.contains(60)  # C4
        assert scale.contains(62)  # D4
        assert scale.contains(64)  # E4
        assert scale.contains(65)  # F4
        assert scale.contains(67)  # G4

    def test_nearest_note(self):
        """Test nearest note quantization."""
        scale = Scale("C", "major")
        # 61 (C#4) should quantize to 60 (C4) or 62 (D4)
        nearest = scale.nearest_note(61.0)
        assert nearest in [60, 62]

    def test_get_degree(self):
        """Test scale degree detection."""
        scale = Scale("C", "major")
        assert scale.get_degree(60) == 1  # C = 1
        assert scale.get_degree(62) == 2  # D = 2
        assert scale.get_degree(64) == 3  # E = 3
        assert scale.get_degree(65) == 4  # F = 4
        assert scale.get_degree(67) == 5  # G = 5
        assert scale.get_degree(69) == 6  # A = 6
        assert scale.get_degree(71) == 7  # B = 7
        assert scale.get_degree(61) == 0  # C# not in scale

    def test_invalid_key(self):
        """Test invalid key raises error."""
        with pytest.raises(ValueError):
            Scale("H", "major")

    def test_invalid_scale(self):
        """Test invalid scale raises error."""
        with pytest.raises(ValueError):
            Scale("C", "invalid_scale")


class TestQuantizeToScale:
    """Test quantization functions."""

    def test_quantize_to_scale_midi(self):
        """Test MIDI quantization."""
        # 61.3 (slightly sharp C#) in C major -> should be 60 or 62
        result = quantize_to_scale(61.3, "C", "major")
        assert result in [60, 62]

    def test_quantize_freq_to_scale(self):
        """Test frequency quantization."""
        # 450 Hz (between A4=440 and A#4=466) in C major
        result = quantize_freq_to_scale(450.0, "C", "major")
        # Should be either A4 (440) or B4 (493.88)
        assert abs(result - 440.0) < 10 or abs(result - 493.88) < 10

    def test_cents_to_scale(self):
        """Test cents offset from scale."""
        # 440 Hz in C major -> A4 is in scale, should be ~0 cents
        cents = cents_to_scale(440.0, "C", "major")
        assert abs(cents) < 5

        # 450 Hz in C major -> between A4 and B4
        cents = cents_to_scale(450.0, "C", "major")
        # Should be positive (sharp relative to A4) or negative (flat relative to B4)
        assert abs(cents) < 100


class TestValidateFunctions:
    """Test validation functions."""

    def test_validate_key(self):
        """Test key validation."""
        assert validate_key("c") == "C"
        assert validate_key("C") == "C"
        assert validate_key("f#") == "F#"
        assert validate_key("Bb") == "Bb"

        with pytest.raises(ValueError):
            validate_key("H")

    def test_validate_scale(self):
        """Test scale validation."""
        assert validate_scale("MAJOR") == "major"
        assert validate_scale("Major") == "major"
        assert validate_scale("harmonic_minor") == "harmonic_minor"

        with pytest.raises(ValueError):
            validate_scale("invalid")


class TestScaleInfo:
    """Test scale info function."""

    def test_get_scale_info_c_major(self):
        """Test C major scale info."""
        info = get_scale_info("C", "major")
        assert info["key"] == "C"
        assert info["scale_type"] == "major"
        assert info["intervals"] == [0, 2, 4, 5, 7, 9, 11]
        assert "C4" in info["note_names"]
        assert "D4" in info["note_names"]
        assert "E4" in info["note_names"]


class TestGetScaleNotes:
    """Test get_scale_notes function."""

    def test_c_major_notes(self):
        """Get all C major notes."""
        notes = get_scale_notes("C", "major")
        # Should have notes across piano range
        assert len(notes) > 50
        # All should be in C major pitch classes
        pcs = {n % 12 for n in notes}
        assert pcs == {0, 2, 4, 5, 7, 9, 11}  # C major pitch classes

    def test_a_minor_notes(self):
        """Get all A minor notes."""
        notes = get_scale_notes("A", "minor")
        pcs = {n % 12 for n in notes}
        assert pcs == {9, 11, 0, 2, 4, 5, 7}  # A minor pitch classes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
